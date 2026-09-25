from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://vouch:vouch_dev_password@localhost:5432/vouch"
    database_url_sync: str = "postgresql://vouch:vouch_dev_password@localhost:5432/vouch"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "vouch-dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # Supabase (Auth)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    privy_app_id: str = ""

    # Gemini LLM for Falsifiability
    # Supported models: any Gemini model id, e.g. "gemini-2.5-flash"
    llm_model: str = "gemini-2.5-flash"
    gemini_api_key: str | None = None
    enable_llm_check: bool = False

    # Vote window
    vote_window_hours: int = 72

    # Phase 4: public-figure accountability
    # Comma-separated handles promoted to moderators (bootstrap for the first ones)
    moderator_handles: str = ""
    # Jury pool size auto-assigned to commitments published from approved extractions
    public_jury_pool_size: int = 5
    # How many recent public commitments to include in a contradiction check
    contradiction_ledger_size: int = 100

    # Reputation
    reputation_recompute_interval_minutes: int = 15
    reputation_decay_factor: float = 0.95  # per-event decay for older events

    class Config:
        env_file = ".env"
        env_prefix = "VOUCH_"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
