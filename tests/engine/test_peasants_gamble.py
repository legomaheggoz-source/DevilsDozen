"""
Devil's Dozen - Peasant's Gamble Engine Tests

Comprehensive tests for the D6 scoring engine. Coverage target: 100%
"""

import pytest
from src.engine.peasants_gamble import PeasantsGambleEngine
from src.engine.base import DiceRoll, DiceType, ScoringCategory


class TestSingleDieScoring:
    """Tests for single die scoring (1s and 5s)."""

    def test_single_one_scores_100(self):
        result = PeasantsGambleEngine.calculate_score((1,))
        assert result.points == 100
        assert not result.is_bust

    def test_single_five_scores_50(self):
        result = PeasantsGambleEngine.calculate_score((5,))
        assert result.points == 50
        assert not result.is_bust

    def test_two_ones_score_200(self):
        result = PeasantsGambleEngine.calculate_score((1, 1))
        assert result.points == 200

    def test_two_fives_score_100(self):
        result = PeasantsGambleEngine.calculate_score((5, 5))
        assert result.points == 100

    def test_one_and_five_score_150(self):
        result = PeasantsGambleEngine.calculate_score((1, 5))
        assert result.points == 150

    @pytest.mark.parametrize("value", [2, 3, 4, 6])
    def test_non_scoring_single_is_bust(self, value: int):
        result = PeasantsGambleEngine.calculate_score((value,))
        assert result.points == 0
        assert result.is_bust


class TestThreeOfAKind:
    """Tests for three of a kind scoring."""

    def test_three_ones_scores_1000(self):
        result = PeasantsGambleEngine.calculate_score((1, 1, 1))
        assert result.points == 1000
        assert any(b.category == ScoringCategory.THREE_OF_A_KIND for b in result.breakdown)

    @pytest.mark.parametrize("value,expected", [
        (2, 200),
        (3, 300),
        (4, 400),
        (5, 500),
        (6, 600),
    ])
    def test_three_of_kind_scores_value_times_100(self, value: int, expected: int):
        dice = (value, value, value)
        result = PeasantsGambleEngine.calculate_score(dice)
        assert result.points == expected


class TestFourOrMoreOfAKind:
    """Tests for four, five, and six of a kind (doubling rules)."""

    def test_four_ones_scores_2000(self):
        result = PeasantsGambleEngine.calculate_score((1, 1, 1, 1))
        assert result.points == 2000  # 1000 * 2

    def test_five_ones_scores_4000(self):
        result = PeasantsGambleEngine.calculate_score((1, 1, 1, 1, 1))
        assert result.points == 4000  # 1000 * 2 * 2

    def test_six_ones_scores_8000(self):
        result = PeasantsGambleEngine.calculate_score((1, 1, 1, 1, 1, 1))
        assert result.points == 8000  # 1000 * 2 * 2 * 2

    @pytest.mark.parametrize("value,expected", [
        (2, 400),   # 200 * 2
        (3, 600),   # 300 * 2
        (4, 800),   # 400 * 2
        (5, 1000),  # 500 * 2
        (6, 1200),  # 600 * 2
    ])
    def test_four_of_kind_doubles_three_of_kind(self, value: int, expected: int):
        dice = (value, value, value, value)
        result = PeasantsGambleEngine.calculate_score(dice)
        assert result.points == expected

    def test_five_fours_scores_1600(self):
        result = PeasantsGambleEngine.calculate_score((4, 4, 4, 4, 4))
        assert result.points == 1600  # 400 * 2 * 2

    def test_six_fours_scores_3200(self):
        result = PeasantsGambleEngine.calculate_score((4, 4, 4, 4, 4, 4))
        assert result.points == 3200  # 400 * 2 * 2 * 2


class TestStraights:
    """Tests for straight combinations."""

    def test_low_straight_scores_500(self):
        result = PeasantsGambleEngine.calculate_score((1, 2, 3, 4, 5))
        assert result.points == 500
        assert any(b.category == ScoringCategory.LOW_STRAIGHT for b in result.breakdown)

    def test_high_straight_scores_750(self):
        result = PeasantsGambleEngine.calculate_score((2, 3, 4, 5, 6))
        assert result.points == 750
        assert any(b.category == ScoringCategory.HIGH_STRAIGHT for b in result.breakdown)

    def test_full_straight_scores_1500(self):
        result = PeasantsGambleEngine.calculate_score((1, 2, 3, 4, 5, 6))
        assert result.points == 1500
        assert any(b.category == ScoringCategory.FULL_STRAIGHT for b in result.breakdown)

    def test_straight_order_doesnt_matter(self):
        """Straights should be detected regardless of dice order."""
        shuffled = (5, 3, 1, 4, 2)
        result = PeasantsGambleEngine.calculate_score(shuffled)
        assert result.points == 500

    def test_full_straight_shuffled(self):
        shuffled = (6, 4, 2, 5, 3, 1)
        result = PeasantsGambleEngine.calculate_score(shuffled)
        assert result.points == 1500


class TestMixedCombinations:
    """Tests for combinations of different scoring patterns."""

    def test_three_ones_plus_single_five(self):
        result = PeasantsGambleEngine.calculate_score((1, 1, 1, 5))
        assert result.points == 1050  # 1000 + 50

    def test_three_fours_plus_single_one(self):
        result = PeasantsGambleEngine.calculate_score((4, 4, 4, 1))
        assert result.points == 500  # 400 + 100

    def test_three_fives_plus_single_one(self):
        result = PeasantsGambleEngine.calculate_score((5, 5, 5, 1))
        assert result.points == 600  # 500 + 100

    def test_two_three_of_kinds(self):
        """Two different three of a kinds in same roll."""
        result = PeasantsGambleEngine.calculate_score((1, 1, 1, 5, 5, 5))
        assert result.points == 1500  # 1000 + 500


class TestBustDetection:
    """Tests for bust detection."""

    @pytest.mark.parametrize("dice", [
        (2,),
        (3,),
        (4,),
        (6,),
        (2, 3),
        (2, 4),
        (2, 6),
        (3, 4),
        (3, 6),
        (4, 6),
        (2, 3, 4),
        (2, 3, 6),
        (2, 4, 6),
        (3, 4, 6),
        (2, 3, 4, 6),
    ])
    def test_non_scoring_rolls_are_bust(self, dice: tuple):
        assert PeasantsGambleEngine.is_bust(dice) is True
        result = PeasantsGambleEngine.calculate_score(dice)
        assert result.is_bust is True

    def test_single_one_is_not_bust(self):
        assert PeasantsGambleEngine.is_bust((1, 2, 3, 4)) is False

    def test_single_five_is_not_bust(self):
        assert PeasantsGambleEngine.is_bust((2, 3, 4, 5)) is False


class TestHotDice:
    """Tests for hot dice detection."""

    def test_full_straight_is_hot_dice(self):
        assert PeasantsGambleEngine.is_hot_dice((1, 2, 3, 4, 5, 6)) is True

    def test_two_three_of_kinds_is_hot_dice(self):
        assert PeasantsGambleEngine.is_hot_dice((1, 1, 1, 5, 5, 5)) is True

    def test_four_ones_two_fives_is_hot_dice(self):
        assert PeasantsGambleEngine.is_hot_dice((1, 1, 1, 1, 5, 5)) is True

    def test_partial_scoring_is_not_hot_dice(self):
        assert PeasantsGambleEngine.is_hot_dice((1, 2, 3, 4)) is False

    def test_empty_is_not_hot_dice(self):
        assert PeasantsGambleEngine.is_hot_dice(()) is False


class TestScoringIndices:
    """Tests for tracking which dice scored."""

    def test_single_one_index_tracked(self):
        result = PeasantsGambleEngine.calculate_score((1, 2, 3, 4))
        assert 0 in result.scoring_dice_indices
        assert len(result.scoring_dice_indices) == 1

    def test_all_scoring_indices_tracked_for_straight(self):
        result = PeasantsGambleEngine.calculate_score((1, 2, 3, 4, 5))
        assert len(result.scoring_dice_indices) == 5

    def test_mixed_scoring_indices(self):
        result = PeasantsGambleEngine.calculate_score((1, 1, 1, 2, 3, 5))
        # Three 1s at indices 0,1,2 and single 5 at index 5
        assert len(result.scoring_dice_indices) == 4


class TestDiceRollInput:
    """Tests for DiceRoll input handling."""

    def test_accepts_dice_roll_object(self):
        roll = DiceRoll(values=(1, 2, 3, 4, 5, 6), dice_type=DiceType.D6)
        result = PeasantsGambleEngine.calculate_score(roll)
        assert result.points == 1500

    def test_accepts_tuple(self):
        result = PeasantsGambleEngine.calculate_score((1, 5))
        assert result.points == 150

    def test_accepts_list(self):
        result = PeasantsGambleEngine.calculate_score([1, 5])
        assert result.points == 150


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_dice_is_bust(self):
        result = PeasantsGambleEngine.calculate_score(())
        assert result.is_bust is True
        assert result.points == 0

    def test_all_same_value_scoring(self):
        """All dice are the same scoring value."""
        result = PeasantsGambleEngine.calculate_score((5, 5, 5, 5, 5, 5))
        # Six 5s = 500 * 2 * 2 * 2 = 4000
        assert result.points == 4000


class TestRollGeneration:
    """Tests for dice roll generation."""

    def test_roll_dice_returns_correct_count(self):
        roll = PeasantsGambleEngine.roll_dice(6)
        assert len(roll.values) == 6

    def test_roll_dice_values_in_range(self):
        roll = PeasantsGambleEngine.roll_dice(6)
        for value in roll.values:
            assert 1 <= value <= 6

    def test_roll_dice_returns_d6_type(self):
        roll = PeasantsGambleEngine.roll_dice(6)
        assert roll.dice_type == DiceType.D6


class TestTurnStateProcessing:
    """Tests for turn state management."""

    def test_create_initial_turn_state(self):
        state = PeasantsGambleEngine.create_initial_turn_state()
        assert state.active_dice == tuple()
        assert state.held_indices == frozenset()
        assert state.turn_score == 0
        assert state.roll_count == 0

    def test_process_roll_updates_state(self):
        state = PeasantsGambleEngine.create_initial_turn_state()
        roll = DiceRoll(values=(1, 2, 3, 4, 5, 6), dice_type=DiceType.D6)

        new_state, result = PeasantsGambleEngine.process_roll(state, roll)

        assert new_state.active_dice == (1, 2, 3, 4, 5, 6)
        assert new_state.roll_count == 1
        assert result.points == 1500

    def test_process_bust_resets_turn_score(self):
        from src.engine.base import TurnState

        state = TurnState(
            active_dice=(1, 5),
            held_indices=frozenset({0, 1}),
            turn_score=150,
            roll_count=1,
            is_hot_dice=False
        )

        # Roll a bust
        bust_roll = DiceRoll(values=(2, 3, 4, 6), dice_type=DiceType.D6)
        new_state, result = PeasantsGambleEngine.process_roll(state, bust_roll)

        assert result.is_bust is True
        assert new_state.turn_score == 0

    def test_process_hold_adds_score(self):
        from src.engine.base import TurnState

        state = TurnState(
            active_dice=(1, 5, 2, 3, 4, 6),
            held_indices=frozenset(),
            turn_score=0,
            roll_count=1,
            is_hot_dice=False
        )

        new_state, result = PeasantsGambleEngine.process_hold(state, {0, 1})

        assert new_state.turn_score == 150
        assert new_state.held_indices == frozenset({0, 1})

    def test_cannot_hold_non_scoring_dice(self):
        from src.engine.base import TurnState

        state = TurnState(
            active_dice=(2, 3, 4, 6, 1, 5),
            held_indices=frozenset(),
            turn_score=0,
            roll_count=1,
            is_hot_dice=False
        )

        with pytest.raises(ValueError, match="non-scoring"):
            PeasantsGambleEngine.process_hold(state, {0, 1})
