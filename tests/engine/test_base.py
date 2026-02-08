"""
Devil's Dozen - Base Classes Tests

Tests for dataclasses, enums, and validation utilities.
"""

import pytest
from src.engine.base import (
    DiceRoll,
    DiceType,
    GameConfig,
    GameMode,
    ScoringBreakdown,
    ScoringCategory,
    ScoringResult,
    Tier,
    TurnState,
)
from src.engine.validators import (
    validate_dice_values,
    validate_held_indices,
    validate_player_count,
    validate_score,
    validate_target_score,
)


class TestDiceType:
    """Tests for DiceType enum."""

    def test_d6_value(self):
        assert DiceType.D6.value == 6

    def test_d20_value(self):
        assert DiceType.D20.value == 20


class TestGameMode:
    """Tests for GameMode enum."""

    def test_peasants_gamble_value(self):
        assert GameMode.PEASANTS_GAMBLE.value == "peasants_gamble"

    def test_alchemists_ascent_value(self):
        assert GameMode.ALCHEMISTS_ASCENT.value == "alchemists_ascent"


class TestTier:
    """Tests for Tier enum."""

    def test_tier_values(self):
        assert Tier.RED.value == 1
        assert Tier.GREEN.value == 2
        assert Tier.BLUE.value == 3


class TestDiceRoll:
    """Tests for DiceRoll dataclass."""

    def test_create_valid_d6_roll(self):
        roll = DiceRoll(values=(1, 2, 3, 4, 5, 6), dice_type=DiceType.D6)
        assert len(roll) == 6
        assert roll.values == (1, 2, 3, 4, 5, 6)

    def test_create_valid_d20_roll(self):
        roll = DiceRoll(values=(1, 10, 20), dice_type=DiceType.D20)
        assert len(roll) == 3

    def test_invalid_d6_value_raises(self):
        with pytest.raises(ValueError, match="Invalid die value 7"):
            DiceRoll(values=(1, 2, 7), dice_type=DiceType.D6)

    def test_invalid_d20_value_raises(self):
        with pytest.raises(ValueError, match="Invalid die value 21"):
            DiceRoll(values=(1, 21), dice_type=DiceType.D20)

    def test_zero_value_raises(self):
        with pytest.raises(ValueError, match="Invalid die value 0"):
            DiceRoll(values=(0, 1, 2), dice_type=DiceType.D6)

    def test_negative_value_raises(self):
        with pytest.raises(ValueError, match="Invalid die value -1"):
            DiceRoll(values=(-1, 1, 2), dice_type=DiceType.D6)

    def test_from_sequence_list(self):
        roll = DiceRoll.from_sequence([1, 2, 3], DiceType.D6)
        assert roll.values == (1, 2, 3)

    def test_indexing(self):
        roll = DiceRoll(values=(1, 2, 3), dice_type=DiceType.D6)
        assert roll[0] == 1
        assert roll[2] == 3


class TestScoringBreakdown:
    """Tests for ScoringBreakdown dataclass."""

    def test_create_breakdown(self):
        breakdown = ScoringBreakdown(
            category=ScoringCategory.THREE_OF_A_KIND,
            dice_values=(4, 4, 4),
            points=400,
            description="Three 4s"
        )
        assert breakdown.points == 400
        assert breakdown.category == ScoringCategory.THREE_OF_A_KIND


class TestScoringResult:
    """Tests for ScoringResult dataclass."""

    def test_has_scoring_dice(self):
        result = ScoringResult(
            points=100,
            breakdown=tuple(),
            scoring_dice_indices=frozenset({0}),
            is_bust=False
        )
        assert result.has_scoring_dice is True

    def test_no_scoring_dice(self):
        result = ScoringResult(
            points=0,
            breakdown=tuple(),
            scoring_dice_indices=frozenset(),
            is_bust=True
        )
        assert result.has_scoring_dice is False

    def test_str_bust(self):
        result = ScoringResult(
            points=0,
            breakdown=tuple(),
            scoring_dice_indices=frozenset(),
            is_bust=True
        )
        assert "BUST" in str(result)

    def test_str_with_breakdown(self):
        breakdown = ScoringBreakdown(
            category=ScoringCategory.SINGLE_ONE,
            dice_values=(1,),
            points=100,
            description="Single 1"
        )
        result = ScoringResult(
            points=100,
            breakdown=(breakdown,),
            scoring_dice_indices=frozenset({0}),
            is_bust=False
        )
        output = str(result)
        assert "100" in output
        assert "Single 1" in output


class TestTurnState:
    """Tests for TurnState dataclass."""

    def test_available_dice_count(self):
        state = TurnState(
            active_dice=(1, 2, 3, 4, 5, 6),
            held_indices=frozenset({0, 1}),
            turn_score=0,
            roll_count=1
        )
        assert state.available_dice_count == 4

    def test_held_dice_values(self):
        state = TurnState(
            active_dice=(1, 2, 3, 4, 5, 6),
            held_indices=frozenset({0, 2}),
            turn_score=0,
            roll_count=1
        )
        assert state.held_dice_values == (1, 3)

    def test_unheld_dice_values(self):
        state = TurnState(
            active_dice=(1, 2, 3, 4, 5, 6),
            held_indices=frozenset({0, 2}),
            turn_score=0,
            roll_count=1
        )
        assert state.unheld_dice_values == (2, 4, 5, 6)


class TestGameConfig:
    """Tests for GameConfig dataclass."""

    def test_valid_peasants_gamble_config(self):
        config = GameConfig(
            mode=GameMode.PEASANTS_GAMBLE,
            target_score=5000,
            num_players=4
        )
        assert config.target_score == 5000

    def test_invalid_peasants_gamble_target(self):
        with pytest.raises(ValueError, match="must be one of"):
            GameConfig(
                mode=GameMode.PEASANTS_GAMBLE,
                target_score=4000,
                num_players=2
            )

    def test_valid_alchemists_ascent_config(self):
        config = GameConfig(
            mode=GameMode.ALCHEMISTS_ASCENT,
            target_score=250,
            num_players=3
        )
        assert config.target_score == 250

    def test_invalid_alchemists_ascent_target(self):
        with pytest.raises(ValueError, match="must be 250"):
            GameConfig(
                mode=GameMode.ALCHEMISTS_ASCENT,
                target_score=300,
                num_players=2
            )

    def test_invalid_player_count_low(self):
        with pytest.raises(ValueError, match="between 2 and 4"):
            GameConfig(
                mode=GameMode.PEASANTS_GAMBLE,
                target_score=5000,
                num_players=1
            )

    def test_invalid_player_count_high(self):
        with pytest.raises(ValueError, match="between 2 and 4"):
            GameConfig(
                mode=GameMode.PEASANTS_GAMBLE,
                target_score=5000,
                num_players=5
            )


class TestValidators:
    """Tests for validation utilities."""

    class TestValidateDiceValues:
        def test_valid_d6_values(self):
            result = validate_dice_values([1, 2, 3, 4, 5, 6], DiceType.D6)
            assert result == (1, 2, 3, 4, 5, 6)

        def test_empty_with_min_zero(self):
            result = validate_dice_values([], DiceType.D6, min_count=0)
            assert result == tuple()

        def test_empty_with_min_one_raises(self):
            with pytest.raises(ValueError, match="At least 1"):
                validate_dice_values([], DiceType.D6, min_count=1)

        def test_too_many_dice(self):
            with pytest.raises(ValueError, match="At most 6"):
                validate_dice_values([1, 2, 3, 4, 5, 6, 7], DiceType.D6, max_count=6)

        def test_invalid_value(self):
            with pytest.raises(ValueError, match="must be between 1 and 6"):
                validate_dice_values([1, 2, 7], DiceType.D6)

        def test_non_integer_value(self):
            with pytest.raises(ValueError, match="must be an integer"):
                validate_dice_values([1, 2, "three"], DiceType.D6)

    class TestValidateHeldIndices:
        def test_valid_indices(self):
            result = validate_held_indices({0, 2, 4}, dice_count=6)
            assert result == frozenset({0, 2, 4})

        def test_empty_indices(self):
            result = validate_held_indices(set(), dice_count=6)
            assert result == frozenset()

        def test_out_of_range_index(self):
            with pytest.raises(ValueError, match="out of range"):
                validate_held_indices({0, 6}, dice_count=6)

        def test_negative_index(self):
            with pytest.raises(ValueError, match="out of range"):
                validate_held_indices({-1, 0}, dice_count=6)

    class TestValidateScore:
        def test_valid_positive_score(self):
            assert validate_score(100) == 100

        def test_zero_score(self):
            assert validate_score(0) == 0

        def test_negative_score_raises(self):
            with pytest.raises(ValueError, match="cannot be negative"):
                validate_score(-100)

        def test_negative_score_allowed(self):
            assert validate_score(-100, allow_negative=True) == -100

    class TestValidatePlayerCount:
        def test_valid_counts(self):
            for count in [2, 3, 4]:
                assert validate_player_count(count) == count

        def test_invalid_count(self):
            with pytest.raises(ValueError, match="must be 2-4"):
                validate_player_count(5)

    class TestValidateTargetScore:
        def test_valid_target(self):
            assert validate_target_score(5000) == 5000

        def test_invalid_target_zero(self):
            with pytest.raises(ValueError, match="must be positive"):
                validate_target_score(0)

        def test_invalid_target_option(self):
            with pytest.raises(ValueError, match="must be one of"):
                validate_target_score(4000, valid_options={3000, 5000, 10000})
