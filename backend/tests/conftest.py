from pathlib import Path

import pytest

from scripts.prepare_dataset import load_source, prepare_catalog, write_catalog


@pytest.fixture(autouse=True)
def isolate_llm_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the default test run off any live model provider."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)


@pytest.fixture
def fixture_catalog_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    parquet_path = tmp_path / "restaurants.parquet"
    write_catalog(prepare_catalog(load_source("fixture")), parquet_path, tmp_path / "facets.json")
    monkeypatch.setenv("CATALOG_PATH", str(parquet_path))
    return parquet_path
