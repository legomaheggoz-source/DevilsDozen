# Context: Game Engine

## Quick Summary

Pure Python game logic with zero UI/database dependencies. Handles dice rolling, scoring calculations, bust detection, and hot dice mechanics for both game modes.

---

## Files in This Module

| File | Purpose |
|------|---------|
| `src/engine/__init__.py` | Public exports |
| `src/engine/base.py` | Abstract base classes, dataclasses, enums |
| `src/engine/peasants_gamble.py` | D6 mode scoring and game rules |
| `src/engine/alchemists_ascent.py` | D20 tiered mode scoring and rules |
| `src/engine/validators.py` | Input validation helpers |

---

## Dependencies

### External Packages
- `random` (stdlib): Dice rolling
- `dataclasses` (stdlib): Immutable state objects
- `enum` (stdlib): Game modes, dice types
- `typing` (stdlib): Type hints
- `collections.Counter` (stdlib): Efficient dice counting

### Internal Imports
- **None** - This is the foundation layer with zero internal dependencies

---

## Exports (What Others Import)

```python
from src.engine import (
    # Data Classes
    DiceRoll,           # Immutable roll result
    ScoringResult,      # Points with breakdown
    ScoringBreakdown,   # Individual scoring components
    TurnState,          # Full turn state snapshot

    # Enums
    DiceType,           # D6, D20
    GameMode,           # PEASANTS_GAMBLE, ALCHEMISTS_ASCENT

    # Engines
    PeasantsGambleEngine,    # D6 mode calculator
    AlchemistsAscentEngine,  # D20 mode calculator
)
```

---

## Current State

- [ ] `base.py` - Dataclasses and enums
- [ ] `peasants_gamble.py` - D6 scoring engine
- [ ] `alchemists_ascent.py` - D20 scoring engine
- [ ] `validators.py` - Input validation
- [ ] Unit tests with 100% coverage

---

## Key Patterns & Conventions

### All Scoring Functions Are Pure

```python
def calculate_score(dice: tuple[int, ...]) -> ScoringResult:
    """
    Pure function: same input always produces same output.
    No side effects, no state mutation, fully deterministic.
    """
    # Implementation
```

### Engines Are Stateless Calculators

```python
class PeasantsGambleEngine:
    """
    All methods are @classmethod or @staticmethod.
    State is passed in as parameters, not stored in the class.
    This allows thread-safe, parallel calculations.
    """

    @classmethod
    def calculate_roll_score(cls, dice: tuple[int, ...]) -> ScoringResult:
        ...

    @classmethod
    def is_bust(cls, dice: tuple[int, ...]) -> bool:
        ...
```

### Dataclasses Are Immutable

```python
@dataclass(frozen=True)
class DiceRoll:
    """Frozen dataclass - cannot be modified after creation."""
    values: tuple[int, ...]
    dice_type: DiceType
```

### Use `tuple` Not `list` for Dice Values

```python
# Good - immutable, hashable
dice: tuple[int, ...] = (1, 4, 5, 2, 3, 6)

# Bad - mutable, not hashable
dice: list[int] = [1, 4, 5, 2, 3, 6]
```

---

## Scoring Logic Reference

### Peasant's Gamble (D6)

| Roll | Points | Detection Priority |
|------|--------|-------------------|
| 1-2-3-4-5-6 | 1,500 | Check FIRST |
| 1-2-3-4-5 | 500 | Check second |
| 2-3-4-5-6 | 750 | Check third |
| Three 1s | 1,000 | Check before generic 3-of-kind |
| Three X | X × 100 | e.g., Three 4s = 400 |
| Four+ X | Double previous tier | e.g., Four 4s = 800 |
| Single 1 | 100 | After straights and sets |
| Single 5 | 50 | After straights and sets |

**Order matters**: Check straights before three-of-a-kind, or 1-2-3-4-5 would be partially consumed as three-of-a-kind.

### Alchemist's Ascent (D20)

**Tier 1 (Red, 0-100):**
- Single 1 = 1, Single 5 = 5
- Pair = face value (pair of 1s = 10, pair of 5s = 20)
- Three+ of kind = sum of all matching dice
- Sequence of 3+ = 10 × (length - 2)

**Tier 2 (Green, 101-200):**
- Same as Tier 1 but multiply result by 5

**Tier 3 (Blue, 201-250):**
- Roll 1 = RESET to 0
- Roll 20 = Give 20 to last place
- Roll 2-19 = Face value

---

## Integration Points

| Consumer | What They Use |
|----------|---------------|
| `ui/components/dice_tray.py` | `ScoringResult` for display |
| `ui/components/turn_controls.py` | `is_bust()`, `is_hot_dice()` |
| `database/game_state.py` | `TurnState` for persistence |
| `tests/engine/*` | All public classes/functions |

---

## Testing Notes

### Run Tests
```bash
pytest tests/engine/ -v --cov=src/engine
```

### Coverage Target
- **100%** line coverage for all scoring functions
- All edge cases documented as test cases

### Key Edge Cases to Test
1. Six of a kind (e.g., six 1s = 8,000 points)
2. Mixed straights and singles (1-2-3-4-5 + extra 1)
3. Empty dice roll (should not be possible, but validate)
4. Tier transitions in Alchemist's Ascent
5. Reroll bust detection (new < old in Tier 2)

---

## Discovered Context

> This section is updated during implementation. Check here before starting work.

[Empty until implementation begins]
