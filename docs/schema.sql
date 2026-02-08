-- =============================================================================
-- Devil's Dozen - Supabase Database Schema
-- =============================================================================
-- Run this SQL in your Supabase SQL Editor to set up the database.
-- Supabase Dashboard → SQL Editor → New Query → Paste & Run
-- =============================================================================

-- Enable UUID extension (usually already enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- TABLES
-- =============================================================================

-- Lobbies: Game rooms that contain players
CREATE TABLE IF NOT EXISTS lobbies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Shareable 6-character join code (e.g., "ABC123")
    code VARCHAR(6) UNIQUE NOT NULL,

    -- Game mode: 'peasants_gamble' or 'alchemists_ascent'
    game_mode VARCHAR(20) NOT NULL CHECK (game_mode IN ('peasants_gamble', 'alchemists_ascent')),

    -- Target score to win the game
    win_condition INT NOT NULL CHECK (win_condition > 0),

    -- Index of current player's turn (0-based, references players by turn_order)
    current_turn_index INT DEFAULT 0 CHECK (current_turn_index >= 0),

    -- Lobby status: waiting (for players), active (in game), finished (game over)
    status VARCHAR(20) DEFAULT 'waiting' CHECK (status IN ('waiting', 'active', 'finished')),

    -- Winner player ID (set when game finishes)
    winner_id UUID,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Players: Participants in a game lobby
CREATE TABLE IF NOT EXISTS players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Reference to the lobby this player is in
    lobby_id UUID NOT NULL REFERENCES lobbies(id) ON DELETE CASCADE,

    -- Player display name (unique within lobby)
    username VARCHAR(30) NOT NULL,

    -- Total score accumulated across all banked turns
    total_score INT DEFAULT 0 CHECK (total_score >= 0),

    -- Turn order (0, 1, 2, or 3 for up to 4 players)
    turn_order INT NOT NULL CHECK (turn_order >= 0 AND turn_order <= 3),

    -- Connection status for handling disconnects
    is_connected BOOLEAN DEFAULT true,

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    UNIQUE(lobby_id, username),     -- No duplicate names in same lobby
    UNIQUE(lobby_id, turn_order)    -- No duplicate turn orders in same lobby
);

-- Game State: Current turn state (transient, one per lobby)
CREATE TABLE IF NOT EXISTS game_state (
    -- One game state per lobby
    lobby_id UUID PRIMARY KEY REFERENCES lobbies(id) ON DELETE CASCADE,

    -- Current dice values as JSON array (e.g., [1, 4, 5, 2, 3, 6])
    active_dice JSONB DEFAULT '[]'::jsonb,

    -- Indices of held dice as JSON array (e.g., [0, 2])
    held_indices JSONB DEFAULT '[]'::jsonb,

    -- Points accumulated this turn (not yet banked)
    turn_score INT DEFAULT 0 CHECK (turn_score >= 0),

    -- Whether the current roll resulted in a bust
    is_bust BOOLEAN DEFAULT false,

    -- Number of rolls taken this turn
    roll_count INT DEFAULT 0 CHECK (roll_count >= 0),

    -- Current tier for Alchemist's Ascent (1=Red, 2=Green, 3=Blue)
    tier INT DEFAULT 1 CHECK (tier >= 1 AND tier <= 3),

    -- Previous dice values for Tier 2 reroll comparison
    previous_dice JSONB DEFAULT '[]'::jsonb,

    -- Timestamp for last update
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Fast lookup of players by lobby
CREATE INDEX IF NOT EXISTS idx_players_lobby ON players(lobby_id);

-- Fast lookup of lobbies by join code
CREATE INDEX IF NOT EXISTS idx_lobbies_code ON lobbies(code);

-- Filter lobbies by status (for listing active/waiting games)
CREATE INDEX IF NOT EXISTS idx_lobbies_status ON lobbies(status);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Auto-update lobbies.updated_at
CREATE TRIGGER update_lobbies_updated_at
    BEFORE UPDATE ON lobbies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update game_state.updated_at
CREATE TRIGGER update_game_state_updated_at
    BEFORE UPDATE ON game_state
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE lobbies ENABLE ROW LEVEL SECURITY;
ALTER TABLE players ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_state ENABLE ROW LEVEL SECURITY;

-- Lobbies: Anyone can read, insert, and update
-- (In production, you might want more restrictive policies)
CREATE POLICY "Lobbies are publicly readable"
    ON lobbies FOR SELECT
    USING (true);

CREATE POLICY "Anyone can create lobbies"
    ON lobbies FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Anyone can update lobbies"
    ON lobbies FOR UPDATE
    USING (true);

CREATE POLICY "Anyone can delete lobbies"
    ON lobbies FOR DELETE
    USING (true);

-- Players: Same permissive policies for MVP
CREATE POLICY "Players are publicly readable"
    ON players FOR SELECT
    USING (true);

CREATE POLICY "Anyone can create players"
    ON players FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Anyone can update players"
    ON players FOR UPDATE
    USING (true);

CREATE POLICY "Anyone can delete players"
    ON players FOR DELETE
    USING (true);

-- Game State: Same permissive policies
CREATE POLICY "Game state is publicly readable"
    ON game_state FOR SELECT
    USING (true);

CREATE POLICY "Anyone can create game state"
    ON game_state FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Anyone can update game state"
    ON game_state FOR UPDATE
    USING (true);

CREATE POLICY "Anyone can delete game state"
    ON game_state FOR DELETE
    USING (true);

-- =============================================================================
-- REALTIME CONFIGURATION
-- =============================================================================

-- Enable realtime for all tables
-- Go to Supabase Dashboard → Database → Replication and enable these tables

-- Alternatively, use this command (requires superuser):
-- ALTER PUBLICATION supabase_realtime ADD TABLE lobbies;
-- ALTER PUBLICATION supabase_realtime ADD TABLE players;
-- ALTER PUBLICATION supabase_realtime ADD TABLE game_state;

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Generate a unique lobby code
CREATE OR REPLACE FUNCTION generate_lobby_code()
RETURNS VARCHAR(6) AS $$
DECLARE
    code VARCHAR(6);
    chars VARCHAR := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';  -- Excluding O, I, 0, 1
    i INT;
BEGIN
    LOOP
        code := '';
        FOR i IN 1..6 LOOP
            code := code || substr(chars, floor(random() * length(chars) + 1)::int, 1);
        END LOOP;

        -- Check if code already exists
        IF NOT EXISTS (SELECT 1 FROM lobbies WHERE lobbies.code = code) THEN
            RETURN code;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create a new lobby with auto-generated code
CREATE OR REPLACE FUNCTION create_lobby(
    p_game_mode VARCHAR(20),
    p_win_condition INT
)
RETURNS UUID AS $$
DECLARE
    new_lobby_id UUID;
    new_code VARCHAR(6);
BEGIN
    new_code := generate_lobby_code();

    INSERT INTO lobbies (code, game_mode, win_condition)
    VALUES (new_code, p_game_mode, p_win_condition)
    RETURNING id INTO new_lobby_id;

    -- Create initial game state for this lobby
    INSERT INTO game_state (lobby_id)
    VALUES (new_lobby_id);

    RETURN new_lobby_id;
END;
$$ LANGUAGE plpgsql;

-- Add a player to a lobby
CREATE OR REPLACE FUNCTION join_lobby(
    p_lobby_code VARCHAR(6),
    p_username VARCHAR(30)
)
RETURNS UUID AS $$
DECLARE
    v_lobby_id UUID;
    v_player_count INT;
    v_new_player_id UUID;
BEGIN
    -- Find the lobby
    SELECT id INTO v_lobby_id
    FROM lobbies
    WHERE code = p_lobby_code AND status = 'waiting';

    IF v_lobby_id IS NULL THEN
        RAISE EXCEPTION 'Lobby not found or game already started';
    END IF;

    -- Count existing players
    SELECT COUNT(*) INTO v_player_count
    FROM players
    WHERE lobby_id = v_lobby_id;

    IF v_player_count >= 4 THEN
        RAISE EXCEPTION 'Lobby is full';
    END IF;

    -- Add the player
    INSERT INTO players (lobby_id, username, turn_order)
    VALUES (v_lobby_id, p_username, v_player_count)
    RETURNING id INTO v_new_player_id;

    RETURN v_new_player_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- CLEANUP (run manually to reset database)
-- =============================================================================

-- To reset the database, uncomment and run:
-- DROP TABLE IF EXISTS game_state CASCADE;
-- DROP TABLE IF EXISTS players CASCADE;
-- DROP TABLE IF EXISTS lobbies CASCADE;
-- DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;
-- DROP FUNCTION IF EXISTS generate_lobby_code CASCADE;
-- DROP FUNCTION IF EXISTS create_lobby CASCADE;
-- DROP FUNCTION IF EXISTS join_lobby CASCADE;
