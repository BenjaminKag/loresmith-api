"""
Tests for the TraitSet and Trait API.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from core import models


TRAIT_SETS_URL = reverse("trait-set-list")
TRAITS_URL = reverse("trait-list")


def trait_set_detail_url(trait_set_id: int):
    return reverse("trait-set-detail", args=[trait_set_id])


def trait_detail_url(trait_id: int):
    return reverse("trait-detail", args=[trait_id])


def create_user(email, password="testpass123", **extra):
    return get_user_model().objects.create_user(email, password, **extra)


class TraitApiTests(APITestCase):

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    # ----------------------
    # TraitSet tests
    # ----------------------

    def test_list_trait_sets(self):
        models.TraitSet.objects.create(name="Magic Traits", owner=self.user)

        other_user = create_user("other@example.com")
        models.TraitSet.objects.create(name="Secret", owner=other_user)

        res = self.client.get(TRAIT_SETS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [trait_set["name"] for trait_set in res.data],
            ["Physical Traits", "Personality Traits", "Magic Traits"],
        )

    def test_create_trait_set(self):
        payload = {"name": "Magic"}

        res = self.client.post(TRAIT_SETS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        trait_set = models.TraitSet.objects.get(id=res.data["id"])
        self.assertEqual(trait_set.name, "Magic")
        self.assertEqual(trait_set.owner, self.user)

    def test_duplicate_trait_set_for_same_user_fails(self):
        models.TraitSet.objects.create(name="Physical", owner=self.user)

        res = self.client.post(TRAIT_SETS_URL, {"name": "physical"})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_same_trait_set_allowed_for_different_users(self):
        other_user = create_user("other@example.com")
        models.TraitSet.objects.create(name="Physical", owner=other_user)

        res = self.client.post(TRAIT_SETS_URL, {"name": "physical"})

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_user_cannot_access_others_trait_set(self):
        other_user = create_user("other@example.com")
        trait_set = models.TraitSet.objects.create(
            name="Hidden",
            owner=other_user,
        )

        url = trait_set_detail_url(trait_set.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ----------------------
    # Trait tests
    # ----------------------

    def test_create_trait(self):
        trait_set = models.TraitSet.objects.create(
            name="Physical",
            owner=self.user,
        )

        payload = {
            "trait_set": trait_set.id,
            "label": "Age",
        }

        res = self.client.post(TRAITS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        trait = models.Trait.objects.get(id=res.data["id"])
        self.assertEqual(trait.label, "Age")
        self.assertEqual(trait.key, "age")

    def test_cannot_create_trait_in_other_users_set(self):
        other_user = create_user("other@example.com")
        trait_set = models.TraitSet.objects.create(
            name="Secret",
            owner=other_user,
        )

        payload = {
            "trait_set": trait_set.id,
            "label": "Age",
        }

        res = self.client.post(TRAITS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_trait_in_same_set_fails(self):
        trait_set = models.TraitSet.objects.create(
            name="Physical",
            owner=self.user,
        )

        models.Trait.objects.create(
            trait_set=trait_set,
            label="Age",
        )

        payload = {
            "trait_set": trait_set.id,
            "label": "age",
        }

        res = self.client.post(TRAITS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_same_trait_allowed_in_different_sets(self):
        set1 = models.TraitSet.objects.create(
            name="Set1",
            owner=self.user,
        )
        set2 = models.TraitSet.objects.create(
            name="Set2",
            owner=self.user,
        )

        models.Trait.objects.create(trait_set=set1, label="Element")

        payload = {
            "trait_set": set2.id,
            "label": "Element",
        }

        res = self.client.post(TRAITS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_user_cannot_access_others_traits(self):
        other_user = create_user("other@example.com")
        trait_set = models.TraitSet.objects.create(
            name="Hidden",
            owner=other_user,
        )
        trait = models.Trait.objects.create(
            trait_set=trait_set,
            label="Secret",
        )

        url = trait_detail_url(trait.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
