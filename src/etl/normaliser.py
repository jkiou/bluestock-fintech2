import re
import datetime
import pandas as pd

# Map month names and abbreviations to two-digit strings
MONTH_MAP = {
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}


def normalize_ticker(ticker: any) -> str:
    """
    Normalise company_id to uppercase stripped NSE ticker.
    If missing, empty or null, returns 'MISSING'.
    """
    if pd.isna(ticker) or ticker is None:
        return "MISSING"

    ticker_str = str(ticker).strip().upper()
    if ticker_str in ("", "NAN", "NONE", "NULL"):
        return "MISSING"

    return ticker_str


def normalize_year(year: any) -> str:
    """
    Standardise year labels to 'YYYY-MM' format.
    Handles standard formats (Mar-23), variations (March-2023, Mar 23),
    integer years (2023), and FY prefix (FY23).
    Returns 'PARSE_ERROR' for invalid formats.
    """
    if pd.isna(year) or year is None:
        return "PARSE_ERROR"

    # Handle datetime/timestamp objects directly
    if isinstance(year, (datetime.datetime, datetime.date, pd.Timestamp)):
        return year.strftime("%Y-%m")

    year_str = str(year).strip()

    # Handle potential float representation in pandas (e.g. 2023.0)
    if year_str.endswith(".0"):
        year_str = year_str[:-2]

    if year_str in ("", "NAN", "NONE", "NULL"):
        return "PARSE_ERROR"

    # 1. Already Standardized YYYY-MM (e.g. 2023-03)
    if re.match(r"^\d{4}-\d{2}$", year_str):
        return year_str

    # 2. Integer year (e.g. 2023)
    if re.match(r"^\d{4}$", year_str):
        return f"{year_str}-03"

    # 3. Fiscal Year Prefix (e.g. FY23, FY 23, FY2023)
    fy_match = re.match(r"^FY\s*(\d{2}|\d{4})$", year_str, re.IGNORECASE)
    if fy_match:
        yr = fy_match.group(1)
        if len(yr) == 2:
            yr = "20" + yr
        return f"{yr}-03"

    # 4. Month-Year Combinations (e.g. Mar-23, March-2023, Dec-22)
    my_match = re.match(r"^([A-Za-z]+)[\s-]*(\d{2}|\d{4})$", year_str)
    if my_match:
        mon_name = my_match.group(1).lower()
        yr = my_match.group(2)
        if mon_name in MONTH_MAP:
            mon_num = MONTH_MAP[mon_name]
            if len(yr) == 2:
                # Standard cutoff: < 50 assume 20XX, otherwise 19XX
                yr_val = int(yr)
                if yr_val < 50:
                    yr = "20" + yr
                else:
                    yr = "19" + yr
            return f"{yr}-{mon_num}"

    return "PARSE_ERROR"
