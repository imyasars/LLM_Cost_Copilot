"""
Phase 3 end-to-end demo — shows the full smart_request pipeline.
Run: python scripts/test_phase3.py
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

from verifier.pipeline import smart_request

TIER_COLORS = {1: "\033[92m", 2: "\033[93m", 3: "\033[91m"}
RESET = "\033[0m"

TEST_CASES = [
    {
        "prompt": "What is the capital of France?",
        "task_type": "qa",
        "label": "Simple Q&A",
    },
    {
        "prompt": (
            "what is apple its a fruit or mobile"
        ),
        "task_type": "summarization",
        "label": "Summarization",
    },
    {
        "prompt": (
            "Design a scalable microservices architecture for a real-time payment "
            "processing system that must handle 10,000 transactions per second with "
            "strong consistency guarantees and sub-100ms latency."
        ),
        "task_type": "reasoning",
        "label": "Complex Reasoning",
    },
]


async def run_demo():
    print(f"\n{'='*65}")
    print("  Phase 3 — Smart Request Pipeline Demo")
    print("  (route → send → verify in background → escalate if needed)")
    print(f"{'='*65}\n")

    for i, case in enumerate(TEST_CASES, 1):
        print(f"── Test {i}: {case['label']} ──────────────────────────────────")
        print(f"  Prompt   : {case['prompt'][:80]}{'...' if len(case['prompt']) > 80 else ''}")

        result = await smart_request(
            prompt=case["prompt"],
            task_type=case["task_type"],
            wait_for_verification=True,   # block so demo shows verdict
        )

        color = TIER_COLORS[result.routing.tier]
        print(f"  Routing  : {color}Tier {result.routing.tier} ({result.routing.tier_name}){RESET} → {result.routing.model_id}")
        print(f"  Response : {result.response.text[:120].strip()}...")
        print(f"  Tokens   : {result.response.input_tokens} in / {result.response.output_tokens} out")
        print(f"  Cost     : ${result.response.cost_usd:.6f} | Latency: {result.response.latency_ms:.0f}ms")

        if result.escalation and result.escalation.triggered:
            print(f"  \033[91m⚠ ESCALATED\033[0m → {result.escalation.escalated_model}")
            print(f"  Reason   : {result.escalation.reason[:100]}")
            if result.escalation.escalated_response:
                er = result.escalation.escalated_response
                print(f"  Escalated: {er.text[:120].strip()}...")
                print(f"  Extra cost: ${result.escalation.cost_delta_usd:.6f}")
        else:
            print(f"  \033[92m✅ Quality passed — no escalation needed\033[0m")

        print()

    print(f"{'='*65}")
    print("Demo complete!")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
