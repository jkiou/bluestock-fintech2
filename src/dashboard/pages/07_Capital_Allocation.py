"""
pages/07_Capital_Allocation.py — Capital Allocation Map
Visually stunning & premium design with curated palettes, HSL mapping, cards, and interactive charts.
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
from src.dashboard.utils.db import load_companies, load_cf

st.set_page_config(page_title="Capital Allocation — Nifty 100", page_icon="💰", layout="wide")

# ── Custom CSS for Premium Look ────────────────────────────────────────────────
st.markdown("""
<style>
.pattern-badge {
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    display: inline-block;
}
.badge-reinvestor { background-color: rgba(0, 201, 167, 0.15); color: #00C9A7; border: 1px solid #00C9A7; }
.badge-fundraiser { background-color: rgba(52, 152, 219, 0.15); color: #3498db; border: 1px solid #3498db; }
.badge-distress { background-color: rgba(231, 76, 60, 0.15); color: #e74c3c; border: 1px solid #e74c3c; }
.badge-neutral { background-color: rgba(127, 140, 141, 0.15); color: #7f8c8d; border: 1px solid #7f8c8d; }

.allocation-card {
    background: linear-gradient(135deg, #112233 0%, #0c1a26 100%);
    border: 1px solid #1a3044;
    border-radius: 12px;
    padding: 16px 20px;
    color: white;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}
.allocation-card .title { font-size: 12px; color: #a0b4cc; text-transform: uppercase; letter-spacing: 0.5px; }
.allocation-card .count { font-size: 32px; font-weight: 700; color: #00C9A7; margin-top: 4px; }
.allocation-card .desc { font-size: 11px; color: #7a98b8; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

st.title("💰 Capital Allocation Map")
st.markdown("*Analysis of operating (CFO), investing (CFI), and financing (CFF) cash flows to classify company capital strategies.*")
st.markdown("---")

companies = load_companies()
cf        = load_cf()

if cf.empty:
    st.warning("⚠️ No Cash Flow data found. Please run the ETL pipeline first.")
    st.stop()

latest_year = cf["year"].max()
cf_latest = cf[cf["year"] == latest_year].copy()

# Compute patterns using the logic from analytics
from src.analytics.cashflow_kpis import compute_capital_allocation
allocation_data = compute_capital_allocation(cf_latest)
allocation_merged = allocation_data.merge(companies, left_on="company_id", right_on="id", how="inner")

# ── Summary metrics row ───────────────────────────────────────────────────────
st.subheader("📊 Capital Strategy Distribution")
c1, c2, c3, c4 = st.columns(4)

counts = allocation_merged["pattern_label"].value_counts().to_dict()

c1.markdown(
    f'<div class="allocation-card"><div class="title">🔄 Reinvestors</div>'
    f'<div class="count">{counts.get("Reinvestor", 0)}</div>'
    f'<div class="desc">CFO > 0, CFI < 0, CFF < 0 (Investing in growth + paying dividends)</div></div>',
    unsafe_allow_html=True
)

c2.markdown(
    f'<div class="allocation-card"><div class="title">🚀 Growth Fundraisers</div>'
    f'<div class="count" style="color: #3498db;">{counts.get("Growth Fundraiser", 0)}</div>'
    f'<div class="desc">CFO > 0, CFI < 0, CFF > 0 (Expanding fast via fresh capital)</div></div>',
    unsafe_allow_html=True
)

c3.markdown(
    f'<div class="allocation-card"><div class="title">⚠️ Distress Signals</div>'
    f'<div class="count" style="color: #e74c3c;">{counts.get("Distress Signal", 0)}</div>'
    f'<div class="desc">CFO < 0, CFI < 0, CFF > 0 (Borrowing/diluting to cover operating losses)</div></div>',
    unsafe_allow_html=True
)

c4.markdown(
    f'<div class="allocation-card"><div class="title">🛠️ Restructuring / Others</div>'
    f'<div class="count" style="color: #e67e22;">{counts.get("Asset Seller / Returns", 0) + counts.get("Restructuring", 0)}</div>'
    f'<div class="desc">CFO > 0, CFI > 0, CFF < 0 (Divesting assets, paying back debt/equity)</div></div>',
    unsafe_allow_html=True
)

st.markdown("---")

# ── Interactive Charts Row ───────────────────────────────────────────────────
col_a, col_b = st.columns([3, 2])

with col_a:
    st.subheader("🗺️ Capital Allocation Treemap")
    
    # Custom color map matching the visual styles
    color_map = {
        "Reinvestor": "#00A896",
        "Growth Fundraiser": "#3498db",
        "Distress Signal": "#e74c3c",
        "Asset Seller / Returns": "#F4A261",
        "Restructuring": "#e67e22",
        "Cash Accumulator": "#2ecc71",
        "Liquidator": "#c0392b",
        "Cash Burner": "#962d22",
    }
    
    fig = px.treemap(
        allocation_merged,
        path=["pattern_label", "sector", "company_id"],
        values="market_cap_cr",
        color="pattern_label",
        color_discrete_map=color_map,
    )
    fig.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=480)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("📈 CFO vs CFI vs CFF Core Allocations")
    
    # Scatter plot of CFO vs CFI (colour coded by pattern)
    fig_scatter = px.scatter(
        allocation_merged,
        x="operating_activity",
        y="investing_activity",
        size="market_cap_cr",
        color="pattern_label",
        color_discrete_map=color_map,
        hover_name="company_id",
        hover_data=["company_name"],
        labels={"operating_activity": "CFO (₹ Crore)", "investing_activity": "CFI (₹ Crore)"},
    )
    fig_scatter.update_layout(
        plot_bgcolor="#f8fafc", paper_bgcolor="#f8fafc",
        height=450, margin=dict(t=10)
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("---")

# ── Detailed breakdown by Strategy ───────────────────────────────────────────
st.subheader("📋 Strategy Categorisation Drill-Down")

selected_pattern = st.selectbox("Select Capital Allocation Strategy", sorted(list(counts.keys())))

pattern_cos = allocation_merged[allocation_merged["pattern_label"] == selected_pattern].sort_values("market_cap_cr", ascending=False)

st.markdown(f"Showing **{len(pattern_cos)} companies** matching **{selected_pattern}** strategy:")

show_cols = ["id", "company_name", "sector", "market_cap_cr", "operating_activity", "investing_activity", "financing_activity"]
show_df = pattern_cos[show_cols].rename(columns={
    "id": "Ticker",
    "company_name": "Company Name",
    "sector": "Sector",
    "market_cap_cr": "Market Cap (Cr)",
    "operating_activity": "CFO (Cr)",
    "investing_activity": "CFI (Cr)",
    "financing_activity": "CFF (Cr)"
})

st.dataframe(
    show_df.style.format({
        "Market Cap (Cr)": "₹{:,.0f}",
        "CFO (Cr)": "₹{:,.0f}",
        "CFI (Cr)": "₹{:,.0f}",
        "CFF (Cr)": "₹{:,.0f}"
    }, na_rep="N/A"),
    use_container_width=True,
    hide_index=True
)
