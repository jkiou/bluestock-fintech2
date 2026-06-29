"""
src/dashboard/utils/db.py
Shared database utilities for the Streamlit dashboard.
All data loading functions are cached with @st.cache_data.
"""
import os
import sqlite3
import streamlit as st
import pandas as pd

DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")


@st.cache_data(ttl=300)
def load_companies() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        # Join companies with latest year of market_cap and sectors to get all required columns
        query = """
            SELECT 
                c.*, 
                c.company_name AS name,
                s.broad_sector AS sector, 
                s.sub_sector AS industry,
                mc.market_cap_crore AS market_cap_cr,
                mc.pe_ratio,
                mc.pb_ratio,
                mc.dividend_yield_pct
            FROM companies c
            LEFT JOIN sectors s ON c.id = s.company_id
            LEFT JOIN market_cap mc ON c.id = mc.company_id AND mc.year = (SELECT MAX(year) FROM market_cap)
            ORDER BY mc.market_cap_crore DESC NULLS LAST
        """
        return pd.read_sql(query, conn)


@st.cache_data(ttl=300)
def load_ratios() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM financial_ratios ORDER BY company_id, year", conn)
        if "id" in df.columns:
            df = df.drop(columns=["id"])
        return df


@st.cache_data(ttl=300)
def load_pl() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM profitandloss ORDER BY company_id, year", conn)
        if "id" in df.columns:
            df = df.drop(columns=["id"])
        return df


@st.cache_data(ttl=300)
def load_bs() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM balancesheet ORDER BY company_id, year", conn)
        if "id" in df.columns:
            df = df.drop(columns=["id"])
        return df


@st.cache_data(ttl=300)
def load_cf() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM cashflow ORDER BY company_id, year", conn)
        if "id" in df.columns:
            df = df.drop(columns=["id"])
        return df


@st.cache_data(ttl=300)
def load_sectors() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        try:
            return pd.read_sql("SELECT * FROM sectors", conn)
        except Exception:
            return pd.DataFrame()


@st.cache_data(ttl=300)
def load_market_cap() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        try:
            return pd.read_sql("SELECT * FROM market_cap ORDER BY company_id, year", conn)
        except Exception:
            return pd.DataFrame()


@st.cache_data(ttl=300)
def load_peer_groups() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        try:
            return pd.read_sql("SELECT * FROM peer_groups", conn)
        except Exception:
            return pd.DataFrame()


@st.cache_data(ttl=300)
def load_documents() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        try:
            return pd.read_sql("SELECT * FROM documents ORDER BY company_id, Year DESC", conn)
        except Exception:
            return pd.DataFrame()


def latest_ratios(ratios: pd.DataFrame) -> pd.DataFrame:
    """Return only the latest year row per company."""
    if ratios.empty:
        return ratios
    return ratios.loc[ratios.groupby("company_id")["year"].idxmax()].copy()


def get_company_ratios(ratios: pd.DataFrame, company_id: str) -> pd.DataFrame:
    return ratios[ratios["company_id"] == company_id].sort_values("year")


def get_company_pl(pl: pd.DataFrame, company_id: str) -> pd.DataFrame:
    return pl[pl["company_id"] == company_id].sort_values("year")
