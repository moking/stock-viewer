"""Trend analysis: analyst forecasts, institutional ratings, and market views."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from src.stock_data import fetch_history, get_period_bounds, get_ticker, normalize_symbol
from src.stock_news import prepare_news_items

GRADE_TO_CANONICAL = {
    "Strong Buy": "strong_buy",
    "Buy": "buy",
    "Hold": "hold",
    "Sell": "sell",
    "Strong Sell": "strong_sell",
    "Outperform": "outperform",
    "Underperform": "underperform",
    "Overweight": "overweight",
    "Underweight": "underweight",
    "Equal-Weight": "hold",
    "Neutral": "hold",
    "Positive": "buy",
    "Negative": "sell",
    "Market Perform": "hold",
}

RECOMMENDATION_TO_CANONICAL = {
    "strong_buy": "strong_buy",
    "buy": "buy",
    "hold": "hold",
    "sell": "sell",
    "strong_sell": "strong_sell",
    "underperform": "underperform",
    "outperform": "outperform",
    "positive": "buy",
    "negative": "sell",
    "neutral": "hold",
    "market_perform": "hold",
    "equal_weight": "hold",
    "overweight": "overweight",
    "underweight": "underweight",
}


def _safe_df(attr) -> pd.DataFrame:
    try:
        if attr is None:
            return pd.DataFrame()
        if isinstance(attr, pd.DataFrame):
            return attr.copy()
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _extract_value(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, dict):
        raw = value.get("raw")
        return float(raw) if raw is not None else None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_grade(grade: str) -> str:
    if not grade or pd.isna(grade):
        return "—"
    text = str(grade).strip()
    return GRADE_TO_CANONICAL.get(text, text)


def _normalize_recommendation(key: str | None) -> str:
    if not key:
        return ""
    norm = str(key).lower().replace(" ", "_").replace("-", "_")
    return RECOMMENDATION_TO_CANONICAL.get(norm, norm)


def _filter_index_by_period(df: pd.DataFrame, start: pd.Timestamp | None, end: pd.Timestamp | None) -> pd.DataFrame:
    if df.empty or start is None or end is None:
        return df
    idx = pd.to_datetime(df.index, errors="coerce")
    if hasattr(idx, "tz_localize"):
        try:
            idx = idx.tz_localize(None)
        except TypeError:
            pass
    mask = (idx >= start) & (idx <= end)
    return df.loc[mask].copy()


def _prepare_upgrades_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.reset_index().rename(columns={"GradeDate": "grade_date", "index": "grade_date"})
    rename_map = {
        "Firm": "firm",
        "ToGrade": "to_grade",
        "FromGrade": "from_grade",
        "Action": "action",
        "priceTarget": "price_target",
        "currentPriceTarget": "current_price_target",
        "priorPriceTarget": "prior_price_target",
    }
    out = out.rename(columns=rename_map)
    for col in ("to_grade", "from_grade"):
        if col in out.columns:
            out[col] = out[col].apply(_normalize_grade)
    if "grade_date" in out.columns:
        out["grade_date"] = pd.to_datetime(out["grade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    for col in ("price_target", "current_price_target", "prior_price_target"):
        if col in out.columns:
            out[col] = out[col].apply(_extract_value)
    return out


def _prepare_recommendation_trend(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    mapping = {
        "strongBuy": "strong_buy",
        "buy": "buy",
        "hold": "hold",
        "sell": "sell",
        "strongSell": "strong_sell",
    }
    cols = [c for c in mapping if c in out.columns]
    if not cols:
        return pd.DataFrame()

    result = out[cols].rename(columns=mapping)
    if "period" in out.columns:
        result.insert(0, "period", out["period"].values)
    return result


def _prepare_growth_estimates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    rename = {
        "stockTrend": "stock_growth_pct",
        "industryTrend": "industry_growth_pct",
        "sectorTrend": "sector_growth_pct",
        "indexTrend": "index_growth_pct",
    }
    out = df.rename(columns=rename)
    out.index.name = "period"
    return out.reset_index()


def _prepare_eps_table(df: pd.DataFrame, category: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.reset_index().rename(columns={"period": "period", "index": "period"})
    out.insert(0, "category", category)
    return out


def _prepare_news(news_items: list[dict], start: pd.Timestamp | None, end: pd.Timestamp | None) -> pd.DataFrame:
    df = prepare_news_items(news_items, start, end)
    if df.empty:
        return df
    return df.drop(columns=["summary"], errors="ignore")


def fetch_trend_analysis(symbol: str, period_label: str = "3个月", current_price: float | None = None) -> dict[str, Any]:
    symbol = normalize_symbol(symbol)
    ticker = get_ticker(symbol)
    history = fetch_history(symbol, period_label)
    period_start, period_end = get_period_bounds(history)
    info = ticker.info or {}

    targets_raw = getattr(ticker, "analyst_price_targets", {}) or {}
    targets = {k: _extract_value(v) for k, v in targets_raw.items()}

    price = current_price or _extract_value(targets.get("current")) or info.get("currentPrice")
    mean_target = targets.get("mean") or info.get("targetMeanPrice")
    high_target = targets.get("high") or info.get("targetHighPrice")
    low_target = targets.get("low") or info.get("targetLowPrice")

    upside = None
    if price and mean_target:
        upside = (mean_target - price) / price * 100

    recommendations = _safe_df(getattr(ticker, "recommendations", None))
    recommendation_trend = _prepare_recommendation_trend(recommendations)

    try:
        upgrades = _safe_df(getattr(ticker, "upgrades_downgrades", None))
    except Exception:
        upgrades = pd.DataFrame()
    upgrades_in_period = _filter_index_by_period(upgrades, period_start, period_end)
    upgrades_table = _prepare_upgrades_table(upgrades_in_period)

    growth = _prepare_growth_estimates(_safe_df(getattr(ticker, "growth_estimates", None)))
    eps_trend = _prepare_eps_table(_safe_df(getattr(ticker, "eps_trend", None)), "eps_trend")
    eps_revisions = _prepare_eps_table(_safe_df(getattr(ticker, "eps_revisions", None)), "eps_revisions")

    try:
        news_items = ticker.get_news(count=30) or []
    except Exception:
        news_items = []
    news_table = _prepare_news(news_items, period_start, period_end)

    latest_distribution = {}
    if not recommendation_trend.empty:
        latest = recommendation_trend.iloc[-1]
        for col in latest.index:
            if col != "period" and pd.notna(latest[col]):
                latest_distribution[col] = int(latest[col])

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
        "consensus_rating": _normalize_recommendation(info.get("recommendationKey")),
        "consensus_score": info.get("recommendationMean"),
        "analyst_count": info.get("numberOfAnalystOpinions"),
        "average_rating_text": info.get("averageAnalystRating"),
        "current_price": price,
        "target_mean": mean_target,
        "target_high": high_target,
        "target_low": low_target,
        "upside_pct": upside,
        "recommendation_trend": recommendation_trend,
        "latest_distribution": latest_distribution,
        "upgrades_downgrades": upgrades_table,
        "growth_estimates": growth,
        "eps_trend": eps_trend,
        "eps_revisions": eps_revisions,
        "news": news_table,
        "has_data": any(
            [
                info.get("recommendationKey"),
                mean_target is not None,
                not recommendation_trend.empty,
                not upgrades_table.empty,
                not growth.empty,
                not news_table.empty,
            ]
        ),
        "updated_at": datetime.now(),
    }
