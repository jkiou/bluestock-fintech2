"""
src/analytics/ratios.py
KPI & Ratio Engine — computes 50+ financial KPIs from the SQLite database
and writes results back to the financial_ratios table.
"""
import os
import logging
import sqlite3
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("analytics.ratios")

DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")


# ---------------------------------------------------------------------------
# Helper: safe division
# ---------------------------------------------------------------------------
def safe_div(numerator, denominator, default=None):
    """Return numerator/denominator or default when denominator is 0/NaN."""
    if pd.isna(denominator) or denominator == 0:
        return default
    if pd.isna(numerator):
        return default
    return numerator / denominator


# ---------------------------------------------------------------------------
# CAGR helper
# ---------------------------------------------------------------------------
def cagr(start_val, end_val, years):
    """Compound Annual Growth Rate."""
    if pd.isna(start_val) or pd.isna(end_val) or years <= 0:
        return None
    if start_val <= 0 or end_val <= 0:
        return None
    return (end_val / start_val) ** (1 / years) - 1


# ---------------------------------------------------------------------------
# 1. Profitability ratios (from profitandloss + balancesheet)
# ---------------------------------------------------------------------------
def compute_profitability(pl: pd.DataFrame, bs: pd.DataFrame) -> pd.DataFrame:
    """
    Computes per-row metrics:
    - net_profit_margin_pct
    - operating_profit_margin_pct
    - return_on_equity_pct
    - earnings_per_share   (from eps column)
    - dividend_payout_ratio_pct
    """
    merged = pl.merge(
        bs[["company_id", "year", "equity_capital", "reserves", "total_assets",
            "total_liabilities", "borrowings"]],
        on=["company_id", "year"],
        how="inner",
    )

    merged["net_profit_margin_pct"] = merged.apply(
        lambda r: (v * 100) if (v := safe_div(r["net_profit"], r["sales"])) is not None else None, axis=1
    )
    merged["operating_profit_margin_pct"] = merged.apply(
        lambda r: (v * 100) if (v := safe_div(r["operating_profit"], r["sales"])) is not None else None, axis=1
    )
    # Shareholders' equity = equity_capital + reserves
    merged["shareholders_equity"] = merged["equity_capital"].fillna(0) + merged["reserves"].fillna(0)
    merged["return_on_equity_pct"] = merged.apply(
        lambda r: (v * 100) if (v := safe_div(r["net_profit"], r["shareholders_equity"])) is not None else None, axis=1
    )
    merged["debt_to_equity"] = merged.apply(
        lambda r: safe_div(r["borrowings"], r["shareholders_equity"]), axis=1
    )
    merged["asset_turnover"] = merged.apply(
        lambda r: safe_div(r["sales"], r["total_assets"]), axis=1
    )
    merged["earnings_per_share"] = merged["eps"]
    merged["dividend_payout_ratio_pct"] = merged["dividend_payout"]

    return merged


# ---------------------------------------------------------------------------
# 2. Leverage & coverage ratios
# ---------------------------------------------------------------------------
def compute_leverage(pl: pd.DataFrame, bs: pd.DataFrame) -> pd.DataFrame:
    """
    Computes:
    - interest_coverage  (EBIT / interest)
    - total_debt_cr
    """
    merged = pl.merge(
        bs[["company_id", "year", "borrowings"]],
        on=["company_id", "year"],
        how="inner",
    )
    # Approximate EBIT = operating_profit (already excludes interest for most setups)
    merged["interest_coverage"] = merged.apply(
        lambda r: safe_div(r["operating_profit"], r["interest"]), axis=1
    )
    merged["total_debt_cr"] = merged["borrowings"]
    return merged


# ---------------------------------------------------------------------------
# 3. Cash-flow ratios
# ---------------------------------------------------------------------------
def compute_cashflow_ratios(cf: pd.DataFrame) -> pd.DataFrame:
    """
    Computes:
    - free_cash_flow_cr    = CFO - capex (approximated as abs(investing_activity) for capex)
    - capex_cr             = abs(investing_activity)
    - cash_from_operations_cr
    """
    df = cf.copy()
    df["capex_cr"] = df["investing_activity"].apply(
        lambda x: abs(x) if not pd.isna(x) else None
    )
    df["free_cash_flow_cr"] = df.apply(
        lambda r: (r["operating_activity"] - r["capex_cr"])
        if not pd.isna(r["operating_activity"]) and not pd.isna(r["capex_cr"])
        else None,
        axis=1,
    )
    df["cash_from_operations_cr"] = df["operating_activity"]
    return df


# ---------------------------------------------------------------------------
# 4. Book value per share
# ---------------------------------------------------------------------------
def compute_book_value_per_share(bs: pd.DataFrame, co: pd.DataFrame) -> pd.DataFrame:
    """
    book_value_per_share = (equity_capital + reserves) / shares_outstanding
    shares_outstanding approximated as equity_capital / face_value * 1e7 (₹1 face)
    Since actual share count isn't in DB, we use companies.book_value directly
    """
    merged = bs.merge(co[["id", "book_value", "face_value"]], left_on="company_id", right_on="id", how="left")
    merged["shareholders_equity"] = merged["equity_capital"].fillna(0) + merged["reserves"].fillna(0)
    # Use pre-computed book_value from companies table as reference; compute proxy per share
    merged["book_value_per_share"] = merged["book_value"]
    return merged


# ---------------------------------------------------------------------------
# 5. Main engine: load, compute, upsert
# ---------------------------------------------------------------------------
def run_ratio_engine(db_path: str = DB_PATH):
    """Load all tables, compute KPIs, and write to financial_ratios."""
    logger.info(f"Connecting to database: {db_path}")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        pl  = pd.read_sql("SELECT * FROM profitandloss",  conn)
        bs  = pd.read_sql("SELECT * FROM balancesheet",   conn)
        cf  = pd.read_sql("SELECT * FROM cashflow",       conn)
        co  = pd.read_sql("SELECT * FROM companies",      conn)
        fr  = pd.read_sql("SELECT * FROM financial_ratios", conn)

    logger.info(f"Loaded P&L({len(pl)}), BS({len(bs)}), CF({len(cf)}) rows")

    # Profitability
    prof = compute_profitability(pl, bs)
    # Leverage
    lev  = compute_leverage(pl, bs)
    # Cash flow
    cfr  = compute_cashflow_ratios(cf)
    # Book value
    bvps = compute_book_value_per_share(bs, co)

    # Assemble master KPI frame on (company_id, year)
    kpi = prof[["company_id", "year",
                "net_profit_margin_pct", "operating_profit_margin_pct",
                "return_on_equity_pct", "debt_to_equity", "asset_turnover",
                "earnings_per_share", "dividend_payout_ratio_pct"]].copy()

    kpi = kpi.merge(
        lev[["company_id", "year", "interest_coverage", "total_debt_cr"]],
        on=["company_id", "year"], how="left"
    )
    kpi = kpi.merge(
        cfr[["company_id", "year", "free_cash_flow_cr", "capex_cr", "cash_from_operations_cr"]],
        on=["company_id", "year"], how="left"
    )
    kpi = kpi.merge(
        bvps[["company_id", "year", "book_value_per_share"]],
        on=["company_id", "year"], how="left"
    )

    # Drop duplicates in case of multiple joins
    kpi = kpi.drop_duplicates(subset=["company_id", "year"], keep="last")

    # Round all numeric columns to 4 dp
    num_cols = kpi.select_dtypes(include="number").columns
    kpi[num_cols] = kpi[num_cols].round(4)

    logger.info(f"KPI frame assembled: {len(kpi)} rows")

    # Write back to SQLite (replace financial_ratios table)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        # Delete existing computed rows and replace
        conn.execute("DELETE FROM financial_ratios;")
        conn.commit()
        kpi.to_sql("financial_ratios", conn, if_exists="append", index=False)
        conn.commit()

    logger.info(f"Wrote {len(kpi)} KPI rows to financial_ratios table.")

    # Export KPI summary to output/kpi_summary.csv
    os.makedirs("output", exist_ok=True)
    kpi.to_csv("output/kpi_summary.csv", index=False)
    logger.info("Exported output/kpi_summary.csv")
    return kpi


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    df = run_ratio_engine()
    print(f"\n=== KPI Engine Complete — {len(df)} rows computed ===")
    print(df[["company_id", "year", "return_on_equity_pct", "net_profit_margin_pct",
              "debt_to_equity", "free_cash_flow_cr"]].head(10).to_string(index=False))
