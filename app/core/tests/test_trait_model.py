"""
Tests for Trait and TraitSet models.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from core import models

import uuid


def create_user(email=None, password="testpass123", **extra):
    if email is None:
        email = f"test_{uuid.uuid4().hex}@example.com"

    return get_user_model().objects.create_user(email, password, **extra)


def create_trait_set(user, **params):
    defaults = {
        "name": "Physical",
    }
    defaults.update(params)

    return models.TraitSet.objects.create(owner=user, **defaults)


def create_trait(trait_set, **params):
    defaults = {
        "label": "Age",
    }
    defaults.update(params)

    return models.Trait.objects.create(trait_set=trait_set, **defaults)


class TraitModelTests(TestCase):

    def test_trait_set_string_representation(self):
        user = create_user()
        trait_set = create_trait_set(user, name="Physical")

        self.assertEqual(str(trait_set), "Physical")

    def test_trait_string_representation(self):
        user = create_user()
        trait_set = create_trait_set(user)
        trait = create_trait(trait_set, label="Age")

        self.assertEqual(str(trait), "Physical: Age")

    def test_trait_set_slug_is_generated(self):
        user = create_user()
        trait_set = create_trait_set(user, name="Magic Traits")

        self.assertEqual(trait_set.slug, "magic_traits")

    def test_trait_key_is_generated(self):
        user = create_user()
        trait_set = create_trait_set(user)
        trait = create_trait(trait_set, label="Eye Color")

        self.assertEqual(trait.key, "eye_color")

    def test_duplicate_trait_set_slug_for_same_user_fails(self):
        user = create_user()

        create_trait_set(user, name="Physical")

        with self.assertRaises(IntegrityError):
            create_trait_set(user, name="physical")

    def test_same_trait_set_name_allowed_for_different_users(self):
        user1 = create_user()
        user2 = create_user()

        create_trait_set(user1, name="Physical")
        trait_set2 = create_trait_set(user2, name="Physical")

        self.assertEqual(trait_set2.slug, "physical")

    def test_duplicate_trait_in_same_set_fails(self):
        user = create_user()
        trait_set = create_trait_set(user)

        create_trait(trait_set, label="Age")

        with self.assertRaises(IntegrityError):
            create_trait(trait_set, label="age")

    def test_same_trait_allowed_in_different_sets(self):
        user = create_user()
        set1 = create_trait_set(user, name="Set1")
        set2 = create_trait_set(user, name="Set2")

        create_trait(set1, label="Element")
        trait2 = create_trait(set2, label="Element")

        self.assertEqual(trait2.key, "element")

    def test_trait_requires_trait_set(self):
        with self.assertRaises(IntegrityError):
            models.Trait.objects.create(label="Age")
