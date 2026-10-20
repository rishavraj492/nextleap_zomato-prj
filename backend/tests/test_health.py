import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.catalog import get_catalog, load_catalog, load_catalog_or_exit, set_catalog
from scripts.prepare_dataset import load_source, prepare_catalog


def test_health_reports_fixture_restaurant_count(fixture_catalog_path: Path) -> None:
    expected = len(prepare_catalog(load_source("fixture")))

    with TestClient(app) as client:
        response = client.get("/api/health")
        loaded = get_catalog()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "catalogLoaded": True,
        "restaurantCount": expected,
    }
    assert loaded is not None
    assert len(loaded) == expected
    assert len(load_catalog(fixture_catalog_path)) == expected


def test_startup_can_look_up_a_restaurant_by_id(fixture_catalog_path: Path) -> None:
    with TestClient(app) as client:
        client.get("/api/health")
        catalog = get_catalog()
        assert catalog is not None
        sample = catalog.restaurants[0]
        assert catalog.get(sample.id) == sample
        assert catalog.get("missing-id") is None
        assert sample.location
        assert catalog.by_location
        assert catalog.by_cuisine


def test_facets_lists_only_catalog_locations_and_cuisines(fixture_catalog_path: Path) -> None:
    catalog = load_catalog(fixture_catalog_path)

    with TestClient(app) as client:
        response = client.get("/api/facets")

    assert response.status_code == 200
    body = response.json()
    assert body["locations"] == catalog.locations()
    assert body["cuisines"] == catalog.cuisines()
    assert body["budgets"] == ["low", "medium", "high"]
    assert body["ratingMin"] == 0
    assert body["ratingMax"] == 5
    assert body["cuisines"]
    assert all(cuisine == cuisine.lower() for cuisine in body["cuisines"])
    assert "Banashankari" in body["locations"]
    assert "banashankari" not in body["locations"]
    assert "continental" in body["cuisines"]
    assert "North Indian" not in body["cuisines"]


def test_facets_returns_503_when_catalog_is_not_loaded(fixture_catalog_path: Path) -> None:
    with TestClient(app) as client:
        set_catalog(None)
        response = client.get("/api/facets")

    assert response.status_code == 503


def test_missing_catalog_exits_and_names_prepare_script(tmp_path: Path, caplog) -> None:
    missing = tmp_path / "missing.parquet"

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exited:
            load_catalog_or_exit(missing)

    assert exited.value.code == 1
    assert "prepare_dataset.py" in caplog.text


def test_cors_allows_vite_dev_origin(fixture_catalog_path: Path) -> None:
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_allows_vercel_preview_origin(fixture_catalog_path: Path) -> None:
    origin = "https://zomato-git-main-team.vercel.app"

    with TestClient(app) as client:
        response = client.get("/api/health", headers={"Origin": origin})

    assert response.headers["access-control-allow-origin"] == origin


def test_cors_rejects_unknown_origin(fixture_catalog_path: Path) -> None:
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
