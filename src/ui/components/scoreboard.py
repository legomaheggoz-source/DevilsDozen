"""Scoreboard component — player rankings and turn indicator."""

from __future__ import annotations

import streamlit as st

from src.database.models import Player


def render_scoreboard(
    players: list[Player],
    current_turn_index: int,
    turn_score: int,
    target_score: int,
    my_player_id: str,
    game_mode: str,
) -> None:
    """Render the scoreboard panel.

    Args:
        players: All players in the lobby, ordered by turn_order.
        current_turn_index: Index into the players list for whose turn it is.
        turn_score: Accumulated (unbanked) turn score for the active player.
        target_score: Score needed to win.
        my_player_id: The local player's UUID string.
        game_mode: ``"peasants_gamble"`` or ``"alchemists_ascent"``.
    """
    html = ['<div class="scoreboard">']
    html.append(f'<div class="scoreboard-title">Scoreboard &mdash; {target_score} to Win</div>')

    for idx, player in enumerate(players):
        pid = str(player.id)
        is_active = idx == current_turn_index
        is_me = pid == my_player_id

        row_classes = ["player-row"]
        if is_active:
            row_classes.append("active")
        if is_me:
            row_classes.append("is-me")

        name_display = player.username
        if is_me:
            name_display += " (You)"

        # Turn indicator
        indicator = "&#9876; " if is_active else ""

        # Score delta for active player
        delta_html = ""
        if is_active and turn_score > 0:
            delta_html = f'<span class="score-delta">+{turn_score}</span>'

        # Disconnect indicator
        disc_html = ""
        if not player.is_connected:
            disc_html = '<span class="disconnected">[away]</span>'

        html.append(
            f'<div class="{" ".join(row_classes)}">'
            f'<span class="name">{indicator}{name_display}{disc_html}</span>'
            f'<span class="score">{player.total_score}{delta_html}</span>'
            f"</div>"
        )

    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)
