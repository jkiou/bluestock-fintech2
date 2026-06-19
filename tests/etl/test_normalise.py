import datetime
import pytest
import pandas as pd
from src.etl.normaliser import normalize_ticker, normalize_year

# 20+ test cases for normalize_ticker
TICKER_TEST_CASES = [
    ("TCS", "TCS"),
    ("tcs", "TCS"),
    ("  TCS  ", "TCS"),
    ("BAJAJ-AUTO", "BAJAJ-AUTO"),
    ("bajaj-auto", "BAJAJ-AUTO"),
    ("M&M", "M&M"),
    ("m&m", "M&M"),
    ("HDFCBANK", "HDFCBANK"),
    ("hdfcbank", "HDFCBANK"),
    ("  hdfcbank  ", "HDFCBANK"),
    ("RELIANCE", "RELIANCE"),
    ("reliance", "RELIANCE"),
    ("INFY", "INFY"),
    (None, "MISSING"),
    ("", "MISSING"),
    ("   ", "MISSING"),
    ("nan", "MISSING"),
    ("NaN", "MISSING"),
    ("None", "MISSING"),
    ("NONE", "MISSING"),
    ("NULL", "MISSING"),
    (123, "123"),
    ("inf", "INF")
]

# 20+ test cases for normalize_year
YEAR_TEST_CASES = [
    ("Mar-23", "2023-03"),
    ("Mar 23", "2023-03"),
    ("March-2023", "2023-03"),
    ("march 2023", "2023-03"),
    ("2023", "2023-03"),
    (2023, "2023-03"),
    ("2023.0", "2023-03"),
    (2023.0, "2023-03"),
    ("FY23", "2023-03"),
    ("fy23", "2023-03"),
    ("FY 23", "2023-03"),
    ("FY2023", "2023-03"),
    ("fy 2023", "2023-03"),
    ("Dec-22", "2022-12"),
    ("dec 22", "2022-12"),
    ("December-2022", "2022-12"),
    ("Jun-23", "2023-06"),
    ("jun 23", "2023-06"),
    ("June-2023", "2023-06"),
    ("2023-03", "2023-03"),
    ("September-2021", "2021-09"),
    ("Sep 21", "2021-09"),
    ("Dec 99", "1999-12"),
    ("Jan 05", "2005-01"),
    (datetime.datetime(2023, 3, 31), "2023-03"),
    (datetime.date(2022, 12, 31), "2022-12"),
    (pd.Timestamp("2023-06-30"), "2023-06"),
    ("garbage", "PARSE_ERROR"),
    ("", "PARSE_ERROR"),
    ("   ", "PARSE_ERROR"),
    ("nan", "PARSE_ERROR"),
    (None, "PARSE_ERROR"),
    ("invalid-month-12", "PARSE_ERROR"),
    ("FY", "PARSE_ERROR")
]

@pytest.mark.parametrize("ticker_input, expected", TICKER_TEST_CASES)
def test_normalize_ticker(ticker_input, expected):
    assert normalize_ticker(ticker_input) == expected

@pytest.mark.parametrize("year_input, expected", YEAR_TEST_CASES)
def test_normalize_year(year_input, expected):
    assert normalize_year(year_input) == expected
