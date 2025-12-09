"""
Tests for the Story API.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from core import models


STORIES_URL = reverse("story-list")


def detail_url(story_id: int):
    """Create and return a story detail URL."""
    return reverse("story-detail", args=[story_id])


def create_user(**params):
    """Helper to create a user."""
    return get_user_model().objects.create_user(**params)


class StoryApiTests(APITestCase):
    """Tests for the Story API."""

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
            name="Test User",
        )
        self.client.force_authenticate(self.user)

    def test_create_story_with_relations(self):
        """
        Test creating a story with characters, locations, factions, and items.
        """
        location = models.Location.objects.create(
            name="Liyue Harbor",
            description="A bustling harbor city.",
            location_type="city",
        )
        faction = models.Faction.objects.create(
            name="Liyue Qixing",
            description="Leaders of Liyue.",
            faction_type="government",
        )
        item = models.Item.objects.create(
            name="Primordial Jade Winged-Spear",
            item_type="weapon",
            rarity="5-star",
        )
        character = models.Character.objects.create(
            name="Xiao",
            description="A vigilant yaksha.",
        )
        parent_story = models.Story.objects.create(
            title="Rex Lapis' Contract",
            summary="The long-standing contract of Liyue.",
            body="Once upon a time...",
        )

        payload = {
            "title": "Rite of Descension",
            "summary": "The ceremony where Rex Lapis appears.",
            "body": "Every year, the people of Liyue...",
            "kind": models.Story.Kind.PART,
            "story_type": models.Story.StoryType.WORLD_EVENT,
            "visibility": models.Story.Visibility.PRIVATE,
            "in_world_date": "Year 1107 AE",
            "parent": parent_story.id,
            "order": 3,
            "characters": [character.id],
            "locations": [location.id],
            "factions": [faction.id],
            "items": [item.id],
        }

        res = self.client.post(STORIES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        story = models.Story.objects.get(id=res.data["id"])

        self.assertEqual(story.title, "Rite of Descension")
        self.assertEqual(
            story.summary,
            "The ceremony where Rex Lapis appears.",
        )
        self.assertEqual(story.body, "Every year, the people of Liyue...")
        self.assertEqual(story.kind, models.Story.Kind.PART)
        self.assertEqual(story.story_type, models.Story.StoryType.WORLD_EVENT)
        self.assertEqual(story.visibility, models.Story.Visibility.PRIVATE)
        self.assertEqual(story.in_world_date, "Year 1107 AE")
        self.assertEqual(story.parent, parent_story)
        self.assertEqual(story.order, 3)
        self.assertEqual(story.created_by, self.user)

        self.assertEqual(list(story.characters.all()), [character])
        self.assertEqual(list(story.locations.all()), [location])
        self.assertEqual(list(story.factions.all()), [faction])
        self.assertEqual(list(story.items.all()), [item])

        self.assertIsNotNone(story.slug)
        self.assertTrue(story.slug)

    def test_list_stories(self):
        """GET /api/stories/ should return a list of stories."""
        models.Story.objects.create(title="Story A")
        models.Story.objects.create(title="Story B")

        res = self.client.get(STORIES_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertCountEqual(
            [s["title"] for s in res.data],
            ["Story A", "Story B"],
        )

    def test_retrieve_story_detail(self):
        """GET /api/stories/{id}/ should return story details."""
        story = models.Story.objects.create(
            title="The Archon War",
            summary="The great war of the Archons.",
            body="Long ago...",
            in_world_date="Before the Archon War",
        )
        url = detail_url(story.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "The Archon War")
        self.assertEqual(res.data["summary"], "The great war of the Archons.")
        self.assertEqual(res.data["in_world_date"], "Before the Archon War")

    def test_anonymous_user_cannot_create(self):
        """Anonymous users should not be able to create stories."""
        self.client.force_authenticate(None)

        payload = {"title": "Untitled Lore Entry"}

        res = self.client.post(STORIES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_update_own_story(self):
        """Owner can update their own story."""
        story = models.Story.objects.create(
            title="Old Title",
            created_by=self.user,
        )
        url = detail_url(story.id)

        res = self.client.patch(url, {"title": "New Title"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        story.refresh_from_db()
        self.assertEqual(story.title, "New Title")

    def test_user_cannot_update_others_story(self):
        """Users cannot update stories owned by other users."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        story = models.Story.objects.create(
            title="Secret Story",
            created_by=other_user,
        )
        url = detail_url(story.id)

        res = self.client.patch(url, {"title": "Hacked!"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        story.refresh_from_db()
        self.assertEqual(story.title, "Secret Story")

    def test_user_can_delete_own_story(self):
        """Owner can delete their own story."""
        story = models.Story.objects.create(
            title="Temporary Story",
            created_by=self.user,
        )
        url = detail_url(story.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        exists = models.Story.objects.filter(id=story.id).exists()
        self.assertFalse(exists)

    def test_user_cannot_delete_others_story(self):
        """Users cannot delete stories owned by others."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        story = models.Story.objects.create(
            title="Restricted Story",
            created_by=other_user,
        )
        url = detail_url(story.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        exists = models.Story.objects.filter(id=story.id).exists()
        self.assertTrue(exists)
