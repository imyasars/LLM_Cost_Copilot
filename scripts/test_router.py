"""
Interactive Phase 2 test — shows how the router classifies prompts and picks models.
Run: python scripts/test_router.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from routing.router import route

PROMPTS = [
    # Tier 1 — Simple
    "What is the capital of France?",
    "Convert 100 USD to EUR.",
    "Fix the typo: 'recieve'",

    # Tier 2 — Moderate
    "Summarize this article in 3 bullet points.",
    "Classify this customer review as positive, negative, or neutral.",
    "Compare Python and JavaScript for backend development.",

    # Tier 3 — Complex
    "Design a fault-tolerant microservices architecture for a real-time payment system handling 10,000 TPS.",
    "Write a comprehensive business plan for a B2B SaaS startup, including go-to-market strategy and financial projections.",
    "Critically analyze the ethical implications and long-term consequences of deploying predictive policing algorithms in urban areas.",
]

TIER_COLORS = {1: "\033[92m", 2: "\033[93m", 3: "\033[91m"}  # green / yellow / red
RESET = "\033[0m"

print(f"\n{'='*65}")
print("  Phase 2 — Complexity Router Test")
print(f"{'='*65}\n")

for prompt in PROMPTS:
    d = route(prompt)
    color = TIER_COLORS[d.tier]
    print(f"{color}Tier {d.tier} ({d.tier_name}){RESET} → {d.model_id}")
    print(f"  Prompt   : {prompt}")
    print(f"  Fallbacks: {' → '.join(d.fallback_models)}")
    print()

print(f"{'='*65}")
print("Routing map:")
print("  Tier 1 (Simple)   → gemini-flash   (cheapest)")
print("  Tier 2 (Moderate) → gpt-4o-mini    (balanced)")
print("  Tier 3 (Complex)  → gpt-4o         (most capable)")
print(f"{'='*65}\n")
