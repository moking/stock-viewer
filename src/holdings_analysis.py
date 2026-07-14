"""Institutional ownership and large transaction analysis."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from src.stock_data import fetch_history, get_period_bounds, get_ticker, normalize_symbol


def _safe_df(attr) -> pd.DataFrame:
    try:
        if attr is None:
            return pd.DataFrame()
        if isinstance(attr, pd.DataFrame):
            return attr.copy()
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _parse_percent(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", "")
    match = re.search(r"([-+]?\d*\.?\d+)", text)
    if not match:
        return None
    return float(match.group(1))


def _normalize_major_holders(df: pd.DataFrame) -> dict[str, float | int | None]:
    result: dict[str, float | int | None] = {
        "insider_pct": None,
        "institution_pct": None,
        "mutual_fund_pct": None,
        "institution_float_pct": None,
        "institution_count": None,
        "retail_pct": None,
    }

    if df.empty:
        return result

    working = df.copy()
    if working.shape[1] >= 2:
        labels = working.iloc[:, 0].astype(str).str.strip()
        values = working.iloc[:, 1]
    else:
        labels = working.index.astype(str)
        values = working.iloc[:, 0]

    for label, value in zip(labels, values):
        lower = label.lower()
        if "insider" in lower and "held" in lower:
            result["insider_pct"] = _parse_percent(value)
        elif "institutions holders" in lower or "institution holders" in lower:
            parsed = _parse_percent(value)
            result["institution_count"] = int(parsed) if parsed is not None else None
        elif "float held by institutions" in lower:
            result["institution_float_pct"] = _parse_percent(value)
        elif "mutual fund" in lower:
            result["mutual_fund_pct"] = _parse_percent(value)
        elif "institution" in lower and "held" in lower:
            result["institution_pct"] = _parse_percent(value)

    known = [v for v in [result["insider_pct"], result["institution_pct"]] if v is not None]
    if known:
        total_known = sum(known)
        result["retail_pct"] = max(0.0, 100.0 - total_known) if total_known <= 100 else None

    return result


def _prepare_holders_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    rename_map = {}
    for col in out.columns:
        lower = str(col).lower()
        if lower in {"holder", "name"}:
            rename_map[col] = "holder"
        elif "pctheld" in lower or "% out" in lower or "percent" in lower:
            rename_map[col] = "pct_held"
        elif lower == "shares":
            rename_map[col] = "shares"
        elif "value" in lower:
            rename_map[col] = "market_value"
        elif "date" in lower:
            rename_map[col] = "date_reported"
        elif "change" in lower:
            rename_map[col] = "change_pct"

    out = out.rename(columns=rename_map)
    if "pct_held" in out.columns:
        def _format_pct(x):
            if pd.isna(x):
                return None
            parsed = _parse_percent(x)
            if parsed is not None:
                return round(parsed, 4)
            try:
                val = float(x)
                return round(val * 100, 4) if val <= 1 else round(val, 4)
            except (TypeError, ValueError):
                return x

        out["pct_held"] = out["pct_held"].apply(_format_pct)
    return out


def _prepare_insider_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    rename_map = {}
    for col in out.columns:
        lower = str(col).lower()
        if lower == "insider":
            rename_map[col] = "insider"
        elif lower == "position":
            rename_map[col] = "position"
        elif lower == "shares":
            rename_map[col] = "shares"
        elif "latest trans date" in lower or "transaction date" in lower:
            rename_map[col] = "transaction_date"
        elif lower == "owner":
            rename_map[col] = "owner"
        elif lower == "relationship":
            rename_map[col] = "relationship"
        elif lower == "type":
            rename_map[col] = "transaction_type"
        elif lower == "text":
            rename_map[col] = "transaction_text"
        elif "filing date" in lower:
            rename_map[col] = "filing_date"
        elif lower == "value":
            rename_map[col] = "transaction_value"

    return out.rename(columns=rename_map)


def _filter_dataframe_by_period(
    df: pd.DataFrame,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
    date_columns: list[str],
) -> pd.DataFrame:
    if df.empty or start is None or end is None:
        return pd.DataFrame()

    for col in date_columns:
        if col not in df.columns:
            continue
        work = df.copy()
        work["_filter_date"] = pd.to_datetime(work[col], errors="coerce")
        if hasattr(work["_filter_date"].dt, "tz_localize"):
            work["_filter_date"] = work["_filter_date"].dt.tz_localize(None)
        filtered = work[(work["_filter_date"] >= start) & (work["_filter_date"] <= end)].drop(
            columns=["_filter_date"]
        )
        if not filtered.empty:
            return filtered

    return pd.DataFrame()


def _detect_large_volume_days(
    history: pd.DataFrame, threshold: float = 2.0, limit: int = 50
) -> pd.DataFrame:
    if history.empty or "Volume" not in history.columns:
        return pd.DataFrame()

    work = history.copy()
    avg_volume = work["Volume"].mean()
    if avg_volume <= 0:
        return pd.DataFrame()

    work["avg_volume_multiple"] = work["Volume"] / avg_volume
    work["volume"] = work["Volume"]
    large = work[work["avg_volume_multiple"] >= threshold].sort_values("Date", ascending=False).head(limit)

    cols = ["Date", "Close", "volume", "avg_volume_multiple"]
    if "High" in large.columns and "Low" in large.columns:
        large = large.copy()
        large["swing_pct"] = ((large["High"] - large["Low"]) / large["Low"] * 100).round(2)
        cols.append("swing_pct")

    display = large[cols].copy()
    display = display.rename(columns={"Date": "date", "Close": "close"})
    display["date"] = pd.to_datetime(display["date"]).dt.strftime("%Y-%m-%d")
    display["volume"] = display["volume"].astype("int64")
    display["avg_volume_multiple"] = display["avg_volume_multiple"].round(2)
    return display


def fetch_ownership_analysis(symbol: str, period_label: str = "3个月") -> dict[str, Any]:
    symbol = normalize_symbol(symbol)
    ticker = get_ticker(symbol)
    history = fetch_history(symbol, period_label)
    period_start, period_end = get_period_bounds(history)

    major_df = _safe_df(getattr(ticker, "major_holders", None))
    institutional_df = _safe_df(getattr(ticker, "institutional_holders", None))
    mutualfund_df = _safe_df(getattr(ticker, "mutualfund_holders", None))
    insider_roster_df = _safe_df(getattr(ticker, "insider_roster_holders", None))
    insider_tx_df = _safe_df(getattr(ticker, "insider_transactions", None))

    insider_tx_in_period = _filter_dataframe_by_period(
        insider_tx_df,
        period_start,
        period_end,
        ["Transaction Date", "Start Date", "Filing Date"],
    )
    institutional_in_period = _filter_dataframe_by_period(
        institutional_df,
        period_start,
        period_end,
        ["Date Reported"],
    )
    mutualfund_in_period = _filter_dataframe_by_period(
        mutualfund_df,
        period_start,
        period_end,
        ["Date Reported"],
    )

    breakdown = _normalize_major_holders(major_df)
    institution_count = breakdown.get("institution_count")
    if institution_count is None and not institutional_in_period.empty:
        institution_count = len(institutional_in_period)
    elif institution_count is None and not institutional_df.empty:
        institution_count = len(institutional_df)

    institutional_table = _prepare_holders_table(institutional_in_period)
    mutualfund_table = _prepare_holders_table(mutualfund_in_period)
    insider_roster_table = _prepare_insider_table(insider_roster_df)
    insider_tx_table = _prepare_insider_table(insider_tx_in_period)

    if not insider_tx_table.empty:
        date_col = next((c for c in insider_tx_table.columns if "date" in c.lower()), None)
        if date_col:
            insider_tx_table = insider_tx_table.sort_values(date_col, ascending=False)

    large_volume_days = _detect_large_volume_days(history)

    period_range_text = period_label
    if period_start is not None and period_end is not None:
        period_range_text = (
            f"{period_start.strftime('%Y-%m-%d')} ~ {period_end.strftime('%Y-%m-%d')} ({period_label})"
        )

    return {
        "symbol": symbol,
        "period_label": period_label,
        "period_range_text": period_range_text,
        "period_start": period_start,
        "period_end": period_end,
        "breakdown": breakdown,
        "institution_count": institution_count,
        "mutualfund_count": len(mutualfund_in_period) if not mutualfund_in_period.empty else 0,
        "insider_count": len(insider_roster_df) if not insider_roster_df.empty else 0,
        "institutional_holders": institutional_table,
        "mutualfund_holders": mutualfund_table,
        "insider_roster": insider_roster_table,
        "insider_transactions": insider_tx_table,
        "large_volume_days": large_volume_days,
        "has_data": any(
            [
                breakdown.get("institution_pct") is not None,
                not institutional_table.empty,
                not insider_tx_table.empty,
                not large_volume_days.empty,
                not history.empty,
            ]
        ),
    }
