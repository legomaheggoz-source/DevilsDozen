"""
Devil's Dozen - Database Models

Pydantic models that mirror the Supabase table schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Lobby(BaseModel):
    """Mirrors the `lobbies` table."""

    id: UUID
    code: str = Field(max_length=6)
    game_mode: str
    win_condition: int
    current_turn_index: int = 0
    status: str = "waiting"
    winner_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Player(BaseModel):
    """Mirrors the `players` table."""

    id: UUID
    lobby_id: UUID
    username: str = Field(max_length=30)
    total_score: int = 0
    turn_order: int
    is_connected: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class GameState(BaseModel):
    """Mirrors the `game_state` table."""

    lobby_id: UUID
    active_dice: list[int] = Field(default_factory=list)
    held_indices: list[int] = Field(default_factory=list)
    turn_score: int = 0
    is_bust: bool = False
    roll_count: int = 0
    tier: int = 1
    previous_dice: list[int] = Field(default_factory=list)
    # Knucklebones fields
    player1_grid: dict = Field(default_factory=lambda: {"columns": [[], [], []]})
    player2_grid: dict = Field(default_factory=lambda: {"columns": [[], [], []]})
    current_die_value: int | None = None
    # Alien Invasion fields
    tanks_count: int = 0
    death_rays_count: int = 0
    earthlings_count: int = 0
    selected_earthling_types: list[str] = Field(default_factory=list)
    updated_at: datetime

    model_config = {"from_attributes": True}
