"""Local favorite stocks storage."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.stock_data import normalize_symbol

FAVORITES_PATH = Path(__file__).resolve().parent.parent / "data" / "favorites.json"


@dataclass
class Favorite:
    symbol: str
    name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Favorite:
        return cls(
            symbol=normalize_symbol(data["symbol"]),
            name=data.get("name", ""),
        )


def _ensure_data_dir() -> None:
    FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_favorites() -> list[Favorite]:
    _ensure_data_dir()
    if not FAVORITES_PATH.exists():
        return []

    with FAVORITES_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    return [Favorite.from_dict(item) for item in raw.get("favorites", [])]


def save_favorites(favorites: list[Favorite]) -> None:
    _ensure_data_dir()
    payload = {"favorites": [f.to_dict() for f in favorites]}
    with FAVORITES_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def is_favorite(symbol: str) -> bool:
    symbol = normalize_symbol(symbol)
    return any(f.symbol == symbol for f in load_favorites())


def add_favorite(symbol: str, name: str = "") -> None:
    symbol = normalize_symbol(symbol)
    favorites = load_favorites()
    for i, fav in enumerate(favorites):
        if fav.symbol == symbol:
            if name and name != fav.name:
                favorites[i] = Favorite(symbol=symbol, name=name)
                save_favorites(favorites)
            return
    favorites.append(Favorite(symbol=symbol, name=name))
    favorites.sort(key=lambda f: f.symbol)
    save_favorites(favorites)


def remove_favorite(symbol: str) -> None:
    symbol = normalize_symbol(symbol)
    favorites = [f for f in load_favorites() if f.symbol != symbol]
    save_favorites(favorites)


def toggle_favorite(symbol: str, name: str = "") -> bool:
    symbol = normalize_symbol(symbol)
    if is_favorite(symbol):
        remove_favorite(symbol)
        return False
    add_favorite(symbol, name)
    return True
