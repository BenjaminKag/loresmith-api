from unittest import mock
from django.test import override_settings

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache

from rest_framework.test import APITestCase
from rest_framework import status

from core import models
from core.services.ai_client import DailyBudgetExceeded, AiServiceError
from core.services import ai_idempotency

import uuid

ANALYZE_URL_NAME = "story-analyze"


def analyze_url(story_id: int) -> str:
    return reverse("story-analyze", args=[story_id])


def create_user(email=None, password="testpass123", **extra):
    """Helper function to create a new user."""
    if email is None:
        email = f"test_{uuid.uuid4().hex}@example.com"

    return get_user_model().objects.create_user(email, password, **extra)


def create_story(owner, **params):
    defaults = {
        "title": "Test story",
        "summary": "Short summary",
        "body": "Longer body text for AI analysis.",
        "owner": owner,
    }
    defaults.update(params)
    return models.Story.objects.create(**defaults)


class StoryAIApiTests(APITestCase):
    """Tests for the story AI analyze endpoint."""

    def setUp(self):
        cache.clear()
        self.user = create_user()
        self.user = create_user(is_premium=True)
        self.client.force_authenticate(self.user)

    @mock.patch("core.views.story.StoryAnalysisGenerator")
    def test_owner_can_analyze_story(self, mock_generator_cls):
        """Owner can call /analyze and gets structured response."""
        story = create_story(owner=self.user)

        mock_generator = mock_generator_cls.return_value
        mock_generator.generate.return_value = {
            "summary": "AI summary",
            "themes": ["theme1"],
            "tone": "serious",
            "strengths": ["strong point"],
            "weaknesses": ["weak point"],
            "suggestions": ["do X"],
            "consistency_notes": ["note"],
            "open_questions": ["question"],
            "meta": {"ai_mode": "live", "model": "test-model"},
        }

        res = self.client.post(analyze_url(story.id))

        assert res.status_code == status.HTTP_200_OK
        assert res.data["entity_id"] == story.id
        assert res.data["summary"] == "AI summary"
        assert res.data["themes"] == ["theme1"]
        mock_generator.generate.assert_called_once()

    def test_anonymous_cannot_analyze(self):
        """Unauthenticated user cannot access the analyze endpoint."""
        story = create_story(owner=self.user)
        self.client.force_authenticate(user=None)

        res = self.client.post(analyze_url(story.id))

        assert res.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        )

    def test_non_owner_cannot_analyze(self):
        """Another authenticated user cannot analyze someone else's story."""
        other_user = create_user(email="other@example.com")
        story = create_story(owner=self.user)

        self.client.force_authenticate(other_user)
        res = self.client.post(analyze_url(story.id))

        assert res.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        )

    @override_settings(
        LORESMITH_AI_ENABLED=False,
        OPENAI_API_KEY="",  # simulate "no key" as well
    )
    @mock.patch(
        "core.services.story_analysis_generator."
        "StoryAnalysisGenerator._mock_response"
    )
    def test_ai_uses_mock_mode_when_disabled(self, mock_mock_response):
        """AI should fall back to mock mode when disabled or no API key."""
        story = create_story(owner=self.user)

        mock_mock_response.return_value = {
            "summary": "mock summary",
            "themes": ["theme1"],
            "tone": "neutral",
            "strengths": ["strength"],
            "weaknesses": ["weakness"],
            "suggestions": ["suggestion"],
            "consistency_notes": ["note"],
            "open_questions": ["question"],
            "meta": {
                "ai_mode": "mock",
                "model": None,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }

        res = self.client.post(analyze_url(story.id))

        assert res.status_code == status.HTTP_200_OK
        assert res.data["meta"]["ai_mode"] == "mock"

        # Make sure the mock path was actually used
        mock_mock_response.assert_called_once()

    def test_analyze_returns_400_when_nothing_to_analyze(self):
        """Return 400 if story has no summary/body."""
        story = create_story(
            owner=self.user,
            title="Valid Title",
            summary="  ",  # whitespace only
            body="",
        )

        res = self.client.post(analyze_url(story.id))

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "Nothing to analyze" in res.data["detail"]

    @mock.patch("core.views.story.StoryAnalysisGenerator")
    def test_analyze_returns_429_when_daily_budget_exceeded(
        self,
        mock_generator_cls,
    ):
        """Return 429 when AI daily budget is exceeded."""
        story = create_story(owner=self.user)

        mock_generator = mock_generator_cls.return_value
        mock_generator.generate.side_effect = DailyBudgetExceeded(
            "AI daily budget or rate limit."
        )

        res = self.client.post(analyze_url(story.id))

        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "budget" in res.data["detail"].lower()

    @mock.patch("core.views.story.StoryAnalysisGenerator")
    def test_analyze_returns_503_when_ai_service_fails(
        self,
        mock_generator_cls,
    ):
        """Return 503 when AI service raises an error."""
        story = create_story(owner=self.user)

        mock_generator = mock_generator_cls.return_value
        mock_generator.generate.side_effect = AiServiceError(
            "AI service unavailable."
        )

        res = self.client.post(analyze_url(story.id))

        assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "ai" in res.data["detail"].lower()

    @mock.patch(
            "core.throttling.AIUserThrottle.get_rate",
            return_value="2/min"
    )
    @mock.patch("core.views.story.StoryAnalysisGenerator")
    def test_analyze_is_rate_limited_after_too_many_calls(
        self,
        mock_generator_cls,
        _mock_get_rate,
    ):
        """User should be throttled on /analyze after exceeding the rate."""
        story = create_story(owner=self.user)
        url = analyze_url(story.id)

        mock_generator = mock_generator_cls.return_value
        mock_generator.generate.return_value = {
            "summary": "AI summary",
            "themes": ["t"],
            "tone": "neutral",
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "consistency_notes": [],
            "open_questions": [],
            "meta": {"ai_mode": "live", "model": "test-model"},
        }

        # First two calls: within the "2/min" limit → should be 200
        res1 = self.client.post(url)
        res2 = self.client.post(url)

        # Third call: over the limit → should be 429
        res3 = self.client.post(url)

        assert res1.status_code == status.HTTP_200_OK
        assert res2.status_code == status.HTTP_200_OK
        assert res3.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_analyze_creates_ai_request_log(self):
        """Analyze should create a completed AI request log."""
        story = create_story(
            owner=self.user,
            title="Test Story",
            summary="A story summary.",
            body="A story body.",
        )

        self.client.force_authenticate(self.user)

        res = self.client.post(analyze_url(story.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        request_log = models.AIRequestLog.objects.get(
            owner=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
        )

        self.assertEqual(
            request_log.status,
            models.AIRequestStatus.COMPLETED,
        )
        self.assertEqual(request_log.response_payload["entity_type"], "story")
        self.assertEqual(request_log.response_payload["entity_id"], story.id)
        self.assertIsNotNone(request_log.completed_at)

    def test_duplicate_analyze_returns_deduped_response(self):
        """Duplicate analyze request should reuse recent completed response."""
        story = create_story(
            owner=self.user,
            title="Test Story",
            summary="A story summary.",
            body="A story body.",
        )

        self.client.force_authenticate(self.user)

        first_res = self.client.post(analyze_url(story.id))
        second_res = self.client.post(analyze_url(story.id))

        self.assertEqual(first_res.status_code, status.HTTP_200_OK)
        self.assertEqual(second_res.status_code, status.HTTP_200_OK)

        self.assertEqual(models.AIRequestLog.objects.count(), 1)
        self.assertTrue(second_res.data["meta"]["deduped"])
        self.assertEqual(second_res.data["entity_id"], story.id)

    def test_duplicate_in_progress_analyze_returns_429(self):
        """Analyze should return 429 if same request is already in progress."""
        story = create_story(
            owner=self.user,
            title="Test Story",
            summary="A story summary.",
            body="A story body.",
        )

        request_payload = {
            "story_id": story.id,
            "story_input": {
                "title": story.title,
                "summary": story.summary,
                "body": story.body,
                "parent": None,
            },
            "settings": {
                "endpoint_type": models.AIEndpointType.STORY_ANALYSIS,
            },
        }

        ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            request_payload=request_payload,
        )

        self.client.force_authenticate(self.user)

        res = self.client.post(analyze_url(story.id))

        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(
            res.data["detail"],
            "A matching story analysis request is already in progress.",
        )
        self.assertEqual(models.AIRequestLog.objects.count(), 1)

    @mock.patch("core.views.story.StoryAnalysisGenerator.generate")
    def test_failed_analyze_marks_ai_request_log_failed(self, mock_generate):
        """Failed AI analysis should mark the AI request log as failed."""
        mock_generate.side_effect = AiServiceError("AI generation failed.")

        story = create_story(
            owner=self.user,
            title="Test Story",
            summary="A story summary.",
            body="A story body.",
        )

        self.client.force_authenticate(self.user)

        res = self.client.post(analyze_url(story.id))

        self.assertEqual(
            res.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

        request_log = models.AIRequestLog.objects.get(
            owner=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
        )

        self.assertEqual(
            request_log.status,
            models.AIRequestStatus.FAILED,
        )
        self.assertEqual(request_log.error_message, "AI generation failed.")

    def test_non_premium_user_cannot_analyze_story(self):
        """Non-premium users cannot use story analysis."""
        self.user.is_premium = False
        self.user.save()

        story = create_story(owner=self.user)

        res = self.client.post(analyze_url(story.id))

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            res.data["detail"],
            "AI features require a premium plan.",
        )

    def test_analyze_creates_ai_usage_log(self):
        """Analyze should create an AI usage log."""
        story = create_story(
            owner=self.user,
            title="Test Story",
            summary="A story summary.",
            body="A story body.",
        )

        res = self.client.post(analyze_url(story.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        usage_log = models.AIUsageLog.objects.get(
            owner=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
        )

        self.assertEqual(usage_log.ai_mode, res.data["meta"]["ai_mode"])
        self.assertEqual(usage_log.model, res.data["meta"]["model"])
        self.assertEqual(
            usage_log.total_tokens,
            res.data["meta"]["total_tokens"],
        )
        self.assertIsNotNone(usage_log.request_log)

    def test_duplicate_analyze_does_not_create_new_usage_log(self):
        """Deduped analyze response should not create another usage log."""
        story = create_story(
            owner=self.user,
            title="Test Story",
            summary="A story summary.",
            body="A story body.",
        )

        first_res = self.client.post(analyze_url(story.id))
        second_res = self.client.post(analyze_url(story.id))

        self.assertEqual(first_res.status_code, status.HTTP_200_OK)
        self.assertEqual(second_res.status_code, status.HTTP_200_OK)
        self.assertTrue(second_res.data["meta"]["deduped"])

        self.assertEqual(models.AIUsageLog.objects.count(), 1)
