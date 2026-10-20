"""Keep a bounded shortlist ordered by rating, votes, and name."""

from __future__ import annotations

from app.config import CANDIDATE_CAP
from app.services.catalog import Restaurant


def select_candidates(
    restaurants: list[Restaurant],
    *,
    cap: int = CANDIDATE_CAP,
) -> list[Restaurant]:
    """Sort matches and keep at most ``cap`` restaurants.

    Order is rating descending, votes descending, then name ascending.
    The id is a final tie-break so the same set always yields the same list.
    """
    ranked = sorted(restaurants, key=_sort_key)
    if cap < 0:
        return []
    return ranked[:cap]


def _sort_key(restaurant: Restaurant) -> tuple[float, int, str, str]:
    rating = restaurant.rating if restaurant.rating is not None else float("-inf")
    return (-rating, -restaurant.votes, restaurant.name, restaurant.id)
