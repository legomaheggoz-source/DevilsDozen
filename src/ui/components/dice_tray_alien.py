"""
Alien Invasion Dice Tray Component

Renders dice with custom face icons and group selection buttons.
"""

from __future__ import annotations

import base64
from collections import Counter
from pathlib import Path

import streamlit as st
from src.engine.alien_invasion import AlienInvasionScoringResult, FaceType


# Face value to type name mapping
FACE_TO_TYPE = {
    1: "human",
    2: "cow",
    3: "chicken",
    4: "death-ray",
    5: "death-ray",
    6: "tank",
}

# Face type to display emoji
TYPE_TO_EMOJI = {
    "human": "👤",
    "cow": "🐄",
    "chicken": "🐔",
    "death-ray": "⚡",
    "tank": "🔺",
}


@st.cache_data(show_spinner=False)
def _load_dice_image_b64(face_type: str) -> str:
    """Load a dice image and return as base64 data URI."""
    # Map face types to file names
    file_map = {
        "human": "human.png",
        "cow": "cow.png",
        "chicken": "chicken.png",
        "death-ray": "death_ray.png",
        "tank": "tank.png",
    }

    dice_dir = Path(__file__).resolve().parents[3] / "assets" / "dice" / "d6"
    file_path = dice_dir / file_map[face_type]

    if not file_path.exists():
        return ""

    img_data = base64.b64encode(file_path.read_bytes()).decode()
    return f"data:image/png;base64,{img_data}"


@st.cache_data(show_spinner=False)
def _get_dice_face_css() -> str:
    """Generate CSS with background-image rules for each dice face type.

    Loaded once per session to avoid embedding large base64 data in every
    st.markdown call (which overwhelms Streamlit's HTML sanitizer).
    """
    face_types = ["human", "cow", "chicken", "death-ray", "tank"]
    rules = []
    for ft in face_types:
        b64 = _load_dice_image_b64(ft)
        if b64:
            rules.append(
                f'.die.alien-invasion.face-{ft} {{'
                f'  background-image: url("{b64}");'
                f'  background-size: 80%;'
                f'  background-repeat: no-repeat;'
                f'  background-position: center;'
                f'}}'
            )
    return "\n".join(rules)


def _inject_dice_face_css() -> None:
    """Inject the dice face background-image CSS on every render.

    The CSS string itself is cached via @st.cache_data, so file I/O and
    base64 encoding only happen once per session.
    """
    css = _get_dice_face_css()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_alien_dice_tray(
    dice: list[int],
    held_indices: set[int],
    auto_locked_indices: set[int],
    is_my_turn: bool,
    roll_count: int,
) -> None:
    """
    Render Alien Invasion dice with custom icon images.

    Args:
        dice: Current dice face values (1-6)
        held_indices: All indices currently held (includes auto-locked tanks)
        auto_locked_indices: Indices of auto-locked tanks
        is_my_turn: Whether it's the local player's turn
        roll_count: Current roll number
    """
    # Inject background-image CSS for dice faces (once per session)
    _inject_dice_face_css()

    if not dice:
        st.markdown(
            '<div class="dice-tray">'
            '<span style="color:var(--text-secondary);font-style:italic;">'
            "Roll the dice to begin your abductions!"
            "</span></div>",
            unsafe_allow_html=True,
        )
        return

    # Build lightweight HTML — images come from CSS background-image
    html_parts = ['<div class="dice-tray">']

    for i, val in enumerate(dice):
        face_type = FACE_TO_TYPE[val]
        classes = ["die", "alien-invasion", f"face-{face_type}"]

        # Mark auto-locked tanks
        if i in auto_locked_indices:
            classes.append("auto-locked")
        # Mark held dice (but not tanks, which are already marked)
        elif i in held_indices:
            classes.append("held")

        html_parts.append(f'<div class="{" ".join(classes)}"></div>')

    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_group_selection_buttons(
    available_selections: dict[FaceType, list[int]],
    is_my_turn: bool,
    roll_count: int,
) -> FaceType | None:
    """
    Render group selection buttons for available face types.

    Args:
        available_selections: Dict mapping FaceType to available indices
        is_my_turn: Whether it's the local player's turn
        roll_count: Current roll number (for button keys)

    Returns:
        Selected FaceType, or None if no button clicked
    """
    if not is_my_turn or roll_count == 0:
        return None

    if not available_selections:
        st.info("No more dice to select. Roll again or Bank your Earthlings!")
        return None

    st.markdown("**Select a group:**")

    # Order: Earthlings first, then Death Rays
    type_order = [FaceType.HUMAN, FaceType.COW, FaceType.CHICKEN, FaceType.DEATH_RAY]

    cols = st.columns(len(available_selections))
    col_idx = 0

    selected_type = None

    for face_type in type_order:
        if face_type not in available_selections:
            continue

        with cols[col_idx]:
            indices = available_selections[face_type]
            count = len(indices)

            # Get emoji and label (FaceType uses underscores, display uses hyphens)
            display_name = face_type.value.replace("_", "-")
            emoji = TYPE_TO_EMOJI.get(display_name, "")
            label = face_type.value.replace("_", " ").title()

            # Button text
            button_text = f"{emoji} {label} ({count})"

            # Unique key per type and roll
            key = f"select_{face_type.value}_r{roll_count}"

            if st.button(button_text, key=key, use_container_width=True):
                selected_type = face_type

        col_idx += 1

    return selected_type


def render_set_aside_dice(
    selected_earthling_types: list[str],
    death_rays_count: int,
    tanks_count: int,
    scoring_result: AlienInvasionScoringResult,
) -> None:
    """
    Render set-aside dice grouped by type (Earthlings, Death Rays, Tanks).

    Args:
        selected_earthling_types: Repeated type names, e.g. ["human","human","cow"]
        death_rays_count: Total death rays set aside
        tanks_count: Total tanks auto-locked
        scoring_result: AlienInvasionScoringResult for status line
    """
    # Inject background-image CSS (needed for mini dice)
    _inject_dice_face_css()

    # Status line
    if scoring_result.is_safe_to_bank:
        status_color = "#4ecca3"
        status_text = f"✅ SAFE TO BANK: {scoring_result.total_points} PTS"
    else:
        deficit = tanks_count - death_rays_count
        status_color = "#ff2e2e"
        status_text = f"⚠️ BUST: TANKS ({tanks_count}) > DEATH RAYS ({death_rays_count})"

    # Count earthlings by sub-type
    earthling_counts = Counter(selected_earthling_types)

    # Build HTML
    parts = [
        f'<div class="set-aside-container">',
        f'<div class="set-aside-status" style="color: {status_color};">{status_text}</div>',
    ]

    # Earthling rows
    earthling_rows = [
        ("👤 Humans:", "human", earthling_counts.get("human", 0)),
        ("🐄 Cows:", "cow", earthling_counts.get("cow", 0)),
        ("🐔 Chickens:", "chicken", earthling_counts.get("chicken", 0)),
    ]

    for label, face_css, count in earthling_rows:
        parts.append(f'<div class="set-aside-section">')
        parts.append(f'<span class="set-aside-label">{label}</span>')
        parts.append(f'<span class="set-aside-dice">')
        if count > 0:
            for _ in range(count):
                parts.append(
                    f'<div class="die alien-invasion set-aside face-{face_css}"></div>'
                )
        else:
            parts.append(f'<span class="set-aside-empty">—</span>')
        parts.append(f'</span></div>')

    # Death Rays row
    parts.append(f'<div class="set-aside-section">')
    parts.append(f'<span class="set-aside-label">⚡ Death Rays:</span>')
    parts.append(f'<span class="set-aside-dice">')
    if death_rays_count > 0:
        for _ in range(death_rays_count):
            parts.append(
                f'<div class="die alien-invasion set-aside face-death-ray"></div>'
            )
    else:
        parts.append(f'<span class="set-aside-empty">—</span>')
    parts.append(f'</span></div>')

    # Tanks row
    parts.append(f'<div class="set-aside-section">')
    parts.append(f'<span class="set-aside-label">🔺 Tanks:</span>')
    parts.append(f'<span class="set-aside-dice">')
    if tanks_count > 0:
        for _ in range(tanks_count):
            parts.append(
                f'<div class="die alien-invasion set-aside face-tank auto-locked"></div>'
            )
    else:
        parts.append(f'<span class="set-aside-empty">—</span>')
    parts.append(f'</span></div>')

    parts.append(f'</div>')

    st.markdown("".join(parts), unsafe_allow_html=True)
