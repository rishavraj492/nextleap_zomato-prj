import json

from app.config import MEDIUM_BUDGET_MIN, REASON_MAX_CHARS, RESULT_CAP
from app.schemas.llm import LlmRanking, groq_json_schema, groq_response_format, parse_ranking
from app.schemas.request import RecommendationRequest
from app.services.catalog import Catalog, Restaurant
from app.services.guard import apply_guard, cap_reason
from app.services.recommend import recommend
from tests.support import FakeClient, restaurant


def test_groq_schema_marks_every_property_required() -> None:
    schema = groq_json_schema()
    item = schema["properties"]["recommendations"]["items"]

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"summary", "recommendations"}
    assert set(schema["properties"]) == {"summary", "recommendations"}
    assert item["additionalProperties"] is False
    assert set(item["required"]) == {"id", "reason"}
    assert set(item["properties"]) == {"id", "reason"}

    response_format = groq_response_format()
    assert response_format == {
        "type": "json_schema",
        "json_schema": {
            "name": "recommendations",
            "strict": True,
            "schema": schema,
        },
    }


def test_parser_keeps_summary_and_reasons_and_drops_echoed_facts() -> None:
    ranking = parse_ranking(
        json.dumps(
            {
                "summary": "A quiet pair.",
                "extra": "ignore me",
                "recommendations": [
                    {
                        "id": "alpha",
                        "reason": "Fits the preference.",
                        "name": "Not Real",
                        "rating": 1.0,
                        "costForTwo": 1,
                    }
                ],
            }
        )
    )

    assert ranking.summary == "A quiet pair."
    assert [(item.id, item.reason) for item in ranking.recommendations] == [
        ("alpha", "Fits the preference.")
    ]
    assert not hasattr(ranking.recommendations[0], "rating")


def test_unknown_and_duplicate_ids_are_dropped_and_reasons_are_capped() -> None:
    shortlist = [
        restaurant("alpha", name="Alpha", rating=4.8),
        restaurant("beta", name="Beta", rating=4.4),
        restaurant("gamma", name="Gamma", rating=4.2),
    ]
    long_reason = "y" * (REASON_MAX_CHARS + 40)
    ranking = LlmRanking.model_validate(
        {
            "summary": "Reordered.",
            "recommendations": [
                {"id": "missing", "reason": "nope"},
                {"id": "gamma", "reason": long_reason},
                {"id": "gamma", "reason": "second copy"},
                {"id": "alpha", "reason": None},
                {"id": "beta", "reason": "Kept."},
            ],
        }
    )

    guarded = apply_guard(ranking, shortlist, limit=RESULT_CAP)

    assert guarded is not None
    assert [(row.id, reason) for row, reason in guarded] == [
        ("gamma", "y" * REASON_MAX_CHARS),
        ("alpha", None),
        ("beta", "Kept."),
    ]
    assert cap_reason("short") == "short"
    assert cap_reason(None) is None


def test_limit_is_applied_after_invalid_ids_are_removed() -> None:
    shortlist = [restaurant(f"r{index}") for index in range(6)]
    ranking = LlmRanking.model_validate(
        {
            "summary": "Many.",
            "recommendations": [{"id": "nope", "reason": "x"}]
            + [{"id": restaurant_row.id, "reason": f"Because {restaurant_row.id}"} for restaurant_row in shortlist],
        }
    )

    guarded = apply_guard(ranking, shortlist, limit=2)

    assert guarded is not None
    assert [row.id for row, _reason in guarded] == ["r0", "r1"]


def test_empty_or_all_invalid_ids_have_no_guarded_rows() -> None:
    shortlist = [restaurant("alpha")]
    empty = LlmRanking.model_validate({"summary": "Nothing.", "recommendations": []})
    invalid = LlmRanking.model_validate(
        {"summary": "Wrong place.", "recommendations": [{"id": "other", "reason": "no"}]}
    )

    assert apply_guard(empty, shortlist, limit=5) is None
    assert apply_guard(invalid, shortlist, limit=5) is None


def test_catalog_fields_win_over_anything_echoed_by_the_model() -> None:
    chosen = restaurant(
        "alpha",
        name="Real Name",
        rating=4.6,
        votes=80,
        cost_for_two=MEDIUM_BUDGET_MIN,
        cuisines="North Indian",
        location="Banashankari",
        rest_type="Casual Dining",
    )
    other = restaurant("beta", name="Other", rating=4.2, votes=10)
    catalog = Catalog([chosen, other])
    payload = {
        "summary": "Model summary.",
        "recommendations": [
            {
                "id": "beta",
                "reason": "Second.",
                "name": "Echoed Other",
                "rating": 1.1,
                "votes": 1,
                "costForTwo": 9,
                "location": "Delhi",
                "restType": "Bar",
                "cuisines": "Thai",
            },
            {
                "id": "alpha",
                "reason": "First pick.",
                "name": "Echoed Name",
                "rating": 0.2,
                "votes": 0,
                "costForTwo": 1,
                "location": "Delhi",
                "restType": "Pub",
                "cuisines": "Thai",
            },
        ],
    }
    client = FakeClient(json.dumps(payload))

    response = recommend(catalog, _request(limit=1), client=client)

    assert response.explanations == "available"
    assert response.summary == "Model summary."
    assert len(response.recommendations) == 1
    card = response.recommendations[0]
    assert card.id == "beta"
    assert card.reason == "Second."
    assert card.name == "Other"
    assert card.rating == 4.2
    assert card.votes == 10
    assert card.cost_for_two == MEDIUM_BUDGET_MIN
    assert card.location == "Banashankari"
    assert card.rest_type == "Casual Dining"
    assert card.cuisines == "North Indian"


def _request(**overrides: object) -> RecommendationRequest:
    values: dict[str, object] = {
        "location": "Banashankari",
        "budget": "medium",
        "cuisines": ["north indian"],
        "minRating": 0,
    }
    values.update(overrides)
    return RecommendationRequest(**values)
