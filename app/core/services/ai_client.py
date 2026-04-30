"""
AI service for LoreSmith.

This module wraps the OpenAI client, applies safety limits
(max chars, max tokens, daily budget), and returns a structured
analysis suitable for all entity types (story, character, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict
import logging

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
    Shared AI infrastructure service.

    Handles:
    - AI configuration
    - OpenAI client initialization
    - mock-mode detection
    - daily token budget checks
    - JSON-mode OpenAI calls
    - token usage tracking

    Feature-specific services are responsible for building prompts,
    mock responses, and normalizing outputs.
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
        Raise an error if AI is disabled or no API key is configured.

        Most current features use should_use_mock() instead, because they
        fall back to mock responses during development.
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

    # ---------- public API ----------

    def should_use_mock(self) -> bool:
        """Return whether feature services should use mock mode."""
        return not self.config.enabled or not self._has_key

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
    ) -> Dict[str, Any]:
        """
        Generate a JSON response from system/user prompts.

        Feature-specific services are responsible for:
        - building prompts
        - deciding when to use mock mode
        - normalizing the parsed response
        """
        if not self.config.enabled or not self._has_key:
            raise AiServiceError(
                "AI is disabled or OPENAI_API_KEY is not configured."
            )

        self._check_daily_budget()

        if not self.client:
            raise AiServiceError("AI client is not initialized.")

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self.config.max_output_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
        except OpenAIError as exc:
            logger.exception("OpenAI chat.completions failed")
            raise AiServiceError("AI generation failed.") from exc

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

        parsed = response.choices[0].message.parsed

        return {
            "data": parsed,
            "meta": {
                "ai_mode": "live",
                "model": self.config.model,
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        }
