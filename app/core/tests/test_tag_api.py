"""
Tests for the Tag API.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from core import models


TAGS_URL = reverse("tag-list")


def detail_url(tag_id: int):
    """Create and return a tag detail URL."""
    return reverse("tag-detail", args=[tag_id])


def create_user(email, password="testpass123", **extra):
    """Helper function to create a new user."""
    return get_user_model().objects.create_user(email, password, **extra)


class TagApiTests(APITestCase):
    """Tests for the Tag API."""

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
            name="Test User",
        )
        self.client.force_authenticate(self.user)

    def test_list_tags(self):
        """GET /api/tags/ should return only the user's tags."""
        models.Tag.objects.create(name="Mystic", owner=self.user)

        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        models.Tag.objects.create(name="Secret", owner=other_user)

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], "Mystic")

    def test_create_tag(self):
        """Test creating a tag with valid data."""
        payload = {
            "name": "mystic",
        }

        res = self.client.post(TAGS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        tag = models.Tag.objects.get(id=res.data["id"])
        self.assertEqual(tag.name, "Mystic")
        self.assertEqual(tag.owner, self.user)

    def test_anonymous_user_cannot_list_tags(self):
        """Anonymous users should not be able to list tags."""
        self.client.force_authenticate(None)

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_user_cannot_create_tag(self):
        """Anonymous users should not be able to create tags."""
        self.client.force_authenticate(None)

        payload = {"name": "Mystic"}

        res = self.client.post(TAGS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_retrieve_own_tag(self):
        """Owner can retrieve their own tag."""
        tag = models.Tag.objects.create(
            name="Mystic",
            owner=self.user,
        )
        url = detail_url(tag.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Mystic")

    def test_user_cannot_retrieve_others_tag(self):
        """Users cannot retrieve tags owned by others."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        tag = models.Tag.objects.create(
            name="Hidden",
            owner=other_user,
        )
        url = detail_url(tag.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_update_own_tag(self):
        """Owner can rename their own tag."""
        tag = models.Tag.objects.create(
            name="Mystic",
            owner=self.user,
        )
        url = detail_url(tag.id)

        res = self.client.patch(url, {"name": "ancient"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        tag.refresh_from_db()
        self.assertEqual(tag.name, "Ancient")

    def test_user_cannot_update_others_tag(self):
        """Users cannot update tags owned by others."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        tag = models.Tag.objects.create(
            name="Hidden",
            owner=other_user,
        )
        url = detail_url(tag.id)

        res = self.client.patch(url, {"name": "Hacked"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        tag.refresh_from_db()
        self.assertEqual(tag.name, "Hidden")

    def test_user_can_delete_own_tag(self):
        """Owner can delete their own tag."""
        tag = models.Tag.objects.create(
            name="Temporary",
            owner=self.user,
        )
        url = detail_url(tag.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(models.Tag.objects.filter(id=tag.id).exists())

    def test_user_cannot_delete_others_tag(self):
        """Users cannot delete tags owned by others."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        tag = models.Tag.objects.create(
            name="Restricted",
            owner=other_user,
        )
        url = detail_url(tag.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(models.Tag.objects.filter(id=tag.id).exists())

    def test_create_tag_with_duplicate_name_for_same_user_returns_400(self):
        """User cannot create a duplicate tag name for themselves."""
        models.Tag.objects.create(
            name="Mystic",
            owner=self.user,
        )

        payload = {
            "name": "mystic",
        }

        res = self.client.post(TAGS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            models.Tag.objects.filter(owner=self.user, name="Mystic").count(),
            1,
        )

    def test_same_tag_name_can_exist_for_different_users(self):
        """Different users can have tags with the same name."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        models.Tag.objects.create(
            name="Mystic",
            owner=other_user,
        )

        payload = {
            "name": "mystic",
        }

        res = self.client.post(TAGS_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            models.Tag.objects.filter(name="Mystic").count(),
            2,
        )

    def test_deleting_tag_removes_m2m_links_but_not_objects(self):
        """Deleting a tag removes links but does not delete related objects."""
        tag = models.Tag.objects.create(
            name="Mystic",
            owner=self.user,
        )
        character = models.Character.objects.create(
            name="Xiao",
            owner=self.user,
        )
        location = models.Location.objects.create(
            name="Liyue Harbor",
            location_type="city",
            owner=self.user,
        )

        character.tags.add(tag)
        location.tags.add(tag)

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        character.refresh_from_db()
        location.refresh_from_db()

        self.assertTrue(
            models.Character.objects.filter(id=character.id).exists()
        )
        self.assertTrue(
            models.Location.objects.filter(id=location.id).exists()
        )
        self.assertEqual(character.tags.count(), 0)
        self.assertEqual(location.tags.count(), 0)
