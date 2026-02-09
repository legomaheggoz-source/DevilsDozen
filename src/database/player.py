"""
Devil's Dozen - Player Manager

CRUD operations for the `players` table.
"""

from supabase import Client

from src.database.models import Player


class PlayerManager:
    """Manages player records in Supabase."""

    def __init__(self, client: Client) -> None:
        self.client = client
        self.table = client.table("players")

    def join(self, lobby_id: str, username: str, turn_order: int) -> Player:
        """Add a player to a lobby."""
        data = (
            self.table
            .insert({
                "lobby_id": lobby_id,
                "username": username,
                "turn_order": turn_order,
            })
            .execute()
        )
        return Player.model_validate(data.data[0])

    def get(self, player_id: str) -> Player | None:
        """Get a single player by ID."""
        data = (
            self.table
            .select("*")
            .eq("id", player_id)
            .execute()
        )
        if data.data:
            return Player.model_validate(data.data[0])
        return None

    def list_by_lobby(self, lobby_id: str) -> list[Player]:
        """Get all players in a lobby, ordered by turn."""
        data = (
            self.table
            .select("*")
            .eq("lobby_id", lobby_id)
            .order("turn_order")
            .execute()
        )
        return [Player.model_validate(row) for row in data.data]

    def update_score(self, player_id: str, new_total: int) -> Player:
        """Update a player's total score."""
        data = (
            self.table
            .update({"total_score": new_total})
            .eq("id", player_id)
            .execute()
        )
        return Player.model_validate(data.data[0])

    def set_connected(self, player_id: str, is_connected: bool) -> Player:
        """Update a player's connection status."""
        data = (
            self.table
            .update({"is_connected": is_connected})
            .eq("id", player_id)
            .execute()
        )
        return Player.model_validate(data.data[0])

    def count_in_lobby(self, lobby_id: str) -> int:
        """Count players currently in a lobby."""
        data = (
            self.table
            .select("id", count="exact")
            .eq("lobby_id", lobby_id)
            .execute()
        )
        return data.count or 0
