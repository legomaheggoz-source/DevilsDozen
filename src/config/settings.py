"""
Devil's Dozen - Application Settings

Loads configuration from environment variables using Pydantic Settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    supabase_url: str
    supabase_anon_key: str

    # Application
    debug: bool = False
    log_level: str = "INFO"

    # Audio
    enable_sounds: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton settings instance."""
    return Settings()
