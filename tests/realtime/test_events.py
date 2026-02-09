"""Tests for src/realtime/events.py — event types and classification."""

import pytest

from src.realtime.events import (
    EventPayload,
    GameEvent,
    classify_game_state_change,
    classify_lobby_change,
    classify_player_change,
)


# ── GameEvent enum ──────────────────────────────────────────────────────

class TestGameEvent:
    def test_all_events_defined(self):
        expected = {
            "PLAYER_JOINED", "PLAYER_LEFT", "GAME_STARTED", "DICE_ROLLED",
            "DICE_HELD", "TURN_BANKED", "PLAYER_BUST", "GAME_WON",
            "TURN_ADVANCED", "STATE_UPDATED",
        }
        assert {e.name for e in GameEvent} == expected

    def test_events_are_unique(self):
        values = [e.value for e in GameEvent]
        assert len(values) == len(set(values))


# ── EventPayload ────────────────────────────────────────────────────────

class TestEventPayload:
    def test_minimal_payload(self):
        p = EventPayload(event=GameEvent.DICE_ROLLED, lobby_id="abc-123")
        assert p.event == GameEvent.DICE_ROLLED
        assert p.lobby_id == "abc-123"
        assert p.player_id is None
        assert p.data == {}

    def test_full_payload(self):
        p = EventPayload(
            event=GameEvent.PLAYER_JOINED,
            lobby_id="abc-123",
            player_id="player-1",
            data={"username": "Lancelot"},
        )
        assert p.player_id == "player-1"
        assert p.data["username"] == "Lancelot"


# ── classify_lobby_change ──────────────────────────────────────────────

class TestClassifyLobbyChange:
    def test_status_to_playing(self):
        result = classify_lobby_change(
            "UPDATE",
            {"status": "playing", "current_turn_index": 0},
            {"status": "waiting", "current_turn_index": 0},
        )
        assert result == GameEvent.GAME_STARTED

    def test_status_to_finished(self):
        result = classify_lobby_change(
            "UPDATE",
            {"status": "finished", "current_turn_index": 2},
            {"status": "playing", "current_turn_index": 2},
        )
        assert result == GameEvent.GAME_WON

    def test_turn_advanced(self):
        result = classify_lobby_change(
            "UPDATE",
            {"status": "playing", "current_turn_index": 1},
            {"status": "playing", "current_turn_index": 0},
        )
        assert result == GameEvent.TURN_ADVANCED

    def test_no_meaningful_change(self):
        result = classify_lobby_change(
            "UPDATE",
            {"status": "waiting", "current_turn_index": 0},
            {"status": "waiting", "current_turn_index": 0},
        )
        assert result is None

    def test_insert_returns_none(self):
        result = classify_lobby_change("INSERT", {"status": "waiting"}, {})
        assert result is None


# ── classify_player_change ─────────────────────────────────────────────

class TestClassifyPlayerChange:
    def test_insert_is_joined(self):
        result = classify_player_change("INSERT", {"id": "p1"}, {})
        assert result == GameEvent.PLAYER_JOINED

    def test_delete_is_left(self):
        result = classify_player_change("DELETE", {}, {"id": "p1"})
        assert result == GameEvent.PLAYER_LEFT

    def test_disconnect_is_left(self):
        result = classify_player_change(
            "UPDATE",
            {"is_connected": False},
            {"is_connected": True},
        )
        assert result == GameEvent.PLAYER_LEFT

    def test_reconnect_is_joined(self):
        result = classify_player_change(
            "UPDATE",
            {"is_connected": True},
            {"is_connected": False},
        )
        assert result == GameEvent.PLAYER_JOINED

    def test_score_update_returns_none(self):
        result = classify_player_change(
            "UPDATE",
            {"is_connected": True, "total_score": 500},
            {"is_connected": True, "total_score": 200},
        )
        assert result is None


# ── classify_game_state_change ─────────────────────────────────────────

class TestClassifyGameStateChange:
    def test_bust_detected(self):
        result = classify_game_state_change(
            "UPDATE",
            {"is_bust": True, "active_dice": [1, 2], "held_indices": [], "turn_score": 0},
            {"is_bust": False, "active_dice": [3, 4], "held_indices": [], "turn_score": 100},
        )
        assert result == GameEvent.PLAYER_BUST

    def test_dice_rolled(self):
        result = classify_game_state_change(
            "UPDATE",
            {"is_bust": False, "active_dice": [1, 3, 5], "held_indices": [], "turn_score": 0},
            {"is_bust": False, "active_dice": [], "held_indices": [], "turn_score": 0},
        )
        assert result == GameEvent.DICE_ROLLED

    def test_dice_held(self):
        result = classify_game_state_change(
            "UPDATE",
            {"is_bust": False, "active_dice": [1, 3, 5], "held_indices": [0, 2], "turn_score": 150},
            {"is_bust": False, "active_dice": [1, 3, 5], "held_indices": [], "turn_score": 0},
        )
        assert result == GameEvent.DICE_HELD

    def test_turn_banked(self):
        result = classify_game_state_change(
            "UPDATE",
            {"is_bust": False, "active_dice": [], "held_indices": [], "turn_score": 0},
            {"is_bust": False, "active_dice": [1, 5], "held_indices": [0], "turn_score": 250},
        )
        assert result == GameEvent.TURN_BANKED

    def test_insert_is_state_updated(self):
        result = classify_game_state_change(
            "INSERT",
            {"is_bust": False, "active_dice": [], "held_indices": [], "turn_score": 0},
            {},
        )
        assert result == GameEvent.STATE_UPDATED

    def test_generic_update(self):
        """Same dice/bust/held but different timestamp → STATE_UPDATED."""
        result = classify_game_state_change(
            "UPDATE",
            {"is_bust": False, "active_dice": [1, 2, 3], "held_indices": [0], "turn_score": 100},
            {"is_bust": False, "active_dice": [1, 2, 3], "held_indices": [0], "turn_score": 100},
        )
        assert result == GameEvent.STATE_UPDATED
