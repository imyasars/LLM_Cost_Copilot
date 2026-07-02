"""Tests for Phase 3: Quality Verification Loop."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.response import LLMResponse
from verifier.thresholds import get_threshold, THRESHOLDS, QualityThreshold
from verifier.judge import _parse_verdict, JudgeVerdict
from verifier.verifier import verify_and_wait, VerificationResult
from verifier.escalator import EscalationResult
from verifier.pipeline import SmartResponse


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_response(model_id="gpt-4o-mini", text="Paris is the capital of France.",
                  cost=0.000003, latency=1200.0) -> LLMResponse:
    return LLMResponse(
        model_id=model_id,
        provider="openrouter",
        prompt="What is the capital of France?",
        text=text,
        input_tokens=15,
        output_tokens=8,
        latency_ms=latency,
        cost_usd=cost,
    )


# ── Thresholds ────────────────────────────────────────────────────────────────

def test_all_task_types_have_thresholds():
    for task in ["extraction", "summarization", "classification", "qa",
                 "reasoning", "creative", "general"]:
        t = get_threshold(task)
        assert isinstance(t, QualityThreshold)


def test_unknown_task_type_falls_back_to_general():
    t = get_threshold("nonexistent_task_type")
    assert t.task_type == "general"


def test_thresholds_min_score_in_valid_range():
    for t in THRESHOLDS.values():
        assert 1 <= t.min_score <= 5


def test_classification_has_highest_threshold():
    assert get_threshold("classification").min_score == 5


def test_creative_has_lowest_threshold():
    assert get_threshold("creative").min_score <= get_threshold("general").min_score


def test_all_thresholds_have_judge_model():
    for t in THRESHOLDS.values():
        assert t.judge_model


# ── Judge parsing ─────────────────────────────────────────────────────────────

def test_parse_verdict_valid():
    text = "SCORE: 4\nREASON: The response is accurate and complete."
    score, reason = _parse_verdict(text)
    assert score == 4
    assert "accurate" in reason


def test_parse_verdict_score_5():
    score, reason = _parse_verdict("SCORE: 5\nREASON: Perfect answer.")
    assert score == 5


def test_parse_verdict_score_1():
    score, reason = _parse_verdict("SCORE: 1\nREASON: Completely wrong.")
    assert score == 1


def test_parse_verdict_missing_score_defaults_to_3():
    score, _ = _parse_verdict("No score here, just text.")
    assert score == 3


def test_parse_verdict_missing_reason_uses_text():
    _, reason = _parse_verdict("SCORE: 4\nSome explanation without REASON prefix.")
    assert reason  # non-empty


def test_parse_verdict_extra_whitespace():
    score, reason = _parse_verdict("SCORE:  3  \nREASON:  Acceptable.  ")
    assert score == 3
    assert reason == "Acceptable."


# ── Verifier ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_and_wait_pass():
    response = make_response(text="Paris is the capital of France.")
    judge_response = make_response(text="SCORE: 5\nREASON: Perfect factual answer.")

    with patch("verifier.verifier.judge") as mock_judge:
        mock_judge.return_value = JudgeVerdict(
            score=5, reason="Perfect.", judge_model="gpt-4o",
            passed=True, threshold=4,
        )
        result = await verify_and_wait(
            prompt="What is the capital of France?",
            response=response,
            complexity_tier=1,
            task_type="qa",
        )

    assert isinstance(result, VerificationResult)
    assert result.is_routing_failure is False
    assert result.verdict.score == 5


@pytest.mark.asyncio
async def test_verify_and_wait_fail():
    response = make_response(text="London is the capital of France.")

    with patch("verifier.verifier.judge") as mock_judge:
        mock_judge.return_value = JudgeVerdict(
            score=1, reason="Factually wrong.", judge_model="gpt-4o",
            passed=False, threshold=4,
        )
        result = await verify_and_wait(
            prompt="What is the capital of France?",
            response=response,
            complexity_tier=1,
            task_type="qa",
        )

    assert result.is_routing_failure is True
    assert result.verdict.score == 1


@pytest.mark.asyncio
async def test_verify_calls_on_failure_callback():
    response = make_response(text="Wrong answer.")
    callback_called = []

    async def on_failure(result: VerificationResult):
        callback_called.append(result)

    with patch("verifier.verifier.judge") as mock_judge:
        mock_judge.return_value = JudgeVerdict(
            score=2, reason="Poor quality.", judge_model="gpt-4o",
            passed=False, threshold=4,
        )
        from verifier.verifier import _run_verification
        await _run_verification(
            "What is the capital?", response, 1, "qa", on_failure
        )

    assert len(callback_called) == 1


def test_verification_result_summary_pass():
    vr = VerificationResult(
        prompt_hash="abc", prompt="test", original_model="gpt-4o-mini",
        complexity_tier=1, task_type="qa",
        verdict=JudgeVerdict(score=5, reason="Perfect.", judge_model="gpt-4o",
                             passed=True, threshold=4),
        timestamp="2026-07-01T00:00:00",
        is_routing_failure=False,
    )
    summary = vr.summary()
    assert "PASS" in summary
    assert "gpt-4o-mini" in summary


def test_verification_result_summary_fail():
    vr = VerificationResult(
        prompt_hash="abc", prompt="test", original_model="gemini-flash",
        complexity_tier=1, task_type="qa",
        verdict=JudgeVerdict(score=2, reason="Wrong.", judge_model="gpt-4o",
                             passed=False, threshold=4),
        timestamp="2026-07-01T00:00:00",
        is_routing_failure=True,
    )
    summary = vr.summary()
    assert "FAIL" in summary
    assert "gemini-flash" in summary


# ── Pipeline ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smart_response_best_response_no_escalation():
    response = make_response()
    sr = SmartResponse(prompt="test", routing=MagicMock(), response=response)
    assert sr.best_response is response


@pytest.mark.asyncio
async def test_smart_response_best_response_with_escalation():
    original = make_response(model_id="gemini-flash")
    escalated = make_response(model_id="gpt-4o", text="Better answer.")
    sr = SmartResponse(
        prompt="test",
        routing=MagicMock(),
        response=original,
        escalation=EscalationResult(
            triggered=True,
            original_model="gemini-flash",
            escalated_model="gpt-4o",
            original_response=original,
            escalated_response=escalated,
            cost_delta_usd=0.005,
            quality_gap=2,
            reason="Score too low",
        ),
    )
    assert sr.best_response is escalated


@pytest.mark.asyncio
async def test_smart_request_no_verify():
    with patch("verifier.pipeline.route") as mock_route, \
         patch("verifier.pipeline.send_request") as mock_send:

        mock_route.return_value = MagicMock(
            tier=1, tier_name="Simple", model_id="gemini-flash",
            fallback_models=["gpt-4o-mini"],
        )
        mock_send.return_value = make_response()

        from verifier.pipeline import smart_request
        result = await smart_request("What is 2+2?", verify=False)

    assert result.response.model_id == "gpt-4o-mini"
    assert result.verification_task is None
    assert result.escalation is None
