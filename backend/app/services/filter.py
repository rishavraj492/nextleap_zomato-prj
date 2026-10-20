"""Hard filters for location, cuisine, budget, and minimum rating."""

from __future__ import annotations

from app.config import (
    HIGH_BUDGET_ABOVE,
    LOW_BUDGET_UNDER,
    MEDIUM_BUDGET_MAX,
    MEDIUM_BUDGET_MIN,
)
from app.services.catalog import Catalog, Restaurant, normalize_cuisine, normalize_location


def filter_restaurants(
    catalog: Catalog,
    *,
    location: str,
    cuisines: list[str],
    budget: str,
    min_rating: float,
) -> list[Restaurant]:
    """Return restaurants that satisfy every hard constraint.

    Cuisine selections are OR: one overlapping token is enough. An empty cuisine
    list leaves that constraint off. A null cost is dropped when a budget is set.
    A null rating is dropped when a minimum is set.
    """
    selected = {normalize_cuisine(cuisine) for cuisine in cuisines}
    selected.discard("")
    cuisine_ids: set[str] | None = None
    if selected:
        cuisine_ids = set()
        for token in selected:
            for restaurant in catalog.by_cuisine.get(token, ()):
                cuisine_ids.add(restaurant.id)

    matched: list[Restaurant] = []
    for restaurant in catalog.by_location.get(normalize_location(location), ()):
        if cuisine_ids is not None and restaurant.id not in cuisine_ids:
            continue
        if not _cost_in_budget(restaurant.cost_for_two, budget):
            continue
        if restaurant.rating is None or restaurant.rating < min_rating:
            continue
        matched.append(restaurant)
    return matched


def _cost_in_budget(cost: int | None, budget: str) -> bool:
    if cost is None:
        return False
    if budget == "low":
        return cost < LOW_BUDGET_UNDER
    if budget == "medium":
        return MEDIUM_BUDGET_MIN <= cost <= MEDIUM_BUDGET_MAX
    if budget == "high":
        return cost > HIGH_BUDGET_ABOVE
    raise ValueError(f"Unknown budget {budget!r}. Expected low, medium, or high.")
