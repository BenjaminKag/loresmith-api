"""
Tests for Story model.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.db import IntegrityError

from core import models


def create_user(email="test@example.com", password="testpass123", **extra):
    """Helper function to create a new user."""

    return get_user_model().objects.create_user(email, password, **extra)


def create_story(**params):
    """Helper function to create a story."""
    defaults = {
        "title": "The Fall of Kharios",
        "summary": "A brief summary of the events.",
        "body": "Full story body goes here.",
    }
    defaults.update(params)
    return models.Story.objects.create(**defaults)


class StoryModelTests(TestCase):
    """Tests for story model."""

    def test_string_representation_returns_title(self):
        """__str__ should return the story title."""
        story = create_story(title="Jade Winged Spear Legend")
        self.assertEqual(str(story), "Jade Winged Spear Legend")

    def test_slug_is_auto_generated_on_create(self):
        """Slug should be auto-generated from title if not provided."""
        story = create_story(title="Jade Winged Spear Legend")
        expected_slug = slugify("Jade Winged Spear Legend")

        self.assertEqual(story.slug, expected_slug)

    def test_slug_does_not_change_when_title_changes(self):
        """Slug should stay the same when the title changes."""
        story = create_story(title="Old Title")
        original_slug = story.slug

        story.title = "New Title"
        story.save()

        self.assertEqual(story.slug, original_slug)

    def test_default_enum_values(self):
        """
        kind, story_type, visibility and order should have correct defaults.
        """
        story = create_story(title="Defaults Story")

        self.assertEqual(story.kind, models.Story.Kind.STANDALONE)
        self.assertEqual(story.story_type, models.Story.StoryType.LORE)
        self.assertEqual(story.visibility, models.Story.Visibility.PRIVATE)
        self.assertEqual(story.order, 0)

    def test_can_set_created_by(self):
        """created_by can be set and retrieved."""
        user = create_user()
        story = create_story(created_by=user)

        self.assertEqual(story.created_by, user)

    def test_parent_and_sub_stories_relationship(self):
        """Test that parent and sub_stories relationship works correctly."""
        arc = create_story(
            title="Arc: The Fall of Kharios",
            kind=models.Story.Kind.ARC,
        )
        part1 = create_story(
            title="Part 1: The Betrayal",
            kind=models.Story.Kind.PART,
            parent=arc,
            order=1,
        )
        part2 = create_story(
            title="Part 2: Fire at Dawn",
            kind=models.Story.Kind.PART,
            parent=arc,
            order=2,
        )

        sub_stories = list(arc.sub_stories.all())

        self.assertIn(part1, sub_stories)
        self.assertIn(part2, sub_stories)
        self.assertEqual(len(sub_stories), 2)

    def test_in_world_date_is_optional(self):
        """in_world_date can be blank or set."""
        story_blank = create_story(title="No Date Story")
        story_with_date = create_story(
            title="Dated Story",
            in_world_date="Year 1107 AE",
        )

        self.assertEqual(story_blank.in_world_date, "")
        self.assertEqual(story_with_date.in_world_date, "Year 1107 AE")

    def test_many_to_many_relations_can_be_used(self):
        """
        Characters, locations, factions and items can be
        linked to a story.
        """
        character1 = models.Character.objects.create(name="Xiao")
        character2 = models.Character.objects.create(name="Venti")
        location1 = models.Location.objects.create(name="Liyue")
        location2 = models.Location.objects.create(name="Mondstadt")
        faction1 = models.Faction.objects.create(name="Adepti")
        faction2 = models.Faction.objects.create(name="Archons")
        item1 = models.Item.objects.create(name="Jade Winged Spear")
        item2 = models.Item.objects.create(name="The Daybreak Chronicles")

        story = create_story(title="Xiao and Venti meeting")

        story.characters.add(character1)
        story.characters.add(character2)
        story.locations.add(location1)
        story.locations.add(location2)
        story.factions.add(faction1)
        story.factions.add(faction2)
        story.items.add(item1)
        story.items.add(item2)

        self.assertIn(story, character1.stories.all())
        self.assertIn(story, character2.stories.all())
        self.assertIn(story, location1.stories.all())
        self.assertIn(story, location2.stories.all())
        self.assertIn(story, faction1.stories.all())
        self.assertIn(story, faction2.stories.all())
        self.assertIn(story, item1.stories.all())
        self.assertIn(story, item2.stories.all())

        self.assertIn(character1, story.characters.all())
        self.assertIn(character2, story.characters.all())
        self.assertIn(location1, story.locations.all())
        self.assertIn(location2, story.locations.all())
        self.assertIn(faction1, story.factions.all())
        self.assertIn(faction2, story.factions.all())
        self.assertIn(item1, story.items.all())
        self.assertIn(item2, story.items.all())

    def test_sub_stories_are_ordered_by_order_field(self):
        """
        Given multiple parts under the same parent, they should
        follow Meta.ordering: kind, parent__id, order, title.
        For a single parent, the important part is 'order' then 'title'.
        """
        arc = create_story(
            title="Arc: The Voyage",
            kind=models.Story.Kind.ARC,
        )
        part2 = create_story(
            title="Part B",
            kind=models.Story.Kind.PART,
            parent=arc,
            order=2,
        )
        part1 = create_story(
            title="Part A",
            kind=models.Story.Kind.PART,
            parent=arc,
            order=1,
        )

        ordered_parts = list(arc.sub_stories.all())
        self.assertEqual(ordered_parts, [part1, part2])

    def test_meta_ordering_across_kinds(self):
        """
        Stories should follow Meta.ordering across different kinds:
        kind, parent__id, order, title.
        With our Kind values, that means: ARC -> PART -> STANDALONE.
        """
        # Create an arc (no parent)
        arc = create_story(
            title="Arc Story",
            kind=models.Story.Kind.ARC,
            order=2,
        )

        # Create a part under that arc
        part = create_story(
            title="Part Story",
            kind=models.Story.Kind.PART,
            parent=arc,
            order=1,
        )

        # Create a standalone story
        standalone = create_story(
            title="Standalone Story",
            kind=models.Story.Kind.STANDALONE,
            order=1,
        )

        stories = list(models.Story.objects.all())
        self.assertEqual(stories, [arc, part, standalone])

    def test_creating_two_stories_with_same_title_raises_integrity_error(self):
        """
        Because slug is unique and auto-generated from title,
        creating two stories with the same title should raise IntegrityError.
        """
        create_story(title="Duplicate Title")

        with self.assertRaises(IntegrityError):
            create_story(title="Duplicate Title")
