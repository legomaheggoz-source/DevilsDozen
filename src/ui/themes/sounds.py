"""Sound effects and background music for Devil's Dozen.

SFX are base64-encoded and injected as <audio autoplay> via st.markdown.
Background music uses an HTML <audio autoplay loop controls> element in the
sidebar so it plays immediately and loops without user interaction.
A fire-once pattern (_sfx_pending) prevents re-triggering on Streamlit reruns.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

# Path to the sounds directory
_SOUNDS_DIR = Path(__file__).resolve().parents[3] / "assets" / "sounds"

# SFX file mapping: logical name → filename
_SFX_FILES: dict[str, str] = {
    "dice_roll": "dice_roll.mp3",
    "bust": "bust.mp3",
    "bank": "bank.mp3",
    "hot_dice": "hot_dice.mp3",
    "victory": "victory.mp3",
    "tier_advance": "tier_advance.mp3",
}

# Background music mapping: context → filename
_MUSIC_FILES: dict[str, str] = {
    "menu": "menu_theme.mp3",
    "peasants_gamble": "d6_theme.mp3",
    "alchemists_ascent": "d20_theme.mp3",
}


@st.cache_data(show_spinner=False)
def _load_audio_b64(filename: str) -> str | None:
    """Read an audio file and return its base64-encoded string.

    Returns None if the file doesn't exist (audio files not yet provided).
    """
    path = _SOUNDS_DIR / filename
    if not path.exists():
        return None
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")


def _inject_sfx(filename: str) -> None:
    """Inject a hidden <audio autoplay> element via st.markdown."""
    b64 = _load_audio_b64(filename)
    if b64 is None:
        return
    st.markdown(
        f'<audio autoplay src="data:audio/mpeg;base64,{b64}"></audio>',
        unsafe_allow_html=True,
    )


def play_sfx(name: str) -> None:
    """Queue a sound effect to be played on the next render cycle.

    Call this from action handlers (roll, bust, bank, etc.).
    The actual audio injection happens in render_pending_sfx().
    """
    if not st.session_state.get("sfx_enabled", True):
        return
    if name not in _SFX_FILES:
        return
    st.session_state["_sfx_pending"] = name


def render_pending_sfx() -> None:
    """Consume and play any pending sound effect.

    Call this once at the end of the page render (in app.py) so the
    <audio> tag is emitted exactly once per event, not on every rerun.
    """
    pending = st.session_state.pop("_sfx_pending", None)
    if pending and pending in _SFX_FILES:
        _inject_sfx(_SFX_FILES[pending])


def render_background_music(page: str, game_mode: str | None = None) -> None:
    """Render the background music player in the sidebar.

    Uses an HTML <audio> element with autoplay, loop, and controls so music
    starts immediately and the user can pause/adjust volume via native controls.
    Tracks the current track key in session state so the element is only
    re-injected when the track actually changes (avoids restarting on reruns).

    Args:
        page: Current page name (home, lobby_waiting, game, results).
        game_mode: Current game mode if in-game (peasants_gamble / alchemists_ascent).
    """
    if not st.session_state.get("music_enabled", True):
        st.session_state.pop("_current_music_track", None)
        return

    # Determine which track to play
    if page in ("home", "lobby_waiting", "results"):
        track_key = "menu"
    elif page == "game" and game_mode in _MUSIC_FILES:
        track_key = game_mode
    else:
        track_key = "menu"

    filename = _MUSIC_FILES[track_key]
    b64 = _load_audio_b64(filename)
    if b64 is None:
        return

    with st.sidebar:
        # Only re-inject when the track changes to avoid restarting mid-song
        prev_track = st.session_state.get("_current_music_track")
        if prev_track != track_key:
            st.session_state["_current_music_track"] = track_key

        st.markdown(
            f'<audio id="bg-music" autoplay loop controls '
            f'src="data:audio/mpeg;base64,{b64}" '
            f'style="width:100%;margin-top:8px;"></audio>',
            unsafe_allow_html=True,
        )


def render_sound_controls() -> None:
    """Render SFX and music toggles in the sidebar."""
    with st.sidebar:
        st.session_state.setdefault("sfx_enabled", True)
        st.session_state.setdefault("music_enabled", True)

        st.toggle(
            "Sound Effects",
            key="sfx_enabled",
        )
        st.toggle(
            "Music",
            key="music_enabled",
        )
