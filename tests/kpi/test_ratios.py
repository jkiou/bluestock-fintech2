"""
tests/kpi/test_ratios.py
Unit tests for the KPI Ratio Engine (src/analytics/ratios.py).
Covers: safe_div, cagr, compute_profitability, compute_leverage, compute_cashflow_ratios.
"""
import sys
import os
import math
import pytest
import pandas as pd

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from src.analytics.ratios import (
    safe_div,
    cagr,
    compute_profitability,
    compute_leverage,
    compute_cashflow_ratios,
)


# ---------------------------------------------------------------------------
# safe_div
# ---------------------------------------------------------------------------
class TestSafeDiv:
    def test_normal_division(self):
        assert safe_div(10, 2) == 5.0

    def test_zero_denominator_returns_none(self):
        assert safe_div(10, 0) is None

    def test_zero_denominator_custom_default(self):
        assert safe_div(10, 0, default=0.0) == 0.0

    def test_nan_denominator(self):
        assert safe_div(10, float("nan")) is None

    def test_nan_numerator(self):
        assert safe_div(float("nan"), 5) is None

    def test_negative_values(self):
        assert safe_div(-20, 4) == -5.0

    def test_small_positive(self):
        assert abs(safe_div(1, 3) - 0.3333) < 1e-4

    def test_both_zero(self):
        assert safe_div(0, 0) is None


# ---------------------------------------------------------------------------
# cagr
# ---------------------------------------------------------------------------
class TestCagr:
    def test_positive_cagr(self):
        # 100 → 161.05 over 5 years ≈ 10%
        result = cagr(100, 161.05, 5)
        assert result is not None
        assert abs(result - 0.10) < 0.002

    def test_zero_years(self):
        assert cagr(100, 200, 0) is None

    def test_negative_start(self):
        assert cagr(-100, 200, 3) is None

    def test_zero_start(self):
        assert cagr(0, 100, 3) is None

    def test_flat_cagr(self):
        result = cagr(100, 100, 5)
        assert abs(result) < 1e-6

    def test_nan_input(self):
        assert cagr(None, 200, 5) is None


# ---------------------------------------------------------------------------
# compute_profitability
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_pl():
    return pd.DataFrame([
        {"company_id": 1, "year": 2022, "sales": 10000.0, "net_profit": 1500.0,
         "operating_profit": 2000.0, "eps": 12.5, "dividend_payout": 30.0,
         "interest": 200.0},
        {"company_id": 1, "year": 2023, "sales": 12000.0, "net_profit": 1800.0,
         "operating_profit": 2600.0, "eps": 15.0, "dividend_payout": 28.0,
         "interest": 180.0},
    ])

@pytest.fixture
def sample_bs():
    return pd.DataFrame([
        {"company_id": 1, "year": 2022, "equity_capital": 500.0, "reserves": 3000.0,
         "total_assets": 8000.0, "total_liabilities": 4500.0, "borrowings": 1000.0},
        {"company_id": 1, "year": 2023, "equity_capital": 500.0, "reserves": 3500.0,
         "total_assets": 9500.0, "total_liabilities": 5500.0, "borrowings": 900.0},
    ])

class TestComputeProfitability:
    def test_returns_dataframe(self, sample_pl, sample_bs):
        result = compute_profitability(sample_pl, sample_bs)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_net_profit_margin(self, sample_pl, sample_bs):
        result = compute_profitability(sample_pl, sample_bs)
        row = result[result["year"] == 2022].iloc[0]
        expected = 1500 / 10000 * 100
        assert abs(row["net_profit_margin_pct"] - expected) < 0.01

    def test_roe(self, sample_pl, sample_bs):
        result = compute_profitability(sample_pl, sample_bs)
        row = result[result["year"] == 2022].iloc[0]
        equity = 500 + 3000
        expected_roe = 1500 / equity * 100
        assert abs(row["return_on_equity_pct"] - expected_roe) < 0.01

    def test_debt_to_equity(self, sample_pl, sample_bs):
        result = compute_profitability(sample_pl, sample_bs)
        row = result[result["year"] == 2022].iloc[0]
        equity = 500 + 3000
        expected = 1000 / equity
        assert abs(row["debt_to_equity"] - expected) < 0.001

    def test_opm(self, sample_pl, sample_bs):
        result = compute_profitability(sample_pl, sample_bs)
        row = result[result["year"] == 2022].iloc[0]
        expected = 2000 / 10000 * 100
        assert abs(row["operating_profit_margin_pct"] - expected) < 0.01


# ---------------------------------------------------------------------------
# compute_leverage
# ---------------------------------------------------------------------------
class TestComputeLeverage:
    def test_interest_coverage(self, sample_pl, sample_bs):
        result = compute_leverage(sample_pl, sample_bs)
        row = result[result["year"] == 2022].iloc[0]
        expected = 2000 / 200  # op_profit / interest
        assert abs(row["interest_coverage"] - expected) < 0.01

    def test_zero_interest(self, sample_pl, sample_bs):
        pl = sample_pl.copy()
        pl.loc[pl["year"] == 2022, "interest"] = 0.0
        result = compute_leverage(pl, sample_bs)
        row = result[result["year"] == 2022].iloc[0]
        assert row["interest_coverage"] is None or pd.isna(row["interest_coverage"])


# ---------------------------------------------------------------------------
# compute_cashflow_ratios
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_cf():
    return pd.DataFrame([
        {"company_id": 1, "year": 2022,
         "operating_activity": 1800.0, "investing_activity": -600.0, "financing_activity": -400.0},
        {"company_id": 1, "year": 2023,
         "operating_activity": 2100.0, "investing_activity": -800.0, "financing_activity": -200.0},
    ])

class TestComputeCashflowRatios:
    def test_capex_absolute(self, sample_cf):
        result = compute_cashflow_ratios(sample_cf)
        row = result[result["year"] == 2022].iloc[0]
        assert row["capex_cr"] == 600.0

    def test_free_cash_flow(self, sample_cf):
        result = compute_cashflow_ratios(sample_cf)
        row = result[result["year"] == 2022].iloc[0]
        assert row["free_cash_flow_cr"] == 1800 - 600

    def test_nan_investing(self, sample_cf):
        cf = sample_cf.copy()
        cf.loc[cf["year"] == 2022, "investing_activity"] = float("nan")
        result = compute_cashflow_ratios(cf)
        row = result[result["year"] == 2022].iloc[0]
        assert row["capex_cr"] is None or pd.isna(row["capex_cr"])

    def test_cash_from_operations(self, sample_cf):
        result = compute_cashflow_ratios(sample_cf)
        row = result[result["year"] == 2023].iloc[0]
        assert row["cash_from_operations_cr"] == 2100.0
