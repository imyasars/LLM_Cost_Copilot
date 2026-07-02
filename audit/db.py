"""
SQLite audit database for Phase 4.

Schema — transactions table:
  id               INTEGER  primary key
  timestamp        TEXT     ISO-8601 UTC
  prompt_hash      TEXT     md5 of prompt
  prompt_preview   TEXT     first 120 chars
  complexity_tier  INTEGER  1 / 2 / 3
  tier_name        TEXT     Simple / Moderate / Complex
  task_type        TEXT     qa / summarization / etc.
  model_id         TEXT     model that answered
  input_tokens     INTEGER
  output_tokens    INTEGER
  latency_ms       REAL
  cost_usd         REAL
  baseline_cost    REAL     cost if GPT-4o had answered
  quality_score    INTEGER  1–5 (NULL if not verified)
  quality_passed   INTEGER  1 / 0 / NULL
  escalated        INTEGER  1 / 0
  escalated_model  TEXT     NULL if no escalation
  escalation_cost  REAL     extra cost from escalation (0 if none)
"""
from __future__ import annotations

import pathlib
import sqlite3
from contextlib import contextmanager
from typing import Optional

DB_PATH = pathlib.Path(__file__).parent.parent / "data" / "transactions.db"

# GPT-4o cost used as the "baseline" for savings calculations
BASELINE_MODEL_COST_PER_1K = 0.005   # $5 / 1M tokens


def init_db(db_path: pathlib.Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp        TEXT    NOT NULL,
                prompt_hash      TEXT    NOT NULL,
                prompt_preview   TEXT    NOT NULL,
                complexity_tier  INTEGER NOT NULL,
                tier_name        TEXT    NOT NULL,
                task_type        TEXT    NOT NULL,
                model_id         TEXT    NOT NULL,
                input_tokens     INTEGER NOT NULL,
                output_tokens    INTEGER NOT NULL,
                latency_ms       REAL    NOT NULL,
                cost_usd         REAL    NOT NULL,
                baseline_cost    REAL    NOT NULL,
                quality_score    INTEGER,
                quality_passed   INTEGER,
                escalated        INTEGER NOT NULL DEFAULT 0,
                escalated_model  TEXT,
                escalation_cost  REAL    NOT NULL DEFAULT 0.0
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON transactions(timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_model ON transactions(model_id)"
        )


def insert_transaction(
    timestamp: str,
    prompt_hash: str,
    prompt_preview: str,
    complexity_tier: int,
    tier_name: str,
    task_type: str,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    cost_usd: float,
    quality_score: Optional[int] = None,
    quality_passed: Optional[bool] = None,
    escalated: bool = False,
    escalated_model: Optional[str] = None,
    escalation_cost: float = 0.0,
    db_path: pathlib.Path = DB_PATH,
) -> int:
    baseline_cost = (input_tokens / 1000) * BASELINE_MODEL_COST_PER_1K
    with _connect(db_path) as conn:
        cur = conn.execute("""
            INSERT INTO transactions (
                timestamp, prompt_hash, prompt_preview,
                complexity_tier, tier_name, task_type,
                model_id, input_tokens, output_tokens,
                latency_ms, cost_usd, baseline_cost,
                quality_score, quality_passed,
                escalated, escalated_model, escalation_cost
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            timestamp, prompt_hash, prompt_preview,
            complexity_tier, tier_name, task_type,
            model_id, input_tokens, output_tokens,
            latency_ms, cost_usd, baseline_cost,
            quality_score,
            int(quality_passed) if quality_passed is not None else None,
            int(escalated), escalated_model, escalation_cost,
        ))
        return cur.lastrowid


def get_all_transactions(db_path: pathlib.Path = DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY timestamp DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats(db_path: pathlib.Path = DB_PATH) -> dict:
    with _connect(db_path) as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)                          AS total_requests,
                SUM(cost_usd)                     AS total_cost,
                SUM(baseline_cost)                AS total_baseline_cost,
                AVG(cost_usd)                     AS avg_cost,
                AVG(latency_ms)                   AS avg_latency_ms,
                SUM(input_tokens + output_tokens) AS total_tokens,
                SUM(escalated)                    AS escalation_count,
                AVG(quality_score)                AS avg_quality_score
            FROM transactions
        """).fetchone()

    total_cost     = row[1] or 0.0
    baseline_cost  = row[2] or 0.0
    savings        = baseline_cost - total_cost
    savings_pct    = (savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

    return {
        "total_requests":    row[0] or 0,
        "total_cost":        total_cost,
        "total_baseline":    baseline_cost,
        "total_savings":     savings,
        "savings_pct":       savings_pct,
        "avg_cost":          row[3] or 0.0,
        "avg_latency_ms":    row[4] or 0.0,
        "total_tokens":      row[5] or 0,
        "escalation_count":  row[6] or 0,
        "avg_quality_score": row[7],
    }


def get_model_distribution(db_path: pathlib.Path = DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("""
            SELECT model_id,
                   COUNT(*)       AS request_count,
                   SUM(cost_usd)  AS total_cost,
                   AVG(latency_ms) AS avg_latency
            FROM transactions
            GROUP BY model_id
            ORDER BY request_count DESC
        """).fetchall()
    return [{"model_id": r[0], "request_count": r[1],
             "total_cost": r[2], "avg_latency": r[3]} for r in rows]


def get_tier_distribution(db_path: pathlib.Path = DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("""
            SELECT complexity_tier, tier_name, COUNT(*) AS request_count,
                   SUM(cost_usd) AS total_cost
            FROM transactions
            GROUP BY complexity_tier
            ORDER BY complexity_tier
        """).fetchall()
    return [{"tier": r[0], "tier_name": r[1],
             "request_count": r[2], "total_cost": r[3]} for r in rows]


def get_cost_over_time(db_path: pathlib.Path = DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("""
            SELECT DATE(timestamp) AS day,
                   SUM(cost_usd)       AS actual_cost,
                   SUM(baseline_cost)  AS baseline_cost,
                   COUNT(*)            AS requests
            FROM transactions
            GROUP BY day
            ORDER BY day
        """).fetchall()
    return [{"day": r[0], "actual_cost": r[1],
             "baseline_cost": r[2], "requests": r[3]} for r in rows]


def get_quality_distribution(db_path: pathlib.Path = DB_PATH) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("""
            SELECT quality_score, COUNT(*) AS count
            FROM transactions
            WHERE quality_score IS NOT NULL
            GROUP BY quality_score
            ORDER BY quality_score
        """).fetchall()
    return [{"score": r[0], "count": r[1]} for r in rows]


@contextmanager
def _connect(db_path: pathlib.Path):
    conn = sqlite3.connect(str(db_path))
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
