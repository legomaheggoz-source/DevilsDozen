"""Sound effects and background music for Devil's Dozen.

Audio data (base64-encoded MP3) is sent to the browser ONCE per track and
cached as JavaScript Audio objects in ``window.parent._dd_audio``.  Subsequent
Streamlit reruns send only tiny control commands (<1 KB) instead of the
multi-megabyte base64 payloads, eliminating the latency that previously made
buttons unresponsive.

Preferences (SFX on/off, music on/off) are stored in non-widget session-state
keys (``_sfx_pref``, ``_music_pref``) so they survive Streamlit's widget-
lifecycle cleanup during page transitions.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Asset paths and mappings
# ---------------------------------------------------------------------------

_SOUNDS_DIR = Path(__file__).resolve().parents[3] / "assets" / "sounds"

_SFX_FILES: dict[str, str] = {
    "dice_roll": "dice_roll.mp3",
    "bust": "bust.mp3",
    "bank": "bank.mp3",
    "hot_dice": "hot_dice.mp3",
    "victory": "victory.mp3",
    "tier_advance": "tier_advance.mp3",
}

_MUSIC_FILES: dict[str, str] = {
    "menu": "menu_theme.mp3",
    "peasants_gamble": "d6_theme.mp3",
    "alchemists_ascent": "d20_theme.mp3",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _load_audio_b64(filename: str) -> str | None:
    """Read an audio file and return its base64-encoded string.

    Returns ``None`` if the file doesn't exist.
    """
    path = _SOUNDS_DIR / filename
    if not path.exists():
        return None
    return base64.b64encode(path.read_bytes()).decode("ascii")


# ---------------------------------------------------------------------------
# Public API — SFX
# ---------------------------------------------------------------------------


def play_sfx(name: str) -> None:
    """Queue a sound effect to be played on the next render cycle.

    Call this from action handlers (roll, bust, bank, etc.).
    The actual playback happens in :func:`render_audio_system`.
    """
    if not st.session_state.get("_sfx_pref", True):
        return
    if name not in _SFX_FILES:
        return
    st.session_state["_sfx_pending"] = name


# ---------------------------------------------------------------------------
# Public API — sidebar controls
# ---------------------------------------------------------------------------


def _sync_sfx_pref() -> None:
    st.session_state["_sfx_pref"] = st.session_state["_sfx_widget"]


def _sync_music_pref() -> None:
    st.session_state["_music_pref"] = st.session_state["_music_widget"]


def _sync_sfx_volume() -> None:
    st.session_state["_sfx_volume"] = st.session_state["_sfx_vol_widget"]


def _sync_music_volume() -> None:
    st.session_state["_music_volume"] = st.session_state["_music_vol_widget"]


def render_sound_controls() -> None:
    """Render SFX and music toggles with volume sliders in the sidebar.

    Uses ``_sfx_pref`` / ``_music_pref`` (non-widget keys) for persistent
    storage so preferences survive page transitions and reruns where the
    sidebar widgets might not render (e.g. when ``st.rerun()`` fires
    mid-page).
    """
    with st.sidebar:
        st.session_state.setdefault("_sfx_pref", True)
        st.session_state.setdefault("_music_pref", True)
        st.session_state.setdefault("_sfx_volume", 50)
        st.session_state.setdefault("_music_volume", 30)

        st.toggle(
            "Sound Effects",
            value=st.session_state["_sfx_pref"],
            key="_sfx_widget",
            on_change=_sync_sfx_pref,
        )
        if st.session_state["_sfx_pref"]:
            st.slider(
                "SFX Volume",
                min_value=0,
                max_value=100,
                value=st.session_state["_sfx_volume"],
                key="_sfx_vol_widget",
                on_change=_sync_sfx_volume,
                format="%d%%",
            )

        st.toggle(
            "Music",
            value=st.session_state["_music_pref"],
            key="_music_widget",
            on_change=_sync_music_pref,
        )
        if st.session_state["_music_pref"]:
            st.slider(
                "Music Volume",
                min_value=0,
                max_value=100,
                value=st.session_state["_music_volume"],
                key="_music_vol_widget",
                on_change=_sync_music_volume,
                format="%d%%",
            )


# ---------------------------------------------------------------------------
# Public API — audio system renderer
# ---------------------------------------------------------------------------


def render_audio_system(page: str, game_mode: str | None = None) -> None:
    """Render the complete audio system (background music + pending SFX).

    Uses a single ``components.html`` call with JavaScript that caches
    ``Audio`` objects in ``window.parent._dd_audio``.  Base64 audio data is
    included **only** the first time a track is needed; all subsequent
    reruns send only lightweight play/pause commands.
    """
    music_enabled = st.session_state.get("_music_pref", True)
    sfx_enabled = st.session_state.get("_sfx_pref", True)
    volume = st.session_state.get("_music_volume", 30) / 100.0
    sfx_volume = st.session_state.get("_sfx_volume", 50) / 100.0

    # --- Determine current music track --------------------------------
    if page in ("home", "lobby_waiting", "results"):
        track_key = "menu"
    elif page == "game" and game_mode in _MUSIC_FILES:
        track_key = game_mode
    else:
        track_key = "menu"

    # --- Consume pending SFX ------------------------------------------
    sfx_pending = st.session_state.pop("_sfx_pending", None)
    if not sfx_enabled:
        sfx_pending = None

    # --- Build JS for one-time data preloads --------------------------
    loaded: set[str] = st.session_state.get("_audio_loaded", set())
    preload_parts: list[str] = []

    # Music: load current track if not yet cached in the browser
    if music_enabled and track_key not in loaded:
        b64 = _load_audio_b64(_MUSIC_FILES[track_key])
        if b64:
            preload_parts.append(
                f"dd.music['{track_key}'] = new p.Audio("
                f"'data:audio/mpeg;base64,{b64}');\n"
                f"dd.music['{track_key}'].loop = true;\n"
                f"dd.music['{track_key}'].volume = {volume};"
            )
            loaded.add(track_key)

    # SFX: load on first trigger (lazy — ~50-300 KB each)
    sfx_cache_key = f"sfx_{sfx_pending}" if sfx_pending else None
    if sfx_pending and sfx_cache_key and sfx_cache_key not in loaded:
        b64 = _load_audio_b64(_SFX_FILES[sfx_pending])
        if b64:
            preload_parts.append(
                f"dd.sfx['{sfx_pending}'] = "
                f"'data:audio/mpeg;base64,{b64}';"
            )
            loaded.add(sfx_cache_key)

    st.session_state["_audio_loaded"] = loaded

    # --- Build lightweight control JS ---------------------------------
    control_parts: list[str] = []

    if music_enabled:
        control_parts.append(
            f"Object.entries(dd.music).forEach(function(e) {{\n"
            f"  if (e[0] !== '{track_key}') e[1].pause();\n"
            f"}});\n"
            f"var cur = dd.music['{track_key}'];\n"
            f"if (cur) cur.volume = {volume};\n"
            f"if (cur && cur.paused) cur.play().catch(function(){{}});"
        )
    else:
        control_parts.append(
            "Object.values(dd.music).forEach(function(a){ a.pause(); });"
        )

    if sfx_pending:
        control_parts.append(
            f"if (dd.sfx['{sfx_pending}']) {{\n"
            f"  var s = new p.Audio(dd.sfx['{sfx_pending}']);\n"
            f"  s.volume = {sfx_volume};\n"
            f"  s.play().catch(function(){{}});\n"
            f"}}"
        )

    # --- Combine into a single components.html call -------------------
    preload_js = "\n".join(preload_parts)
    control_js = "\n".join(control_parts)

    html = (
        "<script>\n"
        "(function() {\n"
        "  try {\n"
        "    var p = window.parent;\n"
        "    if (!p._dd_audio) p._dd_audio = { music: {}, sfx: {} };\n"
        "    var dd = p._dd_audio;\n"
        + preload_js + "\n"
        + control_js + "\n"
        "  } catch(e) { console.warn('DD audio:', e); }\n"
        "})();\n"
        "</script>"
    )

    components.html(html, height=0)
