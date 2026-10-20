"""Build the chat messages for a shortlist. The model never sees the full catalog."""

from __future__ import annotations

import json

from app.config import CANDIDATE_CAP
from app.schemas.request import RecommendationRequest
from app.services.catalog import Restaurant

LIKED_DISHES_MAX_CHARS = 40

SYSTEM_PROMPT = (
    "Rank only supplied ids for the free-text preference. Rating and cost already match. "
    "One short sentence per reason, citing only cuisine, cost, rest type, or liked dishes given below. "
    "Do not invent dishes, reviews, or awards. "
    "JSON only. Summary may be empty. Return at most 5 ids."
)


def prompt_rows(shortlist: list[Restaurant]) -> list[tuple[str, Restaurant]]:
    """Alias each shortlist row as 1..N so the model does not echo long catalog ids."""
    return [
        (str(index), restaurant)
        for index, restaurant in enumerate(shortlist[:CANDIDATE_CAP], start=1)
    ]


def build_messages(
    request: RecommendationRequest,
    shortlist: list[Restaurant],
) -> list[dict[str, str]]:
    """System rules plus one compact user message of at most 20 restaurants."""
    payload = {
        "location": request.location,
        "budget": request.budget,
        "cuisines": list(request.cuisines),
        "preference": soft_preference(request.preferences),
        "restaurants": [_record(alias, restaurant) for alias, restaurant in prompt_rows(shortlist)],
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        },
    ]


def soft_preference(value: str | None) -> str:
    """Blank free text is sent as the word none."""
    if value is None:
        return "none"
    text = value.strip()
    if text == "":
        return "none"
    return text


def _record(alias: str, restaurant: Restaurant) -> dict[str, object]:
    record: dict[str, object] = {
        "id": alias,
        "name": restaurant.name,
        "cuisines": restaurant.cuisines,
        "cost": restaurant.cost_for_two,
        "type": restaurant.rest_type,
    }
    dishes = restaurant.dish_liked[:LIKED_DISHES_MAX_CHARS].strip()
    if dishes:
        record["dishes"] = dishes
    return record
