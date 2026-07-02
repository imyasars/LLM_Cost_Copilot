import os
import time
from google import genai
from models.config import ModelConfig
from models.response import LLMResponse
from providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    def __init__(self):
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    async def send(self, prompt: str, config: ModelConfig) -> LLMResponse:
        start = time.monotonic()
        response = await self.client.aio.models.generate_content(
            model=config.api_name,
            contents=prompt,
        )
        latency_ms = (time.monotonic() - start) * 1000

        text = response.text
        input_tokens = response.usage_metadata.prompt_token_count or 0
        output_tokens = response.usage_metadata.candidates_token_count or 0
        cost = (input_tokens / 1000) * config.cost_per_1k_tokens

        return LLMResponse(
            model_id=config.model_id,
            provider="gemini",
            prompt=prompt,
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
        )
