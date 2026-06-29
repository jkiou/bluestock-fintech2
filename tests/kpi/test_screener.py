"""
tests/kpi/test_screener.py
Unit tests for the Stock Screener (src/analytics/screener.py).
"""
import sys
import os
import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from src.analytics.screener import apply_filters, _OPS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_df():
    return pd.DataFrame([
        {"company_id": 1, "ticker": "AAA", "sector": "IT",
         "return_on_equity_pct": 20.0, "debt_to_equity": 0.5,
         "free_cash_flow_cr": 1000.0, "pe_ratio": 18.0,
         "pb_ratio": 2.5, "dividend_yield_pct": 2.0,
         "market_cap_cr": 50000.0},
        {"company_id": 2, "ticker": "BBB", "sector": "Banking",
         "return_on_equity_pct": 12.0, "debt_to_equity": 1.5,
         "free_cash_flow_cr": -200.0, "pe_ratio": 25.0,
         "pb_ratio": 4.0, "dividend_yield_pct": 0.5,
         "market_cap_cr": 80000.0},
        {"company_id": 3, "ticker": "CCC", "sector": "IT",
         "return_on_equity_pct": 30.0, "debt_to_equity": 0.0,
         "free_cash_flow_cr": 5000.0, "pe_ratio": 35.0,
         "pb_ratio": 6.0, "dividend_yield_pct": 1.2,
         "market_cap_cr": 120000.0},
    ])


# ---------------------------------------------------------------------------
# apply_filters tests
# ---------------------------------------------------------------------------
class TestApplyFilters:
    def test_gt_filter(self, sample_df):
        result = apply_filters(sample_df, {"return_on_equity_pct": {"operator": ">", "value": 15.0}})
        assert len(result) == 2
        assert all(result["return_on_equity_pct"] > 15.0)

    def test_lt_filter(self, sample_df):
        result = apply_filters(sample_df, {"debt_to_equity": {"operator": "<", "value": 1.0}})
        assert len(result) == 2

    def test_le_filter(self, sample_df):
        result = apply_filters(sample_df, {"debt_to_equity": {"operator": "<=", "value": 1.5}})
        assert len(result) == 3

    def test_eq_filter(self, sample_df):
        result = apply_filters(sample_df, {"debt_to_equity": {"operator": "==", "value": 0.0}})
        assert len(result) == 1
        assert result.iloc[0]["ticker"] == "CCC"

    def test_positive_fcf_filter(self, sample_df):
        result = apply_filters(sample_df, {"free_cash_flow_cr": {"operator": ">", "value": 0.0}})
        assert len(result) == 2

    def test_multiple_filters(self, sample_df):
        filters = {
            "return_on_equity_pct": {"operator": ">",  "value": 15.0},
            "debt_to_equity":       {"operator": "<",  "value": 1.0},
            "free_cash_flow_cr":    {"operator": ">",  "value": 0.0},
        }
        result = apply_filters(sample_df, filters)
        assert len(result) == 2
        assert set(result["ticker"]) == {"AAA", "CCC"}

    def test_no_match_returns_empty(self, sample_df):
        result = apply_filters(sample_df, {"return_on_equity_pct": {"operator": ">", "value": 100.0}})
        assert result.empty

    def test_unknown_column_skipped(self, sample_df):
        """Unknown column should be silently skipped (no crash)."""
        result = apply_filters(sample_df, {"non_existent_col": {"operator": ">", "value": 1.0}})
        assert len(result) == len(sample_df)  # no rows dropped

    def test_unknown_operator_skipped(self, sample_df):
        """Unknown operator should be silently skipped."""
        result = apply_filters(sample_df, {"return_on_equity_pct": {"operator": "between", "value": 10.0}})
        assert len(result) == len(sample_df)

    def test_empty_filters(self, sample_df):
        result = apply_filters(sample_df, {})
        assert len(result) == len(sample_df)


# ---------------------------------------------------------------------------
# Operator map sanity
# ---------------------------------------------------------------------------
class TestOpsMap:
    def test_all_operators_callable(self):
        for sym, fn in _OPS.items():
            assert callable(fn), f"Operator {sym!r} is not callable"

    def test_gt_correct(self):
        assert _OPS[">"](5, 3)
        assert not _OPS[">"](3, 5)

    def test_lt_correct(self):
        assert _OPS["<"](2, 4)
        assert not _OPS["<"](4, 2)

    def test_eq_correct(self):
        assert _OPS["=="](5, 5)
        assert not _OPS["=="](5, 6)
