"""
Tests for the Faction model.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

import time

from core import models


def create_user(email="test@example.com", password="testpass123", **extra):
    """Helper function to create a new user."""

    return get_user_model().objects.create_user(email, password, **extra)


class FactionModelTests(TestCase):
    """Tests for Faction model."""

    def test_string_representation(self):
        """__str__ should return the faction name."""
        faction = models.Faction.objects.create(
            name="Knights of Favonius",
        )
        self.assertEqual(str(faction), "Knights of Favonius")

    def test_faction_with_basic_fields(self):
        """Test faction creation with basic fields."""
        faction = models.Faction.objects.create(
            name="Knights of Favonius",
            description="Protectors of Mondstadt.",
            faction_type="guild",
        )

        self.assertEqual(faction.name, "Knights of Favonius")
        self.assertEqual(faction.description, "Protectors of Mondstadt.")
        self.assertEqual(faction.faction_type, "guild")

    def test_faction_with_location(self):
        """Test faction creation with associated location."""
        city = models.Location.objects.create(
            name="Mondstadt",
            location_type="city",
        )

        faction = models.Faction.objects.create(
            name="Knights of Favonius",
            location=city,
        )

        self.assertEqual(faction.location, city)
        self.assertIn(faction, city.factions.all())

    def test_faction_without_location_is_allowed(self):
        """Faction can be created without a location."""
        faction = models.Faction.objects.create(
            name="Hexenzirkel",
        )
        self.assertIsNone(faction.location)

    def test_faction_created_by_user(self):
        """Test that faction has created_by field set correctly."""
        user = create_user()
        faction = models.Faction.objects.create(
            name="Adepti",
            created_by=user,
        )

        self.assertEqual(faction.created_by, user)
        self.assertIn(faction, user.factions.all())

    def test_faction_tags_field(self):
        """tags stores a list and defaults to empty list."""
        faction = models.Faction.objects.create(
            name="Harbingers",
            tags=["Delusions", "Fatui"],
        )
        self.assertEqual(faction.tags, ["Delusions", "Fatui"])

        other = models.Faction.objects.create(name="Liyue Qixing")
        self.assertEqual(other.tags, [])

    def test_faction_extra_data_field(self):
        """extra_data defaults to {} and can store arbitrary dict."""
        data = {
            "alignment": "neutral",
            "influence_level": "high",
            "notes": {"archon_related": True},
        }

        faction = models.Faction.objects.create(
            name="Liyue Qixing",
            extra_data=data,
        )
        self.assertEqual(faction.extra_data, data)

        other = models.Faction.objects.create(name="Knights of Favonius")
        self.assertEqual(other.extra_data, {})

    def test_faction_timestamps_set_on_create(self):
        """created_at and updated_at are set when faction is created."""
        before = timezone.now()
        faction = models.Faction.objects.create(name="Knights of Favonius")
        after = timezone.now()

        self.assertIsNotNone(faction.created_at)
        self.assertIsNotNone(faction.updated_at)
        self.assertGreaterEqual(faction.created_at, before)
        self.assertLessEqual(faction.created_at, after)

    def test_faction_updated_at_changes_on_save(self):
        """updated_at should change when the faction is saved again."""
        faction = models.Faction.objects.create(name="Knights of Favonius")
        original_updated = faction.updated_at

        time.sleep(0.01)
        faction.description = "Order that protects Mondstadt."
        faction.save()

        self.assertGreater(faction.updated_at, original_updated)

    def test_faction_default_ordering_by_name(self):
        """Factions should be ordered by name by default (Meta.ordering)."""
        models.Faction.objects.create(name="Liyue Qixing")
        models.Faction.objects.create(name="Fatui")
        models.Faction.objects.create(name="Knights of Favonius")

        names = list(
            models.Faction.objects.values_list("name", flat=True)
        )

        self.assertEqual(
            names,
            ["Fatui", "Knights of Favonius", "Liyue Qixing"],
        )
