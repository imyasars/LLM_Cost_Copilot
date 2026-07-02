"""
Auto-escalator — retries a failed request with the next model in the fallback chain.

Also implements the Data Flywheel:
  - Appends routing failures to classifier/dataset.py as new labeled examples
  - Triggers classifier retraining after accumulating enough new failures
"""
from __future__ import annotations

import asyncio
import logging
import pathlib
from dataclasses import dataclass
from typing import Optional

from models.response import LLMResponse
from router.send_request import send_request
from routing.router import RoutingDecision
from verifier.verifier import VerificationResult

logger = logging.getLogger(__name__)

_DATASET_PATH = pathlib.Path(__file__).parent.parent / "classifier" / "dataset.py"
_RETRAIN_AFTER_N_FAILURES = 10   # trigger retraining after this many new flywheel entries
_flywheel_counter = 0            # in-process counter (resets on restart)


@dataclass
class EscalationResult:
    triggered: bool
    original_model: str
    escalated_model: Optional[str]
    original_response: Optional[LLMResponse]
    escalated_response: Optional[LLMResponse]
    cost_delta_usd: float          # escalated cost − original cost
    quality_gap: int               # escalated_score − original_score (if re-judged)
    reason: str


async def escalate(
    prompt: str,
    routing_decision: RoutingDecision,
    verification_result: VerificationResult,
    latency_budget_ms: float = 10_000,
) -> EscalationResult:
    """
    Try each fallback model in order until one succeeds or the list is exhausted.
    Logs original model, escalated model, cost delta, and quality gap.
    """
    fallbacks = routing_decision.fallback_models
    original_response = None  # we log cost delta vs the original call

    for fallback_model in fallbacks:
        if fallback_model == routing_decision.model_id:
            continue  # skip — already tried this one

        logger.info(
            "Escalating from %s → %s (score was %d/%d)",
            routing_decision.model_id, fallback_model,
            verification_result.verdict.score,
            verification_result.verdict.threshold,
        )

        try:
            escalated = await asyncio.wait_for(
                send_request(prompt, fallback_model),
                timeout=latency_budget_ms / 1000,
            )
        except asyncio.TimeoutError:
            logger.warning("Escalation to %s timed out", fallback_model)
            continue
        except Exception as e:
            logger.warning("Escalation to %s failed: %s", fallback_model, e)
            continue

        cost_delta = escalated.cost_usd - verification_result.verdict.score * 0  # placeholder
        # cost delta = escalated call cost vs original call cost
        # (we don't have original LLMResponse here, use 0 as base)
        cost_delta = escalated.cost_usd

        result = EscalationResult(
            triggered=True,
            original_model=routing_decision.model_id,
            escalated_model=fallback_model,
            original_response=None,
            escalated_response=escalated,
            cost_delta_usd=cost_delta,
            quality_gap=0,   # would require re-judging; skipped to save cost
            reason=(
                f"Original score {verification_result.verdict.score}/"
                f"{verification_result.verdict.threshold} — "
                f"{verification_result.verdict.reason[:100]}"
            ),
        )

        logger.info(
            "Escalation complete: %s → %s | cost_delta=$%.6f",
            routing_decision.model_id, fallback_model, cost_delta,
        )

        # Feed into flywheel
        _feed_flywheel(prompt, verification_result)

        return result

    return EscalationResult(
        triggered=False,
        original_model=routing_decision.model_id,
        escalated_model=None,
        original_response=None,
        escalated_response=None,
        cost_delta_usd=0.0,
        quality_gap=0,
        reason="All fallback models exhausted or failed",
    )


def _feed_flywheel(prompt: str, result: VerificationResult) -> None:
    """
    Append the failed prompt back into classifier/dataset.py with its tier label
    so the next retraining cycle learns from this real-world routing failure.
    """
    global _flywheel_counter

    try:
        content = _DATASET_PATH.read_text()
        # Escape quotes in the prompt
        safe_prompt = prompt.replace('"', '\\"').replace("\n", " ").strip()
        tier = result.complexity_tier
        new_entry = f'    ("{safe_prompt}", {tier}),  # flywheel\n'

        # Insert before the closing bracket of LABELED_PROMPTS
        content = content.rstrip()
        if content.endswith("]"):
            content = content[:-1] + new_entry + "]\n"
            _DATASET_PATH.write_text(content)
            _flywheel_counter += 1
            logger.info("Flywheel: added entry #%d for tier %d", _flywheel_counter, tier)

        if _flywheel_counter >= _RETRAIN_AFTER_N_FAILURES:
            _trigger_retraining()
            _flywheel_counter = 0

    except Exception as e:
        logger.warning("Flywheel write failed: %s", e)


def _trigger_retraining() -> None:
    """Re-train the classifier in a subprocess so it doesn't block the event loop."""
    import subprocess
    import sys
    logger.info("Flywheel threshold reached — triggering classifier retraining")
    subprocess.Popen(
        [sys.executable, "-m", "classifier.train"],
        cwd=str(_DATASET_PATH.parent.parent),
    )
