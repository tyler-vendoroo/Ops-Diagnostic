"""Shared date parsing utilities."""
from __future__ import annotations

from typing import Any

import pandas as pd


def auto_parse_dates(series: pd.Series) -> pd.Series:
    """Try multiple formats, pick the one that works, fall back to inference."""
    if series.dtype in ("datetime64[ns]", "<M8[ns]"):
        return series

    formats = [
        "%b %d, %Y, %I:%M %p",   # "Mar 25, 2026, 7:50 PM"
        "%m-%d-%Y %I:%M %p",     # "03-16-2026 6:46 PM"
        "%m/%d/%Y %I:%M %p",     # "03/16/2026 6:46 PM"
        "%Y-%m-%d %H:%M:%S",     # "2026-03-16 18:46:00"
        "%Y-%m-%dT%H:%M:%S",     # "2026-03-16T18:46:00"
        "%m-%d-%Y",              # "03-18-2026"
        "%m/%d/%Y",              # "03/18/2026"
        "%Y-%m-%d",              # "2026-03-16"
        "%d/%m/%Y",              # "16/03/2026"
        "%b %d, %Y",             # "Mar 16, 2026"
        "%B %d, %Y",             # "March 16, 2026"
        "%m/%d/%y",              # "03/16/26"
    ]

    sample = series.dropna().head(20)
    if len(sample) == 0:
        return pd.Series(pd.NaT, index=series.index)

    for fmt in formats:
        try:
            parsed = pd.to_datetime(sample, format=fmt, errors="coerce")
            if parsed.notna().sum() / len(sample) >= 0.8:
                return pd.to_datetime(series, format=fmt, errors="coerce")
        except Exception:
            continue

    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except TypeError:
        # Older pandas versions do not support format='mixed'.
        return pd.to_datetime(series, errors="coerce")


def auto_parse_datetime_value(value: Any):
    """Parse a single datetime-like value using shared auto parsing logic."""
    if value is None or pd.isna(value):
        return None

    parsed = auto_parse_dates(pd.Series([value])).iloc[0]
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()
