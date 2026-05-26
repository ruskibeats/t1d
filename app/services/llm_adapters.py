"""LLM provider adapters.

Each adapter implements a single interface: execute(messages, model, max_tokens, stream) → dict.
New providers are added by creating one class — no changes to LLMService.

Usage:
    registry = ProviderRegistry()
    registry.register("openai", OpenAIAdapter())
    registry.register("openrouter", OpenRouterAdapter())
    adapter = registry.get("openrouter")
    response = await adapter.execute(messages, "gpt-4o", max_tokens=800)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class LLMResponse:
    """Normalized response from any provider."""

    def __init__(
        self,
        content: str,
        tokens_used: int,
        model: str,
        provider: str,
        streamed: bool = False,
        raw: dict | None = None,
    ):
        self.content = content
        self.tokens_used = tokens_used
        self.model = model
        self.provider = provider
        self.streamed = streamed
        self.raw = raw or {}

    def to_dict(self) -> dict:
        return {
            "response": self.content,
            "tokens_used": self.tokens_used,
            "model": self.model,
            "provider": self.provider,
            "streamed": self.streamed,
            "safety_flagged": False,
        }


class ProviderAdapter(ABC):
    """Interface for LLM provider adapters.

    Each adapter encapsulates one provider's HTTP call format,
    auth headers, and response parsing.
    """

    @abstractmethod
    async def execute(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        stream: bool = False,
        api_key: str | None = None,
        extra_headers: dict | None = None,
    ) -> LLMResponse:
        """Call the provider and return a normalized response."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and response metadata."""
        ...


class OpenAIAdapter(ProviderAdapter):
    """OpenAI chat completions API."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "openai"

    async def execute(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        stream: bool = False,
        api_key: str | None = None,
        extra_headers: dict | None = None,
    ) -> LLMResponse:
        key = api_key or self._api_key
        if not key:
            raise ValueError("No OpenAI API key")

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "stream": stream,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        tokens = data["usage"]["total_tokens"]
        return LLMResponse(content, tokens, model, self.name, stream, raw=data)


class AnthropicAdapter(ProviderAdapter):
    """Anthropic messages API."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "anthropic"

    async def execute(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        stream: bool = False,
        api_key: str | None = None,
        extra_headers: dict | None = None,
    ) -> LLMResponse:
        key = api_key or self._api_key
        if not key:
            raise ValueError("No Anthropic API key")

        # Split system message from conversation turns
        system_msg = None
        conv_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                conv_messages.append({"role": msg["role"], "content": msg["content"]})

        payload: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": conv_messages,
            "temperature": 0.7,
        }
        if system_msg:
            payload["system"] = system_msg

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["content"][0]["text"]
        tokens = data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
        return LLMResponse(content, tokens, model, self.name, False, raw=data)


class OpenRouterAdapter(ProviderAdapter):
    """OpenRouter unified API (OpenAI-compatible format)."""

    def __init__(self, api_key: str | None = None, referer: str | None = None):
        self._api_key = api_key
        self._referer = referer or "https://github.com/ruskibeats/t1d"

    @property
    def name(self) -> str:
        return "openrouter"

    async def execute(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        stream: bool = False,
        api_key: str | None = None,
        extra_headers: dict | None = None,
    ) -> LLMResponse:
        key = api_key or self._api_key
        if not key:
            raise ValueError("No OpenRouter API key")

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self._referer,
        }
        if extra_headers:
            headers.update(extra_headers)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "stream": stream,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        tokens = data["usage"]["total_tokens"]
        return LLMResponse(content, tokens, model, self.name, stream, raw=data)


class OllamaAdapter(ProviderAdapter):
    """Ollama local LLM API.

    Tries /api/chat first (newer Ollama), falls back to /api/generate (older).
    """

    def __init__(self, base_url: str = "http://192.168.0.211:11434", api_key: str | None = None):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "ollama"

    async def execute(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        stream: bool = False,
        api_key: str | None = None,
        extra_headers: dict | None = None,
    ) -> LLMResponse:
        headers = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)

        # Try /api/chat first (Ollama 0.1.30+), fall back to /api/generate
        try:
            return await self._try_chat(messages, model, max_tokens, headers)
        except Exception as chat_err:
            logger.debug(f"/api/chat failed ({chat_err}), trying /api/generate")
            try:
                return await self._try_generate(messages, model, max_tokens, headers)
            except Exception as gen_err:
                raise Exception(f"Ollama both /api/chat and /api/generate failed: {chat_err} / {gen_err}")

    async def _try_chat(
        self, messages, model, max_tokens, headers
    ) -> LLMResponse:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/chat",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
            )
            resp.raise_for_status()
            data = resp.json()
        content = data.get("message", {}).get("content", "")
        tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
        return LLMResponse(content, tokens, model, self.name, False, raw=data)

    async def _try_generate(
        self, messages, model, max_tokens, headers
    ) -> LLMResponse:
        # Convert messages to a single prompt for /api/generate
        prompt = self._messages_to_prompt(messages)
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/generate",
                headers=headers,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
            )
            resp.raise_for_status()
            data = resp.json()
        content = data.get("response", "")
        tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
        return LLMResponse(content, tokens, model, self.name, False, raw=data)

    @staticmethod
    def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI-style messages to a single prompt string."""
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant:")
        return "\n\n".join(parts)


class ProviderRegistry:
    """Registry of provider adapters.

    Usage:
        registry = ProviderRegistry()
        registry.register("openai", OpenAIAdapter(key))
        registry.register("openrouter", OpenRouterAdapter(key))
        adapter = registry.get("openrouter")
    """

    def __init__(self):
        self._adapters: dict[str, ProviderAdapter] = {}

    def register(self, name: str, adapter: ProviderAdapter) -> None:
        """Register a provider adapter."""
        self._adapters[name] = adapter

    def get(self, name: str) -> ProviderAdapter:
        """Get a provider adapter by name."""
        if name not in self._adapters:
            raise KeyError(f"Unknown provider: {name}. Registered: {list(self._adapters.keys())}")
        return self._adapters[name]

    def providers(self) -> list[str]:
        """List registered provider names."""
        return list(self._adapters.keys())
