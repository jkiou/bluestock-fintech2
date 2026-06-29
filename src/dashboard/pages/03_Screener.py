"""
pages/03_Screener.py — Investment Screener
"""
import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(ROOT / "data" / "nifty100.db"))

import streamlit as st
import pandas as pd
from src.dashboard.utils.db import load_companies, load_ratios, latest_ratios

st.set_page_config(page_title="Screener — Nifty 100", page_icon="🔍", layout="wide")
st.title("🔍 Investment Screener")
st.markdown("Filter 92 Nifty 100 companies using institutional-grade metrics.")

companies = load_companies()
ratios    = load_ratios()
lr        = latest_ratios(ratios)
merged    = companies.merge(lr, left_on="id", right_on="company_id", how="left")

# ── Preset or Custom ─────────────────────────────────────────────────────────
mode = st.radio("Mode", ["📋 Use Preset", "⚙️ Custom Filters"], horizontal=True)

if mode == "📋 Use Preset":
    PRESETS = {
        "Quality Compounder": {"return_on_equity_pct": (15, 9999), "debt_to_equity": (0, 1.0), "free_cash_flow_cr": (0, 9e9)},
        "Value Pick":         {"pe_ratio": (0, 20), "pb_ratio": (0, 3), "dividend_yield_pct": (1, 9999)},
        "Growth Accelerator": {"net_profit_margin_pct": (10, 9999), "return_on_equity_pct": (15, 9999)},
        "Dividend Champion":  {"dividend_yield_pct": (2, 9999), "free_cash_flow_cr": (0, 9e9)},
        "Debt-Free Blue Chip":{"debt_to_equity": (0, 0.01), "return_on_equity_pct": (12, 9999)},
        "Turnaround Watch":   {"net_profit_margin_pct": (0, 9999), "return_on_equity_pct": (0, 9999)},
    }
    preset = st.selectbox("Select Preset", list(PRESETS.keys()))
    filters = PRESETS[preset]
    df_filtered = merged.copy()
    for col, (lo, hi) in filters.items():
        if col in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered[col].between(lo, hi, inclusive="both") |
                df_filtered[col].isna().eq(False)
            ]
            df_filtered = df_filtered[df_filtered[col].fillna(-9e9).between(lo, hi)]
else:
    st.sidebar.header("Custom Filters")
    min_roe   = st.sidebar.slider("Min ROE (%)",          -50.0, 100.0, 0.0,  1.0)
    max_de    = st.sidebar.slider("Max D/E",                0.0,  10.0, 10.0, 0.1)
    min_npm   = st.sidebar.slider("Min Net Margin (%)",   -50.0, 100.0, 0.0,  1.0)
    min_fcf   = st.sidebar.slider("Min FCF (Cr)",       -5000.0, 5000.0, 0.0, 100.0)
    sector_f  = st.sidebar.multiselect("Sector", sorted(merged["sector"].dropna().unique().tolist()))

    df_filtered = merged.copy()
    df_filtered = df_filtered[df_filtered["return_on_equity_pct"].fillna(-9e9) >= min_roe]
    df_filtered = df_filtered[df_filtered["debt_to_equity"].fillna(9e9)       <= max_de]
    df_filtered = df_filtered[df_filtered["net_profit_margin_pct"].fillna(-9e9) >= min_npm]
    df_filtered = df_filtered[df_filtered["free_cash_flow_cr"].fillna(-9e9) >= min_fcf]
    if sector_f:
        df_filtered = df_filtered[df_filtered["sector"].isin(sector_f)]

st.success(f"✅ **{len(df_filtered)} companies** matched your criteria")

display_cols = [c for c in [
    "id", "company_name", "sector", "market_cap_cr",
    "return_on_equity_pct", "operating_profit_margin_pct",
    "net_profit_margin_pct", "debt_to_equity", "free_cash_flow_cr",
    "pe_ratio", "dividend_yield_pct",
] if c in df_filtered.columns]

show = df_filtered[display_cols].rename(columns={
    "id": "Ticker", "company_name": "Company", "sector": "Sector",
    "market_cap_cr": "MCap (Cr)", "return_on_equity_pct": "ROE%",
    "operating_profit_margin_pct": "OPM%", "net_profit_margin_pct": "NPM%",
    "debt_to_equity": "D/E", "free_cash_flow_cr": "FCF (Cr)",
    "pe_ratio": "P/E", "dividend_yield_pct": "Div Yield%",
}).sort_values("MCap (Cr)", ascending=False)

st.dataframe(show.style.format({
    "MCap (Cr)": "₹{:,.0f}", "ROE%": "{:.1f}%", "OPM%": "{:.1f}%",
    "NPM%": "{:.1f}%", "D/E": "{:.2f}", "FCF (Cr)": "₹{:,.0f}",
    "P/E": "{:.1f}", "Div Yield%": "{:.2f}%",
}, na_rep="N/A"), use_container_width=True, hide_index=True)

csv = show.to_csv(index=False)
st.download_button("⬇️ Download Screener Results (CSV)", csv, "screener_output.csv", "text/csv")
