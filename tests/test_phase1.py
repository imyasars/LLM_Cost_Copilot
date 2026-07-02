import pytest
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from models.config import MODELS
from models.response import LLMResponse
from router.send_request import send_request


# --- Unit tests (no API calls) ---

def test_models_registry_not_empty():
    assert len(MODELS) > 0

def test_all_models_have_required_fields():
    for model_id, config in MODELS.items():
        assert config.model_id == model_id
        assert config.provider in ("openrouter", "ollama")
        assert config.api_name
        assert config.cost_per_1k_tokens >= 0
        assert config.tier in (1, 2, 3)

def test_unknown_model_raises():
    async def _run():
        await send_request("hello", "nonexistent-model")
    with pytest.raises(ValueError, match="Unknown model_id"):
        asyncio.run(_run())


# --- Live API tests (only run if key is present) ---

openrouter_available = os.environ.get("OPENROUTER_API_KEY", "").startswith("sk-or-")

@pytest.mark.skipif(not openrouter_available, reason="OPENROUTER_API_KEY not set")
def test_openrouter_gpt4o_mini():
    async def _run():
        return await send_request("Say hello in one word.", "gpt-4o-mini")
    result = asyncio.run(_run())
    assert isinstance(result, LLMResponse)
    assert result.text
    assert result.input_tokens > 0
    assert result.latency_ms > 0
    assert result.provider == "openrouter"

@pytest.mark.skipif(not openrouter_available, reason="OPENROUTER_API_KEY not set")
def test_openrouter_gemini_flash():
    async def _run():
        return await send_request("Say hello in one word.", "gemini-flash")
    result = asyncio.run(_run())
    assert isinstance(result, LLMResponse)
    assert result.text
    assert result.latency_ms > 0
    assert result.provider == "openrouter"

@pytest.mark.skipif(not openrouter_available, reason="OPENROUTER_API_KEY not set")
def test_openrouter_free_llama():
    async def _run():
        return await send_request("Say hello in one word.", "llama-3-8b")
    result = asyncio.run(_run())
    assert isinstance(result, LLMResponse)
    assert result.text
    assert result.cost_usd == 0.0
    assert result.provider == "openrouter"


# --- Ollama local tests ---

def test_ollama_qwen_1_5b():
    async def _run():
        return await send_request("Say hello in one word.", "qwen-coder-1.5b")
    result = asyncio.run(_run())
    assert isinstance(result, LLMResponse)
    assert result.text
    assert result.cost_usd == 0.0
    assert result.provider == "ollama"

def test_ollama_qwen_14b():
    async def _run():
        return await send_request("Say hello in one word.", "qwen-coder-14b")
    result = asyncio.run(_run())
    assert isinstance(result, LLMResponse)
    assert result.text
    assert result.cost_usd == 0.0
    assert result.provider == "ollama"
