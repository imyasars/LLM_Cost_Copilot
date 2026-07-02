"""
Quality thresholds — defines what "good enough" means per task type.

Each threshold has:
  min_score     : minimum LLM-as-judge score (1–5) to pass
  judge_model   : which model acts as judge
  description   : human-readable explanation
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class QualityThreshold:
    task_type: str
    min_score: int        # 1–5; responses below this trigger escalation
    judge_model: str      # model used to evaluate quality
    description: str


# Default judge — always the most capable available model
DEFAULT_JUDGE = "gpt-4o"

THRESHOLDS: dict[str, QualityThreshold] = {
    "extraction": QualityThreshold(
        task_type="extraction",
        min_score=4,
        judge_model=DEFAULT_JUDGE,
        description="Key fields must be correctly extracted; score < 4 means missing or wrong data",
    ),
    "summarization": QualityThreshold(
        task_type="summarization",
        min_score=4,
        judge_model=DEFAULT_JUDGE,
        description="Summary must cover main points faithfully without hallucination",
    ),
    "classification": QualityThreshold(
        task_type="classification",
        min_score=5,
        judge_model=DEFAULT_JUDGE,
        description="Classification must agree with the judge's own answer",
    ),
    "qa": QualityThreshold(
        task_type="qa",
        min_score=4,
        judge_model=DEFAULT_JUDGE,
        description="Answer must be factually correct and complete",
    ),
    "reasoning": QualityThreshold(
        task_type="reasoning",
        min_score=4,
        judge_model=DEFAULT_JUDGE,
        description="Logic must be sound and conclusion well-supported",
    ),
    "creative": QualityThreshold(
        task_type="creative",
        min_score=3,
        judge_model=DEFAULT_JUDGE,
        description="Creative tasks have more tolerance; must meet basic coherence",
    ),
    "general": QualityThreshold(
        task_type="general",
        min_score=4,
        judge_model=DEFAULT_JUDGE,
        description="Default threshold for unclassified task types",
    ),
}


def get_threshold(task_type: str) -> QualityThreshold:
    return THRESHOLDS.get(task_type, THRESHOLDS["general"])
