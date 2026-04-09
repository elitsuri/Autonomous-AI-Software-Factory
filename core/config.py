from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Autonomous AI Software Factory"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False

    database_url: PostgresDsn | str = "postgresql+asyncpg://factory:factory@postgres:5432/factory"
    redis_url: RedisDsn | str = "redis://redis:6379/0"
    celery_broker_url: RedisDsn | str = "redis://redis:6379/1"
    celery_result_backend: RedisDsn | str = "redis://redis:6379/2"

    github_repository: str | None = None
    github_token: str | None = None
    github_default_base: str = "main"
    git_author_name: str = "AI Software Factory"
    git_author_email: str = "factory@example.com"

    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 60
    password_pbkdf2_iterations: int = 210_000

    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    generated_projects_dir: Path = Path("workspaces")
    plugin_dirs: list[Path] = Field(default_factory=lambda: [Path("external_plugins")])
    prompt_cache_seconds: int = 3_600
    max_scan_file_bytes: int = 750_000

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8000"])

    @field_validator("jwt_secret_key")
    @classmethod
    def require_non_example_secret(cls, value: str) -> str:
        weak_values = {"factory-secret", "secret", "local-dev-jwt-secret-32-bytes-minimum"}
        if value in weak_values:
            raise ValueError("JWT_SECRET_KEY must be a unique 32+ character secret")
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
