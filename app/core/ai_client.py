"""
AI service for LoreSmith.

This module wraps the OpenAI client, applies safety limits
(max chars, max tokens, daily budget), and returns a structured
analysis suitable for all entity types (story, character, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
from typing import Any, Dict

from django.conf import settings
from django.core.cache import cache
from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)


@dataclass
class LoreAIConfig:
    enabled: bool
    model: str
    max_output_tokens: int
    max_input_chars: int
    daily_token_budget: int


class AiServiceError(RuntimeError):
    """Base error for AI service issues."""


class DailyBudgetExceeded(AiServiceError):
    """Raised when the global daily token budget is exceeded."""


def _get_config() -> LoreAIConfig:
    return LoreAIConfig(
        enabled=getattr(settings, "LORESMITH_AI_ENABLED", True),
        model=getattr(settings, "LORESMITH_AI_MODEL", "gpt-4.1-mini"),
        max_output_tokens=getattr(
            settings,
            "LORESMITH_MAX_OUTPUT_TOKENS",
            256,
        ),
        max_input_chars=getattr(
            settings,
            "LORESMITH_MAX_INPUT_CHARS",
            8000,
        ),
        daily_token_budget=getattr(
            settings,
            "LORESMITH_DAILY_TOKEN_BUDGET",
            200000,
        ),
    )


def _daily_token_key() -> str:
    return f"loresmith_ai_tokens_{date.today().isoformat()}"


def get_daily_tokens_used() -> int:
    return int(cache.get(_daily_token_key(), 0))


def add_daily_tokens_used(tokens: int) -> None:
    key = _daily_token_key()
    current = int(cache.get(key, 0))
    # expire after 24 hours
    cache.set(key, current + tokens, timeout=60 * 60 * 24)


class LoreAIService:
    """
    Main entrypoint for AI analysis.

    Usage:
        service = LoreAIService()
        result = service.analyze_text(full_text)

    Returns a dict with:
        summary, themes, tone, strengths, weaknesses, suggestions, meta
    """

    def __init__(self) -> None:
        self.config = _get_config()

        api_key = getattr(settings, "OPENAI_API_KEY", None)
        self._has_key = bool(api_key)
        self.client = OpenAI(api_key=api_key) if self._has_key else None

    # ---------- internal helpers ----------

    # pylint: disable=unused-private-member
    def _check_enabled(self) -> None:
        """
        Ensure AI is enabled and API key is configured.
        Currently unused because analyze_text handles mock-mode fallback.
        Retained for future versions where strict enforcement may return.
        """
        if not self.config.enabled:
            raise AiServiceError(
                "AI is disabled. Set LORESMITH_AI_ENABLED=true to enable."
            )
        if not self._has_key:
            raise AiServiceError(
                "OPENAI_API_KEY is not configured. "
                "Set it in your environment to enable AI."
            )

    def _check_daily_budget(self) -> None:
        """
        Ensure daily token budget is not exceeded.
        """
        used = get_daily_tokens_used()
        if used >= self.config.daily_token_budget:
            logger.warning(
                "LoreAI daily token budget exceeded. used=%s budget=%s",
                used,
                self.config.daily_token_budget,
            )
            raise DailyBudgetExceeded(
                "AI daily token budget exceeded. Try again tomorrow."
            )

    def _build_prompt(self, text: str) -> Dict[str, Any]:
        """
        Build system/user messages for the model.
        """

        system_prompt = (
            "You are LoreSmith, an assistant that analyzes worldbuilding "
            "content (stories, characters, locations, factions, items). "
            "You MUST respond with a single JSON object only. "
            "Do not include any explanation outside of JSON.\n\n"
            "The JSON object must have these keys:\n"
            "- summary (string)\n"
            "- themes (array of strings)\n"
            "- tone (string)\n"
            "- strengths (array of strings)\n"
            "- weaknesses (array of strings)\n"
            "- suggestions (array of strings)\n\n"
            "Keep summaries concise and spoiler-light. Do not invent new lore."
        )

        user_prompt = (
            "Analyze the following lore content and fill the JSON fields.\n\n"
            "Lore content:\n"
            "----------------------\n"
            f"{text}"
        )

        return {
            "system": system_prompt,
            "user": user_prompt,
        }

    def _mock_response(self, text: str) -> Dict[str, Any]:
        """
        Cheap, local fake analysis used only to support a 'mock' mode.
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
            "meta": {
                "ai_mode": "mock",
                "model": None,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
            "snippet": snippet,
        }

    # ---------- public API ----------

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze arbitrary lore text and return a structured dict.

        The caller (view) is responsible for attaching entity_type,
        entity_id, etc., on top of this result.
        """
        text = (text or "").strip()
        if not text:
            raise AiServiceError("No content provided for analysis.")

        # enforce character limit before sending to the model
        if len(text) > self.config.max_input_chars:
            text = text[: self.config.max_input_chars]

        if not self.config.enabled or not self._has_key:
            logger.info(
                "Using mock AI response "
                "(AI disabled or missing OPENAI_API_KEY)."
            )
            return self._mock_response(text)

        # From here on: REAL OpenAI path only
        self._check_daily_budget()

        if not self.client:
            # Should not happen if config is correct, but safety net
            raise AiServiceError("AI client is not initialized.")

        prompts = self._build_prompt(text)

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]},
                ],
                max_tokens=self.config.max_output_tokens,
                temperature=0.4,
                response_format={"type": "json_object"},
            )
        except OpenAIError as exc:
            logger.exception("OpenAI chat.completions failed")
            raise AiServiceError("AI analysis failed.") from exc

        # usage info
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)

        if total_tokens is not None:
            add_daily_tokens_used(total_tokens)
            logger.info(
                "LoreAI call model=%s prompt=%s completion=%s total=%s "
                "daily_used=%s budget=%s",
                self.config.model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                get_daily_tokens_used(),
                self.config.daily_token_budget,
            )

        # JSON-mode parsed response
        parsed = response.choices[0].message.parsed

        # Build final result with meta
        result: Dict[str, Any] = {
            "summary": parsed.get("summary", "").strip(),
            "themes": parsed.get("themes", []),
            "tone": parsed.get("tone", "").strip(),
            "strengths": parsed.get("strengths", []),
            "weaknesses": parsed.get("weaknesses", []),
            "suggestions": parsed.get("suggestions", []),
            "meta": {
                "ai_mode": "live",
                "model": self.config.model,
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        }

        return result
