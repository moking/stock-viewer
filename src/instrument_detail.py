"""Index and ETF detail for macro market dialogs."""

from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf

from src.macro_overview import INDEX_NAME_KEYS, SECTOR_ETF_SYMBOLS, SECTOR_NAME_KEYS
from src.stock_data import normalize_symbol

# Representative top constituents (illustrative; weights approximate where noted).
INDEX_PROFILES: dict[str, dict[str, Any]] = {
    "^GSPC": {
        "description_key": "macro_desc_sp500",
        "components": [
            ("AAPL", "Apple", 7.2),
            ("MSFT", "Microsoft", 6.8),
            ("NVDA", "NVIDIA", 6.1),
            ("AMZN", "Amazon", 3.8),
            ("META", "Meta", 2.5),
            ("GOOGL", "Alphabet A", 2.3),
            ("BRK-B", "Berkshire Hathaway", 1.7),
            ("AVGO", "Broadcom", 1.6),
            ("TSLA", "Tesla", 1.4),
            ("JPM", "JPMorgan Chase", 1.3),
        ],
    },
    "^IXIC": {
        "description_key": "macro_desc_nasdaq",
        "components": [
            ("AAPL", "Apple", None),
            ("MSFT", "Microsoft", None),
            ("NVDA", "NVIDIA", None),
            ("AMZN", "Amazon", None),
            ("META", "Meta", None),
            ("GOOGL", "Alphabet A", None),
            ("AVGO", "Broadcom", None),
            ("TSLA", "Tesla", None),
            ("COST", "Costco", None),
            ("NFLX", "Netflix", None),
        ],
    },
    "^DJI": {
        "description_key": "macro_desc_dow",
        "components": [
            ("UNH", "UnitedHealth", None),
            ("GS", "Goldman Sachs", None),
            ("MSFT", "Microsoft", None),
            ("HD", "Home Depot", None),
            ("CAT", "Caterpillar", None),
            ("CRM", "Salesforce", None),
            ("V", "Visa", None),
            ("MCD", "McDonald's", None),
            ("AXP", "American Express", None),
            ("BA", "Boeing", None),
        ],
    },
    "^RUT": {
        "description_key": "macro_desc_russell",
        "components": [
            ("SMCI", "Super Micro Computer", None),
            ("MSTR", "MicroStrategy", None),
            ("PLTR", "Palantir", None),
            ("COIN", "Coinbase", None),
            ("CRWD", "CrowdStrike", None),
            ("DDOG", "Datadog", None),
            ("ZS", "Zscaler", None),
            ("ROKU", "Roku", None),
            ("SNOW", "Snowflake", None),
            ("NET", "Cloudflare", None),
        ],
    },
}

ETF_PROFILES: dict[str, dict[str, Any]] = {
    "XLK": {"description_key": "macro_desc_xlk"},
    "XLF": {"description_key": "macro_desc_xlf"},
    "XLV": {"description_key": "macro_desc_xlv"},
    "XLE": {"description_key": "macro_desc_xle"},
    "XLI": {"description_key": "macro_desc_xli"},
    "XLP": {"description_key": "macro_desc_xlp"},
    "XLY": {"description_key": "macro_desc_xly"},
    "XLB": {"description_key": "macro_desc_xlb"},
    "XLU": {"description_key": "macro_desc_xlu"},
    "XLRE": {"description_key": "macro_desc_xlre"},
    "XLC": {"description_key": "macro_desc_xlc"},
}


def _components_df(components: list[tuple]) -> pd.DataFrame:
    rows = []
    for item in components:
        symbol = item[0]
        name = item[1] if len(item) > 1 else symbol
        weight = item[2] if len(item) > 2 else None
        rows.append({"symbol": symbol, "name": name, "weight_pct": weight})
    return pd.DataFrame(rows)


def _sector_weightings_df(weightings: dict[str, float] | None) -> pd.DataFrame:
    if not weightings:
        return pd.DataFrame()
    rows = [{"sector": k, "weight_pct": v * 100 if abs(v) <= 1 else v} for k, v in weightings.items()]
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("weight_pct", ascending=False).reset_index(drop=True)
    return df


def _holdings_df(raw: pd.DataFrame | None) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame()

    df = raw.reset_index()
    rename_map = {}
    for col in df.columns:
        low = str(col).lower()
        if low == "symbol":
            rename_map[col] = "symbol"
        elif low == "name":
            rename_map[col] = "name"
        elif "holding" in low and "percent" in low:
            rename_map[col] = "weight_pct"
        elif col == "Name":
            rename_map[col] = "name"

    df = df.rename(columns=rename_map)
    if "weight_pct" in df.columns:
        df["weight_pct"] = df["weight_pct"].apply(
            lambda v: float(v) * 100 if pd.notna(v) and abs(float(v)) <= 1 else v
        )
    keep = [c for c in ("symbol", "name", "weight_pct") if c in df.columns]
    return df[keep] if keep else df


def fetch_instrument_detail(symbol: str) -> dict[str, Any]:
    symbol = normalize_symbol(symbol)
    is_etf = symbol in SECTOR_ETF_SYMBOLS
    is_index = symbol in INDEX_PROFILES

    ticker = yf.Ticker(symbol)
    info = ticker.info or {}

    quote_type = info.get("quoteType") or ("ETF" if is_etf else "INDEX")
    name = info.get("longName") or info.get("shortName") or symbol

    profile = ETF_PROFILES.get(symbol) or INDEX_PROFILES.get(symbol) or {}
    description_key = profile.get("description_key")
    description = info.get("longBusinessSummary") or ""

    holdings = pd.DataFrame()
    sectors = pd.DataFrame()
    components = pd.DataFrame()

    if is_etf:
        try:
            funds = ticker.funds_data
            if funds is not None:
                if getattr(funds, "description", None):
                    description = funds.description or description
                holdings = _holdings_df(getattr(funds, "top_holdings", None))
                sectors = _sector_weightings_df(getattr(funds, "sector_weightings", None))
        except Exception:
            pass

    if is_index and profile.get("components"):
        components = _components_df(profile["components"])

    expense_ratio = info.get("annualReportExpenseRatio") or info.get("netExpenseRatio") or info.get("expenseRatio")
    if expense_ratio is not None and abs(float(expense_ratio)) > 1:
        expense_ratio = float(expense_ratio) / 100

    dividend_yield = info.get("yield") or info.get("dividendYield")
    if dividend_yield is not None and abs(float(dividend_yield)) > 1:
        dividend_yield = float(dividend_yield) / 100

    name_key = INDEX_NAME_KEYS.get(symbol) or SECTOR_NAME_KEYS.get(symbol)

    return {
        "symbol": symbol,
        "name": name,
        "name_key": name_key,
        "quote_type": quote_type,
        "description": description,
        "description_key": description_key,
        "currency": info.get("currency"),
        "total_assets": info.get("totalAssets"),
        "expense_ratio": expense_ratio,
        "dividend_yield": dividend_yield,
        "category": info.get("category"),
        "fund_family": info.get("fundFamily") or info.get("fundFamilyName"),
        "holdings": holdings,
        "sectors": sectors,
        "components": components,
        "is_etf": is_etf,
        "is_index": is_index,
    }
