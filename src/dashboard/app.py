"""
src/dashboard/app.py
Nifty 100 Financial Intelligence Platform — Streamlit Home Screen
Multi-page application with 8 screens covering the full analytical workflow.

Screens:
  app.py                        — 🏠 Home / Overview
  pages/02_Company_Profile.py   — 📋 Company Profile
  pages/03_Screener.py          — 🔍 Investment Screener
  pages/04_Peer_Comparison.py   — 👥 Peer Comparison
  pages/05_Trend_Analysis.py    — 📈 Trend Analysis
  pages/06_Sector_Analysis.py   — 🏭 Sector Analysis
  pages/07_Capital_Allocation.py — 💰 Capital Allocation Map
  pages/08_Annual_Reports.py    — 📄 Annual Reports
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(ROOT / "data" / "nifty100.db"))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from src.dashboard.utils.db import (
    load_companies, load_ratios, load_sectors, latest_ratios
)

st.set_page_config(
    page_title="Nifty 100 Intelligence Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A2342 0%, #0d2d55 100%);
}
[data-testid="stSidebar"] * { color: #e8edf5 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label { color: #a0b4cc !important; }
.kpi-card {
    background: linear-gradient(135deg, #0A2342 0%, #16335a 100%);
    border: 1px solid #1e4a7a;
    border-radius: 14px;
    padding: 20px 24px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
}
.kpi-card .label { font-size: 11px; color: #7a98b8; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }
.kpi-card .value { font-size: 28px; font-weight: 700; color: #00C9A7; margin-bottom: 2px; }
.kpi-card .sub   { font-size: 11px; color: #5a7a9a; }
.section-header { color: #0A2342; font-weight: 700; margin-top: 24px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Nifty 100")
    st.markdown("**Financial Intelligence Platform**")
    st.markdown("---")
    st.caption("Navigate using the pages above ↑")
    st.markdown("---")
    st.caption("🗄️ Data: NSE Nifty 100 | FY2010–2024")
    st.caption("📊 92 Companies | 50+ KPIs | 12 Modules")

# ── Main Content ─────────────────────────────────────────────────────────────
st.title("📈 Nifty 100 Financial Intelligence Platform")
st.markdown("*Transform raw financial statement data into structured analytics intelligence*")
st.markdown("---")

companies = load_companies()
ratios    = load_ratios()
sectors   = load_sectors()
lr        = latest_ratios(ratios)
merged    = companies.merge(lr, left_on="id", right_on="company_id", how="left")

# ── KPI Banner ───────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
kpi_data = [
    ("Total Companies",   f"{len(companies):,}",                         "in Nifty 100 universe"),
    ("Total Market Cap",  f"₹{companies['market_cap_cr'].sum()/1e5:.2f}L Cr", "combined"),
    ("Sectors Covered",   str(merged.get("sector", companies["sector"]).dropna().nunique()), "distinct sectors"),
    ("Avg ROE",           f"{lr['return_on_equity_pct'].mean():.1f}%",   "universe median"),
    ("Avg Net Margin",    f"{lr['net_profit_margin_pct'].mean():.1f}%",  "universe median"),
]
for col, (label, val, sub) in zip([col1, col2, col3, col4, col5], kpi_data):
    col.markdown(
        f'<div class="kpi-card"><div class="label">{label}</div>'
        f'<div class="value">{val}</div><div class="sub">{sub}</div></div>',
        unsafe_allow_html=True
    )

st.markdown("---")

# ── Charts Row ───────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("#### 🗺️ Market Cap by Sector")
    sector_col = "broad_sector" if "broad_sector" in merged.columns else "sector"
    if sector_col in merged.columns:
        sec = merged.groupby(sector_col)["market_cap_cr"].sum().reset_index()
        sec.columns = ["Sector", "Market Cap (Cr)"]
        fig = px.treemap(
            sec, path=["Sector"], values="Market Cap (Cr)",
            color="Market Cap (Cr)",
            color_continuous_scale=["#0A2342", "#1a5276", "#00A896", "#00C9A7"],
        )
        fig.update_traces(textinfo="label+percent root")
        fig.update_layout(margin=dict(t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sector data not available — run ETL to load sectors table.")

with col_b:
    st.markdown("#### 📊 ROE Distribution Across Nifty 100")
    roe_data = lr["return_on_equity_pct"].dropna()
    fig2 = go.Figure()
    fig2.add_trace(go.Histogram(
        x=roe_data, nbinsx=30,
        marker_color="#00A896",
        marker_line_color="#0A2342", marker_line_width=0.5,
        name="ROE %"
    ))
    fig2.add_vline(x=roe_data.mean(), line_dash="dash", line_color="#F4A261",
                   annotation_text=f"Mean: {roe_data.mean():.1f}%")
    fig2.update_layout(
        xaxis_title="Return on Equity (%)",
        yaxis_title="Number of Companies",
        showlegend=False, height=350,
        plot_bgcolor="#f8fafc", paper_bgcolor="#f8fafc",
        margin=dict(t=10)
    )
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── Top 10 Companies ────────────────────────────────────────────────────────
st.markdown("#### 🏆 Top 15 Companies by Market Cap")
top15_cols = ["id", "company_name", "sector", "market_cap_cr",
              "return_on_equity_pct", "net_profit_margin_pct",
              "debt_to_equity", "free_cash_flow_cr"]
avail = [c for c in top15_cols if c in merged.columns]
top15 = merged.nlargest(15, "market_cap_cr")[avail].rename(columns={
    "id": "Ticker", "company_name": "Company", "sector": "Sector",
    "market_cap_cr": "MCap (Cr)", "return_on_equity_pct": "ROE %",
    "net_profit_margin_pct": "NPM %", "debt_to_equity": "D/E",
    "free_cash_flow_cr": "FCF (Cr)",
})
fmt = {}
if "MCap (Cr)" in top15.columns: fmt["MCap (Cr)"] = "₹{:,.0f}"
if "ROE %" in top15.columns:     fmt["ROE %"]     = "{:.1f}%"
if "NPM %" in top15.columns:     fmt["NPM %"]     = "{:.1f}%"
if "D/E" in top15.columns:       fmt["D/E"]       = "{:.2f}"
if "FCF (Cr)" in top15.columns:  fmt["FCF (Cr)"]  = "₹{:,.0f}"
st.dataframe(
    top15.style.format(fmt, na_rep="N/A"),
    use_container_width=True, hide_index=True
)

st.markdown("---")
st.markdown(
    "**Navigate** the platform using the sidebar pages above. "
    "Start with 📋 **Company Profile** to explore any of the 92 companies."
)
