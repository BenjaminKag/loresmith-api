"""
Tests for the Story API.
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


STORIES_URL = reverse("story-list")


def detail_url(story_id: int):
    """Create and return a story detail URL."""
    return reverse("story-detail", args=[story_id])


def create_user(email=None, password="testpass123", **extra):
    """Helper function to create a new user."""
    if email is None:
        email = f"test_{uuid.uuid4().hex}@example.com"

    return get_user_model().objects.create_user(email, password, **extra)


def create_story(owner, **params):
    defaults = {
        "title": f"Test story {uuid.uuid4().hex}",
        "owner": owner,
    }
    defaults.update(params)
    return models.Story.objects.create(**defaults)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class StoryApiTests(APITestCase):
    """Tests for the Story API."""

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

    def test_create_story_with_relations(self):
        """
        Test creating a story with characters, locations, factions, and items.
        """
        location = models.Location.objects.create(
            name="Liyue Harbor",
            description="A bustling harbor city.",
            location_type="city",
            owner=self.user,
        )
        faction = models.Faction.objects.create(
            name="Liyue Qixing",
            description="Leaders of Liyue.",
            faction_type="government",
            owner=self.user,
        )
        item = models.Item.objects.create(
            name="Primordial Jade Winged-Spear",
            item_type="weapon",
            rarity="5-star",
            owner=self.user,
        )
        character = models.Character.objects.create(
            name="Xiao",
            description="A vigilant yaksha.",
            owner=self.user,
        )
        parent_story = models.Story.objects.create(
            title="Rex Lapis' Contract",
            summary="The long-standing contract of Liyue.",
            body="Once upon a time...",
            kind=models.Story.Kind.STORY,
            owner=self.user,
        )

        payload = {
            "title": "Rite of Descension",
            "summary": "The ceremony where Rex Lapis appears.",
            "body": "Every year, the people of Liyue...",
            "kind": models.Story.Kind.PART,
            "story_type": models.Story.StoryType.WORLD_EVENT,
            "visibility": models.Story.Visibility.PRIVATE,
            "in_world_date": "Year 1107 AE",
            "parent": parent_story.id,
            "order": 3,
            "characters": [character.id],
            "locations": [location.id],
            "factions": [faction.id],
            "items": [item.id],
        }

        res = self.client.post(STORIES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        story = models.Story.objects.get(id=res.data["id"])

        self.assertEqual(story.title, "Rite of Descension")
        self.assertEqual(
            story.summary,
            "The ceremony where Rex Lapis appears.",
        )
        self.assertEqual(story.body, "Every year, the people of Liyue...")
        self.assertEqual(story.kind, models.Story.Kind.PART)
        self.assertEqual(story.story_type, models.Story.StoryType.WORLD_EVENT)
        self.assertEqual(story.visibility, models.Story.Visibility.PRIVATE)
        self.assertEqual(story.in_world_date, "Year 1107 AE")
        self.assertEqual(story.parent, parent_story)
        self.assertEqual(story.order, 3)
        self.assertEqual(story.owner, self.user)

        self.assertEqual(list(story.characters.all()), [character])
        self.assertEqual(list(story.locations.all()), [location])
        self.assertEqual(list(story.factions.all()), [faction])
        self.assertEqual(list(story.items.all()), [item])

        self.assertIsNotNone(story.slug)
        self.assertTrue(story.slug)

    def test_list_stories(self):
        """GET /api/stories/ should return a list of the user's stories."""
        models.Story.objects.create(title="Story A", owner=self.user)
        models.Story.objects.create(title="Story B", owner=self.user)

        res = self.client.get(STORIES_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertCountEqual(
            [s["title"] for s in res.data],
            ["Story A", "Story B"],
        )

    def test_retrieve_story_detail(self):
        """GET /api/stories/{id}/ should return story details."""
        story = models.Story.objects.create(
            title="The Archon War",
            summary="The great war of the Archons.",
            body="Long ago...",
            in_world_date="Before the Archon War",
            owner=self.user,
        )
        url = detail_url(story.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "The Archon War")
        self.assertEqual(res.data["summary"], "The great war of the Archons.")
        self.assertEqual(res.data["in_world_date"], "Before the Archon War")

    def test_anonymous_user_cannot_create(self):
        """Anonymous users should not be able to create stories."""
        self.client.force_authenticate(None)

        payload = {"title": "Untitled Lore Entry"}

        res = self.client.post(STORIES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_update_own_story(self):
        """Owner can update their own story."""
        story = models.Story.objects.create(
            title="Old Title",
            owner=self.user,
        )
        url = detail_url(story.id)

        res = self.client.patch(url, {"title": "New Title"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        story.refresh_from_db()
        self.assertEqual(story.title, "New Title")

    def test_user_cannot_update_others_story(self):
        """Users cannot update stories owned by other users."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        story = models.Story.objects.create(
            title="Secret Story",
            owner=other_user,
        )
        url = detail_url(story.id)

        res = self.client.patch(url, {"title": "Hacked!"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        story.refresh_from_db()
        self.assertEqual(story.title, "Secret Story")

    def test_user_can_delete_own_story(self):
        """Owner can delete their own story."""
        story = models.Story.objects.create(
            title="Temporary Story",
            owner=self.user,
        )
        url = detail_url(story.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        exists = models.Story.objects.filter(id=story.id).exists()
        self.assertFalse(exists)

    def test_user_cannot_delete_others_story(self):
        """Users cannot delete stories owned by others."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        story = models.Story.objects.create(
            title="Restricted Story",
            owner=other_user,
        )
        url = detail_url(story.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        exists = models.Story.objects.filter(id=story.id).exists()
        self.assertTrue(exists)

    def test_create_part_without_parent_returns_400(self):
        """API should reject PART stories without a parent."""
        payload = {
            "title": "Lonely Part",
            "kind": models.Story.Kind.PART,
        }

        res = self.client.post(STORIES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", res.data)

    def test_create_story_with_parent_returns_400(self):
        """API should reject STORY entries that have a parent."""
        parent = models.Story.objects.create(
            title="Root Story",
            kind=models.Story.Kind.STORY,
            owner=self.user,
        )

        payload = {
            "title": "Invalid Nested Story",
            "kind": models.Story.Kind.STORY,
            "parent": parent.id,
        }

        res = self.client.post(STORIES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", res.data)

    def test_create_part_under_standalone_returns_400(self):
        """API should reject PART entries under standalone stories."""
        standalone = models.Story.objects.create(
            title="Standalone Story",
            kind=models.Story.Kind.STANDALONE,
            owner=self.user,
        )

        payload = {
            "title": "Invalid Child",
            "kind": models.Story.Kind.PART,
            "parent": standalone.id,
        }

        res = self.client.post(STORIES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", res.data)

    def test_create_standalone_story_returns_201(self):
        """API should allow creating a standalone story."""
        payload = {
            "title": "One-Shot Lore Entry",
            "kind": models.Story.Kind.STANDALONE,
        }

        res = self.client.post(STORIES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        story = models.Story.objects.get(id=res.data["id"])
        self.assertEqual(story.kind, models.Story.Kind.STANDALONE)
        self.assertIsNone(story.parent)

    def test_user_can_view_others_public_story(self):
        """Authenticated users can retrieve another user's public story."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        story = models.Story.objects.create(
            title="Public Story",
            summary="Visible to everyone.",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        url = detail_url(story.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Public Story")

    def test_anonymous_user_can_view_public_story(self):
        """Anonymous users can retrieve public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        url = detail_url(story.id)

        self.client.force_authenticate(None)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Public Story")

    def test_anonymous_user_cannot_view_private_story(self):
        """Anonymous users cannot retrieve private stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        story = models.Story.objects.create(
            title="Private Story",
            visibility=models.Story.Visibility.PRIVATE,
            owner=other_user,
        )
        url = detail_url(story.id)

        self.client.force_authenticate(None)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_includes_public_stories_from_other_users(self):
        """Authenticated users can see their own stories
            and others' public stories."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        models.Story.objects.create(title="My Story", owner=self.user)
        models.Story.objects.create(
            title="Public Story",
            owner=other_user,
            visibility=models.Story.Visibility.PUBLIC,
        )
        models.Story.objects.create(
            title="Private Story",
            owner=other_user,
            visibility=models.Story.Visibility.PRIVATE,
        )

        res = self.client.get(STORIES_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [s["title"] for s in res.data],
            ["My Story", "Public Story"],
        )

    def test_upload_image_to_story(self):
        """User can upload an image to their own story."""
        story = models.Story.objects.create(
            title="Story with Image",
            owner=self.user,
        )
        url = detail_url(story.id)
        image = self.generate_image_file()

        res = self.client.patch(
            url,
            {"image": image},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        story.refresh_from_db()
        self.assertTrue(bool(story.image))
        self.assertIn("/media/uploads/story/", res.data["image"])
        self.assertTrue(os.path.exists(story.image.path))

    def test_upload_invalid_image_returns_400(self):
        """Uploading a non-image file should return 400."""
        story = models.Story.objects.create(
            title="Story with Invalid Image",
            owner=self.user,
        )
        url = detail_url(story.id)

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
        """Replacing a story image deletes the old file from storage."""
        story = models.Story.objects.create(
            title="Story Replace Image",
            owner=self.user,
            image=self.generate_image_file(name="old.jpg"),
        )
        old_image_path = story.image.path
        url = detail_url(story.id)

        new_image = self.generate_image_file(name="new.jpg")

        res = self.client.patch(
            url,
            {"image": new_image},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        story.refresh_from_db()
        self.assertTrue(bool(story.image))
        self.assertTrue(os.path.exists(story.image.path))
        self.assertFalse(os.path.exists(old_image_path))
        self.assertNotEqual(story.image.path, old_image_path)

    def test_remove_image_deletes_file(self):
        """Clearing a story image deletes the file from storage."""
        story = models.Story.objects.create(
            title="Story Remove Image",
            owner=self.user,
            image=self.generate_image_file(),
        )
        image_path = story.image.path
        url = detail_url(story.id)

        res = self.client.patch(
            url,
            {"image": ""},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        story.refresh_from_db()
        self.assertFalse(bool(story.image))
        self.assertFalse(os.path.exists(image_path))

    def test_delete_story_deletes_image_file(self):
        """Deleting a story deletes its image file from storage."""
        story = models.Story.objects.create(
            title="Story Delete Image",
            owner=self.user,
            image=self.generate_image_file(),
        )
        image_path = story.image.path
        url = detail_url(story.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(models.Story.objects.filter(id=story.id).exists())
        self.assertFalse(os.path.exists(image_path))

    def test_user_cannot_upload_image_to_others_story(self):
        """Users cannot upload an image to another user's story."""
        other_user = create_user(
            email="other@example.com",
            password="testpass123",
        )
        story = models.Story.objects.create(
            title="Other User Story",
            owner=other_user,
        )
        url = detail_url(story.id)
        image = self.generate_image_file()

        res = self.client.patch(
            url,
            {"image": image},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        story.refresh_from_db()
        self.assertFalse(bool(story.image))

    def test_filter_stories_by_tag(self):
        """Filtering stories by tag returns matching stories only."""
        tag_myth = models.Tag.objects.create(
            name="Myth",
            owner=self.user,
        )
        tag_quest = models.Tag.objects.create(
            name="Quest",
            owner=self.user,
        )

        story1 = models.Story.objects.create(
            title="Archon War",
            owner=self.user,
        )
        story2 = models.Story.objects.create(
            title="Rite of Descension",
            owner=self.user,
        )

        story1.tags.add(tag_myth)
        story2.tags.add(tag_quest)

        res = self.client.get(STORIES_URL, {"tags": "Myth"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Archon War")


class StoryWikiApiTests(APITestCase):
    """Tests for the Story Wiki API endpoint."""

    def test_wiki_returns_data_for_story_root(self):
        user = create_user(email="user@example.com", password="testpass123")
        self.client.force_authenticate(user)

        story = create_story(owner=user, kind=models.Story.Kind.STORY)

        url = detail_url(story.id) + "wiki/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("story", res.data)
        self.assertIn("aggregated", res.data)
        self.assertIn("tree", res.data)

    def test_wiki_returns_data_for_standalone_root(self):
        user = create_user(email="user@example.com", password="testpass123")
        self.client.force_authenticate(user)

        story = create_story(owner=user, kind=models.Story.Kind.STANDALONE)

        url = detail_url(story.id) + "wiki/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["story"]["part_count"], 0)
        self.assertEqual(res.data["tree"]["children"], [])

    def test_wiki_returns_400_for_part_root(self):
        user = create_user(email="user@example.com", password="testpass123")
        self.client.force_authenticate(user)

        root = create_story(owner=user, kind=models.Story.Kind.STORY)
        part = create_story(
            owner=user,
            kind=models.Story.Kind.PART,
            parent=root,
        )

        url = detail_url(part.id) + "wiki/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data["detail"],
            "Wiki is only available for STORY or STANDALONE stories."
        )

    def test_wiki_aggregated_characters_are_deduplicated(self):
        user = create_user(email="user@example.com", password="testpass123")
        self.client.force_authenticate(user)

        root = create_story(
            owner=user,
            title="Root",
            kind=models.Story.Kind.STORY
        )
        child = create_story(
            owner=user,
            title="Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
        )
        character = models.Character.objects.create(
            owner=user,
            name="Hero"
        )

        root.characters.add(character)
        child.characters.add(character)

        url = detail_url(root.id) + "wiki/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["aggregated"]["characters"]), 1)
        self.assertEqual(
            res.data["aggregated"]["characters"][0]["id"],
            character.id,
        )

    def test_wiki_tree_shows_direct_characters_per_node(self):
        user = create_user(email="user@example.com", password="testpass123")
        self.client.force_authenticate(user)

        root = create_story(
            owner=user,
            title="Root",
            kind=models.Story.Kind.STORY
        )
        child = create_story(
            owner=user,
            title="Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
        )

        root_character = models.Character.objects.create(
            owner=user,
            name="Root Hero"
        )
        child_character = models.Character.objects.create(
            owner=user,
            name="Child Hero"
        )

        root.characters.add(root_character)
        child.characters.add(child_character)

        url = detail_url(root.id) + "wiki/"
        res = self.client.get(url)

        tree = res.data["tree"]
        child_tree = tree["children"][0]

        self.assertEqual(len(tree["characters"]), 1)
        self.assertEqual(tree["characters"][0]["id"], root_character.id)

        self.assertEqual(len(child_tree["characters"]), 1)
        self.assertEqual(child_tree["characters"][0]["id"], child_character.id)

    def test_wiki_tree_children_are_ordered(self):
        user = create_user(email="user@example.com", password="testpass123")
        self.client.force_authenticate(user)

        root = create_story(owner=user, kind=models.Story.Kind.STORY)

        child_2 = create_story(
            owner=user,
            title="Second",
            kind=models.Story.Kind.PART,
            parent=root,
            order=2,
        )
        child_1 = create_story(
            owner=user,
            title="First",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
        )

        url = detail_url(root.id) + "wiki/"
        res = self.client.get(url)

        children = res.data["tree"]["children"]
        self.assertEqual(children[0]["id"], child_1.id)
        self.assertEqual(children[1]["id"], child_2.id)

    def test_wiki_hides_private_child_content_from_non_owner(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="A",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="B",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        public_child = create_story(
            owner=owner,
            title="C",
            kind=models.Story.Kind.PART,
            parent=root,
            order=2,
            visibility=models.Story.Visibility.PUBLIC,
        )

        char_a = models.Character.objects.create(
            owner=owner,
            name="Char A"
        )
        char_b = models.Character.objects.create(
            owner=owner,
            name="Char B"
        )
        char_c = models.Character.objects.create(
            owner=owner,
            name="Char C"
        )

        root.characters.add(char_a)
        private_child.characters.add(char_b)
        public_child.characters.add(char_c)

        url = detail_url(root.id) + "wiki/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        aggregated_ids = [
            character["id"]
            for character in res.data["aggregated"]["characters"]
        ]
        tree_child_ids = [
            child["id"]
            for child in res.data["tree"]["children"]
        ]

        self.assertIn(char_a.id, aggregated_ids)
        self.assertIn(char_c.id, aggregated_ids)
        self.assertNotIn(char_b.id, aggregated_ids)

        self.assertIn(public_child.id, tree_child_ids)
        self.assertNotIn(private_child.id, tree_child_ids)

    def test_wiki_includes_private_child_content_for_owner(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="A",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="B",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        public_child = create_story(
            owner=owner,
            title="C",
            kind=models.Story.Kind.PART,
            parent=root,
            order=2,
            visibility=models.Story.Visibility.PUBLIC,
        )

        char_a = models.Character.objects.create(
            owner=owner,
            name="Char A"
        )
        char_b = models.Character.objects.create(
            owner=owner,
            name="Char B"
        )
        char_c = models.Character.objects.create(
            owner=owner,
            name="Char C"
        )

        root.characters.add(char_a)
        private_child.characters.add(char_b)
        public_child.characters.add(char_c)

        url = detail_url(root.id) + "wiki/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        aggregated_ids = [
            character["id"]
            for character in res.data["aggregated"]["characters"]
        ]

        tree_child_ids = [
            child["id"]
            for child in res.data["tree"]["children"]
        ]

        self.assertIn(char_a.id, aggregated_ids)
        self.assertIn(char_b.id, aggregated_ids)
        self.assertIn(char_c.id, aggregated_ids)

        self.assertIn(private_child.id, tree_child_ids)
        self.assertIn(public_child.id, tree_child_ids)

    def test_wiki_metadata_counts_respect_visibility(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        public_child = create_story(
            owner=owner,
            kind=models.Story.Kind.PART,
            parent=root,
            order=2,
            visibility=models.Story.Visibility.PUBLIC,
        )

        char_root = models.Character.objects.create(
            owner=owner,
            name="Root Char"
        )
        char_private = models.Character.objects.create(
            owner=owner,
            name="Private Char"
        )
        char_public = models.Character.objects.create(
            owner=owner,
            name="Public Char"
        )

        root.characters.add(char_root)
        private_child.characters.add(char_private)
        public_child.characters.add(char_public)

        url = detail_url(root.id) + "wiki/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["story"]["character_count"], 2)
        self.assertEqual(res.data["story"]["part_count"], 1)


class StoryCharacterWikiApiTests(APITestCase):
    """Tests for the Story Character Wiki API endpoint."""

    def test_character_wiki_returns_data_for_character_in_root_story(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        character = models.Character.objects.create(
            owner=owner,
            name="Root Hero",
            description="Main protagonist.",
        )
        root.characters.add(character)

        url = detail_url(root.id) + f"wiki/characters/{character.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], character.id)
        self.assertEqual(res.data["name"], "Root Hero")
        self.assertEqual(res.data["description"], "Main protagonist.")

    def test_character_wiki_returns_data_for_character_in_public_child(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        public_child = create_story(
            owner=owner,
            title="Public Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PUBLIC,
        )
        character = models.Character.objects.create(
            owner=owner,
            name="Public Child Hero",
        )
        public_child.characters.add(character)

        url = detail_url(root.id) + f"wiki/characters/{character.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], character.id)
        self.assertEqual(res.data["name"], "Public Child Hero")

    def test_private_child_character_not_visible_to_non_owner(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        character = models.Character.objects.create(
            owner=owner,
            name="Hidden Hero",
        )
        private_child.characters.add(character)

        url = detail_url(root.id) + f"wiki/characters/{character.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_private_child_character_visible_to_owner(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        character = models.Character.objects.create(
            owner=owner,
            name="Hidden Hero",
        )
        private_child.characters.add(character)

        url = detail_url(root.id) + f"wiki/characters/{character.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], character.id)
        self.assertEqual(res.data["name"], "Hidden Hero")

    def test_character_outside_story_subtree_gives_404(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        other_story = create_story(
            owner=owner,
            title="Other Story",
            kind=models.Story.Kind.STORY,
        )
        character = models.Character.objects.create(
            owner=owner,
            name="Unrelated Hero",
        )
        other_story.characters.add(character)

        url = detail_url(root.id) + f"wiki/characters/{character.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_character_wiki_returns_400_for_part_root(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        part = create_story(
            owner=owner,
            title="Part Story",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
        )
        character = models.Character.objects.create(
            owner=owner,
            name="Part Hero",
        )
        part.characters.add(character)

        url = detail_url(part.id) + f"wiki/characters/{character.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data["detail"],
            "Wiki is only available for STORY or STANDALONE stories.",
        )

    def test_character_wiki_stories_field_includes_only_visible_stories(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        public_child = create_story(
            owner=owner,
            title="Public Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=2,
            visibility=models.Story.Visibility.PUBLIC,
        )
        character = models.Character.objects.create(
            owner=owner,
            name="Shared Hero",
        )

        root.characters.add(character)
        private_child.characters.add(character)
        public_child.characters.add(character)

        url = detail_url(root.id) + f"wiki/characters/{character.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        story_ids = [story["id"] for story in res.data["stories"]]

        self.assertIn(root.id, story_ids)
        self.assertIn(public_child.id, story_ids)
        self.assertNotIn(private_child.id, story_ids)


class StoryLocationWikiApiTests(APITestCase):
    """Tests for the Story Location Wiki API endpoint."""

    def test_location_wiki_returns_data_for_location_in_root_story(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        location = models.Location.objects.create(
            owner=owner,
            name="Root City",
            description="Main city.",
            location_type="city",
        )
        root.locations.add(location)

        url = detail_url(root.id) + f"wiki/locations/{location.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], location.id)
        self.assertEqual(res.data["name"], "Root City")
        self.assertEqual(res.data["description"], "Main city.")
        self.assertEqual(res.data["location_type"], "city")

    def test_location_wiki_returns_data_for_location_in_public_child(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        public_child = create_story(
            owner=owner,
            title="Public Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PUBLIC,
        )
        location = models.Location.objects.create(
            owner=owner,
            name="Public Forest",
            location_type="forest",
        )
        public_child.locations.add(location)

        url = detail_url(root.id) + f"wiki/locations/{location.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], location.id)
        self.assertEqual(res.data["name"], "Public Forest")

    def test_private_child_location_not_visible_to_non_owner(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        location = models.Location.objects.create(
            owner=owner,
            name="Hidden Cave",
            location_type="cave",
        )
        private_child.locations.add(location)

        url = detail_url(root.id) + f"wiki/locations/{location.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_private_child_location_visible_to_owner(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        location = models.Location.objects.create(
            owner=owner,
            name="Hidden Cave",
            location_type="cave",
        )
        private_child.locations.add(location)

        url = detail_url(root.id) + f"wiki/locations/{location.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], location.id)
        self.assertEqual(res.data["name"], "Hidden Cave")

    def test_location_outside_story_subtree_gives_404(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        other_story = create_story(
            owner=owner,
            title="Other Story",
            kind=models.Story.Kind.STORY,
        )
        location = models.Location.objects.create(
            owner=owner,
            name="Unrelated Place",
            location_type="city",
        )
        other_story.locations.add(location)

        url = detail_url(root.id) + f"wiki/locations/{location.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_location_wiki_returns_400_for_part_root(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        part = create_story(
            owner=owner,
            title="Part Story",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
        )
        location = models.Location.objects.create(
            owner=owner,
            name="Part Town",
            location_type="town",
        )
        part.locations.add(location)

        url = detail_url(part.id) + f"wiki/locations/{location.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data["detail"],
            "Wiki is only available for STORY or STANDALONE stories.",
        )

    def test_location_wiki_stories_field_includes_only_visible_stories(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        public_child = create_story(
            owner=owner,
            title="Public Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=2,
            visibility=models.Story.Visibility.PUBLIC,
        )
        location = models.Location.objects.create(
            owner=owner,
            name="Shared Place",
            location_type="ruins",
        )

        root.locations.add(location)
        private_child.locations.add(location)
        public_child.locations.add(location)

        url = detail_url(root.id) + f"wiki/locations/{location.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        story_ids = [story["id"] for story in res.data["stories"]]

        self.assertIn(root.id, story_ids)
        self.assertIn(public_child.id, story_ids)
        self.assertNotIn(private_child.id, story_ids)


class StoryItemWikiApiTests(APITestCase):
    """Tests for the Story Item Wiki API endpoint."""

    def test_item_wiki_returns_data_for_item_in_root_story(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        item = models.Item.objects.create(
            owner=owner,
            name="Ancient Sword",
            description="A blade from the old kingdom.",
            item_type="weapon",
            rarity="legendary",
        )
        root.items.add(item)

        url = detail_url(root.id) + f"wiki/items/{item.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], item.id)
        self.assertEqual(res.data["name"], "Ancient Sword")
        self.assertEqual(
            res.data["description"], "A blade from the old kingdom."
        )
        self.assertEqual(res.data["item_type"], "weapon")
        self.assertEqual(res.data["rarity"], "legendary")

    def test_item_wiki_returns_data_for_item_in_public_child(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        public_child = create_story(
            owner=owner,
            title="Public Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PUBLIC,
        )
        item = models.Item.objects.create(
            owner=owner,
            name="Traveler's Compass",
            item_type="tool",
            rarity="common",
        )
        public_child.items.add(item)

        url = detail_url(root.id) + f"wiki/items/{item.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], item.id)
        self.assertEqual(res.data["name"], "Traveler's Compass")

    def test_private_child_item_not_visible_to_non_owner(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        item = models.Item.objects.create(
            owner=owner,
            name="Hidden Relic",
            item_type="artifact",
            rarity="rare",
        )
        private_child.items.add(item)

        url = detail_url(root.id) + f"wiki/items/{item.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_private_child_item_visible_to_owner(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        item = models.Item.objects.create(
            owner=owner,
            name="Hidden Relic",
            item_type="artifact",
            rarity="rare",
        )
        private_child.items.add(item)

        url = detail_url(root.id) + f"wiki/items/{item.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], item.id)
        self.assertEqual(res.data["name"], "Hidden Relic")

    def test_item_outside_story_subtree_gives_404(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        other_story = create_story(
            owner=owner,
            title="Other Story",
            kind=models.Story.Kind.STORY,
        )
        item = models.Item.objects.create(
            owner=owner,
            name="Unrelated Item",
            item_type="artifact",
            rarity="rare",
        )
        other_story.items.add(item)

        url = detail_url(root.id) + f"wiki/items/{item.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_item_wiki_returns_400_for_part_root(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        part = create_story(
            owner=owner,
            title="Part Story",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
        )
        item = models.Item.objects.create(
            owner=owner,
            name="Part Dagger",
            item_type="weapon",
            rarity="common",
        )
        part.items.add(item)

        url = detail_url(part.id) + f"wiki/items/{item.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data["detail"],
            "Wiki is only available for STORY or STANDALONE stories.",
        )

    def test_item_wiki_stories_field_includes_only_visible_stories(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        public_child = create_story(
            owner=owner,
            title="Public Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=2,
            visibility=models.Story.Visibility.PUBLIC,
        )
        item = models.Item.objects.create(
            owner=owner,
            name="Shared Relic",
            item_type="artifact",
            rarity="epic",
        )

        root.items.add(item)
        private_child.items.add(item)
        public_child.items.add(item)

        url = detail_url(root.id) + f"wiki/items/{item.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        story_ids = [story["id"] for story in res.data["stories"]]

        self.assertIn(root.id, story_ids)
        self.assertIn(public_child.id, story_ids)
        self.assertNotIn(private_child.id, story_ids)


class StoryFactionWikiApiTests(APITestCase):
    """Tests for the Story Faction Wiki API endpoint."""

    def test_faction_wiki_returns_data_for_faction_in_root_story(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        faction = models.Faction.objects.create(
            owner=owner,
            name="Silver Guard",
            description="Protectors of the capital.",
            faction_type="military",
        )
        root.factions.add(faction)

        url = detail_url(root.id) + f"wiki/factions/{faction.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], faction.id)
        self.assertEqual(res.data["name"], "Silver Guard")
        self.assertEqual(res.data["description"], "Protectors of the capital.")
        self.assertEqual(res.data["faction_type"], "military")

    def test_faction_wiki_returns_data_for_faction_in_public_child(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        public_child = create_story(
            owner=owner,
            title="Public Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PUBLIC,
        )
        faction = models.Faction.objects.create(
            owner=owner,
            name="Free Traders",
            faction_type="guild",
        )
        public_child.factions.add(faction)

        url = detail_url(root.id) + f"wiki/factions/{faction.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], faction.id)
        self.assertEqual(res.data["name"], "Free Traders")

    def test_private_child_faction_not_visible_to_non_owner(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        faction = models.Faction.objects.create(
            owner=owner,
            name="Shadow Circle",
            faction_type="cult",
        )
        private_child.factions.add(faction)

        url = detail_url(root.id) + f"wiki/factions/{faction.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_private_child_faction_visible_to_owner(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        faction = models.Faction.objects.create(
            owner=owner,
            name="Shadow Circle",
            faction_type="cult",
        )
        private_child.factions.add(faction)

        url = detail_url(root.id) + f"wiki/factions/{faction.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], faction.id)
        self.assertEqual(res.data["name"], "Shadow Circle")

    def test_faction_outside_story_subtree_gives_404(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        other_story = create_story(
            owner=owner,
            title="Other Story",
            kind=models.Story.Kind.STORY,
        )
        faction = models.Faction.objects.create(
            owner=owner,
            name="Unrelated Order",
            faction_type="religious",
        )
        other_story.factions.add(faction)

        url = detail_url(root.id) + f"wiki/factions/{faction.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_faction_wiki_returns_400_for_part_root(self):
        owner = create_user(email="owner@example.com", password="testpass123")
        self.client.force_authenticate(owner)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
        )
        part = create_story(
            owner=owner,
            title="Part Story",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
        )
        faction = models.Faction.objects.create(
            owner=owner,
            name="Part Guild",
            faction_type="guild",
        )
        part.factions.add(faction)

        url = detail_url(part.id) + f"wiki/factions/{faction.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data["detail"],
            "Wiki is only available for STORY or STANDALONE stories.",
        )

    def test_faction_wiki_stories_field_includes_only_visible_stories(self):
        owner = create_user(
            email="owner@example.com",
            password="testpass123"
        )
        other_user = create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(other_user)

        root = create_story(
            owner=owner,
            title="Root Story",
            kind=models.Story.Kind.STORY,
            visibility=models.Story.Visibility.PUBLIC,
        )
        private_child = create_story(
            owner=owner,
            title="Private Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=1,
            visibility=models.Story.Visibility.PRIVATE,
        )
        public_child = create_story(
            owner=owner,
            title="Public Child",
            kind=models.Story.Kind.PART,
            parent=root,
            order=2,
            visibility=models.Story.Visibility.PUBLIC,
        )
        faction = models.Faction.objects.create(
            owner=owner,
            name="Shared Alliance",
            faction_type="alliance",
        )

        root.factions.add(faction)
        private_child.factions.add(faction)
        public_child.factions.add(faction)

        url = detail_url(root.id) + f"wiki/factions/{faction.id}/"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        story_ids = [story["id"] for story in res.data["stories"]]

        self.assertIn(root.id, story_ids)
        self.assertIn(public_child.id, story_ids)
        self.assertNotIn(private_child.id, story_ids)
