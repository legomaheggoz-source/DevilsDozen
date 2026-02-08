# Context: Real-time Sync

## Quick Summary

Manages Supabase Realtime subscriptions for live multiplayer. Handles turn changes, score updates, and player connection status. Coordinates optimistic UI updates with server state reconciliation.

---

## Files in This Module

| File | Purpose |
|------|---------|
| `src/realtime/__init__.py` | Public exports |
| `src/realtime/subscriptions.py` | Channel subscription management |
| `src/realtime/events.py` | Event type definitions |
| `src/realtime/sync_manager.py` | Turn coordination and state sync |

---

## Dependencies

### External Packages
- `supabase`: Realtime channel support

### Internal Imports
- From `database.client`: `get_supabase_client`
- From `database.models`: `Lobby`, `Player`, `GameState`

---

## Exports (What Others Import)

```python
from src.realtime import (
    # Manager
    RealtimeManager,          # Main subscription handler

    # Event Types
    GameEvent,                # Enum of event types
    EventPayload,             # Typed event data

    # Convenience Functions
    subscribe_to_lobby,       # Quick subscription setup
    unsubscribe_from_lobby,   # Cleanup
)
```

---

## Current State

- [ ] `events.py` - Event definitions
- [ ] `subscriptions.py` - Channel management
- [ ] `sync_manager.py` - State coordination
- [ ] Reconnection logic
- [ ] Integration with Streamlit

---

## Key Patterns & Conventions

### Event Types

```python
# src/realtime/events.py
from enum import Enum, auto
from dataclasses import dataclass
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

@dataclass
class EventPayload:
    """Wrapper for realtime event data."""
    event: GameEvent
    lobby_id: str
    player_id: str | None
    data: dict[str, Any]
```

### Subscription Pattern

```python
# src/realtime/subscriptions.py
from supabase import Client

class ChannelManager:
    """Manages Supabase Realtime channel subscriptions."""

    def __init__(self, client: Client):
        self.client = client
        self._channels: dict[str, Any] = {}

    def subscribe(
        self,
        lobby_id: str,
        on_event: Callable[[EventPayload], None]
    ) -> None:
        """Subscribe to all events for a lobby."""
        channel_name = f"lobby:{lobby_id}"

        channel = self.client.channel(channel_name)

        # Subscribe to table changes
        channel.on(
            "postgres_changes",
            callback=lambda payload: self._handle_change(payload, on_event),
            event="*",
            schema="public",
            table="game_state",
            filter=f"lobby_id=eq.{lobby_id}"
        ).subscribe()

        self._channels[lobby_id] = channel

    def unsubscribe(self, lobby_id: str) -> None:
        """Unsubscribe and cleanup."""
        if lobby_id in self._channels:
            self._channels[lobby_id].unsubscribe()
            del self._channels[lobby_id]
```

### Streamlit Integration Pattern

```python
# In ui/pages/game.py
import streamlit as st
from src.realtime import subscribe_to_lobby

def handle_game_event(payload: EventPayload) -> None:
    """Handle incoming game events."""
    if payload.event == GameEvent.DICE_ROLLED:
        st.session_state.current_dice = payload.data["dice"]
        st.rerun()
    elif payload.event == GameEvent.PLAYER_BUST:
        st.session_state.show_bust_animation = True
        st.rerun()

# On page load
if "realtime_subscribed" not in st.session_state:
    subscribe_to_lobby(st.session_state.lobby_id, handle_game_event)
    st.session_state.realtime_subscribed = True
```

### Polling Fallback (If Realtime Fails)

```python
# Fallback polling for Streamlit (blocks main thread)
import time

def poll_for_updates(lobby_id: str, interval: float = 2.0) -> None:
    """Poll database for updates if realtime fails."""
    placeholder = st.empty()

    while True:
        state = GameStateManager.get(lobby_id)
        with placeholder.container():
            render_game_state(state)
        time.sleep(interval)
```

---

## Supabase Realtime Configuration

### Enable Realtime in Dashboard

1. Go to Supabase Dashboard → Database → Replication
2. Enable replication for tables:
   - `lobbies`
   - `players`
   - `game_state`

### Channel Naming Convention

```
lobby:{lobby_id}  → Game state updates for a specific lobby
```

---

## Integration Points

| Consumer | What They Use |
|----------|---------------|
| `ui/pages/game.py` | `subscribe_to_lobby`, `GameEvent` |
| `ui/components/scoreboard.py` | Listens for score updates |

---

## Testing Notes

### Run Tests
```bash
pytest tests/integration/test_realtime.py -v
```

### Testing Realtime Locally
1. Open two browser windows to same lobby
2. Verify both receive updates when one player acts
3. Test reconnection by temporarily disabling network

### Mocking for Unit Tests
```python
from unittest.mock import Mock, patch

@patch("src.realtime.subscriptions.get_supabase_client")
def test_subscription(mock_client):
    mock_channel = Mock()
    mock_client.return_value.channel.return_value = mock_channel

    manager = ChannelManager(mock_client.return_value)
    manager.subscribe("lobby-123", lambda x: None)

    mock_channel.subscribe.assert_called_once()
```

---

## Discovered Context

> This section is updated during implementation. Check here before starting work.

[Empty until implementation begins]
