"""
Tests for the Character API.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from core import models


CHARACTERS_URL = reverse("character-list")


def detail_url(character_id: int):
    """Create and return a character detail URL."""
    return reverse("character-detail", args=[character_id])


def create_user(**params):
    """Helper to create a user."""
    return get_user_model().objects.create_user(**params)


class CharacterApiTests(APITestCase):
    """Tests for the Character API."""

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
            name="Test User",
        )
        self.client.force_authenticate(self.user)

    def test_create_character_with_relations(self):
        """
        Test creating a character with location, affiliations and equipment.
        """
        location = models.Location.objects.create(
            name="Liyue Harbor",
            description="A bustling harbor city.",
            location_type="city",
            owner=self.user,
        )
        faction1 = models.Faction.objects.create(
            name="Adepti",
            description="Protectors of Liyue.",
            faction_type="Illuminated beasts and gods",
            owner=self.user,
        )
        faction2 = models.Faction.objects.create(
            name="Knights of Favonius",
            description="Protectors of Mondstadt.",
            faction_type="knightly order",
            owner=self.user,
        )
        item1 = models.Item.objects.create(
            name="Jade Winged-Spear",
            item_type="weapon",
            rarity="5-star",
            owner=self.user,
        )
        item2 = models.Item.objects.create(
            name="Favonius Lance",
            item_type="weapon",
            rarity="4-star",
            owner=self.user,
        )

        payload = {
            "name": "Xiao",
            "description": "A vigilant yaksha.",
            "age": 2000,
            "age_description": "Over 2000 years old",
            "species": "Adeptus",
            "gender": "male",
            "location": location.id,
            "affiliations": [faction1.id, faction2.id],
            "equipment": [item1.id, item2.id],
            "relationships": {
                "allies": ["Venti"],
                "fellow adepti": ["Cloud Retainer"]
            },
            "extra_data": {"vision": "Anemo", "weapon": "Polearm"},
        }

        res = self.client.post(CHARACTERS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        character = models.Character.objects.get(id=res.data["id"])

        self.assertEqual(character.name, "Xiao")
        self.assertEqual(character.description, "A vigilant yaksha.")
        self.assertEqual(character.age, 2000)
        self.assertEqual(character.age_description, "Over 2000 years old")
        self.assertEqual(character.species, "Adeptus")
        self.assertEqual(character.gender, "male")
        self.assertEqual(character.location, location)
        self.assertEqual(character.owner, self.user)

        self.assertCountEqual(
            list(character.affiliations.all()),
            [faction1, faction2],
        )
        self.assertCountEqual(
            list(character.equipment.all()),
            [item1, item2],
        )
        self.assertEqual(
            character.relationships,
            {"allies": ["Venti"], "fellow adepti": ["Cloud Retainer"]},
        )
        self.assertEqual(
            character.extra_data,
            {"vision": "Anemo", "weapon": "Polearm"},
        )

    def test_list_characters(self):
        """GET /api/characters/ should return a list of characters."""
        models.Character.objects.create(name="Xiao", owner=self.user)
        models.Character.objects.create(name="Venti", owner=self.user)

        res = self.client.get(CHARACTERS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertCountEqual(
            [c["name"] for c in res.data],
            ["Xiao", "Venti"],
        )

    def test_retrieve_character_detail(self):
        """GET /api/characters/{id}/ should return character details."""
        character = models.Character.objects.create(
            name="Xiao",
            description="A vigilant yaksha.",
            species="Adeptus",
            gender="male",
            owner=self.user,
        )
        url = detail_url(character.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Xiao")
        self.assertEqual(res.data["description"], "A vigilant yaksha.")

    def test_anonymous_user_cannot_create(self):
        """Anonymous users should not be able to create characters."""
        self.client.force_authenticate(None)

        payload = {"name": "Mysterious Stranger"}

        res = self.client.post(CHARACTERS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_update_own_character(self):
        """Owner can update their own character."""
        character = models.Character.objects.create(
            name="Old Name",
            owner=self.user,
        )
        url = detail_url(character.id)

        res = self.client.patch(url, {"name": "New Name"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        character.refresh_from_db()
        self.assertEqual(character.name, "New Name")

    def test_user_cannot_update_others_character(self):
        """Users cannot update characters owned by other users."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        character = models.Character.objects.create(
            name="Secret Character",
            owner=other_user,
        )
        url = detail_url(character.id)

        res = self.client.patch(url, {"name": "Hacked!"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        character.refresh_from_db()
        self.assertEqual(character.name, "Secret Character")

    def test_user_can_delete_own_character(self):
        """Owner can delete their own character."""
        character = models.Character.objects.create(
            name="Temporary Character",
            owner=self.user,
        )
        url = detail_url(character.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        exists = models.Character.objects.filter(id=character.id).exists()
        self.assertFalse(exists)

    def test_user_cannot_delete_others_character(self):
        """Users cannot delete characters owned by others."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        character = models.Character.objects.create(
            name="Restricted Character",
            owner=other_user,
        )
        url = detail_url(character.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        exists = models.Character.objects.filter(id=character.id).exists()
        self.assertTrue(exists)

    def test_user_can_view_others_character_in_public_story(self):
        """Authenticated users can retrieve characters
            that appear in public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        character = models.Character.objects.create(
            name="Xiao",
            description="A vigilant yaksha.",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        story.characters.add(character)

        url = detail_url(character.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Xiao")

    def test_anonymous_user_can_view_character_in_public_story(self):
        """Anonymous users can retrieve characters
          that appear in public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        character = models.Character.objects.create(
            name="Venti",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        story.characters.add(character)

        self.client.force_authenticate(None)
        url = detail_url(character.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Venti")

    def test_anonymous_user_cant_view_character_only_in_private_stories(self):
        """Anonymous users cannot retrieve characters that
          appear only in private stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        character = models.Character.objects.create(
            name="Hidden Character",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Private Story",
            visibility=models.Story.Visibility.PRIVATE,
            owner=other_user,
        )
        story.characters.add(character)

        self.client.force_authenticate(None)
        url = detail_url(character.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_view_own_character_without_public_story(self):
        """Owners can retrieve their own characters
          even without any public story."""
        character = models.Character.objects.create(
            name="Private Character",
            owner=self.user,
        )

        url = detail_url(character.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Private Character")

    def test_list_includes_own_and_public_story_characters_only(self):
        """Authenticated users see their own characters
          and characters from public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )

        _ = models.Character.objects.create(
            name="My Character",
            owner=self.user,
        )
        public_character = models.Character.objects.create(
            name="Public Character",
            owner=other_user,
        )
        private_character = models.Character.objects.create(
            name="Private Character",
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

        public_story.characters.add(public_character)
        private_story.characters.add(private_character)

        res = self.client.get(CHARACTERS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [c["name"] for c in res.data],
            ["My Character", "Public Character"],
        )
