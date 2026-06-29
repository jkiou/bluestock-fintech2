"""
pages/04_Peer_Comparison.py — Peer Comparison
"""
import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(ROOT / "data" / "nifty100.db"))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.dashboard.utils.db import load_companies, load_ratios, load_peer_groups, latest_ratios

st.set_page_config(page_title="Peer Comparison — Nifty 100", page_icon="👥", layout="wide")
st.title("👥 Peer Comparison Engine")

companies   = load_companies()
ratios      = load_ratios()
peer_groups = load_peer_groups()
lr          = latest_ratios(ratios)
merged      = companies.merge(lr, left_on="id", right_on="company_id", how="left")

METRICS = [
    ("return_on_equity_pct",           "ROE %"),
    ("operating_profit_margin_pct",    "OPM %"),
    ("net_profit_margin_pct",          "NPM %"),
    ("debt_to_equity",                 "D/E"),
    ("interest_coverage",              "ICR"),
    ("asset_turnover",                 "Asset TO"),
    ("free_cash_flow_cr",              "FCF (Cr)"),
    ("earnings_per_share",             "EPS"),
]

if not peer_groups.empty and "peer_group_name" in peer_groups.columns:
    groups = sorted(peer_groups["peer_group_name"].dropna().unique())
    selected_group = st.selectbox("Select Peer Group", groups)
    members = peer_groups[peer_groups["peer_group_name"] == selected_group]["company_id"].tolist()
    group_data = merged[merged["id"].isin(members)]
else:
    # Fallback: use sector
    st.info("No peer_groups table found — grouping by Sector instead.")
    sector = st.selectbox("Select Sector", sorted(merged["sector"].dropna().unique()))
    group_data = merged[merged["sector"] == sector]
    selected_group = sector

st.markdown(f"**{selected_group}** — {len(group_data)} companies")

# ── Radar Chart ────────────────────────────────────────────────────────────
st.subheader("📡 Radar Chart — Normalised KPI Comparison")

radar_cols = [c for c, _ in METRICS if c in group_data.columns]
radar_labels = [n for c, n in METRICS if c in group_data.columns]

if len(group_data) >= 2 and radar_cols:
    fig = go.Figure()
    colors = ["#0A2342", "#00C9A7", "#F4A261", "#e74c3c", "#9b59b6",
              "#2ecc71", "#3498db", "#e67e22"]

    for i, (_, row) in enumerate(group_data.iterrows()):
        vals = []
        for col in radar_cols:
            col_data = group_data[col].dropna()
            v = row.get(col)
            if v is None or (hasattr(v, '__float__') and __import__('math').isnan(float(v))):
                vals.append(0)
            elif col_data.max() == col_data.min():
                vals.append(50)
            else:
                normed = (float(v) - col_data.min()) / (col_data.max() - col_data.min()) * 100
                vals.append(round(max(0, min(100, normed)), 1))
        vals_closed = vals + [vals[0]]
        labels_closed = radar_labels + [radar_labels[0]]
        fig.add_trace(go.Scatterpolar(
            r=vals_closed, theta=labels_closed,
            fill="toself", name=str(row.get("id", i)),
            line_color=colors[i % len(colors)],
            opacity=0.65,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=500, showlegend=True,
        title=f"Peer Radar — {selected_group}"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Not enough companies in this group for radar chart.")

# ── Side-by-side Table ─────────────────────────────────────────────────────
st.subheader("📊 Side-by-Side KPI Comparison")
display_metrics = ["id", "company_name"] + [c for c, _ in METRICS if c in group_data.columns]
avail = [c for c in display_metrics if c in group_data.columns]

# Sort before slicing with [avail] to prevent KeyError on missing columns in the slice
show = group_data.sort_values("market_cap_cr" if "market_cap_cr" in group_data.columns else "id", ascending=False)[avail]
show = show.rename(columns={
    "id": "Ticker", "company_name": "Company",
    **{c: n for c, n in METRICS}
})

st.dataframe(show.style.format(na_rep="N/A"), use_container_width=True, hide_index=True)
