from pathlib import Path

from app.config import (
    HIGH_BUDGET_ABOVE,
    LOW_BUDGET_UNDER,
    MEDIUM_BUDGET_MAX,
    MEDIUM_BUDGET_MIN,
)
from app.services.catalog import Catalog, Restaurant, load_catalog
from app.services.filter import filter_restaurants

JALSA_ADDRESS = "942, 21st Main Road, Banashankari, Bangalore"
KORAMANGALA_JALSA_ADDRESS = "100, Koramangala 5th Block, Bangalore"


def test_budget_edges_follow_configured_bands() -> None:
    # Current bands make these costs 499, 500, 1000, and 1001.
    low_cost = LOW_BUDGET_UNDER - 1
    medium_floor = MEDIUM_BUDGET_MIN
    medium_ceiling = MEDIUM_BUDGET_MAX
    high_cost = HIGH_BUDGET_ABOVE + 1
    catalog = Catalog(
        [
            _restaurant("low", cost_for_two=low_cost),
            _restaurant("medium-floor", cost_for_two=medium_floor),
            _restaurant("medium-ceiling", cost_for_two=medium_ceiling),
            _restaurant("high", cost_for_two=high_cost),
            _restaurant("missing-cost", cost_for_two=None, rating=4.0),
        ]
    )

    assert _ids(catalog, budget="low") == {"low"}
    assert _ids(catalog, budget="medium") == {"medium-floor", "medium-ceiling"}
    assert _ids(catalog, budget="high") == {"high"}


def test_null_cost_is_excluded_when_a_budget_is_set() -> None:
    catalog = Catalog(
        [
            _restaurant("priced", cost_for_two=MEDIUM_BUDGET_MIN, rating=4.0),
            _restaurant("unpriced", cost_for_two=None, rating=4.0),
        ]
    )

    assert _ids(catalog, budget="medium") == {"priced"}


def test_null_rating_is_excluded_and_equal_rating_is_included() -> None:
    catalog = Catalog(
        [
            _restaurant("exact", rating=4.0, cost_for_two=MEDIUM_BUDGET_MIN),
            _restaurant("higher", rating=4.5, cost_for_two=MEDIUM_BUDGET_MIN),
            _restaurant("lower", rating=3.5, cost_for_two=MEDIUM_BUDGET_MIN),
            _restaurant("unrated", rating=None, cost_for_two=MEDIUM_BUDGET_MIN),
            _restaurant("zero", rating=0.0, cost_for_two=MEDIUM_BUDGET_MIN),
        ]
    )

    assert _ids(catalog, min_rating=4.0) == {"exact", "higher"}
    assert _ids(catalog, min_rating=0) == {"exact", "higher", "lower", "zero"}
    assert "unrated" not in _ids(catalog, min_rating=0)
    assert _ids(catalog, min_rating=5) == set()


def test_empty_cuisine_list_does_not_filter_by_cuisine(fixture_catalog_path: Path) -> None:
    catalog = load_catalog(fixture_catalog_path)

    matches = filter_restaurants(
        catalog,
        location="Koramangala 5th Block",
        cuisines=[],
        budget="low",
        min_rating=0,
    )
    names = {restaurant.name for restaurant in matches}

    assert names == {"Jalsa", "Spice Elephant"}


def test_cuisine_or_matches_any_selected_token(fixture_catalog_path: Path) -> None:
    catalog = load_catalog(fixture_catalog_path)

    matches = filter_restaurants(
        catalog,
        location="Koramangala 5th Block",
        cuisines=["Chinese", "North Indian"],
        budget="low",
        min_rating=0,
    )
    names = {restaurant.name for restaurant in matches}

    assert "Spice Elephant" in names
    assert "Jalsa" in names
    assert "Onesta" not in names
    assert len(matches) == len({restaurant.id for restaurant in matches})


def test_one_cuisine_does_not_require_the_others(fixture_catalog_path: Path) -> None:
    catalog = load_catalog(fixture_catalog_path)

    chinese = filter_restaurants(
        catalog,
        location="Koramangala 5th Block",
        cuisines=["chinese"],
        budget="low",
        min_rating=0,
    )
    both_required_would_miss_spice = filter_restaurants(
        catalog,
        location="Banashankari",
        cuisines=["chinese", "continental"],
        budget="medium",
        min_rating=4.1,
    )

    assert [restaurant.name for restaurant in chinese] == ["Spice Elephant"]
    assert [restaurant.name for restaurant in both_required_would_miss_spice] == ["Jalsa"]
    assert both_required_would_miss_spice[0].address == JALSA_ADDRESS


def test_location_match_is_normalized_and_exact(fixture_catalog_path: Path) -> None:
    catalog = load_catalog(fixture_catalog_path)

    matched = filter_restaurants(
        catalog,
        location="  banashankari  ",
        cuisines=["north indian"],
        budget="medium",
        min_rating=4.1,
    )
    different_neighborhood = filter_restaurants(
        catalog,
        location="Koramangala",
        cuisines=["north indian"],
        budget="low",
        min_rating=0,
    )

    assert [restaurant.address for restaurant in matched] == [JALSA_ADDRESS]
    assert different_neighborhood == []
    koramangala = filter_restaurants(
        catalog,
        location="koramangala 5th block",
        cuisines=["north indian"],
        budget="low",
        min_rating=4.5,
    )
    assert [restaurant.address for restaurant in koramangala] == [KORAMANGALA_JALSA_ADDRESS]


def test_fixture_null_rating_and_null_cost_drop_out(fixture_catalog_path: Path) -> None:
    catalog = load_catalog(fixture_catalog_path)

    unrated = filter_restaurants(
        catalog,
        location="Koramangala 5th Block",
        cuisines=["italian"],
        budget="high",
        min_rating=0,
    )
    unpriced = filter_restaurants(
        catalog,
        location="Indiranagar",
        cuisines=["thai"],
        budget="low",
        min_rating=0,
    )

    assert unrated == []
    assert unpriced == []
    onesta = catalog.get(_restaurant_id(catalog, "Onesta"))
    thai = catalog.get(_restaurant_id(catalog, "Thai House"))
    assert onesta is not None and onesta.rating is None and onesta.cost_for_two == 1200
    assert thai is not None and thai.cost_for_two is None


def test_indexes_point_at_the_same_restaurants(fixture_catalog_path: Path) -> None:
    catalog = load_catalog(fixture_catalog_path)
    jalsa = next(restaurant for restaurant in catalog.restaurants if restaurant.address == JALSA_ADDRESS)

    assert catalog.get(jalsa.id) == jalsa
    assert jalsa in catalog.by_location["banashankari"]
    assert jalsa in catalog.by_cuisine["continental"]
    assert jalsa in catalog.by_cuisine["north indian"]
    assert "koramangala" not in catalog.by_location
    assert catalog.by_location["koramangala 5th block"]


def _ids(catalog: Catalog, **overrides: object) -> set[str]:
    arguments = {
        "location": "Banashankari",
        "cuisines": ["north indian"],
        "budget": "medium",
        "min_rating": 0,
    }
    arguments.update(overrides)
    return {restaurant.id for restaurant in filter_restaurants(catalog, **arguments)}


def _restaurant(restaurant_id: str, **overrides: object) -> Restaurant:
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
        "dish_liked": "",
        "online_order": False,
        "book_table": False,
        "url": "",
    }
    values.update(overrides)
    return Restaurant(**values)


def _restaurant_id(catalog: Catalog, name: str) -> str:
    matches = [restaurant.id for restaurant in catalog.restaurants if restaurant.name == name]
    assert len(matches) == 1
    return matches[0]
