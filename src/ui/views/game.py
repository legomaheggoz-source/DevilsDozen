"""Game page — the main play area with dice, controls, and scoreboard."""

from __future__ import annotations

import time

import streamlit as st
from httpx import RemoteProtocolError

from src.database.client import get_supabase_client
from src.database.lobby import LobbyManager
from src.database.player import PlayerManager
from src.database.game_state import GameStateManager
from src.engine.peasants_gamble import PeasantsGambleEngine
from src.engine.alchemists_ascent import AlchemistsAscentEngine
from src.engine.base import Tier
from src.engine.knucklebones import KnuckleboneEngine, GridState
from src.engine.alien_invasion import (
    AlienInvasionEngine,
    AlienInvasionTurnState,
    FaceType,
)
from src.ui.components.dice_tray import render_dice_tray
from src.ui.components.scoreboard import render_scoreboard
from src.ui.components.turn_controls import render_turn_controls
from src.ui.components.knucklebones_board import render_knucklebones_board
from src.ui.components.dice_tray_alien import (
    render_alien_dice_tray,
    render_group_selection_buttons,
    render_set_aside_dice,
)
from src.ui.themes.animations import (
    render_bust_animation,
    render_hot_dice_animation,
    render_score_popup,
    render_tier_indicator,
)
from src.ui.themes.sounds import play_sfx


def _managers():
    client = get_supabase_client()
    return LobbyManager(client), PlayerManager(client), GameStateManager(client)


def _db_retry(fn, *args, retries=2, **kwargs):
    """Call *fn* with simple retry on transient connection errors."""
    for attempt in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except (RemoteProtocolError, ConnectionError, OSError) as exc:
            if attempt == retries:
                raise
            # Clear the cached client so next call creates a fresh connection
            get_supabase_client.cache_clear()
            time.sleep(0.3)


def render_game_page() -> None:
    """Render the main game page."""
    ss = st.session_state
    lobby_id = ss.get("lobby_id")
    player_id = ss.get("player_id")

    if not lobby_id or not player_id:
        ss["page"] = "home"
        st.rerun()
        return

    try:
        lobby_mgr, player_mgr, gs_mgr = _managers()

        lobby = _db_retry(lobby_mgr.get_by_id, lobby_id)
        if lobby is None:
            st.error("Lobby no longer exists.")
            ss["page"] = "home"
            st.rerun()
            return

        # Redirect if game finished
        if lobby.status == "finished":
            ss["page"] = "results"
            st.rerun()
            return

        players = _db_retry(player_mgr.list_by_lobby, lobby_id)
        game_state = _db_retry(gs_mgr.get, lobby_id)
    except Exception as exc:
        st.error(
            f"Connection error — please refresh the page. ({type(exc).__name__})"
        )
        # Show lobby code so player can rejoin if session is lost
        if lobby_id:
            _show_lobby_code_hint(lobby_id)
        return

    if not players or game_state is None:
        st.error("Game data not found.")
        return

    game_mode = lobby.game_mode
    ss["game_mode"] = game_mode  # Store for background music in app.py

    # Route to Knucklebones if that's the game mode
    if game_mode == "knucklebones":
        _render_knucklebones_game(lobby, players, game_state, player_id)
        return

    # Route to Alien Invasion if that's the game mode
    if game_mode == "alien_invasion":
        _render_alien_invasion_game(lobby, players, game_state, player_id)
        return

    is_d20 = game_mode == "alchemists_ascent"
    current_turn_index = lobby.current_turn_index
    active_player = players[current_turn_index] if current_turn_index < len(players) else players[0]
    is_my_turn = str(active_player.id) == player_id

    # Find my player for tier display
    my_player = next((p for p in players if str(p.id) == player_id), None)

    # --- Layout: game area (3) | scoreboard (1) ---
    game_col, score_col = st.columns([3, 1])

    with score_col:
        # Lobby code for reconnection
        st.caption(f"Lobby: **{lobby.code}**")

        # Tier indicator for D20 mode
        if is_d20 and my_player:
            tier_obj = AlchemistsAscentEngine.get_tier_for_score(my_player.total_score)
            tier_map = {
                Tier.RED: ("Red", "red"),
                Tier.GREEN: ("Green", "green"),
                Tier.BLUE: ("Blue", "blue"),
            }
            name, color = tier_map[tier_obj]
            render_tier_indicator(name, color)

            # Detect tier advancement
            prev_tier = ss.get("_last_tier")
            if prev_tier is not None and tier_obj.value > prev_tier:
                play_sfx("tier_advance")
            ss["_last_tier"] = tier_obj.value

        render_scoreboard(
            players=players,
            current_turn_index=current_turn_index,
            turn_score=game_state.turn_score,
            target_score=lobby.win_condition,
            my_player_id=player_id,
            game_mode=game_mode,
        )

    with game_col:
        st.subheader(f"{active_player.username}'s Turn")

        # Bust overlay
        if game_state.is_bust:
            render_bust_animation()

        # Hot dice banner
        if _check_hot_dice(game_state, game_mode):
            render_hot_dice_animation()
            play_sfx("hot_dice")

        # Dice tray
        scoring = _get_scoring_indices(game_state, game_mode)
        toggled = render_dice_tray(
            dice=game_state.active_dice,
            held_indices=set(game_state.held_indices),
            scoring_indices=scoring,
            is_my_turn=is_my_turn,
            dice_type="d20" if is_d20 else "d6",
            tier=game_state.tier,
            roll_count=game_state.roll_count,
            disabled=game_state.is_bust,
        )

        # Handle hold/unhold toggling (D6 and D20 Tier 1)
        # D20 Tier 2 reroll buttons handled separately
        if toggled and is_my_turn and not game_state.is_bust:
            if is_d20 and game_state.tier == 2:
                _handle_d20_reroll(toggled, game_state, gs_mgr, lobby)
            else:
                _handle_hold_toggle(toggled, game_state, gs_mgr, lobby_id, game_mode, game_state.tier)

        # Tier 3: show result message + Continue button (no normal controls)
        tier3_rolled = (
            is_d20
            and game_state.tier == 3
            and game_state.roll_count > 0
            and game_state.active_dice
        )

        if tier3_rolled:
            _show_tier3_result(game_state)
            if is_my_turn:
                if st.button(
                    "Continue",
                    key="btn_tier3_continue",
                    type="primary",
                    use_container_width=True,
                ):
                    _advance_turn(gs_mgr, lobby_mgr, lobby, players)
            else:
                st.caption("Waiting for player to continue...")
        else:
            # Score breakdown display
            if game_state.roll_count > 0 and not game_state.is_bust and game_state.active_dice:
                _show_score_breakdown(game_state, game_mode)

            # Turn controls
            action = render_turn_controls(
                is_my_turn=is_my_turn,
                roll_count=game_state.roll_count,
                has_held=len(game_state.held_indices) > 0,
                is_bust=game_state.is_bust,
                is_hot_dice=_check_hot_dice(game_state, game_mode),
                turn_score=game_state.turn_score,
                game_mode=game_mode,
                tier=game_state.tier,
            )

            if action == "roll":
                _handle_roll(game_state, gs_mgr, lobby, players, player_id)
            elif action == "bank":
                _handle_bank(game_state, gs_mgr, lobby_mgr, player_mgr, lobby, players, player_id)
            elif action == "end_turn":
                _advance_turn(gs_mgr, lobby_mgr, lobby, players)

    # Polling fragment for multiplayer sync
    _poll_game_state()


# === Action Handlers ===


def _handle_roll(game_state, gs_mgr, lobby, players, player_id):
    """Process a dice roll."""
    ss = st.session_state
    lobby_id = str(lobby.id)
    game_mode = lobby.game_mode
    is_d20 = game_mode == "alchemists_ascent"

    if is_d20:
        active_player = players[lobby.current_turn_index]
        current_score = active_player.total_score
        tier = AlchemistsAscentEngine.get_tier_for_score(current_score)

        if tier == Tier.RED:
            # Tier 1: subtract held dice when rolling again (like D6)
            base_count = AlchemistsAscentEngine.get_dice_count_for_tier(tier)
            is_hot = _check_hot_dice(game_state, game_mode)
            if game_state.roll_count == 0 or is_hot:
                dice_count = base_count
            else:
                dice_count = len(game_state.active_dice) - len(game_state.held_indices)
        else:
            dice_count = AlchemistsAscentEngine.get_dice_count_for_tier(tier)

        roll = AlchemistsAscentEngine.roll_dice(dice_count)
        dice_values = list(roll.values)

        if tier == Tier.BLUE:
            # Tier 3: auto-apply result
            play_sfx("dice_roll")
            _handle_tier3_roll(roll, current_score, active_player, players, gs_mgr, lobby, lobby_id)
            return

        if tier == Tier.GREEN:
            # Tier 2: every die scores face value × 5, NEVER busts on initial roll
            result = AlchemistsAscentEngine.calculate_score_tier2(roll.values)
            gs_mgr.update(
                lobby_id,
                active_dice=dice_values,
                held_indices=[],
                turn_score=result.points,
                is_bust=False,
                roll_count=game_state.roll_count + 1,
                tier=tier.value,
                previous_dice=dice_values,
            )
            play_sfx("dice_roll")
        else:
            # Tier 1: standard scoring with hold mechanic
            result = AlchemistsAscentEngine.calculate_score(roll.values, tier)

            if result.is_bust:
                gs_mgr.update(
                    lobby_id,
                    active_dice=dice_values,
                    held_indices=[],
                    turn_score=0,
                    is_bust=True,
                    roll_count=game_state.roll_count + 1,
                    tier=tier.value,
                    previous_dice=dice_values,
                )
                play_sfx("bust")
            else:
                # Auto-hold all scoring dice; player can unhold as desired
                ss["_prior_roll_score"] = game_state.turn_score
                auto_held = sorted(
                    _get_potentially_scoring_indices_d20_t1(dice_values)
                )
                held_vals = [dice_values[i] for i in auto_held]
                held_result = AlchemistsAscentEngine.calculate_score(
                    held_vals, tier
                )
                gs_mgr.update(
                    lobby_id,
                    active_dice=dice_values,
                    held_indices=auto_held,
                    turn_score=game_state.turn_score + held_result.points,
                    is_bust=False,
                    roll_count=game_state.roll_count + 1,
                    tier=tier.value,
                    previous_dice=dice_values,
                )
                play_sfx("dice_roll")
    else:
        # D6 mode
        # Before rolling, commit current turn_score as the prior baseline
        # so that hold-toggle on the new roll adds on top of it.
        ss["_prior_roll_score"] = game_state.turn_score

        is_hot = _check_hot_dice(game_state, game_mode)
        if game_state.roll_count == 0 or is_hot:
            dice_count = PeasantsGambleEngine.NUM_DICE
        else:
            available = len(game_state.active_dice) - len(game_state.held_indices)
            dice_count = available

        roll = PeasantsGambleEngine.roll_dice(dice_count)
        result = PeasantsGambleEngine.calculate_score(roll.values)
        dice_values = list(roll.values)

        if result.is_bust:
            gs_mgr.update(
                lobby_id,
                active_dice=dice_values,
                held_indices=[],
                turn_score=0,
                is_bust=True,
                roll_count=game_state.roll_count + 1,
            )
            ss["_prior_roll_score"] = 0
            play_sfx("bust")
        else:
            # Auto-hold all scoring dice; player can unhold as desired
            auto_held = sorted(result.scoring_dice_indices)
            gs_mgr.update(
                lobby_id,
                active_dice=dice_values,
                held_indices=auto_held,
                turn_score=ss["_prior_roll_score"] + result.points,
                is_bust=False,
                roll_count=game_state.roll_count + 1,
            )
            play_sfx("dice_roll")

    st.rerun()


def _handle_tier3_roll(roll, current_score, active_player, players, gs_mgr, lobby, lobby_id):
    """Handle Tier 3 single-die roll with special rules.

    Applies score changes immediately but does NOT advance the turn.
    The die stays visible so both players can see the result; the active
    player clicks 'Continue' to advance.
    """
    lobby_mgr, player_mgr, _ = _managers()
    dice_value = roll.values[0]

    # Find last-place player for kingmaker
    sorted_players = sorted(players, key=lambda p: p.total_score)
    last_place = sorted_players[0] if sorted_players else None
    last_place_id = str(last_place.id) if last_place and str(last_place.id) != str(active_player.id) else None

    points_delta, is_reset, is_kingmaker, beneficiary_id = (
        AlchemistsAscentEngine.calculate_score_tier3(dice_value, current_score, last_place_id)
    )

    if is_reset:
        player_mgr.update_score(str(active_player.id), 0)
    elif is_kingmaker:
        if beneficiary_id:
            beneficiary = player_mgr.get(beneficiary_id)
            if beneficiary:
                player_mgr.update_score(beneficiary_id, beneficiary.total_score + 20)
    else:
        new_total = current_score + points_delta
        player_mgr.update_score(str(active_player.id), new_total)

        # Check win
        if new_total >= AlchemistsAscentEngine.TARGET_SCORE:
            lobby_mgr.set_winner(lobby_id, str(active_player.id))
            st.session_state["page"] = "results"
            st.rerun()
            return

    # Write the die to game_state — keep tier=3 so UI shows result display
    gs_mgr.update(
        lobby_id,
        active_dice=list(roll.values),
        held_indices=[],
        turn_score=0,
        is_bust=False,
        roll_count=1,
        tier=3,
    )
    st.rerun()


def _handle_hold_toggle(toggled, game_state, gs_mgr, lobby_id, game_mode="peasants_gamble", tier=1):
    """Process hold/unhold of dice (D6 and D20 Tier 1)."""
    current_held = set(game_state.held_indices)

    for idx in toggled:
        if idx in current_held:
            current_held.discard(idx)
        else:
            current_held.add(idx)

    # Recalculate turn_score based on all currently held dice
    if current_held and game_state.active_dice:
        held_values = [game_state.active_dice[i] for i in sorted(current_held)]
        if game_mode == "alchemists_ascent":
            tier_enum = {1: Tier.RED, 2: Tier.GREEN}.get(tier, Tier.RED)
            result = AlchemistsAscentEngine.calculate_score(held_values, tier_enum)
        else:
            result = PeasantsGambleEngine.calculate_score(held_values)
        prior_score = st.session_state.get("_prior_roll_score", 0)
        new_turn_score = prior_score + result.points
    else:
        new_turn_score = st.session_state.get("_prior_roll_score", 0)

    gs_mgr.update(
        lobby_id,
        held_indices=sorted(current_held),
        turn_score=new_turn_score,
    )
    st.rerun()


def _handle_d20_reroll(toggled, game_state, gs_mgr, lobby):
    """Handle Tier 2 per-die reroll."""
    lobby_id = str(lobby.id)
    die_index = next(iter(toggled))
    previous_values = tuple(game_state.active_dice)

    reroll_result = AlchemistsAscentEngine.process_reroll(die_index, previous_values)

    new_dice = list(game_state.active_dice)
    new_dice[die_index] = reroll_result.new_value

    if reroll_result.is_bust:
        gs_mgr.update(
            lobby_id,
            active_dice=new_dice,
            turn_score=0,
            is_bust=True,
            previous_dice=list(previous_values),
        )
        play_sfx("bust")
    else:
        # Recalculate score with updated dice
        result = AlchemistsAscentEngine.calculate_score_tier2(new_dice)
        gs_mgr.update(
            lobby_id,
            active_dice=new_dice,
            turn_score=result.points,
            is_bust=False,
            previous_dice=list(previous_values),
        )
        play_sfx("dice_roll")

    st.rerun()


def _handle_bank(game_state, gs_mgr, lobby_mgr, player_mgr, lobby, players, player_id):
    """Bank the turn score and check win condition."""
    lobby_id = str(lobby.id)
    current_turn_index = lobby.current_turn_index
    active_player = players[current_turn_index]

    turn_score = game_state.turn_score

    # Ensure final held dice are scored before banking
    if game_state.held_indices and game_state.active_dice:
        held_values = [game_state.active_dice[i] for i in sorted(game_state.held_indices)]
        if lobby.game_mode == "alchemists_ascent":
            tier_enum = {1: Tier.RED, 2: Tier.GREEN}.get(game_state.tier, Tier.RED)
            result = AlchemistsAscentEngine.calculate_score(held_values, tier_enum)
        else:
            result = PeasantsGambleEngine.calculate_score(held_values)
        prior_score = st.session_state.get("_prior_roll_score", 0)
        turn_score = prior_score + result.points

    new_total = active_player.total_score + turn_score
    player_mgr.update_score(str(active_player.id), new_total)
    play_sfx("bank")

    # Check win
    target = lobby.win_condition
    if new_total >= target:
        lobby_mgr.set_winner(str(lobby.id), str(active_player.id))
        st.session_state["page"] = "results"
        st.rerun()
        return

    # Advance turn
    _advance_turn(gs_mgr, lobby_mgr, lobby, players)


def _advance_turn(gs_mgr, lobby_mgr, lobby, players):
    """Reset game state and advance to the next player."""
    lobby_id = str(lobby.id)
    next_index = (lobby.current_turn_index + 1) % len(players)

    gs_mgr.reset_turn(lobby_id)
    lobby_mgr.advance_turn(lobby_id, next_index)

    # Reset tracked prior score
    st.session_state["_prior_roll_score"] = 0
    st.rerun()


# === Helpers ===


def _show_lobby_code_hint(lobby_id: str) -> None:
    """Try to show the lobby code so player can rejoin."""
    try:
        lobby_mgr, _, _ = _managers()
        lobby = lobby_mgr.get_by_id(lobby_id)
        if lobby:
            st.info(f"Your lobby code is **{lobby.code}** — use it to rejoin after refreshing.")
    except Exception:
        pass


def _get_scoring_indices(game_state, game_mode: str) -> set[int]:
    """Calculate which dice in the current roll are scoring."""
    if not game_state.active_dice or game_state.is_bust:
        return set()

    if game_mode == "alchemists_ascent":
        tier = {1: Tier.RED, 2: Tier.GREEN, 3: Tier.BLUE}.get(game_state.tier, Tier.RED)
        if tier == Tier.BLUE:
            return {0}  # Single die always "scores"
        if tier == Tier.GREEN:
            # Tier 2: Tier 1 scoring rules × 5 — highlight combo dice
            result = AlchemistsAscentEngine.calculate_score(game_state.active_dice, tier)
            return set(result.scoring_dice_indices)
        # Tier 1: show hold buttons for ALL potentially-scoring dice
        return _get_potentially_scoring_indices_d20_t1(list(game_state.active_dice))
    else:
        result = PeasantsGambleEngine.calculate_score(game_state.active_dice)
        return set(result.scoring_dice_indices)


def _get_potentially_scoring_indices_d20_t1(dice: list[int]) -> set[int]:
    """Get all dice indices that could participate in any D20 Tier 1 scoring combo.

    A die is potentially scoring if it:
    - Is a 1 or 5 (always scores as single)
    - Has at least one duplicate (pair/triple potential)
    - Is part of a consecutive sequence of 3+ among the roll values
    """
    from collections import Counter as Ctr

    scoring: set[int] = set()
    counts = Ctr(dice)
    sorted_unique = sorted(set(dice))

    # Find all values that belong to a consecutive run of 3+
    seq_values: set[int] = set()
    i = 0
    while i < len(sorted_unique):
        seq = [sorted_unique[i]]
        j = i + 1
        while j < len(sorted_unique) and sorted_unique[j] == seq[-1] + 1:
            seq.append(sorted_unique[j])
            j += 1
        if len(seq) >= 3:
            seq_values.update(seq)
        i = j if j > i + 1 else i + 1

    for idx, val in enumerate(dice):
        if val in (1, 5):
            scoring.add(idx)
        if counts[val] >= 2:
            scoring.add(idx)
        if val in seq_values:
            scoring.add(idx)

    return scoring


def _check_hot_dice(game_state, game_mode: str) -> bool:
    """Check if hot dice condition is met."""
    if not game_state.active_dice or game_state.is_bust:
        return False
    if game_mode == "alchemists_ascent":
        # D20 Tier 1: hot dice when ALL dice are held
        if game_state.tier == 1 and game_state.held_indices:
            return len(game_state.held_indices) == len(game_state.active_dice)
        return False
    return PeasantsGambleEngine.is_hot_dice(game_state.active_dice)


def _show_tier3_result(game_state):
    """Show what happened on a Tier 3 (Blue) die roll."""
    die_value = game_state.active_dice[0]
    if die_value == 1:
        st.error("**RESET!** Score has been reset to 0!")
    elif die_value == 20:
        st.warning("**KINGMAKER!** 20 pts given to last place player")
    else:
        st.success(f"**+{die_value} pts**")


def _show_score_breakdown(game_state, game_mode: str):
    """Show a brief score breakdown for the current roll."""
    if not game_state.active_dice:
        return

    if game_mode == "alchemists_ascent":
        tier = {1: Tier.RED, 2: Tier.GREEN, 3: Tier.BLUE}.get(game_state.tier, Tier.RED)
        if tier == Tier.BLUE:
            return  # Tier 3 handled differently
        result = AlchemistsAscentEngine.calculate_score(game_state.active_dice, tier)
    else:
        result = PeasantsGambleEngine.calculate_score(game_state.active_dice)

    if result.points > 0:
        render_score_popup(result.points)
        with st.expander("Score Breakdown", expanded=False):
            for item in result.breakdown:
                st.markdown(f"- **{item.description}**: {item.points} pts")


@st.fragment(run_every=2)
def _poll_game_state() -> None:
    """Poll for opponent updates every 2 seconds.

    Triggers a full-app rerun when meaningful state changes are detected,
    so the spectating player sees the opponent's dice, busts, etc.
    """
    ss = st.session_state
    lobby_id = ss.get("lobby_id")
    player_id = ss.get("player_id")
    if not lobby_id or not player_id:
        return

    try:
        lobby_mgr, player_mgr, gs_mgr = _managers()
        lobby = _db_retry(lobby_mgr.get_by_id, lobby_id)
        if lobby is None:
            return
    except Exception:
        return  # Silently skip this poll cycle on connection error

    # Check if game finished
    if lobby.status == "finished":
        ss["page"] = "results"
        st.rerun(scope="app")
        return

    try:
        game_state = _db_retry(gs_mgr.get, lobby_id)
    except Exception:
        return

    needs_rerun = False

    # Detect turn changes
    prev_turn = ss.get("_last_turn_index")
    if prev_turn is not None and prev_turn != lobby.current_turn_index:
        ss["_prior_roll_score"] = 0
        needs_rerun = True
    ss["_last_turn_index"] = lobby.current_turn_index

    # Detect dice/roll changes so spectators see opponent's moves
    if game_state:
        prev_roll = ss.get("_last_roll_count")
        prev_dice = ss.get("_last_active_dice")
        if prev_roll is not None and prev_roll != game_state.roll_count:
            needs_rerun = True
        if prev_dice is not None and prev_dice != game_state.active_dice:
            needs_rerun = True
        ss["_last_roll_count"] = game_state.roll_count
        ss["_last_active_dice"] = list(game_state.active_dice)

    if needs_rerun:
        st.rerun(scope="app")


# === Knucklebones Mode ===


def _render_knucklebones_game(lobby, players, game_state, player_id):
    """Render Knucklebones game mode."""
    ss = st.session_state
    lobby_id = str(lobby.id)

    # Knucklebones is always 2-player
    if len(players) != 2:
        st.error("Knucklebones requires exactly 2 players.")
        return

    current_turn_index = lobby.current_turn_index
    active_player = players[current_turn_index]
    is_my_turn = str(active_player.id) == player_id

    # Find my turn order (0 or 1)
    my_turn_order = next((i for i, p in enumerate(players) if str(p.id) == player_id), 0)

    # Convert grids to GridState for score calculation
    p1_grid = GridState.from_dict(game_state.player1_grid)
    p2_grid = GridState.from_dict(game_state.player2_grid)

    # Calculate current scores from grids
    p1_score = KnuckleboneEngine.calculate_grid_score(p1_grid)
    p2_score = KnuckleboneEngine.calculate_grid_score(p2_grid)

    # --- Layout: board (3) | controls (1) ---
    board_col, controls_col = st.columns([3, 1])

    with controls_col:
        st.caption(f"Lobby: **{lobby.code}**")

        # Knucklebones scoreboard
        st.markdown("### 📊 Scores")
        for i, player in enumerate(players):
            score = p1_score if i == 0 else p2_score
            is_active = i == current_turn_index
            is_me = str(player.id) == player_id

            css_classes = []
            if is_active:
                css_classes.append("active")
            if is_me:
                css_classes.append("is-me")

            css_class = " ".join(css_classes)
            st.markdown(
                f'<div class="player-row {css_class}">'
                f'<span class="name">{player.username}</span>'
                f'<span class="score">{score}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.divider()

        # Current die display (if rolled)
        if game_state.current_die_value:
            st.markdown("### 🎲 Rolled Die")
            # Use same die styling as D6 mode (just the number, not Unicode)
            st.markdown(
                f'<div class="dice-tray" style="min-height: auto; padding: 12px;">'
                f'<div class="die">{game_state.current_die_value}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        # Action buttons
        column_clicked = None
        if is_my_turn:
            if game_state.current_die_value is None:
                # No die rolled yet - show roll button
                if st.button(
                    "🎲 Roll Die",
                    key="roll_kb",
                    type="primary",
                    use_container_width=True,
                ):
                    _handle_knucklebones_roll(game_state, lobby_id)
            else:
                # Die rolled - show placement buttons
                st.markdown("**Place in column:**")
                my_grid = p1_grid if my_turn_order == 0 else p2_grid
                available_columns = KnuckleboneEngine.get_available_columns(my_grid)

                for col_idx in range(3):
                    is_full = col_idx not in available_columns
                    button_label = "FULL" if is_full else f"Column {col_idx + 1}"

                    if st.button(
                        button_label,
                        key=f"place_col_{col_idx}",
                        disabled=is_full,
                        use_container_width=True,
                        type="primary" if not is_full else "secondary"
                    ):
                        column_clicked = col_idx
        else:
            if game_state.current_die_value is None:
                st.info("Waiting for opponent to roll...")
            else:
                st.info("Waiting for opponent to place die...")

        # Handle placement after rendering (outside callback)
        if column_clicked is not None:
            _handle_knucklebones_placement(
                column_clicked,
                game_state,
                lobby,
                players,
                my_turn_order,
            )

    with board_col:
        st.subheader(f"{active_player.username}'s Turn")

        # Render the board (grids only)
        render_knucklebones_board(
            player1_grid=game_state.player1_grid,
            player2_grid=game_state.player2_grid,
            my_turn_order=my_turn_order,
            player1_name=players[0].username,
            player2_name=players[1].username,
        )

    # Polling fragment for multiplayer sync
    _poll_game_state()


def _handle_knucklebones_roll(game_state, lobby_id):
    """Roll a single D6 for Knucklebones."""
    die_value = KnuckleboneEngine.roll_die()

    lobby_mgr, _, gs_mgr = _managers()
    _db_retry(
        gs_mgr.update_knucklebones,
        lobby_id,
        current_die_value=die_value,
    )

    play_sfx("dice_roll")
    st.rerun()


def _handle_knucklebones_placement(column_idx, game_state, lobby, players, my_turn_order):
    """Handle placing a die in a column."""
    lobby_id = str(lobby.id)
    die_value = game_state.current_die_value

    if die_value is None:
        return

    # Convert dicts to GridState
    p1_grid = GridState.from_dict(game_state.player1_grid)
    p2_grid = GridState.from_dict(game_state.player2_grid)

    # Determine which grid is player's and which is opponent's
    if my_turn_order == 0:
        player_grid = p1_grid
        opponent_grid = p2_grid
    else:
        player_grid = p2_grid
        opponent_grid = p1_grid

    try:
        # Place the die
        result = KnuckleboneEngine.place_die(die_value, column_idx, player_grid, opponent_grid)

        # Update grids in database
        if my_turn_order == 0:
            new_p1 = result.player_grid.to_dict()
            new_p2 = result.opponent_grid.to_dict()
        else:
            new_p1 = result.opponent_grid.to_dict()
            new_p2 = result.player_grid.to_dict()

        lobby_mgr, player_mgr, gs_mgr = _managers()

        # Play appropriate sound
        if result.destroyed_count > 0:
            play_sfx("die_destroy")
        else:
            play_sfx("place_die")

        # Check if game is over
        if KnuckleboneEngine.is_game_over(result.player_grid, result.opponent_grid):
            # Calculate final scores
            p1_final = KnuckleboneEngine.calculate_grid_score(
                GridState.from_dict(new_p1)
            )
            p2_final = KnuckleboneEngine.calculate_grid_score(
                GridState.from_dict(new_p2)
            )

            # Update grids without clearing die yet
            _db_retry(
                gs_mgr.update_knucklebones,
                lobby_id,
                player1_grid=new_p1,
                player2_grid=new_p2,
            )

            # Update player scores
            _db_retry(player_mgr.update_score, str(players[0].id), p1_final)
            _db_retry(player_mgr.update_score, str(players[1].id), p2_final)

            # Determine winner
            winner_idx = KnuckleboneEngine.get_winner(
                GridState.from_dict(new_p1),
                GridState.from_dict(new_p2)
            )

            if winner_idx is not None:
                winner_id = str(players[winner_idx - 1].id)
                _db_retry(lobby_mgr.set_winner, lobby_id, winner_id)
                play_sfx("victory")
            else:
                # Tie (no winner)
                _db_retry(lobby_mgr.update_status, lobby_id, "finished")

            st.session_state["page"] = "results"
            st.rerun()
            return

        # Game continues - advance turn FIRST, then clear die
        new_turn_index = 1 if lobby.current_turn_index == 0 else 0
        _db_retry(lobby_mgr.advance_turn, lobby_id, new_turn_index)

        # Now update grids and clear the die (so next player sees None)
        _db_retry(
            gs_mgr.update_knucklebones,
            lobby_id,
            player1_grid=new_p1,
            player2_grid=new_p2,
            current_die_value=None,
        )

        st.rerun()

    except ValueError as e:
        st.error(f"Cannot place die: {e}")
        return


# === Alien Invasion Game Mode ===


def _render_alien_invasion_game(lobby, players, game_state, player_id):
    """Render the Alien Invasion (Martian Dice) game mode."""
    ss = st.session_state
    lobby_id = str(lobby.id)

    lobby_mgr, player_mgr, gs_mgr = _managers()

    current_turn_index = lobby.current_turn_index
    active_player = players[current_turn_index] if current_turn_index < len(players) else players[0]
    is_my_turn = str(active_player.id) == player_id

    # Build Alien Invasion turn state from DB state
    turn_state = AlienInvasionTurnState(
        active_dice=tuple(game_state.active_dice),
        held_indices=frozenset(game_state.held_indices),
        tanks_count=game_state.tanks_count,
        death_rays_count=game_state.death_rays_count,
        earthlings_count=game_state.earthlings_count,
        selected_types=tuple(game_state.selected_earthling_types),
        turn_score=game_state.turn_score,
        roll_count=game_state.roll_count,
    )

    # --- "Must select before rerolling" flag ---
    # Reset when turn changes (roll_count == 0)
    if turn_state.roll_count == 0:
        ss["_alien_needs_selection"] = False
    needs_selection = ss.get("_alien_needs_selection", False)

    # --- Immediate bust detection ---
    # A true immediate bust means: even if you set aside every visible
    # death ray right now AND rolled all remaining dice as death rays on
    # future rolls, you still can't reach enough to match the tanks.
    #
    # After taking visible death rays, the unheld non-ray dice become
    # the pool for the next roll — every one of those *could* be a
    # death ray.  So max theoretical rays = set-aside + visible + remaining.
    is_immediate_bust = False
    if turn_state.roll_count > 0 and turn_state.active_dice:
        visible_death_rays = sum(
            1 for i, v in enumerate(turn_state.active_dice)
            if i not in turn_state.held_indices and v in (4, 5)
        )
        # Unheld dice that are NOT death rays = future reroll pool
        remaining_after_select = sum(
            1 for i, v in enumerate(turn_state.active_dice)
            if i not in turn_state.held_indices and v not in (4, 5)
        )
        max_possible_rays = (
            turn_state.death_rays_count + visible_death_rays + remaining_after_select
        )
        is_immediate_bust = turn_state.tanks_count > max_possible_rays

    # --- Layout: game area (3) | scoreboard (1) ---
    game_col, score_col = st.columns([3, 1])

    with score_col:
        st.caption(f"Lobby: **{lobby.code}**")

        render_scoreboard(
            players=players,
            current_turn_index=current_turn_index,
            turn_score=game_state.turn_score,
            target_score=lobby.win_condition,
            my_player_id=player_id,
            game_mode="alien_invasion",
        )

    with game_col:
        st.subheader(f"{active_player.username}'s Turn")

        # Render dice tray (active dice with held styling)
        auto_locked_indices = set()
        if turn_state.active_dice:
            classification = AlienInvasionEngine.classify_dice(turn_state.active_dice)
            auto_locked_indices = set(classification[FaceType.TANK])

        render_alien_dice_tray(
            dice=game_state.active_dice,
            held_indices=set(game_state.held_indices),
            auto_locked_indices=auto_locked_indices,
            is_my_turn=is_my_turn,
            roll_count=game_state.roll_count,
        )

        # --- Immediate bust: show bust message + forced end turn ---
        if is_immediate_bust:
            st.error(
                f"💀 IMMEDIATE BUST! Tanks ({turn_state.tanks_count}) outnumber "
                f"the maximum possible Death Rays ({max_possible_rays}) even if "
                f"every remaining die were a Death Ray. No recovery possible!"
            )
            if is_my_turn:
                if st.button(
                    "End Turn (0 pts)",
                    key="btn_immediate_bust",
                    type="primary",
                    use_container_width=True,
                ):
                    _handle_alien_invasion_end_turn_bust(gs_mgr, lobby_mgr, lobby, players)
        else:
            # Show group selection buttons if roll count > 0
            if is_my_turn and turn_state.roll_count > 0 and not game_state.is_bust:
                available = AlienInvasionEngine.get_available_selections(turn_state)

                # Check if stuck (no selections and no earthlings)
                if AlienInvasionEngine.is_stuck(turn_state):
                    st.error("⚠️ All remaining dice are Tanks! You're stuck - must end turn (BUST).")
                    if st.button("End Turn (Bust)", key="btn_stuck_end", type="primary", use_container_width=True):
                        _handle_alien_invasion_end_turn_bust(gs_mgr, lobby_mgr, lobby, players)
                else:
                    # Show "must select" warning if needed
                    if needs_selection and available:
                        st.warning("⚠️ You must select at least one group before rolling again!")

                    # Show selection buttons
                    selected_type = render_group_selection_buttons(
                        available_selections=available,
                        is_my_turn=is_my_turn,
                        roll_count=turn_state.roll_count,
                    )

                    if selected_type:
                        _handle_alien_invasion_selection(
                            turn_state,
                            selected_type,
                            available[selected_type],
                            gs_mgr,
                            lobby_id,
                        )

        # Set-aside dice display (replaces old progress expander)
        if turn_state.roll_count > 0:
            scoring_result = AlienInvasionEngine.calculate_final_score(turn_state)
            render_set_aside_dice(
                selected_earthling_types=list(turn_state.selected_types),
                death_rays_count=turn_state.death_rays_count,
                tanks_count=turn_state.tanks_count,
                scoring_result=scoring_result,
            )

        # Turn controls (skip if immediate bust — already handled above)
        if not is_immediate_bust and is_my_turn and not game_state.is_bust:
            st.markdown("---")

            # Determine what actions are available
            needs_selection = ss.get("_alien_needs_selection", False)
            can_roll = turn_state.roll_count == 0 or (
                not needs_selection and turn_state.available_dice_count > 0
            )
            scoring_result = AlienInvasionEngine.calculate_final_score(turn_state)
            can_bank = turn_state.earthlings_count > 0 and scoring_result.is_safe_to_bank
            available = AlienInvasionEngine.get_available_selections(turn_state) if turn_state.roll_count > 0 else {}
            has_selections = len(available) > 0

            if turn_state.roll_count > 0 and not can_roll and not can_bank and not has_selections:
                # Player has no actions left — forced end of turn
                if scoring_result.is_bust:
                    st.error(
                        f"Turn over! Tanks ({turn_state.tanks_count}) > "
                        f"Death Rays ({turn_state.death_rays_count}) — BUST!"
                    )
                else:
                    st.warning("No more actions available.")
                if st.button(
                    "End Turn (0 pts)",
                    key="btn_forced_end",
                    type="primary",
                    use_container_width=True,
                ):
                    _handle_alien_invasion_end_turn_bust(gs_mgr, lobby_mgr, lobby, players)
            else:
                # Show Roll / Bank / End Turn buttons
                show_end_turn = (
                    turn_state.roll_count > 0
                    and not can_bank
                    and scoring_result.is_bust
                )
                btn_cols = st.columns(3 if show_end_turn else 2)

                with btn_cols[0]:
                    roll_label = "Roll Dice" if turn_state.roll_count == 0 else "Roll Again"
                    if st.button(roll_label, key="btn_roll", disabled=not can_roll, use_container_width=True):
                        _handle_alien_invasion_roll(turn_state, gs_mgr, lobby_id)

                with btn_cols[1]:
                    if st.button("Bank Earthlings", key="btn_bank", type="primary", disabled=not can_bank, use_container_width=True):
                        _handle_alien_invasion_bank(
                            turn_state,
                            scoring_result,
                            gs_mgr,
                            lobby_mgr,
                            player_mgr,
                            lobby,
                            players,
                            player_id,
                        )

                if show_end_turn:
                    with btn_cols[2]:
                        if st.button("End Turn (0 pts)", key="btn_end_turn", use_container_width=True):
                            _handle_alien_invasion_end_turn_bust(gs_mgr, lobby_mgr, lobby, players)

        elif not is_immediate_bust and not is_my_turn:
            st.info("Waiting for opponent's turn...")

    # Polling fragment for multiplayer sync
    _poll_game_state()


def _handle_alien_invasion_roll(turn_state, gs_mgr, lobby_id):
    """Handle rolling dice in Alien Invasion mode."""
    # Process roll (auto-locks tanks)
    new_state = AlienInvasionEngine.process_roll(turn_state)

    # Update database
    _db_retry(
        gs_mgr.update,
        lobby_id,
        active_dice=list(new_state.active_dice),
        held_indices=list(new_state.held_indices),
        roll_count=new_state.roll_count,
    )

    # Update alien-specific fields
    _db_retry(
        gs_mgr.update_alien_invasion,
        lobby_id,
        tanks_count=new_state.tanks_count,
    )

    # Mark that player must select a group before rolling again
    st.session_state["_alien_needs_selection"] = True

    # Play sound effect
    if new_state.tanks_count > turn_state.tanks_count:
        play_sfx("tank_roll")  # Tanks rolled
    else:
        play_sfx("dice_roll")  # Normal roll

    st.rerun()


def _handle_alien_invasion_selection(turn_state, face_type, indices, gs_mgr, lobby_id):
    """Handle group selection in Alien Invasion mode."""
    try:
        # Process selection
        new_state = AlienInvasionEngine.process_selection(turn_state, face_type, indices)

        # Update database
        _db_retry(
            gs_mgr.update,
            lobby_id,
            held_indices=list(new_state.held_indices),
            turn_score=new_state.turn_score,
        )

        # Update alien-specific fields
        _db_retry(
            gs_mgr.update_alien_invasion,
            lobby_id,
            death_rays_count=new_state.death_rays_count,
            earthlings_count=new_state.earthlings_count,
            selected_earthling_types=list(new_state.selected_types),
        )

        # Clear the "must select" flag — player has now selected a group
        st.session_state["_alien_needs_selection"] = False

        # Play sound effect based on type
        if face_type == FaceType.DEATH_RAY:
            play_sfx("blaster")
        else:
            play_sfx("abduction")

        st.rerun()

    except ValueError as e:
        st.error(f"Cannot select: {e}")


def _handle_alien_invasion_bank(
    turn_state,
    scoring_result,
    gs_mgr,
    lobby_mgr,
    player_mgr,
    lobby,
    players,
    player_id,
):
    """Handle banking Earthlings in Alien Invasion mode."""
    lobby_id = str(lobby.id)

    if not scoring_result.is_safe_to_bank:
        st.error("Cannot bank: Too many Tanks! You would BUST.")
        return

    if scoring_result.total_points == 0:
        st.error("Cannot bank: No points to bank.")
        return

    # Update player score
    active_player = players[lobby.current_turn_index]
    new_score = active_player.total_score + scoring_result.total_points

    _db_retry(
        player_mgr.update_score,
        str(active_player.id),
        new_score,
    )

    # Check for win
    if new_score >= lobby.win_condition:
        _db_retry(lobby_mgr.set_winner, lobby_id, str(active_player.id))
        _db_retry(lobby_mgr.update_status, lobby_id, "finished")
        play_sfx("victory")
        st.session_state["page"] = "results"
        st.rerun()
        return

    # Advance turn
    new_turn_index = (lobby.current_turn_index + 1) % len(players)
    _db_retry(lobby_mgr.advance_turn, lobby_id, new_turn_index)

    # Reset turn state
    _db_retry(gs_mgr.reset_turn, lobby_id)

    # Play bank sound
    play_sfx("bank")

    # Show score popup
    render_score_popup(scoring_result.total_points)

    st.rerun()


def _handle_alien_invasion_end_turn_bust(gs_mgr, lobby_mgr, lobby, players):
    """Handle ending turn with a bust in Alien Invasion mode."""
    lobby_id = str(lobby.id)

    # Advance turn
    new_turn_index = (lobby.current_turn_index + 1) % len(players)
    _db_retry(lobby_mgr.advance_turn, lobby_id, new_turn_index)

    # Reset turn state
    _db_retry(gs_mgr.reset_turn, lobby_id)

    # Play bust sound
    play_sfx("bust")

    st.rerun()
