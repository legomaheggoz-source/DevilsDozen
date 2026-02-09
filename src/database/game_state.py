"""
Devil's Dozen - Game State Manager

CRUD operations for the `game_state` table.
"""

from supabase import Client

from src.database.models import GameState


class GameStateManager:
    """Manages active game state in Supabase."""

    def __init__(self, client: Client) -> None:
        self.client = client
        self.table = client.table("game_state")

    def create(self, lobby_id: str) -> GameState:
        """Initialize game state for a lobby."""
        data = (
            self.table
            .insert({"lobby_id": lobby_id})
            .execute()
        )
        return GameState.model_validate(data.data[0])

    def get(self, lobby_id: str) -> GameState | None:
        """Get the current game state for a lobby."""
        data = (
            self.table
            .select("*")
            .eq("lobby_id", lobby_id)
            .execute()
        )
        if data.data:
            return GameState.model_validate(data.data[0])
        return None

    def update(
        self,
        lobby_id: str,
        *,
        active_dice: list[int] | None = None,
        held_indices: list[int] | None = None,
        turn_score: int | None = None,
        is_bust: bool | None = None,
        roll_count: int | None = None,
        tier: int | None = None,
        previous_dice: list[int] | None = None,
    ) -> GameState:
        """Update game state fields. Only provided fields are changed."""
        updates: dict = {}
        if active_dice is not None:
            updates["active_dice"] = active_dice
        if held_indices is not None:
            updates["held_indices"] = held_indices
        if turn_score is not None:
            updates["turn_score"] = turn_score
        if is_bust is not None:
            updates["is_bust"] = is_bust
        if roll_count is not None:
            updates["roll_count"] = roll_count
        if tier is not None:
            updates["tier"] = tier
        if previous_dice is not None:
            updates["previous_dice"] = previous_dice

        if not updates:
            return self.get(lobby_id)  # type: ignore[return-value]

        data = (
            self.table
            .update(updates)
            .eq("lobby_id", lobby_id)
            .execute()
        )
        return GameState.model_validate(data.data[0])

    def reset_turn(self, lobby_id: str) -> GameState:
        """Reset state for a new turn."""
        data = (
            self.table
            .update({
                "active_dice": [],
                "held_indices": [],
                "turn_score": 0,
                "is_bust": False,
                "roll_count": 0,
                "previous_dice": [],
            })
            .eq("lobby_id", lobby_id)
            .execute()
        )
        return GameState.model_validate(data.data[0])

    def delete(self, lobby_id: str) -> None:
        """Delete game state for a lobby."""
        self.table.delete().eq("lobby_id", lobby_id).execute()
