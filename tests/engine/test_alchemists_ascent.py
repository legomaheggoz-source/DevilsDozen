"""
Devil's Dozen - Alchemist's Ascent Engine Tests

Comprehensive tests for the D20 tiered scoring engine. Coverage target: 100%
"""

import pytest
from src.engine.alchemists_ascent import AlchemistsAscentEngine, RerollResult
from src.engine.base import DiceRoll, DiceType, Tier, ScoringCategory


class TestTierDetermination:
    """Tests for tier assignment based on score."""

    @pytest.mark.parametrize("score,expected_tier", [
        (0, Tier.RED),
        (50, Tier.RED),
        (100, Tier.RED),
        (101, Tier.GREEN),
        (150, Tier.GREEN),
        (200, Tier.GREEN),
        (201, Tier.BLUE),
        (225, Tier.BLUE),
        (250, Tier.BLUE),
    ])
    def test_tier_for_score(self, score: int, expected_tier: Tier):
        assert AlchemistsAscentEngine.get_tier_for_score(score) == expected_tier

    @pytest.mark.parametrize("tier,expected_count", [
        (Tier.RED, 8),
        (Tier.GREEN, 3),
        (Tier.BLUE, 1),
    ])
    def test_dice_count_for_tier(self, tier: Tier, expected_count: int):
        assert AlchemistsAscentEngine.get_dice_count_for_tier(tier) == expected_count


class TestTier1Singles:
    """Tests for Tier 1 single die scoring."""

    def test_single_one_scores_1(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((1,))
        assert result.points == 1

    def test_single_five_scores_5(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((5,))
        assert result.points == 5

    @pytest.mark.parametrize("value", [2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    def test_other_singles_score_zero(self, value: int):
        result = AlchemistsAscentEngine.calculate_score_tier1((value,))
        assert result.points == 0


class TestTier1Pairs:
    """Tests for Tier 1 pair scoring."""

    def test_pair_of_ones_scores_10(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((1, 1))
        assert result.points == 10
        assert any(b.category == ScoringCategory.PAIR for b in result.breakdown)

    def test_pair_of_fives_scores_20(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((5, 5))
        assert result.points == 20

    @pytest.mark.parametrize("value", [2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    def test_pair_scores_face_value(self, value: int):
        result = AlchemistsAscentEngine.calculate_score_tier1((value, value))
        assert result.points == value


class TestTier1ThreeOrMore:
    """Tests for Tier 1 three or more of a kind (sum of dice)."""

    def test_three_eighteens_scores_54(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((18, 18, 18))
        assert result.points == 54  # 18 * 3

    def test_three_fours_scores_12(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((4, 4, 4))
        assert result.points == 12  # 4 * 3

    def test_five_fours_scores_20(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((4, 4, 4, 4, 4))
        assert result.points == 20  # 4 * 5

    def test_four_twenties_scores_80(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((20, 20, 20, 20))
        assert result.points == 80  # 20 * 4


class TestTier1Sequences:
    """Tests for Tier 1 sequence scoring."""

    def test_sequence_of_three_scores_10(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((3, 4, 5))
        assert result.points == 10
        assert any(b.category == ScoringCategory.SEQUENCE for b in result.breakdown)

    def test_sequence_of_four_scores_20(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((9, 10, 11, 12))
        assert result.points == 20  # 10 * (4 - 2)

    def test_sequence_of_five_scores_30(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((9, 10, 11, 12, 13))
        assert result.points == 30

    def test_sequence_of_six_scores_40(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((9, 10, 11, 12, 13, 14))
        assert result.points == 40

    def test_high_sequence_17_18_19(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((17, 18, 19))
        assert result.points == 10

    def test_sequence_order_doesnt_matter(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((5, 3, 4))
        assert result.points == 10


class TestTier1MixedCombinations:
    """Tests for Tier 1 mixed scoring patterns."""

    def test_pair_plus_single(self):
        # Pair of 10s (10) + single 1 (1)
        result = AlchemistsAscentEngine.calculate_score_tier1((10, 10, 1))
        assert result.points == 11

    def test_sequence_plus_pair(self):
        # Sequence 3-4-5 (10) + pair of 7s (7)
        result = AlchemistsAscentEngine.calculate_score_tier1((3, 4, 5, 7, 7))
        assert result.points == 17


class TestTier2Multiplier:
    """Tests for Tier 2 5× multiplier."""

    def test_tier2_single_one_scores_5(self):
        result = AlchemistsAscentEngine.calculate_score_tier2((1,))
        assert result.points == 5  # 1 * 5

    def test_tier2_single_five_scores_25(self):
        result = AlchemistsAscentEngine.calculate_score_tier2((5,))
        assert result.points == 25  # 5 * 5

    def test_tier2_pair_of_eights_scores_40(self):
        result = AlchemistsAscentEngine.calculate_score_tier2((8, 8))
        assert result.points == 40  # 8 * 5

    def test_tier2_sequence_scores_50(self):
        result = AlchemistsAscentEngine.calculate_score_tier2((3, 4, 5))
        assert result.points == 50  # 10 * 5

    def test_tier2_breakdown_shows_multiplier(self):
        result = AlchemistsAscentEngine.calculate_score_tier2((1,))
        assert "(×5)" in result.breakdown[0].description


class TestTier3SpecialRules:
    """Tests for Tier 3 single die special rules."""

    def test_tier3_roll_one_resets_to_zero(self):
        result = AlchemistsAscentEngine.calculate_score_tier3(
            dice_value=1,
            current_score=225
        )
        points_delta, is_reset, is_kingmaker, beneficiary = result

        assert is_reset is True
        assert is_kingmaker is False
        assert points_delta == -225  # Lose all points

    def test_tier3_roll_twenty_is_kingmaker(self):
        result = AlchemistsAscentEngine.calculate_score_tier3(
            dice_value=20,
            current_score=225,
            last_place_player_id="player-last"
        )
        points_delta, is_reset, is_kingmaker, beneficiary = result

        assert is_kingmaker is True
        assert is_reset is False
        assert beneficiary == "player-last"
        assert points_delta == 0  # No points for self

    @pytest.mark.parametrize("value", range(2, 20))
    def test_tier3_normal_roll_gives_face_value(self, value: int):
        result = AlchemistsAscentEngine.calculate_score_tier3(
            dice_value=value,
            current_score=225
        )
        points_delta, is_reset, is_kingmaker, beneficiary = result

        assert points_delta == value
        assert is_reset is False
        assert is_kingmaker is False


class TestTier2Reroll:
    """Tests for Tier 2 reroll mechanics."""

    def test_reroll_higher_is_success(self):
        result = AlchemistsAscentEngine.process_reroll(
            die_index=0,
            previous_values=(5, 10, 15),
            new_value=10
        )
        assert result.is_bust is False
        assert result.old_value == 5
        assert result.new_value == 10

    def test_reroll_lower_is_bust(self):
        result = AlchemistsAscentEngine.process_reroll(
            die_index=0,
            previous_values=(15, 10, 5),
            new_value=10
        )
        assert result.is_bust is True
        assert result.old_value == 15
        assert result.new_value == 10

    def test_reroll_equal_is_success(self):
        result = AlchemistsAscentEngine.process_reroll(
            die_index=0,
            previous_values=(10, 10, 10),
            new_value=10
        )
        assert result.is_bust is False

    def test_reroll_generates_value_if_none(self):
        result = AlchemistsAscentEngine.process_reroll(
            die_index=0,
            previous_values=(10, 10, 10),
            new_value=None
        )
        assert 1 <= result.new_value <= 20


class TestCalculateScoreRouter:
    """Tests for the main calculate_score method."""

    def test_routes_to_tier1_for_red(self):
        result = AlchemistsAscentEngine.calculate_score((1,), Tier.RED)
        assert result.points == 1

    def test_routes_to_tier2_for_green(self):
        result = AlchemistsAscentEngine.calculate_score((1,), Tier.GREEN)
        assert result.points == 5

    def test_raises_for_tier3(self):
        with pytest.raises(ValueError, match="Tier 3"):
            AlchemistsAscentEngine.calculate_score((10,), Tier.BLUE)


class TestRollGeneration:
    """Tests for D20 dice roll generation."""

    def test_roll_dice_returns_correct_count(self):
        roll = AlchemistsAscentEngine.roll_dice(8)
        assert len(roll.values) == 8

    def test_roll_dice_values_in_range(self):
        roll = AlchemistsAscentEngine.roll_dice(8)
        for value in roll.values:
            assert 1 <= value <= 20

    def test_roll_dice_returns_d20_type(self):
        roll = AlchemistsAscentEngine.roll_dice(8)
        assert roll.dice_type == DiceType.D20


class TestTurnStateProcessing:
    """Tests for turn state management."""

    def test_create_initial_turn_state_tier1(self):
        state = AlchemistsAscentEngine.create_initial_turn_state(current_score=50)
        assert state.tier == Tier.RED
        assert state.active_dice == tuple()

    def test_create_initial_turn_state_tier2(self):
        state = AlchemistsAscentEngine.create_initial_turn_state(current_score=150)
        assert state.tier == Tier.GREEN

    def test_create_initial_turn_state_tier3(self):
        state = AlchemistsAscentEngine.create_initial_turn_state(current_score=220)
        assert state.tier == Tier.BLUE

    def test_process_roll_tier1(self):
        state = AlchemistsAscentEngine.create_initial_turn_state(current_score=50)
        # Pair of 1s (10) + single 5 (5) + non-scoring values = 15
        roll = DiceRoll(values=(1, 1, 5, 7, 9, 11, 13, 17), dice_type=DiceType.D20)

        new_state, result = AlchemistsAscentEngine.process_roll(state, 50, roll)

        assert new_state.active_dice == roll.values
        assert new_state.roll_count == 1
        # Pair of 1s (10) + single 5 (5) = 15
        assert result.points == 15

    def test_process_roll_tier3_reset(self):
        state = AlchemistsAscentEngine.create_initial_turn_state(current_score=220)
        roll = DiceRoll(values=(1,), dice_type=DiceType.D20)

        new_state, result = AlchemistsAscentEngine.process_roll(state, 220, roll)

        points_delta, is_reset, is_kingmaker, beneficiary = result
        assert is_reset is True


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_dice_is_bust_tier1(self):
        result = AlchemistsAscentEngine.calculate_score_tier1(())
        assert result.is_bust is True

    def test_all_same_non_scoring_value(self):
        result = AlchemistsAscentEngine.calculate_score_tier1((7, 7, 7, 7, 7, 7, 7, 7))
        # Eight 7s = 7 * 8 = 56 (three or more of a kind)
        assert result.points == 56

    def test_dice_roll_input_accepted(self):
        roll = DiceRoll(values=(1, 5), dice_type=DiceType.D20)
        result = AlchemistsAscentEngine.calculate_score_tier1(roll)
        assert result.points == 6  # 1 + 5

    def test_long_sequence(self):
        # Sequence from 1 to 10
        values = tuple(range(1, 11))
        result = AlchemistsAscentEngine.calculate_score_tier1(values)
        # Sequence of 10 = 10 * (10 - 2) = 80
        assert result.points == 80
