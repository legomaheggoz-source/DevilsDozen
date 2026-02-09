"""UI components for Devil's Dozen."""

from src.ui.components.dice_tray import render_dice_tray
from src.ui.components.scoreboard import render_scoreboard
from src.ui.components.turn_controls import render_turn_controls
from src.ui.components.lobby import render_lobby

__all__ = [
    "render_dice_tray",
    "render_scoreboard",
    "render_turn_controls",
    "render_lobby",
]
