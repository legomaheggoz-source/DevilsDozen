# Game Mode Implementation Guide

This guide documents patterns, best practices, and common gotchas when adding new game modes to Devil's Dozen, based on lessons learned from implementing Peasant's Gamble, Alchemist's Ascent, and Knucklebones.

---

## Quick Start Checklist

- [ ] Review `docs/NEW_GAME_MODE_TEMPLATE.md` for structure
- [ ] Read this guide for common patterns and gotchas
- [ ] Write engine tests FIRST (TDD approach)
- [ ] Follow die styling conventions (numeric display)
- [ ] Test database update methods with None values
- [ ] Verify turn advancement timing
- [ ] Test multiplayer sync with 2+ players
- [ ] Ensure audio triggers correctly

---

## Architecture Overview

### Layer Structure
```
┌─────────────────────────────────────────┐
│  UI Layer (Streamlit)                   │
│  - src/ui/views/game.py (routing)      │
│  - src/ui/components/                   │
├─────────────────────────────────────────┤
│  Database Layer (Supabase)              │
│  - src/database/models.py               │
│  - src/database/*_manager.py            │
├─────────────────────────────────────────┤
│  Engine Layer (Pure Python)             │
│  - src/engine/<mode>.py                 │
│  - Stateless, immutable dataclasses     │
└─────────────────────────────────────────┘
```

**Separation of Concerns:**
- **Engine**: Pure game logic, no I/O, 100% tested
- **Database**: CRUD operations, state persistence
- **UI**: Rendering, user interaction, polling

---

## Critical Patterns

### 1. Die Styling - ALWAYS Use Numeric Display

**❌ WRONG:**
```python
# Using Unicode die faces
die_face = {"1": "⚀", "2": "⚁", ...}[value]
html = f'<div class="die">{die_face}</div>'
```

**✅ CORRECT:**
```python
# Use numeric values (matches D6 standard)
html = f'<div class="die">{value}</div>'
```

**Why:** All D6 dice across all game modes display as numbers (1-6), not Unicode characters. This ensures:
- Consistent styling across modes
- Better readability
- Easier to understand at a glance
- Works with existing CSS (`.die` class)

**Standard die HTML:**
```html
<div class="die">4</div>                    <!-- Basic die -->
<div class="die scoring">4</div>            <!-- Scoring die (gold) -->
<div class="die held">4</div>               <!-- Held die (green) -->
<div class="die d20 tier-red">15</div>      <!-- D20 with tier color -->
<div class="die grid-die">6</div>           <!-- Grid die (Knucklebones) -->
```

**CSS Classes:**
- `.die` - Base die styling (72px × 72px by default)
- `.scoring` - Gold border (scoring dice)
- `.held` - Green border with lift effect
- `.d20` - Circular D20 styling
- `.tier-red`, `.tier-green`, `.tier-blue` - D20 tier colors
- `.grid-die` - Smaller dice for grids (60px × 60px)

---

### 2. Database Updates - Handle None Values Correctly

**❌ WRONG:**
```python
def update_game_state(self, lobby_id: str, field: int | None = None):
    updates = {}
    if field is not None:  # BUG: None values are skipped!
        updates["field"] = field
```

**Problem:** When you pass `field=None` to clear a value, it won't update the database because `if field is not None` evaluates to False.

**✅ CORRECT:**
```python
def update_game_state(self, lobby_id: str, **kwargs):
    updates = {}
    if "field" in kwargs:  # Check if parameter was provided
        updates["field"] = kwargs["field"]  # Can be None!
```

**Why:** Using `**kwargs` lets you distinguish between:
- "Parameter not provided" (don't update)
- "Parameter provided as None" (clear the field)

**Example from Knucklebones:**
```python
# Clear current_die_value after placement
gs_mgr.update_knucklebones(
    lobby_id,
    player1_grid=new_grid,
    current_die_value=None,  # This MUST update to NULL in DB
)
```

---

### 3. Turn Advancement - Order Matters!

**❌ WRONG:**
```python
# Update game state (clear die)
gs_mgr.update(lobby_id, current_die=None)

# Advance turn
lobby_mgr.advance_turn(lobby_id, next_player)

# BUG: Race condition! Other player might see cleared die
# but old turn index during polling.
```

**✅ CORRECT:**
```python
# Advance turn FIRST
lobby_mgr.advance_turn(lobby_id, next_player)

# THEN clear die
gs_mgr.update(lobby_id, current_die=None)

# Now when next player polls, they see:
# - current_turn_index points to them
# - current_die is None
# - Result: "Roll Die" button appears
```

**Why:** Database updates happen in separate transactions. If you clear the die before advancing the turn, there's a window where the next player might poll and see:
- Old turn index (still not their turn)
- Cleared die value (None)
- Result: Confusing UI state

**Best Practice:** Order operations so that each intermediate state is valid:
1. Change turn index
2. Clear/update related state
3. Rerun UI

---

### 4. Immutable Data Structures

**Always use frozen dataclasses in the engine layer:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class GameState:
    """Immutable game state."""
    dice: tuple[int, ...]  # Use tuples, not lists
    score: int

    # ❌ WRONG: Mutable default
    # held: list[int] = []

    # ✅ CORRECT: Immutable default
    held: frozenset[int] = field(default_factory=frozenset)
```

**Why:**
- Thread-safe
- No accidental mutations
- Easier to reason about
- Better for testing

**Converting to/from database:**
```python
# From DB (lists) -> Engine (tuples)
grid_state = GridState(
    columns=(tuple(col1), tuple(col2), tuple(col3))
)

# From Engine (tuples) -> DB (lists)
db_data = {
    "columns": [list(col) for col in grid_state.columns]
}
```

---

### 5. Stateless Engine Methods

**All engine methods should be `@classmethod` and stateless:**

```python
class MyGameEngine:
    @classmethod
    def calculate_score(cls, dice: tuple[int, ...]) -> int:
        """Pure function - no side effects."""
        return sum(dice)

    @classmethod
    def roll_dice(cls, count: int) -> tuple[int, ...]:
        """Returns new dice, doesn't modify state."""
        return tuple(random.randint(1, 6) for _ in range(count))
```

**Why:**
- Easy to test
- No hidden state
- Deterministic (given same inputs, same outputs)
- Can be called in any order

---

## Common Gotchas

### Gotcha 1: Streamlit Reruns in Callbacks

**❌ WRONG:**
```python
if st.button("Roll", on_click=lambda: handle_roll()):
    pass

def handle_roll():
    # Do stuff
    st.rerun()  # ERROR: "st.rerun() within a callback is a no-op"
```

**✅ CORRECT:**
```python
clicked = st.button("Roll")
if clicked:
    handle_roll()  # Call after button render

def handle_roll():
    # Do stuff
    st.rerun()  # Now it works!
```

**Why:** Streamlit doesn't allow `st.rerun()` inside `on_click` callbacks. Detect clicks AFTER rendering, then call handlers.

---

### Gotcha 2: Widget Keys and Roll Count

**Always include roll count in widget keys:**

```python
# ❌ WRONG: Same key across rolls
st.button("Hold", key=f"hold_{die_index}")

# ✅ CORRECT: Unique key per roll
st.button("Hold", key=f"hold_{die_index}_r{roll_count}")
```

**Why:** Streamlit caches widget state by key. If you don't change keys between rolls, old button states persist, causing clicks to be ignored.

---

### Gotcha 3: Session State Cleanup

**Use non-widget keys for persistent data:**

```python
# ❌ WRONG: Widget keys get cleared on page change
st.session_state["_sfx_widget"] = True

# ✅ CORRECT: Use non-widget keys for persistence
st.session_state["_sfx_pref"] = True  # Survives page changes

# Sync widget -> preference
def sync_sfx():
    st.session_state["_sfx_pref"] = st.session_state["_sfx_widget"]

st.checkbox("SFX", key="_sfx_widget", on_change=sync_sfx)
```

**Pattern:** Store preferences in `_name_pref` keys, sync from `_name_widget` keys.

---

### Gotcha 4: LobbyManager Method Names

**Use specific methods, not generic `update()`:**

```python
# ❌ WRONG: LobbyManager has no update() method
lobby_mgr.update(lobby_id, current_turn_index=1)

# ✅ CORRECT: Use specific methods
lobby_mgr.advance_turn(lobby_id, 1)
lobby_mgr.update_status(lobby_id, "playing")
lobby_mgr.set_winner(lobby_id, winner_id)
```

**Available methods:**
- `advance_turn(lobby_id, turn_index)`
- `update_status(lobby_id, status)`
- `set_winner(lobby_id, winner_id)`

---

## Testing Patterns

### 1. TDD Approach - Tests First

Write tests BEFORE implementing the engine:

```python
def test_calculate_score_pair():
    """Test pair scoring."""
    result = Engine.calculate_score((4, 4))
    assert result == 16  # (4 + 4) × 2
```

**Benefits:**
- Forces you to think about edge cases
- Prevents regressions
- Documents expected behavior
- Enables refactoring

**Target:** 100% engine coverage, 40+ tests per mode

---

### 2. Test Categories

Organize tests by concern:

```python
class TestDataStructures:
    """Test GridState, validation, conversions."""

class TestScoring:
    """Test score calculation logic."""

class TestGameRules:
    """Test placement, win conditions, etc."""

class TestIntegration:
    """Test full game flows."""
```

---

### 3. Manual Testing Checklist

After implementation, test end-to-end:

- [ ] Create lobby (correct player count shown)
- [ ] Join with 2nd player
- [ ] Player 1: Full turn cycle
- [ ] Player 2: Full turn cycle (polling works)
- [ ] Turn advancement works correctly
- [ ] Scoring updates in real-time
- [ ] Fill win condition
- [ ] Winner announced correctly
- [ ] Audio plays (roll, bank, bust, victory)
- [ ] Rules display in sidebar
- [ ] Mobile responsive (if applicable)

---

## UI Patterns

### 1. Layout Structure

**Standard layout: game area (3) | controls (1)**

```python
game_col, controls_col = st.columns([3, 1])

with controls_col:
    st.caption(f"Lobby: **{lobby.code}**")
    render_scoreboard(...)
    st.divider()
    # Mode-specific controls (roll, bank, placement, etc.)

with game_col:
    st.subheader(f"{active_player.username}'s Turn")
    # Mode-specific display (dice, grids, etc.)
```

**Why:** Keeps controls always visible on the right, game area has space to breathe.

---

### 2. Polling Fragment

**Use for multiplayer sync:**

```python
@st.fragment(run_every=2)
def _poll_game_state():
    """Check for updates from other players."""
    lobby = lobby_mgr.get_by_id(lobby_id)

    # Detect turn changes
    if lobby.current_turn_index != prev_turn:
        st.rerun(scope="app")

    # Detect game end
    if lobby.status == "finished":
        st.session_state["page"] = "results"
        st.rerun(scope="app")
```

**Call at end of game page:**
```python
def render_game_page():
    # ... render game ...
    _poll_game_state()  # Auto-polls every 2 seconds
```

---

### 3. Mode Routing

**Add mode routing early in `game.py`:**

```python
def render_game_page():
    # ... setup ...

    game_mode = lobby.game_mode

    # Route to mode-specific logic
    if game_mode == "my_new_mode":
        _render_my_new_mode(lobby, players, game_state, player_id)
        return

    # Existing D6/D20 logic below...
```

**Keep mode logic isolated in separate functions.**

---

## Audio Integration

### 1. Add Audio Files

**Add to dictionaries in `src/ui/themes/sounds.py`:**

```python
_SFX_FILES = {
    # ... existing ...
    "my_sfx": "my_sfx.mp3",
}

_MUSIC_FILES = {
    # ... existing ...
    "my_mode": "my_mode_theme.mp3",
}
```

---

### 2. Play Sounds

**Use `play_sfx()` from action handlers:**

```python
def _handle_roll():
    dice = engine.roll_dice(6)
    play_sfx("dice_roll")  # Queues sound for next render
    # ... update database ...
    st.rerun()
```

**Available SFX:**
- `dice_roll` - Rolling sound
- `bank` - Banking points
- `bust` - Busting
- `hot_dice` - Hot dice trigger
- `victory` - Game won
- `tier_advance` - Tier up (D20)
- `die_destroy` - Destruction (Knucklebones)
- `place_die` - Placement (Knucklebones)

---

### 3. Background Music

**Automatically plays based on page + game mode:**

```python
# In render_audio_system()
if page == "game" and game_mode in _MUSIC_FILES:
    track_key = game_mode  # Plays mode-specific music
else:
    track_key = "menu"  # Menu theme
```

**Note:** Browsers block autoplay until user interaction. Music starts on first click/interaction (standard web behavior).

---

## Deployment Checklist

Before pushing to production:

1. **Run Tests**
   ```bash
   pytest tests/engine/test_<mode>.py -v
   pytest tests/engine/ --cov=src/engine
   ```

2. **Database Migration**
   - Create SQL migration in `database/migrations/`
   - Test locally first
   - Run in Supabase SQL Editor
   - Verify columns exist

3. **Audio Files**
   - Confirm all audio files exist in `assets/sounds/`
   - Test playback locally
   - Check file sizes (use Git LFS for >1MB)

4. **Manual E2E Test**
   - Full game playthrough with 2+ players
   - Test all edge cases (full columns, ties, etc.)
   - Verify winner determination

5. **Commit & Push**
   ```bash
   git add .
   git commit -m "feat: Add <Mode> game mode"
   git push origin master
   git push hf master:main
   ```

6. **Verify Deployment**
   - Check Hugging Face Spaces rebuild
   - Test live version
   - Confirm audio files loaded (check Network tab)

---

## Common Issues & Solutions

### Issue: Die styling inconsistent
**Solution:** Always use numeric display, never Unicode characters.

### Issue: Turn not advancing
**Solution:** Advance turn BEFORE clearing die value.

### Issue: Database field not clearing
**Solution:** Use `**kwargs` in manager methods to handle None values.

### Issue: Music not playing
**Solution:** Browser autoplay policy - music starts on first interaction (normal).

### Issue: Widget clicks ignored
**Solution:** Include roll count in widget keys.

### Issue: "st.rerun() in callback" error
**Solution:** Call handlers AFTER button render, not in `on_click`.

### Issue: Polling not detecting changes
**Solution:** Ensure `st.rerun(scope="app")` is called when changes detected.

---

## Resources

- **Template:** `docs/NEW_GAME_MODE_TEMPLATE.md`
- **Architecture:** `docs/CONTEXT_*.md` files
- **Existing Engines:** `src/engine/peasants_gamble.py`, `src/engine/knucklebones.py`
- **Existing Tests:** `tests/engine/test_*.py`
- **Audio System:** `src/ui/themes/sounds.py`

---

## Questions?

If you encounter issues not covered here, document them as you solve them and add to this guide for future implementations!
