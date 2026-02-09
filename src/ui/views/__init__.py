"""Page renderers for Devil's Dozen."""

from src.ui.views.home import render_home_page
from src.ui.views.game import render_game_page
from src.ui.views.results import render_results_page

__all__ = ["render_home_page", "render_game_page", "render_results_page"]
