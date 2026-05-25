"""LLM capture module.

A callable that wraps LLMService with token tracking, logging, and dry-run support.
Replaces the inline llm_call closures that were duplicated across pipeline runners.

Usage:
    llm = LLMCapture(provider=LLMProvider.OPENROUTER, model="deepseek/deepseek-v4-flash")
    response = await llm(messages, max_tokens=600)
    print(llm.total_tokens_used)
    print(llm.call_count)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from app.services.llm_service import LLMService, LLMProvider, LLMServiceError

logger = logging.getLogger(__name__)


class LLMCapture:
    """Callable wrapper around LLMService that tracks usage and handles errors.

    Stages call this instead of reaching into LLMService directly.
    The interface is (messages, max_tokens=600) -> str response.
    """

    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OPENROUTER,
        model: str = "deepseek/deepseek-v4-flash",
        api_key: str | None = None,
        dry_run: bool = False,
    ):
        self._service = LLMService(provider=provider, model=model, api_key=api_key)
        self._dry_run = dry_run
        self.total_tokens_used: int = 0
        self.call_count: int = 0
        self.errors: list[str] = []

    async def __call__(self, messages: List[Dict[str, str]], max_tokens: int = 600) -> str:
        """Call the LLM and return the response string.

        Returns empty string on any error (safe for pipeline stages).
        """
        if self._dry_run:
            return "[dry run — no LLM call]"

        self.call_count += 1
        try:
            result = await self._service._call_llm(messages, max_tokens=max_tokens, stream=False)
            tokens = result.get("tokens_used", 0)
            self.total_tokens_used += tokens
            response = result.get("response", "")
            logger.debug(f"LLM call #{self.call_count}: {tokens} tokens, {len(response)} chars")
            return response
        except (LLMServiceError, Exception) as e:
            error_msg = str(e)
            self.errors.append(error_msg)
            logger.warning(f"LLM call #{self.call_count} failed: {error_msg}")
            return ""

    def summary(self) -> dict:
        """Return usage summary."""
        return {
            "call_count": self.call_count,
            "total_tokens_used": self.total_tokens_used,
            "error_count": len(self.errors),
            "errors": self.errors,
        }


def create_llm_call(
    provider: LLMProvider = LLMProvider.OPENROUTER,
    model: str = "deepseek/deepseek-v4-flash",
    api_key: str | None = None,
) -> LLMCapture:
    """Factory function for backward compatibility.

    Returns an LLMCapture instance that can be used as llm_call(messages, max_tokens).
    """
    return LLMCapture(provider=provider, model=model, api_key=api_key)
