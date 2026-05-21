"""Application configuration."""

import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_title: str = "T1D Companion"
    description: str = (
        "A sensor-agnostic conversational AI companion for Type 1 Diabetes "
        "that connects to CGM/sensor data, spots personal patterns, and helps "
        "users understand what usually happens in real life."
    )
    version: str = "0.1.0"
    environment: str = os.getenv("ENVIRONMENT", "development")

    # Derived/alias properties for compatibility
    @property
    def app_description(self) -> str:
        """Alias for description (backward compatibility)."""
        return self.description

    @property
    def api_docs_url(self) -> str:
        """API documentation URL."""
        return "/docs"

    @property
    def cors_origins(self) -> list[str]:
        """CORS allowed origins list."""
        env_origins = os.getenv("CORS_ORIGINS", "")
        if env_origins:
            return [o.strip() for o in env_origins.split(",")]
        return ["http://localhost:3000", "http://localhost:8000"]

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/t1d_companion",
        validation_alias="DATABASE_URL",
    )

    # Redis (for Celery/Caching)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # External APIs
    # Dexcom
    dexcom_client_id: str | None = os.getenv("DEXCOM_CLIENT_ID")
    dexcom_client_secret: str | None = os.getenv("DEXCOM_CLIENT_SECRET")
    dexcom_redirect_uri: str | None = os.getenv(
        "DEXCOM_REDIRECT_URI",
        "http://localhost:8000/auth/dexcom/callback",
    )
    dexcom_base_url: str = "https://api.dexcom.com/v3"

    # OpenAI
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Anthropic
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

    # USDA FoodData Central
    usda_api_key: str | None = os.getenv("USDA_API_KEY")

    # Nightscout
    nightscout_url: str | None = os.getenv("NIGHTSCOUT_URL")
    nightscout_api_token: str | None = os.getenv("NIGHTSCOUT_API_TOKEN")

    # Dexcom
    dexcom_use_sandbox: bool = os.getenv("DEXCOM_USE_SANDBOX", "false").lower() == "true"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Documentation
    api_docs_url: str = "/docs"
    redoc_url: str = "/redoc"

    # Pagination
    default_page_size: int = 50
    max_page_size: int = 100

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # File Upload
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    allowed_image_extensions: list[str] = [".jpg", ".jpeg", ".png", ".gif"]

    # LLM Configuration
    llm_provider: str = os.getenv("LLM_PROVIDER", "openrouter")  # openai, anthropic, openrouter
    llm_model: Optional[str] = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")  # defaults per provider
    openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    openrouter_referer: str = os.getenv("OPENROUTER_REFERER", "T1D-Companion")

    # LLM provider pool (comma-separated, format: "provider/model:free")
    # Used for automatic fallback rotation when primary provider fails
    llm_provider_pool: str = os.getenv(
        "LLM_PROVIDER_POOL",
        "",
    )

    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def parse_provider_pool(self) -> list[tuple[str, str]]:
        """Parse llm_provider_pool into list of (provider, model) tuples."""
        if not self.llm_provider_pool:
            return []
        entries = []
        for item in self.llm_provider_pool.split(","):
            item = item.strip()
            if not item:
                continue
            # format: "provider/model" — split on first /
            if "/" in item:
                provider, model = item.split("/", 1)
                # openrouter prefix means openrouter provider
                if provider == "openrouter":
                    entries.append(("openrouter", model))
                else:
                    entries.append((provider, model))
            else:
                entries.append((self.llm_provider, item))
        return entries

    # Derived properties
    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern).
    
    Returns:
        Settings: Application settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
