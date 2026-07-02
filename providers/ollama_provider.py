import os
import time
import httpx
from models.config import ModelConfig
from models.response import LLMResponse
from providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    def __init__(self):
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    async def send(self, prompt: str, config: ModelConfig) -> LLMResponse:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": config.api_name, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            data = response.json()

        latency_ms = (time.monotonic() - start) * 1000
        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        return LLMResponse(
            model_id=config.model_id,
            provider="ollama",
            prompt=prompt,
            text=data["response"],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=0.0,
        )
