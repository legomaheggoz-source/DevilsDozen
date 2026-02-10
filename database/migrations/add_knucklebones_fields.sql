-- Migration: Add Knucklebones game mode fields to game_state table
-- Run this in Supabase SQL Editor

-- Add grid storage columns
ALTER TABLE game_state
ADD COLUMN IF NOT EXISTS player1_grid JSONB DEFAULT '{"columns": [[], [], []]}',
ADD COLUMN IF NOT EXISTS player2_grid JSONB DEFAULT '{"columns": [[], [], []]}',
ADD COLUMN IF NOT EXISTS current_die_value INTEGER DEFAULT NULL;

-- Add comment for documentation
COMMENT ON COLUMN game_state.player1_grid IS 'Player 1''s 3x3 Knucklebones grid stored as JSONB {"columns": [[die1, die2], [], [die1, die2, die3]]}';
COMMENT ON COLUMN game_state.player2_grid IS 'Player 2''s 3x3 Knucklebones grid stored as JSONB {"columns": [[die1, die2], [], [die1, die2, die3]]}';
COMMENT ON COLUMN game_state.current_die_value IS 'Current rolled die value (1-6) awaiting placement in Knucklebones mode';
