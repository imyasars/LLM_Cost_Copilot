"""
Pydantic schemas for the FastAPI service.
"""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


# ── POST /v1/completions ──────────────────────────────────────────────────────

class CompletionRequest(BaseModel):
    prompt: str = Field(..., description="The user prompt to complete")
    task_type: str = Field("general", description=(
        "Task category: qa, summarization, classification, "
        "extraction, reasoning, creative, general"
    ))
    verify: bool = Field(False, description="Run background quality verification")
    latency_budget_ms: float = Field(10_000, description="Max ms budget for escalation")


class RoutingMeta(BaseModel):
    tier: int
    tier_name: str
    model_id: str
    fallback_models: List[str]
    description: str


class EscalationMeta(BaseModel):
    triggered: bool
    original_model: str
    escalated_model: Optional[str]
    cost_delta_usd: float
    reason: str


class CompletionResponse(BaseModel):
    text: str
    model_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    routing: RoutingMeta
    escalation: Optional[EscalationMeta] = None


# ── GET /v1/models ────────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    model_id: str
    provider: str
    api_name: str
    cost_per_1k_tokens: float
    tier: int


class ModelsResponse(BaseModel):
    models: List[ModelInfo]
    total: int


# ── GET /v1/stats ─────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_requests: int
    total_cost_usd: float
    total_baseline_usd: float
    total_savings_usd: float
    savings_pct: float
    avg_cost_usd: float
    avg_latency_ms: float
    total_tokens: int
    escalation_count: int
    avg_quality_score: Optional[float]


# ── PUT /v1/routing-config ────────────────────────────────────────────────────

class TierConfig(BaseModel):
    primary: str = Field(..., description="Primary model ID for this tier")
    fallbacks: List[str] = Field(..., description="Ordered fallback model IDs")


class RoutingConfigUpdate(BaseModel):
    tier1: Optional[TierConfig] = None
    tier2: Optional[TierConfig] = None
    tier3: Optional[TierConfig] = None


class RoutingConfigResponse(BaseModel):
    message: str
    updated_tiers: List[int]
