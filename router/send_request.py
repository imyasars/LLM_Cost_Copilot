from models.config import MODELS, ModelConfig
from models.response import LLMResponse
from providers.base import BaseProvider


def _get_provider(provider_name: str) -> BaseProvider:
    if provider_name == "openrouter":
        from providers.openrouter_provider import OpenRouterProvider
        return OpenRouterProvider()
    elif provider_name == "anthropic":
        from providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    elif provider_name == "ollama":
        from providers.ollama_provider import OllamaProvider
        return OllamaProvider()
    elif provider_name == "gemini":
        from providers.gemini_provider import GeminiProvider
        return GeminiProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


async def send_request(prompt: str, model_id: str) -> LLMResponse:
    """Send a prompt to any model using a single unified interface."""
    if model_id not in MODELS:
        raise ValueError(f"Unknown model_id '{model_id}'. Available: {list(MODELS.keys())}")

    config = MODELS[model_id]
    provider = _get_provider(config.provider)
    return await provider.send(prompt, config)
