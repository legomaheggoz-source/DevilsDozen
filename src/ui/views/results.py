"""Results page — victory screen and final standings."""

from __future__ import annotations

import streamlit as st

from src.database.client import get_supabase_client
from src.database.lobby import LobbyManager
from src.database.player import PlayerManager
from src.database.game_state import GameStateManager
from src.ui.themes.animations import render_victory_animation
from src.ui.themes.sounds import play_sfx


def render_results_page() -> None:
    """Render the results / victory page."""
    ss = st.session_state
    lobby_id = ss.get("lobby_id")

    if not lobby_id:
        ss["page"] = "home"
        st.rerun()
        return

    client = get_supabase_client()
    lobby_mgr = LobbyManager(client)
    player_mgr = PlayerManager(client)
    gs_mgr = GameStateManager(client)

    lobby = lobby_mgr.get_by_id(lobby_id)
    if lobby is None:
        st.error("Lobby not found.")
        ss["page"] = "home"
        return

    players = player_mgr.list_by_lobby(lobby_id)
    sorted_players = sorted(players, key=lambda p: p.total_score, reverse=True)

    # Winner display
    winner = None
    if lobby.winner_id:
        winner = next(
            (p for p in players if str(p.id) == str(lobby.winner_id)),
            None,
        )

    if winner:
        render_victory_animation(winner.username)
        if not ss.get("_victory_sfx_played"):
            play_sfx("victory")
            ss["_victory_sfx_played"] = True
    else:
        st.title("Game Over")

    # Final standings
    st.subheader("Final Standings")

    for rank, player in enumerate(sorted_players, 1):
        pid = str(player.id)
        is_me = pid == ss.get("player_id")
        is_winner = winner and pid == str(winner.id)

        medal = ""
        if rank == 1:
            medal = "1st"
        elif rank == 2:
            medal = "2nd"
        elif rank == 3:
            medal = "3rd"
        else:
            medal = f"{rank}th"

        name = player.username
        if is_me:
            name += " (You)"

        style = "font-weight:700;" if is_winner else ""
        st.markdown(
            f'<div class="player-row" style="{style}">'
            f'<span class="name">{medal} — {name}</span>'
            f'<span class="score">{player.total_score}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Play Again", type="primary", use_container_width=True):
            _play_again(lobby_mgr, gs_mgr, player_mgr, lobby, players)

    with col2:
        if st.button("Return Home", use_container_width=True):
            _return_home()


def _play_again(lobby_mgr, gs_mgr, player_mgr, lobby, players):
    """Reset the lobby for a new game."""
    ss = st.session_state
    lobby_id = str(lobby.id)

    # Reset all player scores
    for p in players:
        player_mgr.update_score(str(p.id), 0)

    # Reset game state
    gs_mgr.reset_turn(lobby_id)

    # Reset lobby status
    lobby_mgr.update_status(lobby_id, "waiting")

    # Update lobby to remove winner and reset turn
    lobby_mgr.advance_turn(lobby_id, 0)

    ss["page"] = "lobby_waiting"
    ss["_prior_roll_score"] = 0
    ss.pop("_victory_sfx_played", None)
    st.rerun()


def _return_home():
    """Clean up session and go home."""
    ss = st.session_state
    keys_to_clear = [
        "lobby_id", "player_id", "username", "is_host",
        "_prior_roll_score", "_last_turn_index", "_victory_sfx_played",
    ]
    for key in keys_to_clear:
        ss.pop(key, None)
    ss["page"] = "home"
    st.rerun()
