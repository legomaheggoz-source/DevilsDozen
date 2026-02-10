"""Home page — title, mode descriptions, lobby creation/joining."""

from __future__ import annotations

import streamlit as st

from src.ui.components.lobby import render_lobby


def render_home_page() -> None:
    """Render the home / landing page."""
    st.title("Devil's Dozen")
    st.caption("Medieval dice games of risk and reward")

    # Lobby creation/joining
    render_lobby()

    st.divider()

    # Game mode descriptions (below lobby)
    with st.expander("Peasant's Gamble (D6) — Rules"):
        st.markdown(
            """
**Roll six dice and press your luck!**

- **Single 1** = 100 pts | **Single 5** = 50 pts
- **Three of a kind** = face value x 100 (three 1s = 1,000)
- **Four+** of a kind = previous tier x 2
- **Straights**: 1-5 = 500 | 2-6 = 750 | 1-6 = 1,500
- **Bust** = no scoring dice; lose your unbanked turn score
- **Hot Dice** = all dice score; pick them all up and roll again!

Hold scoring dice, then roll the rest. Bank your turn score
or keep rolling — but beware the bust!
"""
        )

    with st.expander("Alchemist's Ascent (D20) — Rules"):
        st.markdown(
            """
**Climb three tiers to reach 250 points!**

**Tier 1 — Red (0-100 pts):** Roll 8 D20s. Score singles (1 & 5),
pairs, three-of-a-kind (sum), and sequences (3+ consecutive = 10 pts each).
Bank or roll again (all dice re-rolled).

**Tier 2 — Green (101-200 pts):** Roll 3 D20s with a **5x multiplier**.
You may reroll individual dice, but if the new value is *lower*,
you bust!

**Tier 3 — Blue (201-250 pts):** Roll 1 D20.
- Roll **1** = reset to 0 points!
- Roll **20** = Kingmaker (give 20 pts to last place)
- Anything else = face value added to your score
"""
        )

    with st.expander("Knucklebones (Grid Battle) — Rules"):
        st.markdown(
            """
**A 2-player strategic dice placement game!**

**Setup:**
- Each player has a 3×3 grid
- Take turns rolling a single D6 and placing it

**The Crunch:**
- When you place a die, **all matching opponent dice in the same column are destroyed!**
- Destroyed dice are removed from their grid (and their score)

**Scoring (per column):**
- **Single die:** face value (e.g., [4] = 4 pts)
- **Pair (2 of kind):** sum × 2 (e.g., [4, 4] = 16 pts)
- **Triple (3 of kind):** sum × 3 (e.g., [4, 4, 4] = 36 pts)
- **Mixed values:** sum only (e.g., [4, 6] = 10 pts)

**Example:** Column with [4, 4, 6] scores (4+4)×2 + 6 = 22 points

**Grid Lock:**
- Game ends when **any grid is completely full**
- Highest total score wins!
- Ties are possible

**No busting, no banking — pure placement strategy!**
"""
        )
