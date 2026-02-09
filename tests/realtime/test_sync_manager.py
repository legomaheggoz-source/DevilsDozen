"""Tests for src/realtime/sync_manager.py — RealtimeManager and convenience functions."""

from unittest.mock import MagicMock, patch

import pytest

from src.realtime.events import EventPayload, GameEvent
from src.realtime.sync_manager import RealtimeManager


@pytest.fixture
def mock_client():
    """Minimal mock Supabase client for RealtimeManager."""
    return MagicMock()


class TestRealtimeManager:
    @patch("src.realtime.sync_manager.ChannelManager")
    def test_subscribe_delegates_to_channel_manager(self, MockCM, mock_client):
        mgr = RealtimeManager(mock_client)
        callback = lambda p: None

        mgr.subscribe("lobby-1", callback)

        MockCM.return_value.subscribe.assert_called_once_with("lobby-1", callback)

    @patch("src.realtime.sync_manager.ChannelManager")
    def test_subscribe_falls_back_to_polling_on_failure(self, MockCM, mock_client):
        MockCM.return_value.subscribe.side_effect = Exception("WS failed")
        mgr = RealtimeManager(mock_client)

        mgr.subscribe("lobby-1", lambda p: None, use_polling_fallback=True)

        # Polling thread should have been started
        assert "lobby-1" in mgr._poll_threads

        # Cleanup
        mgr.shutdown()

    @patch("src.realtime.sync_manager.ChannelManager")
    def test_subscribe_raises_without_fallback(self, MockCM, mock_client):
        MockCM.return_value.subscribe.side_effect = Exception("WS failed")
        mgr = RealtimeManager(mock_client)

        with pytest.raises(Exception, match="WS failed"):
            mgr.subscribe("lobby-1", lambda p: None, use_polling_fallback=False)

    @patch("src.realtime.sync_manager.ChannelManager")
    def test_unsubscribe_stops_polling(self, MockCM, mock_client):
        MockCM.return_value.subscribe.side_effect = Exception("WS failed")
        mgr = RealtimeManager(mock_client)

        mgr.subscribe("lobby-1", lambda p: None)
        assert "lobby-1" in mgr._poll_threads

        mgr.unsubscribe("lobby-1")
        assert "lobby-1" not in mgr._poll_threads

        mgr.shutdown()

    @patch("src.realtime.sync_manager.ChannelManager")
    @patch("src.realtime.sync_manager.GameStateManager")
    @patch("src.realtime.sync_manager.LobbyManager")
    @patch("src.realtime.sync_manager.PlayerManager")
    def test_get_snapshot(self, MockPM, MockLM, MockGSM, MockCM, mock_client):
        mgr = RealtimeManager(mock_client)
        snapshot = mgr.get_snapshot("lobby-1")

        assert "lobby" in snapshot
        assert "players" in snapshot
        assert "game_state" in snapshot


class TestConvenienceFunctions:
    @patch("src.realtime.sync_manager._manager_instance", None)
    @patch("src.realtime.sync_manager.ChannelManager")
    def test_subscribe_to_lobby_creates_manager(self, MockCM, mock_client):
        from src.realtime.sync_manager import subscribe_to_lobby

        result = subscribe_to_lobby(mock_client, "lobby-1", lambda p: None)

        assert isinstance(result, RealtimeManager)

    @patch("src.realtime.sync_manager._manager_instance", None)
    @patch("src.realtime.sync_manager.ChannelManager")
    def test_unsubscribe_from_lobby(self, MockCM, mock_client):
        from src.realtime.sync_manager import subscribe_to_lobby, unsubscribe_from_lobby

        subscribe_to_lobby(mock_client, "lobby-1", lambda p: None)
        unsubscribe_from_lobby(mock_client, "lobby-1")

        MockCM.return_value.unsubscribe.assert_called_with("lobby-1")
