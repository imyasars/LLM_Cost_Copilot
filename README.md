# ⚡ LLM Cost Autopilot

> **Reduced LLM API costs by ~80% while maintaining quality parity** — an intelligent routing system that automatically selects the cheapest model capable of handling each request.

## The Problem

Most teams route every prompt to GPT-4o or Anthropic Opus & Sonnet.. Over 60% of real-world prompts are simple Q&A, extraction, or formatting tasks that a $0.075/1M token model handles just as well.

## The Solution

Classify each prompt's complexity in **<1ms**, then route to the right model:

| Tier | Type | Models | Cost |
|---|---|---|---|
| 1 — Simple | Q&A, extraction, formatting | Gemini Flash, Llama 3 | $0.075/1M |
| 2 — Moderate | Summarization, classification | GPT-4o-mini, DeepSeek V3 | $0.15–0.27/1M |
| 3 — Complex | Reasoning, creative generation | GPT-4o, Claude Sonnet | $3–5/1M |

## Results

- **79.7% cost reduction** vs. routing everything to GPT-4o
- **4.33/5 average quality score** (verified by LLM-as-judge)
- **95.12% classifier accuracy** (RandomForest, 220+ labeled prompts)
- **<1ms routing latency** (pure Python feature extraction, no API call)

## Architecture

```
Prompt → Complexity Classifier → Routing Decision → Provider API
                                        ↓
                              Background Quality Verifier
                                        ↓
                              Auto-Escalation if needed
                                        ↓
                              SQLite Audit Log → Dashboard
```

## Tech Stack

- **Language:** Python 3.11
- **API:** FastAPI + Uvicorn
- **Classifier:** scikit-learn (RandomForest)
- **Providers:** OpenRouter (OpenAI, Anthropic, Google, DeepSeek, Meta)
- **Database:** SQLite
- **Dashboard:** Streamlit + Plotly
- **Containerization:** Docker + docker-compose

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/your-username/LLM_Cost_Autopilot.git
cd LLM_Cost_Autopilot
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# 3. Train the classifier
python -m classifier.train

# 4. Run tests
python -m pytest tests/ -v

# 5. Start the API
uvicorn api.app:app --reload --port 8000
# → Swagger UI at http://localhost:8000/docs

# 6. Seed demo data and launch dashboard
python scripts/seed_demo_data.py
streamlit run dashboard/app.py
# → Dashboard at http://localhost:8501
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/v1/completions` | Route and complete a prompt |
| `GET` | `/v1/models` | List all models and costs |
| `GET` | `/v1/stats` | Cost savings summary |
| `PUT` | `/v1/routing-config` | Hot-swap models at runtime |
| `GET` | `/health` | Health check |

**Example request:**
```bash
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the capital of France?", "task_type": "qa"}'
```

**Example response:**
```json
{
  "text": "The capital of France is Paris.",
  "model_id": "gemini-flash",
  "cost_usd": 0.000001,
  "routing": {
    "tier": 1,
    "tier_name": "Simple",
    "model_id": "gemini-flash"
  }
}
```

## Project Structure

```
├── models/          # ModelConfig registry (11 models)
├── providers/       # OpenRouter + Ollama provider implementations
├── router/          # Unified send_request() interface
├── classifier/      # RandomForest complexity classifier
├── routing/         # YAML routing config (hot-swappable)
├── verifier/        # LLM-as-judge + auto-escalation pipeline
├── audit/           # SQLite logging
├── dashboard/       # Streamlit cost dashboard
├── api/             # FastAPI service
├── scripts/         # Baseline test, load test, demo scripts
└── tests/           # 79 automated tests
```

## Running with Docker

```bash
docker-compose up --build
# API → http://localhost:8000
# Dashboard → http://localhost:8501
```

## Load Test

```bash
# Ensure API is running, then:
python scripts/load_test.py --total 500 --batch 10
```

## Get Your OpenRouter API Key

All 11 models (OpenAI, Anthropic, Google, DeepSeek, Meta) are accessed through a single [OpenRouter](https://openrouter.ai) key — no need for separate API accounts.

## License

MIT
