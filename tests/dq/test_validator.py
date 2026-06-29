import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.etl.validator import DataValidator, ValidationError


@pytest.fixture
def clean_dfs():
    """Generates clean, minimally valid core DataFrames that should pass basic validation."""
    companies = pd.DataFrame(
        {
            "id": ["TCS", "INFY"],
            "company_name": ["Tata Consultancy Services Ltd", "Infosys Ltd"],
            "face_value": [1, 1],
            "book_value": [150.0, 100.0],
        }
    )

    profitandloss = pd.DataFrame(
        {
            "id": [1, 2],
            "company_id": ["TCS", "INFY"],
            "year": ["2023-03", "2023-03"],
            "sales": [200000.0, 150000.0],
            "expenses": [150000.0, 110000.0],
            "operating_profit": [50000.0, 40000.0],
            "opm_percentage": [25.0, 26.67],
            "other_income": [3000.0, 2000.0],
            "interest": [500.0, 400.0],
            "depreciation": [4000.0, 3000.0],
            "profit_before_tax": [48500.0, 38600.0],
            "tax_percentage": [25.0, 25.0],
            "net_profit": [36375.0, 28950.0],
            "eps": [95.0, 70.0],
            "dividend_payout": [45.0, 40.0],
        }
    )

    balancesheet = pd.DataFrame(
        {
            "id": [1, 2],
            "company_id": ["TCS", "INFY"],
            "year": ["2023-03", "2023-03"],
            "equity_capital": [366.0, 207.0],
            "reserves": [90000.0, 75000.0],
            "borrowings": [8000.0, 6000.0],
            "other_liabilities": [25000.0, 20000.0],
            "total_liabilities": [123366.0, 101207.0],
            "fixed_assets": [20000.0, 18000.0],
            "cwip": [1000.0, 800.0],
            "investments": [50000.0, 40000.0],
            "other_asset": [52366.0, 42407.0],
            "total_assets": [123366.0, 101207.0],
        }
    )

    cashflow = pd.DataFrame(
        {
            "id": [1, 2],
            "company_id": ["TCS", "INFY"],
            "year": ["2023-03", "2023-03"],
            "operating_activity": [45000.0, 35000.0],
            "investing_activity": [-12000.0, -10000.0],
            "financing_activity": [-33000.0, -25000.0],
            "net_cash_flow": [0.0, 0.0],
        }
    )

    analysis = pd.DataFrame(
        {
            "id": [1, 2],
            "company_id": ["TCS", "INFY"],
            "compounded_sales_growth": ["10 Years: 15%", "10 Years: 12%"],
            "compounded_profit_growth": ["10 Years: 18%", "10 Years: 14%"],
            "stock_price_cagr": ["10 Years: 20%", "10 Years: 18%"],
            "roe": ["10 Years: 35%", "10 Years: 28%"],
        }
    )

    documents = pd.DataFrame(
        {
            "id": [1, 2],
            "company_id": ["TCS", "INFY"],
            "Year": [2023, 2023],
            "Annual_Report": [
                "https://bseindia.com/tcs23.pdf",
                "https://bseindia.com/infy23.pdf",
            ],
        }
    )

    prosandcons = pd.DataFrame(
        {
            "id": [1, 2],
            "company_id": ["TCS", "INFY"],
            "pros": ["Good growth", "Consistent profit"],
            "cons": ["High valuation", "Slowing sector"],
        }
    )

    return {
        "companies": companies,
        "profitandloss": profitandloss,
        "balancesheet": balancesheet,
        "cashflow": cashflow,
        "analysis": analysis,
        "documents": documents,
        "prosandcons": prosandcons,
    }


@pytest.fixture
def sectors_df():
    return pd.DataFrame(
        {
            "company_id": ["TCS", "INFY"],
            "broad_sector": ["Information Technology", "Information Technology"],
            "sub_sector": ["IT Services", "IT Services"],
        }
    )


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_clean_validation(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """Verify that clean, correct data passes validation with 0 failures except coverage/urls if mocked."""
    # Ensure requests.head returns 200 OK
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    # Check that criticals and basic warnings aren't present (low coverage is normal since we only pass 1 year)
    critical_failures = failures[failures["severity"] == "CRITICAL"]
    assert len(critical_failures) == 0


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
def test_dq01_duplicate_companies_ticker(
    mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-01: Company PK Uniqueness should raise ValidationError on duplicates."""
    clean_dfs["companies"] = pd.DataFrame(
        {"id": ["TCS", "TCS"], "company_name": ["TCS 1", "TCS 2"]}
    )
    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    with pytest.raises(ValidationError):
        validator.validate()


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq02_annual_pk_uniqueness(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-02: Annual PK Uniqueness logs duplicates."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Add duplicate P&L record
    pnl = clean_dfs["profitandloss"]
    duplicate_row = pnl.iloc[0:1].copy()
    clean_dfs["profitandloss"] = pd.concat([pnl, duplicate_row], ignore_index=True)

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    dup_failures = failures[
        (failures["severity"] == "CRITICAL") & (failures["field"] == "company_id, year")
    ]
    assert len(dup_failures) == 1
    assert "Duplicate annual record" in dup_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq03_fk_integrity(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-03: FK Integrity rejects orphan child rows."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Child table has orphan ticker ORPHAN
    pnl = clean_dfs["profitandloss"]
    orphan_row = pnl.iloc[0:1].copy()
    orphan_row["company_id"] = "ORPHAN"
    clean_dfs["profitandloss"] = pd.concat([pnl, orphan_row], ignore_index=True)

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    fk_failures = failures[
        (failures["severity"] == "CRITICAL")
        & (failures["issue"].str.contains("Orphan"))
    ]
    assert len(fk_failures) == 1
    assert fk_failures.iloc[0]["company_id"] == "ORPHAN"


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq04_bs_balance(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-04: BS Balance flags large differences (>1%)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Imbalance in balance sheet: total_assets = 100000, total_liabilities = 120000 (20% diff)
    clean_dfs["balancesheet"].loc[0, "total_liabilities"] = 120000.0
    clean_dfs["balancesheet"].loc[0, "total_assets"] = 100000.0

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    bs_failures = failures[
        (failures["severity"] == "WARNING")
        & (failures["field"] == "total_assets/total_liabilities")
    ]
    assert len(bs_failures) >= 1
    assert "Balance sheet imbalance" in bs_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq05_opm_cross_check(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-05: OPM check flags mismatch between OPM and operating_profit/sales."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Set OPM percentage to 50% while operating profit / sales is 25%
    clean_dfs["profitandloss"].loc[0, "opm_percentage"] = 50.0

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    opm_failures = failures[failures["field"] == "opm_percentage"]
    assert len(opm_failures) == 1


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq06_positive_sales(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-06: Sales <= 0 flags non-bank companies."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Set sales to 0 for TCS (which is in IT sector, hence non-bank)
    clean_dfs["profitandloss"].loc[0, "sales"] = 0.0

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    sales_failures = failures[failures["field"] == "sales"]
    assert len(sales_failures) == 1
    assert "Non-positive sales" in sales_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq07_year_format(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-07: Year format rejects invalid/PARSE_ERROR years."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Set year to PARSE_ERROR in profitandloss
    clean_dfs["profitandloss"].loc[0, "year"] = "PARSE_ERROR"

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    year_failures = failures[
        (failures["severity"] == "CRITICAL") & (failures["field"] == "year")
    ]
    assert len(year_failures) == 1
    assert "Invalid year format" in year_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq08_ticker_format(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-08: Ticker format rejects out-of-range tickers."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Set ticker to too short or MISSING in profitandloss
    clean_dfs["profitandloss"].loc[0, "company_id"] = "A"  # 1 char -> rejected

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    ticker_failures = failures[
        (failures["severity"] == "CRITICAL") & (failures["field"] == "company_id")
    ]
    assert len(ticker_failures) == 1
    assert "Invalid ticker format" in ticker_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq09_net_cash_check(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-09: Cash flow checks flag net cash flow mismatch >10 Cr."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # CFO=45000, CFI=-12000, CFF=-33000 -> Sum = 0. But net_cash_flow = 100
    clean_dfs["cashflow"].loc[0, "net_cash_flow"] = 100.0

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    cash_failures = failures[failures["field"] == "net_cash_flow"]
    assert len(cash_failures) == 1
    assert "Net cash flow mismatch" in cash_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq10_non_negative_fixed_assets(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-10: Fixed assets < 0 flags warning."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Set fixed_assets to -100 in balancesheet
    clean_dfs["balancesheet"].loc[0, "fixed_assets"] = -100.0

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    fa_failures = failures[failures["field"] == "fixed_assets"]
    assert len(fa_failures) == 1
    assert "Negative fixed assets" in fa_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq11_tax_rate_range(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-11: Tax rate out of range ([0, 60]) flags warning."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Set tax_percentage to 80% in profitandloss
    clean_dfs["profitandloss"].loc[0, "tax_percentage"] = 80.0

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    tax_failures = failures[failures["field"] == "tax_percentage"]
    assert len(tax_failures) == 1
    assert "Tax percentage out of range" in tax_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq12_dividend_payout_cap(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-12: Dividend payout > 200% flags warning."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Set dividend_payout to 250% in profitandloss
    clean_dfs["profitandloss"].loc[0, "dividend_payout"] = 250.0

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    div_failures = failures[failures["field"] == "dividend_payout"]
    assert len(div_failures) == 1
    assert "Dividend payout exceeds 200%" in div_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq13_url_validity(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-13: URL validation logs 404/invalid URLs."""

    # Ensure requests.head returns 404 for TCS URL and 200 for INFY URL
    def head_side_effect(url, *args, **kwargs):
        resp = MagicMock()
        if "tcs" in url:
            resp.status_code = 404
        else:
            resp.status_code = 200
        return resp

    mock_head.side_effect = head_side_effect

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    url_failures = failures[failures["field"] == "Annual_Report"]
    assert len(url_failures) == 1
    assert "tcs" in url_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq14_eps_sign_consistency(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-14: EPS <= 0 when net profit > 0 flags warning."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Net profit is 36375 (positive) but EPS is -1.0 (negative)
    clean_dfs["profitandloss"].loc[0, "eps"] = -1.0

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    eps_failures = failures[failures["field"] == "eps"]
    assert len(eps_failures) == 1
    assert "EPS is non-positive" in eps_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq15_bse_ase_balance(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-15: total_assets != total_liabilities logs INFO level when within 1% imbalance."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Set a tiny mismatch: total_assets = 123366, total_liabilities = 123367 (diff < 1%)
    clean_dfs["balancesheet"].loc[0, "total_liabilities"] = 123367.0

    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    info_failures = failures[failures["severity"] == "INFO"]
    assert len(info_failures) == 1
    assert "Strict balance sheet mismatch" in info_failures.iloc[0]["issue"]


@patch("src.etl.validator.load_all_core")
@patch("src.etl.validator.pd.read_excel")
@patch("src.etl.validator.requests.head")
def test_dq16_coverage_check(
    mock_head, mock_read_excel, mock_load_all, clean_dfs, sectors_df
):
    """DQ-16: Low coverage (<5 years) flags warning."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    # Our clean fixture only has 1 year of data for TCS and INFY, so both should trigger coverage check warnings
    mock_load_all.return_value = clean_dfs
    mock_read_excel.return_value = sectors_df

    validator = DataValidator()
    failures = validator.validate()

    cov_failures = failures[failures["field"] == "coverage"]
    assert len(cov_failures) == 2
    assert "low coverage" in cov_failures.iloc[0]["issue"]
