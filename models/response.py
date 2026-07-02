from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    model_id: str
    provider: str
    prompt: str
    text: str              # the actual reply
    input_tokens: int
    output_tokens: int
    latency_ms: float      # how long the call took
    cost_usd: float        # estimated cost

    def __str__(self) -> str:
        return (
            f"[{self.model_id}] {self.text[:120]}\n"
            f"  tokens: {self.input_tokens} in / {self.output_tokens} out | "
            f"latency: {self.latency_ms:.0f}ms | cost: ${self.cost_usd:.6f}"
        )
