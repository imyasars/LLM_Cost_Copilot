"""
Baseline test script for Phase 1.
Run: python scripts/baseline_test.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from router.send_request import send_request

TEST_PROMPTS = [
    "What is 2 + 2?",
    "In one sentence, what is the capital of France?",
    "Give me a one-line Python function that reverses a string.",
]

MODELS_TO_TEST = []

if os.environ.get("OPENROUTER_API_KEY", "").startswith("sk-or-"):
    MODELS_TO_TEST += [
        "gpt-4o-mini", "llama-3-8b",
        "gemini-flash", "gemini-pro",
        "deepseek-v3", "deepseek-r1",
        "claude-haiku-3.5", "claude-sonnet-4.5",
    ]
else:
    print("⚠️  Skipping OpenRouter models — OPENROUTER_API_KEY not set in .env")

# Ollama models are always tested (they run locally)
MODELS_TO_TEST += ["qwen-coder-1.5b", "qwen-coder-14b"]


async def test_model(model_id: str, prompt: str):
    try:
        result = await send_request(prompt, model_id)
        print(f"\n✅ {result}")
    except Exception as e:
        print(f"\n❌ [{model_id}] FAILED: {e}")


async def main():
    if not MODELS_TO_TEST:
        print("\n❌ No models to test. Please add OPENROUTER_API_KEY to .env")
        return

    print(f"\n{'='*60}")
    print(f"Testing {len(MODELS_TO_TEST)} model(s) with {len(TEST_PROMPTS)} prompt(s)")
    print(f"{'='*60}")

    for prompt in TEST_PROMPTS:
        print(f"\nPrompt: \"{prompt}\"")
        for model_id in MODELS_TO_TEST:
            await test_model(model_id, prompt)

    print(f"\n{'='*60}")
    print("Baseline test complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
