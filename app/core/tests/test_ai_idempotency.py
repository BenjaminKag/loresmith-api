"""
Tests for AI idempotency helpers.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from core import models
from core.services import ai_idempotency


class AIIdempotencyTests(TestCase):
    """Tests for AI idempotency helper functions."""

    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.payload = {
            "story_id": 1,
            "input_hash": "abc123",
            "settings": {
                "model": "mock",
                "force_refresh": False,
            },
        }

    def test_normalize_payload_is_stable_for_key_order(self):
        """Same logical payload should normalize to the same value."""
        payload_a = {
            "story_id": 1,
            "input_hash": "abc123",
            "settings": {
                "model": "mock",
                "force_refresh": False,
            },
        }
        payload_b = {
            "settings": {
                "force_refresh": False,
                "model": "mock",
            },
            "input_hash": "abc123",
            "story_id": 1,
        }

        self.assertEqual(
            ai_idempotency.normalize_payload(payload_a),
            ai_idempotency.normalize_payload(payload_b),
        )

    def test_build_content_hash_is_stable_for_same_payload(self):
        """Same logical payload should produce the same content hash."""
        payload_a = {
            "story_id": 1,
            "input_hash": "abc123",
        }
        payload_b = {
            "input_hash": "abc123",
            "story_id": 1,
        }

        self.assertEqual(
            ai_idempotency.build_content_hash(payload_a),
            ai_idempotency.build_content_hash(payload_b),
        )

    def test_build_content_hash_changes_for_different_payload(self):
        """Different payloads should produce different content hashes."""
        payload_a = {
            "story_id": 1,
            "input_hash": "abc123",
        }
        payload_b = {
            "story_id": 2,
            "input_hash": "abc123",
        }

        self.assertNotEqual(
            ai_idempotency.build_content_hash(payload_a),
            ai_idempotency.build_content_hash(payload_b),
        )

    def test_build_idempotency_key_includes_user(self):
        """Different users should produce different idempotency keys."""
        content_hash = ai_idempotency.build_content_hash(self.payload)

        key_a = ai_idempotency.build_idempotency_key(
            user_id=1,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            content_hash=content_hash,
        )
        key_b = ai_idempotency.build_idempotency_key(
            user_id=2,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            content_hash=content_hash,
        )

        self.assertNotEqual(key_a, key_b)

    def test_create_in_progress_request_creates_log(self):
        """Creating an AI request should create an in-progress log."""
        request_log, created = ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            request_payload=self.payload,
        )

        self.assertTrue(created)
        self.assertEqual(request_log.owner, self.user)
        self.assertEqual(
            request_log.endpoint_type,
            models.AIEndpointType.STORY_ANALYSIS,
        )
        self.assertEqual(
            request_log.status,
            models.AIRequestStatus.IN_PROGRESS,
        )
        self.assertEqual(request_log.request_payload, self.payload)
        self.assertEqual(models.AIRequestLog.objects.count(), 1)

    def test_duplicate_in_progress_request_raises_error(self):
        """Duplicate in-progress request should not create another log."""
        ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            request_payload=self.payload,
        )

        with self.assertRaises(ai_idempotency.AIRequestInProgress):
            ai_idempotency.create_in_progress_request(
                user=self.user,
                endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
                request_payload=self.payload,
            )

        self.assertEqual(models.AIRequestLog.objects.count(), 1)

    def test_recent_completed_duplicate_returns_existing_log(self):
        """Recent completed request should be reused."""
        request_log, _ = ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            request_payload=self.payload,
        )

        response_payload = {
            "summary": "Cached result",
            "meta": {"cached": False},
        }

        ai_idempotency.mark_request_completed(
            request_log,
            response_payload,
        )

        duplicate_log, created = ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            request_payload=self.payload,
        )

        self.assertFalse(created)
        self.assertEqual(duplicate_log.id, request_log.id)
        self.assertEqual(duplicate_log.response_payload, response_payload)
        self.assertEqual(models.AIRequestLog.objects.count(), 1)

    def test_mark_request_completed_updates_log(self):
        """Completed request should store response payload and timestamp."""
        request_log, _ = ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.CHARACTER_PROFILE,
            request_payload=self.payload,
        )

        response_payload = {
            "profile": {"physical_traits": {"age": "25"}},
        }

        updated_log = ai_idempotency.mark_request_completed(
            request_log,
            response_payload,
        )

        self.assertEqual(
            updated_log.status,
            models.AIRequestStatus.COMPLETED,
        )
        self.assertEqual(updated_log.response_payload, response_payload)
        self.assertIsNotNone(updated_log.completed_at)

    def test_mark_request_failed_updates_log(self):
        """Failed request should store error details."""
        request_log, _ = ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.CHARACTER_PROFILE,
            request_payload=self.payload,
        )

        updated_log = ai_idempotency.mark_request_failed(
            request_log,
            "Something went wrong.",
        )

        self.assertEqual(
            updated_log.status,
            models.AIRequestStatus.FAILED,
        )
        self.assertEqual(
            updated_log.error_message,
            "Something went wrong.",
        )

    def test_old_completed_request_is_not_reused_by_recent_lookup(self):
        """
        Completed request outside the dedupe window should not count as recent.
        """
        request_log, _ = ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            request_payload=self.payload,
        )

        ai_idempotency.mark_request_completed(
            request_log,
            {"summary": "Old result"},
        )

        old_time = timezone.now() - timezone.timedelta(minutes=30)

        models.AIRequestLog.objects.filter(id=request_log.id).update(
            completed_at=old_time,
        )

        recent_log = ai_idempotency.get_recent_completed_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            content_hash=request_log.content_hash,
            dedupe_window_minutes=10,
        )

        self.assertIsNone(recent_log)

    def test_cached_in_progress_check_avoids_db_query(self):
        """A cached in-progress dedupe entry raises without hitting the DB."""
        ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            request_payload=self.payload,
        )

        with self.assertNumQueries(0):
            with self.assertRaises(ai_idempotency.AIRequestInProgress):
                ai_idempotency.create_in_progress_request(
                    user=self.user,
                    endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
                    request_payload=self.payload,
                )

    def test_cached_completed_check_avoids_db_query(self):
        """A cached completed dedupe entry resolves without hitting the DB."""
        request_log, _ = ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            request_payload=self.payload,
        )

        response_payload = {"summary": "Cached result"}
        ai_idempotency.mark_request_completed(request_log, response_payload)

        with self.assertNumQueries(0):
            duplicate_log, created = (
                ai_idempotency.create_in_progress_request(
                    user=self.user,
                    endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
                    request_payload=self.payload,
                )
            )

        self.assertFalse(created)
        self.assertEqual(duplicate_log.response_payload, response_payload)

    def test_cold_cache_falls_back_to_db_and_repopulates(self):
        """A cache miss falls back to the DB and repopulates the cache."""
        content_hash = ai_idempotency.build_content_hash(self.payload)
        idempotency_key = ai_idempotency.build_idempotency_key(
            user_id=self.user.id,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            content_hash=content_hash,
        )
        request_log = models.AIRequestLog.objects.create(
            owner=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            idempotency_key=idempotency_key,
            content_hash=content_hash,
            status=models.AIRequestStatus.COMPLETED,
            response_payload={"summary": "Pre-existing result"},
            completed_at=timezone.now(),
        )

        duplicate_log, created = ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            request_payload=self.payload,
        )

        self.assertFalse(created)
        self.assertEqual(duplicate_log.id, request_log.id)

        with self.assertNumQueries(0):
            second_log, second_created = (
                ai_idempotency.create_in_progress_request(
                    user=self.user,
                    endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
                    request_payload=self.payload,
                )
            )

        self.assertFalse(second_created)
        self.assertEqual(second_log.id, request_log.id)

    def test_mark_request_failed_updates_cache(self):
        """Marking a request failed updates the dedupe cache entry too."""
        request_log, _ = ai_idempotency.create_in_progress_request(
            user=self.user,
            endpoint_type=models.AIEndpointType.STORY_ANALYSIS,
            request_payload=self.payload,
        )

        ai_idempotency.mark_request_failed(request_log, "boom")

        cached = cache.get(
            ai_idempotency._dedupe_cache_key(request_log.idempotency_key)
        )
        self.assertIsNotNone(cached)
        self.assertEqual(cached["status"], models.AIRequestStatus.FAILED)
