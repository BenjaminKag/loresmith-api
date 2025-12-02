"""
Tests for Item model.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

import time

from core import models


def create_user(email="test@example.com", password="testpass123", **extra):
    """Helper function to create a new user."""

    return get_user_model().objects.create_user(email, password, **extra)


class ItemModelTests(TestCase):
    """Tests for Item model."""

    def test_string_representation(self):
        """__str__ should return the item name."""
        item = models.Item.objects.create(
            name="Jade Winged Spear",
        )
        self.assertEqual(str(item), "Jade Winged Spear")

    def test_item_with_basic_fields(self):
        """Test item creation with basic fields."""
        item = models.Item.objects.create(
            name="Jade Winged Spear",
            description="A spear that cuts through the air.",
            item_type="Polearm",
            rarity="5 Stars",
        )

        self.assertEqual(item.name, "Jade Winged Spear")
        self.assertEqual(
            item.description,
            "A spear that cuts through the air."
        )
        self.assertEqual(item.item_type, "Polearm")
        self.assertEqual(item.rarity, "5 Stars")

    def test_item_held_by_mutliple_characters(self):
        """Test that an item can be held by multiple characters."""
        user = create_user()
        char1 = models.Character.objects.create(
            name="Xiao",
            created_by=user,
        )
        char2 = models.Character.objects.create(
            name="Arlecchino",
            created_by=user,
        )

        item = models.Item.objects.create(
            name="Jade Winged Spear",
            created_by=user,
        )

        char1.equipment.add(item)
        char2.equipment.add(item)

        self.assertIn(char1, item.holders.all())
        self.assertIn(char2, item.holders.all())
        self.assertIn(item, char1.equipment.all())
        self.assertIn(item, char2.equipment.all())

    def test_item_created_by_user(self):
        """Test that item has created_by field set correctly."""
        user = create_user()
        item = models.Item.objects.create(
            name="Anemo Vision",
            created_by=user,
        )

        self.assertEqual(item.created_by, user)
        self.assertIn(item, user.items.all())

    def test_item_tags_field(self):
        """tags stores a list and defaults to empty list."""
        item = models.Item.objects.create(
            name="Anemo Vision",
            tags=["anemo", "vision"],
        )
        self.assertEqual(item.tags, ["anemo", "vision"])

        other = models.Item.objects.create(name="Geo Vision")
        self.assertEqual(other.tags, [])

    def test_item_extra_data_field(self):
        """extra_data defaults to {} and can store arbitrary dict."""
        data = {
            "attack": 674,
            "crit_rate": 22.1,
            "notes": {"polearm": True},
        }

        item = models.Item.objects.create(
            name="Jade Winged Spear",
            extra_data=data,
        )
        self.assertEqual(item.extra_data, data)

        other = models.Item.objects.create(name="Favonius Lance")
        self.assertEqual(other.extra_data, {})

    def test_item_timestamps_set_on_create(self):
        """created_at and updated_at are set when item is created."""
        before = timezone.now()
        item = models.Item.objects.create(name="Jade Winged Spear")
        after = timezone.now()

        self.assertIsNotNone(item.created_at)
        self.assertIsNotNone(item.updated_at)
        self.assertGreaterEqual(item.created_at, before)
        self.assertLessEqual(item.created_at, after)

    def test_item_updated_at_changes_on_save(self):
        """updated_at should change when the item is saved again."""
        item = models.Item.objects.create(name="Jade Winged Spear")
        original_updated = item.updated_at

        time.sleep(0.01)
        item.description = "A spear used by the vigilant yaksha."
        item.save()

        self.assertGreater(item.updated_at, original_updated)

    def test_item_default_ordering_by_name(self):
        """Items should be ordered by name by default (Meta.ordering)."""
        models.Item.objects.create(name="Iron Sting")
        models.Item.objects.create(name="Prototype Starglitter")
        models.Item.objects.create(name="Dull Blade")

        names = list(
            models.Item.objects.values_list("name", flat=True)
        )

        self.assertEqual(
            names,
            ["Dull Blade", "Iron Sting", "Prototype Starglitter"],
        )
