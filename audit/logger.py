"""
Transaction logger — wraps db.insert_transaction() with a clean call interface.
Called from verifier/pipeline.py after every smart_request().
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from audit.db import init_db, insert_transaction
from verifier.pipeline import SmartResponse

logger = logging.getLogger(__name__)

# Ensure DB and table exist on first import
init_db()


def log_response(
    result: SmartResponse,
    task_type: str = "general",
    quality_score: Optional[int] = None,
    quality_passed: Optional[bool] = None,
) -> int:
    """
    Persist a completed SmartResponse to the audit database.
    Returns the row ID of the inserted record.
    """
    prompt = result.prompt
    response = result.response
    routing = result.routing
    escalation = result.escalation

    escalated = bool(escalation and escalation.triggered)
    escalated_model = escalation.escalated_model if escalated else None
    escalation_cost = escalation.cost_delta_usd if escalated else 0.0

    row_id = insert_transaction(
        timestamp=datetime.now(timezone.utc).isoformat(),
        prompt_hash=hashlib.md5(prompt.encode()).hexdigest(),
        prompt_preview=prompt[:120],
        complexity_tier=routing.tier,
        tier_name=routing.tier_name,
        task_type=task_type,
        model_id=response.model_id,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        latency_ms=response.latency_ms,
        cost_usd=response.cost_usd,
        quality_score=quality_score,
        quality_passed=quality_passed,
        escalated=escalated,
        escalated_model=escalated_model,
        escalation_cost=escalation_cost,
    )

    logger.info(
        "Logged transaction #%d | model=%s tier=%d cost=$%.6f escalated=%s",
        row_id, response.model_id, routing.tier, response.cost_usd, escalated,
    )
    return row_id
