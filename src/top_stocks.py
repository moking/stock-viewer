"""Top stock ranking for sidebar picker."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import yfinance as yf

from src.stock_data import PERIOD_OPTIONS, normalize_symbol

# Liquid large-cap US stocks
STOCK_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM", "V",
    "UNH", "XOM", "JNJ", "WMT", "MA", "PG", "HD", "CVX", "MRK", "ABBV",
    "KO", "PEP", "COST", "AVGO", "LLY", "TMO", "MCD", "CSCO", "ACN", "ABT",
    "AMD", "QCOM", "NFLX", "CRM", "ORCL", "INTC", "BA", "DIS", "GS", "MS",
    "WFC", "BAC", "MU", "ADI", "SBUX", "PYPL",
]

TOP_SORT_KEYS = ("market_cap", "period_amount", "active_trade_days")
TOP_LIMIT = 15

_COMPANY_SUFFIX_RE = re.compile(
    r",?\s+(?:Corporation|Corp\.?|Inc\.?|Incorporated|Company|Co\.?|Ltd\.?|Limited|PLC|Group)\.?$",
    re.IGNORECASE,
)


def simplify_company_name(name: str) -> str:
    if not name:
        return name
    result = name.strip()
    while True:
        cleaned = _COMPANY_SUFFIX_RE.sub("", result).strip()
        if cleaned == result:
            break
        result = cleaned
    return result


def _safe_history_frame(raw, symbol: str) -> pd.DataFrame:
    if raw is None or (isinstance(raw, pd.DataFrame) and raw.empty):
        return pd.DataFrame()

    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        if symbol in df.columns.get_level_values(0):
            df = df[symbol].copy()
        else:
            return pd.DataFrame()

    if "Close" not in df.columns or "Volume" not in df.columns:
        return pd.DataFrame()

    work = df.reset_index()
    if "Date" not in work.columns and "Datetime" in work.columns:
        work = work.rename(columns={"Datetime": "Date"})
    return work


def _metric_from_history(df: pd.DataFrame) -> tuple[float, float, int]:
    if df.empty:
        return 0.0, 0.0, 0
    volume = df["Volume"].fillna(0)
    close = df["Close"].fillna(0)
    period_amount = float((volume * close).sum())
    avg_volume = float(volume.mean()) if len(volume) else 0.0
    active_trade_days = int((volume > avg_volume).sum()) if avg_volume > 0 else 0
    return period_amount, avg_volume, active_trade_days


def format_top_row_label(row: pd.Series, sort_by: str = "") -> str:
    symbol = str(row["symbol"])
    name = simplify_company_name(str(row.get("name") or symbol))
    return f"{symbol} · {name}"


def fetch_top_stocks(period_label: str, sort_by: str, limit: int = TOP_LIMIT) -> pd.DataFrame:
    period = PERIOD_OPTIONS.get(period_label, "3mo")
    if sort_by not in TOP_SORT_KEYS:
        sort_by = "market_cap"

    symbols = [normalize_symbol(s) for s in STOCK_UNIVERSE]
    rows: list[dict[str, Any]] = []

    try:
        history = yf.download(
            symbols,
            period=period,
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
    except Exception:
        history = None

    tickers = yf.Tickers(" ".join(symbols))

    for symbol in symbols:
        try:
            hist_df = _safe_history_frame(history, symbol)
            if hist_df.empty:
                ticker = yf.Ticker(symbol)
                hist_df = ticker.history(period=period, auto_adjust=True).reset_index()

            period_amount, _, active_trade_days = _metric_from_history(hist_df)

            fast = tickers.tickers[symbol].fast_info
            market_cap = getattr(fast, "market_cap", None)
            if market_cap is None:
                info = tickers.tickers[symbol].info or {}
                market_cap = info.get("marketCap")

            name = getattr(fast, "short_name", None) or symbol
            try:
                info_name = (tickers.tickers[symbol].info or {}).get("shortName")
                if info_name:
                    name = info_name
            except Exception:
                pass

            name = simplify_company_name(str(name or symbol))

            rows.append(
                {
                    "symbol": symbol,
                    "name": name,
                    "market_cap": float(market_cap or 0),
                    "period_amount": period_amount,
                    "active_trade_days": active_trade_days,
                }
            )
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.sort_values(sort_by, ascending=False).head(limit).reset_index(drop=True)
    return df
