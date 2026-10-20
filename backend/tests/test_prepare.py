import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

from scripts.prepare_dataset import (
    CATALOG_COLUMNS,
    DISH_LIKED_MAX_CHARS,
    FIXTURE_PATH,
    SOURCE_COLUMNS,
    build_parser,
    load_source,
    parse_cost,
    parse_cuisines,
    parse_rating,
    parse_yes_no,
    prepare_catalog,
    restaurant_id,
    truncate_dish_liked,
    write_catalog,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
JALSA_ADDRESS = "942, 21st Main Road, Banashankari, Bangalore"
JALSA_OTHER_ADDRESS = "100, Koramangala 5th Block, Bangalore"


def test_fixture_has_source_columns_and_required_cases() -> None:
    frame = pd.read_csv(FIXTURE_PATH, dtype=str, keep_default_na=False)

    assert list(frame.columns) == SOURCE_COLUMNS
    jalsa = frame[frame["address"] == JALSA_ADDRESS]
    assert set(jalsa["listed_in(type)"]) == {"Delivery", "Dine-out"}
    assert set(frame["rate"]) >= {"4.1/5", "NEW", "-", ""}
    assert " 4.1/5 " in set(frame["rate"])
    assert set(frame["approx_cost(for two people)"]) >= {"300", "1,200", ""}
    multi = frame[frame["cuisines"] == "North Indian, Mughlai, Chinese"]
    assert len(multi) == 1
    assert (frame["cuisines"] == "").any()


def test_parse_rating() -> None:
    assert parse_rating("4.1/5") == 4.1
    assert parse_rating(" 4.1/5 ") == 4.1
    assert parse_rating("NEW") is None
    assert parse_rating("-") is None
    assert parse_rating("") is None
    assert parse_rating("   ") is None
    assert parse_rating(None) is None
    assert parse_rating("excellent") is None
    assert parse_rating("not/5") is None


def test_parse_cost() -> None:
    assert parse_cost("300") == 300
    assert parse_cost("1,200") == 1200
    assert parse_cost(" 1,200 ") == 1200
    assert parse_cost("") is None
    assert parse_cost("abc") is None
    assert parse_cost(None) is None


def test_cuisine_tokens_keep_display_casing_and_trim() -> None:
    display, tokens = parse_cuisines("North Indian, Mughlai, Chinese")
    assert display == "North Indian, Mughlai, Chinese"
    assert tokens == ["north indian", "mughlai", "chinese"]

    spaced_display, spaced_tokens = parse_cuisines(" Thai , South Indian ")
    assert spaced_display == "Thai , South Indian"
    assert spaced_tokens == ["thai", "south indian"]

    assert parse_cuisines(None) == ("", [])
    assert parse_cuisines("") == ("", [])


def test_yes_no_and_dish_liked() -> None:
    assert parse_yes_no("Yes") is True
    assert parse_yes_no("yes") is True
    assert parse_yes_no("No") is False
    assert parse_yes_no("Maybe") is False
    assert parse_yes_no("") is False
    assert truncate_dish_liked(None) == ""
    assert truncate_dish_liked("x" * (DISH_LIKED_MAX_CHARS + 50)) == "x" * DISH_LIKED_MAX_CHARS


def test_dedup_keeps_most_votes_and_unions_tokens_and_types() -> None:
    catalog = prepare_catalog(load_source("fixture"))
    jalsa = _row(catalog, "Jalsa", JALSA_ADDRESS)

    assert jalsa["votes"] == 775
    assert jalsa["rating"] == 4.1
    assert jalsa["cost_for_two"] == 800
    assert jalsa["location"] == "Banashankari"
    assert jalsa["rest_type"] == "Casual Dining"
    assert jalsa["cuisines"] == "North Indian, Mughlai, Chinese"
    assert jalsa["cuisine_tokens"] == ["chinese", "continental", "mughlai", "north indian"]
    assert jalsa["listed_types"] == ["Delivery", "Dine-out"]
    assert bool(jalsa["online_order"]) is True
    assert bool(jalsa["book_table"]) is True
    assert len(catalog[catalog["name"] == "Jalsa"]) == 2


def test_same_name_different_address_stays_separate() -> None:
    catalog = prepare_catalog(load_source("fixture"))
    banashankari = _row(catalog, "Jalsa", JALSA_ADDRESS)
    koramangala = _row(catalog, "Jalsa", JALSA_OTHER_ADDRESS)

    assert banashankari["id"] != koramangala["id"]
    assert koramangala["id"] == restaurant_id("Jalsa", JALSA_OTHER_ADDRESS)


def test_equal_votes_keep_the_earliest_row() -> None:
    catalog = prepare_catalog(load_source("fixture"))
    tie = _row(catalog, "Tie House", "1, MG Road, Bangalore")

    assert tie["votes"] == 20
    assert tie["rest_type"] == "Cafe"
    assert tie["rating"] == 4.0
    assert tie["cost_for_two"] == 600
    assert tie["cuisine_tokens"] == ["bar food", "cafe"]
    assert tie["listed_types"] == ["Desserts", "Drinks & nightlife"]


def test_null_rating_cost_and_cuisines() -> None:
    catalog = prepare_catalog(load_source("fixture"))

    onesta = _row(catalog, "Onesta", "90, Koramangala 5th Block, Bangalore")
    assert pd.isna(onesta["rating"])
    assert onesta["cost_for_two"] == 1200
    assert onesta["rest_type"] == "Cafe, Casual Dining"
    assert onesta["cuisine_tokens"] == ["italian", "pizza"]

    adda = _row(catalog, "Adda", "100, 100 Feet Road, Indiranagar, Bangalore")
    assert pd.isna(adda["rating"])
    assert pd.isna(adda["cost_for_two"])
    assert adda["cuisines"] == ""
    assert adda["cuisine_tokens"] == []

    thai = _row(catalog, "Thai House", "12, Indiranagar 100 Feet Road, Bangalore")
    assert pd.isna(thai["rating"])
    assert pd.isna(thai["cost_for_two"])
    assert thai["cuisine_tokens"] == ["south indian", "thai"]
    assert bool(thai["online_order"]) is False
    assert bool(thai["book_table"]) is False

    bad = _row(catalog, "Bad Rate", "3, Whitefield Main Road, Bangalore")
    assert pd.isna(bad["rating"])
    assert bad["cost_for_two"] == 250


def test_stable_ids_across_runs() -> None:
    frame = load_source("fixture")
    first = prepare_catalog(frame)
    second = prepare_catalog(frame)

    assert first["id"].tolist() == second["id"].tolist()
    jalsa_id = restaurant_id("Jalsa", JALSA_ADDRESS)
    assert _row(first, "Jalsa", JALSA_ADDRESS)["id"] == jalsa_id
    assert _row(second, "Jalsa", JALSA_ADDRESS)["id"] == jalsa_id


def test_dropped_fields_and_truncated_dishes(tmp_path: Path) -> None:
    catalog = prepare_catalog(load_source("fixture"))
    long_menu = _row(catalog, "Long Menu", "9, Jayanagar 4th Block, Bangalore")
    raw = pd.read_csv(FIXTURE_PATH, dtype=str, keep_default_na=False)
    raw_dish = raw.loc[raw["name"] == "Long Menu", "dish_liked"].iloc[0]

    assert len(raw_dish) > DISH_LIKED_MAX_CHARS
    assert long_menu["dish_liked"] == raw_dish.strip()[:DISH_LIKED_MAX_CHARS]
    assert _row(catalog, "Adda", "100, 100 Feet Road, Indiranagar, Bangalore")["dish_liked"] == ""

    parquet_path = tmp_path / "restaurants.parquet"
    facets_path = tmp_path / "facets.json"
    write_catalog(catalog, parquet_path, facets_path)
    stored = pd.read_parquet(parquet_path)

    assert list(stored.columns) == CATALOG_COLUMNS
    for dropped in ("reviews_list", "menu_item", "phone"):
        assert dropped not in stored.columns

    facets = json.loads(facets_path.read_text(encoding="utf-8"))
    assert facets["locations"] == sorted(facets["locations"])
    assert facets["cuisines"] == sorted(facets["cuisines"])
    assert "banashankari" not in facets["locations"]
    assert "Banashankari" in facets["locations"]
    assert "continental" in facets["cuisines"]
    assert "North Indian" not in facets["cuisines"]


def test_default_source_is_fixture_not_huggingface() -> None:
    args = build_parser().parse_args([])
    assert args.source == "fixture"
    assert "huggingface" in build_parser().parse_args(["--source", "huggingface"]).source


def test_fixture_source_does_not_download(monkeypatch) -> None:
    def boom() -> pd.DataFrame:
        raise AssertionError("Hugging Face download attempted")

    monkeypatch.setattr("scripts.prepare_dataset._load_huggingface", boom)
    frame = load_source("fixture")
    assert len(frame) == 11


def test_fixture_cli_writes_parquet_and_facets_offline(tmp_path: Path) -> None:
    parquet_path = tmp_path / "restaurants.parquet"
    facets_path = tmp_path / "facets.json"
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["HF_DATASETS_OFFLINE"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_dataset.py",
            "--source",
            "fixture",
            "--output",
            str(parquet_path),
            "--facets",
            str(facets_path),
        ],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert parquet_path.exists()
    assert facets_path.exists()
    stored = pd.read_parquet(parquet_path)
    assert len(stored) == 9
    assert stored["id"].is_unique


def _row(catalog: pd.DataFrame, name: str, address: str) -> pd.Series:
    matches = catalog[(catalog["name"] == name) & (catalog["address"] == address)]
    assert len(matches) == 1
    row = matches.iloc[0].copy()
    row["cuisine_tokens"] = list(row["cuisine_tokens"])
    row["listed_types"] = list(row["listed_types"])
    return row
