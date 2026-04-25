"""
Tests for Character model.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

import time
import uuid

from core import models


def create_user(email=None, password="testpass123", **extra):
    """Helper function to create a new user."""
    if email is None:
        email = f"test_{uuid.uuid4().hex}@example.com"

    return get_user_model().objects.create_user(email, password, **extra)


def create_character(**params):
    if "owner" not in params:
        params["owner"] = create_user()

    defaults = {
        "name": "Default Character",
    }
    defaults.update(params)

    return models.Character.objects.create(**defaults)


class CharacterModelTests(TestCase):
    """Tests for Character model."""

    def test_string_representation(self):
        """__str__ should return the character name."""
        character = create_character(name="Xiao")
        self.assertEqual(str(character), "Xiao")

    def test_character_with_basic_identity_fields(self):
        """Test character creation with basic identity fields."""
        character = create_character(
            name="Xiao",
            description="A vigilant yaksha.",
        )

        self.assertEqual(character.name, "Xiao")
        self.assertEqual(character.description, "A vigilant yaksha.")

    def test_character_relationships_field(self):
        """Test the relationships field."""
        mentor = create_character(name="Rheindottir")
        sibling1 = create_character(name="Klee")
        sibling2 = create_character(name="Durin")

        data = {
            "mentor": [mentor.id],
            "siblings": [sibling1.id, sibling2.id]
        }

        character = create_character(
            name="Albedo",
            relationships=data,
        )

        self.assertEqual(character.relationships, data)

    def test_character_relationships_default_empty(self):
        """Test that relationships field defaults to empty dict."""
        character = create_character(name="Xiao")
        self.assertEqual(character.relationships, {})

    def test_character_with_location_affiliation_items(self):
        """Test character with location, affiliations, and equipment."""
        user = create_user()
        location = models.Location.objects.create(
            name="Liyue Harbor",
            owner=user
        )
        affiliation = models.Faction.objects.create(
            name="Adepti",
            owner=user
        )
        item = models.Item.objects.create(
            name="Vortex Vanquisher",
            owner=user
        )

        character = create_character(
            name="Zhongli",
            location=location,
            owner=user
        )
        character.affiliations.add(affiliation)
        character.equipment.add(item)

        # Location
        self.assertEqual(character.location, location)
        self.assertIn(character, location.characters.all())

        # Affiliations
        self.assertIn(affiliation, character.affiliations.all())
        self.assertIn(character, affiliation.members.all())

        # Equipment
        self.assertIn(item, character.equipment.all())
        self.assertIn(character, item.holders.all())

    def test_character_with_multiple_affiliations(self):
        """Test character with multiple affiliations."""
        user = create_user()
        faction1 = models.Faction.objects.create(
            name="Hexenzirkel",
            owner=user
        )
        faction2 = models.Faction.objects.create(
            name="Sinners",
            owner=user
        )

        character = models.Character.objects.create(
            name="Rheindottir",
            owner=user,
        )
        character.affiliations.add(faction1, faction2)

        self.assertIn(faction1, character.affiliations.all())
        self.assertIn(faction2, character.affiliations.all())
        self.assertIn(character, faction1.members.all())
        self.assertIn(character, faction2.members.all())

    def test_character_with_multiple_equipment(self):
        """Test character with multiple equipment items."""
        user = create_user()
        item1 = models.Item.objects.create(
            name="Anemo Vision",
            owner=user
        )
        item2 = models.Item.objects.create(
            name="Jade Winged Spear",
            owner=user
        )

        character = models.Character.objects.create(
            name="Xiao",
            owner=user,
        )
        character.equipment.add(item1, item2)

        self.assertIn(item1, character.equipment.all())
        self.assertIn(item2, character.equipment.all())
        self.assertIn(character, item1.holders.all())
        self.assertIn(character, item2.holders.all())

    def test_character_owner_user(self):
        """Test that character has owner field set correctly."""
        user = create_user()
        character = create_character(
            name="Diluc",
            owner=user
        )

        self.assertEqual(character.owner, user)
        self.assertIn(character, user.owned_characters.all())

    def test_character_extra_data_field(self):
        """Character extra_data defaults to {} and can store arbitrary dict."""
        data = {
            "combat_role": "DPS",
            "power_level": 9001,
            "notes": {"mask": True, "adeptus": True},
        }

        character = create_character(
            name="Xiao",
            extra_data=data,
        )
        self.assertEqual(character.extra_data, data)

        other = create_character(name="Albedo")
        self.assertEqual(other.extra_data, {})

    def test_character_timestamps_set_on_create(self):
        """created_at and updated_at are set when character is created."""
        before = timezone.now()
        character = create_character(name="Xiao")
        after = timezone.now()

        self.assertIsNotNone(character.created_at)
        self.assertIsNotNone(character.updated_at)
        self.assertGreaterEqual(character.created_at, before)
        self.assertLessEqual(character.created_at, after)

    def test_character_updated_at_changes_on_save(self):
        """updated_at should change when the character is saved again."""
        character = create_character(name="Xiao")
        original_updated = character.updated_at

        time.sleep(0.01)
        character.description = "A vigilant yaksha."
        character.save()

        self.assertGreater(character.updated_at, original_updated)
