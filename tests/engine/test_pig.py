"""
Devil's Dozen - Pig Engine Tests

Comprehensive tests for the Pig (single-die push-your-luck) engine.
"""

import pytest
from src.engine.pig import PigEngine
from src.engine.base import DiceRoll, DiceType, GameConfig, GameMode


# === Roll Dice ===


class TestRollDice:
    """Tests for PigEngine.roll_dice()."""

    def test_returns_dice_roll(self):
        roll = PigEngine.roll_dice()
        assert isinstance(roll, DiceRoll)

    def test_single_die(self):
        roll = PigEngine.roll_dice()
        assert len(roll.values) == 1

    def test_dice_type_d6(self):
        roll = PigEngine.roll_dice()
        assert roll.dice_type == DiceType.D6

    def test_value_range(self):
        """Roll 200 times; every value should be 1-6."""
        for _ in range(200):
            roll = PigEngine.roll_dice()
            assert 1 <= roll.values[0] <= 6

    def test_randomness(self):
        """Rolling many times should produce more than one unique value."""
        values = {PigEngine.roll_dice().values[0] for _ in range(100)}
        assert len(values) > 1


# === Calculate Score ===


class TestCalculateScore:
    """Tests for PigEngine.calculate_score()."""

    def test_roll_1_is_bust(self):
        result = PigEngine.calculate_score((1,))
        assert result.is_bust is True
        assert result.points == 0

    def test_roll_1_no_scoring_dice(self):
        result = PigEngine.calculate_score((1,))
        assert len(result.scoring_dice_indices) == 0

    @pytest.mark.parametrize("value", [2, 3, 4, 5, 6])
    def test_roll_2_through_6_scores_face_value(self, value):
        result = PigEngine.calculate_score((value,))
        assert result.is_bust is False
        assert result.points == value

    @pytest.mark.parametrize("value", [2, 3, 4, 5, 6])
    def test_scoring_dice_index_is_zero(self, value):
        result = PigEngine.calculate_score((value,))
        assert result.scoring_dice_indices == frozenset({0})

    @pytest.mark.parametrize("value", [2, 3, 4, 5, 6])
    def test_breakdown_present(self, value):
        result = PigEngine.calculate_score((value,))
        assert len(result.breakdown) == 1
        assert result.breakdown[0].points == value

    def test_accepts_dice_roll_object(self):
        roll = DiceRoll(values=(4,), dice_type=DiceType.D6)
        result = PigEngine.calculate_score(roll)
        assert result.points == 4
        assert result.is_bust is False

    def test_bust_with_dice_roll_object(self):
        roll = DiceRoll(values=(1,), dice_type=DiceType.D6)
        result = PigEngine.calculate_score(roll)
        assert result.is_bust is True


# === Is Bust ===


class TestIsBust:
    """Tests for PigEngine.is_bust()."""

    def test_1_is_bust(self):
        assert PigEngine.is_bust((1,)) is True

    @pytest.mark.parametrize("value", [2, 3, 4, 5, 6])
    def test_2_through_6_not_bust(self, value):
        assert PigEngine.is_bust((value,)) is False

    def test_accepts_dice_roll(self):
        roll = DiceRoll(values=(1,), dice_type=DiceType.D6)
        assert PigEngine.is_bust(roll) is True

    def test_accepts_dice_roll_not_bust(self):
        roll = DiceRoll(values=(5,), dice_type=DiceType.D6)
        assert PigEngine.is_bust(roll) is False


# === Process Roll ===


class TestProcessRoll:
    """Tests for PigEngine.process_roll()."""

    def test_returns_tuple_of_three(self):
        result = PigEngine.process_roll(0)
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_accumulates_turn_score(self):
        roll = DiceRoll(values=(4,), dice_type=DiceType.D6)
        new_score, _, is_bust = PigEngine.process_roll(10, roll=roll)
        assert new_score == 14
        assert is_bust is False

    def test_bust_resets_to_zero(self):
        roll = DiceRoll(values=(1,), dice_type=DiceType.D6)
        new_score, _, is_bust = PigEngine.process_roll(50, roll=roll)
        assert new_score == 0
        assert is_bust is True

    def test_returns_dice_roll(self):
        _, dice, _ = PigEngine.process_roll(0)
        assert isinstance(dice, DiceRoll)
        assert len(dice.values) == 1

    def test_uses_provided_roll(self):
        roll = DiceRoll(values=(6,), dice_type=DiceType.D6)
        new_score, returned_roll, is_bust = PigEngine.process_roll(0, roll=roll)
        assert returned_roll is roll
        assert new_score == 6
        assert is_bust is False

    def test_sequential_rolls_accumulate(self):
        """Simulate multiple non-bust rolls."""
        score = 0
        for value in [3, 5, 2, 6]:
            roll = DiceRoll(values=(value,), dice_type=DiceType.D6)
            score, _, _ = PigEngine.process_roll(score, roll=roll)
        assert score == 16  # 3+5+2+6

    def test_bust_after_accumulation(self):
        """Build up a score, then bust."""
        score = 0
        for value in [4, 6, 5]:
            roll = DiceRoll(values=(value,), dice_type=DiceType.D6)
            score, _, _ = PigEngine.process_roll(score, roll=roll)
        assert score == 15

        bust_roll = DiceRoll(values=(1,), dice_type=DiceType.D6)
        score, _, is_bust = PigEngine.process_roll(score, roll=bust_roll)
        assert score == 0
        assert is_bust is True

    def test_zero_start_non_bust(self):
        roll = DiceRoll(values=(2,), dice_type=DiceType.D6)
        new_score, _, is_bust = PigEngine.process_roll(0, roll=roll)
        assert new_score == 2
        assert is_bust is False


# === GameConfig Validation ===


class TestGameConfigPig:
    """Tests for GameConfig with Pig mode."""

    def test_valid_config_50(self):
        config = GameConfig(mode=GameMode.PIG, target_score=50, num_players=2)
        assert config.target_score == 50

    def test_valid_config_100(self):
        config = GameConfig(mode=GameMode.PIG, target_score=100, num_players=4)
        assert config.target_score == 100

    def test_valid_config_250(self):
        config = GameConfig(mode=GameMode.PIG, target_score=250, num_players=10)
        assert config.target_score == 250

    def test_invalid_target_score(self):
        with pytest.raises(ValueError, match="Target score for Pig"):
            GameConfig(mode=GameMode.PIG, target_score=999, num_players=2)

    def test_max_players_10(self):
        config = GameConfig(mode=GameMode.PIG, target_score=100, num_players=10)
        assert config.num_players == 10

    def test_min_players_2(self):
        config = GameConfig(mode=GameMode.PIG, target_score=100, num_players=2)
        assert config.num_players == 2

    def test_too_few_players(self):
        with pytest.raises(ValueError, match="between 2 and 10"):
            GameConfig(mode=GameMode.PIG, target_score=100, num_players=1)

    def test_too_many_players(self):
        with pytest.raises(ValueError, match="between 2 and 10"):
            GameConfig(mode=GameMode.PIG, target_score=100, num_players=11)
