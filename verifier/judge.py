"""
LLM-as-judge — scores a model response on a 1–5 scale.

The judge is given the original prompt and the response to evaluate.
It returns a structured score with reasoning.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from models.response import LLMResponse
from router.send_request import send_request


JUDGE_PROMPT_TEMPLATE = """You are an impartial quality evaluator for LLM responses.

Evaluate the following response to the given prompt on a scale of 1 to 5:

  5 = Perfect: complete, accurate, well-structured, no issues
  4 = Good: mostly correct with minor omissions or style issues
  3 = Acceptable: partially correct but missing key content or clarity
  2 = Poor: significant errors, hallucinations, or incomplete answer
  1 = Fail: wrong, irrelevant, or harmful

PROMPT:
{prompt}

RESPONSE:
{response}

Reply in EXACTLY this format (no other text):
SCORE: <1-5>
REASON: <one sentence explaining the score>"""


@dataclass
class JudgeVerdict:
    score: int           # 1–5
    reason: str          # one-sentence explanation
    judge_model: str     # which model produced this verdict
    passed: bool         # True if score >= threshold
    threshold: int       # the threshold that was checked against


async def judge(
    prompt: str,
    response: LLMResponse,
    judge_model: str,
    min_score: int,
) -> JudgeVerdict:
    """Ask the judge model to score a response. Returns a JudgeVerdict."""
    judge_prompt = JUDGE_PROMPT_TEMPLATE.format(
        prompt=prompt,
        response=response.text,
    )

    try:
        judge_response = await send_request(judge_prompt, judge_model)
        score, reason = _parse_verdict(judge_response.text)
    except Exception as e:
        # If the judge call fails, default to passing to avoid blocking the user
        score = 4
        reason = f"Judge call failed ({e}); defaulting to pass"

    return JudgeVerdict(
        score=score,
        reason=reason,
        judge_model=judge_model,
        passed=score >= min_score,
        threshold=min_score,
    )


def _parse_verdict(text: str) -> tuple[int, str]:
    """Extract SCORE and REASON from the judge's structured reply."""
    score_match = re.search(r"SCORE:\s*([1-5])", text)
    reason_match = re.search(r"REASON:\s*(.+)", text, re.DOTALL)

    score = int(score_match.group(1)) if score_match else 3
    reason = reason_match.group(1).strip() if reason_match else text.strip()[:200]

    return score, reason
