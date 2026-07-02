import os
import time
import certifi
import httpx
from openai import AsyncOpenAI
from models.config import ModelConfig
from models.response import LLMResponse
from providers.base import BaseProvider


class OpenRouterProvider(BaseProvider):
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
            http_client=httpx.AsyncClient(verify=certifi.where()),
        )

    async def send(self, prompt: str, config: ModelConfig) -> LLMResponse:
        start = time.monotonic()
        response = await self.client.chat.completions.create(
            model=config.api_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        latency_ms = (time.monotonic() - start) * 1000

        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens / 1000) * config.cost_per_1k_tokens

        return LLMResponse(
            model_id=config.model_id,
            provider="openrouter",
            prompt=prompt,
            text=response.choices[0].message.content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
        )
