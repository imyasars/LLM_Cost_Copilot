import os
import time
import anthropic
from models.config import ModelConfig
from models.response import LLMResponse
from providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    async def send(self, prompt: str, config: ModelConfig) -> LLMResponse:
        start = time.monotonic()
        response = await self.client.messages.create(
            model=config.api_name,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = (time.monotonic() - start) * 1000

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens / 1000) * config.cost_per_1k_tokens

        return LLMResponse(
            model_id=config.model_id,
            provider="anthropic",
            prompt=prompt,
            text=response.content[0].text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
        )
