"""
Tests for story analysis cleanup helpers.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from core import models
from core.services.story_analysis_cleanup import (
    cleanup_old_story_analyses,
)


class StoryAnalysisCleanupTests(TestCase):
    """Tests for old StoryAnalysis cleanup behavior."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.story = models.Story.objects.create(
            title="Test Story",
            summary="Summary",
            body="Body",
            owner=self.user,
        )

    def _create_analysis(self, input_hash):
        """Create a StoryAnalysis record for the test story."""
        return models.StoryAnalysis.objects.create(
            story=self.story,
            owner=self.user,
            input_hash=input_hash,
            result={
                "summary": f"Summary {input_hash}",
                "meta": {},
            },
            ai_mode="mock",
            model=None,
        )

    def test_cleanup_keeps_latest_story_analysis(self):
        """Cleanup should keep only the latest analysis for a story."""
        analyses = [
            self._create_analysis(f"hash-{index}")
            for index in range(3)
        ]

        deleted_count = cleanup_old_story_analyses(story=self.story)

        self.assertEqual(deleted_count, 2)

        remaining_analysis = models.StoryAnalysis.objects.get(
            story=self.story,
        )

        self.assertEqual(remaining_analysis.id, analyses[-1].id)

    def test_cleanup_does_not_delete_other_story_analyses(self):
        """Cleanup should only affect analyses for the selected story."""
        other_story = models.Story.objects.create(
            title="Other Story",
            summary="Summary",
            body="Body",
            owner=self.user,
        )

        for index in range(7):
            self._create_analysis(f"hash-{index}")

        other_analysis = models.StoryAnalysis.objects.create(
            story=other_story,
            owner=self.user,
            input_hash="other-hash",
            result={"summary": "Other", "meta": {}},
            ai_mode="mock",
            model=None,
        )

        cleanup_old_story_analyses(story=self.story)

        self.assertTrue(
            models.StoryAnalysis.objects
            .filter(id=other_analysis.id)
            .exists()
        )

    def test_cleanup_with_single_analysis_deletes_nothing(self):
        """Cleanup should delete nothing if there is only one analysis."""
        self._create_analysis("hash-1")

        deleted_count = cleanup_old_story_analyses(story=self.story)

        self.assertEqual(deleted_count, 0)
        self.assertEqual(
            models.StoryAnalysis.objects.filter(story=self.story).count(),
            1,
        )

    def test_cleanup_rejects_invalid_keep_latest(self):
        """Cleanup should reject keep_latest values below 1."""
        with self.assertRaises(ValueError):
            cleanup_old_story_analyses(
                story=self.story,
                keep_latest=0,
            )

    def test_cleanup_can_keep_custom_number_of_analyses(self):
        """Cleanup can keep more analyses when keep_latest is provided."""
        analyses = [
            self._create_analysis(f"hash-{index}")
            for index in range(7)
        ]

        deleted_count = cleanup_old_story_analyses(
            story=self.story,
            keep_latest=5,
        )

        self.assertEqual(deleted_count, 2)

        remaining_ids = set(
            models.StoryAnalysis.objects
            .filter(story=self.story)
            .values_list("id", flat=True)
        )

        expected_remaining_ids = {
            analysis.id
            for analysis in analyses[-5:]
        }

        self.assertEqual(remaining_ids, expected_remaining_ids)
