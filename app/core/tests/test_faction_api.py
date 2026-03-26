"""
Tests for the Faction API.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from core import models


FACTIONS_URL = reverse("faction-list")


def detail_url(faction_id: int):
    """Create and return a faction detail URL."""
    return reverse("faction-detail", args=[faction_id])


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class FactionApiTests(APITestCase):
    """Tests for the Faction API."""

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
            name="Test User",
        )
        self.client.force_authenticate(self.user)

    def test_create_faction(self):
        """Test creating a faction with valid data."""
        payload = {
            "name": "Knights of Favonius",
            "description": "Protectors of Mondstadt.",
            "faction_type": "knightly order",
        }

        res = self.client.post(FACTIONS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        faction = models.Faction.objects.get(id=res.data["id"])
        self.assertEqual(faction.name, payload["name"])
        self.assertEqual(faction.description, payload["description"])
        self.assertEqual(faction.faction_type, payload["faction_type"])
        self.assertEqual(faction.owner, self.user)

    def test_create_faction_with_location(self):
        """Test creating a faction that is linked to a location."""
        location = models.Location.objects.create(
            name="Mondstadt",
            description="City of freedom.",
            location_type="city",
        )
        payload = {
            "name": "Church of Favonius",
            "description": "Religious institution in Mondstadt.",
            "faction_type": "church",
            "location": location.id,
        }

        res = self.client.post(FACTIONS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        faction = models.Faction.objects.get(id=res.data["id"])
        self.assertEqual(faction.location, location)

    def test_list_factions(self):
        """GET /api/factions/ should return a list of factions."""
        models.Faction.objects.create(name="Adepti", owner=self.user)
        models.Faction.objects.create(name="Fatui", owner=self.user)

        res = self.client.get(FACTIONS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertCountEqual(
            [f["name"] for f in res.data],
            ["Adepti", "Fatui"]
        )

    def test_retrieve_faction_detail(self):
        """GET /api/factions/{id}/ should return faction details."""
        faction = models.Faction.objects.create(
            name="Adepti",
            description="Protectors of Liyue.",
            faction_type="Illuminated beasts and gods",
            owner=self.user,
        )
        url = detail_url(faction.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Adepti")
        self.assertEqual(res.data["description"], "Protectors of Liyue.")

    def test_anonymous_user_cannot_create(self):
        """Anonymous users should not be able to create factions."""
        self.client.force_authenticate(None)

        payload = {"name": "Fatui"}

        res = self.client.post(FACTIONS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_update_own_faction(self):
        """Owner can update their own faction."""
        faction = models.Faction.objects.create(
            name="Old Name",
            owner=self.user,
        )
        url = detail_url(faction.id)

        res = self.client.patch(url, {"name": "New Name"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        faction.refresh_from_db()
        self.assertEqual(faction.name, "New Name")

    def test_user_cannot_update_others_faction(self):
        """Users cannot update factions owned by other users."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        faction = models.Faction.objects.create(
            name="Secret Society",
            owner=other_user,
        )
        url = detail_url(faction.id)

        res = self.client.patch(url, {"name": "Hacked!"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        faction.refresh_from_db()
        self.assertEqual(faction.name, "Secret Society")

    def test_user_can_delete_own_faction(self):
        """Owner can delete their own faction."""
        faction = models.Faction.objects.create(
            name="Temporary Faction",
            owner=self.user,
        )
        url = detail_url(faction.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        exists = models.Faction.objects.filter(id=faction.id).exists()
        self.assertFalse(exists)

    def test_user_cannot_delete_others_faction(self):
        """Users cannot delete factions owned by others."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        faction = models.Faction.objects.create(
            name="Restricted Faction",
            owner=other_user,
        )
        url = detail_url(faction.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        exists = models.Faction.objects.filter(id=faction.id).exists()
        self.assertTrue(exists)

    def test_user_can_view_others_faction_in_public_story(self):
        """Authenticated users can retrieve factions
          that appear in public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        faction = models.Faction.objects.create(
            name="Adepti",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        story.factions.add(faction)

        url = detail_url(faction.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Adepti")

    def test_anonymous_user_can_view_faction_in_public_story(self):
        """Anonymous users can retrieve factions
          that appear in public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        faction = models.Faction.objects.create(
            name="Fatui",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        story.factions.add(faction)

        self.client.force_authenticate(None)
        url = detail_url(faction.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Fatui")

    def test_anonymous_user_cannot_view_faction_only_in_private_stories(self):
        """Anonymous users cannot retrieve factions
          that appear only in private stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        faction = models.Faction.objects.create(
            name="Hidden Faction",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Private Story",
            visibility=models.Story.Visibility.PRIVATE,
            owner=other_user,
        )
        story.factions.add(faction)

        self.client.force_authenticate(None)
        url = detail_url(faction.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_view_own_faction_without_public_story(self):
        """Owners can retrieve their own factions
          even without public story."""
        faction = models.Faction.objects.create(
            name="Private Faction",
            owner=self.user,
        )

        url = detail_url(faction.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Private Faction")

    def test_list_includes_own_and_public_story_factions_only(self):
        """Authenticated users see their own factions
          and factions from public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )

        models.Faction.objects.create(
            name="My Faction",
            owner=self.user,
        )
        public_faction = models.Faction.objects.create(
            name="Public Faction",
            owner=other_user,
        )
        private_faction = models.Faction.objects.create(
            name="Private Faction",
            owner=other_user,
        )

        public_story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        private_story = models.Story.objects.create(
            title="Private Story",
            visibility=models.Story.Visibility.PRIVATE,
            owner=other_user,
        )

        public_story.factions.add(public_faction)
        private_story.factions.add(private_faction)

        res = self.client.get(FACTIONS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [f["name"] for f in res.data],
            ["My Faction", "Public Faction"],
        )
