"""Configuração global lida do .env via pydantic-settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = Path(__file__).resolve().parents[5] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    llm_provider: str = "anthropic"
    llm_model_fast: str = "anthropic/claude-haiku-4-5"
    llm_model_smart: str = "anthropic/claude-sonnet-4-6"
    groq_api_key: str = ""
    anthropic_api_key: str | None = None

    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    openai_api_key: str = ""

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    database_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3030"

    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_service_account_json: str = ""

    next_public_ai_api_url: str = "http://localhost:8000"
    next_public_supabase_url: str = ""
    next_public_supabase_publishable_key: str = ""

    document_ai_incoming_dir: str = "C:/oraculo-thorus/incoming"

    allowed_email_domain: str = "thorus.com.br"
    supabase_jwt_secret: str = ""
    supabase_jwks_url: str = ""

    thorus_drive_root_id: str = "0AGS3i6FJiluJUk9PVA"

    ldp_master_sheet_id: str = "1zVwOQQVe6MAZoi4HV8sL1muKlNHZDf_G9F06E7h9aOE"
    ldp_master_tab: str = "Lista de definições"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
