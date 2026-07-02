"""
Async background verifier — fires after the response is already delivered to the user.

Flow:
  1. User gets the response immediately (no waiting)
  2. A background asyncio task calls the judge
  3. If score < threshold → log as routing failure
  4. Return a VerificationResult for the escalator to act on
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from models.response import LLMResponse
from verifier.judge import judge, JudgeVerdict
from verifier.thresholds import get_threshold

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    prompt_hash: str
    prompt: str
    original_model: str
    complexity_tier: int
    task_type: str
    verdict: JudgeVerdict
    timestamp: str
    is_routing_failure: bool   # True when score < threshold

    def summary(self) -> str:
        status = "FAIL" if self.is_routing_failure else "PASS"
        return (
            f"[{status}] {self.original_model} | tier={self.complexity_tier} "
            f"| score={self.verdict.score}/{self.verdict.threshold} "
            f"| {self.verdict.reason[:80]}"
        )


async def verify_in_background(
    prompt: str,
    response: LLMResponse,
    complexity_tier: int,
    task_type: str = "general",
    on_failure=None,        # optional async callback(VerificationResult)
) -> asyncio.Task:
    """
    Schedule verification as a background asyncio task.
    Returns the Task immediately — caller does not await it.
    The optional on_failure callback is called if quality is below threshold.
    """
    task = asyncio.create_task(
        _run_verification(prompt, response, complexity_tier, task_type, on_failure),
        name=f"verify-{response.model_id}-{hashlib.md5(prompt.encode()).hexdigest()[:8]}",
    )
    return task


async def _run_verification(
    prompt: str,
    response: LLMResponse,
    complexity_tier: int,
    task_type: str,
    on_failure,
) -> VerificationResult:
    threshold = get_threshold(task_type)

    verdict = await judge(
        prompt=prompt,
        response=response,
        judge_model=threshold.judge_model,
        min_score=threshold.min_score,
    )

    result = VerificationResult(
        prompt_hash=hashlib.md5(prompt.encode()).hexdigest(),
        prompt=prompt,
        original_model=response.model_id,
        complexity_tier=complexity_tier,
        task_type=task_type,
        verdict=verdict,
        timestamp=datetime.utcnow().isoformat(),
        is_routing_failure=not verdict.passed,
    )

    if result.is_routing_failure:
        logger.warning("Routing failure: %s", result.summary())
        if on_failure:
            await on_failure(result)
    else:
        logger.info("Verification passed: %s", result.summary())

    return result


async def verify_and_wait(
    prompt: str,
    response: LLMResponse,
    complexity_tier: int,
    task_type: str = "general",
) -> VerificationResult:
    """Synchronous version — awaits the full verification. Used in tests."""
    return await _run_verification(prompt, response, complexity_tier, task_type, None)
