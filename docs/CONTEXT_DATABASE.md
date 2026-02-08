# Context: Database Layer

## Quick Summary

Supabase integration layer using the official Python client. Handles all persistence: lobbies, players, and game state. Uses Pydantic for validation and Row Level Security for multi-tenant safety.

---

## Files in This Module

| File | Purpose |
|------|---------|
| `src/database/__init__.py` | Public exports |
| `src/database/client.py` | Supabase client singleton |
| `src/database/models.py` | Pydantic models matching DB schema |
| `src/database/lobby.py` | Lobby CRUD operations |
| `src/database/player.py` | Player CRUD operations |
| `src/database/game_state.py` | Active game state sync |

---

## Dependencies

### External Packages
- `supabase`: Official Supabase Python client
- `pydantic`: Data validation and serialization
- `python-dotenv`: Environment variable loading

### Internal Imports
- From `config.settings`: `Settings` (for credentials)

---

## Exports (What Others Import)

```python
from src.database import (
    # Client
    get_supabase_client,     # Singleton factory

    # Models
    Lobby,                   # Lobby data model
    Player,                  # Player data model
    GameState,               # Turn state model

    # Managers (CRUD)
    LobbyManager,            # Lobby operations
    PlayerManager,           # Player operations
    GameStateManager,        # Game state operations
)
```

---

## Current State

- [ ] Supabase project created (manual step)
- [ ] Schema migrations written
- [ ] `client.py` - Singleton client
- [ ] `models.py` - Pydantic models
- [ ] `lobby.py` - Lobby CRUD
- [ ] `player.py` - Player CRUD
- [ ] `game_state.py` - Game state operations
- [ ] Row Level Security configured
- [ ] Integration tests passing

---

## Supabase Schema

### Tables

```sql
-- Lobby: Game room containing players
CREATE TABLE lobbies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(6) UNIQUE NOT NULL,
    game_mode VARCHAR(20) NOT NULL,
    win_condition INT NOT NULL,
    current_turn_index INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'waiting',
    winner_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Player: Participant in a game
CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lobby_id UUID REFERENCES lobbies(id) ON DELETE CASCADE,
    username VARCHAR(30) NOT NULL,
    total_score INT DEFAULT 0,
    turn_order INT NOT NULL,
    is_connected BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(lobby_id, username),
    UNIQUE(lobby_id, turn_order)
);

-- Game State: Current turn state
CREATE TABLE game_state (
    lobby_id UUID PRIMARY KEY REFERENCES lobbies(id) ON DELETE CASCADE,
    active_dice JSONB DEFAULT '[]',
    held_indices JSONB DEFAULT '[]',
    turn_score INT DEFAULT 0,
    is_bust BOOLEAN DEFAULT false,
    roll_count INT DEFAULT 0,
    tier INT DEFAULT 1,
    previous_dice JSONB DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_players_lobby ON players(lobby_id);
CREATE INDEX idx_lobbies_code ON lobbies(code);
CREATE INDEX idx_lobbies_status ON lobbies(status);
```

### Row Level Security

```sql
-- Enable RLS
ALTER TABLE lobbies ENABLE ROW LEVEL SECURITY;
ALTER TABLE players ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_state ENABLE ROW LEVEL SECURITY;

-- Policies (permissive for MVP)
CREATE POLICY "public_read" ON lobbies FOR SELECT USING (true);
CREATE POLICY "public_insert" ON lobbies FOR INSERT WITH CHECK (true);
CREATE POLICY "public_update" ON lobbies FOR UPDATE USING (true);

-- Same for players and game_state
```

---

## Key Patterns & Conventions

### Singleton Client Pattern

```python
# src/database/client.py
from functools import lru_cache
from supabase import create_client, Client
from src.config.settings import get_settings

@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Thread-safe singleton client."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)
```

### Pydantic Models Match Schema

```python
# src/database/models.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class Lobby(BaseModel):
    id: UUID
    code: str = Field(max_length=6)
    game_mode: str
    win_condition: int
    current_turn_index: int = 0
    status: str = "waiting"
    winner_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Enable ORM mode
```

### Manager Classes for CRUD

```python
# src/database/lobby.py
class LobbyManager:
    def __init__(self, client: Client):
        self.client = client
        self.table = client.table("lobbies")

    def create(self, game_mode: str, win_condition: int) -> Lobby:
        code = self._generate_code()
        data = self.table.insert({
            "code": code,
            "game_mode": game_mode,
            "win_condition": win_condition
        }).execute()
        return Lobby.model_validate(data.data[0])

    def get_by_code(self, code: str) -> Lobby | None:
        data = self.table.select("*").eq("code", code).execute()
        if data.data:
            return Lobby.model_validate(data.data[0])
        return None
```

### Lobby Code Generation

```python
import secrets
import string

def _generate_code(length: int = 6) -> str:
    """Generate alphanumeric lobby code, avoiding ambiguous characters."""
    alphabet = string.ascii_uppercase.replace("O", "").replace("I", "")
    alphabet += string.digits.replace("0", "").replace("1", "")
    return "".join(secrets.choice(alphabet) for _ in range(length))
```

---

## Integration Points

| Consumer | What They Use |
|----------|---------------|
| `realtime/subscriptions.py` | `get_supabase_client()` |
| `ui/components/lobby.py` | `LobbyManager`, `PlayerManager` |
| `ui/pages/game.py` | `GameStateManager` |

---

## Testing Notes

### Prerequisites
- Supabase project with schema applied
- Environment variables configured

### Run Tests
```bash
pytest tests/database/ -v
```

### Test Database
- Use separate Supabase project for testing
- Or mock the client in unit tests

---

## Discovered Context

> This section is updated during implementation. Check here before starting work.

[Empty until implementation begins]
