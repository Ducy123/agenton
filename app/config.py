from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AgentOn"
    env: str = "development"
    secret_key: str = "change-me-to-a-random-64-char-string"
    access_token_expire_minutes: int = 1440

    database_url: str = "sqlite:///./agenton.db"

    payment_provider: str = "mock"
    low_balance_threshold_cents: int = 500

    instance_tick_seconds: int = 30

    claude_cli_path: str = "claude"
    claude_cli_idle_timeout_seconds: int = 180

    twitter_client_id: str = ""
    twitter_client_secret: str = ""
    discord_bot_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
