"""
Tests for the Location API.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from core import models


LOCATIONS_URL = reverse("location-list")


def detail_url(location_id):
    """Create and return a location detail URL."""
    return reverse("location-detail", args=[location_id])


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class LocationApiTests(APITestCase):
    """Tests for the Location API."""

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
            name="Test User",
        )
        self.client.force_authenticate(self.user)

    def test_create_location(self):
        """Test creating a location with basic valid data."""
        payload = {
            "name": "Dragonspine",
            "description": "A frozen mountain.",
            "location_type": "region",
        }

        res = self.client.post(LOCATIONS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "Dragonspine")

        location = models.Location.objects.get(id=res.data["id"])
        self.assertEqual(location.description, "A frozen mountain.")
        self.assertEqual(location.location_type, "region")
        self.assertEqual(location.created_by, self.user)

    def test_list_locations(self):
        """GET /api/locations/ should return a list of locations."""
        models.Location.objects.create(name="Mondstadt")
        models.Location.objects.create(name="Liyue Harbor")

        res = self.client.get(LOCATIONS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(
            sorted([loc["name"] for loc in res.data]),
            ["Liyue Harbor", "Mondstadt"]
        )

    def test_retrieve_location_detail(self):
        """GET /api/locations/{id}/ should return location details."""
        location = models.Location.objects.create(
            name="Dragonspine",
            description="A frozen mountain.",
            location_type="region",
        )
        url = detail_url(location.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Dragonspine")
        self.assertEqual(res.data["description"], "A frozen mountain.")

    def test_anonymous_user_cannot_create(self):
        """Anonymous users should not be able to create locations."""
        self.client.force_authenticate(None)  # logout

        payload = {"name": "Snezhnaya"}

        res = self.client.post(LOCATIONS_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_update_own_location(self):
        """PATCH should allow the owner to update their location."""
        location = models.Location.objects.create(
            name="Old Name",
            created_by=self.user,
        )
        url = detail_url(location.id)

        res = self.client.patch(url, {"name": "New Name"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        location.refresh_from_db()
        self.assertEqual(location.name, "New Name")

    def test_user_cannot_update_others_location(self):
        """Users should not be able to update locations they don't own."""
        other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="testpass123"
        )
        location = models.Location.objects.create(
            name="Secret Base",
            created_by=other_user,
        )
        url = detail_url(location.id)

        res = self.client.patch(url, {"name": "Hacked!"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        location.refresh_from_db()
        self.assertEqual(location.name, "Secret Base")

    def test_user_can_delete_own_location(self):
        """DELETE should allow the owner to delete their location."""
        location = models.Location.objects.create(
            name="Temporary Location",
            created_by=self.user,
        )
        url = detail_url(location.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        exists = models.Location.objects.filter(id=location.id).exists()
        self.assertFalse(exists)

    def test_user_cannot_delete_others_location(self):
        """Users should not be able to delete other users' locations."""
        other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="testpass123"
        )
        location = models.Location.objects.create(
            name="Restricted Area",
            created_by=other_user,
        )
        url = detail_url(location.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        exists = models.Location.objects.filter(id=location.id).exists()
        self.assertTrue(exists)
