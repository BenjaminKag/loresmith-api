"""
Character profile generation service.

This service generates a suggested character profile from an existing
character. It does not save anything automatically.
"""
from typing import Any, Dict
import json

from core.services.ai_client import LoreAIService, AiServiceError
from core.models import slugify_underscore


class CharacterProfileGenerator:
    """Generate suggested profile data for an existing character."""

    def generate(self, character, include_story_context=False):
        """
        Generate a suggested character profile.
            - character: Character instance to analyze
            - include_story_context:
                Whether to include story context in the analysis
        """
        allowed_trait_sets = self._build_allowed_trait_sets(character)

        character_data = {
            "name": character.name,
            "description": character.description,
            "allowed_trait_sets": allowed_trait_sets,
            "include_story_context": include_story_context,
        }

        if not character_data.get("allowed_trait_sets"):
            raise AiServiceError(
                "No trait sets provided for profile generation."
            )

        ai_service = LoreAIService()
        character_data = self._truncate_character_data(
            character_data,
            ai_service.config.max_input_chars,
        )

        if ai_service.should_use_mock():
            result = self._mock_response(character_data)
        else:
            prompts = self._build_prompt(character_data)
            ai_result = ai_service.generate_json(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                temperature=0.3,
            )
            result = self._normalize_response(
                ai_result["data"],
                ai_result["meta"],
            )

        return {
            "profile": result["profile"],
            "meta": {
                **result["meta"],
                "include_story_context": include_story_context,
                "notes": "Generated character profile suggestion.",
            },
        }

    def _build_allowed_trait_sets(self, character):
        """
        Build an AI-friendly list of selected trait sets and their traits.
        """
        selected_trait_sets = character.profile_trait_sets.prefetch_related(
            "traits"
        )

        return [
            {
                "key": slugify_underscore(trait_set.name),
                "label": trait_set.name,
                "traits": [
                    {
                        "key": trait.key,
                        "label": trait.label,
                    }
                    for trait in trait_set.traits.all()
                ],
            }
            for trait_set in selected_trait_sets
        ]

    def _build_prompt(
        self,
        character_data: Dict[str, Any],
    ) -> Dict[str, str]:
        """Build system/user messages for character profile generation."""
        system_prompt = (
            "You are LoreSmith, a worldbuilding assistant.\n"
            "Generate a structured character profile from "
            "the provided character data.\n\n"
            "Rules:\n"
            "- Return ONLY a single JSON object.\n"
            "- Do not include explanations outside JSON.\n"
            "- Do not invent trait keys.\n"
            "- Use ONLY the allowed trait keys provided.\n"
            "- If the description does not contain "
            "enough information for a trait, "
            "use a reasonable concise value like 'Unknown', "
            "'Unclear', or 'Not specified'.\n\n"
            "The JSON object must match this structure:\n"
            "{\n"
            '  "profile": {\n'
            '    "trait_set_slug": {\n'
            '      "trait_key": "value"\n'
            "    }\n"
            "  }\n"
            "}"
        )

        user_prompt = (
            "Generate a character profile for this character.\n\n"
            f"{json.dumps(character_data, indent=2)}"
        )

        return {
            "system": system_prompt,
            "user": user_prompt,
        }

    def _mock_response(
        self,
        character_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Return a mock character profile using only allowed trait keys."""
        profile = {}

        for trait_set in character_data.get("allowed_trait_sets", []):
            set_key = trait_set["key"]

            profile[set_key] = {
                trait["key"]: "Medium"
                for trait in trait_set.get("traits", [])
            }

        return {
            "profile": profile,
            "meta": {
                "ai_mode": "mock",
                "model": None,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }

    def _truncate_character_data(
        self,
        character_data: Dict[str, Any],
        max_input_chars: int,
    ) -> Dict[str, Any]:
        """
        Truncate large fields like description to stay within limits.
        """
        data_copy = dict(character_data)

        # Reserve space for other fields: traits, JSON, metadata, etc.
        description_limit = int(max_input_chars * 0.6)

        description = data_copy.get("description", "")
        if description and len(description) > description_limit:
            data_copy["description"] = description[:description_limit]

        return data_copy

    def _normalize_response(
        self,
        parsed: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalize AI response into the expected profile shape."""
        return {
            "profile": parsed.get("profile", {}),
            "meta": meta,
        }
