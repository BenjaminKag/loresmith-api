from unittest import mock
from django.test import override_settings

from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from core import models
from core.ai_client import DailyBudgetExceeded, AiServiceError

ANALYZE_URL_NAME = "story-analyze"


def analyze_url(story_id: int) -> str:
    return reverse("story-analyze", args=[story_id])


def create_user(email="user@example.com", password="testpass123"):
    return get_user_model().objects.create_user(email=email, password=password)


def create_story(user, **params):
    defaults = {
        "title": "Test story",
        "summary": "Short summary",
        "body": "Longer body text for AI analysis.",
        "created_by": user,
    }
    defaults.update(params)
    return models.Story.objects.create(**defaults)


class StoryAIApiTests(APITestCase):
    """Tests for the story AI analyze endpoint."""

    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(self.user)

    @mock.patch("core.views.story.LoreAIService")
    def test_owner_can_analyze_story(self, mock_ai_service_cls):
        """Owner can call /analyze and gets structured response."""
        story = create_story(user=self.user)

        mock_service = mock_ai_service_cls.return_value
        mock_service.analyze_text.return_value = {
            "summary": "AI summary",
            "themes": ["theme1"],
            "tone": "serious",
            "strengths": ["strong point"],
            "weaknesses": ["weak point"],
            "suggestions": ["do X"],
            "meta": {"ai_mode": "live", "model": "test-model"},
        }

        res = self.client.post(analyze_url(story.id))

        assert res.status_code == status.HTTP_200_OK
        assert res.data["entity_id"] == story.id
        assert res.data["summary"] == "AI summary"
        assert res.data["themes"] == ["theme1"]
        mock_service.analyze_text.assert_called_once()

    def test_anonymous_cannot_analyze(self):
        """Unauthenticated user cannot access the analyze endpoint."""
        story = create_story(user=self.user)
        self.client.force_authenticate(user=None)

        res = self.client.post(analyze_url(story.id))

        assert res.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        )

    def test_non_owner_cannot_analyze(self):
        """Another authenticated user cannot analyze someone else's story."""
        other_user = create_user(email="other@example.com")
        story = create_story(user=self.user)

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
    @mock.patch("core.ai_client.LoreAIService._mock_response")
    def test_ai_uses_mock_mode_when_disabled(self, mock_mock_response):
        """AI should fall back to mock mode when disabled or no API key."""
        story = create_story(user=self.user)

        mock_mock_response.return_value = {
            "summary": "mock summary",
            "themes": ["theme1"],
            "tone": "neutral",
            "strengths": ["strength"],
            "weaknesses": ["weakness"],
            "suggestions": ["suggestion"],
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
        """Return 400 if story has no title/summary/body."""
        story = create_story(
            user=self.user,
            title="",
            summary="  ",  # whitespace only
            body="",
        )

        res = self.client.post(analyze_url(story.id))

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "Nothing to analyze" in res.data["detail"]

    @mock.patch("core.views.story.LoreAIService")
    def test_analyze_returns_429_when_daily_budget_exceeded(
        self,
        mock_ai_service_class,
    ):
        """Return 429 when AI daily budget is exceeded."""
        story = create_story(user=self.user)

        mock_service = mock_ai_service_class.return_value
        mock_service.analyze_text.side_effect = DailyBudgetExceeded(
            "AI daily budget or rate limit."
        )

        res = self.client.post(analyze_url(story.id))

        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "budget" in res.data["detail"].lower()

    @mock.patch("core.views.story.LoreAIService")
    def test_analyze_returns_503_when_ai_service_fails(
        self,
        mock_ai_service_class,
    ):
        """Return 503 when AI service raises an error."""
        story = create_story(user=self.user)

        mock_service = mock_ai_service_class.return_value
        mock_service.analyze_text.side_effect = AiServiceError(
            "AI service unavailable."
        )

        res = self.client.post(analyze_url(story.id))

        assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "ai" in res.data["detail"].lower()

    @mock.patch(
            "core.throttling.AIUserThrottle.get_rate",
            return_value="2/min"
    )
    @mock.patch("core.views.story.LoreAIService")
    def test_analyze_is_rate_limited_after_too_many_calls(
        self,
        mock_ai_service_class,
        _mock_get_rate,
    ):
        """User should be throttled on /analyze after exceeding the rate."""
        story = create_story(user=self.user)
        url = analyze_url(story.id)

        mock_service = mock_ai_service_class.return_value
        mock_service.analyze_text.return_value = {
            "summary": "AI summary",
            "themes": ["t"],
            "tone": "neutral",
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
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
