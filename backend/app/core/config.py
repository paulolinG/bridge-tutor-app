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

    matching_secret: str = ""

    daily_api_key: str = ""
    daily_domain: str = ""

    # Both unset means the Coordinator Digest is simply off — the batch run
    # proceeds and reports notified: 0. Not a 503-when-unconfigured like
    # matching_secret: that guards a security control, this is a
    # notification, and refusing to match students over unset email would
    # be the wrong trade.
    resend_api_key: str = ""
    coordinator_email: str = ""

    # Local development only. Certification is the gate that exists because
    # tutors work with minors, so this defaults off and is enforced on the
    # server — hiding the button in the frontend would not be a control.
    dev_allow_certification_bypass: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
