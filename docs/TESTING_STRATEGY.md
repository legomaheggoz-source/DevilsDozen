# Devil's Dozen - Testing Strategy

## Overview

This document outlines the testing approach for Devil's Dozen, ensuring reliable gameplay and a polished user experience.

---

## 1. Test Pyramid

```
                    ┌───────────────┐
                    │   Manual/E2E  │  ← Minimal, expensive
                    │   (10%)       │
                    ├───────────────┤
                    │  Integration  │  ← Cross-module
                    │   (30%)       │
                    ├───────────────┤
                    │    Unit       │  ← Fast, isolated
                    │   (60%)       │
                    └───────────────┘
```

---

## 2. Unit Tests

### Game Engine (Critical - 100% Coverage)

**Location**: `tests/engine/`

**What to Test**:
- All scoring combinations for Peasant's Gamble
- All tier rules for Alchemist's Ascent
- Edge cases (max scores, empty rolls, bust conditions)
- Hot dice detection
- Bust detection

**Sample Test Cases**:

```python
# tests/engine/test_peasants_gamble.py

class TestSingleDieScoring:
    def test_single_one_scores_100(self):
        result = PeasantsGambleEngine.calculate_score((1,))
        assert result.points == 100

    def test_single_five_scores_50(self):
        result = PeasantsGambleEngine.calculate_score((5,))
        assert result.points == 50

    def test_non_scoring_single_returns_zero(self):
        for value in [2, 3, 4, 6]:
            result = PeasantsGambleEngine.calculate_score((value,))
            assert result.points == 0


class TestThreeOfAKind:
    def test_three_ones_scores_1000(self):
        result = PeasantsGambleEngine.calculate_score((1, 1, 1))
        assert result.points == 1000

    @pytest.mark.parametrize("value,expected", [
        (2, 200), (3, 300), (4, 400), (5, 500), (6, 600)
    ])
    def test_three_of_kind_scores_value_times_100(self, value, expected):
        dice = tuple([value] * 3)
        result = PeasantsGambleEngine.calculate_score(dice)
        assert result.points == expected


class TestStraights:
    def test_low_straight_scores_500(self):
        result = PeasantsGambleEngine.calculate_score((1, 2, 3, 4, 5))
        assert result.points == 500

    def test_high_straight_scores_750(self):
        result = PeasantsGambleEngine.calculate_score((2, 3, 4, 5, 6))
        assert result.points == 750

    def test_full_straight_scores_1500(self):
        result = PeasantsGambleEngine.calculate_score((1, 2, 3, 4, 5, 6))
        assert result.points == 1500


class TestBustDetection:
    def test_no_scoring_dice_is_bust(self):
        assert PeasantsGambleEngine.is_bust((2, 3, 4, 6)) is True

    def test_single_scoring_die_is_not_bust(self):
        assert PeasantsGambleEngine.is_bust((1, 2, 3, 4)) is False


class TestHotDice:
    def test_all_dice_scoring_is_hot(self):
        # 1-5 straight (500) + 1 (100) = all 6 score
        assert PeasantsGambleEngine.is_hot_dice((1, 2, 3, 4, 5, 1)) is True

    def test_remaining_dice_is_not_hot(self):
        assert PeasantsGambleEngine.is_hot_dice((1, 2, 3)) is False
```

### Database Layer

**Location**: `tests/database/`

**What to Test**:
- Pydantic model validation
- CRUD operation return types
- Error handling for invalid inputs

```python
# tests/database/test_models.py

class TestLobbyModel:
    def test_valid_lobby_creation(self):
        lobby = Lobby(
            id=uuid4(),
            code="ABC123",
            game_mode="peasants_gamble",
            win_condition=5000,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert lobby.code == "ABC123"

    def test_invalid_code_length_rejected(self):
        with pytest.raises(ValidationError):
            Lobby(code="TOOLONGCODE", ...)
```

---

## 3. Integration Tests

### Database + Engine Integration

**Location**: `tests/integration/`

**What to Test**:
- Full game flow from lobby creation to win
- Turn state persistence
- Score updates

```python
# tests/integration/test_game_flow.py

class TestFullGameFlow:
    @pytest.fixture
    def lobby(self, supabase_client):
        manager = LobbyManager(supabase_client)
        return manager.create("peasants_gamble", 1000)

    def test_player_can_join_and_score(self, lobby):
        player = PlayerManager.join(lobby.id, "TestPlayer")

        # Simulate scoring roll
        dice = (1, 1, 1, 5, 5, 5)  # 1000 + 500 = 1500
        score = PeasantsGambleEngine.calculate_score(dice)

        PlayerManager.update_score(player.id, score.points)

        updated = PlayerManager.get(player.id)
        assert updated.total_score == 1500
```

### Realtime Sync Integration

```python
# tests/integration/test_realtime.py

class TestRealtimeSync:
    async def test_turn_change_broadcasts(self, two_player_lobby):
        events_received = []

        def on_event(payload):
            events_received.append(payload)

        subscribe_to_lobby(two_player_lobby.id, on_event)

        # Player 1 banks their turn
        advance_turn(two_player_lobby.id)

        await asyncio.sleep(1)  # Wait for broadcast

        assert any(e.event == GameEvent.TURN_CHANGED for e in events_received)
```

---

## 4. Manual Testing Checklist

### Pre-Release Testing

#### Gameplay - Peasant's Gamble
- [ ] Roll 6 dice on turn start
- [ ] Click to hold dice works
- [ ] Bank button ends turn and adds score
- [ ] Bust shows animation and loses turn score
- [ ] Hot dice allows rolling all again
- [ ] Victory triggers at target score
- [ ] Scoring breakdown displays correctly

#### Gameplay - Alchemist's Ascent
- [ ] Tier 1: 8 red dice, standard scoring
- [ ] Tier 2: 3 green dice, 5x multiplier
- [ ] Tier 2: Reroll lower than previous = bust
- [ ] Tier 3: 1 blue die, special rules
- [ ] Tier 3: Rolling 1 resets to 0
- [ ] Tier 3: Rolling 20 gives points to last place

#### Multiplayer
- [ ] Create lobby generates code
- [ ] Join lobby with code works
- [ ] 2 players can play full game
- [ ] 3 players can play full game
- [ ] 4 players can play full game
- [ ] Disconnected player can rejoin
- [ ] Observers see real-time updates

#### UI/UX
- [ ] Medieval theme renders correctly
- [ ] Fonts load properly
- [ ] Dice animations are smooth
- [ ] Sound effects play (when enabled)
- [ ] Sound mute toggle works
- [ ] Mobile layout is usable

#### Edge Cases
- [ ] Rapid clicking doesn't break state
- [ ] Refresh preserves game state
- [ ] Network disconnect shows appropriate message
- [ ] Invalid lobby code shows error

---

## 5. Test Configuration

### pytest.ini / pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --cov=src --cov-report=term-missing --cov-report=html"
asyncio_mode = "auto"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests requiring external services",
]
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/engine tests/database -m "not integration"

# Integration tests (requires Supabase)
pytest tests/integration -m integration

# With coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Specific module
pytest tests/engine/test_peasants_gamble.py -v
```

---

## 6. Coverage Goals

| Module | Target | Rationale |
|--------|--------|-----------|
| `engine` | 100% | Core game logic, must be bulletproof |
| `database` | 80% | CRUD operations, some Supabase mocking |
| `realtime` | 70% | WebSocket complexity, integration-focused |
| `ui` | 50% | Visual testing more valuable |
| **Overall** | **80%** | |

---

## 7. Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run unit tests
        run: pytest tests/engine tests/database -m "not integration" --cov=src

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 8. Test Data Fixtures

### Common Dice Rolls

```python
# tests/conftest.py

@pytest.fixture
def scoring_rolls():
    """Common scoring roll patterns for testing."""
    return {
        "single_one": (1,),
        "single_five": (5,),
        "three_ones": (1, 1, 1),
        "three_fours": (4, 4, 4),
        "full_straight": (1, 2, 3, 4, 5, 6),
        "low_straight": (1, 2, 3, 4, 5),
        "high_straight": (2, 3, 4, 5, 6),
        "bust_roll": (2, 3, 4, 6),
        "hot_dice": (1, 1, 1, 5, 5, 5),
    }

@pytest.fixture
def mock_supabase(mocker):
    """Mock Supabase client for unit tests."""
    mock = mocker.patch("src.database.client.create_client")
    return mock.return_value
```
