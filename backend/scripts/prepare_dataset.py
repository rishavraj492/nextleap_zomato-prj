"""Clean raw Zomato rows into one restaurant per name and address.

The default source is the checked-in fixture, which needs no network:

    python scripts/prepare_dataset.py --source fixture

``--source huggingface`` downloads ManikaSaini/zomato-restaurant-recommendation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import pandas as pd

HF_DATASET_ID = "ManikaSaini/zomato-restaurant-recommendation"
DISH_LIKED_MAX_CHARS = 200

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = BACKEND_ROOT / "data" / "fixtures" / "zomato_sample.csv"
DEFAULT_PARQUET_PATH = BACKEND_ROOT / "data" / "restaurants.parquet"
DEFAULT_FACETS_PATH = BACKEND_ROOT / "data" / "facets.json"

SOURCE_COLUMNS = [
    "url",
    "address",
    "name",
    "online_order",
    "book_table",
    "rate",
    "votes",
    "phone",
    "location",
    "rest_type",
    "dish_liked",
    "cuisines",
    "approx_cost(for two people)",
    "reviews_list",
    "menu_item",
    "listed_in(type)",
    "listed_in(city)",
]

CATALOG_COLUMNS = [
    "id",
    "name",
    "address",
    "location",
    "cuisines",
    "cuisine_tokens",
    "rating",
    "votes",
    "cost_for_two",
    "rest_type",
    "listed_types",
    "dish_liked",
    "online_order",
    "book_table",
    "url",
]

_COST_DIGITS = re.compile(r"^\d+$")
_MISSING_RATING = {"new", "-", "nan", "none"}


def restaurant_id(name: str, address: str) -> str:
    """Stable id for a restaurant. Same name and address always hash the same."""
    payload = f"{name}\0{address}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_rating(value: object) -> float | None:
    """Parse ``4.1/5``. ``NEW``, ``-``, blanks, and other non-numeric text become null."""
    if _is_missing(value):
        return None
    text = str(value).strip()
    if text.lower() in _MISSING_RATING:
        return None
    if "/" in text:
        text = text.split("/", 1)[0].strip()
    if text == "" or text.lower() in _MISSING_RATING:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_cost(value: object) -> int | None:
    """Parse a cost for two. Commas are stripped. Non-numeric values become null."""
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            return None
        return int(value)
    text = str(value).strip().replace(",", "")
    if not _COST_DIGITS.fullmatch(text):
        return None
    return int(text)


def parse_votes(value: object) -> int:
    """Votes are a non-negative integer. Missing or non-numeric values count as 0."""
    if isinstance(value, bool) or _is_missing(value):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            return 0
        return int(value)
    text = str(value).strip().replace(",", "")
    if not _COST_DIGITS.fullmatch(text):
        return 0
    return int(text)


def parse_cuisines(value: object) -> tuple[str, list[str]]:
    """Keep the display string. Tokens are trimmed and lowercased."""
    if _is_missing(value):
        return "", []
    display = str(value).strip()
    if display == "":
        return "", []
    tokens: list[str] = []
    seen: set[str] = set()
    for part in display.split(","):
        token = part.strip().lower()
        if token == "" or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return display, tokens


def parse_yes_no(value: object) -> bool:
    """``Yes`` is true. ``No`` and every other value are false."""
    if _is_missing(value):
        return False
    return str(value).strip().lower() == "yes"


def truncate_dish_liked(value: object) -> str:
    """Shorten liked dishes so prompts stay small. Null becomes an empty string."""
    if _is_missing(value):
        return ""
    return str(value).strip()[:DISH_LIKED_MAX_CHARS]


def prepare_catalog(frame: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate on name + address and return the catalog columns."""
    _require_columns(frame)
    grouped: dict[tuple[str, str], list[tuple[int, dict[str, object]]]] = {}

    for index, record in enumerate(frame.to_dict(orient="records")):
        name = _clean_text(record.get("name"))
        address = _clean_text(record.get("address"))
        if name == "" or address == "":
            continue
        display, tokens = parse_cuisines(record.get("cuisines"))
        parsed = {
            "name": name,
            "address": address,
            "location": _clean_text(record.get("location")),
            "cuisines": display,
            "cuisine_tokens": tokens,
            "rating": parse_rating(record.get("rate")),
            "votes": parse_votes(record.get("votes")),
            "cost_for_two": parse_cost(record.get("approx_cost(for two people)")),
            "rest_type": _clean_text(record.get("rest_type")),
            "listed_type": _clean_text(record.get("listed_in(type)")),
            "dish_liked": truncate_dish_liked(record.get("dish_liked")),
            "online_order": parse_yes_no(record.get("online_order")),
            "book_table": parse_yes_no(record.get("book_table")),
            "url": _clean_text(record.get("url")),
        }
        grouped.setdefault((name, address), []).append((index, parsed))

    restaurants: list[dict[str, object]] = []
    for (name, address), rows in grouped.items():
        rows.sort(key=lambda item: item[0])
        _, winner = min(rows, key=lambda item: (-int(item[1]["votes"]), item[0]))
        tokens: list[str] = []
        seen_tokens: set[str] = set()
        listed_types: list[str] = []
        seen_types: set[str] = set()
        for _, parsed in rows:
            for token in parsed["cuisine_tokens"]:
                if token not in seen_tokens:
                    seen_tokens.add(token)
                    tokens.append(token)
            listed_type = str(parsed["listed_type"])
            if listed_type != "" and listed_type not in seen_types:
                seen_types.add(listed_type)
                listed_types.append(listed_type)
        tokens.sort()
        listed_types.sort()
        restaurants.append(
            {
                "id": restaurant_id(name, address),
                "name": winner["name"],
                "address": winner["address"],
                "location": winner["location"],
                "cuisines": winner["cuisines"],
                "cuisine_tokens": tokens,
                "rating": winner["rating"],
                "votes": winner["votes"],
                "cost_for_two": winner["cost_for_two"],
                "rest_type": winner["rest_type"],
                "listed_types": listed_types,
                "dish_liked": winner["dish_liked"],
                "online_order": winner["online_order"],
                "book_table": winner["book_table"],
                "url": winner["url"],
            }
        )

    catalog = pd.DataFrame(restaurants, columns=CATALOG_COLUMNS)
    if catalog.empty:
        catalog["rating"] = pd.Series(dtype="Float64")
        catalog["cost_for_two"] = pd.Series(dtype="Int64")
        catalog["votes"] = pd.Series(dtype="int64")
        return catalog

    catalog["rating"] = catalog["rating"].astype("Float64")
    catalog["cost_for_two"] = catalog["cost_for_two"].astype("Int64")
    catalog["votes"] = catalog["votes"].astype("int64")
    catalog["online_order"] = catalog["online_order"].astype(bool)
    catalog["book_table"] = catalog["book_table"].astype(bool)
    catalog = catalog.sort_values(["name", "address"], kind="mergesort").reset_index(drop=True)
    return catalog


def build_facets(catalog: pd.DataFrame) -> dict[str, list[str]]:
    """Sorted unique locations and cuisine tokens for the preference form."""
    locations = sorted({str(value) for value in catalog["location"] if str(value).strip() != ""})
    cuisines: set[str] = set()
    for tokens in catalog["cuisine_tokens"]:
        cuisines.update(str(token) for token in tokens if str(token).strip() != "")
    return {"locations": locations, "cuisines": sorted(cuisines)}


def load_source(source: str) -> pd.DataFrame:
    if source == "fixture":
        return pd.read_csv(FIXTURE_PATH, dtype=str, keep_default_na=False)
    if source == "huggingface":
        return _load_huggingface()
    raise ValueError(f"Unknown source {source!r}. Use 'fixture' or 'huggingface'.")


def write_catalog(catalog: pd.DataFrame, parquet_path: Path, facets_path: Path) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    facets_path.parent.mkdir(parents=True, exist_ok=True)
    catalog.to_parquet(parquet_path, index=False)
    facets = build_facets(catalog)
    facets_path.write_text(json.dumps(facets, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare the restaurant catalog.")
    parser.add_argument(
        "--source",
        choices=("fixture", "huggingface"),
        default="fixture",
        help="fixture reads the checked-in CSV (default). huggingface downloads the Zomato dataset.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_PARQUET_PATH)
    parser.add_argument("--facets", type=Path, default=DEFAULT_FACETS_PATH)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    catalog = prepare_catalog(load_source(args.source))
    write_catalog(catalog, args.output, args.facets)
    print(f"Wrote {len(catalog)} restaurants to {args.output}")
    print(f"Wrote facets to {args.facets}")


def _load_huggingface() -> pd.DataFrame:
    from datasets import load_dataset

    dataset = load_dataset(HF_DATASET_ID, split="train")
    return dataset.to_pandas()


def _require_columns(frame: pd.DataFrame) -> None:
    missing = [column for column in SOURCE_COLUMNS if column not in frame.columns]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Dataset is missing columns: {joined}")


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _clean_text(value: object) -> str:
    if _is_missing(value):
        return ""
    return str(value).strip()


if __name__ == "__main__":
    main()
