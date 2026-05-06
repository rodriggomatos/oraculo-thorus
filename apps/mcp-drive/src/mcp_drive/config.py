"""Configuração lida do .env via pydantic-settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    google_service_account_json: str = ""
    thorus_drive_root_id: str = "0AGS3i6FJiluJUk9PVA"
    mcp_drive_cache_ttl_seconds: int = 300
    mcp_drive_log_level: str = "INFO"

    mcp_drive_transport: Literal["stdio", "streamable-http", "sse"] = "stdio"
    mcp_drive_host: str = "127.0.0.1"
    mcp_drive_port: int = 8001
    mcp_drive_auth_token: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
