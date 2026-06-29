import os
import logging
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.etl.loader import load_all_core
from src.etl.normaliser import normalize_ticker

logger = logging.getLogger("etl.validator")


class ValidationError(Exception):
    """Custom exception raised when a critical data quality rule halts validation/load."""

    pass


class DataValidator:
    def __init__(
        self,
        raw_data_dir: str = "data/raw",
        sectors_file: str = "data/supporting/sectors.xlsx",
    ):
        self.raw_data_dir = raw_data_dir
        self.sectors_file = sectors_file
        self.failures = []

    def log_failure(
        self, company_id: str, year: any, field: str, issue: str, severity: str
    ):
        """Helper to append a validation failure."""
        # Convert NaN/None values to clean empty values or strings
        co_id = (
            "MISSING" if pd.isna(company_id) or company_id is None else str(company_id)
        )
        yr_val = "" if pd.isna(year) or year is None else str(year)
        self.failures.append(
            {
                "company_id": co_id,
                "year": yr_val,
                "field": field,
                "issue": issue,
                "severity": severity,
            }
        )
        logger.warning(
            f"[{severity}] Ticker: {co_id}, Year: {yr_val}, Field: {field} -> {issue}"
        )

    def run_url_checks(self, documents_df: pd.DataFrame) -> dict:
        """Run parallel HEAD requests to validate URLs in documents.xlsx (DQ-13)."""
        if "Annual_Report" not in documents_df.columns:
            return {}

        urls = documents_df["Annual_Report"].dropna().unique()
        url_status = {}

        # Fast path if fast validation flag is set to avoid slow external HTTP timeouts
        if os.getenv("FAST_VALIDATION") == "True":
            logger.info("Fast/Simulated validation enabled: Mocking document URL check results.")
            for url in urls:
                if isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
                    url_status[url] = (True, "Mocked 200 OK")
                else:
                    url_status[url] = (False, "Invalid URL schema")
            return url_status

        def check_url(url):
            if not isinstance(url, str) or not (
                url.startswith("http://") or url.startswith("https://")
            ):
                return url, False, "Invalid URL schema"
            try:
                # Use a small timeout of 2 seconds
                response = requests.head(url, timeout=2.0, allow_redirects=True)
                return url, response.status_code == 200, f"HTTP {response.status_code}"
            except Exception as e:
                return url, False, str(e)

        logger.info(f"Checking {len(urls)} unique document URLs in parallel...")
        # Check URLs using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(check_url, url): url for url in urls}
            for future in as_completed(futures):
                url, is_valid, msg = future.result()
                url_status[url] = (is_valid, msg)

        return url_status

    def validate(self) -> pd.DataFrame:
        """Runs the 16 DQ validation rules on all core dataframes."""
        self.failures = []

        # Load raw files using loader helpers
        dfs = load_all_core(self.raw_data_dir)
        companies = dfs["companies"]
        profitandloss = dfs["profitandloss"]
        balancesheet = dfs["balancesheet"]
        cashflow = dfs["cashflow"]
        analysis = dfs["analysis"]
        documents = dfs["documents"]
        prosandcons = dfs["prosandcons"]

        # Load sectors to identify banks
        if os.path.exists(self.sectors_file):
            sectors_df = pd.read_excel(self.sectors_file)
            bank_subsectors = {"Private Banks", "Public Sector Banks"}
            bank_tickers = set(
                sectors_df[sectors_df["sub_sector"].isin(bank_subsectors)][
                    "company_id"
                ].apply(normalize_ticker)
            )
        else:
            logger.warning(
                f"Sectors file not found at {self.sectors_file}. Bank/non-bank checks will treat all as non-bank."
            )
            bank_tickers = set()

        # --- DQ-01: Company PK Uniqueness (CRITICAL) ---
        duplicates_co = companies[companies["id"].duplicated()]["id"].unique()
        for ticker in duplicates_co:
            self.log_failure(
                ticker, None, "id", "Duplicate ticker in companies table", "CRITICAL"
            )
        if len(duplicates_co) > 0:
            raise ValidationError(
                "CRITICAL DQ-01: Duplicate tickers found in companies. Ingestion halted."
            )

        # --- DQ-08: Ticker Format (CRITICAL) ---
        # We need to perform this check on all tables, and reject invalid rows
        tables_to_check = {
            "companies": (companies, "id"),
            "profitandloss": (profitandloss, "company_id"),
            "balancesheet": (balancesheet, "company_id"),
            "cashflow": (cashflow, "company_id"),
            "analysis": (analysis, "company_id"),
            "documents": (documents, "company_id"),
            "prosandcons": (prosandcons, "company_id"),
        }

        for table_name, (df, col) in tables_to_check.items():
            if df.empty or col not in df.columns:
                continue
            # Row-level check
            invalid_mask = (
                (df[col] == "MISSING")
                | (df[col].astype(str).str.len() < 2)
                | (df[col].astype(str).str.len() > 12)
            )
            invalid_df = df[invalid_mask]
            for idx, row in invalid_df.iterrows():
                ticker_val = row[col]
                year_val = row.get("year", row.get("Year", None))
                self.log_failure(
                    ticker_val,
                    year_val,
                    col,
                    f"Invalid ticker format in {table_name}",
                    "CRITICAL",
                )

            # Reject rows (keep valid only)
            dfs[table_name] = df[~invalid_mask]

        # Re-assign clean dataframes
        companies = dfs["companies"]
        profitandloss = dfs["profitandloss"]
        balancesheet = dfs["balancesheet"]
        cashflow = dfs["cashflow"]
        analysis = dfs["analysis"]
        documents = dfs["documents"]
        prosandcons = dfs["prosandcons"]

        # --- DQ-07: Year Format (CRITICAL) ---
        time_series_tables = {
            "profitandloss": profitandloss,
            "balancesheet": balancesheet,
            "cashflow": cashflow,
        }
        for table_name, df in time_series_tables.items():
            if df.empty:
                continue
            invalid_year_mask = (df["year"] == "PARSE_ERROR") | (
                ~df["year"].astype(str).str.match(r"^\d{4}-\d{2}$")
            )
            invalid_years = df[invalid_year_mask]
            for _, row in invalid_years.iterrows():
                self.log_failure(
                    row["company_id"],
                    row["year"],
                    "year",
                    f"Invalid year format in {table_name}",
                    "CRITICAL",
                )

            # Reject rows
            if table_name == "profitandloss":
                profitandloss = df[~invalid_year_mask]
            elif table_name == "balancesheet":
                balancesheet = df[~invalid_year_mask]
            elif table_name == "cashflow":
                cashflow = df[~invalid_year_mask]

        # --- DQ-02: Annual PK Uniqueness (CRITICAL) ---
        # No duplicate (company_id, year) in P&L, BS, CF tables
        for table_name, df in [
            ("profitandloss", profitandloss),
            ("balancesheet", balancesheet),
            ("cashflow", cashflow),
        ]:
            if df.empty:
                continue
            dup_mask = df.duplicated(subset=["company_id", "year"], keep="first")
            duplicates = df[dup_mask]
            for _, row in duplicates.iterrows():
                self.log_failure(
                    row["company_id"],
                    row["year"],
                    "company_id, year",
                    f"Duplicate annual record in {table_name}",
                    "CRITICAL",
                )

            # In actual loader we keep the last occurrence. We will just log here.

        # --- DQ-03: FK Integrity (CRITICAL) ---
        valid_tickers = set(companies["id"])
        child_tables = {
            "profitandloss": profitandloss,
            "balancesheet": balancesheet,
            "cashflow": cashflow,
            "analysis": analysis,
            "documents": documents,
            "prosandcons": prosandcons,
        }
        for table_name, df in child_tables.items():
            if df.empty:
                continue
            orphan_mask = ~df["company_id"].isin(valid_tickers)
            orphans = df[orphan_mask]
            for _, row in orphans.iterrows():
                year_val = row.get("year", row.get("Year", None))
                self.log_failure(
                    row["company_id"],
                    year_val,
                    "company_id",
                    f"Orphan company_id in {table_name}",
                    "CRITICAL",
                )

            # Reject rows (keep only valid foreign keys)
            if table_name == "profitandloss":
                profitandloss = df[~orphan_mask]
            elif table_name == "balancesheet":
                balancesheet = df[~orphan_mask]
            elif table_name == "cashflow":
                cashflow = df[~orphan_mask]
            elif table_name == "analysis":
                analysis = df[~orphan_mask]
            elif table_name == "documents":
                documents = df[~orphan_mask]
            elif table_name == "prosandcons":
                prosandcons = df[~orphan_mask]

        # --- DQ-04: Balance Sheet Balance (WARNING) ---
        for _, row in balancesheet.iterrows():
            ta = row["total_assets"]
            tl = row["total_liabilities"]
            if pd.isna(ta) or pd.isna(tl):
                self.log_failure(
                    row["company_id"],
                    row["year"],
                    "total_assets/total_liabilities",
                    "Missing total assets or liabilities",
                    "WARNING",
                )
            elif ta == 0:
                self.log_failure(
                    row["company_id"],
                    row["year"],
                    "total_assets/total_liabilities",
                    "Total assets is zero",
                    "WARNING",
                )
            elif abs(ta - tl) / ta >= 0.01:
                self.log_failure(
                    row["company_id"],
                    row["year"],
                    "total_assets/total_liabilities",
                    f"Balance sheet imbalance (Assets: {ta}, Liabilities: {tl})",
                    "WARNING",
                )

        # --- DQ-05: OPM Cross-Check (WARNING) ---
        for _, row in profitandloss.iterrows():
            opm = row["opm_percentage"]
            op_profit = row["operating_profit"]
            sales = row["sales"]
            if pd.isna(opm) or pd.isna(op_profit) or pd.isna(sales):
                continue
            if sales == 0:
                if op_profit != 0 and abs(opm) >= 1.0:
                    self.log_failure(
                        row["company_id"],
                        row["year"],
                        "opm_percentage",
                        "OPM percentage mismatch: sales is zero but operating profit is non-zero",
                        "WARNING",
                    )
            else:
                computed_opm = (op_profit / sales) * 100
                if abs(opm - computed_opm) >= 1.0:
                    self.log_failure(
                        row["company_id"],
                        row["year"],
                        "opm_percentage",
                        f"OPM percentage mismatch (source: {opm}%, computed: {computed_opm:.2f}%)",
                        "WARNING",
                    )

        # --- DQ-06: Positive Sales (WARNING) ---
        for _, row in profitandloss.iterrows():
            ticker = row["company_id"]
            if ticker not in bank_tickers:
                if not pd.isna(row["sales"]) and row["sales"] <= 0:
                    self.log_failure(
                        ticker,
                        row["year"],
                        "sales",
                        f"Non-positive sales for non-bank company ({row['sales']})",
                        "WARNING",
                    )

        # --- DQ-09: Net Cash Check (WARNING) ---
        for _, row in cashflow.iterrows():
            cfo = row["operating_activity"]
            cfi = row["investing_activity"]
            cff = row["financing_activity"]
            ncf = row["net_cash_flow"]
            if pd.isna(cfo) or pd.isna(cfi) or pd.isna(cff) or pd.isna(ncf):
                continue
            computed_ncf = cfo + cfi + cff
            if abs(ncf - computed_ncf) > 10:
                self.log_failure(
                    row["company_id"],
                    row["year"],
                    "net_cash_flow",
                    f"Net cash flow mismatch (source: {ncf}, computed: {computed_ncf})",
                    "WARNING",
                )

        # --- DQ-10: Non-Negative Fixed Assets (WARNING) ---
        for _, row in balancesheet.iterrows():
            fa = row["fixed_assets"]
            if not pd.isna(fa) and fa < 0:
                self.log_failure(
                    row["company_id"],
                    row["year"],
                    "fixed_assets",
                    f"Negative fixed assets ({fa})",
                    "WARNING",
                )

        # --- DQ-11: Tax Rate Range (WARNING) ---
        for _, row in profitandloss.iterrows():
            tax = row["tax_percentage"]
            if not pd.isna(tax) and (tax < 0 or tax > 60):
                self.log_failure(
                    row["company_id"],
                    row["year"],
                    "tax_percentage",
                    f"Tax percentage out of range ({tax}%)",
                    "WARNING",
                )

        # --- DQ-12: Dividend Payout Cap (WARNING) ---
        for _, row in profitandloss.iterrows():
            div = row["dividend_payout"]
            if not pd.isna(div) and div > 200:
                self.log_failure(
                    row["company_id"],
                    row["year"],
                    "dividend_payout",
                    f"Dividend payout exceeds 200% ({div}%)",
                    "WARNING",
                )

        # --- DQ-13: URL Validity (WARNING) ---
        url_status = self.run_url_checks(documents)
        for _, row in documents.iterrows():
            url = row["Annual_Report"]
            if pd.isna(url):
                continue
            is_valid, msg = url_status.get(url, (False, "Not checked"))
            if not is_valid:
                self.log_failure(
                    row["company_id"],
                    int(row["Year"]),
                    "Annual_Report",
                    f"Invalid annual report URL: {url} ({msg})",
                    "WARNING",
                )

        # --- DQ-14: EPS Sign Consistency (WARNING) ---
        for _, row in profitandloss.iterrows():
            eps = row["eps"]
            np = row["net_profit"]
            if pd.isna(eps) or pd.isna(np):
                continue
            if np > 0 and eps <= 0:
                self.log_failure(
                    row["company_id"],
                    row["year"],
                    "eps",
                    f"EPS is non-positive ({eps}) while net profit is positive ({np})",
                    "WARNING",
                )

        # --- DQ-15: BSE/ASE Balance (ext.) (INFO) ---
        for _, row in balancesheet.iterrows():
            ta = row["total_assets"]
            tl = row["total_liabilities"]
            if pd.isna(ta) or pd.isna(tl):
                continue
            if ta != tl:
                self.log_failure(
                    row["company_id"],
                    row["year"],
                    "total_assets/total_liabilities",
                    f"Strict balance sheet mismatch (Assets: {ta}, Liabilities: {tl})",
                    "INFO",
                )

        # --- DQ-16: Coverage Check (WARNING) ---
        all_companies = companies["id"].unique()
        for ticker in all_companies:
            pl_yrs = len(
                profitandloss[profitandloss["company_id"] == ticker]["year"].unique()
            )
            bs_yrs = len(
                balancesheet[balancesheet["company_id"] == ticker]["year"].unique()
            )
            cf_yrs = len(cashflow[cashflow["company_id"] == ticker]["year"].unique())
            min_yrs = min(pl_yrs, bs_yrs, cf_yrs)
            if min_yrs < 5:
                self.log_failure(
                    ticker,
                    None,
                    "coverage",
                    f"Company has low coverage: P&L={pl_yrs} yrs, BS={bs_yrs} yrs, CF={cf_yrs} yrs",
                    "WARNING",
                )

        # Convert failures list to DataFrame
        failures_df = pd.DataFrame(self.failures)
        if failures_df.empty:
            failures_df = pd.DataFrame(
                columns=["company_id", "year", "field", "issue", "severity"]
            )

        return failures_df


if __name__ == "__main__":
    import os
    os.environ["FAST_VALIDATION"] = "True"
    logging.basicConfig(level=logging.INFO)
    validator = DataValidator()
    try:
        failures = validator.validate()
        os.makedirs("output", exist_ok=True)
        failures.to_csv("output/validation_failures.csv", index=False)
        print(
            f"Validation completed. Logged {len(failures)} failures to output/validation_failures.csv."
        )
    except Exception as e:
        print(f"Validation halted with error: {e}")
