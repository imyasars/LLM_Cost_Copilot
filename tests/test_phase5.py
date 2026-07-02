"""Tests for Phase 5: FastAPI Service."""
from __future__ import annotations

import pathlib
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── App fixture ───────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    from api.app import app
    return TestClient(app)


# ── GET /health ───────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── GET /v1/models ────────────────────────────────────────────────────────────

def test_list_models_returns_200(client):
    r = client.get("/v1/models")
    assert r.status_code == 200


def test_list_models_has_models_key(client):
    r = client.get("/v1/models")
    assert "models" in r.json()
    assert "total" in r.json()


def test_list_models_total_matches_list(client):
    data = client.get("/v1/models").json()
    assert data["total"] == len(data["models"])


def test_list_models_contains_expected_fields(client):
    model = client.get("/v1/models").json()["models"][0]
    for field in ["model_id", "provider", "api_name", "cost_per_1k_tokens", "tier"]:
        assert field in model


def test_list_models_tiers_are_valid(client):
    models = client.get("/v1/models").json()["models"]
    for m in models:
        assert m["tier"] in {1, 2, 3}


def test_list_models_costs_non_negative(client):
    models = client.get("/v1/models").json()["models"]
    for m in models:
        assert m["cost_per_1k_tokens"] >= 0


# ── GET /v1/stats ─────────────────────────────────────────────────────────────

def test_stats_returns_200(client):
    r = client.get("/v1/stats")
    assert r.status_code == 200


def test_stats_has_required_fields(client):
    data = client.get("/v1/stats").json()
    for field in ["total_requests", "total_cost_usd", "savings_pct",
                  "avg_latency_ms", "escalation_count"]:
        assert field in data


def test_stats_savings_pct_non_negative(client):
    data = client.get("/v1/stats").json()
    assert data["savings_pct"] >= 0


# ── POST /v1/completions ──────────────────────────────────────────────────────

def _mock_smart_response():
    from verifier.pipeline import SmartResponse
    from routing.router import RoutingDecision

    routing = RoutingDecision(
        tier=1, tier_name="Simple", model_id="gemini-flash",
        fallback_models=["gpt-4o-mini"], description="Basic Q&A",
    )
    response = MagicMock()
    response.text = "Paris is the capital of France."
    response.model_id = "gemini-flash"
    response.input_tokens = 15
    response.output_tokens = 8
    response.latency_ms = 1200.0
    response.cost_usd = 0.000001

    sr = SmartResponse(prompt="What is the capital of France?",
                       routing=routing, response=response)
    return sr


def test_completions_returns_200(client):
    with patch("verifier.pipeline.smart_request", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_smart_response()
        r = client.post("/v1/completions",
                        json={"prompt": "What is the capital of France?"})
    assert r.status_code == 200


def test_completions_response_has_text(client):
    with patch("api.app.smart_request", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_smart_response()
        data = client.post("/v1/completions",
                           json={"prompt": "What is the capital of France?"}).json()
    assert "text" in data
    assert len(data["text"]) > 0


def test_completions_response_has_routing_meta(client):
    with patch("verifier.pipeline.smart_request", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_smart_response()
        data = client.post("/v1/completions",
                           json={"prompt": "What is the capital of France?"}).json()
    assert "routing" in data
    assert data["routing"]["tier"] == 1
    assert data["routing"]["model_id"] == "gemini-flash"


def test_completions_no_escalation_by_default(client):
    with patch("verifier.pipeline.smart_request", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_smart_response()
        data = client.post("/v1/completions",
                           json={"prompt": "What is the capital of France?"}).json()
    assert data["escalation"] is None


def test_completions_missing_prompt_returns_422(client):
    r = client.post("/v1/completions", json={})
    assert r.status_code == 422


def test_completions_bad_gateway_on_exception(client):
    with patch("api.app.smart_request", new_callable=AsyncMock) as mock:
        mock.side_effect = Exception("Provider down")
        r = client.post("/v1/completions",
                        json={"prompt": "Hello"})
    assert r.status_code == 502


# ── PUT /v1/routing-config ────────────────────────────────────────────────────

def test_routing_config_update_valid(client, tmp_path):
    config_content = {
        "routing": {
            1: {"tier_name": "Simple", "primary": "gemini-flash",
                "fallbacks": ["gpt-4o-mini"], "description": "Simple"},
            2: {"tier_name": "Moderate", "primary": "gpt-4o-mini",
                "fallbacks": ["gemini-pro"], "description": "Moderate"},
            3: {"tier_name": "Complex", "primary": "gpt-4o",
                "fallbacks": ["gemini-pro"], "description": "Complex"},
        }
    }
    import yaml
    config_file = tmp_path / "routing_config.yaml"
    config_file.write_text(yaml.dump(config_content))

    with patch("api.app._ROUTING_CONFIG_PATH", config_file), \
         patch("api.app.reload_config"):
        r = client.put("/v1/routing-config", json={
            "tier1": {"primary": "gemini-flash", "fallbacks": ["gpt-4o-mini"]}
        })
    assert r.status_code == 200
    assert 1 in r.json()["updated_tiers"]


def test_routing_config_unknown_model_returns_422(client, tmp_path):
    config_content = {"routing": {
        1: {"tier_name": "Simple", "primary": "gemini-flash",
            "fallbacks": ["gpt-4o-mini"], "description": "Simple"},
    }}
    import yaml
    config_file = tmp_path / "routing_config.yaml"
    config_file.write_text(yaml.dump(config_content))

    with patch("api.app._ROUTING_CONFIG_PATH", config_file), \
         patch("api.app.reload_config"):
        r = client.put("/v1/routing-config", json={
            "tier1": {"primary": "nonexistent-model-xyz", "fallbacks": []}
        })
    assert r.status_code == 422


def test_routing_config_empty_body_returns_400(client):
    r = client.put("/v1/routing-config", json={})
    assert r.status_code == 400
