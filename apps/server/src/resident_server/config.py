from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RESIDENT_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://resident:resident@localhost:5432/resident"
    # Tailscale logins (e.g. "you@github") allowed to use the dashboard via the
    # Tailscale-User-Login header. Comma-separated. Empty disables header auth.
    trusted_tailscale_logins: Annotated[list[str], NoDecode] = []
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("trusted_tailscale_logins", "cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
