"""
Tests for Character model.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

import time

from core import models


def create_user(email="test@example.com", password="testpass123", **extra):
    """Helper function to create a new user."""

    return get_user_model().objects.create_user(email, password, **extra)


class CharacterModelTests(TestCase):
    """Tests for Character model."""

    def test_string_representation(self):
        """__str__ should return the character name."""
        character = models.Character.objects.create(
            name="Xiao",
        )
        self.assertEqual(str(character), "Xiao")

    def test_character_with_basic_identity_fields(self):
        """Test character creation with basic identity fields."""
        character = models.Character.objects.create(
            name="Xiao",
            description="A vigilant yaksha.",
            age=2000,
            age_description="Over 2000 years old",
            species="Adeptus",
            gender="Male"
        )

        self.assertEqual(character.name, "Xiao")
        self.assertEqual(character.description, "A vigilant yaksha.")
        self.assertEqual(character.age, 2000)
        self.assertEqual(character.age_description, "Over 2000 years old")
        self.assertEqual(character.species, "Adeptus")
        self.assertEqual(character.gender, "Male")

    def test_character_relationships_field(self):
        """Test the relationships field."""
        mentor = models.Character.objects.create(name="Rheindottir")
        sibling1 = models.Character.objects.create(name="Klee")
        sibling2 = models.Character.objects.create(name="Durin")

        data = {
            "mentor": [mentor.id],
            "siblings": [sibling1.id, sibling2.id]
        }

        character = models.Character.objects.create(
            name="Albedo",
            relationships=data,
        )

        self.assertEqual(character.relationships, data)

    def test_character_relationships_default_empty(self):
        """Test that relationships field defaults to empty dict."""
        character = models.Character.objects.create(name="Xiao")
        self.assertEqual(character.relationships, {})

    def test_character_with_location_affiliation_items(self):
        """Test character with location, affiliations, and equipment."""
        user = create_user()
        location = models.Location.objects.create(
            name="Liyue Harbor",
            created_by=user
        )
        affiliation = models.Faction.objects.create(
            name="Adepti",
            created_by=user
        )
        item = models.Item.objects.create(
            name="Vortex Vanquisher",
            created_by=user
        )

        character = models.Character.objects.create(
            name="Zhongli",
            location=location,
            created_by=user,
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
            created_by=user
        )
        faction2 = models.Faction.objects.create(
            name="Sinners",
            created_by=user
        )

        character = models.Character.objects.create(
            name="Rheindottir",
            created_by=user,
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
            created_by=user
        )
        item2 = models.Item.objects.create(
            name="Jade Winged Spear",
            created_by=user
        )

        character = models.Character.objects.create(
            name="Xiao",
            created_by=user,
        )
        character.equipment.add(item1, item2)

        self.assertIn(item1, character.equipment.all())
        self.assertIn(item2, character.equipment.all())
        self.assertIn(character, item1.holders.all())
        self.assertIn(character, item2.holders.all())

    def test_character_created_by_user(self):
        """Test that character has created_by field set correctly."""
        user = create_user()
        character = models.Character.objects.create(
            name="Diluc",
            created_by=user,
        )

        self.assertEqual(character.created_by, user)
        self.assertIn(character, user.characters.all())

    def test_character_tags_field(self):
        """Character tags field stores a list and defaults to empty list."""
        character = models.Character.objects.create(
            name="Xiao",
            tags=["anemo", "yaksha"],
        )
        self.assertEqual(character.tags, ["anemo", "yaksha"])

        other = models.Character.objects.create(name="Albedo")
        self.assertEqual(other.tags, [])

    def test_character_extra_data_field(self):
        """Character extra_data defaults to {} and can store arbitrary dict."""
        data = {
            "combat_role": "DPS",
            "power_level": 9001,
            "notes": {"mask": True, "adeptus": True},
        }

        character = models.Character.objects.create(
            name="Xiao",
            extra_data=data,
        )
        self.assertEqual(character.extra_data, data)

        other = models.Character.objects.create(name="Albedo")
        self.assertEqual(other.extra_data, {})

    def test_character_timestamps_set_on_create(self):
        """created_at and updated_at are set when character is created."""
        before = timezone.now()
        character = models.Character.objects.create(name="Xiao")
        after = timezone.now()

        self.assertIsNotNone(character.created_at)
        self.assertIsNotNone(character.updated_at)
        self.assertGreaterEqual(character.created_at, before)
        self.assertLessEqual(character.created_at, after)

    def test_character_updated_at_changes_on_save(self):
        """updated_at should change when the character is saved again."""
        character = models.Character.objects.create(name="Xiao")
        original_updated = character.updated_at

        time.sleep(0.01)
        character.description = "A vigilant yaksha."
        character.save()

        self.assertGreater(character.updated_at, original_updated)
