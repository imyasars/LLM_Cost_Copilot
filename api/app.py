"""
LLM Cost Autopilot — FastAPI Service

Endpoints:
  POST /v1/completions        Route and complete a prompt
  GET  /v1/models             List all registered models and costs
  GET  /v1/stats              Cost savings summary
  PUT  /v1/routing-config     Update routing map at runtime
  GET  /health                Health check

Run:
  uvicorn api.app:app --reload --port 8000
"""
from __future__ import annotations

import logging
import pathlib
import sys

# Ensure project root is on the path when running via uvicorn
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    CompletionRequest, CompletionResponse,
    RoutingMeta, EscalationMeta,
    ModelInfo, ModelsResponse,
    StatsResponse,
    RoutingConfigUpdate, RoutingConfigResponse,
)
from models.config import MODELS
from audit.db import get_stats, init_db
from routing.router import reload_config
from verifier.pipeline import smart_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

init_db()

app = FastAPI(
    title="LLM Cost Autopilot",
    description=(
        "Intelligent LLM router that automatically selects the most cost-effective "
        "model for each request based on prompt complexity."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_ROUTING_CONFIG_PATH = pathlib.Path(__file__).parent.parent / "routing" / "routing_config.yaml"


# ── POST /v1/completions ──────────────────────────────────────────────────────

@app.post("/v1/completions", response_model=CompletionResponse)
async def completions(request: CompletionRequest):
    """
    Route a prompt to the best model based on complexity and return the completion.
    Metadata shows the routing decision made and why.
    """
    try:
        result = await smart_request(
            prompt=request.prompt,
            task_type=request.task_type,
            verify=request.verify,
            wait_for_verification=request.verify,
            latency_budget_ms=request.latency_budget_ms,
        )
    except Exception as e:
        logger.error("smart_request failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))

    resp = result.best_response
    routing = result.routing

    escalation_meta = None
    if result.escalation and result.escalation.triggered:
        esc = result.escalation
        escalation_meta = EscalationMeta(
            triggered=True,
            original_model=esc.original_model,
            escalated_model=esc.escalated_model,
            cost_delta_usd=esc.cost_delta_usd,
            reason=esc.reason,
        )

    return CompletionResponse(
        text=resp.text,
        model_id=resp.model_id,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        latency_ms=resp.latency_ms,
        cost_usd=resp.cost_usd,
        routing=RoutingMeta(
            tier=routing.tier,
            tier_name=routing.tier_name,
            model_id=routing.model_id,
            fallback_models=routing.fallback_models,
            description=routing.description,
        ),
        escalation=escalation_meta,
    )


# ── GET /v1/models ────────────────────────────────────────────────────────────

@app.get("/v1/models", response_model=ModelsResponse)
def list_models():
    """List all registered models with their costs and tier assignments."""
    model_list = [
        ModelInfo(
            model_id=cfg.model_id,
            provider=cfg.provider,
            api_name=cfg.api_name,
            cost_per_1k_tokens=cfg.cost_per_1k_tokens,
            tier=cfg.tier,
        )
        for cfg in sorted(MODELS.values(), key=lambda m: (m.tier, m.cost_per_1k_tokens))
    ]
    return ModelsResponse(models=model_list, total=len(model_list))


# ── GET /v1/stats ─────────────────────────────────────────────────────────────

@app.get("/v1/stats", response_model=StatsResponse)
def stats():
    """Return cost savings summary across all logged transactions."""
    s = get_stats()
    return StatsResponse(
        total_requests=s["total_requests"],
        total_cost_usd=s["total_cost"],
        total_baseline_usd=s["total_baseline"],
        total_savings_usd=s["total_savings"],
        savings_pct=s["savings_pct"],
        avg_cost_usd=s["avg_cost"],
        avg_latency_ms=s["avg_latency_ms"],
        total_tokens=s["total_tokens"],
        escalation_count=s["escalation_count"],
        avg_quality_score=s["avg_quality_score"],
    )


# ── PUT /v1/routing-config ────────────────────────────────────────────────────

@app.put("/v1/routing-config", response_model=RoutingConfigResponse)
def update_routing_config(update: RoutingConfigUpdate):
    """
    Update the routing map at runtime without restarting the server.
    Only the tiers included in the request body are updated.
    """
    with open(_ROUTING_CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    tier_map = {1: update.tier1, 2: update.tier2, 3: update.tier3}
    updated = []

    for tier_num, tier_cfg in tier_map.items():
        if tier_cfg is None:
            continue
        if tier_cfg.primary not in MODELS:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown model_id '{tier_cfg.primary}' for tier {tier_num}"
            )
        for fb in tier_cfg.fallbacks:
            if fb not in MODELS:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unknown fallback model '{fb}' for tier {tier_num}"
                )
        config["routing"][tier_num]["primary"] = tier_cfg.primary
        config["routing"][tier_num]["fallbacks"] = tier_cfg.fallbacks
        updated.append(tier_num)

    if not updated:
        raise HTTPException(status_code=400, detail="No tier updates provided")

    with open(_ROUTING_CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    reload_config()

    return RoutingConfigResponse(
        message="Routing config updated and reloaded",
        updated_tiers=updated,
    )


# ── GET /health ───────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Health check — confirms the service is running."""
    return {"status": "ok", "service": "llm-cost-autopilot"}
