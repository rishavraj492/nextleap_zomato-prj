import json
import logging
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import CANDIDATE_CAP, LLM_MAX_OUTPUT_TOKENS, LLM_REASONING_EFFORT, RESULT_CAP, Settings
from app.main import app
from app.schemas.request import RecommendationRequest
from app.services.catalog import Catalog, load_catalog
from app.services.llm_client import TEMPERATURE, ChatCompletionsClient, LlmCompletion, LlmError
from app.services.prompt import LIKED_DISHES_MAX_CHARS, SYSTEM_PROMPT, build_messages
from app.services.recommend import recommend
from tests.support import ExplodingClient, FakeClient, ranking_json, restaurant

SECRET_KEY = "super-secret-groq-key"
PROMPT_SENTINEL = "family-friendly-sentinel"
PHONE_SENTINEL = "PHONE-08042297555"
REVIEW_SENTINEL = "Loved the pasta review text"


def test_valid_ids_follow_model_order_with_reasons_and_summary() -> None:
    places = [
        restaurant("high", name="High", rating=4.9, votes=50),
        restaurant("mid", name="Mid", rating=4.5, votes=40),
        restaurant("low", name="Low", rating=4.1, votes=30),
    ]
    client = FakeClient(
        ranking_json(["low", "high"], summary="Two good rooms."),
        prompt_tokens=12,
        completion_tokens=8,
    )

    response = recommend(Catalog(places), _request(limit=2, preferences=PROMPT_SENTINEL), client=client)

    assert response.explanations == "available"
    assert response.summary == "Two good rooms."
    assert response.matched_count == 3
    assert [(card.id, card.reason) for card in response.recommendations] == [
        ("low", "Because low."),
        ("high", "Because high."),
    ]
    assert response.recommendations[0].name == "Low"
    assert response.recommendations[0].rating == 4.1


def test_prompt_has_at_most_twenty_shortlist_ids_and_no_private_fields() -> None:
    total = CANDIDATE_CAP + 5
    places = [
        restaurant(
            f"r{index:02d}",
            name=f"Place {index:02d}",
            rating=5 - (index * 0.01),
            votes=200 - index,
            url=f"https://example.test/{PHONE_SENTINEL}",
            address=REVIEW_SENTINEL,
            dish_liked="D" * (LIKED_DISHES_MAX_CHARS + 30),
        )
        for index in range(total)
    ]
    client = FakeClient(ranking_json(["r00"]))

    recommend(Catalog(places), _request(preferences="   "), client=client)

    assert len(client.messages) == 1
    messages = client.messages[0]
    assert [message["role"] for message in messages] == ["system", "user"]
    assert messages[0]["content"] == SYSTEM_PROMPT
    for phrase in (
        "Rank only supplied ids",
        "free-text preference",
        "Rating and cost already match",
        "One short sentence",
        "cuisine, cost, rest type, or liked dishes",
        "Do not invent dishes, reviews, or awards",
        "JSON only",
    ):
        assert phrase in SYSTEM_PROMPT

    payload = json.loads(messages[1]["content"])
    assert payload["preference"] == "none"
    assert payload["location"] == "Banashankari"
    assert payload["budget"] == "medium"
    assert payload["cuisines"] == ["north indian"]
    assert "minRating" not in payload
    ids = [row["id"] for row in payload["restaurants"]]
    assert ids == [str(index) for index in range(1, CANDIDATE_CAP + 1)]
    assert len(ids) == CANDIDATE_CAP
    record = payload["restaurants"][0]
    assert set(record) == {"id", "name", "cuisines", "cost", "type", "dishes"}
    assert record["dishes"] == "D" * LIKED_DISHES_MAX_CHARS
    assert ": " not in messages[1]["content"]
    serialized = messages[1]["content"]
    assert PHONE_SENTINEL not in serialized
    assert REVIEW_SENTINEL not in serialized
    assert "reviews" not in serialized


def test_fewer_model_picks_are_not_padded_and_empty_summary_is_kept() -> None:
    places = [restaurant("a", rating=4.8), restaurant("b", rating=4.2)]
    client = FakeClient(ranking_json(["b"], summary=""))

    response = recommend(Catalog(places), _request(), client=client)

    assert response.summary == ""
    assert response.explanations == "available"
    assert [card.id for card in response.recommendations] == ["b"]


def test_client_exception_timeout_http_error_and_prose_keep_selector_order() -> None:
    places = [
        restaurant("b", name="B", rating=4.0, votes=5),
        restaurant("a", name="A", rating=4.8, votes=5),
    ]
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    http_error = httpx.HTTPStatusError(
        "server error",
        request=request,
        response=httpx.Response(500, request=request),
    )
    failures: list[FakeClient | ExplodingClient] = [
        ExplodingClient(RuntimeError("provider down")),
        ExplodingClient(httpx.TimeoutException("timed out")),
        ExplodingClient(http_error),
        FakeClient("Here are a few restaurants you may like."),
        FakeClient("```json\n" + ranking_json(["b", "a"]) + "\n```"),
        FakeClient(ranking_json(["not-a-real-id"])),
        FakeClient(json.dumps({"summary": "Empty.", "recommendations": []})),
    ]

    for client in failures:
        response = recommend(Catalog(places), _request(), client=client)
        assert response.explanations == "unavailable"
        assert response.matched_count == 2
        assert [card.name for card in response.recommendations] == ["A", "B"]
        assert all(card.reason is None for card in response.recommendations)
        assert response.summary == (
            "Explanations are temporarily unavailable. "
            "These are the highest-rated matches in Banashankari."
        )


def test_zero_matches_never_call_the_client() -> None:
    client = ExplodingClient(AssertionError("model must not be called"))
    catalog = Catalog([restaurant("a", rating=3.0)])

    response = recommend(
        catalog,
        _request(location="Indiranagar", minRating=4),
        client=client,
    )

    assert client.calls == 0
    assert response.explanations == "skipped"
    assert response.matched_count == 0
    assert response.recommendations == []
    assert response.summary == "No restaurants in Indiranagar match those filters."


def test_logs_latency_tokens_and_fallback_without_the_key_or_prompt(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    places = [restaurant("a", name="A", rating=4.5)]
    client = FakeClient(ranking_json(["a"], summary="One pick."), prompt_tokens=15, completion_tokens=4)

    recommend(Catalog(places), _request(preferences=PROMPT_SENTINEL), client=client)
    text = caplog.text
    assert "fallback=false" in text
    assert "latency_ms=" in text
    assert "prompt_tokens=15" in text
    assert "completion_tokens=4" in text
    assert PROMPT_SENTINEL not in text
    assert SECRET_KEY not in text

    caplog.clear()
    recommend(Catalog(places), _request(preferences=PROMPT_SENTINEL), client=ExplodingClient(LlmError("nope")))
    assert "fallback=true" in caplog.text
    assert PROMPT_SENTINEL not in caplog.text


def test_chat_client_posts_groq_schema_and_logs_usage(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caplog.set_level(logging.INFO)
    captured: dict[str, object] = {}
    content = ranking_json(["a"], summary="From the wire.")

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 21, "completion_tokens": 9},
            },
        )

    seen_timeout: dict[str, httpx.Timeout] = {}
    real_client = httpx.Client

    class SpyClient(real_client):
        def __init__(self, *args: object, **kwargs: object) -> None:
            seen_timeout["timeout"] = kwargs["timeout"]  # type: ignore[assignment]
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("app.services.llm_client.httpx.Client", SpyClient)
    settings = _settings(llm_api_key=SECRET_KEY, llm_timeout_seconds=7)
    completion = ChatCompletionsClient(settings, transport=httpx.MockTransport(handler)).complete(
        build_messages(_request(preferences=PROMPT_SENTINEL), [restaurant("a")])
    )

    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["authorization"] == f"Bearer {SECRET_KEY}"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "openai/gpt-oss-20b"
    assert body["temperature"] == TEMPERATURE
    assert body["max_tokens"] == LLM_MAX_OUTPUT_TOKENS
    assert body["reasoning_effort"] == LLM_REASONING_EFFORT
    assert "top_p" not in body
    assert "logprobs" not in body
    assert "logit_bias" not in body
    assert "top_logprobs" not in body
    assert "n" not in body
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["name"] == "recommendations"
    assert [set(message) for message in body["messages"]] == [{"role", "content"}, {"role", "content"}]
    assert completion.content == content
    assert completion.prompt_tokens == 21
    assert completion.completion_tokens == 9
    assert seen_timeout["timeout"].read == 7
    assert "prompt_tokens=21" in caplog.text
    assert "completion_tokens=9" in caplog.text
    assert SECRET_KEY not in caplog.text
    assert PROMPT_SENTINEL not in caplog.text


def test_missing_key_and_provider_errors_do_not_call_out_or_leak_the_key() -> None:
    called = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        called["count"] += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    client = ChatCompletionsClient(
        _settings(llm_api_key="  "),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(LlmError):
        client.complete([{"role": "user", "content": "hi"}])
    assert called["count"] == 0

    def refuse(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    failing = ChatCompletionsClient(
        _settings(llm_api_key=SECRET_KEY, llm_base_url="https://api.groq.com/openai/v1/"),
        transport=httpx.MockTransport(refuse),
    )
    with pytest.raises(LlmError) as caught:
        failing.complete([{"role": "user", "content": PROMPT_SENTINEL}])
    assert SECRET_KEY not in str(caught.value)
    assert PROMPT_SENTINEL not in str(caught.value)

    def server_error(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "slow down"})

    limited = ChatCompletionsClient(_settings(llm_api_key=SECRET_KEY), transport=httpx.MockTransport(server_error))
    with pytest.raises(LlmError) as limited_error:
        limited.complete([{"role": "user", "content": "hi"}])
    assert SECRET_KEY not in str(limited_error.value)


def test_api_uses_model_order_when_a_client_returns_valid_ids(fixture_catalog_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    catalog = load_catalog(fixture_catalog_path)

    class ReversingClient:
        def complete(self, messages: list[dict[str, str]]):
            payload = json.loads(messages[1]["content"])
            ids = [row["id"] for row in reversed(payload["restaurants"])]
            return LlmCompletion(
                ranking_json(ids, summary="Reversed by the model."),
                prompt_tokens=3,
                completion_tokens=2,
            )

    monkeypatch.setattr("app.services.recommend.build_llm_client", lambda: ReversingClient())

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
    assert body["explanations"] == "available"
    assert body["summary"] == "Reversed by the model."
    assert body["matchedCount"] == 2
    assert [card["name"] for card in body["recommendations"]] == ["Spice Elephant", "Jalsa"]
    jalsa = next(card for card in body["recommendations"] if card["name"] == "Jalsa")
    stored = next(
        row
        for row in catalog.restaurants
        if row.name == "Jalsa" and row.location == "Koramangala 5th Block"
    )
    assert jalsa["rating"] == stored.rating
    assert jalsa["costForTwo"] == stored.cost_for_two
    assert jalsa["reason"] == "Because 1."
    assert jalsa["id"] == stored.id


def _request(**overrides: object) -> RecommendationRequest:
    values: dict[str, object] = {
        "location": "Banashankari",
        "budget": "medium",
        "cuisines": ["north indian"],
        "minRating": 0,
        "limit": RESULT_CAP,
    }
    values.update(overrides)
    return RecommendationRequest(**values)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "catalog_path": Path("unused.parquet"),
        "llm_api_key": "",
        "llm_base_url": "https://api.groq.com/openai/v1",
        "llm_model": "openai/gpt-oss-20b",
        "llm_timeout_seconds": 20,
    }
    values.update(overrides)
    return Settings(**values)
