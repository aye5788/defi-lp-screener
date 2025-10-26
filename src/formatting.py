# formatting.py
# Functions to turn numeric data into human-readable display strings for the dashboard.
# This should ONLY do presentation formatting. No business logic or filtering.

import pandas as pd


def _format_usd(x):
    """
    Turn a raw number like 1234567.89 into something like "$1.23M".
    If x is missing or not a number, return "-".
    """
    try:
        val = float(x)
    except (TypeError, ValueError):
        return "-"

    if val >= 1_000_000_000:
        return f"${val/1_000_000_000:.2f}B"
    if val >= 1_000_000:
        return f"${val/1_000_000:.2f}M"
    if val >= 1_000:
        return f"${val/1_000:.2f}K"
    return f"${val:,.0f}"


def _format_pct(x):
    """
    Turn 12.3456 into '12.3%'.
    If x is missing, return '-'.
    """
    try:
        val = float(x)
    except (TypeError, ValueError):
        return "-"
    return f"{val:.1f}%"


def _format_tvl_trend(v):
    """
    Takes something like +12.34 and returns '▲ +12.3%'.
    Takes something like -5.2 and returns '▼ -5.2%'.
    For placeholder '—', just return '—'.
    """
    if v == "—":
        return "—"
    try:
        val = float(v)
    except (TypeError, ValueError):
        return "—"

    arrow = "▲" if val >= 0 else "▼"
    return f"{arrow} {val:.1f}%"


def format_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a NEW dataframe (safe to display) with pretty strings for:
    - TVL ($)
    - Fee APY (%)
    - Reward APY (%)
    - Total APY (%)
    - Net Yield After Gas (%)
    - TVL Trend (7d)
    We leave flags, IL risk, audit status, etc. as-is because those are already short labels.
    """
    df = df.copy()

    if "TVL ($)" in df.columns:
        df["TVL ($)"] = df["TVL ($)"].apply(_format_usd)

    if "Fee APY (%)" in df.columns:
        df["Fee APY (%)"] = df["Fee APY (%)"].apply(_format_pct)

    if "Reward APY (%)" in df.columns:
        df["Reward APY (%)"] = df["Reward APY (%)"].apply(_format_pct)

    if "Total APY (%)" in df.columns:
        df["Total APY (%)"] = df["Total APY (%)"].apply(_format_pct)

    if "Net Yield After Gas (%)" in df.columns:
        df["Net Yield After Gas (%)"] = df["Net Yield After Gas (%)"].apply(_format_pct)

    if "TVL Trend (7d)" in df.columns:
        df["TVL Trend (7d)"] = df["TVL Trend (7d)"].apply(_format_tvl_trend)

    return df
