"""
Devil's Dozen - Supabase Client

Thread-safe singleton factory for the Supabase client.
"""

from functools import lru_cache

from supabase import Client, create_client

from src.config.settings import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Create and cache a Supabase client instance."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)
