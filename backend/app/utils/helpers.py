"""Formatting and utility helpers."""
from datetime import date


def format_date(d: date = None) -> str:
    """Format a date as 'March 2026'."""
    if d is None:
        d = date.today()
    return d.strftime("%B %Y")


def format_number(n: float) -> str:
    """Format a number with commas: 1234 -> '1,234'."""
    if n == int(n):
        return f"{int(n):,}"
    return f"{n:,.1f}"
