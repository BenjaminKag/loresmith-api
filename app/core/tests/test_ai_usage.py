"""
Tests for AI usage tracking helpers.
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from core import models
from core.services import ai_client, ai_usage
from core.services.ai_client import DailyBudgetExceeded, LoreAIService


class AIUsageTests(TestCase):
    """Tests for AI usage tracking."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_record_ai_usage_creates_usage_log(self):
        """record_ai_usage should create an AIUsageLog."""
        meta = {
            "ai_mode": "live",
            "model": "test-model",
            "input_tokens": 100,
            "output_tokens": 40,
            "total_tokens": 140,
        }

        usage_log = ai_usage.record_ai_usage(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            meta=meta,
        )

        self.assertEqual(usage_log.owner, self.user)
        self.assertEqual(
            usage_log.endpoint_type,
            models.AIEndpointType.STORY_ANALYSIS,
        )
        self.assertEqual(usage_log.ai_mode, "live")
        self.assertEqual(usage_log.model, "test-model")
        self.assertEqual(usage_log.input_tokens, 100)
        self.assertEqual(usage_log.output_tokens, 40)
        self.assertEqual(usage_log.total_tokens, 140)
        self.assertEqual(models.AIUsageLog.objects.count(), 1)

    def test_record_ai_usage_defaults_missing_token_values_to_zero(self):
        """Missing token values should be stored as zero."""
        meta = {
            "ai_mode": "mock",
            "model": None,
        }

        usage_log = ai_usage.record_ai_usage(
            user=self.user,
            endpoint_type=models.AIEndpointType.CHARACTER_PROFILE,
            meta=meta,
        )

        self.assertEqual(usage_log.ai_mode, "mock")
        self.assertIsNone(usage_log.model)
        self.assertEqual(usage_log.input_tokens, 0)
        self.assertEqual(usage_log.output_tokens, 0)
        self.assertEqual(usage_log.total_tokens, 0)

    def test_record_ai_usage_can_link_to_request_log(self):
        """Usage log can be linked to an AI request log."""
        request_log = models.AIRequestLog.objects.create(
            owner=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            idempotency_key="abc123",
            content_hash="def456",
            status=models.AIRequestStatus.COMPLETED,
            request_payload={},
            response_payload={},
        )

        usage_log = ai_usage.record_ai_usage(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            meta={"ai_mode": "mock"},
            request_log=request_log,
        )

        self.assertEqual(usage_log.request_log, request_log)


@override_settings(
    LORESMITH_AI_ENABLED=True,
    OPENAI_API_KEY="test-key",
    LORESMITH_DAILY_TOKEN_BUDGET=1000,
    LORESMITH_USER_DAILY_TOKEN_BUDGET=100,
)
class DailyBudgetTests(TestCase):
    """Tests for global + per-user daily token budget enforcement."""

    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            email="budget@example.com",
            password="testpass123",
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="testpass123",
        )

    def tearDown(self):
        cache.clear()

    def test_check_daily_budget_passes_when_under_both_limits(self):
        """No exception is raised when both budgets have room."""
        service = LoreAIService(user=self.user)

        service._check_daily_budget()

    def test_check_daily_budget_skips_user_check_when_no_user(self):
        """With no user attached, only the global budget is checked."""
        service = LoreAIService(user=None)

        service._check_daily_budget()

    def test_check_daily_budget_raises_when_global_budget_exceeded(self):
        """Exceeding the global daily budget blocks every user."""
        ai_client.add_daily_tokens_used(1000)
        service = LoreAIService(user=self.user)

        with self.assertRaises(DailyBudgetExceeded):
            service._check_daily_budget()

    def test_check_daily_budget_raises_when_user_budget_exceeded(self):
        """Exceeding just the per-user budget blocks that user."""
        ai_client.add_user_daily_tokens_used(self.user.id, 100)
        service = LoreAIService(user=self.user)

        with self.assertRaises(DailyBudgetExceeded):
            service._check_daily_budget()

    def test_user_budget_exceeded_does_not_affect_other_users(self):
        """One user's exhausted budget leaves other users unaffected."""
        ai_client.add_user_daily_tokens_used(self.user.id, 100)

        other_service = LoreAIService(user=self.other_user)

        other_service._check_daily_budget()

    def test_generate_json_increments_both_global_and_user_counters(self):
        """A successful call adds its tokens to both counters."""
        service = LoreAIService(user=self.user)

        mock_response = mock.Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.choices = [
            mock.Mock(message=mock.Mock(content='{"ok": true}'))
        ]
        service.client = mock.Mock()
        service.client.chat.completions.create.return_value = mock_response

        service.generate_json("system prompt", "user prompt")

        self.assertEqual(ai_client.get_daily_tokens_used(), 15)
        self.assertEqual(
            ai_client.get_user_daily_tokens_used(self.user.id),
            15,
        )
