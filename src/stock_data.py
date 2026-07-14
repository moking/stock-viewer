"""Fetch stock market data via yfinance."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf


PERIOD_OPTIONS = {
    "1周": "5d",
    "1个月": "1mo",
    "3个月": "3mo",
    "6个月": "6mo",
    "1年": "1y",
    "2年": "2y",
    "5年": "5y",
}


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def is_us_symbol(symbol: str) -> bool:
    """Return True for US tickers and US index symbols (^GSPC, etc.)."""
    sym = normalize_symbol(symbol)
    if sym.endswith((".SS", ".SZ", ".HK")):
        return False
    return True


def get_ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(normalize_symbol(symbol))


def fetch_quote(symbol: str) -> dict[str, Any]:
    ticker = get_ticker(symbol)
    info = ticker.info or {}
    fast = ticker.fast_info

    price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or getattr(fast, "last_price", None)
        or info.get("previousClose")
    )
    prev_close = (
        info.get("regularMarketPreviousClose")
        or info.get("previousClose")
        or getattr(fast, "previous_close", None)
    )

    change = None
    change_pct = None
    if price is not None and prev_close:
        change = price - prev_close
        change_pct = (change / prev_close) * 100

    return {
        "symbol": normalize_symbol(symbol),
        "name": info.get("shortName") or info.get("longName") or symbol,
        "price": price,
        "prev_close": prev_close,
        "change": change,
        "change_pct": change_pct,
        "volume": info.get("volume") or getattr(fast, "last_volume", None),
        "avg_volume": info.get("averageVolume") or info.get("averageVolume10days"),
        "market_cap": info.get("marketCap"),
        "currency": info.get("currency", "USD"),
        "exchange": info.get("exchange"),
        "day_high": info.get("dayHigh") or getattr(fast, "day_high", None),
        "day_low": info.get("dayLow") or getattr(fast, "day_low", None),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "pe_ratio": info.get("trailingPE"),
        "dividend_yield": info.get("dividendYield"),
        "updated_at": datetime.now(),
    }


def fetch_history(symbol: str, period_label: str = "3个月") -> pd.DataFrame:
    period = PERIOD_OPTIONS.get(period_label, "3mo")
    ticker = get_ticker(symbol)
    df = ticker.history(period=period, auto_adjust=True)

    if df.empty:
        return df

    df = df.reset_index()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    return df


def get_period_bounds(history: pd.DataFrame) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    if history.empty or "Date" not in history.columns:
        return None, None
    dates = pd.to_datetime(history["Date"], errors="coerce")
    return dates.min(), dates.max()


def compute_period_trading_summary(history: pd.DataFrame) -> dict[str, Any]:
    if history.empty:
        return {}

    start_price = history["Close"].iloc[0]
    end_price = history["Close"].iloc[-1]
    period_change = (end_price / start_price - 1) * 100 if start_price else None

    return {
        "trading_days": len(history),
        "total_volume": int(history["Volume"].sum()) if "Volume" in history.columns else None,
        "avg_volume": int(history["Volume"].mean()) if "Volume" in history.columns else None,
        "avg_close": float(history["Close"].mean()),
        "period_high": float(history["High"].max()) if "High" in history.columns else None,
        "period_low": float(history["Low"].min()) if "Low" in history.columns else None,
        "period_change_pct": period_change,
        "start_date": history["Date"].iloc[0],
        "end_date": history["Date"].iloc[-1],
    }


def fetch_batch_quotes(symbols: list[str]) -> list[dict[str, Any]]:
    results = []
    for symbol in symbols:
        try:
            results.append(fetch_quote(symbol))
        except Exception:
            results.append(
                {
                    "symbol": normalize_symbol(symbol),
                    "name": symbol,
                    "price": None,
                    "error": True,
                }
            )
    return results
