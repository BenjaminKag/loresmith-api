"""
AI idempotency helpers for LoreSmith.

This module handles short-term duplicate request protection for AI endpoints.
It is separate from long-term feature caches such as StoryAnalysis.
"""
from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

from django.db import IntegrityError, transaction
from django.utils import timezone

from core import models


DEFAULT_DEDUPE_WINDOW_MINUTES = 10


class AIRequestInProgress(RuntimeError):
    """Raised when a matching AI request is already running."""

    def __init__(self, request_log: models.AIRequestLog):
        self.request_log = request_log
        super().__init__("A matching AI request is already in progress.")


def normalize_payload(payload: Dict[str, Any]) -> str:
    """
    Convert a payload into a stable JSON string.

    This makes sure the same logical input creates the same hash even if
    dictionary key order is different.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def build_content_hash(payload: Dict[str, Any]) -> str:
    """Build a stable SHA-256 hash for the AI request input/settings."""
    normalized_payload = normalize_payload(payload)

    return hashlib.sha256(
        normalized_payload.encode("utf-8")
    ).hexdigest()


def build_idempotency_key(
    *,
    user_id: int,
    endpoint_type: str,
    content_hash: str,
) -> str:
    """
    Build a stable idempotency key for one user/endpoint/content combination.
    """
    raw_key = normalize_payload({
        "user_id": user_id,
        "endpoint_type": endpoint_type,
        "content_hash": content_hash,
    })

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_recent_completed_request(
    *,
    user,
    endpoint_type: str,
    content_hash: str,
    dedupe_window_minutes: int = DEFAULT_DEDUPE_WINDOW_MINUTES,
) -> Optional[models.AIRequestLog]:
    """
    Return a recent completed duplicate AI request, if one exists.
    """
    cutoff = timezone.now() - timedelta(minutes=dedupe_window_minutes)

    return (
        models.AIRequestLog.objects
        .filter(
            owner=user,
            endpoint_type=endpoint_type,
            content_hash=content_hash,
            status=models.AIRequestStatus.COMPLETED,
            completed_at__gte=cutoff,
        )
        .first()
    )


def get_recent_in_progress_request(
    *,
    user,
    endpoint_type: str,
    content_hash: str,
    dedupe_window_minutes: int = DEFAULT_DEDUPE_WINDOW_MINUTES,
) -> Optional[models.AIRequestLog]:
    """
    Return a recent in-progress duplicate AI request, if one exists.
    """
    cutoff = timezone.now() - timedelta(minutes=dedupe_window_minutes)

    return (
        models.AIRequestLog.objects
        .filter(
            owner=user,
            endpoint_type=endpoint_type,
            content_hash=content_hash,
            status=models.AIRequestStatus.IN_PROGRESS,
            created_at__gte=cutoff,
        )
        .first()
    )


@transaction.atomic
def create_in_progress_request(
    *,
    user,
    endpoint_type: str,
    request_payload: Dict[str, Any],
) -> Tuple[models.AIRequestLog, bool]:
    """
    Create an in-progress AI request log.

    Returns:
        (request_log, created)

    If a matching completed request exists recently, returns it with
    created=False.

    If a matching in-progress request exists recently, raises
    AIRequestInProgress.

    The unique idempotency_key protects against race-condition duplicate
    inserts.
    """
    content_hash = build_content_hash(request_payload)
    idempotency_key = build_idempotency_key(
        user_id=user.id,
        endpoint_type=endpoint_type,
        content_hash=content_hash,
    )

    completed_request = get_recent_completed_request(
        user=user,
        endpoint_type=endpoint_type,
        content_hash=content_hash,
    )
    if completed_request:
        return completed_request, False

    in_progress_request = get_recent_in_progress_request(
        user=user,
        endpoint_type=endpoint_type,
        content_hash=content_hash,
    )
    if in_progress_request:
        raise AIRequestInProgress(in_progress_request)

    try:
        request_log = models.AIRequestLog.objects.create(
            owner=user,
            endpoint_type=endpoint_type,
            idempotency_key=idempotency_key,
            content_hash=content_hash,
            status=models.AIRequestStatus.IN_PROGRESS,
            request_payload=request_payload,
        )
        return request_log, True

    except IntegrityError:
        existing_request = models.AIRequestLog.objects.get(
            idempotency_key=idempotency_key,
        )

        if existing_request.status == models.AIRequestStatus.COMPLETED:
            return existing_request, False

        if existing_request.status == models.AIRequestStatus.IN_PROGRESS:
            raise AIRequestInProgress(existing_request)

        return existing_request, False


def mark_request_completed(
    request_log: models.AIRequestLog,
    response_payload: Dict[str, Any],
) -> models.AIRequestLog:
    """Mark an AI request log as completed."""
    request_log.status = models.AIRequestStatus.COMPLETED
    request_log.response_payload = response_payload
    request_log.error_message = ""
    request_log.completed_at = timezone.now()
    request_log.save(
        update_fields=[
            "status",
            "response_payload",
            "error_message",
            "completed_at",
            "updated_at",
        ]
    )

    return request_log


def mark_request_failed(
    request_log: models.AIRequestLog,
    error_message: str,
) -> models.AIRequestLog:
    """Mark an AI request log as failed."""
    request_log.status = models.AIRequestStatus.FAILED
    request_log.error_message = error_message
    request_log.save(
        update_fields=[
            "status",
            "error_message",
            "updated_at",
        ]
    )

    return request_log
