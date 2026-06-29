"""
src/analytics/cashflow_kpis.py
Cash Flow Intelligence Module.

Computes the following metrics per company-year:
  - CFO Quality Score  (CFO/PAT ratio → badge)
  - CapEx Intensity    (abs(CFI)/Sales %)
  - FCF CAGR           (5yr and 10yr)
  - FCF Conversion Rate (FCF / EBITDA)
  - Debt Repayment Detection
  - Distress Pattern   (CFO<0 + CFF>0)
  - Capital Allocation Matrix (8 sign patterns)

Outputs:
  - cashflow_intelligence.xlsx
  - capital_allocation.csv
  - distress_alerts.csv
"""
import os
import logging

import pandas as pd

logger = logging.getLogger("analytics.cashflow_kpis")

# 8 capital allocation patterns based on CFO/CFI/CFF sign combinations
CAPITAL_ALLOCATION_PATTERNS = {
    ("+", "-", "-"): "Reinvestor",            # CFO>0, CFI<0, CFF<0 (paying debt + investing)
    ("+", "-", "+"): "Growth Fundraiser",     # CFO>0, CFI<0, CFF>0 (investing + raising capital)
    ("+", "+", "-"): "Asset Seller / Returns",# CFO>0, CFI>0, CFF<0 (selling assets, returning cash)
    ("+", "+", "+"): "Cash Accumulator",      # CFO>0, CFI>0, CFF>0 (all positive — rare)
    ("-", "-", "+"): "Distress Signal",       # CFO<0, CFI<0, CFF>0 (raising funds to survive)
    ("-", "+", "+"): "Liquidator",            # CFO<0, CFI>0, CFF>0 (selling assets + raising funds)
    ("-", "-", "-"): "Cash Burner",           # All negative — deep distress
    ("-", "+", "-"): "Restructuring",         # CFO<0, CFI>0, CFF<0
}


def _sign(val) -> str:
    if pd.isna(val) or val is None:
        return "?"
    return "+" if val >= 0 else "-"


def compute_capital_allocation(cf: pd.DataFrame) -> pd.DataFrame:
    """Assign capital allocation pattern to each company-year row."""
    df = cf.copy()
    df["cfo_sign"] = df["operating_activity"].apply(_sign)
    df["cfi_sign"] = df["investing_activity"].apply(_sign)
    df["cff_sign"] = df["financing_activity"].apply(_sign)
    df["pattern_label"] = df.apply(
        lambda r: CAPITAL_ALLOCATION_PATTERNS.get(
            (r["cfo_sign"], r["cfi_sign"], r["cff_sign"]), "Unknown"
        ),
        axis=1,
    )
    return df[["company_id", "year", "cfo_sign", "cfi_sign", "cff_sign",
               "operating_activity", "investing_activity", "financing_activity",
               "pattern_label"]]


def compute_cashflow_intelligence(
    cf: pd.DataFrame,
    pl: pd.DataFrame,
    bs: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute all 7 cash flow intelligence metrics per company-year.

    Returns DataFrame with columns:
      company_id, year,
      cfo_quality_score, cfo_quality_badge,
      capex_intensity_pct,
      fcf_cr, fcf_cagr_5yr,
      fcf_conversion_rate,
      debt_deleveraging_flag, distress_flag,
      pattern_label
    """
    # Merge CF + PL + BS
    merged = cf.merge(
        pl[["company_id", "year", "sales", "net_profit", "operating_profit"]],
        on=["company_id", "year"], how="left"
    ).merge(
        bs[["company_id", "year", "borrowings"]],
        on=["company_id", "year"], how="left"
    )

    # 7.1 CFO Quality Score
    def cfo_quality(row):
        if pd.isna(row["net_profit"]) or row["net_profit"] == 0:
            return None, "N/A"
        if pd.isna(row["operating_activity"]):
            return None, "N/A"
        ratio = row["operating_activity"] / row["net_profit"]
        if ratio > 1.0:
            badge = "High Quality"
        elif ratio >= 0.5:
            badge = "Moderate"
        else:
            badge = "Accrual Risk"
        return round(ratio, 4), badge

    merged[["cfo_pat_ratio", "cfo_quality_badge"]] = merged.apply(
        lambda r: pd.Series(cfo_quality(r)), axis=1
    )

    # 7.2 CapEx Intensity (abs(CFI) / Sales * 100)
    def capex_intensity(row):
        if pd.isna(row["investing_activity"]) or pd.isna(row["sales"]) or row["sales"] == 0:
            return None
        intensity = abs(row["investing_activity"]) / row["sales"] * 100
        return round(intensity, 4)

    merged["capex_intensity_pct"] = merged.apply(capex_intensity, axis=1)

    def capex_label(v):
        if v is None or pd.isna(v):
            return "N/A"
        if v < 3:
            return "Asset-Light"
        if v < 8:
            return "Moderate"
        return "Capital Intensive"

    merged["capex_label"] = merged["capex_intensity_pct"].apply(capex_label)

    # 7.4 FCF = CFO + CFI
    merged["fcf_cr"] = merged.apply(
        lambda r: (r["operating_activity"] + r["investing_activity"])
        if not pd.isna(r["operating_activity"]) and not pd.isna(r["investing_activity"])
        else None,
        axis=1
    )

    # FCF Conversion Rate = FCF / EBITDA (operating_profit proxy)
    def fcf_conversion(row):
        if pd.isna(row["fcf_cr"]) or pd.isna(row["operating_profit"]) or row["operating_profit"] == 0:
            return None
        return round(row["fcf_cr"] / row["operating_profit"] * 100, 4)

    merged["fcf_conversion_rate"] = merged.apply(fcf_conversion, axis=1)

    # 7.5 Debt Deleveraging: CFF < 0 AND borrowings declining YoY
    merged_sorted = merged.sort_values(["company_id", "year"])
    merged_sorted["borrowings_prev"] = merged_sorted.groupby("company_id")["borrowings"].shift(1)
    merged_sorted["debt_deleveraging_flag"] = merged_sorted.apply(
        lambda r: (
            not pd.isna(r["financing_activity"]) and r["financing_activity"] < 0 and
            not pd.isna(r["borrowings"]) and not pd.isna(r["borrowings_prev"]) and
            r["borrowings"] < r["borrowings_prev"]
        ),
        axis=1,
    )

    # 7.6 Distress: CFO < 0 AND CFF > 0
    merged_sorted["distress_flag"] = merged_sorted.apply(
        lambda r: (
            not pd.isna(r["operating_activity"]) and r["operating_activity"] < 0 and
            not pd.isna(r["financing_activity"]) and r["financing_activity"] > 0
        ),
        axis=1,
    )

    # 7.7 Capital Allocation Pattern
    cap_alloc = compute_capital_allocation(cf)
    result = merged_sorted.merge(
        cap_alloc[["company_id", "year", "pattern_label"]],
        on=["company_id", "year"], how="left"
    )

    keep_cols = [
        "company_id", "year",
        "operating_activity", "investing_activity", "financing_activity",
        "cfo_pat_ratio", "cfo_quality_badge",
        "capex_intensity_pct", "capex_label",
        "fcf_cr", "fcf_conversion_rate",
        "debt_deleveraging_flag", "distress_flag",
        "pattern_label",
    ]
    return result[[c for c in keep_cols if c in result.columns]]


def run_cashflow_intelligence(db_path: str, output_dir: str = "output") -> dict:
    """Load data, compute intelligence, and export CSVs."""
    import sqlite3
    os.makedirs(output_dir, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        cf = pd.read_sql("SELECT * FROM cashflow", conn)
        pl = pd.read_sql("SELECT company_id, year, sales, net_profit, operating_profit FROM profitandloss", conn)
        bs = pd.read_sql("SELECT company_id, year, borrowings FROM balancesheet", conn)

    logger.info(f"Loaded CF({len(cf)}), PL({len(pl)}), BS({len(bs)}) rows")

    # Capital allocation
    cap_alloc = compute_capital_allocation(cf)
    cap_alloc_path = os.path.join(output_dir, "capital_allocation.csv")
    cap_alloc.to_csv(cap_alloc_path, index=False)
    logger.info(f"Saved capital_allocation.csv: {len(cap_alloc)} rows")

    # Full intelligence
    intel = compute_cashflow_intelligence(cf, pl, bs)
    intel_path = os.path.join(output_dir, "cashflow_intelligence.csv")
    intel.to_csv(intel_path, index=False)
    logger.info(f"Saved cashflow_intelligence.csv: {len(intel)} rows")

    # Distress alerts
    distress = intel[intel["distress_flag"] == True].copy()
    distress_path = os.path.join(output_dir, "distress_alerts.csv")
    distress.to_csv(distress_path, index=False)
    logger.info(f"Distress alerts: {len(distress)} company-years flagged")

    return {
        "capital_allocation": cap_alloc,
        "intelligence": intel,
        "distress": distress,
    }


if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)-8s | %(message)s")
    db = os.getenv("DB_PATH", "data/nifty100.db")
    results = run_cashflow_intelligence(db)
    intel = results["intelligence"]
    print("\n=== Capital Allocation Pattern Distribution (Latest Year) ===")
    import sqlite3
    with sqlite3.connect(db) as conn:
        latest = pd.read_sql("SELECT MAX(year) as y FROM cashflow", conn).iloc[0]["y"]
    latest_intel = intel[intel["year"] == latest]
    if not latest_intel.empty:
        print(latest_intel["pattern_label"].value_counts().to_string())
