"""
pages/06_Sector_Analysis.py — Sector Analytics
"""
import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(ROOT / "data" / "nifty100.db"))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.dashboard.utils.db import load_companies, load_ratios, latest_ratios

st.set_page_config(page_title="Sector Analysis — Nifty 100", page_icon="🏭", layout="wide")
st.title("🏭 Sector Analytics")

companies = load_companies()
ratios    = load_ratios()
lr        = latest_ratios(ratios)
merged    = companies.merge(lr, left_on="id", right_on="company_id", how="left")

sector_col = "sector"
all_sectors = sorted(merged[sector_col].dropna().unique())

# ── Sector KPI Bar Chart ───────────────────────────────────────────────────
st.subheader("📊 Sector Median KPI Comparison")
kpi_choice = st.selectbox("Select KPI", [
    "return_on_equity_pct", "net_profit_margin_pct",
    "operating_profit_margin_pct", "debt_to_equity", "asset_turnover"
], format_func=lambda x: {
    "return_on_equity_pct":         "Return on Equity %",
    "net_profit_margin_pct":        "Net Profit Margin %",
    "operating_profit_margin_pct":  "Operating Profit Margin %",
    "debt_to_equity":               "Debt-to-Equity",
    "asset_turnover":               "Asset Turnover",
}.get(x, x))

if kpi_choice in merged.columns:
    sec_kpi = merged.groupby(sector_col)[kpi_choice].median().reset_index()
    sec_kpi.columns = ["Sector", "Value"]
    sec_kpi = sec_kpi.sort_values("Value", ascending=False)
    fig = px.bar(sec_kpi, x="Sector", y="Value",
                 color="Value", color_continuous_scale=["#1a5276", "#00C9A7"],
                 title=f"Sector Median — {kpi_choice}")
    fig.update_layout(height=380, plot_bgcolor="#f8fafc", paper_bgcolor="#f8fafc")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Bubble Chart: Revenue vs ROE, size = Market Cap ───────────────────────
st.subheader("🔵 Bubble Chart — Revenue vs ROE (Size = Market Cap)")
bdf = merged.dropna(subset=["market_cap_cr", "return_on_equity_pct"])
if "sales" in merged.columns:
    bdf2 = merged.dropna(subset=["sales", "return_on_equity_pct", "market_cap_cr"])
    fig2 = px.scatter(
        bdf2, x="sales", y="return_on_equity_pct",
        size="market_cap_cr", color=sector_col,
        hover_name="id" if "id" in bdf2.columns else sector_col,
        hover_data=["company_name"] if "company_name" in bdf2.columns else [],
        labels={"sales": "Latest Revenue (₹ Cr)", "return_on_equity_pct": "ROE %",
                "market_cap_cr": "Market Cap (Cr)"},
        title="Revenue vs ROE — Bubble Size = Market Cap",
        height=500,
    )
    fig2.update_layout(plot_bgcolor="#f8fafc", paper_bgcolor="#f8fafc")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── Drill-down per sector ──────────────────────────────────────────────────
st.subheader("🔍 Sector Deep Dive")
selected_sector = st.selectbox("Select Sector", all_sectors)
sec_data = merged[merged[sector_col] == selected_sector].sort_values(
    "market_cap_cr", ascending=False
)

display_cols = [c for c in [
    "id", "company_name", "market_cap_cr",
    "return_on_equity_pct", "net_profit_margin_pct",
    "operating_profit_margin_pct", "debt_to_equity", "free_cash_flow_cr",
    "pe_ratio",
] if c in sec_data.columns]

st.markdown(f"**{selected_sector}** — {len(sec_data)} companies")
st.dataframe(
    sec_data[display_cols].rename(columns={
        "id": "Ticker", "company_name": "Company",
        "market_cap_cr": "MCap (Cr)", "return_on_equity_pct": "ROE%",
        "net_profit_margin_pct": "NPM%", "operating_profit_margin_pct": "OPM%",
        "debt_to_equity": "D/E", "free_cash_flow_cr": "FCF (Cr)", "pe_ratio": "P/E"
    }).style.format({
        "MCap (Cr)": "₹{:,.0f}", "ROE%": "{:.1f}%", "NPM%": "{:.1f}%",
        "OPM%": "{:.1f}%", "D/E": "{:.2f}", "FCF (Cr)": "₹{:,.0f}", "P/E": "{:.1f}",
    }, na_rep="N/A"),
    use_container_width=True, hide_index=True
)
