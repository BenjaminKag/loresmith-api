from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core import models
from core.services.ai_client import AiServiceError
from core.services.story_analysis_generator import StoryAnalysisGenerator


def create_user(email="test@example.com", password="testpass123", **extra):
    """Create and return a user."""
    return get_user_model().objects.create_user(email, password, **extra)


def create_story(owner, **params):
    """Create and return a story."""
    defaults = {
        "title": "The Fallen Kingdom",
        "summary": "A kingdom falls after a betrayal.",
        "body": "The prince discovers the truth behind the war.",
        "owner": owner,
    }
    defaults.update(params)
    return models.Story.objects.create(**defaults)


class StoryAnalysisGeneratorTests(TestCase):
    """Tests for StoryAnalysisGenerator service behavior."""

    def setUp(self):
        self.user = create_user()
        self.generator = StoryAnalysisGenerator()

    def test_build_story_text_includes_title_summary_and_body(self):
        """Story text should include title, summary and body."""
        story = create_story(owner=self.user)

        text = self.generator._build_story_text(story)

        self.assertIn("The Fallen Kingdom", text)
        self.assertIn("A kingdom falls after a betrayal.", text)
        self.assertIn("The prince discovers the truth behind the war.", text)

    def test_build_story_text_ignores_empty_summary_or_body_parts(self):
        """Story text should still work when one content field is empty."""
        story = create_story(
            owner=self.user,
            summary="",
            body="Only body content.",
        )

        text = self.generator._build_story_text(story)

        self.assertIn("The Fallen Kingdom", text)
        self.assertIn("Only body content.", text)

    def test_build_story_text_raises_error_when_no_content(self):
        """Story text should fail when summary and body are empty."""
        story = create_story(
            owner=self.user,
            summary="   ",
            body="",
        )

        with self.assertRaises(AiServiceError):
            self.generator._build_story_text(story)

    @override_settings(
        LORESMITH_AI_ENABLED=False,
        OPENAI_API_KEY="",
    )
    def test_generate_uses_mock_response_when_ai_disabled(self):
        """Generator should use mock response when AI is disabled."""
        story = create_story(owner=self.user)

        result = self.generator.generate(story)

        self.assertEqual(result["meta"]["ai_mode"], "mock")
        self.assertEqual(result["meta"]["story_id"], story.id)
        self.assertEqual(result["meta"]["story_title"], story.title)
        self.assertIn("analysis_id", result["meta"])
        self.assertEqual(result["meta"]["cached"], False)
        self.assertIn("summary", result)
        self.assertIn("themes", result)
        self.assertIn("tone", result)
        self.assertIn("strengths", result)
        self.assertIn("weaknesses", result)
        self.assertIn("suggestions", result)
        self.assertIn("consistency_notes", result)
        self.assertIn("open_questions", result)
        self.assertEqual(len(result["consistency_notes"]), 1)
        self.assertEqual(len(result["open_questions"]), 1)

    @override_settings(
        LORESMITH_AI_ENABLED=True,
        OPENAI_API_KEY="test-key",
    )
    @mock.patch("core.services.story_analysis_generator.LoreAIService")
    def test_generate_calls_ai_service_and_normalizes_live_response(
        self,
        mock_ai_service_cls,
    ):
        """Generator should call LoreAIService and normalize live output."""
        story = create_story(owner=self.user)

        mock_ai_service = mock_ai_service_cls.return_value
        mock_ai_service.should_use_mock.return_value = False
        mock_ai_service.generate_json.return_value = {
            "data": {
                "summary": "Live summary",
                "themes": ["betrayal", "war"],
                "tone": "tragic",
                "strengths": ["Strong conflict"],
                "weaknesses": ["Unclear motivation"],
                "suggestions": ["Clarify the prince's goal"],
                "consistency_notes": ["No contradictions found."],
                "open_questions": ["What caused the betrayal?"],
            },
            "meta": {
                "ai_mode": "live",
                "model": "test-model",
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
            },
        }

        result = self.generator.generate(story)

        self.assertEqual(result["summary"], "Live summary")
        self.assertEqual(result["themes"], ["betrayal", "war"])
        self.assertEqual(result["tone"], "tragic")
        self.assertEqual(result["strengths"], ["Strong conflict"])
        self.assertEqual(result["weaknesses"], ["Unclear motivation"])
        self.assertEqual(result["suggestions"], ["Clarify the prince's goal"])
        self.assertEqual(
            result["consistency_notes"],
            ["No contradictions found."],
        )
        self.assertEqual(
            result["open_questions"],
            ["What caused the betrayal?"],
        )
        self.assertEqual(result["meta"]["ai_mode"], "live")
        self.assertEqual(result["meta"]["story_id"], story.id)
        self.assertEqual(result["meta"]["story_title"], story.title)

        mock_ai_service.generate_json.assert_called_once()

    def test_normalize_response_uses_defaults_for_missing_fields(self):
        """Missing AI fields should be normalized to safe defaults."""
        result = self.generator._normalize_response(
            parsed={},
            meta={"ai_mode": "live"},
        )

        self.assertEqual(result["summary"], "")
        self.assertEqual(result["themes"], [])
        self.assertEqual(result["tone"], "")
        self.assertEqual(result["strengths"], [])
        self.assertEqual(result["weaknesses"], [])
        self.assertEqual(result["suggestions"], [])
        self.assertEqual(result["meta"], {"ai_mode": "live"})
        self.assertEqual(result["consistency_notes"], [])
        self.assertEqual(result["open_questions"], [])

    @override_settings(
        LORESMITH_AI_ENABLED=False,
        OPENAI_API_KEY="",
    )
    def test_generate_creates_story_analysis_record(self):
        """Fresh analysis should save a StoryAnalysis record."""
        story = create_story(owner=self.user)

        result = self.generator.generate(story)

        analysis = models.StoryAnalysis.objects.get(story=story)

        self.assertEqual(analysis.owner, self.user)
        self.assertEqual(analysis.ai_mode, "mock")
        self.assertIsNone(analysis.model)
        self.assertEqual(result["meta"]["cached"], False)
        self.assertEqual(result["meta"]["analysis_id"], analysis.id)

    @override_settings(
        LORESMITH_AI_ENABLED=False,
        OPENAI_API_KEY="",
    )
    def test_generate_returns_cached_analysis_for_same_input(self):
        """Second analysis with same story input should use cached result."""
        story = create_story(owner=self.user)

        first_result = self.generator.generate(story)
        second_result = self.generator.generate(story)

        self.assertEqual(models.StoryAnalysis.objects.count(), 1)
        self.assertEqual(
            first_result["meta"]["analysis_id"],
            second_result["meta"]["analysis_id"]
        )
        self.assertEqual(first_result["meta"]["cached"], False)
        self.assertEqual(second_result["meta"]["cached"], True)

    @override_settings(
        LORESMITH_AI_ENABLED=False,
        OPENAI_API_KEY="",
    )
    def test_generate_creates_new_analysis_when_story_changes(self):
        """Changing story content should create a new analysis record."""
        story = create_story(owner=self.user)

        first_result = self.generator.generate(story)

        story.body = "The story has changed."
        story.save()

        second_result = self.generator.generate(story)

        self.assertEqual(models.StoryAnalysis.objects.count(), 1)
        self.assertNotEqual(
            first_result["meta"]["analysis_id"],
            second_result["meta"]["analysis_id"],
        )
        self.assertEqual(second_result["meta"]["cached"], False)

    @override_settings(
        LORESMITH_AI_ENABLED=False,
        OPENAI_API_KEY="",
    )
    def test_part_story_analysis_hash_changes_if_parent_summary_changes(self):
        """Part story analysis should change when parent context changes."""
        parent = create_story(
            owner=self.user,
            title="Main Story",
            summary="Original parent summary.",
            body="Parent body.",
            kind=models.Story.Kind.STORY,
        )
        part = create_story(
            owner=self.user,
            title="Chapter One",
            summary="Part summary.",
            body="Part body.",
            parent=parent,
            kind=models.Story.Kind.PART,
        )

        first_result = self.generator.generate(part)

        parent.summary = "Updated parent summary."
        parent.save()

        second_result = self.generator.generate(part)

        self.assertEqual(models.StoryAnalysis.objects.count(), 1)
        self.assertNotEqual(
            first_result["meta"]["analysis_id"],
            second_result["meta"]["analysis_id"],
        )
        self.assertEqual(second_result["meta"]["cached"], False)
