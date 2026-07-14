"""Local portfolio storage and calculations."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.stock_data import fetch_quote, normalize_symbol

PORTFOLIO_PATH = Path(__file__).resolve().parent.parent / "data" / "portfolio.json"


@dataclass
class Holding:
    symbol: str
    shares: float
    cost_basis: float
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Holding:
        return cls(
            symbol=normalize_symbol(data["symbol"]),
            shares=float(data["shares"]),
            cost_basis=float(data["cost_basis"]),
            note=data.get("note", ""),
        )


def _ensure_data_dir() -> None:
    PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_holdings() -> list[Holding]:
    _ensure_data_dir()
    if not PORTFOLIO_PATH.exists():
        return []

    with PORTFOLIO_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    return [Holding.from_dict(item) for item in raw.get("holdings", [])]


def save_holdings(holdings: list[Holding]) -> None:
    _ensure_data_dir()
    payload = {"holdings": [h.to_dict() for h in holdings]}
    with PORTFOLIO_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def add_holding(symbol: str, shares: float, cost_basis: float, note: str = "") -> None:
    holdings = load_holdings()
    symbol = normalize_symbol(symbol)
    holdings.append(Holding(symbol=symbol, shares=shares, cost_basis=cost_basis, note=note))
    save_holdings(holdings)


def remove_holding(symbol: str) -> None:
    symbol = normalize_symbol(symbol)
    holdings = [h for h in load_holdings() if h.symbol != symbol]
    save_holdings(holdings)


def update_holding(symbol: str, shares: float, cost_basis: float, note: str = "") -> None:
    symbol = normalize_symbol(symbol)
    holdings = load_holdings()
    updated = []
    found = False
    for h in holdings:
        if h.symbol == symbol:
            updated.append(Holding(symbol=symbol, shares=shares, cost_basis=cost_basis, note=note))
            found = True
        else:
            updated.append(h)
    if not found:
        updated.append(Holding(symbol=symbol, shares=shares, cost_basis=cost_basis, note=note))
    save_holdings(updated)


def compute_portfolio_summary() -> dict[str, Any]:
    holdings = load_holdings()
    rows = []
    total_cost = 0.0
    total_value = 0.0

    for h in holdings:
        quote = fetch_quote(h.symbol)
        price = quote.get("price")
        cost = h.shares * h.cost_basis
        value = h.shares * price if price is not None else None
        pnl = (value - cost) if value is not None else None
        pnl_pct = ((pnl / cost) * 100) if pnl is not None and cost else None

        if value is not None:
            total_value += value
        total_cost += cost

        rows.append(
            {
                "symbol": h.symbol,
                "name": quote.get("name", h.symbol),
                "shares": h.shares,
                "cost_basis": h.cost_basis,
                "current_price": price,
                "cost_total": cost,
                "market_value": value,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "note": h.note,
                "currency": quote.get("currency", "USD"),
            }
        )

    total_pnl = total_value - total_cost if holdings else 0.0
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0

    return {
        "rows": rows,
        "total_cost": total_cost,
        "total_value": total_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
    }
