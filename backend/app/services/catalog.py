"""In-memory restaurant catalog loaded from parquet."""

from __future__ import annotations

import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_catalog: Catalog | None = None


@dataclass(frozen=True)
class Restaurant:
    id: str
    name: str
    address: str
    location: str
    cuisines: str
    cuisine_tokens: tuple[str, ...]
    rating: float | None
    votes: int
    cost_for_two: int | None
    rest_type: str
    listed_types: tuple[str, ...]
    dish_liked: str
    online_order: bool
    book_table: bool
    url: str


class Catalog:
    """Restaurants plus location and cuisine indexes."""

    def __init__(self, restaurants: list[Restaurant]) -> None:
        self.restaurants: tuple[Restaurant, ...] = tuple(restaurants)
        self.by_id: dict[str, Restaurant] = {restaurant.id: restaurant for restaurant in self.restaurants}
        by_location: dict[str, list[Restaurant]] = {}
        by_cuisine: dict[str, list[Restaurant]] = {}
        for restaurant in self.restaurants:
            location_key = normalize_location(restaurant.location)
            if location_key:
                by_location.setdefault(location_key, []).append(restaurant)
            for token in restaurant.cuisine_tokens:
                cuisine_key = normalize_cuisine(token)
                if cuisine_key:
                    by_cuisine.setdefault(cuisine_key, []).append(restaurant)
        self.by_location: dict[str, tuple[Restaurant, ...]] = {
            key: tuple(value) for key, value in by_location.items()
        }
        self.by_cuisine: dict[str, tuple[Restaurant, ...]] = {
            key: tuple(value) for key, value in by_cuisine.items()
        }

    def __len__(self) -> int:
        return len(self.restaurants)

    def get(self, restaurant_id: str) -> Restaurant | None:
        return self.by_id.get(restaurant_id)

    def locations(self) -> list[str]:
        return sorted({restaurant.location for restaurant in self.restaurants if restaurant.location.strip()})

    def cuisines(self) -> list[str]:
        found: set[str] = set()
        for restaurant in self.restaurants:
            for token in restaurant.cuisine_tokens:
                cuisine_key = normalize_cuisine(token)
                if cuisine_key:
                    found.add(cuisine_key)
        return sorted(found)


def normalize_location(value: str) -> str:
    return value.strip().casefold()


def normalize_cuisine(value: str) -> str:
    return value.strip().lower()


def get_catalog() -> Catalog | None:
    return _catalog


def set_catalog(catalog: Catalog | None) -> None:
    global _catalog
    _catalog = catalog


def load_catalog(path: Path) -> Catalog:
    frame = pd.read_parquet(path)
    restaurants = [_restaurant_from_record(record) for record in frame.to_dict(orient="records")]
    return Catalog(restaurants)


def load_catalog_or_exit(path: Path) -> Catalog:
    if not path.is_file():
        logger.error(
            "Catalog file not found at %s. Run python scripts/prepare_dataset.py",
            path,
        )
        sys.exit(1)
    return load_catalog(path)


def _restaurant_from_record(record: dict[str, object]) -> Restaurant:
    return Restaurant(
        id=_text(record.get("id")),
        name=_text(record.get("name")),
        address=_text(record.get("address")),
        location=_text(record.get("location")),
        cuisines=_text(record.get("cuisines")),
        cuisine_tokens=_texts(record.get("cuisine_tokens")),
        rating=_optional_float(record.get("rating")),
        votes=_int(record.get("votes")),
        cost_for_two=_optional_int(record.get("cost_for_two")),
        rest_type=_text(record.get("rest_type")),
        listed_types=_texts(record.get("listed_types")),
        dish_liked=_text(record.get("dish_liked")),
        online_order=bool(record.get("online_order")),
        book_table=bool(record.get("book_table")),
        url=_text(record.get("url")),
    )


def _text(value: object) -> str:
    if _is_null(value):
        return ""
    return str(value).strip()


def _texts(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _optional_float(value: object) -> float | None:
    if _is_null(value):
        return None
    return float(value)  # type: ignore[arg-type]


def _optional_int(value: object) -> int | None:
    if _is_null(value):
        return None
    return int(value)  # type: ignore[arg-type]


def _int(value: object) -> int:
    if _is_null(value):
        return 0
    return int(value)  # type: ignore[arg-type]


def _is_null(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
