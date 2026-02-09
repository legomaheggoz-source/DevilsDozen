"""
Devil's Dozen - Application Settings

Loads configuration from environment variables using Pydantic Settings.
On Streamlit Cloud, bridges st.secrets into env vars so Pydantic can read them.
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


def _load_streamlit_secrets() -> None:
    """Bridge Streamlit Cloud secrets into environment variables."""
    try:
        import streamlit as st

        for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "DEBUG", "LOG_LEVEL", "ENABLE_SOUNDS"):
            if key not in os.environ and key in st.secrets:
                os.environ[key] = str(st.secrets[key])
    except Exception:
        pass


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
    _load_streamlit_secrets()
    return Settings()
