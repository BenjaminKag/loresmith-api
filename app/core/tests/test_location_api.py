"""
Tests for the Location API.
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
from PIL import Image


LOCATIONS_URL = reverse("location-list")


def detail_url(location_id):
    """Create and return a location detail URL."""
    return reverse("location-detail", args=[location_id])


def create_user(**params):
    return get_user_model().objects.create_user(**params)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class LocationApiTests(APITestCase):
    """Tests for the Location API."""

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
        self.assertEqual(location.owner, self.user)

    def test_list_locations(self):
        """GET /api/locations/ should return a list of locations."""
        models.Location.objects.create(name="Mondstadt", owner=self.user)
        models.Location.objects.create(name="Liyue Harbor", owner=self.user)

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
            owner=self.user,
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
            owner=self.user,
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
            owner=other_user,
        )
        url = detail_url(location.id)

        res = self.client.patch(url, {"name": "Hacked!"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        location.refresh_from_db()
        self.assertEqual(location.name, "Secret Base")

    def test_user_can_delete_own_location(self):
        """DELETE should allow the owner to delete their location."""
        location = models.Location.objects.create(
            name="Temporary Location",
            owner=self.user,
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
            owner=other_user,
        )
        url = detail_url(location.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        exists = models.Location.objects.filter(id=location.id).exists()
        self.assertTrue(exists)

    def test_user_can_view_others_location_in_public_story(self):
        """Authenticated users can retrieve locations
          that appear in public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        location = models.Location.objects.create(
            name="Liyue Harbor",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        story.locations.add(location)

        url = detail_url(location.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Liyue Harbor")

    def test_anonymous_user_can_view_location_in_public_story(self):
        """Anonymous users can retrieve locations
          that appear in public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        location = models.Location.objects.create(
            name="Mondstadt",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        story.locations.add(location)

        self.client.force_authenticate(None)
        url = detail_url(location.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_anonymous_user_cannot_view_location_only_in_private_stories(self):
        """Anonymous users cannot retrieve locations that
          appear only in private stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        location = models.Location.objects.create(
            name="Hidden Location",
            owner=other_user,
        )
        story = models.Story.objects.create(
            title="Private Story",
            visibility=models.Story.Visibility.PRIVATE,
            owner=other_user,
        )
        story.locations.add(location)

        self.client.force_authenticate(None)
        url = detail_url(location.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_view_own_location_without_public_story(self):
        """Owners can retrieve their own locations
          even without public story."""
        location = models.Location.objects.create(
            name="Private Location",
            owner=self.user,
        )

        url = detail_url(location.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Private Location")

    def test_upload_image_to_location(self):
        """User can upload an image to their own location."""
        location = models.Location.objects.create(
            name="Location with Image",
            owner=self.user,
        )
        url = detail_url(location.id)
        image = self.generate_image_file()

        res = self.client.patch(
            url,
            {"image": image},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        location.refresh_from_db()
        self.assertTrue(bool(location.image))
        self.assertIn("/media/uploads/location/", res.data["image"])
        self.assertTrue(os.path.exists(location.image.path))

    def test_upload_invalid_image_returns_400(self):
        """Uploading a non-image file should return 400."""
        location = models.Location.objects.create(
            name="Location with Invalid Image",
            owner=self.user,
        )
        url = detail_url(location.id)

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
        """Replacing a location image deletes the old file from storage."""
        location = models.Location.objects.create(
            name="Location Replace Image",
            owner=self.user,
            image=self.generate_image_file(name="old.jpg"),
        )
        old_image_path = location.image.path
        url = detail_url(location.id)

        new_image = self.generate_image_file(name="new.jpg")

        res = self.client.patch(
            url,
            {"image": new_image},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        location.refresh_from_db()
        self.assertTrue(bool(location.image))
        self.assertTrue(os.path.exists(location.image.path))
        self.assertFalse(os.path.exists(old_image_path))
        self.assertNotEqual(location.image.path, old_image_path)

    def test_remove_image_deletes_file(self):
        """Clearing a location image deletes the file from storage."""
        location = models.Location.objects.create(
            name="Location Remove Image",
            owner=self.user,
            image=self.generate_image_file(),
        )
        image_path = location.image.path
        url = detail_url(location.id)

        res = self.client.patch(
            url,
            {"image": ""},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        location.refresh_from_db()
        self.assertFalse(bool(location.image))
        self.assertFalse(os.path.exists(image_path))

    def test_delete_location_deletes_image_file(self):
        """Deleting a location deletes its image file from storage."""
        location = models.Location.objects.create(
            name="Location Delete Image",
            owner=self.user,
            image=self.generate_image_file(),
        )
        image_path = location.image.path
        url = detail_url(location.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            models.Location.objects.filter(id=location.id).exists()
        )
        self.assertFalse(os.path.exists(image_path))

    def test_user_cannot_upload_image_to_others_location(self):
        """Users cannot upload an image to another user's location."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        location = models.Location.objects.create(
            name="Other User Location",
            owner=other_user,
        )
        url = detail_url(location.id)
        image = self.generate_image_file()

        res = self.client.patch(
            url,
            {"image": image},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        location.refresh_from_db()
        self.assertFalse(bool(location.image))
