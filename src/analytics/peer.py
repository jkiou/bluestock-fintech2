"""
src/analytics/peer.py
Peer Comparison Engine.

Features:
  - Intra-group percentile rank per metric
  - Radar chart data across 8 axes
  - Benchmark gap analysis vs group benchmark company
  - Best-in-class detection (top quartile on ≥6 of 10 metrics)
  - Weak company detection (bottom quartile on ≥4 of 10 metrics)

Outputs:
  - peer_percentiles table / DataFrame
  - peer_comparison.xlsx (one sheet per group)
  - radar chart data dicts
"""
import os
import logging

import numpy as np
import pandas as pd
from scipy.stats import percentileofscore

logger = logging.getLogger("analytics.peer")

# 8 radar chart axes
RADAR_METRICS = [
    "return_on_equity_pct",
    "operating_profit_margin_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "sales_cagr_5yr",
    "net_profit_cagr_5yr",
    "earnings_per_share",
]

# 10 metrics used for best-in-class / weak detection
SCORING_METRICS = [
    "return_on_equity_pct",
    "operating_profit_margin_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "interest_coverage",
    "asset_turnover",
    "earnings_per_share",
]

# Metrics where lower is better (inverted for ranking)
LOWER_IS_BETTER = {"debt_to_equity"}


def load_peer_groups(db_path: str) -> pd.DataFrame:
    """Load peer_groups table from SQLite."""
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        try:
            pg = pd.read_sql("SELECT * FROM peer_groups", conn)
        except Exception:
            logger.warning("peer_groups table not found — returning empty DataFrame")
            pg = pd.DataFrame(columns=["company_id", "peer_group_name", "is_benchmark"])
    return pg


def compute_percentile_ranks(
    ratios: pd.DataFrame,
    peer_groups: pd.DataFrame,
    year: str = None,
) -> pd.DataFrame:
    """
    Compute within-group percentile ranks for all metrics.

    Parameters
    ----------
    ratios      : DataFrame with company KPIs (from financial_ratios table + CAGR cols)
    peer_groups : DataFrame with columns [company_id, peer_group_name, is_benchmark]
    year        : optional string to filter; if None uses latest available per company

    Returns
    -------
    DataFrame with columns:
        company_id, peer_group_name, year, <metric>, <metric>_pct_rank
    """
    if year is None:
        # Use latest year per company
        latest = ratios.loc[ratios.groupby("company_id")["year"].idxmax()].copy()
    else:
        latest = ratios[ratios["year"] == year].copy()

    # Merge with peer groups
    merged = peer_groups.merge(latest, on="company_id", how="left")
    if merged.empty:
        return pd.DataFrame()

    results = []
    for group_name, group_df in merged.groupby("peer_group_name"):
        for metric in SCORING_METRICS:
            if metric not in group_df.columns:
                continue
            valid = group_df[metric].dropna()
            if valid.empty:
                continue
            invert = metric in LOWER_IS_BETTER
            group_df[f"{metric}_pct_rank"] = group_df[metric].apply(
                lambda v: (
                    100 - percentileofscore(valid, v, kind="rank")
                    if invert else
                    percentileofscore(valid, v, kind="rank")
                ) if not pd.isna(v) else None
            )
        results.append(group_df)

    if not results:
        return pd.DataFrame()

    out = pd.concat(results, ignore_index=True)
    return out


def compute_best_worst_flags(pct_df: pd.DataFrame) -> pd.DataFrame:
    """Add best_in_class and watchlist flags per company per group."""
    rank_cols = [c for c in pct_df.columns if c.endswith("_pct_rank")]

    def _classify(row):
        top  = sum(1 for c in rank_cols if not pd.isna(row.get(c)) and row[c] >= 75)
        bot  = sum(1 for c in rank_cols if not pd.isna(row.get(c)) and row[c] <= 25)
        best = top >= 6
        weak = bot >= 4
        return pd.Series({"best_in_class": best, "watchlist": weak})

    flags = pct_df.apply(_classify, axis=1)
    return pd.concat([pct_df, flags], axis=1)


def get_radar_data(
    company_id: str,
    peer_group: str,
    ratios: pd.DataFrame,
    peer_groups: pd.DataFrame,
) -> dict:
    """
    Return radar chart data for a company vs its peer group average.

    Returns dict with keys:
      company_id, peer_group, metrics, company_values, group_avg_values, benchmark_values
    """
    latest_all = ratios.loc[ratios.groupby("company_id")["year"].idxmax()]

    # Group members
    members = peer_groups[peer_groups["peer_group_name"] == peer_group]["company_id"].tolist()
    group_data = latest_all[latest_all["company_id"].isin(members)]
    company_data = latest_all[latest_all["company_id"] == company_id]

    benchmark = peer_groups[
        (peer_groups["peer_group_name"] == peer_group) &
        (peer_groups["is_benchmark"] == True)
    ]["company_id"].tolist()
    bench_data = latest_all[latest_all["company_id"].isin(benchmark)] if benchmark else pd.DataFrame()

    avail = [m for m in RADAR_METRICS if m in group_data.columns]
    company_vals = []
    group_avg    = []
    bench_vals   = []

    for m in avail:
        col_vals = group_data[m].dropna()
        p10 = col_vals.quantile(0.10) if len(col_vals) > 1 else 0
        p90 = col_vals.quantile(0.90) if len(col_vals) > 1 else 1
        rng  = p90 - p10 if p90 != p10 else 1

        def norm(v):
            if pd.isna(v):
                return None
            if m in LOWER_IS_BETTER:
                return round(max(0, min(100, (1 - (v - p10) / rng) * 100)), 1)
            return round(max(0, min(100, (v - p10) / rng * 100)), 1)

        cv = company_data[m].iloc[0] if not company_data.empty and m in company_data.columns else None
        company_vals.append(norm(cv))
        group_avg.append(round(col_vals.mean(), 2) if len(col_vals) > 0 else None)

        if not bench_data.empty and m in bench_data.columns:
            bv = bench_data[m].iloc[0]
            bench_vals.append(norm(bv))
        else:
            bench_vals.append(None)

    return {
        "company_id":       company_id,
        "peer_group":       peer_group,
        "metrics":          avail,
        "company_values":   company_vals,
        "group_avg_values": group_avg,
        "benchmark_values": bench_vals,
    }


def export_peer_comparison_excel(
    pct_df: pd.DataFrame,
    output_path: str = "output/peer_comparison.xlsx",
):
    """Export one sheet per peer group to Excel with colour-coded percentile cells."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    try:
        import openpyxl
        from openpyxl.styles import PatternFill, Font
    except ImportError:
        logger.warning("openpyxl not installed — skipping Excel export")
        return

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for group_name, gdf in pct_df.groupby("peer_group_name"):
            sheet_name = str(group_name)[:31]  # Excel sheet name limit
            display_cols = ["company_id", "peer_group_name"] + SCORING_METRICS + [
                f"{m}_pct_rank" for m in SCORING_METRICS if f"{m}_pct_rank" in gdf.columns
            ] + ["best_in_class", "watchlist"]
            display_cols = [c for c in display_cols if c in gdf.columns]
            gdf[display_cols].to_excel(writer, sheet_name=sheet_name, index=False)

    logger.info(f"Peer comparison Excel saved: {output_path}")


def run_peer_engine(db_path: str, output_dir: str = "output") -> dict:
    """Full peer comparison pipeline."""
    import sqlite3
    os.makedirs(output_dir, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        ratios = pd.read_sql("SELECT * FROM financial_ratios", conn)
        peer_groups = pd.read_sql("SELECT * FROM peer_groups", conn) if _has_table(conn, "peer_groups") else pd.DataFrame()
        if peer_groups.empty:
            # Try loading from companies / sectors
            logger.warning("peer_groups table empty — peer engine will produce no output")
            return {}

    if "is_benchmark" not in peer_groups.columns:
        peer_groups["is_benchmark"] = False

    pct_df = compute_percentile_ranks(ratios, peer_groups)
    if pct_df.empty:
        logger.warning("Percentile rank DataFrame is empty")
        return {}

    pct_df = compute_best_worst_flags(pct_df)

    # Save percentiles CSV
    pct_path = os.path.join(output_dir, "peer_percentiles.csv")
    pct_df.to_csv(pct_path, index=False)
    logger.info(f"Peer percentiles saved: {pct_path}")

    # Export Excel
    excel_path = os.path.join(output_dir, "peer_comparison.xlsx")
    export_peer_comparison_excel(pct_df, excel_path)

    # Best-in-class / watchlist
    best = pct_df[pct_df.get("best_in_class", pd.Series(False, index=pct_df.index)) == True]
    weak = pct_df[pct_df.get("watchlist", pd.Series(False, index=pct_df.index)) == True]
    logger.info(f"Best-in-class companies: {len(best)}")
    logger.info(f"Watchlist companies: {len(weak)}")

    return {"percentiles": pct_df, "best_in_class": best, "watchlist": weak}


def _has_table(conn, table_name: str) -> bool:
    cur = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None


if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)-8s | %(message)s")
    db = os.getenv("DB_PATH", "data/nifty100.db")
    results = run_peer_engine(db)
    if "percentiles" in results:
        print(f"\nPeer percentiles: {len(results['percentiles'])} rows")
