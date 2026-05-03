"""
AI usage tracking helpers.
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from core import models


def record_ai_usage(
    *,
    user,
    endpoint_type: str,
    meta: Dict[str, Any],
    request_log: Optional[models.AIRequestLog] = None,
) -> models.AIUsageLog:
    """Create an AI usage log from response metadata."""
    return models.AIUsageLog.objects.create(
        owner=user,
        request_log=request_log,
        endpoint_type=endpoint_type,
        ai_mode=meta.get("ai_mode", ""),
        model=meta.get("model"),
        input_tokens=meta.get("input_tokens") or 0,
        output_tokens=meta.get("output_tokens") or 0,
        total_tokens=meta.get("total_tokens") or 0,
        estimated_cost_usd=Decimal("0.000000"),
    )
