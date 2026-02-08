# Devil's Dozen - Technical Architecture

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT (Browser)                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 Streamlit Frontend                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │  │
│  │  │  Dice Tray  │  │ Scoreboard  │  │   Turn Controls    │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Game Engine                             │  │
│  │  ┌──────────────────┐  ┌──────────────────────────────┐   │  │
│  │  │ PeasantsGamble   │  │   AlchemistsAscent           │   │  │
│  │  │     Engine       │  │       Engine                  │   │  │
│  │  └──────────────────┘  └──────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SUPABASE                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │     Lobbies     │  │    Players      │  │   Game State    │  │
│  │      Table      │  │     Table       │  │     Table       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  Realtime Channels                         │  │
│  │              (WebSocket Push Notifications)                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Module Dependency Graph

```
                    ┌───────────┐
                    │  config   │
                    └─────┬─────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  engine  │   │ database │   │ realtime │
    └──────────┘   └────┬─────┘   └────┬─────┘
          │             │              │
          │             └──────┬───────┘
          │                    │
          ▼                    ▼
    ┌─────────────────────────────────────┐
    │                 ui                   │
    │   (imports engine, database, realtime)│
    └─────────────────────────────────────┘
```

**Dependency Rules**:
- `engine` has ZERO external dependencies (pure Python)
- `database` depends only on `config` for settings
- `realtime` depends on `database` for client access
- `ui` imports from all other modules
- No circular dependencies allowed

---

## 3. Data Flow

### 3.1 Turn Flow (Happy Path)

```
Player A                    Supabase                    Player B
    │                           │                           │
    │──── Click "Roll" ─────────►                           │
    │                           │                           │
    │   [Engine calculates      │                           │
    │    scoring locally]       │                           │
    │                           │                           │
    │──── UPDATE game_state ────►                           │
    │     (dice, turn_score)    │                           │
    │                           │── Realtime broadcast ────►│
    │                           │                           │
    │◄─── Confirmation ─────────│                           │
    │                           │                           │
    │──── Click "Bank" ─────────►                           │
    │                           │                           │
    │──── UPDATE players ───────►                           │
    │     (add turn_score)      │                           │
    │                           │                           │
    │──── UPDATE lobbies ───────►                           │
    │     (next turn_index)     │                           │
    │                           │── Realtime broadcast ────►│
```

### 3.2 Bust Flow

```
Player A                    Supabase                    Player B
    │                           │                           │
    │──── Click "Roll" ─────────►                           │
    │                           │                           │
    │   [Engine: no scoring     │                           │
    │    dice = BUST]           │                           │
    │                           │                           │
    │──── UPDATE game_state ────►                           │
    │     (bust: true)          │                           │
    │                           │── Realtime broadcast ────►│
    │                           │      (bust event)         │
    │                           │                           │
    │──── UPDATE lobbies ───────►                           │
    │     (next turn_index)     │                           │
    │                           │                           │
    │◄─── Now it's Player B ────│◄── Player B's turn now ──│
```

---

## 4. Database Schema

### 4.1 Tables

```sql
-- Lobby: Game room containing players
CREATE TABLE lobbies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(6) UNIQUE NOT NULL,        -- Shareable join code
    game_mode VARCHAR(20) NOT NULL,         -- 'peasants_gamble' | 'alchemists_ascent'
    win_condition INT NOT NULL,             -- Target score to win
    current_turn_index INT DEFAULT 0,       -- Index into player turn order
    status VARCHAR(20) DEFAULT 'waiting',   -- waiting | active | finished
    winner_id UUID REFERENCES players(id),  -- Set when game ends
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Player: Participant in a game
CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lobby_id UUID REFERENCES lobbies(id) ON DELETE CASCADE,
    username VARCHAR(30) NOT NULL,
    total_score INT DEFAULT 0,
    turn_order INT NOT NULL,                -- 0, 1, 2, or 3
    is_connected BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(lobby_id, username),             -- No duplicate names in lobby
    UNIQUE(lobby_id, turn_order)            -- No duplicate turn orders
);

-- Game State: Current turn state (transient)
CREATE TABLE game_state (
    lobby_id UUID PRIMARY KEY REFERENCES lobbies(id) ON DELETE CASCADE,
    active_dice JSONB DEFAULT '[]',         -- Current dice values [1,4,5,2,3,6]
    held_indices JSONB DEFAULT '[]',        -- Indices of held dice [0, 2]
    turn_score INT DEFAULT 0,               -- Points accumulated this turn
    is_bust BOOLEAN DEFAULT false,          -- Did player bust?
    roll_count INT DEFAULT 0,               -- Number of rolls this turn
    tier INT DEFAULT 1,                     -- For Alchemist's Ascent
    previous_dice JSONB DEFAULT '[]',       -- For Tier 2 reroll comparison
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_players_lobby ON players(lobby_id);
CREATE INDEX idx_lobbies_code ON lobbies(code);
CREATE INDEX idx_lobbies_status ON lobbies(status);
```

### 4.2 Row Level Security

```sql
-- Lobbies: Anyone can read, only creator can update
ALTER TABLE lobbies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Lobbies are publicly readable"
    ON lobbies FOR SELECT
    USING (true);

CREATE POLICY "Anyone can create lobbies"
    ON lobbies FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Lobby members can update"
    ON lobbies FOR UPDATE
    USING (true);  -- Simplified for MVP

-- Similar policies for players and game_state tables
```

---

## 5. State Management

### 5.1 Streamlit Session State

```python
# Session state structure
st.session_state = {
    # Identity
    "player_id": "uuid",
    "player_name": "string",

    # Lobby
    "lobby_id": "uuid",
    "lobby_code": "ABC123",
    "game_mode": "peasants_gamble",

    # Turn state
    "is_my_turn": bool,
    "current_dice": [1, 4, 5, 2, 3, 6],
    "held_indices": {0, 2},
    "turn_score": 0,

    # UI state
    "sound_enabled": True,
    "show_rules": False,
}
```

### 5.2 Optimistic Updates

To reduce perceived latency:
1. Update local state immediately on user action
2. Send update to Supabase
3. If Supabase update fails, rollback local state
4. Other players receive update via Realtime subscription

---

## 6. Error Handling Strategy

| Error Type | Response |
|------------|----------|
| Network failure | Retry 3x with backoff, then show error |
| Supabase error | Log, show user-friendly message |
| Invalid game state | Reset to last known good state |
| Concurrent modification | Last write wins (simplified) |
| Player disconnect | Mark as disconnected, allow rejoin |

---

## 7. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Hugging Face Spaces                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Streamlit Application                     │  │
│  │                 (Free Tier)                            │  │
│  │  - Serves UI                                           │  │
│  │  - Runs game engine                                    │  │
│  │  - Connects to Supabase                                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Supabase                               │
│                     (Free Tier)                              │
│  - PostgreSQL database                                       │
│  - Realtime WebSocket channels                               │
│  - Row Level Security                                        │
│  - 500MB storage limit                                       │
└─────────────────────────────────────────────────────────────┘
```

### Environment Variables (Hugging Face Secrets)

```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJxxx...
```

---

## 8. Performance Considerations

### Bottlenecks & Mitigations

| Bottleneck | Mitigation |
|------------|------------|
| Streamlit rerun on state change | Use `st.fragment` for isolated updates |
| Database round-trips | Batch updates where possible |
| Realtime subscription limits | One channel per lobby |
| Animation performance | CSS animations over JS |

### Scaling Limits (Free Tier)

- **Supabase**: 500MB database, 2GB bandwidth/month
- **HF Spaces**: 2 vCPU, 16GB RAM
- **Concurrent games**: ~50 lobbies estimated
