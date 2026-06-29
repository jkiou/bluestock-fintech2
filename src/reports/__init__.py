"""
src/reports/__init__.py
Reports package — PDF generators for tearsheets, sectors, and portfolios.
"""
from .tearsheet import generate_tearsheet, generate_all_tearsheets
from .sector_report import generate_sector_report
from .portfolio_report import generate_portfolio_report

__all__ = [
    "generate_tearsheet",
    "generate_all_tearsheets",
    "generate_sector_report",
    "generate_portfolio_report",
]
