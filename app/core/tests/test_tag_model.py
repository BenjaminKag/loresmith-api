"""
Tests for the Tag model.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from core import models

import uuid


def create_user(email=None, password="testpass123", **extra):
    """Helper function to create a new user."""
    if email is None:
        email = f"test_{uuid.uuid4().hex}@example.com"

    return get_user_model().objects.create_user(email, password, **extra)


def create_tag(user, **params):
    """Helper function to create a tag."""

    defaults = {
        "name": "Mystic",
    }
    defaults.update(params)

    return models.Tag.objects.create(owner=user, **defaults)


class TagModelTests(TestCase):
    """Tests for Tag model."""

    def test_string_representation_returns_name(self):
        """__str__ should return the normalized tag name."""
        user = create_user()
        tag = create_tag(user, name="mystic")

        self.assertEqual(str(tag), "Mystic")

    def test_tag_name_is_normalized_on_save(self):
        """Tag name should be stripped, cleaned and title-cased."""
        user = create_user()
        tag = create_tag(user, name="   mYsTiC   power  ")

        self.assertEqual(tag.name, "Mystic Power")

    def test_duplicate_tag_for_same_user_raises_error(self):
        """Creating the same tag twice for the same user should fail."""
        user = create_user()

        create_tag(user, name="mystic")

        with self.assertRaises(IntegrityError):
            create_tag(user, name="  MYSTIC  ")

    def test_same_tag_name_allowed_for_different_users(self):
        """Different users can have tags with the same name."""
        user1 = create_user(email="user1@example.com")
        user2 = create_user(email="user2@example.com")

        tag1 = create_tag(user1, name="mystic")
        tag2 = create_tag(user2, name="mystic")

        self.assertEqual(tag1.name, "Mystic")
        self.assertEqual(tag2.name, "Mystic")
        self.assertNotEqual(tag1.owner, tag2.owner)

    def test_owner_is_required(self):
        """Tag must have an owner."""
        with self.assertRaises(IntegrityError):
            models.Tag.objects.create(name="Mystic")
