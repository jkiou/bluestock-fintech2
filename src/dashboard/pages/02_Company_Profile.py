"""
pages/02_Company_Profile.py
Company Profile — detailed view for all Nifty 100 companies.
"""
import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(ROOT / "data" / "nifty100.db"))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from src.dashboard.utils.db import load_companies, load_ratios, load_pl, load_bs, load_cf

st.set_page_config(page_title="Company Profile — Nifty 100", page_icon="📋", layout="wide")
st.title("📋 Company Profile")

companies = load_companies()
ratios    = load_ratios()
pl        = load_pl()

ticker_col = "id"
name_col   = "company_name" if "company_name" in companies.columns else "name"

options = companies[ticker_col].dropna().sort_values().tolist()
selected = st.selectbox("🔎 Search Company (Ticker)", options)

comp = companies[companies[ticker_col] == selected]
if comp.empty:
    st.error("Company not found.")
    st.stop()
comp = comp.iloc[0]

# ── Company Card ─────────────────────────────────────────────────────────────
st.markdown(f"## {comp.get(name_col, selected)} `[{selected}]`")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Sector",    comp.get("sector", "—"))
col2.metric("Market Cap", f"₹{comp.get('market_cap_cr', 0):,.0f} Cr")
col3.metric("P/E Ratio",  f"{comp.get('pe_ratio', 0):.1f}×")
col4.metric("P/B Ratio",  f"{comp.get('pb_ratio', 0):.2f}×")

if comp.get("about_company"):
    with st.expander("About the Company"):
        st.write(comp["about_company"])

st.markdown("---")

# ── KPI Tiles ────────────────────────────────────────────────────────────────
c_ratios = ratios[ratios["company_id"] == selected].sort_values("year")
latest   = c_ratios.iloc[-1] if not c_ratios.empty else {}

st.subheader("📊 Latest KPI Snapshot")
k1, k2, k3, k4, k5, k6 = st.columns(6)
def fmt(v, pct=False, cr=False):
    if v is None or (hasattr(v, '__float__') and __import__('math').isnan(float(v) if v else float('nan'))):
        return "N/A"
    if pct: return f"{float(v):.1f}%"
    if cr: return f"₹{float(v):,.0f} Cr"
    return f"{float(v):.2f}"

if hasattr(latest, 'get'):
    k1.metric("ROE",         fmt(latest.get("return_on_equity_pct"), pct=True))
    k2.metric("OPM",         fmt(latest.get("operating_profit_margin_pct"), pct=True))
    k3.metric("Net Margin",  fmt(latest.get("net_profit_margin_pct"), pct=True))
    k4.metric("Debt/Equity", fmt(latest.get("debt_to_equity")))
    k5.metric("FCF",         fmt(latest.get("free_cash_flow_cr"), cr=True))
    k6.metric("EPS",         f"₹{latest.get('earnings_per_share', 0) or 0:.2f}")

st.markdown("---")

# ── Charts ───────────────────────────────────────────────────────────────────
c_pl = pl[pl["company_id"] == selected].sort_values("year")

tab1, tab2, tab3 = st.tabs(["📈 Revenue & Profit", "📊 Margins (10yr)", "🏦 Balance Sheet Trend"])

with tab1:
    if not c_pl.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Sales (Cr)", x=c_pl["year"], y=c_pl["sales"],
                             marker_color="#0A2342", yaxis="y"))
        fig.add_trace(go.Bar(name="Net Profit (Cr)", x=c_pl["year"], y=c_pl["net_profit"],
                             marker_color="#00C9A7", yaxis="y"))
        fig.update_layout(barmode="group", height=380,
                          title=f"{selected} — Revenue vs Net Profit (₹ Crore)",
                          xaxis_title="Financial Year", yaxis_title="₹ Crore",
                          hovermode="x unified",
                          plot_bgcolor="#f8fafc", paper_bgcolor="#f8fafc")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No P&L data.")

with tab2:
    if not c_ratios.empty:
        fig2 = go.Figure()
        for col, name, color in [
            ("return_on_equity_pct", "ROE %", "#0A2342"),
            ("net_profit_margin_pct", "Net Margin %", "#00C9A7"),
            ("operating_profit_margin_pct", "OPM %", "#F4A261"),
        ]:
            if col in c_ratios.columns:
                fig2.add_trace(go.Scatter(
                    x=c_ratios["year"], y=c_ratios[col],
                    name=name, line=dict(color=color, width=2.5),
                    mode="lines+markers"
                ))
        fig2.update_layout(title="Profitability Metrics Over Time",
                           xaxis_title="Year", yaxis_title="%",
                           hovermode="x unified", height=380,
                           plot_bgcolor="#f8fafc", paper_bgcolor="#f8fafc")
        st.plotly_chart(fig2, use_container_width=True)

with tab3:
    bs = load_bs()
    c_bs = bs[bs["company_id"] == selected].sort_values("year")
    if not c_bs.empty:
        fig3 = go.Figure()
        if "total_assets" in c_bs.columns:
            fig3.add_trace(go.Scatter(x=c_bs["year"], y=c_bs["total_assets"],
                                      name="Total Assets", fill="tozeroy",
                                      line=dict(color="#0A2342")))
        if "borrowings" in c_bs.columns:
            fig3.add_trace(go.Scatter(x=c_bs["year"], y=c_bs["borrowings"],
                                      name="Borrowings", line=dict(color="#e74c3c")))
        fig3.update_layout(title="Balance Sheet Trend", height=380,
                           xaxis_title="Year", yaxis_title="₹ Crore",
                           plot_bgcolor="#f8fafc", paper_bgcolor="#f8fafc")
        st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")
st.subheader("📑 Full KPI History")
if not c_ratios.empty:
    st.dataframe(c_ratios.set_index("year").round(2), use_container_width=True)
