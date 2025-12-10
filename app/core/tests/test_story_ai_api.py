from unittest import mock

from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from core import models

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
