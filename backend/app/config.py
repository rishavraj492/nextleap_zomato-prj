"""Runtime settings. Budget bands and caps are fixed. Paths and the model come from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# cost_for_two in rupees. Low is under 500, medium is 500 through 1000 inclusive, high is above 1000.
LOW_BUDGET_UNDER = 500
MEDIUM_BUDGET_MIN = 500
MEDIUM_BUDGET_MAX = 1000
HIGH_BUDGET_ABOVE = 1000

CANDIDATE_CAP = 20
RESULT_CAP = 5
# One short sentence. Longer model text is cut before it reaches the client.
REASON_MAX_CHARS = 180
# openai/gpt-oss-120b on Groq: 8_000 tokens/minute and 200_000 tokens/day.
# The cap is completion tokens only, so one search cannot spend the whole minute.
LLM_MAX_OUTPUT_TOKENS = 512
LLM_REASONING_EFFORT = "low"

BUDGETS = ("low", "medium", "high")
RATING_MIN = 0
RATING_MAX = 5

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CATALOG_PATH = _BACKEND_ROOT / "data" / "restaurants.parquet"
_DEFAULT_LLM_BASE_URL = "https://api.groq.com/openai/v1"
_DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"
_DEFAULT_LLM_TIMEOUT_SECONDS = 20

VITE_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
# Vercel production and preview hosts. Starlette matches this against the full origin.
VERCEL_ORIGIN_REGEX = r"https://.*\.vercel\.app"


def allowed_origins() -> list[str]:
    """Vite dev origins, plus CORS_ORIGINS. An empty variable leaves only the dev origins."""
    configured = os.getenv("CORS_ORIGINS", "")
    extra = [origin.strip() for origin in configured.split(",") if origin.strip()]
    origins: list[str] = []
    seen: set[str] = set()
    for origin in (*VITE_DEV_ORIGINS, *extra):
        if origin in seen:
            continue
        seen.add(origin)
        origins.append(origin)
    return origins


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    catalog_path: Path
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_timeout_seconds: int


def load_settings() -> Settings:
    return Settings(
        catalog_path=Path(_env_str("CATALOG_PATH", str(_DEFAULT_CATALOG_PATH))),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_base_url=_env_str("LLM_BASE_URL", _DEFAULT_LLM_BASE_URL),
        llm_model=_env_str("LLM_MODEL", _DEFAULT_LLM_MODEL),
        llm_timeout_seconds=_env_int("LLM_TIMEOUT_SECONDS", _DEFAULT_LLM_TIMEOUT_SECONDS),
    )


settings = load_settings()
CATALOG_PATH = settings.catalog_path
LLM_API_KEY = settings.llm_api_key
LLM_BASE_URL = settings.llm_base_url
LLM_MODEL = settings.llm_model
LLM_TIMEOUT_SECONDS = settings.llm_timeout_seconds
