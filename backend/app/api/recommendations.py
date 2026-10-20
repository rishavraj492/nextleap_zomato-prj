"""Ranked recommendations. The model orders the shortlist and writes reasons."""

import math

from fastapi import APIRouter, HTTPException

from app.config import BUDGETS, RATING_MAX, RATING_MIN
from app.schemas.request import RecommendationRequest
from app.schemas.response import RecommendationResponse
from app.services.catalog import get_catalog, normalize_location
from app.services.recommend import recommend

router = APIRouter()


@router.post("/recommendations", response_model=RecommendationResponse)
def recommendations(body: RecommendationRequest) -> RecommendationResponse:
    catalog = get_catalog()
    if catalog is None:
        raise HTTPException(status_code=503, detail="Catalog is not loaded")
    if body.budget not in BUDGETS:
        raise HTTPException(status_code=422, detail="Unknown budget")
    if normalize_location(body.location) not in catalog.by_location:
        raise HTTPException(status_code=422, detail="Unknown location")
    if not math.isfinite(body.min_rating) or not (RATING_MIN <= body.min_rating <= RATING_MAX):
        raise HTTPException(status_code=422, detail="Rating must be between 0 and 5")
    return recommend(catalog, body)
