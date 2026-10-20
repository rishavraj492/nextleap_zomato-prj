"""Model payload: ids and reasons only. Catalog facts stay on the server."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, ValidationError


class LlmRecommendation(BaseModel):
    """One ranked id. Extra keys the model echoes are ignored."""

    model_config = ConfigDict(extra="ignore")

    id: str
    reason: str | None = None


class LlmRanking(BaseModel):
    """Parsed model JSON. `summary` may be an empty string."""

    model_config = ConfigDict(extra="ignore")

    summary: str
    recommendations: list[LlmRecommendation]


class UnparseableModelOutput(ValueError):
    """The model body was not the ranking JSON."""


def groq_json_schema() -> dict[str, object]:
    """Strict object schema. Groq rejects optional properties and open objects."""
    item = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["id", "reason"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "recommendations": {"type": "array", "items": item},
        },
        "required": ["summary", "recommendations"],
        "additionalProperties": False,
    }


def groq_response_format() -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "recommendations",
            "strict": True,
            "schema": groq_json_schema(),
        },
    }


def parse_ranking(content: str) -> LlmRanking:
    """Parse the JSON string from `choices[0].message.content`.

    Markdown fences and surrounding prose are rejected so the caller can fall back.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise UnparseableModelOutput("model output is not JSON") from exc
    if not isinstance(data, dict):
        raise UnparseableModelOutput("model output is not a JSON object")
    try:
        return LlmRanking.model_validate(data)
    except ValidationError as exc:
        raise UnparseableModelOutput("model output does not match the ranking schema") from exc
