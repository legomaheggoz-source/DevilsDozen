"""Lobby component — create/join lobbies and waiting room."""

from __future__ import annotations

import streamlit as st

from src.database.client import get_supabase_client
from src.database.lobby import LobbyManager
from src.database.player import PlayerManager
from src.database.game_state import GameStateManager


def _get_managers():
    client = get_supabase_client()
    return LobbyManager(client), PlayerManager(client), GameStateManager(client)


def render_lobby() -> None:
    """Render the lobby creation/joining UI and waiting room."""
    ss = st.session_state

    # If already in a lobby waiting room, show that instead
    if ss.get("page") == "lobby_waiting":
        _render_waiting_room()
        return

    tab_create, tab_join = st.tabs(["Create Lobby", "Join Lobby"])

    with tab_create:
        _render_create_form()

    with tab_join:
        _render_join_form()


def _render_create_form() -> None:
    ss = st.session_state

    # Game mode outside the form so target score updates immediately
    game_mode = st.selectbox(
        "Game Mode",
        options=["peasants_gamble", "alchemists_ascent"],
        format_func=lambda m: (
            "Peasant's Gamble (D6)" if m == "peasants_gamble"
            else "Alchemist's Ascent (D20)"
        ),
        key="create_game_mode",
    )

    if game_mode == "peasants_gamble":
        target = st.selectbox(
            "Target Score",
            options=[3000, 5000, 10000],
            index=1,
            key="create_target_score",
        )
    else:
        target = 250
        st.markdown("**Target Score:** 250 (fixed)")

    with st.form("create_lobby_form"):
        username = st.text_input(
            "Your Name",
            max_chars=30,
            placeholder="Enter your name...",
        )
        submitted = st.form_submit_button("Create Lobby", type="primary")

    if submitted:
        if not username or not username.strip():
            st.error("Please enter your name.")
            return

        username = username.strip()
        try:
            lobby_mgr, player_mgr, gs_mgr = _get_managers()
            lobby = lobby_mgr.create(game_mode, target)
            player = player_mgr.join(str(lobby.id), username, turn_order=0)
            gs_mgr.create(str(lobby.id))

            ss["lobby_id"] = str(lobby.id)
            ss["player_id"] = str(player.id)
            ss["username"] = username
            ss["is_host"] = True
            ss["page"] = "lobby_waiting"
            st.rerun()
        except Exception as e:
            st.error(f"Failed to create lobby: {e}")


def _render_join_form() -> None:
    ss = st.session_state

    with st.form("join_lobby_form"):
        username = st.text_input(
            "Your Name",
            max_chars=30,
            placeholder="Enter your name...",
        )
        code = st.text_input(
            "Lobby Code",
            max_chars=6,
            placeholder="e.g. ABC123",
        )
        submitted = st.form_submit_button("Join Lobby", type="primary")

    if submitted:
        if not username or not username.strip():
            st.error("Please enter your name.")
            return
        if not code or not code.strip():
            st.error("Please enter a lobby code.")
            return

        username = username.strip()
        code = code.strip().upper()
        try:
            lobby_mgr, player_mgr, _ = _get_managers()
            lobby = lobby_mgr.get_by_code(code)
            if lobby is None:
                st.error("Lobby not found. Check the code and try again.")
                return
            if lobby.status != "waiting":
                st.error("That lobby is already in a game.")
                return

            count = player_mgr.count_in_lobby(str(lobby.id))
            if count >= 4:
                st.error("Lobby is full (max 4 players).")
                return

            # Check for existing player with same name (reconnect on refresh)
            existing = player_mgr.list_by_lobby(str(lobby.id))
            match = next(
                (p for p in existing if p.username.lower() == username.lower()),
                None,
            )
            if match:
                # Reconnect to existing player record
                player = match
                count = len(existing)  # don't increment
            else:
                player = player_mgr.join(str(lobby.id), username, turn_order=count)

            ss["lobby_id"] = str(lobby.id)
            ss["player_id"] = str(player.id)
            ss["username"] = username
            ss["is_host"] = player.turn_order == 0
            ss["page"] = "lobby_waiting"
            st.rerun()
        except Exception as e:
            st.error(f"Failed to join lobby: {e}")


def _render_waiting_room() -> None:
    ss = st.session_state
    lobby_id = ss.get("lobby_id")
    if not lobby_id:
        ss["page"] = "home"
        st.rerun()
        return

    lobby_mgr, player_mgr, _ = _get_managers()
    lobby = lobby_mgr.get_by_id(lobby_id)

    if lobby is None:
        st.error("Lobby no longer exists.")
        ss["page"] = "home"
        st.rerun()
        return

    # If game already started (e.g., host pressed start), go to game
    if lobby.status == "playing":
        ss["page"] = "game"
        st.rerun()
        return

    st.subheader("Waiting Room")

    # Lobby code display
    st.markdown(
        f'<div class="lobby-code">{lobby.code}</div>',
        unsafe_allow_html=True,
    )
    st.caption("Share this code with friends to join.")

    # Dynamic content in a polling fragment so it auto-refreshes
    _waiting_room_live(lobby_id)


@st.fragment(run_every=3)
def _waiting_room_live(lobby_id: str) -> None:
    """Live-updating player list, start button, and status polling."""
    ss = st.session_state
    lobby_mgr, player_mgr, _ = _get_managers()

    lobby = lobby_mgr.get_by_id(lobby_id)
    if lobby is None:
        return

    # Detect game started (by host in another session, or another tab)
    if lobby.status == "playing":
        ss["page"] = "game"
        st.rerun(scope="app")
        return

    # Player list (re-fetched every poll)
    players = player_mgr.list_by_lobby(lobby_id)
    st.markdown(f"**Players ({len(players)}/4):**")

    for p in players:
        badge = ""
        if p.turn_order == 0:
            badge = '<span class="host-badge">Host</span>'
        you = " (You)" if str(p.id) == ss.get("player_id") else ""
        st.markdown(
            f'<div class="player-list-item">{p.username}{you} {badge}</div>',
            unsafe_allow_html=True,
        )

    # Host controls
    if ss.get("is_host"):
        st.divider()
        can_start = len(players) >= 2
        if st.button(
            "Start Game",
            disabled=not can_start,
            type="primary",
            use_container_width=True,
        ):
            lobby_mgr.update_status(lobby_id, "playing")
            ss["page"] = "game"
            st.rerun(scope="app")

        if not can_start:
            st.caption("Need at least 2 players to start.")
    else:
        st.info("Waiting for the host to start the game...")
