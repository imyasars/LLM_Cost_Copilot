"""
Smart request pipeline — ties all of Phase 3 together.

Usage:
    result = await smart_request(prompt, task_type="summarization")
    print(result.response.text)        # available immediately
    # verification runs in background; await result.verification_task for the verdict

Full flow:
    1. route(prompt)           → RoutingDecision (classifier, <1ms)
    2. send_request(...)       → LLMResponse     (API call)
    3. [return to caller]
    4. verify_in_background()  → fires background task
    5. if failure → escalate() → re-run with next fallback model
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from models.response import LLMResponse
from router.send_request import send_request
from routing.router import route, RoutingDecision
from verifier.verifier import verify_in_background, verify_and_wait, VerificationResult
from verifier.escalator import escalate, EscalationResult

logger = logging.getLogger(__name__)
_db_logger = None   # lazy import to avoid circular imports


def _get_db_logger():
    global _db_logger
    if _db_logger is None:
        from audit.logger import log_response
        _db_logger = log_response
    return _db_logger


@dataclass
class SmartResponse:
    prompt: str
    routing: RoutingDecision
    response: LLMResponse
    verification_task: Optional[asyncio.Task] = field(default=None, repr=False)
    escalation: Optional[EscalationResult] = None
    final_response: Optional[LLMResponse] = None   # set if escalation happened

    @property
    def best_response(self) -> LLMResponse:
        """The best response available — escalated if escalation happened, else original."""
        if self.escalation and self.escalation.escalated_response:
            return self.escalation.escalated_response
        return self.response

    def summary(self) -> str:
        esc = ""
        if self.escalation and self.escalation.triggered:
            esc = f" → escalated to {self.escalation.escalated_model}"
        return (
            f"Tier {self.routing.tier} ({self.routing.tier_name}) | "
            f"model={self.response.model_id}{esc} | "
            f"cost=${self.response.cost_usd:.6f} | "
            f"latency={self.response.latency_ms:.0f}ms"
        )


async def smart_request(
    prompt: str,
    task_type: str = "general",
    latency_budget_ms: float = 10_000,
    verify: bool = True,
    wait_for_verification: bool = False,
) -> SmartResponse:
    """
    Full Phase 3 pipeline.

    Args:
        prompt:                 The user's input.
        task_type:              One of: extraction, summarization, classification,
                                qa, reasoning, creative, general.
        latency_budget_ms:      Max ms allowed for escalation re-call.
        verify:                 Whether to run background quality verification.
        wait_for_verification:  If True, await the verification before returning
                                (useful for testing; False in production).
    """
    # Step 1 — classify and route
    routing = route(prompt)
    logger.info("Routing: tier=%d model=%s", routing.tier, routing.model_id)

    # Step 2 — send to primary model
    response = await send_request(prompt, routing.model_id)
    logger.info(
        "Response: model=%s tokens=%d cost=$%.6f latency=%.0fms",
        response.model_id, response.output_tokens,
        response.cost_usd, response.latency_ms,
    )

    result = SmartResponse(
        prompt=prompt,
        routing=routing,
        response=response,
    )

    if not verify:
        return result

    # Step 3 — background verification (with escalation callback)
    async def on_failure(verification_result: VerificationResult):
        esc = await escalate(
            prompt=prompt,
            routing_decision=routing,
            verification_result=verification_result,
            latency_budget_ms=latency_budget_ms,
        )
        result.escalation = esc
        if esc.triggered:
            result.final_response = esc.escalated_response

    if wait_for_verification:
        # Blocking — used in tests and demo scripts
        vr = await verify_and_wait(prompt, response, routing.tier, task_type)
        result.verification_task = None
        if vr.is_routing_failure:
            await on_failure(vr)
        # Log with quality verdict
        try:
            _get_db_logger()(result, task_type, vr.verdict.score, vr.verdict.passed)
        except Exception as e:
            logger.warning("DB logging failed: %s", e)
    else:
        # Non-blocking — used in production; caller can await task later
        result.verification_task = await verify_in_background(
            prompt, response, routing.tier, task_type, on_failure
        )
        # Log immediately without quality score (score arrives later in background)
        try:
            _get_db_logger()(result, task_type)
        except Exception as e:
            logger.warning("DB logging failed: %s", e)

    return result
