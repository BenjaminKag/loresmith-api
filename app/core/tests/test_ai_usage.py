"""
Tests for AI usage tracking helpers.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from core import models
from core.services import ai_usage


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
