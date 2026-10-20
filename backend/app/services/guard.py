"""Keep only shortlist ids, and copy display fields from the catalog."""

from __future__ import annotations

from app.config import REASON_MAX_CHARS
from app.schemas.llm import LlmRanking
from app.services.catalog import Restaurant


def apply_guard(
    ranking: LlmRanking,
    shortlist: list[Restaurant],
    *,
    limit: int,
) -> list[tuple[Restaurant, str | None]] | None:
    """Return catalog rows in model order.

    Unknown and duplicate ids are dropped. Reasons are length-capped.
    `None` means no usable id remained, so the caller should use selector order.
    """
    if limit < 1:
        return None
    by_id = {restaurant.id: restaurant for restaurant in shortlist}
    seen: set[str] = set()
    kept: list[tuple[Restaurant, str | None]] = []
    for item in ranking.recommendations:
        restaurant = by_id.get(item.id)
        if restaurant is None or item.id in seen:
            continue
        seen.add(item.id)
        kept.append((restaurant, cap_reason(item.reason)))
        if len(kept) >= limit:
            break
    if not kept:
        return None
    return kept


def cap_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    return reason[:REASON_MAX_CHARS]
