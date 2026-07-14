"""Macro market snapshot: major indices and sector ETFs."""

from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf

from src.stock_data import PERIOD_OPTIONS, normalize_symbol

MARKET_INDEX_SYMBOLS = ("^GSPC", "^IXIC", "^DJI", "^RUT")

SECTOR_ETF_SYMBOLS = (
    "XLK",
    "XLF",
    "XLV",
    "XLE",
    "XLI",
    "XLP",
    "XLY",
    "XLB",
    "XLU",
    "XLRE",
    "XLC",
)

INDEX_NAME_KEYS = {
    "^GSPC": "macro_idx_sp500",
    "^IXIC": "macro_idx_nasdaq",
    "^DJI": "macro_idx_dow",
    "^RUT": "macro_idx_russell",
}

# Common ETFs that track each index (for display; not exhaustive).
INDEX_TRACKER_ETFS = {
    "^GSPC": "SPY, VOO, IVV",
    "^IXIC": "QQQ, ONEQ",
    "^DJI": "DIA",
    "^RUT": "IWM, VTWO",
}

SECTOR_NAME_KEYS = {
    "XLK": "macro_sector_tech",
    "XLF": "macro_sector_financial",
    "XLV": "macro_sector_health",
    "XLE": "macro_sector_energy",
    "XLI": "macro_sector_industrial",
    "XLP": "macro_sector_staples",
    "XLY": "macro_sector_discretionary",
    "XLB": "macro_sector_materials",
    "XLU": "macro_sector_utilities",
    "XLRE": "macro_sector_realestate",
    "XLC": "macro_sector_comm",
}


def _safe_history_frame(raw, symbol: str) -> pd.DataFrame:
    if raw is None or (isinstance(raw, pd.DataFrame) and raw.empty):
        return pd.DataFrame()

    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        if symbol in df.columns.get_level_values(0):
            df = df[symbol].copy()
        else:
            return pd.DataFrame()

    if "Close" not in df.columns:
        return pd.DataFrame()

    work = df.reset_index()
    if "Date" not in work.columns and "Datetime" in work.columns:
        work = work.rename(columns={"Datetime": "Date"})
    if "Date" in work.columns:
        work["Date"] = pd.to_datetime(work["Date"]).dt.tz_localize(None)
    return work


def _metrics_from_history(df: pd.DataFrame) -> dict[str, float | None]:
    if df.empty or "Close" not in df.columns:
        return {"price": None, "day_change_pct": None, "period_change_pct": None}

    close = df["Close"].dropna()
    if close.empty:
        return {"price": None, "day_change_pct": None, "period_change_pct": None}

    price = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) > 1 else None
    start = float(close.iloc[0])

    day_change_pct = ((price / prev) - 1) * 100 if prev else None
    period_change_pct = ((price / start) - 1) * 100 if start else None
    return {
        "price": price,
        "day_change_pct": day_change_pct,
        "period_change_pct": period_change_pct,
    }


def fetch_macro_snapshot(period_label: str) -> dict[str, Any]:
    period = PERIOD_OPTIONS.get(period_label, "3mo")
    index_symbols = [normalize_symbol(s) for s in MARKET_INDEX_SYMBOLS]
    sector_symbols = [normalize_symbol(s) for s in SECTOR_ETF_SYMBOLS]
    all_symbols = index_symbols + sector_symbols

    try:
        history = yf.download(
            all_symbols,
            period=period,
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
    except Exception:
        history = None

    index_rows: list[dict[str, Any]] = []
    sector_rows: list[dict[str, Any]] = []
    index_histories: dict[str, pd.DataFrame] = {}

    for symbol in index_symbols:
        hist_df = _safe_history_frame(history, symbol)
        if hist_df.empty:
            try:
                hist_df = yf.Ticker(symbol).history(period=period, auto_adjust=True).reset_index()
                if "Date" in hist_df.columns:
                    hist_df["Date"] = pd.to_datetime(hist_df["Date"]).dt.tz_localize(None)
            except Exception:
                hist_df = pd.DataFrame()

        metrics = _metrics_from_history(hist_df)
        index_rows.append(
            {
                "symbol": symbol,
                "name_key": INDEX_NAME_KEYS.get(symbol, symbol),
                "etf_codes": INDEX_TRACKER_ETFS.get(symbol, ""),
                **metrics,
            }
        )
        if not hist_df.empty:
            index_histories[symbol] = hist_df[["Date", "Close"]].copy()

    for symbol in sector_symbols:
        hist_df = _safe_history_frame(history, symbol)
        if hist_df.empty:
            try:
                hist_df = yf.Ticker(symbol).history(period=period, auto_adjust=True).reset_index()
                if "Date" in hist_df.columns:
                    hist_df["Date"] = pd.to_datetime(hist_df["Date"]).dt.tz_localize(None)
            except Exception:
                hist_df = pd.DataFrame()

        metrics = _metrics_from_history(hist_df)
        sector_rows.append(
            {
                "symbol": symbol,
                "name_key": SECTOR_NAME_KEYS.get(symbol, symbol),
                **metrics,
            }
        )

    indices_df = pd.DataFrame(index_rows)
    sectors_df = pd.DataFrame(sector_rows)
    if not sectors_df.empty and "period_change_pct" in sectors_df.columns:
        sectors_df = sectors_df.sort_values("period_change_pct", ascending=False, na_position="last")

    return {
        "indices": indices_df,
        "sectors": sectors_df,
        "index_histories": index_histories,
    }
