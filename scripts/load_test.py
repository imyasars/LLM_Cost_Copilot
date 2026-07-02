"""
Phase 6 — Load Test
Sends 500+ diverse prompts through the FastAPI service in concurrent batches.
Generates realistic DB data for the dashboard and prints a cost summary.

Run (API must be running on port 8000):
    python scripts/load_test.py

Options:
    --total   Number of prompts  (default: 500)
    --batch   Concurrent batch size (default: 10)
    --url     API base URL (default: http://localhost:8000)
"""
import asyncio
import argparse
import random
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import certifi
import httpx
from dotenv import load_dotenv
load_dotenv()

random.seed(99)

# ── Prompt pool (150 diverse prompts across all tiers) ────────────────────────

PROMPTS = [
    # ── Tier 1 / Simple ──────────────────────────────────────────────────────
    ("What is the capital of France?",                                    "qa"),
    ("Convert 100 USD to EUR.",                                           "qa"),
    ("What is 17 times 24?",                                              "qa"),
    ("Translate 'Hello, how are you?' into Spanish.",                     "qa"),
    ("What day of the week is 2024-12-25?",                               "qa"),
    ("Extract all email addresses from: contact@example.com, info@test.org", "extraction"),
    ("Format this date: 20240101 → January 1, 2024",                     "extraction"),
    ("List the planets in the solar system.",                             "qa"),
    ("What is the boiling point of water in Celsius?",                   "qa"),
    ("Who wrote Hamlet?",                                                 "qa"),
    ("What is the HTTP status code for Not Found?",                      "qa"),
    ("Fix the typo: recieve → correct spelling.",                         "extraction"),
    ("What does HTML stand for?",                                         "qa"),
    ("Extract the phone number from: Call us at 555-123-4567",           "extraction"),
    ("What is the square root of 144?",                                   "qa"),
    ("Translate Goodbye into French.",                                    "qa"),
    ("List three primary colors.",                                        "qa"),
    ("What year did World War II end?",                                   "qa"),
    ("Convert 10 kilometers to miles.",                                   "qa"),
    ("What programming language uses .py extension?",                     "qa"),
    ("Capitalize: hello world",                                           "extraction"),
    ("What is the ISO code for the United States?",                      "qa"),
    ("How many bytes are in a kilobyte?",                                 "qa"),
    ("What is 2 to the power of 10?",                                    "qa"),
    ("Translate Thank you into Japanese.",                                "qa"),
    ("Remove duplicates: 1, 2, 2, 3, 3, 4",                             "extraction"),
    ("What does API stand for?",                                          "qa"),
    ("Format phone number: 5551234567 → (555) 123-4567",                "extraction"),
    ("Who invented the telephone?",                                       "qa"),
    ("What is the chemical symbol for gold?",                            "qa"),
    ("Convert 32 degrees Fahrenheit to Celsius.",                        "qa"),
    ("What is the largest ocean on Earth?",                              "qa"),
    ("What year was Python first released?",                             "qa"),
    ("Who is the author of 1984?",                                       "qa"),
    ("What is the default port for HTTPS?",                              "qa"),
    ("Extract domain from: https://www.example.com/path",               "extraction"),
    ("What is 15 percent of 200?",                                       "qa"),
    ("What does RAM stand for?",                                         "qa"),
    ("Convert 1 hour to seconds.",                                       "qa"),
    ("What is the tallest mountain in the world?",                       "qa"),
    ("How many sides does a hexagon have?",                              "qa"),
    ("What is the atomic number of carbon?",                             "qa"),
    ("Translate Please into Italian.",                                   "qa"),
    ("What does JSON stand for?",                                        "qa"),
    ("What is the speed of light in km/s?",                              "qa"),
    ("What is the capital of Japan?",                                    "qa"),
    ("Who painted the Mona Lisa?",                                       "qa"),
    ("What is 1000 divided by 8?",                                       "qa"),
    ("What does CSS stand for?",                                         "qa"),
    ("What is the next number: 2, 4, 6, 8?",                            "qa"),

    # ── Tier 2 / Moderate ────────────────────────────────────────────────────
    ("Summarize this in 3 bullet points: Large language models learn from vast text corpora. They generate coherent responses across diverse tasks. They require significant compute to train.", "summarization"),
    ("Classify this review as positive, negative, or neutral: The product arrived on time but the packaging was damaged.", "classification"),
    ("Compare Python and JavaScript for backend web development.",        "general"),
    ("Write a professional email declining a meeting invitation.",        "general"),
    ("Generate a structured outline for a presentation on climate change.", "general"),
    ("Identify potential risks in this plan: Launch new product in Q3 with minimal testing budget.", "general"),
    ("Rewrite this paragraph to be more concise: The meeting that was scheduled for tomorrow morning has been postponed until next week due to several conflicts that arose.", "general"),
    ("Analyze the sentiment of: I love this product! Best purchase ever.", "classification"),
    ("Create a comparison table for AWS, Azure, and Google Cloud.",       "general"),
    ("Summarize the key differences between REST and GraphQL APIs.",      "summarization"),
    ("Write a product description for a wireless ergonomic keyboard.",    "general"),
    ("Identify inconsistencies: Sales up 10% but revenue down 5%.",      "general"),
    ("Create a weekly vegetarian meal plan under 2000 calories per day.", "general"),
    ("Summarize this legal clause in plain English: The licensor grants the licensee a non-exclusive, royalty-free license.", "summarization"),
    ("Generate 5 social media post ideas for a coffee shop.",            "general"),
    ("Analyze this job description and list the top 5 required skills: Senior Python Engineer with 5+ years experience, AWS expertise, and strong communication skills.", "extraction"),
    ("Write a structured comparison of Docker and virtual machines.",     "general"),
    ("Summarize the main purpose of a README file in software projects.", "summarization"),
    ("Create a structured interview guide for a data analyst position.",  "general"),
    ("Extract all action items from: John will send the report by Friday. Mary will schedule the follow-up meeting. Team will review by end of month.", "extraction"),
    ("Analyze this code structure and suggest improvements: function f(x) { return x * x; }",  "general"),
    ("Write a summary of quarterly earnings for a non-technical audience: Revenue $2.3B up 12%, EPS $1.45, margins improved to 23%.", "summarization"),
    ("Classify these transactions: salary credit $5000, grocery $150, Netflix $15, rent $2000.", "classification"),
    ("Identify the tone of this text: We are thrilled to announce our groundbreaking new product!", "classification"),
    ("Generate a list of pros and cons for remote work.",                "general"),
    ("Summarize the key features of Python from its official documentation perspective.", "summarization"),
    ("Categorize these errors: 404 Not Found, 500 Internal Server Error, 401 Unauthorized.", "classification"),
    ("Write an abstract for a research paper on machine learning in healthcare.", "general"),
    ("Create a structured glossary of 5 machine learning terms.",        "general"),
    ("Summarize user feedback themes: Users want faster load times, better mobile experience, and more keyboard shortcuts.", "summarization"),
    ("Compare the pricing models: per-seat vs usage-based SaaS billing.", "general"),
    ("Write a changelog entry for: fixed login bug, added dark mode, improved performance.", "general"),
    ("Classify these bug severities: app crashes on launch, button misaligned, data loss on save.", "classification"),
    ("Generate a structured learning roadmap for full-stack development.", "general"),
    ("Create a SWOT analysis for a startup entering the food delivery market.", "general"),

    # ── Tier 3 / Complex ─────────────────────────────────────────────────────
    ("Design a scalable microservices architecture for a real-time payment processing system handling 10,000 transactions per second with strong consistency guarantees.", "reasoning"),
    ("Write a detailed essay arguing whether artificial general intelligence poses an existential risk to humanity, considering both accelerationist and safety perspectives.", "reasoning"),
    ("Analyze the philosophical implications of Gödel incompleteness theorems for the foundations of mathematics and formal systems.", "reasoning"),
    ("Design a machine learning pipeline to detect financial fraud, including feature engineering, model selection, evaluation strategy, and production monitoring.", "reasoning"),
    ("Write a comprehensive business plan for a B2B SaaS startup targeting the healthcare compliance market, including go-to-market strategy and financial projections.", "reasoning"),
    ("Critically evaluate the long-term geopolitical consequences of de-dollarization trends in emerging markets and implications for global trade.", "reasoning"),
    ("Design a distributed caching strategy for a social media platform with 100 million daily active users requiring sub-10ms read latency.", "reasoning"),
    ("Analyze competing theories of consciousness including functionalism, biological naturalism, and integrated information theory.", "reasoning"),
    ("Design a multi-tenant SaaS authorization system supporting RBAC, ABAC, and row-level security simultaneously with audit logging.", "reasoning"),
    ("Develop a pricing strategy for a new enterprise SaaS product considering value-based, cost-plus, and competitive pricing models with churn sensitivity analysis.", "reasoning"),
    ("Write a nuanced analysis of how algorithmic bias in hiring tools perpetuates systemic inequality and propose mitigation strategies.", "reasoning"),
    ("Design a fault-tolerant event sourcing system with CQRS for a banking application with strict audit requirements and regulatory compliance.", "reasoning"),
    ("Evaluate the trade-offs between strong, eventual, and causal consistency models for a globally distributed e-commerce application.", "reasoning"),
    ("Write a detailed technical proposal for migrating a monolithic Rails application to microservices with zero downtime using a strangler fig pattern.", "reasoning"),
    ("Analyze the ethical implications of predictive policing algorithms and propose comprehensive policy safeguards and oversight mechanisms.", "reasoning"),
    ("Design a recommendation system balancing personalization, diversity, and serendipity while avoiding filter bubbles and optimizing long-term engagement.", "reasoning"),
    ("Write a comparative analysis of Keynesian, Monetarist, and Modern Monetary Theory approaches to managing economic recessions.", "reasoning"),
    ("Develop a comprehensive security threat model for a cloud-native healthcare application storing PHI data under HIPAA compliance.", "reasoning"),
    ("Design a real-time bidding system for programmatic advertising with sub-100ms latency handling 500k requests per second.", "reasoning"),
    ("Evaluate competing approaches to AI alignment including RLHF, Constitutional AI, and interpretability-first methods with long-term safety implications.", "reasoning"),
    ("Write a detailed post-mortem for a hypothetical major cloud outage including root cause analysis, timeline reconstruction, and remediation plan.", "reasoning"),
    ("Design a data governance framework for a multinational company subject to GDPR, CCPA, and emerging AI regulations across 15 jurisdictions.", "reasoning"),
    ("Write a critical analysis of whether Web3 and blockchain technology deliver on their decentralization promises or represent regulatory arbitrage.", "reasoning"),
    ("Create a multi-phase product strategy for an LLM API company entering a market dominated by OpenAI and Anthropic.", "reasoning"),
    ("Analyze the second and third-order effects of widespread autonomous vehicle adoption on urban planning, labor markets, and insurance industries.", "reasoning"),
    ("Design a chaos engineering program for a complex distributed system including failure injection strategies, game days, and success metrics.", "reasoning"),
    ("Write a deep technical analysis of how transformer architecture innovations contributed to the success of large language models.", "reasoning"),
    ("Develop a long-term AI strategy for a mid-size insurance company including build vs buy decisions, risk management, and regulatory compliance.", "reasoning"),
    ("Design a zero-trust network architecture for a hybrid cloud enterprise with legacy on-premises systems and 10,000 remote employees.", "reasoning"),
    ("Analyze how Goodhart Law applies to LLM evaluation benchmarks and propose more robust evaluation frameworks resistant to gaming.", "reasoning"),
    ("Write a strategic analysis of competitive dynamics between open-source and proprietary AI models through 2030 with investment implications.", "reasoning"),
    ("Develop a full technical roadmap for building a production-grade LLM inference engine covering batching, quantization, KV-cache, and serving.", "reasoning"),
    ("Design a federated learning system for healthcare that preserves patient privacy while enabling collaborative model training across hospital networks.", "reasoning"),
    ("Analyze the interplay between network effects, switching costs, and competitive moats in platform businesses with examples from tech giants.", "reasoning"),
    ("Write a philosophy of mind analysis comparing functionalism, biological naturalism, and panpsychism as explanations for consciousness.", "reasoning"),
]


def build_pool(total: int) -> list[tuple[str, str]]:
    """Sample prompts to reach the target total, maintaining tier distribution."""
    pool = []
    while len(pool) < total:
        pool.extend(random.sample(PROMPTS, min(len(PROMPTS), total - len(pool))))
    return pool[:total]


async def send_one(
    client: httpx.AsyncClient,
    prompt: str,
    task_type: str,
    idx: int,
    total: int,
) -> dict:
    try:
        r = await client.post(
            "/v1/completions",
            json={"prompt": prompt, "task_type": task_type, "verify": False},
            timeout=30.0,
        )
        if r.status_code == 200:
            data = r.json()
            tier = data["routing"]["tier"]
            model = data["model_id"]
            cost = data["cost_usd"]
            print(f"  [{idx:>4}/{total}] ✅ Tier {tier} → {model:<20} ${cost:.6f}")
            return {"ok": True, **data}
        else:
            print(f"  [{idx:>4}/{total}] ❌ HTTP {r.status_code}: {r.text[:60]}")
            return {"ok": False}
    except Exception as e:
        print(f"  [{idx:>4}/{total}] ❌ {type(e).__name__}: {str(e)[:60]}")
        return {"ok": False}


async def run_load_test(total: int, batch_size: int, base_url: str):
    pool = build_pool(total)

    print(f"\n{'='*65}")
    print(f"  Phase 6 — Load Test")
    print(f"  {total} prompts · batch size {batch_size} · {base_url}")
    print(f"{'='*65}\n")

    results = []
    start = time.monotonic()

    async with httpx.AsyncClient(
        base_url=base_url,
        verify=certifi.where(),
    ) as client:
        for batch_start in range(0, total, batch_size):
            batch = pool[batch_start: batch_start + batch_size]
            tasks = [
                send_one(client, prompt, task_type, batch_start + i + 1, total)
                for i, (prompt, task_type) in enumerate(batch)
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

    elapsed = time.monotonic() - start

    # ── Summary ──────────────────────────────────────────────────────────────
    ok = [r for r in results if r.get("ok")]
    failed = total - len(ok)

    tier_counts = {1: 0, 2: 0, 3: 0}
    model_counts: dict[str, int] = {}
    total_cost = 0.0

    for r in ok:
        tier = r["routing"]["tier"]
        model = r["model_id"]
        cost = r["cost_usd"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        model_counts[model] = model_counts.get(model, 0) + 1
        total_cost += cost

    # Baseline: what gpt-4o would have cost
    avg_input_tokens = sum(r.get("input_tokens", 20) for r in ok) / max(len(ok), 1)
    baseline_cost = (avg_input_tokens / 1000) * 0.005 * len(ok)
    savings = baseline_cost - total_cost
    savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

    print(f"\n{'='*65}")
    print(f"  LOAD TEST RESULTS")
    print(f"{'='*65}")
    print(f"  Total prompts : {total}")
    print(f"  Successful    : {len(ok)}")
    print(f"  Failed        : {failed}")
    print(f"  Elapsed       : {elapsed:.1f}s  ({len(ok)/elapsed:.1f} req/s)")
    print(f"\n  Cost Summary")
    print(f"  {'─'*40}")
    print(f"  Actual cost   : ${total_cost:.4f}")
    print(f"  GPT-4o baseline: ${baseline_cost:.4f}")
    print(f"  Savings       : ${savings:.4f}  ({savings_pct:.1f}%)")
    print(f"\n  Tier Distribution")
    print(f"  {'─'*40}")
    for tier, count in sorted(tier_counts.items()):
        name = {1: "Simple", 2: "Moderate", 3: "Complex"}[tier]
        pct = count / max(len(ok), 1) * 100
        print(f"  Tier {tier} ({name:<8}) : {count:>4} requests ({pct:.1f}%)")
    print(f"\n  Top Models Used")
    print(f"  {'─'*40}")
    for model, count in sorted(model_counts.items(), key=lambda x: -x[1]):
        print(f"  {model:<24} : {count:>4} requests")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--total",  type=int, default=500)
    parser.add_argument("--batch",  type=int, default=10)
    parser.add_argument("--url",    type=str, default="http://localhost:8000")
    args = parser.parse_args()

    asyncio.run(run_load_test(args.total, args.batch, args.url))
