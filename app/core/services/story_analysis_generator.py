"""
Story analysis generation service.

This service generates structured AI analysis for an existing story.
It stores the latest StoryAnalysis record for caching, and removes older
analysis records according to the cleanup policy.
"""
from typing import Any, Dict
import hashlib

from core.services.ai_client import LoreAIService, AiServiceError
from core.services.story_analysis_cleanup import cleanup_old_story_analyses
from core import models


class StoryAnalysisGenerator:
    """Generate structured analysis for an existing story."""

    def generate(self, story, user=None) -> Dict[str, Any]:
        """Generate AI analysis for a story."""
        text = self._build_story_text(story)
        input_hash = self._build_input_hash(text)

        cached_analysis = self._get_cached_analysis(story, input_hash)
        if cached_analysis:
            return self._build_cached_response(cached_analysis)

        ai_service = LoreAIService(user=user)

        if ai_service.should_use_mock():
            result = self._mock_response(text)
        else:
            prompts = self._build_prompt(text)
            ai_result = ai_service.generate_json(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                temperature=0.4,
            )
            result = self._normalize_response(
                ai_result["data"],
                ai_result["meta"],
            )

        response_data = self._build_response_data(
            story=story,
            result=result,
            input_hash=input_hash,
        )

        analysis_record = models.StoryAnalysis.objects.create(
            story=story,
            owner=story.owner,
            input_hash=input_hash,
            result=response_data,
            ai_mode=response_data["meta"].get("ai_mode", ""),
            model=response_data["meta"].get("model"),
        )

        cleanup_old_story_analyses(story=story)

        response_data["meta"]["cached"] = False
        response_data["meta"]["analysis_id"] = analysis_record.id

        return response_data

    def _build_story_text(self, story) -> str:
        """Build AI-friendly text from the story."""
        data_parts = [
            story.summary or "",
            story.body or "",
        ]

        data = "\n\n".join(
            part.strip()
            for part in data_parts
            if part and part.strip()
        )

        if not data:
            raise AiServiceError(
                "No content provided for analysis."
            )

        sections = []

        parent = getattr(story, "parent", None)
        if parent:
            parent_parts = [
                f"Parent story title: {parent.title}",
            ]

            if parent.summary and parent.summary.strip():
                parent_parts.append(
                    f"Parent story summary: {parent.summary.strip()}"
                )

            sections.append(
                "Parent context:\n"
                + "\n".join(parent_parts)
            )

        sections.append(
            "Current story:\n"
            f"Title: {story.title.strip()}\n\n"
            f"{data}"
        )

        return "\n\n".join(sections)

    def _build_prompt(self, text: str) -> Dict[str, str]:
        """Build system/user messages for story analysis."""
        system_prompt = (
            "You are LoreSmith, an assistant that analyzes worldbuilding "
            "story content. "
            "You MUST respond with a single JSON object only. "
            "Do not include any explanation outside of JSON.\n\n"
            "The JSON object must have these keys:\n"
            "- summary (string)\n"
            "- themes (array of strings)\n"
            "- tone (string)\n"
            "- strengths (array of strings)\n"
            "- weaknesses (array of strings)\n"
            "- suggestions (array of strings)\n"
            "- consistency_notes (array of strings)\n"
            "- open_questions (array of strings)\n\n"
            "Keep summaries concise and spoiler-light. "
            "Do not invent new lore."
            "If something is unclear, add it to open_questions "
            "instead of inventing details."
        )

        user_prompt = (
            "Analyze the following story content and fill the JSON fields.\n\n"
            "Story content:\n"
            "----------------------\n"
            f"{text}"
        )

        return {
            "system": system_prompt,
            "user": user_prompt,
        }

    def _mock_response(self, text: str) -> Dict[str, Any]:
        """
        Cheap, local fake analysis used only to support mock mode.
        """
        snippet = (text[:200] + "...") if len(text) > 200 else text

        return {
            "summary": "AI is not available. This is a placeholder summary.",
            "themes": ["mock-theme"],
            "tone": "neutral",
            "strengths": [
                "Mock analysis enabled so development can proceed "
                "without real AI calls."
            ],
            "weaknesses": [
                "This feedback is not based on the actual content."
            ],
            "suggestions": [
                "Configure OPENAI_API_KEY and LORESMITH_AI_ENABLED=true "
                "to enable real analysis."
            ],
            "consistency_notes": [
                "Mock analysis does not inspect the actual "
                "story for consistency."
            ],
            "open_questions": [
                "What story details should be clarified before "
                "live AI analysis?"
            ],
            "meta": {
                "ai_mode": "mock",
                "model": None,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
            "snippet": snippet,
        }

    def _normalize_response(
        self,
        parsed: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalize AI response into the expected story analysis shape."""
        return {
            "summary": parsed.get("summary", "").strip(),
            "themes": parsed.get("themes", []),
            "tone": parsed.get("tone", "").strip(),
            "strengths": parsed.get("strengths", []),
            "weaknesses": parsed.get("weaknesses", []),
            "suggestions": parsed.get("suggestions", []),
            "consistency_notes": parsed.get("consistency_notes", []),
            "open_questions": parsed.get("open_questions", []),
            "meta": meta,
        }

    def _build_input_hash(self, text: str) -> str:
        """Build a stable hash for the exact AI input text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _get_cached_analysis(self, story, input_hash: str):
        """Return cached analysis for the same story input, if it exists."""
        return (
            models.StoryAnalysis.objects
            .filter(
                story=story,
                owner=story.owner,
                input_hash=input_hash,
            )
            .first()
        )

    def _build_cached_response(self, analysis_record) -> Dict[str, Any]:
        """Build response data from a cached StoryAnalysis record."""
        response_data = dict(analysis_record.result)
        meta = dict(response_data.get("meta", {}))

        meta["cached"] = True
        meta["analysis_id"] = analysis_record.id

        response_data["meta"] = meta

        return response_data

    def _build_response_data(
        self,
        story,
        result: Dict[str, Any],
        input_hash: str,
    ) -> Dict[str, Any]:
        """Build final story analysis response data."""
        return {
            "summary": result["summary"],
            "themes": result["themes"],
            "tone": result["tone"],
            "strengths": result["strengths"],
            "weaknesses": result["weaknesses"],
            "suggestions": result["suggestions"],
            "consistency_notes": result["consistency_notes"],
            "open_questions": result["open_questions"],
            "meta": {
                **result["meta"],
                "story_id": story.id,
                "story_title": story.title,
                "notes": "Generated story analysis.",
            },
        }
