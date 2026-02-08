"""
Devil's Dozen Game Engine.

Pure Python game logic with zero UI/database dependencies.
Handles dice rolling, scoring, bust detection, and hot dice mechanics.
"""

from src.engine.base import (
    DiceRoll,
    DiceType,
    GameMode,
    ScoringBreakdown,
    ScoringResult,
    TurnState,
)
from src.engine.peasants_gamble import PeasantsGambleEngine
from src.engine.alchemists_ascent import AlchemistsAscentEngine

__all__ = [
    # Data Classes
    "DiceRoll",
    "ScoringResult",
    "ScoringBreakdown",
    "TurnState",
    # Enums
    "DiceType",
    "GameMode",
    # Engines
    "PeasantsGambleEngine",
    "AlchemistsAscentEngine",
]
