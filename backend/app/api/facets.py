"""Form options derived from the loaded catalog."""

from fastapi import APIRouter, HTTPException

from app.config import BUDGETS, RATING_MAX, RATING_MIN
from app.services.catalog import get_catalog

router = APIRouter()


@router.get("/facets")
def facets() -> dict[str, list[str] | int]:
    catalog = get_catalog()
    if catalog is None:
        raise HTTPException(status_code=503, detail="Catalog is not loaded")
    return {
        "locations": catalog.locations(),
        "cuisines": catalog.cuisines(),
        "budgets": list(BUDGETS),
        "ratingMin": RATING_MIN,
        "ratingMax": RATING_MAX,
    }
