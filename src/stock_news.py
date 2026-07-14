"""Recent stock news from Yahoo Finance."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.stock_data import get_ticker, normalize_symbol

DEFAULT_NEWS_LIMIT = 12


def _extract_link(content: dict[str, Any]) -> str | None:
    for key in ("canonicalUrl", "clickThroughUrl"):
        value = content.get(key)
        if isinstance(value, dict):
            url = value.get("url")
            if url:
                return url
        elif isinstance(value, str) and value:
            return value
    for key in ("link", "url"):
        value = content.get(key)
        if value:
            return value
    return None


def _extract_publisher(content: dict[str, Any]) -> str:
    provider = content.get("provider")
    if isinstance(provider, dict):
        return provider.get("displayName") or provider.get("name") or "—"
    for key in ("publisher", "source"):
        value = content.get(key)
        if value:
            return str(value)
    return "—"


def _parse_published_at(content: dict[str, Any]) -> pd.Timestamp | None:
    raw = (
        content.get("pubDate")
        or content.get("providerPublishTime")
        or content.get("displayTime")
    )
    if raw is None:
        return None

    if isinstance(raw, (int, float)):
        unit = "ms" if raw > 1_000_000_000_000 else "s"
        published = pd.to_datetime(raw, unit=unit, errors="coerce")
    else:
        published = pd.to_datetime(raw, errors="coerce")

    if pd.isna(published):
        return None
    if hasattr(published, "tz_localize"):
        try:
            published = published.tz_localize(None)
        except TypeError:
            published = published.tz_convert(None) if getattr(published, "tzinfo", None) else published
    return published


def _normalize_news_item(item: dict[str, Any]) -> dict[str, Any] | None:
    content = item.get("content") if isinstance(item.get("content"), dict) else item
    title = content.get("title") or item.get("title")
    if not title:
        return None

    published = _parse_published_at(content) or _parse_published_at(item)
    summary = content.get("summary") or content.get("description") or item.get("summary") or ""
    link = _extract_link(content) or _extract_link(item)

    return {
        "published_at": published,
        "date": published.strftime("%Y-%m-%d %H:%M") if published is not None else "—",
        "source": _extract_publisher(content) if content is not item else _extract_publisher(item),
        "title": str(title),
        "summary": str(summary).strip(),
        "link": link,
    }


def prepare_news_items(
    news_items: list[dict[str, Any]],
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in news_items:
        parsed = _normalize_news_item(item)
        if not parsed:
            continue
        published = parsed.get("published_at")
        if start is not None and end is not None and published is not None:
            if not (start <= published <= end):
                continue
        rows.append(
            {
                "date": parsed["date"],
                "source": parsed["source"],
                "title": parsed["title"],
                "summary": parsed["summary"],
                "link": parsed["link"],
                "published_at": published,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if "published_at" in df.columns:
        df = df.sort_values("published_at", ascending=False, na_position="last")
    return df.drop(columns=["published_at"], errors="ignore").reset_index(drop=True)


def fetch_recent_news(symbol: str, limit: int = DEFAULT_NEWS_LIMIT) -> pd.DataFrame:
    symbol = normalize_symbol(symbol)
    ticker = get_ticker(symbol)
    try:
        news_items = ticker.get_news(count=limit) or []
    except Exception:
        news_items = []
    return prepare_news_items(news_items)
