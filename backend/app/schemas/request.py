"""Preference payload for POST /api/recommendations."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import RESULT_CAP


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    location: str
    budget: str
    cuisines: list[str] = Field(default_factory=list)
    min_rating: float = Field(alias="minRating")
    preferences: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=RESULT_CAP, ge=1, le=RESULT_CAP)

    @field_validator("location")
    @classmethod
    def strip_location(cls, value: str) -> str:
        return value.strip()

    @field_validator("budget")
    @classmethod
    def normalize_budget(cls, value: str) -> str:
        return value.strip().casefold()

    @field_validator("cuisines")
    @classmethod
    def strip_cuisines(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]
