"""Shared fakes for recommendation tests. Not a test module."""

from __future__ import annotations

import json

from app.config import MEDIUM_BUDGET_MIN
from app.services.catalog import Restaurant
from app.services.llm_client import LlmCompletion


class FakeClient:
    def __init__(self, content: str, *, prompt_tokens: int | None = None, completion_tokens: int | None = None) -> None:
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.messages: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> LlmCompletion:
        self.messages.append(messages)
        return LlmCompletion(
            content=self.content,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
        )


class ExplodingClient:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        self.calls = 0

    def complete(self, messages: list[dict[str, str]]) -> LlmCompletion:
        self.calls += 1
        raise self.exc


def restaurant(restaurant_id: str, **overrides: object) -> Restaurant:
    values: dict[str, object] = {
        "id": restaurant_id,
        "name": restaurant_id,
        "address": f"{restaurant_id} address",
        "location": "Banashankari",
        "cuisines": "North Indian",
        "cuisine_tokens": ("north indian",),
        "rating": 4.0,
        "votes": 10,
        "cost_for_two": MEDIUM_BUDGET_MIN,
        "rest_type": "Casual Dining",
        "listed_types": ("Delivery",),
        "dish_liked": "Biryani",
        "online_order": False,
        "book_table": False,
        "url": "https://example.test",
    }
    values.update(overrides)
    return Restaurant(**values)


def ranking_json(ids: list[str], *, summary: str = "Model summary.") -> str:
    return json.dumps(
        {
            "summary": summary,
            "recommendations": [{"id": restaurant_id, "reason": f"Because {restaurant_id}."} for restaurant_id in ids],
        }
    )
