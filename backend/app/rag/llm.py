"""LLM provider abstraction. Any OpenAI-compatible chat-completions endpoint works
(OpenAI, Azure OpenAI proxies, Groq, Together, vLLM, Ollama's OpenAI mode ...).
When no key is configured, `get_llm()` returns None and callers use their non-LLM path."""
from __future__ import annotations

import logging
from typing import Protocol

import httpx

from app.core.config import settings

log = logging.getLogger("polarnexus.llm")


class LLMUnavailable(RuntimeError):
    pass


class LLMProvider(Protocol):
    name: str

    def complete(self, system: str, user: str, max_tokens: int = 700, temperature: float = 0.2) -> str: ...


class OpenAICompatibleLLM:
    def __init__(self) -> None:
        self.name = settings.LLM_MODEL

    def complete(self, system: str, user: str, max_tokens: int = 700, temperature: float = 0.2) -> str:
        try:
            with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                resp = client.post(
                    f"{settings.llm_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={
                        "model": settings.LLM_MODEL,
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            log.warning("LLM call failed: %s", exc)
            raise LLMUnavailable(str(exc)) from exc


def get_llm() -> LLMProvider | None:
    return OpenAICompatibleLLM() if settings.llm_enabled else None


def ai_status() -> dict:
    return {
        "llm_configured": settings.llm_enabled,
        "llm_model": settings.LLM_MODEL if settings.llm_enabled else None,
        "llm_provider": (settings.LLM_PROVIDER or "openai-compatible") if settings.llm_enabled else "none",
        "llm_base_url_host": _host(settings.llm_base_url) if settings.llm_enabled else None,
        "embedding_provider": f"openai:{settings.EMBEDDING_MODEL}" if settings.embedding_api_enabled else "local-lsa-v1",
        "fallback": None if settings.llm_enabled else "Extractive answers + curated demo responses (no LLM key configured)",
        "visual_search": _visual_status(),
    }


def _host(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).netloc  # never expose keys or paths


def _visual_status() -> dict:
    try:
        from app.services.visual import status

        return status()
    except Exception as exc:  # optional subsystem — never break /status
        return {"enabled": False, "reason": str(exc)}
