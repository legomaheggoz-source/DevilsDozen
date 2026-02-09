"""
Devil's Dozen Database Layer.

Supabase integration for lobbies, players, and game state persistence.
"""

from src.database.client import get_supabase_client
from src.database.game_state import GameStateManager
from src.database.lobby import LobbyManager
from src.database.models import GameState, Lobby, Player
from src.database.player import PlayerManager

__all__ = [
    "get_supabase_client",
    "GameState",
    "GameStateManager",
    "Lobby",
    "LobbyManager",
    "Player",
    "PlayerManager",
]
