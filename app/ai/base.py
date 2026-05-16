"""Base agent classes and tool registry for the T1D AI layer.

Provides the foundational abstractions for structured agents:
- Tool: A callable tool with JSON Schema parameters
- ToolRegistry: Manages tool registration and OpenAI-style function listings
- BaseAgent: Abstract base class for all agents
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.core.logging_config import get_logger

logger = get_logger(__name__)

HandlerFn = Callable[..., Awaitable[Any]]


@dataclass
class Tool:
    """A callable tool with a name, description, JSON Schema parameters, and async handler."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: HandlerFn

    def to_openai_schema(self) -> dict[str, Any]:
        """Return OpenAI function-calling schema dict."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Registry for managing and discovering tools.

    Supports registering, retrieving, listing, and removing tools.
    `list_tools()` returns OpenAI function-calling format for direct injection
    into LLM API calls.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool.

        Args:
            tool: Tool instance to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        logger.info("Registered tool: %s", tool.name)

    def get(self, name: str) -> Tool | None:
        """Retrieve a tool by name.

        Args:
            name: Tool name.

        Returns:
            The Tool instance, or None if not found.
        """
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """Return all registered tools in OpenAI function-calling format.

        Returns:
            List of function-calling schemas, e.g.:
            [{"type": "function", "function": {"name": "...", ...}}]
        """
        return [t.to_openai_schema() for t in self._tools.values()]

    def remove(self, name: str) -> bool:
        """Remove a tool by name.

        Args:
            name: Tool name to remove.

        Returns:
            True if the tool was removed, False if it didn't exist.
        """
        if name in self._tools:
            del self._tools[name]
            logger.info("Removed tool: %s", name)
            return True
        return False

    @property
    def count(self) -> int:
        """Number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


class BaseAgent(ABC):
    """Abstract base class for all T1D AI agents.

    Each agent has a name, an optional ToolRegistry, and must implement
    the `handle` method.
    """

    def __init__(self, name: str, tools: ToolRegistry | None = None) -> None:
        """Initialize the agent.

        Args:
            name: Agent name (used for logging and routing).
            tools: Optional ToolRegistry with tools the agent can invoke.
        """
        self.name = name
        self.tools = tools or ToolRegistry()
        self.logger = get_logger(f"ai.{name}")

    @abstractmethod
    async def handle(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process an incoming task and return a result.

        Subclasses must override this method.

        Args:
            data: Task payload dictionary.

        Returns:
            Result dictionary.
        """
        ...

    async def shutdown(self) -> None:
        """Cleanup hook. Override if the agent holds resources."""
        pass
