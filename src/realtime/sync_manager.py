"""
Devil's Dozen - Realtime Sync Manager

High-level manager that ties together channel subscriptions with
game state reconciliation. Provides convenience functions for the UI layer
and a polling fallback when WebSocket connections fail.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from supabase import Client

from src.database.game_state import GameStateManager
from src.database.lobby import LobbyManager
from src.database.models import GameState, Lobby, Player
from src.database.player import PlayerManager
from src.realtime.events import EventPayload, GameEvent
from src.realtime.subscriptions import ChannelManager

logger = logging.getLogger(__name__)


class RealtimeManager:
    """Coordinates realtime subscriptions and state reconciliation.

    Wraps ChannelManager with higher-level game logic: snapshot
    fetching on subscribe, polling fallback, and clean teardown.
    """

    def __init__(self, client: Client) -> None:
        self._client = client
        self._channel_mgr = ChannelManager(client)
        self._lobby_mgr = LobbyManager(client)
        self._player_mgr = PlayerManager(client)
        self._game_state_mgr = GameStateManager(client)
        self._poll_threads: dict[str, threading.Event] = {}

    def subscribe(
        self,
        lobby_id: str,
        on_event: Callable[[EventPayload], None],
        *,
        use_polling_fallback: bool = True,
        poll_interval: float = 2.0,
    ) -> None:
        """Subscribe to live updates for a lobby.

        Attempts WebSocket subscription first. If it fails and
        use_polling_fallback is True, starts a polling thread instead.

        Args:
            lobby_id: UUID of the lobby to watch.
            on_event: Callback receiving EventPayload for each change.
            use_polling_fallback: Fall back to polling on WS failure.
            poll_interval: Seconds between polls (fallback only).
        """
        try:
            self._channel_mgr.subscribe(lobby_id, on_event)
            logger.info("Realtime subscription active for lobby %s", lobby_id)
        except Exception:
            logger.exception("WebSocket subscription failed for lobby %s", lobby_id)
            if use_polling_fallback:
                logger.info("Falling back to polling for lobby %s", lobby_id)
                self._start_polling(lobby_id, on_event, poll_interval)
            else:
                raise

    def unsubscribe(self, lobby_id: str) -> None:
        """Unsubscribe from a lobby (both WS and polling)."""
        self._channel_mgr.unsubscribe(lobby_id)
        self._stop_polling(lobby_id)

    def get_snapshot(self, lobby_id: str) -> dict[str, Any]:
        """Fetch the current full state of a lobby from the database.

        Useful for initial state load on subscribe and for
        reconciliation after reconnects.

        Returns:
            Dict with 'lobby', 'players', and 'game_state' keys.
        """
        lobby = self._lobby_mgr.get_by_id(lobby_id)
        players = self._player_mgr.list_by_lobby(lobby_id)
        game_state = self._game_state_mgr.get(lobby_id)

        return {
            "lobby": lobby,
            "players": players,
            "game_state": game_state,
        }

    def shutdown(self) -> None:
        """Clean up all subscriptions and background threads."""
        for lobby_id in list(self._poll_threads.keys()):
            self._stop_polling(lobby_id)
        self._channel_mgr.shutdown()

    # -- Polling fallback ------------------------------------------------

    def _start_polling(
        self,
        lobby_id: str,
        on_event: Callable[[EventPayload], None],
        interval: float,
    ) -> None:
        """Start a background polling thread for a lobby."""
        if lobby_id in self._poll_threads:
            return

        stop_event = threading.Event()
        self._poll_threads[lobby_id] = stop_event

        thread = threading.Thread(
            target=self._poll_loop,
            args=(lobby_id, on_event, interval, stop_event),
            daemon=True,
            name=f"poll-{lobby_id[:8]}",
        )
        thread.start()

    def _stop_polling(self, lobby_id: str) -> None:
        """Signal a polling thread to stop."""
        stop_event = self._poll_threads.pop(lobby_id, None)
        if stop_event:
            stop_event.set()

    def _poll_loop(
        self,
        lobby_id: str,
        on_event: Callable[[EventPayload], None],
        interval: float,
        stop_event: threading.Event,
    ) -> None:
        """Poll the database for changes and emit events."""
        last_state: dict[str, Any] | None = None

        while not stop_event.is_set():
            try:
                game_state = self._game_state_mgr.get(lobby_id)
                lobby = self._lobby_mgr.get_by_id(lobby_id)

                if game_state and last_state:
                    self._diff_and_emit(
                        lobby_id, game_state, lobby, last_state, on_event
                    )

                last_state = {
                    "game_state": game_state,
                    "lobby": lobby,
                }
            except Exception:
                logger.exception("Polling error for lobby %s", lobby_id)

            stop_event.wait(interval)

    def _diff_and_emit(
        self,
        lobby_id: str,
        game_state: GameState,
        lobby: Lobby | None,
        last_state: dict[str, Any],
        on_event: Callable[[EventPayload], None],
    ) -> None:
        """Compare current state to previous and emit events for differences."""
        prev_gs: GameState | None = last_state.get("game_state")
        prev_lobby: Lobby | None = last_state.get("lobby")

        if prev_gs and game_state:
            if game_state.is_bust and not prev_gs.is_bust:
                on_event(EventPayload(
                    event=GameEvent.PLAYER_BUST,
                    lobby_id=lobby_id,
                    data={"game_state": game_state.model_dump()},
                ))
            elif game_state.active_dice != prev_gs.active_dice:
                on_event(EventPayload(
                    event=GameEvent.DICE_ROLLED,
                    lobby_id=lobby_id,
                    data={"game_state": game_state.model_dump()},
                ))
            elif game_state.held_indices != prev_gs.held_indices:
                on_event(EventPayload(
                    event=GameEvent.DICE_HELD,
                    lobby_id=lobby_id,
                    data={"game_state": game_state.model_dump()},
                ))
            elif game_state.updated_at != prev_gs.updated_at:
                on_event(EventPayload(
                    event=GameEvent.STATE_UPDATED,
                    lobby_id=lobby_id,
                    data={"game_state": game_state.model_dump()},
                ))

        if prev_lobby and lobby:
            if lobby.status != prev_lobby.status:
                if lobby.status == "playing":
                    on_event(EventPayload(
                        event=GameEvent.GAME_STARTED,
                        lobby_id=lobby_id,
                        data={"lobby": lobby.model_dump()},
                    ))
                elif lobby.status == "finished":
                    on_event(EventPayload(
                        event=GameEvent.GAME_WON,
                        lobby_id=lobby_id,
                        data={"lobby": lobby.model_dump()},
                    ))
            elif lobby.current_turn_index != prev_lobby.current_turn_index:
                on_event(EventPayload(
                    event=GameEvent.TURN_ADVANCED,
                    lobby_id=lobby_id,
                    data={"lobby": lobby.model_dump()},
                ))


# -- Module-level convenience functions ----------------------------------

_manager_instance: RealtimeManager | None = None
_manager_lock = threading.Lock()


def _get_manager(client: Client) -> RealtimeManager:
    """Get or create the singleton RealtimeManager."""
    global _manager_instance
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = RealtimeManager(client)
        return _manager_instance


def subscribe_to_lobby(
    client: Client,
    lobby_id: str,
    on_event: Callable[[EventPayload], None],
) -> RealtimeManager:
    """Subscribe to realtime updates for a lobby.

    Convenience function for use in the UI layer.

    Args:
        client: Supabase client instance.
        lobby_id: UUID of the lobby to watch.
        on_event: Callback for game events.

    Returns:
        The RealtimeManager instance (for snapshot access, etc.)
    """
    manager = _get_manager(client)
    manager.subscribe(lobby_id, on_event)
    return manager


def unsubscribe_from_lobby(client: Client, lobby_id: str) -> None:
    """Unsubscribe from realtime updates for a lobby."""
    manager = _get_manager(client)
    manager.unsubscribe(lobby_id)
