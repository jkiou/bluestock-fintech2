import os
import logging
import sqlite3
import time
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from src.etl.normaliser import normalize_ticker, normalize_year

# Load environment variables
load_dotenv()

logger = logging.getLogger("etl.loader")


def load_companies(file_path: str) -> pd.DataFrame:
    """
    Loads companies.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading companies from {file_path}")
    df = pd.read_excel(file_path, header=1)

    # Normalize ticker (id)
    df["id"] = df["id"].apply(normalize_ticker)

    # Strip whitespace/newlines from company name
    if "company_name" in df.columns:
        df["company_name"] = (
            df["company_name"]
            .astype(str)
            .str.replace(r"\n", " ", regex=True)
            .str.strip()
        )

    return df


def load_profit_loss(file_path: str) -> pd.DataFrame:
    """
    Loads profitandloss.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading profit and loss from {file_path}")
    df = pd.read_excel(file_path, header=1)

    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    df["year"] = df["year"].apply(normalize_year)

    return df


def load_balancesheet(file_path: str) -> pd.DataFrame:
    """
    Loads balancesheet.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading balance sheet from {file_path}")
    df = pd.read_excel(file_path, header=1)

    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    df["year"] = df["year"].apply(normalize_year)

    return df


def load_cashflow(file_path: str) -> pd.DataFrame:
    """
    Loads cashflow.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading cash flow from {file_path}")
    df = pd.read_excel(file_path, header=1)

    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    df["year"] = df["year"].apply(normalize_year)

    return df


def load_analysis(file_path: str) -> pd.DataFrame:
    """
    Loads analysis.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading analysis from {file_path}")
    df = pd.read_excel(file_path, header=1)

    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)

    return df


def load_documents(file_path: str) -> pd.DataFrame:
    """
    Loads documents.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading documents from {file_path}")
    df = pd.read_excel(file_path, header=1)

    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)

    # Year in documents is capitalized 'Year' and should be cast to integer
    if "Year" in df.columns:
        # Fill NA, then convert to int
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce").fillna(0).astype(int)

    return df


def load_prosandcons(file_path: str) -> pd.DataFrame:
    """
    Loads prosandcons.xlsx.
    header=1: Row 0 is metadata, Row 1 contains actual headers.
    """
    logger.info(f"Loading pros and cons from {file_path}")
    df = pd.read_excel(file_path, header=1)

    # Normalize fields
    df["company_id"] = df["company_id"].apply(normalize_ticker)

    return df


def load_sectors(file_path: str) -> pd.DataFrame:
    """
    Loads sectors.xlsx (supplementary).
    header=0: Row 0 contains headers.
    """
    logger.info(f"Loading sectors from {file_path}")
    df = pd.read_excel(file_path, header=0)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    return df


def load_stock_prices(file_path: str) -> pd.DataFrame:
    """
    Loads stock_prices.xlsx (supplementary).
    header=0: Row 0 contains headers.
    """
    logger.info(f"Loading stock prices from {file_path}")
    df = pd.read_excel(file_path, header=0)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


def load_market_cap(file_path: str) -> pd.DataFrame:
    """
    Loads market_cap.xlsx (supplementary).
    header=0: Row 0 contains headers.
    """
    logger.info(f"Loading market cap from {file_path}")
    df = pd.read_excel(file_path, header=0)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    return df


def load_financial_ratios(file_path: str) -> pd.DataFrame:
    """
    Loads financial_ratios.xlsx (supplementary).
    header=0: Row 0 contains headers.
    """
    logger.info(f"Loading financial ratios from {file_path}")
    df = pd.read_excel(file_path, header=0)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    if "year" in df.columns:
        df["year"] = df["year"].apply(normalize_year)
    return df


def load_peer_groups(file_path: str) -> pd.DataFrame:
    """
    Loads peer_groups.xlsx (supplementary).
    header=0: Row 0 contains headers.
    """
    logger.info(f"Loading peer groups from {file_path}")
    df = pd.read_excel(file_path, header=0)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    if "is_benchmark" in df.columns:
        df["is_benchmark"] = pd.to_numeric(df["is_benchmark"], errors="coerce").fillna(0).astype(int)
    return df


def load_all_core(raw_data_dir: str) -> dict:
    """
    Loads all 7 core files from the raw data directory and returns a dictionary of DataFrames.
    """
    return {
        "companies": load_companies(os.path.join(raw_data_dir, "companies.xlsx")),
        "profitandloss": load_profit_loss(
            os.path.join(raw_data_dir, "profitandloss.xlsx")
        ),
        "balancesheet": load_balancesheet(
            os.path.join(raw_data_dir, "balancesheet.xlsx")
        ),
        "cashflow": load_cashflow(os.path.join(raw_data_dir, "cashflow.xlsx")),
        "analysis": load_analysis(os.path.join(raw_data_dir, "analysis.xlsx")),
        "documents": load_documents(os.path.join(raw_data_dir, "documents.xlsx")),
        "prosandcons": load_prosandcons(os.path.join(raw_data_dir, "prosandcons.xlsx")),
    }


def init_db(db_path: str, schema_path: str):
    """
    Initialise the SQLite database by running the schema.sql file.
    """
    logger.info(f"Initialising database at {db_path} using schema from {schema_path}")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # If database file already exists, we drop it to ensure clean load
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info("Existing database file removed.")
        except Exception as e:
            logger.warning(f"Could not remove existing database file: {e}")

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
    logger.info("Database schema applied successfully.")


def load_all_to_sqlite(
    db_path: str = None,
    raw_dir: str = "data/raw",
    supporting_dir: str = "data/supporting",
    schema_path: str = "src/etl/schema.sql"
) -> pd.DataFrame:
    """
    Initialises the SQLite database, validates all raw and supporting datasets,
    removes duplicates, and loads them with proper Foreign Key order.
    """
    if db_path is None:
        db_path = os.getenv("DB_PATH", "data/nifty100.db")

    # 1. Initialize schema
    init_db(db_path, schema_path)

    # 2. Load all raw and supporting data
    logger.info("Loading all Excel files into memory...")
    dfs = {
        "companies": load_companies(os.path.join(raw_dir, "companies.xlsx")),
        "profitandloss": load_profit_loss(os.path.join(raw_dir, "profitandloss.xlsx")),
        "balancesheet": load_balancesheet(os.path.join(raw_dir, "balancesheet.xlsx")),
        "cashflow": load_cashflow(os.path.join(raw_dir, "cashflow.xlsx")),
        "analysis": load_analysis(os.path.join(raw_dir, "analysis.xlsx")),
        "documents": load_documents(os.path.join(raw_dir, "documents.xlsx")),
        "prosandcons": load_prosandcons(os.path.join(raw_dir, "prosandcons.xlsx")),
        
        "sectors": load_sectors(os.path.join(supporting_dir, "sectors.xlsx")),
        "stock_prices": load_stock_prices(os.path.join(supporting_dir, "stock_prices.xlsx")),
        "market_cap": load_market_cap(os.path.join(supporting_dir, "market_cap.xlsx")),
        "financial_ratios": load_financial_ratios(os.path.join(supporting_dir, "financial_ratios.xlsx")),
        "peer_groups": load_peer_groups(os.path.join(supporting_dir, "peer_groups.xlsx")),
    }

    audit_records = []
    dfs_cleaned = {}

    # 3. Clean and validate companies (master table) first
    co_df = dfs["companies"]
    
    # Ticker format filters (DQ-08)
    invalid_co_mask = (
        (co_df["id"] == "MISSING")
        | (co_df["id"].astype(str).str.len() < 2)
        | (co_df["id"].astype(str).str.len() > 12)
    )
    co_cleaned = co_df[~invalid_co_mask].copy()

    # Check for duplicate tickers in companies (DQ-01)
    if co_cleaned["id"].duplicated().any():
        dups = co_cleaned[co_cleaned["id"].duplicated()]["id"].unique()
        raise ValueError(f"CRITICAL DQ-01: Duplicate tickers found in companies table: {dups}")

    co_cleaned = co_cleaned.drop_duplicates(subset=["id"], keep="first")
    valid_tickers = set(co_cleaned["id"])
    dfs_cleaned["companies"] = co_cleaned

    # 4. Clean all other tables
    for name, df in dfs.items():
        if name == "companies":
            continue

        df_cleaned = df.copy()

        # Ticker format check (DQ-08)
        ticker_col = "company_id"
        if ticker_col in df_cleaned.columns:
            invalid_ticker_mask = (
                (df_cleaned[ticker_col] == "MISSING")
                | (df_cleaned[ticker_col].astype(str).str.len() < 2)
                | (df_cleaned[ticker_col].astype(str).str.len() > 12)
            )
            df_cleaned = df_cleaned[~invalid_ticker_mask]

        # Year format check (DQ-07)
        if "year" in df_cleaned.columns and name in ("profitandloss", "balancesheet", "cashflow", "financial_ratios"):
            invalid_year_mask = (df_cleaned["year"] == "PARSE_ERROR") | (
                ~df_cleaned["year"].astype(str).str.match(r"^\d{4}-\d{2}$")
            )
            df_cleaned = df_cleaned[~invalid_year_mask]

        # Foreign Key checks (DQ-03)
        if ticker_col in df_cleaned.columns:
            orphan_mask = ~df_cleaned[ticker_col].isin(valid_tickers)
            df_cleaned = df_cleaned[~orphan_mask]

        # Data Coercion & Recalculation Rules
        if name == "balancesheet":
            if "fixed_assets" in df_cleaned.columns:
                neg_fa = df_cleaned["fixed_assets"] < 0
                if neg_fa.any():
                    neg_fa_companies = df_cleaned.loc[neg_fa, ["company_id", "year", "fixed_assets"]]
                    for _, r in neg_fa_companies.iterrows():
                        logger.warning(f"Coercing negative fixed_assets to 0 for {r['company_id']} ({r['year']}): {r['fixed_assets']}")
                    df_cleaned.loc[neg_fa, "fixed_assets"] = 0.0

        if name == "cashflow":
            if all(col in df_cleaned.columns for col in ["net_cash_flow", "operating_activity", "investing_activity", "financing_activity"]):
                cfo = df_cleaned["operating_activity"]
                cfi = df_cleaned["investing_activity"]
                cff = df_cleaned["financing_activity"]
                ncf = df_cleaned["net_cash_flow"]
                computed_ncf = cfo + cfi + cff
                mismatch_mask = abs(ncf - computed_ncf) > 10
                if mismatch_mask.any():
                    mismatches = df_cleaned.loc[mismatch_mask, ["company_id", "year", "net_cash_flow"]]
                    for _, r in mismatches.iterrows():
                        comp_val = cfo.loc[r.name] + cfi.loc[r.name] + cff.loc[r.name]
                        logger.warning(f"Recalculating mismatched net_cash_flow for {r['company_id']} ({r['year']}): {r['net_cash_flow']} -> {comp_val}")
                    df_cleaned.loc[mismatch_mask, "net_cash_flow"] = computed_ncf

        # Deduplication rules (keep="last" per DQ-02)
        if name in ("profitandloss", "balancesheet", "cashflow", "financial_ratios", "market_cap"):
            df_cleaned = df_cleaned.drop_duplicates(subset=["company_id", "year"], keep="last")
        elif name == "stock_prices":
            df_cleaned = df_cleaned.drop_duplicates(subset=["company_id", "date"], keep="last")
        elif name == "documents":
            df_cleaned = df_cleaned.drop_duplicates(subset=["company_id", "Year"], keep="last")
        elif name in ("analysis", "sectors"):
            df_cleaned = df_cleaned.drop_duplicates(subset=["company_id"], keep="last")
        elif name == "peer_groups":
            df_cleaned = df_cleaned.drop_duplicates(subset=["peer_group_name", "company_id"], keep="last")

        # Drop 'id' column if it exists in DataFrame to let SQLite handle the Autoincrement PK
        if "id" in df_cleaned.columns:
            df_cleaned = df_cleaned.drop(columns=["id"])

        dfs_cleaned[name] = df_cleaned

    # 5. Insert into SQLite enforcing Foreign Key order (companies must be loaded first)
    # Define sequence of tables
    load_order = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "sectors",
        "stock_prices",
        "market_cap",
        "financial_ratios",
        "peer_groups"
    ]

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        
        for name in load_order:
            df_cleaned = dfs_cleaned[name]
            start_time = time.time()
            rows_in = len(dfs[name])

            # Insert using pandas to_sql
            df_cleaned.to_sql(name, conn, if_exists="append", index=False)
            
            rows_out = len(df_cleaned)
            runtime = time.time() - start_time
            
            audit_records.append({
                "table": name,
                "rows_in": rows_in,
                "rows_out": rows_out,
                "rejected": rows_in - rows_out,
                "timestamp": datetime.now().isoformat(),
                "runtime_s": round(runtime, 4)
            })

        # Final Database-level Foreign Key Validation
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()
        if fk_violations:
            logger.error(f"Foreign Key check failed: {fk_violations}")
            raise ValueError(f"CRITICAL: SQLite foreign key violations found: {fk_violations}")

    # 6. Generate load_audit.csv
    audit_df = pd.DataFrame(audit_records)
    os.makedirs("output", exist_ok=True)
    audit_df.to_csv("output/load_audit.csv", index=False)
    logger.info("ETL database load completed successfully.")
    
    return audit_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        audit_df = load_all_to_sqlite()
        print("\n=== ETL Load Audit Log ===")
        print(audit_df.to_string(index=False))
    except Exception as e:
        logger.error(f"ETL Load failed: {e}", exc_info=True)
