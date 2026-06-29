"""
src/api/main.py
FastAPI REST API for the Nifty 100 Financial Intelligence Platform.

Routes
------
GET  /                          Health check
GET  /companies                 List all companies (with optional sector filter)
GET  /companies/{ticker}        Full company profile + latest KPIs
GET  /kpi/{ticker}              Historical KPI time-series for a company
GET  /screen/{preset}           Run a named screener preset
GET  /sectors                   Summary stats per sector
GET  /search?q=                 Fuzzy name / ticker search
"""
import os
import logging
import sqlite3
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api.main")

app = FastAPI(
    title="Nifty 100 Financial Intelligence API",
    description="REST API serving KPIs, screener, and company profiles for Nifty 100 stocks.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------
def get_conn():
    """Return a read-only SQLite connection."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def df_from_query(sql: str, params=()) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params=params)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "Nifty100 API", "version": "1.0.0"}


@app.get("/companies", tags=["Companies"])
def list_companies(sector: Optional[str] = Query(None, description="Filter by sector")):
    """Return all companies, optionally filtered by sector."""
    sql = """
        SELECT 
            c.id, 
            c.company_name AS name, 
            c.id AS ticker, 
            s.broad_sector AS sector, 
            s.sub_sector AS industry, 
            mc.market_cap_crore AS market_cap_cr, 
            mc.pe_ratio, 
            mc.pb_ratio 
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN market_cap mc ON c.id = mc.company_id AND mc.year = (SELECT MAX(year) FROM market_cap)
    """
    params = []
    if sector:
        sql += " WHERE s.broad_sector = ?"
        params.append(sector)
    sql += " ORDER BY mc.market_cap_crore DESC NULLS LAST"
    df = df_from_query(sql, params)
    return JSONResponse(content=df.to_dict(orient="records"))


@app.get("/companies/{ticker}", tags=["Companies"])
def get_company(ticker: str):
    """Full company profile + latest KPIs."""
    ticker = ticker.upper()
    company_sql = """
        SELECT 
            c.*, 
            c.company_name AS name,
            c.id AS ticker,
            s.broad_sector AS sector, 
            s.sub_sector AS industry,
            mc.market_cap_crore AS market_cap_cr,
            mc.pe_ratio,
            mc.pb_ratio,
            mc.dividend_yield_pct
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN market_cap mc ON c.id = mc.company_id AND mc.year = (SELECT MAX(year) FROM market_cap)
        WHERE c.id = ?
    """
    comp = df_from_query(company_sql, [ticker])
    if comp.empty:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")

    company_id = comp.iloc[0]["id"]
    kpi_sql = """
        SELECT * FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year DESC
        LIMIT 1
    """
    kpi = df_from_query(kpi_sql, [company_id])

    profile = comp.to_dict(orient="records")[0]
    profile["latest_kpis"] = kpi.to_dict(orient="records")[0] if not kpi.empty else {}
    return JSONResponse(content=profile)


@app.get("/kpi/{ticker}", tags=["KPI"])
def get_kpi_history(ticker: str):
    """Historical KPI time-series for a company."""
    ticker = ticker.upper()
    comp = df_from_query("SELECT id FROM companies WHERE id = ?", [ticker])
    if comp.empty:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
    company_id = comp.iloc[0]["id"]
    df = df_from_query(
        "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year",
        [company_id],
    )
    return JSONResponse(content=df.to_dict(orient="records"))


@app.get("/screen/{preset}", tags=["Screener"])
def run_screen(preset: str, top_n: int = Query(20, ge=1, le=100)):
    """Run a named screener preset and return ranked companies."""
    try:
        # Import here to avoid circular imports at startup
        from src.analytics.screener import screen
        df = screen(preset, top_n=top_n)
        cols = [c for c in ["name", "ticker", "sector", "market_cap_cr",
                             "return_on_equity_pct", "net_profit_margin_pct",
                             "debt_to_equity", "free_cash_flow_cr", "pe_ratio"]
                if c in df.columns]
        return JSONResponse(content=df[cols].to_dict(orient="records"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"/screen/{preset}: {e}")
        raise HTTPException(status_code=500, detail="Screener error — see server logs")


@app.get("/sectors", tags=["Sectors"])
def sector_summary():
    """Aggregated stats per sector."""
    sql = """
        SELECT
            s.broad_sector AS sector,
            COUNT(DISTINCT c.id)                              AS company_count,
            ROUND(AVG(fr.return_on_equity_pct), 2)            AS avg_roe,
            ROUND(AVG(fr.net_profit_margin_pct), 2)           AS avg_npm,
            ROUND(AVG(fr.debt_to_equity), 2)                  AS avg_dte,
            ROUND(SUM(mc.market_cap_crore), 0)                AS total_market_cap_cr
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN financial_ratios fr ON c.id = fr.company_id
        LEFT JOIN market_cap mc ON c.id = mc.company_id AND mc.year = (SELECT MAX(year) FROM market_cap)
        GROUP BY s.broad_sector
        ORDER BY total_market_cap_cr DESC NULLS LAST
    """
    df = df_from_query(sql)
    return JSONResponse(content=df.to_dict(orient="records"))


@app.get("/search", tags=["Search"])
def search(q: str = Query(..., min_length=2, description="Search term (name or ticker)")):
    """Fuzzy search companies by name or ticker."""
    like = f"%{q.lower()}%"
    sql = """
        SELECT 
            c.id, 
            c.company_name AS name, 
            c.id AS ticker, 
            s.broad_sector AS sector, 
            mc.market_cap_crore AS market_cap_cr
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN market_cap mc ON c.id = mc.company_id AND mc.year = (SELECT MAX(year) FROM market_cap)
        WHERE LOWER(c.company_name) LIKE ? OR LOWER(c.id) LIKE ?
        ORDER BY mc.market_cap_crore DESC NULLS LAST
        LIMIT 20
    """
    df = df_from_query(sql, [like, like])
    return JSONResponse(content=df.to_dict(orient="records"))
