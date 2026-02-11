-- Migration: Add Alien Invasion game mode fields to game_state table
-- Date: 2026-02-10
-- Description: Adds columns for tracking tanks, death rays, earthlings, and selected types

-- Add tanks_count column
ALTER TABLE game_state
ADD COLUMN IF NOT EXISTS tanks_count INTEGER DEFAULT 0;

-- Add death_rays_count column
ALTER TABLE game_state
ADD COLUMN IF NOT EXISTS death_rays_count INTEGER DEFAULT 0;

-- Add earthlings_count column
ALTER TABLE game_state
ADD COLUMN IF NOT EXISTS earthlings_count INTEGER DEFAULT 0;

-- Add selected_earthling_types column (stores array of type names)
ALTER TABLE game_state
ADD COLUMN IF NOT EXISTS selected_earthling_types JSONB DEFAULT '[]';

-- Add comment describing the columns
COMMENT ON COLUMN game_state.tanks_count IS 'Alien Invasion: Number of tanks collected (auto-locked threats)';
COMMENT ON COLUMN game_state.death_rays_count IS 'Alien Invasion: Number of death rays collected (defense against tanks)';
COMMENT ON COLUMN game_state.earthlings_count IS 'Alien Invasion: Total number of earthlings collected (humans, cows, chickens)';
COMMENT ON COLUMN game_state.selected_earthling_types IS 'Alien Invasion: Array of earthling type names already selected this turn (human, cow, chicken)';
