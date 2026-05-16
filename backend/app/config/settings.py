"""Application settings, sourced from environment variables and `.env`."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    VERSION: str = "1.0.0"
    APP_NAME: str = "querymind"
    

    # CORS: explicit origins required because the SPA sends credentialed requests
    # (cookies); browsers reject "*" with credentials.
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Optional API key. Empty disables auth.
    API_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://querymind:querymind@localhost:5432/querymind"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 8
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Demo database: the seeded `demo` DB (read-only role) on the same Postgres
    DEMO_DB_ENABLED: bool = True
    DEMO_DB_NAME: str = "demo"
    DEMO_DB_USER: str = "querymind_reader"
    DEMO_DB_PASSWORD: str = "querymind_reader"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    SESSION_TTL: int = 86400  # access-session + ENC_KEY lifetime (1 day)
    REFRESH_TTL: int = 60 * 60 * 24 * 30  # refresh-token lifetime (30 days)

    # Auth / sessions
    AUTH_RATE_LIMIT: str = "5/15minutes"

    # Email (Resend) + frontend links
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "QueryMind <onboarding@resend.dev>"
    FRONTEND_URL: str = "http://localhost:3000"

    # LLM model defaults (per-request keys are BYOK, supplied by the workspace)
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_MODEL: str = "gemini-2.0-flash"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    LLM_MAX_TOKENS: int = 2048

    # Execution
    MAX_ROWS: int = 1000
    QUERY_TIMEOUT_SECONDS: float = 30.0
    MAX_RETRIES: int = 3

    # Result UX
    MAX_VISUALIZABLE_ROWS: int = 200

    # Observability
    OTEL_ENDPOINT: str = ""
    OTEL_ENABLE_INSTRUMENTATION: bool = True

    @property
    def cors_origins(self) -> list[str]:
        if self.CORS_ORIGINS in ("", "*"):
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def cookie_secure(self) -> bool:
        """Secure cookies everywhere except local http development."""
        return self.ENVIRONMENT != "development"

    @property
    def cookie_samesite(self) -> str:
        # Cross-domain deployments (Vercel frontend + Railway backend) require
        # SameSite=None so the browser sends cookies on cross-origin fetch.
        # CSRF tokens already mitigate the CSRF risk this introduces.
        return "none" if self.ENVIRONMENT == "production" else "lax"

    @property
    def demo_db_host(self) -> str:
        from sqlalchemy.engine import make_url

        return make_url(self.DATABASE_URL).host or "localhost"

    @property
    def demo_db_port(self) -> int:
        from sqlalchemy.engine import make_url

        return make_url(self.DATABASE_URL).port or 5432


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
