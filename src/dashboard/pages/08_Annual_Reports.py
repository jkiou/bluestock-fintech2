"""
pages/08_Annual_Reports.py — Annual Report Repository
"""
import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(ROOT / "data" / "nifty100.db"))

import streamlit as st
import pandas as pd
from src.dashboard.utils.db import load_companies, load_documents

st.set_page_config(page_title="Annual Reports — Nifty 100", page_icon="📄", layout="wide")
st.title("📄 Annual Report Repository")
st.markdown("Access corporate annual filings and reports directly.")

companies = load_companies()
documents = load_documents()

if documents.empty:
    st.warning("No documents table found in the database. Please run the ETL load first.")
    st.stop()

# Company selection
ticker_col = "id"
name_col   = "company_name" if "company_name" in companies.columns else "name"
options = companies[ticker_col].dropna().sort_values().tolist()
selected_ticker = st.selectbox("Select Ticker to View Annual Reports", options)

comp_name = companies[companies[ticker_col] == selected_ticker][name_col].iloc[0]
comp_docs = documents[documents["company_id"] == selected_ticker].sort_values("Year", ascending=False)

st.subheader(f"Filings for {comp_name} ({selected_ticker})")

if comp_docs.empty:
    st.info("No annual report links found for this company.")
else:
    # Build list of links
    for _, row in comp_docs.iterrows():
        year = row["Year"]
        url = row["Annual_Report"]
        if url:
            st.markdown(f"- **FY {year} Annual Report:** [Download / View PDF File]({url})")
        else:
            st.markdown(f"- **FY {year} Annual Report:** Link unavailable")

st.markdown("---")
st.subheader("📑 Global Document Coverage Summary")

doc_counts = documents.groupby("company_id")["Year"].count().reset_index().rename(columns={"Year": "Report Count"})
doc_summary = companies.merge(doc_counts, left_on=ticker_col, right_on="company_id", how="left").fillna(0)
doc_summary["Report Count"] = doc_summary["Report Count"].astype(int)

st.dataframe(
    doc_summary[[ticker_col, name_col, "sector", "Report Count"]].rename(columns={
        ticker_col: "Ticker",
        name_col: "Company Name",
        "sector": "Sector",
        "Report Count": "Available Reports"
    }).sort_values("Available Reports", ascending=False),
    use_container_width=True,
    hide_index=True
)
