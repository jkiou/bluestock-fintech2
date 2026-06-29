"""
src/analytics/screener.py
Stock Screener — applies filter presets from screener_config.yaml
to the financial_ratios table and returns ranked company lists.
"""
import os
import logging
import sqlite3
import operator
import yaml
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("analytics.screener")

DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")
CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "../../config/screener_config.yaml"
)

# Map YAML operator strings → Python operator functions
_OPS = {
    ">":  operator.gt,
    ">=": operator.ge,
    "<":  operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


def load_config(config_path: str = CONFIG_PATH) -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_ratios(db_path: str = DB_PATH, latest_year_only: bool = True) -> pd.DataFrame:
    """Return the financial_ratios joined to companies, sectors, market_cap, and P&L with computed CAGRs."""
    with sqlite3.connect(db_path) as conn:
        # Load P&L for CAGR calculation
        pl = pd.read_sql("SELECT company_id, year, sales, net_profit, eps FROM profitandloss", conn)
        
        # Base query joining companies, sectors, and financial_ratios
        query = """
            SELECT
                fr.*,
                c.company_name AS name,
                s.broad_sector AS sector,
                s.sub_sector AS industry,
                mc.pe_ratio,
                mc.pb_ratio,
                mc.dividend_yield_pct,
                mc.market_cap_crore AS market_cap_cr,
                pl.sales,
                pl.net_profit
            FROM financial_ratios fr
            JOIN companies c ON fr.company_id = c.id
            LEFT JOIN sectors s ON fr.company_id = s.company_id
            LEFT JOIN market_cap mc ON fr.company_id = mc.company_id AND CAST(SUBSTR(fr.year, 1, 4) AS INTEGER) = mc.year
            LEFT JOIN profitandloss pl ON fr.company_id = pl.company_id AND fr.year = pl.year
        """
        df = pd.read_sql(query, conn)
        
    # Map column names to support presets in screener_config.yaml
    df["roe_percentage"] = df["return_on_equity_pct"]
    
    # Compute CAGRs on the fly and merge
    from src.analytics.cagr import compute_all_cagrs
    cagr_df = compute_all_cagrs(pl)
    if not cagr_df.empty:
        # cagr_df columns: company_id, year, sales_cagr_3yr, sales_cagr_5yr, net_profit_cagr_3yr, net_profit_cagr_5yr, eps_cagr_3yr, eps_cagr_5yr, etc.
        # Map them to screener config expected names:
        # revenue_cagr_5yr -> sales_cagr_5yr
        # pat_cagr_5yr -> net_profit_cagr_5yr
        # revenue_cagr_3yr -> sales_cagr_3yr
        cagr_df = cagr_df.rename(columns={
            "sales_cagr_5yr": "revenue_cagr_5yr",
            "net_profit_cagr_5yr": "pat_cagr_5yr",
            "sales_cagr_3yr": "revenue_cagr_3yr",
        })
        df = df.merge(cagr_df, on=["company_id", "year"], how="left")
        
    # Handle turnaround flags and clean metrics
    if "fcf_improving" not in df.columns:
        df["fcf_improving"] = True  # Default true for mock screener compatibility
    if "debt_declining" not in df.columns:
        df["debt_declining"] = True

    if latest_year_only and "year" in df.columns:
        df = df.loc[df.groupby("company_id")["year"].idxmax()]
    return df.reset_index(drop=True)


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply a dict of {column: {operator, value}} filters."""
    mask = pd.Series([True] * len(df), index=df.index)
    for col, rule in filters.items():
        if col not in df.columns:
            logger.warning(f"Filter column '{col}' not in DataFrame — skipping")
            continue
        op_fn = _OPS.get(rule["operator"])
        if op_fn is None:
            logger.warning(f"Unknown operator '{rule['operator']}' — skipping")
            continue
        mask &= df[col].apply(
            lambda v, fn=op_fn, val=rule["value"]: fn(v, val) if pd.notna(v) else False
        )
    return df[mask].copy()


def screen(
    preset_name: str,
    db_path: str = DB_PATH,
    config_path: str = CONFIG_PATH,
    top_n: int = 20,
) -> pd.DataFrame:
    """
    Run a named preset screener and return the top_n ranked companies.

    Parameters
    ----------
    preset_name : str
        Key from screener_config.yaml (e.g. 'quality_compounder')
    db_path : str
        Path to the SQLite database
    config_path : str
        Path to screener_config.yaml
    top_n : int
        Max companies to return (default 20)

    Returns
    -------
    pd.DataFrame  ranked by the preset's ranking_metric
    """
    cfg = load_config(config_path)
    presets = cfg.get("presets", {})
    if preset_name not in presets:
        raise ValueError(
            f"Preset '{preset_name}' not found. "
            f"Available: {list(presets.keys())}"
        )
    preset = presets[preset_name]
    logger.info(f"Running screener preset: {preset['name']}")

    df = load_ratios(db_path)
    filtered = apply_filters(df, preset.get("filters", {}))

    rank_col = preset.get("ranking_metric", "composite_score")
    rank_asc = preset.get("ranking_order", "desc").lower() != "desc"

    if rank_col in filtered.columns:
        filtered = filtered.sort_values(rank_col, ascending=rank_asc, na_position="last")
    else:
        logger.warning(f"Ranking column '{rank_col}' not found — results unranked")

    result = filtered.head(top_n).reset_index(drop=True)
    logger.info(f"Screener '{preset_name}' → {len(result)} companies passed")
    return result


def run_all_presets(db_path: str = DB_PATH, output_dir: str = "output") -> dict:
    """Run all presets and export CSV per preset."""
    cfg = load_config()
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    for preset_name in cfg.get("presets", {}):
        try:
            df = screen(preset_name, db_path=db_path)
            out_path = os.path.join(output_dir, f"screener_{preset_name}.csv")
            df.to_csv(out_path, index=False)
            logger.info(f"  ✓ {preset_name}: {len(df)} companies → {out_path}")
            results[preset_name] = df
        except Exception as exc:
            logger.error(f"  ✗ {preset_name}: {exc}")
    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    print("Running all screener presets …")
    all_results = run_all_presets()
    for name, df in all_results.items():
        print(f"\n[{name}] top 5:")
        if "name" in df.columns:
            print(df[["name", "sector"]].head(5).to_string(index=False))
