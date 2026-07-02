"""Tests for Phase 4: Logging and Cost Dashboard."""
from __future__ import annotations

import pathlib
import tempfile
import pytest

from audit.db import (
    init_db, insert_transaction, get_all_transactions,
    get_stats, get_model_distribution, get_tier_distribution,
    get_cost_over_time, get_quality_distribution,
    BASELINE_MODEL_COST_PER_1K,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    """Fresh in-memory DB for each test."""
    db = tmp_path / "test.db"
    init_db(db)
    return db


def insert_sample(db, **overrides):
    defaults = dict(
        timestamp="2026-07-01T10:00:00+00:00",
        prompt_hash="abc12345",
        prompt_preview="What is the capital of France?",
        complexity_tier=1,
        tier_name="Simple",
        task_type="qa",
        model_id="gemini-flash",
        input_tokens=15,
        output_tokens=8,
        latency_ms=1200.0,
        cost_usd=0.000001,
        quality_score=5,
        quality_passed=True,
        escalated=False,
        escalated_model=None,
        escalation_cost=0.0,
        db_path=db,
    )
    defaults.update(overrides)
    return insert_transaction(**defaults)


# ── DB schema and insert ──────────────────────────────────────────────────────

def test_init_db_creates_table(tmp_db):
    import sqlite3
    conn = sqlite3.connect(str(tmp_db))
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    conn.close()
    assert ("transactions",) in tables


def test_insert_returns_row_id(tmp_db):
    row_id = insert_sample(tmp_db)
    assert isinstance(row_id, int)
    assert row_id >= 1


def test_insert_multiple_increments_id(tmp_db):
    id1 = insert_sample(tmp_db)
    id2 = insert_sample(tmp_db, prompt_hash="xyz99999")
    assert id2 > id1


def test_baseline_cost_is_computed(tmp_db):
    insert_sample(tmp_db, input_tokens=1000)
    rows = get_all_transactions(tmp_db)
    expected = (1000 / 1000) * BASELINE_MODEL_COST_PER_1K
    assert abs(rows[0]["baseline_cost"] - expected) < 1e-9


def test_get_all_transactions_returns_list(tmp_db):
    insert_sample(tmp_db)
    rows = get_all_transactions(tmp_db)
    assert isinstance(rows, list)
    assert len(rows) == 1


def test_get_all_returns_dict_rows(tmp_db):
    insert_sample(tmp_db)
    row = get_all_transactions(tmp_db)[0]
    assert "model_id" in row
    assert "cost_usd" in row
    assert "complexity_tier" in row


# ── Stats ─────────────────────────────────────────────────────────────────────

def test_stats_empty_db(tmp_db):
    s = get_stats(tmp_db)
    assert s["total_requests"] == 0
    assert s["savings_pct"] == 0.0


def test_stats_total_requests(tmp_db):
    insert_sample(tmp_db)
    insert_sample(tmp_db, prompt_hash="zzz")
    s = get_stats(tmp_db)
    assert s["total_requests"] == 2


def test_stats_savings_positive(tmp_db):
    # cheap model → baseline (gpt-4o) is much more expensive
    insert_sample(tmp_db, input_tokens=1000, cost_usd=0.000075)
    s = get_stats(tmp_db)
    assert s["total_savings"] > 0
    assert s["savings_pct"] > 0


def test_stats_escalation_count(tmp_db):
    insert_sample(tmp_db, escalated=True, escalated_model="gpt-4o")
    insert_sample(tmp_db, prompt_hash="yyy", escalated=False)
    s = get_stats(tmp_db)
    assert s["escalation_count"] == 1


def test_stats_avg_quality_score(tmp_db):
    insert_sample(tmp_db, quality_score=4)
    insert_sample(tmp_db, prompt_hash="yyy", quality_score=5)
    s = get_stats(tmp_db)
    assert abs(s["avg_quality_score"] - 4.5) < 0.01


# ── Distribution queries ──────────────────────────────────────────────────────

def test_model_distribution(tmp_db):
    insert_sample(tmp_db, model_id="gemini-flash")
    insert_sample(tmp_db, model_id="gemini-flash", prompt_hash="yyy")
    insert_sample(tmp_db, model_id="gpt-4o-mini",  prompt_hash="zzz")
    dist = get_model_distribution(tmp_db)
    models = {d["model_id"]: d["request_count"] for d in dist}
    assert models["gemini-flash"] == 2
    assert models["gpt-4o-mini"] == 1


def test_tier_distribution(tmp_db):
    insert_sample(tmp_db, complexity_tier=1, tier_name="Simple")
    insert_sample(tmp_db, complexity_tier=2, tier_name="Moderate", prompt_hash="yyy")
    dist = get_tier_distribution(tmp_db)
    tiers = {d["tier"]: d["request_count"] for d in dist}
    assert tiers[1] == 1
    assert tiers[2] == 1


def test_cost_over_time(tmp_db):
    insert_sample(tmp_db, timestamp="2026-07-01T10:00:00+00:00")
    insert_sample(tmp_db, timestamp="2026-07-01T12:00:00+00:00", prompt_hash="yyy")
    insert_sample(tmp_db, timestamp="2026-07-02T10:00:00+00:00", prompt_hash="zzz")
    cot = get_cost_over_time(tmp_db)
    assert len(cot) == 2   # two distinct days


def test_quality_distribution(tmp_db):
    insert_sample(tmp_db, quality_score=5)
    insert_sample(tmp_db, quality_score=5, prompt_hash="yyy")
    insert_sample(tmp_db, quality_score=3, prompt_hash="zzz")
    qdist = get_quality_distribution(tmp_db)
    by_score = {d["score"]: d["count"] for d in qdist}
    assert by_score[5] == 2
    assert by_score[3] == 1


def test_quality_distribution_excludes_null(tmp_db):
    insert_sample(tmp_db, quality_score=None, quality_passed=None)
    qdist = get_quality_distribution(tmp_db)
    assert qdist == []
