"""
src/analytics/cagr.py
CAGR Engine — Computes Revenue / PAT / EPS CAGR for 3yr, 5yr, 10yr windows.
Handles all edge cases per the project spec (Section 23.1):
  - Positive→Negative : DECLINE_TO_LOSS → None
  - Negative→Positive : TURNAROUND → None (with flag)
  - Both Negative     : BOTH_NEGATIVE → None
  - Zero base         : ZERO_BASE → None
  - < 3yr history     : INSUFFICIENT → None
"""
import logging
from typing import Optional, Tuple

import pandas as pd

logger = logging.getLogger("analytics.cagr")


CAGR_FLAGS = {
    "DECLINE_TO_LOSS": "N/A — turned loss",
    "TURNAROUND":      "Turnaround ↑",
    "BOTH_NEGATIVE":   "N/A — both loss",
    "ZERO_BASE":       "N/A — base=0",
    "INSUFFICIENT":    "N/A — <3yr history",
    "OK":              None,
}


def _safe_cagr(start: float, end: float, n: int) -> Tuple[Optional[float], str]:
    """Return (cagr_value, flag). Flag is 'OK' on success."""
    if n < 3:
        return None, "INSUFFICIENT"
    if start is None or end is None or pd.isna(start) or pd.isna(end):
        return None, "INSUFFICIENT"
    if start == 0:
        return None, "ZERO_BASE"
    if start > 0 and end < 0:
        return None, "DECLINE_TO_LOSS"
    if start < 0 and end > 0:
        return None, "TURNAROUND"
    if start < 0 and end < 0:
        return None, "BOTH_NEGATIVE"
    try:
        value = ((end / start) ** (1 / n) - 1) * 100
        return round(value, 4), "OK"
    except Exception as e:
        logger.warning(f"CAGR error (start={start}, end={end}, n={n}): {e}")
        return None, "INSUFFICIENT"


def compute_cagr_series(
    df: pd.DataFrame,
    value_col: str,
    windows: tuple = (3, 5, 10),
) -> pd.DataFrame:
    """
    Compute CAGR for a given metric across multiple windows for all companies.

    Parameters
    ----------
    df        : pd.DataFrame with columns [company_id, year, <value_col>]
    value_col : e.g. 'sales', 'net_profit', 'eps'
    windows   : tuple of year windows, default (3, 5, 10)

    Returns
    -------
    pd.DataFrame — pivot with one row per (company_id, latest_year),
                   columns: <metric>_cagr_3yr, <metric>_cagr_5yr, <metric>_cagr_10yr,
                             <metric>_cagr_3yr_flag, etc.
    """
    results = []
    short_col = value_col.replace("_", "")[:8]  # short name for column prefix

    for cid, grp in df.groupby("company_id"):
        grp = grp.sort_values("year").dropna(subset=[value_col])
        if grp.empty:
            continue

        # Latest available row
        latest_year = grp["year"].max()
        latest_val  = grp.loc[grp["year"] == latest_year, value_col].iloc[0]

        row = {"company_id": cid, "year": latest_year}

        for n in windows:
            col_name  = f"{value_col}_cagr_{n}yr"
            flag_name = f"{value_col}_cagr_{n}yr_flag"

            # Find base row (n years back from latest)
            base_rows = grp[grp["year"] <= latest_year].sort_values("year")
            if len(base_rows) < n + 1:
                row[col_name]  = None
                row[flag_name] = "INSUFFICIENT"
                continue

            base_val = base_rows.iloc[-(n + 1)][value_col]
            cagr_val, flag = _safe_cagr(base_val, latest_val, n)
            row[col_name]  = cagr_val
            row[flag_name] = flag

        results.append(row)

    return pd.DataFrame(results) if results else pd.DataFrame()


def compute_all_cagrs(pl: pd.DataFrame) -> pd.DataFrame:
    """Compute Revenue, PAT, and EPS CAGR for all windows."""
    frames = []

    for col in ["sales", "net_profit", "eps"]:
        if col not in pl.columns:
            logger.warning(f"Column '{col}' not in P&L DataFrame — skipping CAGR")
            continue
        cagr_df = compute_cagr_series(pl, col)
        if not cagr_df.empty:
            frames.append(cagr_df.set_index(["company_id", "year"]))

    if not frames:
        return pd.DataFrame()

    merged = frames[0]
    for f in frames[1:]:
        merged = merged.join(f, how="outer")

    return merged.reset_index()


if __name__ == "__main__":
    import os, sqlite3
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)-8s | %(message)s")
    db = os.getenv("DB_PATH", "data/nifty100.db")
    with sqlite3.connect(db) as conn:
        pl = pd.read_sql("SELECT company_id, year, sales, net_profit, eps FROM profitandloss", conn)

    result = compute_all_cagrs(pl)
    print(f"CAGR rows: {len(result)}")
    cols = [c for c in result.columns if "cagr" in c and "flag" not in c]
    print(result[["company_id"] + cols[:6]].head(10).to_string(index=False))
