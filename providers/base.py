from abc import ABC, abstractmethod
from models.config import ModelConfig
from models.response import LLMResponse


class BaseProvider(ABC):
    @abstractmethod
    async def send(self, prompt: str, config: ModelConfig) -> LLMResponse:
        """Send a prompt and return a structured LLMResponse."""
        ...
