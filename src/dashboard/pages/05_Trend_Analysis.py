"""
pages/05_Trend_Analysis.py — Trend & Growth Analytics
"""
import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(ROOT / "data" / "nifty100.db"))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.dashboard.utils.db import load_companies, load_ratios, load_pl

st.set_page_config(page_title="Trend Analysis — Nifty 100", page_icon="📈", layout="wide")
st.title("📈 Trend & Growth Analytics")

companies = load_companies()
pl        = load_pl()
ratios    = load_ratios()

ticker_col = "id"
name_col   = "company_name" if "company_name" in companies.columns else "name"
options    = companies[ticker_col].dropna().sort_values().tolist()

col_l, col_r = st.columns([2, 1])
with col_l:
    selected = st.selectbox("Select Company", options)
with col_r:
    metric_choices = {
        "Sales (Revenue)":   "sales",
        "Net Profit":        "net_profit",
        "Operating Profit":  "operating_profit",
        "ROE %":             "return_on_equity_pct",
        "OPM %":             "operating_profit_margin_pct",
        "Net Margin %":      "net_profit_margin_pct",
        "D/E Ratio":         "debt_to_equity",
        "FCF (Cr)":          "free_cash_flow_cr",
        "EPS":               "earnings_per_share",
    }
    metric_label = st.selectbox("Metric", list(metric_choices.keys()))
    metric_col   = metric_choices[metric_label]

c_pl     = pl[pl["company_id"] == selected].sort_values("year")
c_ratios = ratios[ratios["company_id"] == selected].sort_values("year")

# Determine data source
if metric_col in c_pl.columns:
    plot_data = c_pl[["year", metric_col]].dropna()
elif metric_col in c_ratios.columns:
    plot_data = c_ratios[["year", metric_col]].dropna()
else:
    plot_data = pd.DataFrame()

st.markdown("---")

# ── 10-year Sparkline ──────────────────────────────────────────────────────
if not plot_data.empty:
    fig = go.Figure()
    values = plot_data[metric_col]
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in values]

    fig.add_trace(go.Bar(
        x=plot_data["year"], y=values,
        marker_color=colors,
        name=metric_label,
    ))
    fig.add_trace(go.Scatter(
        x=plot_data["year"], y=values,
        mode="lines+markers",
        line=dict(color="#0A2342", width=2),
        marker=dict(size=6),
        name="Trend",
    ))

    # YoY % change annotation
    pct_changes = values.pct_change() * 100
    for i, (year, pct) in enumerate(zip(plot_data["year"], pct_changes)):
        if i > 0 and not pd.isna(pct):
            arrow = "▲" if pct >= 0 else "▼"
            color = "green" if pct >= 0 else "red"

    fig.update_layout(
        title=f"{selected} — {metric_label} (10-Year Trend)",
        xaxis_title="Financial Year",
        yaxis_title=metric_label,
        height=420,
        hovermode="x unified",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#f8fafc",
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Growth summary
    if len(plot_data) >= 4:
        st.subheader("📊 CAGR Summary")
        c1, c2, c3 = st.columns(3)
        from src.analytics.cagr import _safe_cagr

        sorted_vals = plot_data.sort_values("year")
        latest_val = sorted_vals[metric_col].iloc[-1]

        for label, n in [("3-Year CAGR", 3), ("5-Year CAGR", 5), ("10-Year CAGR", 10)]:
            if len(sorted_vals) > n:
                base_val = sorted_vals[metric_col].iloc[-(n+1)]
                val, flag = _safe_cagr(base_val, latest_val, n)
                display = f"{val:.1f}%" if val is not None else flag
            else:
                display = "Insufficient data"
            if n == 3: c1.metric(label, display)
            elif n == 5: c2.metric(label, display)
            else: c3.metric(label, display)
else:
    st.info(f"No data for **{metric_label}** for {selected}.")

# ── Multi-metric overlay ──────────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 Multi-Metric Overlay")
overlay_metrics = [k for k, v in metric_choices.items()
                   if (v in c_pl.columns or v in c_ratios.columns)]
selected_overlays = st.multiselect("Add metrics to overlay", overlay_metrics,
                                   default=overlay_metrics[:3])

if selected_overlays:
    fig2 = go.Figure()
    for lbl in selected_overlays:
        col = metric_choices[lbl]
        if col in c_pl.columns:
            d = c_pl[["year", col]].dropna()
        elif col in c_ratios.columns:
            d = c_ratios[["year", col]].dropna()
        else:
            continue
        fig2.add_trace(go.Scatter(x=d["year"], y=d[col], name=lbl,
                                  mode="lines+markers"))
    fig2.update_layout(
        title=f"{selected} — Multi-Metric Trend",
        height=380,
        hovermode="x unified",
        plot_bgcolor="#f8fafc", paper_bgcolor="#f8fafc",
    )
    st.plotly_chart(fig2, use_container_width=True)
