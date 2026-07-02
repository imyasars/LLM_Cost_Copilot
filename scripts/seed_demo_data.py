"""
Seed 100 realistic demo transactions into the SQLite database.
Run: python scripts/seed_demo_data.py

Generates a realistic workload distribution:
  ~60% Tier 1 (Simple)   → cheap models
  ~25% Tier 2 (Moderate) → mid models
  ~15% Tier 3 (Complex)  → powerful models
with ~10% escalation rate and quality scores across the board.
"""
import sys
import os
import random
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from audit.db import init_db, insert_transaction

random.seed(42)

TIER1_MODELS   = ["gemini-flash", "llama-3-8b", "gpt-4o-mini", "claude-haiku-3.5"]
TIER2_MODELS   = ["gpt-4o-mini", "deepseek-v3", "gemini-pro"]
TIER3_MODELS   = ["gpt-4o", "claude-sonnet-4.5", "deepseek-r1"]

TIER1_PROMPTS = [
    "What is the capital of France?",
    "Convert 100 USD to EUR.",
    "What is 17 times 24?",
    "Translate 'Hello' into Spanish.",
    "Fix the typo: 'recieve'",
    "List the planets in the solar system.",
    "What is the boiling point of water?",
    "Who wrote Hamlet?",
    "Extract the email from: contact@example.com",
    "Format this date: 20240101",
]
TIER2_PROMPTS = [
    "Summarize this article in 3 bullet points.",
    "Classify this review as positive, negative, or neutral.",
    "Compare Python and JavaScript for backend development.",
    "Write a professional email declining a job offer.",
    "Generate a structured outline for a climate change presentation.",
    "Identify risks in this project plan.",
    "Analyze the sentiment of these customer feedback entries.",
    "Create a table comparing cloud providers.",
]
TIER3_PROMPTS = [
    "Design a scalable microservices architecture for a real-time payment system.",
    "Write a comprehensive business plan for a B2B SaaS startup.",
    "Analyze the ethical implications of predictive policing algorithms.",
    "Evaluate the trade-offs between database consistency models.",
    "Design a zero-trust network architecture for a hybrid cloud enterprise.",
    "Write a multi-step debugging plan for a production system with non-deterministic failures.",
]

# Cost per 1k input tokens per model
MODEL_COSTS = {
    "gemini-flash":      0.000075,
    "llama-3-8b":        0.00006,
    "gpt-4o-mini":       0.00015,
    "claude-haiku-3.5":  0.0008,
    "deepseek-v3":       0.00027,
    "gemini-pro":        0.00125,
    "gpt-4o":            0.005,
    "claude-sonnet-4.5": 0.003,
    "deepseek-r1":       0.0008,
}

MODEL_LATENCY = {
    "gemini-flash":      (800, 2000),
    "llama-3-8b":        (500, 1500),
    "gpt-4o-mini":       (1000, 2500),
    "claude-haiku-3.5":  (900, 2000),
    "deepseek-v3":       (1500, 4000),
    "gemini-pro":        (2000, 7000),
    "gpt-4o":            (1500, 4000),
    "claude-sonnet-4.5": (1500, 3500),
    "deepseek-r1":       (4000, 12000),
}

TASK_TYPES = ["qa", "summarization", "classification", "extraction", "reasoning", "general"]


def generate_transaction(day_offset: int):
    # Weighted tier selection
    tier = random.choices([1, 2, 3], weights=[60, 25, 15])[0]

    if tier == 1:
        model   = random.choice(TIER1_MODELS)
        prompt  = random.choice(TIER1_PROMPTS)
        tier_name = "Simple"
        in_tok  = random.randint(8, 30)
        out_tok = random.randint(5, 50)
        quality = random.choices([3, 4, 5], weights=[5, 35, 60])[0]
        task    = random.choice(["qa", "extraction", "general"])
    elif tier == 2:
        model   = random.choice(TIER2_MODELS)
        prompt  = random.choice(TIER2_PROMPTS)
        tier_name = "Moderate"
        in_tok  = random.randint(20, 80)
        out_tok = random.randint(30, 200)
        quality = random.choices([2, 3, 4, 5], weights=[5, 15, 50, 30])[0]
        task    = random.choice(["summarization", "classification", "general"])
    else:
        model   = random.choice(TIER3_MODELS)
        prompt  = random.choice(TIER3_PROMPTS)
        tier_name = "Complex"
        in_tok  = random.randint(40, 150)
        out_tok = random.randint(100, 500)
        quality = random.choices([2, 3, 4, 5], weights=[8, 20, 45, 27])[0]
        task    = random.choice(["reasoning", "general"])

    cost = (in_tok / 1000) * MODEL_COSTS.get(model, 0.001)
    lat_min, lat_max = MODEL_LATENCY.get(model, (1000, 3000))
    latency = random.uniform(lat_min, lat_max)

    # ~10% escalation rate
    escalated = random.random() < 0.10
    esc_model = None
    esc_cost  = 0.0
    if escalated:
        esc_model = "gpt-4o" if tier < 3 else "claude-sonnet-4.5"
        esc_cost  = (in_tok / 1000) * MODEL_COSTS[esc_model]

    ts = (datetime.now(timezone.utc) - timedelta(days=day_offset,
          seconds=random.randint(0, 86400))).isoformat()

    return dict(
        timestamp=ts,
        prompt_hash=hex(abs(hash(prompt + model)))[2:10],
        prompt_preview=prompt[:120],
        complexity_tier=tier,
        tier_name=tier_name,
        task_type=task,
        model_id=model,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_ms=latency,
        cost_usd=cost,
        quality_score=quality,
        quality_passed=quality >= 4,
        escalated=escalated,
        escalated_model=esc_model,
        escalation_cost=esc_cost,
    )


def seed(n: int = 100):
    init_db()
    print(f"Seeding {n} demo transactions...")
    for i in range(n):
        day_offset = random.randint(0, 13)   # spread across 2 weeks
        tx = generate_transaction(day_offset)
        insert_transaction(**tx)
    print(f"✅ Done — {n} transactions written to data/transactions.db")


if __name__ == "__main__":
    seed(100)
