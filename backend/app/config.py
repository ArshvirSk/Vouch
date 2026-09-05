from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./test.db"
    database_url_sync: str = "sqlite:///./test.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "vouch-dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Vote window
    vote_window_hours: int = 72

    # Reputation
    reputation_recompute_interval_minutes: int = 15
    reputation_decay_factor: float = 0.95  # per-event decay for older events

    # LLM (stubbed for MVP)
    llm_api_key: str = ""
    llm_enabled: bool = False

    class Config:
        env_file = ".env"
        env_prefix = "VOUCH_"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
