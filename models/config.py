from dataclasses import dataclass


@dataclass
class ModelConfig:
    model_id: str        # unique key, e.g. "gpt-4o-mini"
    provider: str        # "openrouter" | "ollama"
    api_name: str        # exact name sent to the provider API
    cost_per_1k_tokens: float  # USD, input tokens
    tier: int            # 1=cheap, 2=mid, 3=powerful


MODELS: dict[str, ModelConfig] = {
    # --- OpenAI via OpenRouter ---
    "gpt-4o-mini": ModelConfig(
        model_id="gpt-4o-mini",
        provider="openrouter",
        api_name="openai/gpt-4o-mini",
        cost_per_1k_tokens=0.00015,
        tier=1,
    ),
    "gpt-4o": ModelConfig(
        model_id="gpt-4o",
        provider="openrouter",
        api_name="openai/gpt-4o",
        cost_per_1k_tokens=0.005,
        tier=3,
    ),
    # --- Gemini via OpenRouter (same OPENROUTER_API_KEY) ---
    "gemini-flash": ModelConfig(
        model_id="gemini-flash",
        provider="openrouter",
        api_name="google/gemini-2.5-flash",
        cost_per_1k_tokens=0.000075,
        tier=1,
    ),
    "gemini-pro": ModelConfig(
        model_id="gemini-pro",
        provider="openrouter",
        api_name="google/gemini-2.5-pro",
        cost_per_1k_tokens=0.00125,
        tier=2,
    ),
    # --- Free models via OpenRouter ---
    "llama-3-8b": ModelConfig(
        model_id="llama-3-8b",
        provider="openrouter",
        api_name="meta-llama/llama-3-8b-instruct",
        cost_per_1k_tokens=0.00006,
        tier=1,
    ),
    "gemma-7b": ModelConfig(
        model_id="gemma-7b",
        provider="openrouter",
        api_name="google/gemma-7b-it:free",
        cost_per_1k_tokens=0.0,
        tier=1,
    ),
    # --- Anthropic via OpenRouter (same OPENROUTER_API_KEY) ---
    "claude-haiku-3.5": ModelConfig(
        model_id="claude-haiku-3.5",
        provider="openrouter",
        api_name="anthropic/claude-haiku-4.5",
        cost_per_1k_tokens=0.0008,
        tier=1,
    ),
    "claude-sonnet-4.5": ModelConfig(
        model_id="claude-sonnet-4.5",
        provider="openrouter",
        api_name="anthropic/claude-sonnet-4-5",
        cost_per_1k_tokens=0.003,
        tier=3,
    ),
    # --- DeepSeek via OpenRouter (same OPENROUTER_API_KEY) ---
    "deepseek-v3": ModelConfig(
        model_id="deepseek-v3",
        provider="openrouter",
        api_name="deepseek/deepseek-chat-v3-0324",
        cost_per_1k_tokens=0.00027,
        tier=2,
    ),
    "deepseek-r1": ModelConfig(
        model_id="deepseek-r1",
        provider="openrouter",
        api_name="deepseek/deepseek-r1-0528",
        cost_per_1k_tokens=0.0008,
        tier=3,
    ),
    # --- Ollama (local, free) ---
    "qwen-coder-14b": ModelConfig(
        model_id="qwen-coder-14b",
        provider="ollama",
        api_name="qwen2.5-coder:14b",
        cost_per_1k_tokens=0.0,
        tier=2,
    ),
    "qwen-coder-1.5b": ModelConfig(
        model_id="qwen-coder-1.5b",
        provider="ollama",
        api_name="qwen2.5-coder:1.5b",
        cost_per_1k_tokens=0.0,
        tier=1,
    ),
}
