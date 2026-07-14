"""Trend analysis: analyst forecasts, institutional ratings, and market views."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from src.stock_data import fetch_history, get_period_bounds, get_ticker, normalize_symbol
from src.stock_news import prepare_news_items

RECOMMENDATION_LABELS = {
    "strong_buy": "强力买入",
    "buy": "买入",
    "hold": "持有",
    "sell": "卖出",
    "strong_sell": "强力卖出",
    "underperform": "跑输大盘",
    "outperform": "跑赢大盘",
    "positive": "看好",
    "negative": "看空",
    "neutral": "中性",
    "market perform": "符合大盘",
    "equal-weight": "中性",
    "overweight": "增持",
    "underweight": "减持",
}

GRADE_CN = {
    "Strong Buy": "强力买入",
    "Buy": "买入",
    "Hold": "持有",
    "Sell": "卖出",
    "Strong Sell": "强力卖出",
    "Outperform": "跑赢大盘",
    "Underperform": "跑输大盘",
    "Overweight": "增持",
    "Underweight": "减持",
    "Equal-Weight": "中性",
    "Neutral": "中性",
    "Positive": "看好",
    "Negative": "看空",
    "Market Perform": "符合大盘",
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


def _translate_grade(grade: str) -> str:
    if not grade or pd.isna(grade):
        return "—"
    text = str(grade).strip()
    return GRADE_CN.get(text, text)


def _translate_recommendation(key: str | None) -> str:
    if not key:
        return "—"
    return RECOMMENDATION_LABELS.get(str(key).lower().replace(" ", "_"), str(key))


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

    out = df.reset_index().rename(columns={"GradeDate": "评级日期", "index": "评级日期"})
    rename_map = {
        "Firm": "机构",
        "ToGrade": "最新评级",
        "FromGrade": "此前评级",
        "Action": "动作",
        "priceTarget": "目标价",
        "currentPriceTarget": "当前目标价",
        "priorPriceTarget": "此前目标价",
    }
    out = out.rename(columns=rename_map)
    for col in ("最新评级", "此前评级"):
        if col in out.columns:
            out[col] = out[col].apply(_translate_grade)
    if "评级日期" in out.columns:
        out["评级日期"] = pd.to_datetime(out["评级日期"], errors="coerce").dt.strftime("%Y-%m-%d")
    for col in ("目标价", "当前目标价", "此前目标价"):
        if col in out.columns:
            out[col] = out[col].apply(_extract_value)
    return out


def _prepare_recommendation_trend(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    mapping = {
        "strongBuy": "强力买入",
        "buy": "买入",
        "hold": "持有",
        "sell": "卖出",
        "strongSell": "强力卖出",
    }
    cols = [c for c in mapping if c in out.columns]
    if not cols:
        return pd.DataFrame()

    result = out[cols].rename(columns=mapping)
    if "period" in out.columns:
        result.insert(0, "周期", out["period"].values)
    return result


def _prepare_growth_estimates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    rename = {
        "stockTrend": "个股增长预期%",
        "industryTrend": "行业增长预期%",
        "sectorTrend": "板块增长预期%",
        "indexTrend": "指数增长预期%",
    }
    out = df.rename(columns=rename)
    out.index.name = "周期"
    return out.reset_index()


def _prepare_eps_table(df: pd.DataFrame, label: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.reset_index().rename(columns={"period": "周期", "index": "周期"})
    out.insert(0, "类型", label)
    return out


def _prepare_news(news_items: list[dict], start: pd.Timestamp | None, end: pd.Timestamp | None) -> pd.DataFrame:
    df = prepare_news_items(news_items, start, end)
    if df.empty:
        return df
    return df.drop(columns=["摘要"], errors="ignore")


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
    eps_trend = _prepare_eps_table(_safe_df(getattr(ticker, "eps_trend", None)), "EPS趋势")
    eps_revisions = _prepare_eps_table(_safe_df(getattr(ticker, "eps_revisions", None)), "EPS修正")

    try:
        news_items = ticker.get_news(count=30) or []
    except Exception:
        news_items = []
    news_table = _prepare_news(news_items, period_start, period_end)

    latest_distribution = {}
    if not recommendation_trend.empty:
        latest = recommendation_trend.iloc[-1]
        for col in latest.index:
            if col != "周期" and pd.notna(latest[col]):
                latest_distribution[col] = int(latest[col])

    period_range_text = period_label
    if period_start is not None and period_end is not None:
        period_range_text = (
            f"{period_start.strftime('%Y-%m-%d')} ~ {period_end.strftime('%Y-%m-%d')}（{period_label}）"
        )

    return {
        "symbol": symbol,
        "period_label": period_label,
        "period_range_text": period_range_text,
        "period_start": period_start,
        "period_end": period_end,
        "consensus_rating": _translate_recommendation(info.get("recommendationKey")),
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
