"""Configuration for the production companion service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CompanionConfig:
    """Configuration loaded from environment variables with sensible defaults."""

    # LLM
    model: str = os.getenv("T1D_MODEL", "deepseek/deepseek-v4-flash")
    llm_provider: str = os.getenv("LLM_PROVIDER", "openrouter")
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    max_tokens: int = int(os.getenv("T1D_MAX_TOKENS", "800"))

    # Cache
    cache_capacity: int = int(os.getenv("T1D_CACHE_CAPACITY", "5000"))
    cache_ttl_seconds: int = int(os.getenv("T1D_CACHE_TTL", "1800"))

    # Postgres
    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://t1d_user:t1d_pass@localhost:5432/t1d_companion"
    ))

    # Rate limiting
    rate_limit_per_minute: int = int(os.getenv("T1D_RATE_LIMIT", "60"))

    # Data paths
    profile_configs: str = os.getenv("T1D_PROFILES_PATH", "/root/t1d/data/profile_configs.json")
    food_history: str = os.getenv("T1D_HISTORY_PATH", "/root/t1d/data/food_history_90d_enhanced.json")

    @classmethod
    def from_env(cls) -> "CompanionConfig":
        return cls()