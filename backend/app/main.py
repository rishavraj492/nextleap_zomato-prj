"""Recommendation API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.facets import router as facets_router
from app.api.recommendations import router as recommendations_router
from app.config import VERCEL_ORIGIN_REGEX, allowed_origins, load_settings
from app.services.catalog import get_catalog, load_catalog_or_exit, set_catalog

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = load_settings()
    catalog = load_catalog_or_exit(settings.catalog_path)
    set_catalog(catalog)
    logger.info("Loaded %s restaurants from %s", len(catalog), settings.catalog_path)
    yield
    set_catalog(None)


app = FastAPI(title="AI-Powered Restaurant Recommendation System", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_origin_regex=VERCEL_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(facets_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str | bool | int]:
    catalog = get_catalog()
    return {
        "status": "ok",
        "catalogLoaded": catalog is not None,
        "restaurantCount": 0 if catalog is None else len(catalog),
    }
