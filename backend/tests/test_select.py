from app.config import CANDIDATE_CAP, MEDIUM_BUDGET_MIN, RESULT_CAP
from app.schemas.request import RecommendationRequest
from app.services.catalog import Catalog, Restaurant
from app.services.recommend import recommend
from app.services.select import select_candidates


def test_sorts_by_rating_then_votes_then_name() -> None:
    restaurants = [
        _restaurant("low-rating", rating=3.0, votes=999, name="Zebra"),
        _restaurant("fewer-votes", rating=4.5, votes=10, name="Mango"),
        _restaurant("more-votes", rating=4.5, votes=40, name="Zebra"),
        _restaurant("later-name", rating=4.5, votes=10, name="Mango Cafe"),
        _restaurant("earlier-name", rating=4.5, votes=10, name="Apple"),
    ]

    ordered = [restaurant.id for restaurant in select_candidates(restaurants)]

    assert ordered == [
        "more-votes",
        "earlier-name",
        "fewer-votes",
        "later-name",
        "low-rating",
    ]


def test_same_input_returns_the_same_order() -> None:
    restaurants = [
        _restaurant("b", rating=4.0, votes=5, name="B"),
        _restaurant("a", rating=4.0, votes=5, name="A"),
        _restaurant("c", rating=4.2, votes=1, name="C"),
    ]

    first = [restaurant.id for restaurant in select_candidates(list(reversed(restaurants)))]
    second = [restaurant.id for restaurant in select_candidates(restaurants)]

    assert first == second == ["c", "a", "b"]


def test_null_rating_sorts_last_and_cap_keeps_the_top() -> None:
    restaurants = [
        _restaurant(f"r{index:02d}", rating=float(index), votes=index, name=f"Place {index:02d}")
        for index in range(CANDIDATE_CAP + 5)
    ]
    restaurants.append(_restaurant("unrated", rating=None, votes=10_000, name="AAA"))

    selected = select_candidates(restaurants)

    assert len(selected) == CANDIDATE_CAP
    assert selected[0].id == f"r{CANDIDATE_CAP + 4:02d}"
    assert "unrated" not in {restaurant.id for restaurant in selected}
    assert [restaurant.rating for restaurant in selected] == sorted(
        (restaurant.rating for restaurant in selected),
        reverse=True,
    )


def test_matched_count_is_every_match_and_the_list_is_capped() -> None:
    total = CANDIDATE_CAP + 8
    catalog = Catalog(
        [
            _restaurant(
                f"r{index:02d}",
                rating=5 - (index * 0.01),
                votes=100 - index,
                name=f"Place {index:02d}",
            )
            for index in range(total)
        ]
    )
    request = RecommendationRequest(
        location="Banashankari",
        budget="medium",
        cuisines=["north indian"],
        minRating=0,
        limit=RESULT_CAP,
    )

    response = recommend(catalog, request)

    assert response.matched_count == total
    assert response.explanations == "unavailable"
    assert len(response.recommendations) == RESULT_CAP
    assert [item.name for item in response.recommendations] == [f"Place {index:02d}" for index in range(RESULT_CAP)]
    assert all(item.reason is None for item in response.recommendations)


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
        "dish_liked": "Biryani",
        "online_order": False,
        "book_table": False,
        "url": "https://example.test",
    }
    values.update(overrides)
    return Restaurant(**values)
