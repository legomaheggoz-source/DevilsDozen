"""
Devil's Dozen - Channel Subscription Management

Manages Supabase Realtime channel subscriptions for live multiplayer.
Uses a background thread with an asyncio event loop since the sync
Realtime client in supabase 2.27.3 is not implemented.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable

from supabase import Client

from src.realtime.events import (
    EventPayload,
    GameEvent,
    classify_game_state_change,
    classify_lobby_change,
    classify_player_change,
)

logger = logging.getLogger(__name__)

# Table-to-classifier mapping
_TABLE_CLASSIFIERS: dict[str, Callable] = {
    "lobbies": classify_lobby_change,
    "players": classify_player_change,
    "game_state": classify_game_state_change,
}

# Tables we subscribe to
_WATCHED_TABLES = ("lobbies", "players", "game_state")


class ChannelManager:
    """Manages Supabase Realtime channel subscriptions.

    Bridges async Realtime API with sync code by running an asyncio
    event loop in a daemon thread. Callbacks are invoked from that
    background thread — callers should handle thread safety.
    """

    def __init__(self, client: Client) -> None:
        self._client = client
        self._channels: dict[str, Any] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        """Start the background event loop if not running."""
        with self._lock:
            if self._loop is None or not self._loop.is_running():
                self._loop = asyncio.new_event_loop()
                self._thread = threading.Thread(
                    target=self._run_loop, daemon=True, name="realtime-loop"
                )
                self._thread.start()
            return self._loop

    def _run_loop(self) -> None:
        """Run the asyncio event loop in the background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def subscribe(
        self,
        lobby_id: str,
        on_event: Callable[[EventPayload], None],
    ) -> None:
        """Subscribe to all table changes for a lobby.

        Creates one channel per table (lobbies, players, game_state),
        filtered by lobby_id. Changes are classified into GameEvent
        types and dispatched via the on_event callback.

        Args:
            lobby_id: UUID of the lobby to watch.
            on_event: Callback receiving EventPayload for each change.
        """
        if lobby_id in self._channels:
            logger.warning("Already subscribed to lobby %s", lobby_id)
            return

        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(
            self._subscribe_async(lobby_id, on_event), loop
        )
        future.result(timeout=10)

    async def _subscribe_async(
        self,
        lobby_id: str,
        on_event: Callable[[EventPayload], None],
    ) -> None:
        """Set up async channel subscriptions for a lobby."""
        channels = []

        for table in _WATCHED_TABLES:
            channel_name = f"lobby:{lobby_id}:{table}"

            # Use the async realtime client directly
            channel = self._client.realtime.channel(channel_name)

            # Determine filter column
            filter_col = "lobby_id" if table != "lobbies" else "id"

            channel.on_postgres_changes(
                event="*",
                callback=lambda payload, t=table: self._handle_change(
                    payload, t, lobby_id, on_event
                ),
                table=table,
                schema="public",
                filter=f"{filter_col}=eq.{lobby_id}",
            )

            await channel.subscribe(
                callback=lambda state, err, t=table: self._on_subscribe_state(
                    state, err, lobby_id, t
                )
            )
            channels.append(channel)

        self._channels[lobby_id] = channels
        logger.info("Subscribed to lobby %s (%d channels)", lobby_id, len(channels))

    def _handle_change(
        self,
        payload: dict[str, Any],
        table: str,
        lobby_id: str,
        on_event: Callable[[EventPayload], None],
    ) -> None:
        """Process a postgres_changes payload into a GameEvent."""
        try:
            data = payload.get("data", payload)
            change_type = data.get("type", data.get("eventType", ""))
            record = data.get("record", {})
            old_record = data.get("old_record", {})

            classifier = _TABLE_CLASSIFIERS.get(table)
            if classifier is None:
                return

            event = classifier(change_type, record, old_record)
            if event is None:
                return

            player_id = record.get("id") if table == "players" else None

            event_payload = EventPayload(
                event=event,
                lobby_id=lobby_id,
                player_id=str(player_id) if player_id else None,
                data={
                    "table": table,
                    "change_type": change_type,
                    "record": record,
                    "old_record": old_record,
                },
            )

            on_event(event_payload)
        except Exception:
            logger.exception("Error handling change for table %s", table)

    def _on_subscribe_state(
        self, state: str, error: Exception | None, lobby_id: str, table: str
    ) -> None:
        """Log subscription state changes."""
        if error:
            logger.error(
                "Subscription error for %s/%s: %s", lobby_id, table, error
            )
        else:
            logger.debug("Channel %s/%s state: %s", lobby_id, table, state)

    def unsubscribe(self, lobby_id: str) -> None:
        """Unsubscribe from all channels for a lobby."""
        channels = self._channels.pop(lobby_id, None)
        if not channels:
            return

        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(
            self._unsubscribe_async(channels), loop
        )
        try:
            future.result(timeout=10)
        except Exception:
            logger.exception("Error unsubscribing from lobby %s", lobby_id)

        logger.info("Unsubscribed from lobby %s", lobby_id)

    async def _unsubscribe_async(self, channels: list[Any]) -> None:
        """Unsubscribe and remove channels."""
        for channel in channels:
            try:
                await channel.unsubscribe()
                await self._client.realtime.remove_channel(channel)
            except Exception:
                logger.exception("Error removing channel")

    def unsubscribe_all(self) -> None:
        """Unsubscribe from all lobbies."""
        lobby_ids = list(self._channels.keys())
        for lobby_id in lobby_ids:
            self.unsubscribe(lobby_id)

    @property
    def active_subscriptions(self) -> list[str]:
        """Return list of lobby IDs with active subscriptions."""
        return list(self._channels.keys())

    def shutdown(self) -> None:
        """Stop the background event loop and clean up."""
        self.unsubscribe_all()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._loop = None
        self._thread = None
