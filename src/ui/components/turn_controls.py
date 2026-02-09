"""Turn control buttons — Roll, Bank, End Turn."""

from __future__ import annotations

import streamlit as st


def render_turn_controls(
    is_my_turn: bool,
    roll_count: int,
    has_held: bool,
    is_bust: bool,
    is_hot_dice: bool,
    turn_score: int,
    game_mode: str,
    tier: int = 1,
) -> str | None:
    """Render contextual turn-action buttons.

    Returns:
        ``"roll"``, ``"bank"``, ``"end_turn"``, or ``None`` if no action taken.
    """
    if not is_my_turn:
        if roll_count > 0:
            st.caption("Watching opponent's turn...")
        else:
            st.info("Waiting for opponent to roll...")
        return None

    # --- Bust state ---
    if is_bust:
        if st.button("End Turn", key="btn_end_turn", use_container_width=True):
            return "end_turn"
        return None

    # D20 Tier 2: only show Bank + guidance (rerolls via dice tray)
    is_tier2 = game_mode == "alchemists_ascent" and tier == 2

    if is_tier2 and roll_count > 0:
        if turn_score > 0:
            if st.button(
                f"Bank {turn_score} pts",
                key=f"btn_bank_{roll_count}",
                use_container_width=True,
                type="primary",
            ):
                return "bank"
        else:
            if st.button(
                "End Turn (0 pts)",
                key="btn_end_turn",
                use_container_width=True,
            ):
                return "end_turn"
        st.caption("Tap **Reroll** on individual dice above to try for higher values.")
        return None

    cols = st.columns(2)

    # --- Roll button ---
    with cols[0]:
        if roll_count == 0:
            roll_label = "Roll Dice"
            roll_disabled = False
        elif is_hot_dice:
            roll_label = "Roll Again (Hot Dice!)"
            roll_disabled = False
        elif has_held:
            roll_label = "Roll Again"
            roll_disabled = False
        else:
            roll_label = "Roll Again"
            # D20 Tier 3: auto-apply, no hold needed
            if game_mode == "alchemists_ascent" and tier == 3:
                roll_disabled = False
            else:
                # D6 and D20 Tier 1: must hold at least one scoring die first
                roll_disabled = roll_count > 0

        if st.button(
            roll_label,
            key=f"btn_roll_{roll_count}",
            use_container_width=True,
            disabled=roll_disabled,
            type="primary",
        ):
            return "roll"

    # --- Bank button ---
    with cols[1]:
        can_bank = roll_count > 0 and turn_score > 0 and not is_bust

        # D20 Tier 3: no banking, result is auto-applied
        if game_mode == "alchemists_ascent" and tier == 3:
            can_bank = False

        if st.button(
            f"Bank {turn_score} pts" if turn_score > 0 else "Bank",
            key=f"btn_bank_{roll_count}",
            use_container_width=True,
            disabled=not can_bank,
        ):
            return "bank"

    return None
