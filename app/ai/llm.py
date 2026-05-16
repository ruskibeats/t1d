"""LLM service with structured generation and tool injection.

Provides:
- Structured output generation with JSON schema
- Tool-enabled generation with function calling
- Retry logic for JSON parsing failures
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable, TypeVar

from pydantic import BaseModel

from app.ai.base import Tool, ToolRegistry
from app.core.logging_config import get_logger
from app.services.llm_service import LLMService

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class StructuredOutputMixin:
    """Mixin for generating structured JSON output from LLM responses.

    Adds response_format={type: "json_object"} and parses JSON into Pydantic models.
    """

    def __init__(self, llm_service: LLMService, max_retries: int = 2):
        self.llm = llm_service
        self.max_retries = max_retries

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        context: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> T:
        """Generate a structured JSON response matching the schema.

        Args:
            prompt: User prompt/instruction.
            schema: Pydantic model class for the expected output.
            context: Optional context variables for the prompt.
            temperature: Sampling temperature.

        Returns:
            Parsed Pydantic model instance.

        Raises:
            ValueError: If JSON parsing fails after retries.
        """
        schema_name = schema.__name__
        schema_desc = schema.__doc__ or "Structured output"

        messages = [{"role": "user", "content": prompt}]
        if context:
            messages.insert(0, {"role": "system", "content": json.dumps(context)})

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.llm.generate(
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )

                content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                data = json.loads(content)
                return schema.model_validate(data)

            except json.JSONDecodeError as e:
                logger.warning("JSON parse attempt %d/%d failed: %s", attempt + 1, self.max_retries + 1, e)
                if attempt == self.max_retries:
                    raise ValueError(f"Failed to parse JSON after {self.max_retries + 1} attempts") from e
            except Exception as e:
                logger.error("Structured generation error: %s", e)
                raise

        raise ValueError("Unexpected state: should not reach here")


class ToolEnabledMixin:
    """Mixin for LLM calls with tool/function calling support.

    Converts ToolRegistry to OpenAI function format and handles tool calls.
    """

    def __init__(self, llm_service: LLMService, tool_registry: ToolRegistry | None = None):
        self.llm = llm_service
        self.tools = tool_registry or ToolRegistry()

    async def generate_with_tools(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Generate a response with tool-calling capability.

        Args:
            prompt: User prompt/instruction.
            context: Optional context variables.
            temperature: Sampling temperature.
            max_tokens: Max tokens in response.

        Returns:
            Either {"response": str} if no tool call, or
            {"tool_name": str, "arguments": dict} if tool was called.
        """
        messages = [{"role": "user", "content": prompt}]
        if context:
            messages.insert(0, {"role": "system", "content": json.dumps(context)})

        tools = self.tools.list_tools()

        response = await self.llm.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
        )

        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})

        tool_call = message.get("tool_calls", [])
        if tool_call:
            tc = tool_call[0]
            return {
                "tool_name": tc.get("function", {}).get("name"),
                "arguments": json.loads(tc.get("function", {}).get("arguments", "{}")),
            }

        return {"response": message.get("content", "")}

    def register_tool(self, tool: Tool) -> None:
        """Register a tool for function calling."""
        self.tools.register(tool)

    def get_tool(self, name: str) -> Tool | None:
        """Get a registered tool by name."""
        return self.tools.get(name)


class LLMOrchestrator:
    """Orchestrates LLM calls with structured output and tool support.

    Combines StructuredOutputMixin and ToolEnabledMixin functionality.
    """

    def __init__(
        self,
        llm_service: LLMService,
        tool_registry: ToolRegistry | None = None,
        max_retries: int = 2,
    ):
        self.llm = llm_service
        self.structured = StructuredOutputMixin(llm_service, max_retries)
        self.tooling = ToolEnabledMixin(llm_service, tool_registry)

    async def generate_structured(self, prompt: str, schema: type[T], **kwargs) -> T:
        return await self.structured.generate_structured(prompt, schema, **kwargs)

    async def generate_with_tools(self, prompt: str, **kwargs) -> dict[str, Any]:
        return await self.tooling.generate_with_tools(prompt, **kwargs)

    def register_tool(self, tool: Tool) -> None:
        self.tooling.register_tool(tool)


def create_structured_generator(
    llm_service: LLMService,
    schema: type[T],
    max_retries: int = 2,
) -> Callable[[str, dict[str, Any] | None], Awaitable[T]]:
    """Factory for creating pre-configured structured generators.

    Args:
        llm_service: LLM service instance.
        schema: Pydantic schema for output.
        max_retries: Max JSON parse retries.

    Returns:
        Async function that generates structured output.
    """
    mixin = StructuredOutputMixin(llm_service, max_retries)

    async def generate(prompt: str, context: dict[str, Any] | None = None) -> T:
        return await mixin.generate_structured(prompt, schema, context)

    return generate