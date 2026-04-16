"""
Tests for the Item API.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from rest_framework.test import APITestCase
from rest_framework import status

from core import models

import os
import shutil
import tempfile
import uuid
from PIL import Image


ITEMS_URL = reverse("item-list")


def detail_url(item_id: int):
    """Create and return an item detail URL."""
    return reverse("item-detail", args=[item_id])


def create_user(email=None, password="testpass123", **extra):
    """Helper function to create a new user."""
    if email is None:
        email = f"test_{uuid.uuid4().hex}@example.com"

    return get_user_model().objects.create_user(email, password, **extra)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ItemApiTests(APITestCase):
    """Tests for the Item API."""

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
            name="Test User",
        )
        self.client.force_authenticate(self.user)

    @staticmethod
    def generate_image_file(name="test.jpg"):
        """Generate a temporary image file for upload tests."""
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            return SimpleUploadedFile(
                name=name,
                content=ntf.read(),
                content_type="image/jpeg",
            )

    def tearDown(self):
        """Clean up temporary media files after each test run."""
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDown()

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
        self.assertEqual(item.owner, self.user)

    def test_list_items(self):
        """GET /api/items/ should return a list of items."""
        models.Item.objects.create(name="Sword", owner=self.user)
        models.Item.objects.create(name="Bow", owner=self.user)

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
            owner=self.user,
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
            owner=self.user,
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
            owner=other_user,
        )
        url = detail_url(item.id)

        res = self.client.patch(url, {"name": "Hacked!"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        item.refresh_from_db()
        self.assertEqual(item.name, "Secret Artifact")

    def test_user_can_delete_own_item(self):
        """Owner can delete their own item."""
        item = models.Item.objects.create(
            name="Temporary Item",
            owner=self.user,
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
            owner=other_user,
        )
        url = detail_url(item.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        exists = models.Item.objects.filter(id=item.id).exists()
        self.assertTrue(exists)

    def test_user_can_view_others_item_in_public_story(self):
        """Authenticated users can retrieve items
          that appear in public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        item = models.Item.objects.create(
            name="Public Sword",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        story.items.add(item)

        url = detail_url(item.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Public Sword")

    def test_anonymous_user_can_view_item_in_public_story(self):
        """Anonymous users can retrieve items
          that appear in public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        item = models.Item.objects.create(
            name="Visible Artifact",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        story.items.add(item)

        self.client.force_authenticate(None)
        url = detail_url(item.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_anonymous_user_cannot_view_item_only_in_private_stories(self):
        """Anonymous users cannot retrieve items
          that appear only in private stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        item = models.Item.objects.create(
            name="Hidden Artifact",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Private Story",
            visibility=models.Story.Visibility.PRIVATE,
            owner=other_user,
        )
        story.items.add(item)

        self.client.force_authenticate(None)
        url = detail_url(item.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_view_own_item_without_public_story(self):
        """Owners can retrieve their own items
          even without public story."""
        item = models.Item.objects.create(
            name="Private Artifact",
            owner=self.user,
        )

        url = detail_url(item.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Private Artifact")

    def test_list_includes_own_and_public_story_items_only(self):
        """Authenticated users see their own items
          and items from public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )

        models.Item.objects.create(
            name="My Item",
            owner=self.user,
        )
        public_item = models.Item.objects.create(
            name="Public Item",
            owner=other_user,
        )
        private_item = models.Item.objects.create(
            name="Private Item",
            owner=other_user,
        )

        public_story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        private_story = models.Story.objects.create(
            title="Private Story",
            visibility=models.Story.Visibility.PRIVATE,
            owner=other_user,
        )

        public_story.items.add(public_item)
        private_story.items.add(private_item)

        res = self.client.get(ITEMS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [i["name"] for i in res.data],
            ["My Item", "Public Item"],
        )

    def test_upload_image_to_item(self):
        """User can upload an image to their own item."""
        item = models.Item.objects.create(
            name="Item with Image",
            owner=self.user,
        )
        url = detail_url(item.id)
        image = self.generate_image_file()

        res = self.client.patch(
            url,
            {"image": image},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        item.refresh_from_db()
        self.assertTrue(bool(item.image))
        self.assertIn("/media/uploads/item/", res.data["image"])
        self.assertTrue(os.path.exists(item.image.path))

    def test_upload_invalid_image_returns_400(self):
        """Uploading a non-image file should return 400."""
        item = models.Item.objects.create(
            name="Item with Invalid Image",
            owner=self.user,
        )
        url = detail_url(item.id)

        bad_file = SimpleUploadedFile(
            "not-image.txt",
            b"this is not an image",
            content_type="text/plain",
        )

        res = self.client.patch(
            url,
            {"image": bad_file},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", res.data)

    def test_replace_image_deletes_old_file(self):
        """Replacing an item image deletes the old file."""
        item = models.Item.objects.create(
            name="Item Replace Image",
            owner=self.user,
            image=self.generate_image_file(name="old.jpg"),
        )
        old_image_path = item.image.path
        url = detail_url(item.id)

        new_image = self.generate_image_file(name="new.jpg")

        res = self.client.patch(
            url,
            {"image": new_image},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        item.refresh_from_db()
        self.assertTrue(os.path.exists(item.image.path))
        self.assertFalse(os.path.exists(old_image_path))
        self.assertNotEqual(item.image.path, old_image_path)

    def test_remove_image_deletes_file(self):
        """Clearing an item image deletes the file."""
        item = models.Item.objects.create(
            name="Item Remove Image",
            owner=self.user,
            image=self.generate_image_file(),
        )
        image_path = item.image.path
        url = detail_url(item.id)

        res = self.client.patch(
            url,
            {"image": ""},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        item.refresh_from_db()
        self.assertFalse(bool(item.image))
        self.assertFalse(os.path.exists(image_path))

    def test_delete_item_deletes_image_file(self):
        """Deleting an item deletes its image file."""
        item = models.Item.objects.create(
            name="Item Delete Image",
            owner=self.user,
            image=self.generate_image_file(),
        )
        image_path = item.image.path
        url = detail_url(item.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(models.Item.objects.filter(id=item.id).exists())
        self.assertFalse(os.path.exists(image_path))

    def test_user_cannot_upload_image_to_others_item(self):
        """Users cannot upload an image to another user's item."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        item = models.Item.objects.create(
            name="Other User Item",
            owner=other_user,
        )
        url = detail_url(item.id)
        image = self.generate_image_file()

        res = self.client.patch(
            url,
            {"image": image},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        item.refresh_from_db()
        self.assertFalse(bool(item.image))

    def test_filter_items_by_tag(self):
        """Filtering items by tag returns matching items only."""
        tag_weapon = models.Tag.objects.create(
            name="Weapon",
            owner=self.user,
        )
        tag_artifact = models.Tag.objects.create(
            name="Artifact",
            owner=self.user,
        )

        item1 = models.Item.objects.create(
            name="Sword",
            owner=self.user,
        )
        item2 = models.Item.objects.create(
            name="Crown",
            owner=self.user,
        )

        item1.tags.add(tag_weapon)
        item2.tags.add(tag_artifact)

        res = self.client.get(ITEMS_URL, {"tags": "Weapon"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], "Sword")
