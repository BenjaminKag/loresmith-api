"""
Tests for AI character profile generation.
"""

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import override_settings, TestCase

from rest_framework.test import APITestCase
from rest_framework import status

from core import models
from core.services.ai_client import AiServiceError
from core.services.character_profile_generator import CharacterProfileGenerator

from unittest import mock
import uuid


def generate_profile_url(character_id):
    """Create and return the character generate-profile URL."""
    return reverse("character-generate-profile", args=[character_id])


def create_user(email=None, password="testpass123", **extra):
    """Create and return a user."""
    if email is None:
        email = f"test_{uuid.uuid4().hex}@example.com"

    return get_user_model().objects.create_user(email, password, **extra)


class CharacterProfileGenerationApiTests(APITestCase):
    """Tests for generating character profiles with AI."""

    def setUp(self):
        self.user = create_user(email="test@example.com")
        self.client.force_authenticate(self.user)

    def test_owner_can_generate_profile(self):
        """Owner can generate a suggested profile for their character."""
        trait_set = models.TraitSet.objects.create(
            name="Physical",
            owner=self.user,
        )
        trait = models.Trait.objects.create(
            trait_set=trait_set,
            label="Age",
        )

        character = models.Character.objects.create(
            name="Xiao",
            description="A vigilant yaksha.",
            owner=self.user,
        )
        character.profile_trait_sets.set([trait_set])

        url = generate_profile_url(character.id)
        res = self.client.post(url, {}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("profile", res.data)
        self.assertIn("meta", res.data)
        self.assertEqual(res.data["meta"]["ai_mode"], "mock")
        self.assertEqual(
            res.data["profile"]["physical"],
            {
                trait.key: "Medium",
            },
        )

    def test_other_user_cannot_generate_profile_for_private_character(self):
        """
        Users cannot generate profiles for private characters they do not own.
        """
        other_user = create_user(email="other@example.com")
        character = models.Character.objects.create(
            name="Hidden Character",
            owner=other_user,
        )

        url = generate_profile_url(character.id)
        res = self.client.post(url, {}, format="json")

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_generated_profile_only_uses_selected_trait_sets(self):
        """
        Generated profile should only use traits from selected trait sets.
        """
        physical = models.TraitSet.objects.create(
            name="Physical",
            owner=self.user,
        )
        magic = models.TraitSet.objects.create(
            name="Magic",
            owner=self.user,
        )

        age = models.Trait.objects.create(
            trait_set=physical,
            label="Age",
        )
        models.Trait.objects.create(
            trait_set=magic,
            label="Element",
        )

        character = models.Character.objects.create(
            name="Xiao",
            description="A vigilant yaksha.",
            owner=self.user,
        )
        character.profile_trait_sets.set([physical])

        url = generate_profile_url(character.id)
        res = self.client.post(url, {}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertIn("physical", res.data["profile"])
        self.assertNotIn("magic", res.data["profile"])
        self.assertEqual(
            res.data["profile"]["physical"][age.key],
            "Medium",
        )

    def test_generate_profile_does_not_save_profile(self):
        """Generating a profile should not automatically persist it."""
        trait_set = models.TraitSet.objects.create(
            name="Physical",
            owner=self.user,
        )
        models.Trait.objects.create(
            trait_set=trait_set,
            label="Age",
        )

        character = models.Character.objects.create(
            name="Xiao",
            owner=self.user,
        )
        character.profile_trait_sets.set([trait_set])

        url = generate_profile_url(character.id)
        res = self.client.post(url, {}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(
            models.CharacterProfile.objects.filter(
                character=character,
            ).exists()
        )

    def test_user_cannot_generate_profile_for_others_public_character(self):
        """
        Users cannot generate profile suggestions
        for characters they do not own, even if the character is public.
        """
        other_user = create_user(email="other@example.com")

        character = models.Character.objects.create(
            name="Public Character",
            description="This character belongs to another user.",
            owner=other_user,
        )

        story = models.Story.objects.create(
            title="Public Story",
            visibility=models.Story.Visibility.PUBLIC,
            owner=other_user,
        )
        story.characters.add(character)

        url = generate_profile_url(character.id)
        res = self.client.post(url, {}, format="json")

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        self.assertFalse(
            models.CharacterProfile.objects.filter(
                character=character,
            ).exists()
        )

    def test_generate_profile_handles_long_description(self):
        """Long descriptions should not break profile generation."""
        trait_set = models.TraitSet.objects.create(
            name="Physical",
            owner=self.user,
        )
        trait = models.Trait.objects.create(
            trait_set=trait_set,
            label="Age",
        )

        character = models.Character.objects.create(
            name="Xiao",
            description="Very long description. " * 1000,
            owner=self.user,
        )
        character.profile_trait_sets.set([trait_set])

        url = generate_profile_url(character.id)
        res = self.client.post(url, {}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res.data["profile"]["physical"],
            {
                trait.key: "Medium",
            },
        )
        self.assertEqual(res.data["meta"]["ai_mode"], "mock")

    def test_generate_profile_with_no_trait_sets_returns_400(self):
        """Generating profile without selected trait sets should return 400."""
        character = models.Character.objects.create(
            name="Xiao",
            description="A vigilant yaksha.",
            owner=self.user,
        )

        url = generate_profile_url(character.id)
        res = self.client.post(url, {}, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data["detail"],
            "No trait sets provided for profile generation.",
        )


class CharacterProfileGeneratorServiceTests(TestCase):
    """Tests for CharacterProfileGenerator service behavior."""

    def setUp(self):
        self.user = create_user(email="service@example.com")
        self.generator = CharacterProfileGenerator()

    def _create_character_with_trait_set(self):
        """Create a character with one selected trait set."""
        trait_set = models.TraitSet.objects.create(
            name="Physical",
            owner=self.user,
        )
        trait = models.Trait.objects.create(
            trait_set=trait_set,
            label="Age",
        )

        character = models.Character.objects.create(
            name="Xiao",
            description="A vigilant yaksha.",
            owner=self.user,
        )
        character.profile_trait_sets.set([trait_set])

        return character, trait_set, trait

    def test_generate_raises_error_when_no_trait_sets(self):
        """Generator should fail when character has no selected trait sets."""
        character = models.Character.objects.create(
            name="Xiao",
            description="A vigilant yaksha.",
            owner=self.user,
        )

        with self.assertRaises(AiServiceError):
            self.generator.generate(character)

    @override_settings(
        LORESMITH_AI_ENABLED=False,
        OPENAI_API_KEY="",
    )
    def test_generate_uses_mock_response_when_ai_disabled(self):
        """Generator should use mock response when AI is disabled."""
        character, _trait_set, trait = self._create_character_with_trait_set()

        result = self.generator.generate(character)

        self.assertEqual(result["meta"]["ai_mode"], "mock")
        self.assertEqual(result["meta"]["include_story_context"], False)
        self.assertEqual(
            result["profile"]["physical"],
            {
                trait.key: "Medium",
            },
        )

    @override_settings(
        LORESMITH_AI_ENABLED=True,
        OPENAI_API_KEY="test-key",
    )
    @mock.patch("core.services.character_profile_generator.LoreAIService")
    def test_generate_calls_ai_service_and_normalizes_live_response(
        self,
        mock_ai_service_cls,
    ):
        """Generator should call LoreAIService and normalize live output."""
        character, _trait_set, trait = self._create_character_with_trait_set()

        mock_ai_service = mock_ai_service_cls.return_value
        mock_ai_service.config.max_input_chars = 8000
        mock_ai_service.should_use_mock.return_value = False
        mock_ai_service.generate_json.return_value = {
            "data": {
                "profile": {
                    "physical": {
                        trait.key: "Ancient",
                    },
                },
            },
            "meta": {
                "ai_mode": "live",
                "model": "test-model",
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
            },
        }

        result = self.generator.generate(
            character,
            include_story_context=True,
        )

        self.assertEqual(
            result["profile"]["physical"][trait.key],
            "Ancient",
        )
        self.assertEqual(result["meta"]["ai_mode"], "live")
        self.assertEqual(result["meta"]["include_story_context"], True)
        self.assertEqual(
            result["meta"]["notes"],
            "Generated character profile suggestion.",
        )

        mock_ai_service.generate_json.assert_called_once()

    def test_normalize_response_uses_default_empty_profile(self):
        """Missing profile field should normalize to an empty profile."""
        result = self.generator._normalize_response(
            parsed={},
            meta={"ai_mode": "live"},
        )

        self.assertEqual(result["profile"], {})
        self.assertEqual(result["meta"], {"ai_mode": "live"})

    def test_truncate_character_data_shortens_long_description(self):
        """Long character descriptions should be truncated."""
        character_data = {
            "name": "Xiao",
            "description": "A" * 1000,
            "allowed_trait_sets": [],
        }

        result = self.generator._truncate_character_data(
            character_data,
            max_input_chars=100,
        )

        self.assertEqual(len(result["description"]), 60)
