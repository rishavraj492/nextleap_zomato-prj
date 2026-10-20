"""Catalog-backed recommendation payload."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExplanationStatus = Literal["available", "unavailable", "skipped"]


class Recommendation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    cuisines: str
    location: str
    rating: float | None
    votes: int
    cost_for_two: int | None = Field(alias="costForTwo")
    rest_type: str = Field(alias="restType")
    reason: str | None


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    summary: str
    explanations: ExplanationStatus
    matched_count: int = Field(alias="matchedCount")
    recommendations: list[Recommendation]
