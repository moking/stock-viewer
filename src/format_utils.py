"""Number formatting helpers."""

from __future__ import annotations

import pandas as pd


def fmt_num(value, decimals: int = 2, prefix: str = "", suffix: str = "") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if decimals == 0:
        return f"{prefix}{int(round(num)):,}{suffix}"
    return f"{prefix}{num:,.{decimals}f}{suffix}"


def fmt_pct(value, decimals: int = 2) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    num = float(value)
    sign = "+" if num >= 0 else "-"
    return f"{sign}{fmt_num(abs(num), decimals=decimals)}%"


def _column_format(col: str) -> str | None:
    low = col.lower()
    if any(key in low for key in ("volume", "shares", "成交量", "持股", "股数", "股數")):
        return "{:,.0f}"
    if "%" in col or "比例" in col or "倍" in col or "pct" in low or "holding" in low:
        return "{:,.2f}"
    if any(
        key in low
        for key in (
            "price",
            "close",
            "value",
            "pnl",
            "盈亏",
            "盈虧",
            "价",
            "價",
            "额",
            "額",
        )
    ):
        return "{:,.2f}"
    return None


def display_dataframe(df: pd.DataFrame):
    from src.i18n import prepare_display_dataframe

    display_df = prepare_display_dataframe(df)
    return style_numeric_dataframe(display_df)


def style_numeric_dataframe(df: pd.DataFrame):
    if df.empty:
        return df

    fmt = {col: spec for col in df.columns if (spec := _column_format(col))}
    if not fmt:
        return df
    return df.style.format(fmt, na_rep="—")
