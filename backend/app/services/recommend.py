"""Filter, shortlist, ask the model to rank, and fall back to selector order."""

from __future__ import annotations

import logging
import time

from app.schemas.llm import LlmRanking, parse_ranking
from app.schemas.request import RecommendationRequest
from app.schemas.response import Recommendation, RecommendationResponse
from app.services.catalog import Catalog, Restaurant, normalize_location
from app.services.filter import filter_restaurants
from app.services.guard import apply_guard
from app.services.llm_client import LlmClient, LlmCompletion, build_llm_client
from app.services.prompt import build_messages, prompt_rows
from app.services.select import select_candidates

logger = logging.getLogger(__name__)


def recommend(
    catalog: Catalog,
    request: RecommendationRequest,
    *,
    client: LlmClient | None = None,
) -> RecommendationResponse:
    """Return up to `limit` cards.

    Zero matches skip the model. A provider failure, or output with no valid ids,
    still returns the selector-ordered cards with reasons omitted.
    """
    location = _display_location(catalog, request.location)
    matches = filter_restaurants(
        catalog,
        location=request.location,
        cuisines=request.cuisines,
        budget=request.budget,
        min_rating=request.min_rating,
    )
    if not matches:
        return RecommendationResponse(
            summary=f"No restaurants in {location} match those filters.",
            explanations="skipped",
            matched_count=0,
            recommendations=[],
        )

    shortlist = select_candidates(matches)
    llm = client if client is not None else build_llm_client()
    messages = build_messages(request, shortlist)
    started = time.perf_counter()
    completion: LlmCompletion | None = None
    ranking = None
    try:
        completion = llm.complete(messages)
        ranking = parse_ranking(completion.content)
        _restore_catalog_ids(ranking, shortlist)
    except Exception:
        ranking = None
    latency_ms = (time.perf_counter() - started) * 1000
    guarded = None if ranking is None else apply_guard(ranking, shortlist, limit=request.limit)
    fallback = guarded is None
    _log_model_call(latency_ms=latency_ms, fallback=fallback, completion=completion)

    if guarded is None or ranking is None:
        return _unavailable(location, len(matches), shortlist[: request.limit])

    return RecommendationResponse(
        summary=ranking.summary,
        explanations="available",
        matched_count=len(matches),
        recommendations=[_recommendation(restaurant, reason) for restaurant, reason in guarded],
    )


def _restore_catalog_ids(ranking: LlmRanking, shortlist: list[Restaurant]) -> None:
    aliases = {alias: restaurant.id for alias, restaurant in prompt_rows(shortlist)}
    for item in ranking.recommendations:
        item.id = aliases.get(item.id, item.id)


def _unavailable(
    location: str,
    matched_count: int,
    chosen: list[Restaurant],
) -> RecommendationResponse:
    return RecommendationResponse(
        summary=(
            "Explanations are temporarily unavailable. "
            f"These are the highest-rated matches in {location}."
        ),
        explanations="unavailable",
        matched_count=matched_count,
        recommendations=[_recommendation(restaurant, None) for restaurant in chosen],
    )


def _log_model_call(
    *,
    latency_ms: float,
    fallback: bool,
    completion: LlmCompletion | None,
) -> None:
    fallback_label = "true" if fallback else "false"
    if completion is not None and (
        completion.prompt_tokens is not None or completion.completion_tokens is not None
    ):
        logger.info(
            "model call latency_ms=%.0f fallback=%s prompt_tokens=%s completion_tokens=%s",
            latency_ms,
            fallback_label,
            completion.prompt_tokens,
            completion.completion_tokens,
        )
        return
    logger.info("model call latency_ms=%.0f fallback=%s", latency_ms, fallback_label)


def _display_location(catalog: Catalog, location: str) -> str:
    key = normalize_location(location)
    names = [name for name in catalog.locations() if normalize_location(name) == key]
    if location in names:
        return location
    if names:
        return sorted(names)[0]
    return location


def _recommendation(restaurant: Restaurant, reason: str | None) -> Recommendation:
    return Recommendation(
        id=restaurant.id,
        name=restaurant.name,
        cuisines=restaurant.cuisines,
        location=restaurant.location,
        rating=restaurant.rating,
        votes=restaurant.votes,
        cost_for_two=restaurant.cost_for_two,
        rest_type=restaurant.rest_type,
        reason=reason,
    )
