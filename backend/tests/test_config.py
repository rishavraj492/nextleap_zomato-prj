from app.config import (
    CANDIDATE_CAP,
    HIGH_BUDGET_ABOVE,
    LOW_BUDGET_UNDER,
    MEDIUM_BUDGET_MAX,
    MEDIUM_BUDGET_MIN,
    RESULT_CAP,
    VITE_DEV_ORIGINS,
    allowed_origins,
    load_settings,
)


def test_budget_bands_and_caps() -> None:
    assert LOW_BUDGET_UNDER == 500
    assert MEDIUM_BUDGET_MIN == 500
    assert MEDIUM_BUDGET_MAX == 1000
    assert HIGH_BUDGET_ABOVE == 1000
    assert CANDIDATE_CAP == 20
    assert RESULT_CAP == 5


def test_settings_read_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("CATALOG_PATH", "custom/restaurants.parquet")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "local-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "9")

    settings = load_settings()

    assert settings.catalog_path.as_posix().endswith("custom/restaurants.parquet")
    assert settings.llm_base_url == "http://localhost:11434/v1"
    assert settings.llm_model == "local-model"
    assert settings.llm_timeout_seconds == 9


def test_llm_defaults_point_at_groq(monkeypatch) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    settings = load_settings()

    assert settings.llm_base_url == "https://api.groq.com/openai/v1"
    assert settings.llm_model == "openai/gpt-oss-120b"


def test_timeout_defaults_to_20_seconds(monkeypatch) -> None:
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)

    assert load_settings().llm_timeout_seconds == 20


def test_cors_origins_default_to_vite_dev(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert allowed_origins() == VITE_DEV_ORIGINS


def test_cors_origins_append_production_hosts(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", " https://app.vercel.app, https://custom.example ,")

    assert allowed_origins() == [
        *VITE_DEV_ORIGINS,
        "https://app.vercel.app",
        "https://custom.example",
    ]
