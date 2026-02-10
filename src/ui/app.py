"""Devil's Dozen — Streamlit Application Entrypoint."""

from __future__ import annotations

import streamlit as st


_D6_RULES = """\
**Goal:** First to the target score wins!

**Rolling:**
- Roll 6 dice — must hold at least one scoring die
- Keep rolling remaining dice to build your turn score
- **Bust** = no scoring dice — lose all unbanked points
- **Hot Dice** = all 6 score — roll all 6 fresh!

**Scoring:**
| Combo | Points |
|---|---|
| Single 1 | 100 |
| Single 5 | 50 |
| Three 1s | 1,000 |
| Three 2s-6s | Face x 100 |
| Four+ of a kind | Previous x 2 |
| 1-2-3-4-5 | 500 |
| 2-3-4-5-6 | 750 |
| 1-2-3-4-5-6 | 1,500 |
"""

_D20_RULES = """\
**Goal:** First to **250 points** wins!

**Tier 1 — Red (0-100 pts):** Roll 8 D20s
- Single 1 = 1 pt | Single 5 = 5 pts
- Pair of 1s = 10 | Pair of 5s = 20
- Three+ of a kind = sum of matching dice
- Sequence of 3+ = 10 pts per die
- Hold scoring dice, roll the rest
- **Hot Dice** = all 8 score — roll all 8 fresh!
- Bust = no scoring dice, lose unbanked points

**Tier 2 — Green (101-200 pts):** Roll 3 D20s
- Same scoring as Tier 1 but **x5 multiplier**
- May reroll individual dice
- If new value <= old value = **Bust!**

**Tier 3 — Blue (201-250 pts):** Roll 1 D20
- Roll **1** = Reset to 0 pts!
- Roll **20** = Give 20 pts to last-place player
- Roll 2-19 = Face value added to score
"""

_KNUCKLEBONES_RULES = """\
**Goal:** Highest score when any grid fills!

**Gameplay:**
- 2 players, each with 3×3 grid
- Roll 1 D6 → Place in any column (if not full)
- **The Crunch:** Matching opponent dice in same column are destroyed
- Turn ends automatically after placement

**Scoring (per column):**
| Combo | Points |
|---|---|
| Single die | Face value |
| Pair (2 of kind) | Sum × 2 |
| Triple (3 of kind) | Sum × 3 |

**Example:** Column with [4, 4, 6] scores (4+4)×2 + 6 = 22

**Grid Lock:** Game ends when either grid is full!
"""


def _render_sidebar_rules(game_mode: str) -> None:
    """Show rules for the current game mode in the sidebar."""
    with st.sidebar:
        st.divider()
        if game_mode == "peasants_gamble":
            st.markdown("### Peasant's Gamble Rules")
            st.markdown(_D6_RULES)
        elif game_mode == "alchemists_ascent":
            st.markdown("### Alchemist's Ascent Rules")
            st.markdown(_D20_RULES)
        elif game_mode == "knucklebones":
            st.markdown("### Knucklebones Rules")
            st.markdown(_KNUCKLEBONES_RULES)


def main() -> None:
    """Application entrypoint. Must call ``st.set_page_config`` first."""
    st.set_page_config(
        page_title="Devil's Dozen",
        page_icon="🎲",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Load medieval theme CSS and sound system
    from src.ui.themes import (
        load_css,
        render_audio_system,
        render_sound_controls,
    )
    load_css()

    # Session state defaults
    if "page" not in st.session_state:
        st.session_state["page"] = "home"
    if "_prior_roll_score" not in st.session_state:
        st.session_state["_prior_roll_score"] = 0

    # Page routing (lazy imports to avoid circular deps)
    page = st.session_state["page"]

    if page == "home" or page == "lobby_waiting":
        from src.ui.views.home import render_home_page
        render_home_page()
    elif page == "game":
        from src.ui.views.game import render_game_page
        render_game_page()
    elif page == "results":
        from src.ui.views.results import render_results_page
        render_results_page()
    else:
        st.session_state["page"] = "home"
        st.rerun()

    # Sound system (sidebar controls + JS-cached audio)
    render_sound_controls()
    game_mode = st.session_state.get("game_mode")
    render_audio_system(page, game_mode)

    # In-game rules in sidebar
    if page == "game" and game_mode:
        _render_sidebar_rules(game_mode)


if __name__ == "__main__":
    main()
