"""
Devil's Dozen - Lobby Manager

CRUD operations for the `lobbies` table.
"""

import secrets
import string

from supabase import Client

from src.database.models import Lobby


def _generate_code(length: int = 6) -> str:
    """Generate an alphanumeric lobby code, avoiding ambiguous characters."""
    alphabet = string.ascii_uppercase.replace("O", "").replace("I", "")
    alphabet += string.digits.replace("0", "").replace("1", "")
    return "".join(secrets.choice(alphabet) for _ in range(length))


class LobbyManager:
    """Manages lobby lifecycle in Supabase."""

    def __init__(self, client: Client) -> None:
        self.client = client
        self.table = client.table("lobbies")

    def create(self, game_mode: str, win_condition: int) -> Lobby:
        """Create a new lobby with a unique code."""
        code = _generate_code()
        data = (
            self.table
            .insert({
                "code": code,
                "game_mode": game_mode,
                "win_condition": win_condition,
            })
            .execute()
        )
        return Lobby.model_validate(data.data[0])

    def get_by_code(self, code: str) -> Lobby | None:
        """Look up a lobby by its join code."""
        data = (
            self.table
            .select("*")
            .eq("code", code.upper())
            .execute()
        )
        if data.data:
            return Lobby.model_validate(data.data[0])
        return None

    def get_by_id(self, lobby_id: str) -> Lobby | None:
        """Look up a lobby by its UUID."""
        data = (
            self.table
            .select("*")
            .eq("id", lobby_id)
            .execute()
        )
        if data.data:
            return Lobby.model_validate(data.data[0])
        return None

    def update_status(self, lobby_id: str, status: str) -> Lobby:
        """Update lobby status (waiting, playing, finished)."""
        data = (
            self.table
            .update({"status": status})
            .eq("id", lobby_id)
            .execute()
        )
        return Lobby.model_validate(data.data[0])

    def advance_turn(self, lobby_id: str, next_turn_index: int) -> Lobby:
        """Move to the next player's turn."""
        data = (
            self.table
            .update({"current_turn_index": next_turn_index})
            .eq("id", lobby_id)
            .execute()
        )
        return Lobby.model_validate(data.data[0])

    def set_winner(self, lobby_id: str, winner_id: str) -> Lobby:
        """Record the winning player and mark lobby as finished."""
        data = (
            self.table
            .update({
                "winner_id": winner_id,
                "status": "finished",
            })
            .eq("id", lobby_id)
            .execute()
        )
        return Lobby.model_validate(data.data[0])

    def delete(self, lobby_id: str) -> None:
        """Delete a lobby (cascades to players and game_state)."""
        self.table.delete().eq("id", lobby_id).execute()
