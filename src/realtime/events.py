"""
Devil's Dozen - Realtime Event Definitions

Event types and payloads for multiplayer game state changes.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class GameEvent(Enum):
    """Events that can occur during a game."""

    PLAYER_JOINED = auto()
    PLAYER_LEFT = auto()
    GAME_STARTED = auto()
    DICE_ROLLED = auto()
    DICE_HELD = auto()
    TURN_BANKED = auto()
    PLAYER_BUST = auto()
    GAME_WON = auto()
    TURN_ADVANCED = auto()
    STATE_UPDATED = auto()


@dataclass
class EventPayload:
    """Wrapper for realtime event data."""

    event: GameEvent
    lobby_id: str
    player_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


# Map database change patterns to game events
_LOBBY_EVENT_MAP: dict[str, GameEvent] = {
    "playing": GameEvent.GAME_STARTED,
    "finished": GameEvent.GAME_WON,
}

_PLAYER_EVENT_MAP: dict[str, GameEvent] = {
    "INSERT": GameEvent.PLAYER_JOINED,
    "DELETE": GameEvent.PLAYER_LEFT,
}


def classify_lobby_change(
    change_type: str, record: dict[str, Any], old_record: dict[str, Any]
) -> GameEvent | None:
    """Determine the game event from a lobbies table change."""
    if change_type == "UPDATE":
        new_status = record.get("status")
        old_status = old_record.get("status")
        if new_status != old_status and new_status in _LOBBY_EVENT_MAP:
            return _LOBBY_EVENT_MAP[new_status]
        if record.get("current_turn_index") != old_record.get("current_turn_index"):
            return GameEvent.TURN_ADVANCED
    return None


def classify_player_change(
    change_type: str, record: dict[str, Any], old_record: dict[str, Any]
) -> GameEvent | None:
    """Determine the game event from a players table change."""
    if change_type in _PLAYER_EVENT_MAP:
        return _PLAYER_EVENT_MAP[change_type]
    if change_type == "UPDATE":
        if record.get("is_connected") != old_record.get("is_connected"):
            if not record.get("is_connected"):
                return GameEvent.PLAYER_LEFT
            return GameEvent.PLAYER_JOINED
    return None


def classify_game_state_change(
    change_type: str, record: dict[str, Any], old_record: dict[str, Any]
) -> GameEvent | None:
    """Determine the game event from a game_state table change."""
    if change_type != "UPDATE":
        return GameEvent.STATE_UPDATED

    if record.get("is_bust") and not old_record.get("is_bust"):
        return GameEvent.PLAYER_BUST
    if record.get("turn_score", 0) == 0 and old_record.get("turn_score", 0) > 0:
        return GameEvent.TURN_BANKED
    if record.get("held_indices") != old_record.get("held_indices"):
        return GameEvent.DICE_HELD
    if record.get("active_dice") != old_record.get("active_dice"):
        return GameEvent.DICE_ROLLED

    return GameEvent.STATE_UPDATED
