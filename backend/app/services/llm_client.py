"""OpenAI-compatible chat completions client. Defaults target Groq. No vendor SDK."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import LLM_MAX_OUTPUT_TOKENS, LLM_REASONING_EFFORT, Settings, load_settings
from app.schemas.llm import groq_response_format

logger = logging.getLogger(__name__)

TEMPERATURE = 0.2


class LlmError(Exception):
    """The provider call failed, timed out, or returned an envelope we cannot read."""


@dataclass(frozen=True)
class LlmCompletion:
    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LlmClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> LlmCompletion:
        """Return the assistant message text and token counts when the provider sends them."""


class ChatCompletionsClient:
    """POST `{LLM_BASE_URL}/chat/completions` with a strict JSON schema."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings if settings is not None else load_settings()
        self._transport = transport

    def complete(self, messages: list[dict[str, str]]) -> LlmCompletion:
        api_key = self._settings.llm_api_key.strip()
        if api_key == "":
            raise LlmError("LLM_API_KEY is not set")

        url = f"{self._settings.llm_base_url.rstrip('/')}/chat/completions"
        body: dict[str, object] = {
            "model": self._settings.llm_model,
            "messages": [_message(message) for message in messages],
            "temperature": TEMPERATURE,
            "max_tokens": LLM_MAX_OUTPUT_TOKENS,
            "response_format": groq_response_format(),
        }
        if "gpt-oss" in self._settings.llm_model:
            body["reasoning_effort"] = LLM_REASONING_EFFORT
        timeout = httpx.Timeout(self._settings.llm_timeout_seconds)
        try:
            with httpx.Client(timeout=timeout, transport=self._transport) as http:
                response = http.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=body,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise LlmError(type(exc).__name__) from exc
        except ValueError as exc:
            raise LlmError("invalid response") from exc
        content = _message_content(payload)
        prompt_tokens, completion_tokens = _usage(payload)
        return LlmCompletion(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )


def build_llm_client(settings: Settings | None = None) -> ChatCompletionsClient:
    return ChatCompletionsClient(settings if settings is not None else load_settings())


def _message(message: dict[str, str]) -> dict[str, str]:
    return {"role": message["role"], "content": message["content"]}


def _message_content(payload: object) -> str:
    if not isinstance(payload, dict):
        raise LlmError("invalid response")
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmError("invalid response") from exc
    if isinstance(content, dict):
        return json.dumps(content)
    if not isinstance(content, str):
        raise LlmError("invalid response")
    return content


def _usage(payload: dict[str, object]) -> tuple[int | None, int | None]:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None, None
    prompt_tokens = _token_count(usage.get("prompt_tokens"))
    completion_tokens = _token_count(usage.get("completion_tokens"))
    if prompt_tokens is None and completion_tokens is None:
        return None, None
    logger.info(
        "llm usage prompt_tokens=%s completion_tokens=%s",
        prompt_tokens,
        completion_tokens,
    )
    return prompt_tokens, completion_tokens


def _token_count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value
