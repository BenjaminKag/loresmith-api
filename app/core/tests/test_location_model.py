"""
Tests for Location model.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

import time

from core import models


def create_user(email="test@example.com", password="testpass123", **extra):
    """Helper function to create a new user."""

    return get_user_model().objects.create_user(email, password, **extra)


class LocationModelTests(TestCase):
    """Tests for Location model."""

    def test_string_representation(self):
        """__str__ should return the location name."""

        location = models.Location.objects.create(
            name="Mondstadt",
        )
        self.assertEqual(str(location), "Mondstadt")

    def test_location_with_basic_fields(self):
        """Test location creation with basic fields."""
        location = models.Location.objects.create(
            name="Mondstadt",
            description="City of freedom.",
            location_type="city",
        )

        self.assertEqual(location.name, "Mondstadt")
        self.assertEqual(location.description, "City of freedom.")
        self.assertEqual(location.location_type, "city")

    def test_location_can_have_parent(self):
        """Location can be nested inside another location via parent."""
        continent = models.Location.objects.create(
            name="Teyvat",
            location_type="world",
        )
        city1 = models.Location.objects.create(
            name="Mondstadt",
            location_type="city",
            parent=continent,
        )

        city2 = models.Location.objects.create(
            name="Liyue Harbor",
            location_type="city",
            parent=continent,
        )

        self.assertEqual(city1.parent, continent)
        self.assertEqual(city2.parent, continent)
        self.assertEqual(continent.sub_locations.count(), 2)

    def test_top_level_location_has_no_parent(self):
        """Top-level locations should have no parent."""
        continent = models.Location.objects.create(
            name="Teyvat",
            location_type="world",
        )
        self.assertIsNone(continent.parent)
        self.assertEqual(continent.sub_locations.count(), 0)

    def test_location_created_by_user(self):
        """Test that location has created_by field set correctly."""
        user = create_user()
        location = models.Location.objects.create(
            name="Liyue Harbor",
            created_by=user,
        )

        self.assertEqual(location.created_by, user)
        self.assertIn(location, user.locations.all())

    def test_location_tags_field(self):
        """tags stores a list and defaults to empty list."""
        location = models.Location.objects.create(
            name="Dragonspine",
            tags=["cold", "dangerous"],
        )
        self.assertEqual(location.tags, ["cold", "dangerous"])

        other = models.Location.objects.create(name="Sumeru City")
        self.assertEqual(other.tags, [])

    def test_location_extra_data_field(self):
        """extra_data defaults to {} and can store arbitrary dict."""
        data = {
            "climate": "cold",
            "danger_level": "high",
            "notes": {"blizzard": True},
        }

        location = models.Location.objects.create(
            name="Dragonspine",
            extra_data=data,
        )
        self.assertEqual(location.extra_data, data)

        other = models.Location.objects.create(name="Mondstadt")
        self.assertEqual(other.extra_data, {})

    def test_location_timestamps_set_on_create(self):
        """created_at and updated_at are set when location is created."""
        before = timezone.now()
        location = models.Location.objects.create(name="Mondstadt")
        after = timezone.now()

        self.assertIsNotNone(location.created_at)
        self.assertIsNotNone(location.updated_at)
        self.assertGreaterEqual(location.created_at, before)
        self.assertLessEqual(location.created_at, after)

    def test_location_updated_at_changes_on_save(self):
        """updated_at should change when the location is saved again."""
        location = models.Location.objects.create(name="Mondstadt")
        original_updated = location.updated_at

        time.sleep(0.01)
        location.description = "City of freedom."
        location.save()

        self.assertGreater(location.updated_at, original_updated)

    def test_location_default_ordering_by_name(self):
        """Locations should be ordered by name by default (Meta.ordering)."""
        models.Location.objects.create(name="Sumeru City")
        models.Location.objects.create(name="Mondstadt")
        models.Location.objects.create(name="Liyue Harbor")

        names = list(
            models.Location.objects.values_list("name", flat=True)
        )

        self.assertEqual(
            names,
            ["Liyue Harbor", "Mondstadt", "Sumeru City"],
        )
