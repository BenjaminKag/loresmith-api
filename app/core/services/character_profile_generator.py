"""
Character profile generation service.

This service generates a suggested character profile from an existing
character. It does not save anything automatically.
"""
from core.services.ai_client import LoreAIService
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

        ai_service = LoreAIService()
        result = ai_service.generate_character_profile(character_data)

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
