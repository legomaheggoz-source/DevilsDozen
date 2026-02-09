"""Tests for src/realtime/subscriptions.py — channel management (mocked)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.realtime.events import EventPayload, GameEvent
from src.realtime.subscriptions import ChannelManager


@pytest.fixture
def mock_client():
    """Create a mock Supabase client with async realtime support."""
    client = MagicMock()

    # Each call to client.realtime.channel() returns a fresh mock channel
    def make_channel(name):
        channel = AsyncMock()
        channel.on_postgres_changes = MagicMock(return_value=channel)
        channel.subscribe = AsyncMock(return_value=channel)
        channel.unsubscribe = AsyncMock()
        return channel

    client.realtime.channel = MagicMock(side_effect=make_channel)
    client.realtime.remove_channel = AsyncMock()
    return client


class TestChannelManager:
    def test_subscribe_creates_channels(self, mock_client):
        mgr = ChannelManager(mock_client)
        try:
            mgr.subscribe("lobby-123", lambda p: None)

            # Should create 3 channels (lobbies, players, game_state)
            assert mock_client.realtime.channel.call_count == 3
            assert "lobby-123" in mgr.active_subscriptions
        finally:
            mgr.shutdown()

    def test_subscribe_idempotent(self, mock_client):
        mgr = ChannelManager(mock_client)
        try:
            mgr.subscribe("lobby-123", lambda p: None)
            mgr.subscribe("lobby-123", lambda p: None)  # duplicate

            # Still only 3 channels
            assert mock_client.realtime.channel.call_count == 3
        finally:
            mgr.shutdown()

    def test_unsubscribe_removes_channels(self, mock_client):
        mgr = ChannelManager(mock_client)
        try:
            mgr.subscribe("lobby-123", lambda p: None)
            mgr.unsubscribe("lobby-123")

            assert "lobby-123" not in mgr.active_subscriptions
        finally:
            mgr.shutdown()

    def test_unsubscribe_nonexistent_is_noop(self, mock_client):
        mgr = ChannelManager(mock_client)
        try:
            mgr.unsubscribe("no-such-lobby")  # should not raise
        finally:
            mgr.shutdown()

    def test_unsubscribe_all(self, mock_client):
        mgr = ChannelManager(mock_client)
        try:
            mgr.subscribe("lobby-1", lambda p: None)
            mgr.subscribe("lobby-2", lambda p: None)
            mgr.unsubscribe_all()

            assert mgr.active_subscriptions == []
        finally:
            mgr.shutdown()

    def test_channel_naming(self, mock_client):
        mgr = ChannelManager(mock_client)
        try:
            mgr.subscribe("abc-def", lambda p: None)

            call_args = [
                call.args[0]
                for call in mock_client.realtime.channel.call_args_list
            ]
            assert "lobby:abc-def:lobbies" in call_args
            assert "lobby:abc-def:players" in call_args
            assert "lobby:abc-def:game_state" in call_args
        finally:
            mgr.shutdown()


class TestHandleChange:
    def test_game_state_update_fires_callback(self, mock_client):
        received = []
        mgr = ChannelManager(mock_client)
        try:
            mgr._handle_change(
                payload={
                    "data": {
                        "type": "UPDATE",
                        "record": {"is_bust": True, "active_dice": [2, 3],
                                   "held_indices": [], "turn_score": 0},
                        "old_record": {"is_bust": False, "active_dice": [1, 5],
                                       "held_indices": [], "turn_score": 150},
                    }
                },
                table="game_state",
                lobby_id="lobby-x",
                on_event=received.append,
            )

            assert len(received) == 1
            assert received[0].event == GameEvent.PLAYER_BUST
            assert received[0].lobby_id == "lobby-x"
        finally:
            mgr.shutdown()

    def test_player_insert_fires_callback(self, mock_client):
        received = []
        mgr = ChannelManager(mock_client)
        try:
            mgr._handle_change(
                payload={
                    "data": {
                        "type": "INSERT",
                        "record": {"id": "player-42", "username": "Guinevere"},
                        "old_record": {},
                    }
                },
                table="players",
                lobby_id="lobby-y",
                on_event=received.append,
            )

            assert len(received) == 1
            assert received[0].event == GameEvent.PLAYER_JOINED
            assert received[0].player_id == "player-42"
        finally:
            mgr.shutdown()

    def test_unknown_table_ignored(self, mock_client):
        received = []
        mgr = ChannelManager(mock_client)
        try:
            mgr._handle_change(
                payload={"data": {"type": "INSERT", "record": {}, "old_record": {}}},
                table="unknown_table",
                lobby_id="lobby-z",
                on_event=received.append,
            )

            assert len(received) == 0
        finally:
            mgr.shutdown()

    def test_callback_error_does_not_propagate(self, mock_client):
        """Errors in _handle_change should be logged, not raised."""
        mgr = ChannelManager(mock_client)
        try:
            mgr._handle_change(
                payload={"data": {"type": "UPDATE", "record": None, "old_record": None}},
                table="game_state",
                lobby_id="lobby-err",
                on_event=lambda p: None,
            )
            # Should not raise
        finally:
            mgr.shutdown()
