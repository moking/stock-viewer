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
    if col in {"成交量", "持股数", "Volume", "Shares", "区间交易日"}:
        return "{:,.0f}"
    if any(key in col for key in ("成交量", "持股数", "股数")):
        return "{:,.0f}"
    if any(key in col for key in ("价", "额", "值", "盈亏", "Close", "Open", "High", "Low")):
        return "{:,.2f}"
    if "%" in col or "倍" in col or "比例" in col:
        return "{:,.2f}"
    return None


def style_numeric_dataframe(df: pd.DataFrame):
    if df.empty:
        return df

    fmt = {col: spec for col in df.columns if (spec := _column_format(col))}
    if not fmt:
        return df
    return df.style.format(fmt, na_rep="—")
