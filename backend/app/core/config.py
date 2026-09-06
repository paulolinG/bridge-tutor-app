from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    anthropic_api_key: str = ""
    anthropic_model_student: str = "claude-haiku-4-5-20251001"
    anthropic_model_scoring: str = "claude-sonnet-5"

    frontend_origin: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
