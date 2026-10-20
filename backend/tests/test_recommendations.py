from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.catalog import Restaurant, get_catalog, load_catalog

CARD_KEYS = [
    "id",
    "name",
    "cuisines",
    "location",
    "rating",
    "votes",
    "costForTwo",
    "restType",
    "reason",
]


def test_unknown_location_budget_and_rating_are_422(fixture_catalog_path: Path) -> None:
    with TestClient(app) as client:
        unknown_location = client.post("/api/recommendations", json=_query(location="Delhi"))
        unknown_neighborhood = client.post("/api/recommendations", json=_query(location="Koramangala"))
        unknown_budget = client.post("/api/recommendations", json=_query(budget="luxury"))
        rating_above = client.post("/api/recommendations", json=_query(minRating=5.1))
        rating_below = client.post("/api/recommendations", json=_query(minRating=-0.1))

    assert unknown_location.status_code == 422
    assert unknown_location.json()["detail"] == "Unknown location"
    assert unknown_neighborhood.status_code == 422
    assert unknown_budget.status_code == 422
    assert unknown_budget.json()["detail"] == "Unknown budget"
    assert rating_above.status_code == 422
    assert rating_below.status_code == 422


def test_omitted_cuisine_still_returns_matches(fixture_catalog_path: Path) -> None:
    with TestClient(app) as client:
        empty_cuisines = client.post("/api/recommendations", json=_query(cuisines=[]))
        blank_cuisines = client.post("/api/recommendations", json=_query(cuisines=["  "]))
        omitted = client.post(
            "/api/recommendations",
            json={"location": "Banashankari", "budget": "medium", "minRating": 4},
        )

    assert empty_cuisines.status_code == 200
    assert blank_cuisines.status_code == 200
    assert omitted.status_code == 200
    assert empty_cuisines.json()["recommendations"]
    assert empty_cuisines.json() == blank_cuisines.json() == omitted.json()


def test_known_query_returns_catalog_cards_in_stable_order(fixture_catalog_path: Path) -> None:
    catalog = load_catalog(fixture_catalog_path)
    payload = _query(
        location="koramangala 5th block",
        budget="low",
        cuisines=["Chinese", "North Indian"],
        minRating=0,
        limit=1,
        preferences="family-friendly",
    )

    with TestClient(app) as client:
        first = client.post("/api/recommendations", json=payload)
        second = client.post("/api/recommendations", json=payload)
        loaded = get_catalog()

    assert first.status_code == 200
    assert first.json() == second.json()
    body = first.json()
    assert list(body.keys()) == ["summary", "explanations", "matchedCount", "recommendations"]
    assert body["explanations"] == "unavailable"
    assert "highest-rated" in body["summary"]
    assert "temporarily unavailable" in body["summary"]
    assert "Koramangala 5th Block" in body["summary"]
    assert body["matchedCount"] == 2
    assert len(body["recommendations"]) == 1

    card = body["recommendations"][0]
    assert list(card.keys()) == CARD_KEYS
    restaurant = _by_name(catalog, "Jalsa", "Koramangala 5th Block")
    assert card == _card(restaurant)
    assert card["rating"] == 4.5
    assert card["votes"] == 40
    assert "phone" not in card
    assert "reviews" not in card
    assert loaded is not None
    assert loaded.get(card["id"]) == restaurant


def test_filters_that_match_nothing_return_an_empty_list(fixture_catalog_path: Path) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/recommendations",
            json=_query(location="Banashankari", budget="high", cuisines=["north indian"], minRating=4),
        )

    assert response.status_code == 200
    assert response.json() == {
        "summary": "No restaurants in Banashankari match those filters.",
        "explanations": "skipped",
        "matchedCount": 0,
        "recommendations": [],
    }


def test_default_limit_returns_the_shortlist_without_a_model_key(
    fixture_catalog_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    catalog = load_catalog(fixture_catalog_path)

    with TestClient(app) as client:
        response = client.post(
            "/api/recommendations",
            json={
                "location": "Koramangala 5th Block",
                "budget": "low",
                "cuisines": ["chinese", "north indian"],
                "minRating": 0,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["matchedCount"] == 2
    assert [card["name"] for card in body["recommendations"]] == ["Jalsa", "Spice Elephant"]
    assert body["recommendations"][1] == _card(_by_name(catalog, "Spice Elephant", "Koramangala 5th Block"))
    assert all(card["reason"] is None for card in body["recommendations"])


def _query(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "location": "Banashankari",
        "budget": "medium",
        "cuisines": ["north indian"],
        "minRating": 4,
    }
    payload.update(overrides)
    return payload


def _by_name(catalog, name: str, location: str) -> Restaurant:
    matches = [
        restaurant
        for restaurant in catalog.restaurants
        if restaurant.name == name and restaurant.location == location
    ]
    assert len(matches) == 1
    return matches[0]


def _card(restaurant: Restaurant) -> dict[str, object]:
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "cuisines": restaurant.cuisines,
        "location": restaurant.location,
        "rating": restaurant.rating,
        "votes": restaurant.votes,
        "costForTwo": restaurant.cost_for_two,
        "restType": restaurant.rest_type,
        "reason": None,
    }
