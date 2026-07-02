"""
LLM Cost Autopilot — Cost Dashboard
Run: streamlit run dashboard/app.py
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from audit.db import (
    init_db, get_stats, get_all_transactions,
    get_model_distribution, get_tier_distribution,
    get_cost_over_time, get_quality_distribution,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LLM Cost Autopilot",
    page_icon="⚡",
    layout="wide",
)

init_db()

# ── Colours ───────────────────────────────────────────────────────────────────
TIER_COLORS  = {"Simple": "#22C55E", "Moderate": "#F59E0B", "Complex": "#EF4444"}
MODEL_PALETTE = px.colors.qualitative.Plotly

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_data():
    stats        = get_stats()
    transactions = get_all_transactions()
    model_dist   = get_model_distribution()
    tier_dist    = get_tier_distribution()
    cost_time    = get_cost_over_time()
    quality_dist = get_quality_distribution()
    return stats, transactions, model_dist, tier_dist, cost_time, quality_dist

stats, transactions, model_dist, tier_dist, cost_time, quality_dist = load_data()
df = pd.DataFrame(transactions)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
            padding:2rem 2.5rem;border-radius:12px;margin-bottom:1.5rem'>
  <h1 style='color:white;margin:0;font-size:2rem'>⚡ LLM Cost Autopilot</h1>
  <p style='color:#93C5FD;margin:0.4rem 0 0'>
      Intelligent routing · Real-time cost tracking · Quality verification
  </p>
</div>
""", unsafe_allow_html=True)

if not transactions:
    st.warning("No transactions yet. Run `python scripts/seed_demo_data.py` to populate demo data, "
               "or use `smart_request()` to generate real data.")
    st.stop()

# ── Headline metric ───────────────────────────────────────────────────────────
savings_pct = stats["savings_pct"]
color = "#22C55E" if savings_pct >= 50 else "#F59E0B"

st.markdown(f"""
<div style='background:linear-gradient(135deg,#052e16,#064e3b);
            border:2px solid #22C55E;border-radius:12px;
            padding:1.5rem 2rem;margin-bottom:1.5rem;text-align:center'>
  <p style='color:#86EFAC;font-size:1rem;margin:0'>💰 Cost Reduction vs GPT-4o Baseline</p>
  <h1 style='color:{color};font-size:4rem;margin:0.3rem 0;font-weight:900'>
      {savings_pct:.1f}% Saved
  </h1>
  <p style='color:#86EFAC;margin:0'>
      ${stats["total_savings"]:.4f} saved across {stats["total_requests"]:,} requests &nbsp;|&nbsp;
      Actual: ${stats["total_cost"]:.4f} &nbsp;vs&nbsp; Baseline: ${stats["total_baseline"]:.4f}
  </p>
</div>
""", unsafe_allow_html=True)

# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Requests",    f"{stats['total_requests']:,}")
k2.metric("Total Cost",        f"${stats['total_cost']:.4f}")
k3.metric("Avg Cost / Request",f"${stats['avg_cost']:.6f}")
k4.metric("Avg Latency",       f"{stats['avg_latency_ms']:.0f} ms")
k5.metric("Escalations",
          f"{stats['escalation_count']}",
          f"{stats['escalation_count']/max(stats['total_requests'],1)*100:.1f}%")

st.divider()

# ── Row 1: Routing distribution + Tier distribution ──────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Model Routing Distribution")
    if model_dist:
        mdf = pd.DataFrame(model_dist)
        fig = px.pie(
            mdf, values="request_count", names="model_id",
            color_discrete_sequence=MODEL_PALETTE,
            hole=0.45,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=10, b=10), showlegend=True,
                          legend=dict(orientation="v", x=1, y=0.5))
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Complexity Tier Distribution")
    if tier_dist:
        tdf = pd.DataFrame(tier_dist)
        fig = px.bar(
            tdf, x="tier_name", y="request_count",
            color="tier_name",
            color_discrete_map=TIER_COLORS,
            text="request_count",
            labels={"tier_name": "Tier", "request_count": "Requests"},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ── Row 2: Cost over time ─────────────────────────────────────────────────────
st.subheader("Actual Cost vs GPT-4o Baseline Over Time")
if cost_time:
    ctdf = pd.DataFrame(cost_time)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ctdf["day"], y=ctdf["baseline_cost"],
        name="GPT-4o Baseline", line=dict(color="#EF4444", width=2, dash="dash"),
        fill=None,
    ))
    fig.add_trace(go.Scatter(
        x=ctdf["day"], y=ctdf["actual_cost"],
        name="Autopilot Cost", line=dict(color="#22C55E", width=2),
        fill="tonexty", fillcolor="rgba(34,197,94,0.1)",
    ))
    fig.update_layout(
        xaxis_title="Date", yaxis_title="Cost (USD)",
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Row 3: Quality scores + Latency by model ─────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("Quality Score Distribution")
    if quality_dist:
        qdf = pd.DataFrame(quality_dist)
        score_labels = {1: "1 - Fail", 2: "2 - Poor", 3: "3 - OK",
                        4: "4 - Good", 5: "5 - Perfect"}
        score_colors = {1: "#EF4444", 2: "#F97316", 3: "#F59E0B",
                        4: "#84CC16", 5: "#22C55E"}
        qdf["label"] = qdf["score"].map(score_labels)
        qdf["color"] = qdf["score"].map(score_colors)
        fig = px.bar(
            qdf, x="label", y="count",
            color="label",
            color_discrete_map={v: score_colors[k] for k, v in score_labels.items()},
            text="count",
            labels={"label": "Score", "count": "Responses"},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No quality scores yet — run with verification enabled.")

with col4:
    st.subheader("Avg Latency by Model (ms)")
    if model_dist:
        mdf = pd.DataFrame(model_dist).sort_values("avg_latency")
        fig = px.bar(
            mdf, x="avg_latency", y="model_id",
            orientation="h",
            color="avg_latency",
            color_continuous_scale=["#22C55E", "#F59E0B", "#EF4444"],
            text=mdf["avg_latency"].apply(lambda x: f"{x:.0f}ms"),
            labels={"avg_latency": "Avg Latency (ms)", "model_id": "Model"},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(coloraxis_showscale=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ── Row 4: Cost per model ─────────────────────────────────────────────────────
st.subheader("Total Cost by Model")
if model_dist:
    mdf = pd.DataFrame(model_dist).sort_values("total_cost", ascending=False)
    fig = px.bar(
        mdf, x="model_id", y="total_cost",
        color="model_id", color_discrete_sequence=MODEL_PALETTE,
        text=mdf["total_cost"].apply(lambda x: f"${x:.5f}"),
        labels={"model_id": "Model", "total_cost": "Total Cost (USD)"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ── Row 5: Escalation analysis ────────────────────────────────────────────────
st.subheader("Escalation Analysis")
if not df.empty and "escalated" in df.columns:
    esc_df = df[df["escalated"] == 1]
    if not esc_df.empty:
        col5, col6 = st.columns(2)
        with col5:
            esc_by_model = esc_df.groupby("model_id").size().reset_index(name="escalations")
            fig = px.bar(esc_by_model, x="model_id", y="escalations",
                         title="Escalations by Original Model",
                         color_discrete_sequence=["#EF4444"])
            st.plotly_chart(fig, use_container_width=True)
        with col6:
            esc_by_tier = esc_df.groupby("tier_name").size().reset_index(name="escalations")
            fig = px.pie(esc_by_tier, values="escalations", names="tier_name",
                         title="Escalations by Tier",
                         color="tier_name", color_discrete_map=TIER_COLORS, hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("✅ No escalations — all routed responses met quality thresholds.")

# ── Raw audit log ─────────────────────────────────────────────────────────────
st.subheader("Audit Log")
if not df.empty:
    display_cols = ["timestamp", "model_id", "complexity_tier", "tier_name",
                    "task_type", "cost_usd", "baseline_cost", "latency_ms",
                    "quality_score", "escalated", "escalated_model"]
    display_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(
        df[display_cols].head(200),
        use_container_width=True,
        hide_index=True,
    )

st.caption("Auto-refreshes every 10 seconds · Data from data/transactions.db")
