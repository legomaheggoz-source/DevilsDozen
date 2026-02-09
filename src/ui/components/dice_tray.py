"""Dice tray component — renders dice with hold/reroll controls."""

from __future__ import annotations

import streamlit as st


def render_dice_tray(
    dice: list[int],
    held_indices: set[int],
    scoring_indices: set[int],
    is_my_turn: bool,
    dice_type: str,
    tier: int,
    roll_count: int,
    disabled: bool = False,
) -> set[int]:
    """Render dice with interactive hold/reroll buttons.

    Args:
        dice: Current dice face values.
        held_indices: Indices currently held.
        scoring_indices: Indices of dice that scored on this roll.
        is_my_turn: Whether it's the local player's turn.
        dice_type: ``"d6"`` or ``"d20"``.
        tier: Current tier (1-3). Only meaningful for d20.
        roll_count: Current roll number (used in button keys).
        disabled: Force-disable all buttons.

    Returns:
        Set of newly-toggled hold indices (empty if nothing changed).
    """
    if not dice:
        st.markdown(
            '<div class="dice-tray">'
            '<span style="color:var(--text-secondary);font-style:italic;">'
            "Roll the dice to begin your turn."
            "</span></div>",
            unsafe_allow_html=True,
        )
        return set()

    # Build the visual dice row via HTML
    is_d20 = dice_type == "d20"
    tier_class = ""
    if is_d20:
        tier_class = {1: "tier-red", 2: "tier-green", 3: "tier-blue"}.get(tier, "")

    html_parts = ['<div class="dice-tray">']
    for i, val in enumerate(dice):
        classes = ["die"]
        if is_d20:
            classes.append("d20")
        if i in held_indices:
            classes.append("held")
        elif i in scoring_indices:
            classes.append("scoring")
        if tier_class and is_d20:
            classes.append(tier_class)
        html_parts.append(
            f'<div class="{" ".join(classes)}">{val}</div>'
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

    # Buttons only when it's the active player's turn and dice have been rolled
    toggled: set[int] = set()
    show_buttons = is_my_turn and not disabled and roll_count > 0

    # D20 Tier 2: show per-die "Reroll" buttons
    if show_buttons and is_d20 and tier == 2:
        cols = st.columns(len(dice))
        for i, col in enumerate(cols):
            with col:
                key = f"reroll_{i}_r{roll_count}"
                if st.button("Reroll", key=key, use_container_width=True):
                    toggled.add(i)
        return toggled

    # D20 Tier 3: auto-apply, no buttons
    if is_d20 and tier == 3:
        return toggled

    # D6 and D20 Tier 1: show hold buttons for ALL dice positions
    if show_buttons:
        cols = st.columns(len(dice))
        for i, col in enumerate(cols):
            with col:
                if i in held_indices:
                    key = f"unhold_{i}_r{roll_count}"
                    if st.button("Held", key=key, use_container_width=True, type="primary"):
                        toggled.add(i)
                elif i in scoring_indices:
                    key = f"hold_{i}_r{roll_count}"
                    if st.button("Hold", key=key, use_container_width=True):
                        toggled.add(i)
                else:
                    # Non-scoring die — disabled button to keep alignment
                    key = f"nohold_{i}_r{roll_count}"
                    st.button("---", key=key, use_container_width=True, disabled=True)

    return toggled
