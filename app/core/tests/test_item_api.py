"""
Tests for the Item API.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from core import models


ITEMS_URL = reverse("item-list")


def detail_url(item_id: int):
    """Create and return an item detail URL."""
    return reverse("item-detail", args=[item_id])


def create_user(**params):
    """Helper to create a user."""
    return get_user_model().objects.create_user(**params)


class ItemApiTests(APITestCase):
    """Tests for the Item API."""

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
            name="Test User",
        )
        self.client.force_authenticate(self.user)

    def test_create_item(self):
        """Test creating an item with valid data."""
        payload = {
            "name": "Jade Winged-Spear",
            "description": "A polearm that cuts through the air.",
            "item_type": "weapon",
            "rarity": "5-star",
            "extra_data": {"attack": 674},
        }

        res = self.client.post(ITEMS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        item = models.Item.objects.get(id=res.data["id"])
        self.assertEqual(item.name, payload["name"])
        self.assertEqual(item.description, payload["description"])
        self.assertEqual(item.item_type, payload["item_type"])
        self.assertEqual(item.rarity, payload["rarity"])
        self.assertEqual(item.extra_data, payload["extra_data"])
        self.assertEqual(item.created_by, self.user)

    def test_list_items(self):
        """GET /api/items/ should return a list of items."""
        models.Item.objects.create(name="Sword")
        models.Item.objects.create(name="Bow")

        res = self.client.get(ITEMS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertCountEqual(
            [i["name"] for i in res.data],
            ["Sword", "Bow"],
        )

    def test_retrieve_item_detail(self):
        """GET /api/items/{id}/ should return item details."""
        item = models.Item.objects.create(
            name="Favonius Lance",
            description="A polearm of the Knights of Favonius.",
            item_type="weapon",
            rarity="4-star",
        )
        url = detail_url(item.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Favonius Lance")
        self.assertEqual(
            res.data["description"],
            "A polearm of the Knights of Favonius.",
        )

    def test_anonymous_user_cannot_create(self):
        """Anonymous users should not be able to create items."""
        self.client.force_authenticate(None)

        payload = {"name": "Nameless Relic"}

        res = self.client.post(ITEMS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_update_own_item(self):
        """Owner can update their own item."""
        item = models.Item.objects.create(
            name="Old Name",
            created_by=self.user,
        )
        url = detail_url(item.id)

        res = self.client.patch(url, {"name": "New Name"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        item.refresh_from_db()
        self.assertEqual(item.name, "New Name")

    def test_user_cannot_update_others_item(self):
        """Users cannot update items owned by other users."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        item = models.Item.objects.create(
            name="Secret Artifact",
            created_by=other_user,
        )
        url = detail_url(item.id)

        res = self.client.patch(url, {"name": "Hacked!"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        item.refresh_from_db()
        self.assertEqual(item.name, "Secret Artifact")

    def test_user_can_delete_own_item(self):
        """Owner can delete their own item."""
        item = models.Item.objects.create(
            name="Temporary Item",
            created_by=self.user,
        )
        url = detail_url(item.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        exists = models.Item.objects.filter(id=item.id).exists()
        self.assertFalse(exists)

    def test_user_cannot_delete_others_item(self):
        """Users cannot delete items owned by others."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        item = models.Item.objects.create(
            name="Restricted Item",
            created_by=other_user,
        )
        url = detail_url(item.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        exists = models.Item.objects.filter(id=item.id).exists()
        self.assertTrue(exists)
