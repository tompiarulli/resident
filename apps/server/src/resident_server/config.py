from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RESIDENT_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://resident:resident@localhost:5432/resident"
    # Bearer token paired devices (the iOS app) send with sync requests.
    # Empty disables device sync. Replaced by per-device tokens once device pairing lands.
    device_token: str = ""
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
