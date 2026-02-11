"""
Devil's Dozen - Alien Invasion Engine Tests

Comprehensive tests for the Alien Invasion (Martian Dice) engine.
Coverage target: 100%
"""

import pytest
from src.engine.alien_invasion import (
    AlienInvasionEngine,
    AlienInvasionTurnState,
    AlienInvasionScoringResult,
    FaceType,
)
from src.engine.base import DiceRoll, DiceType


class TestFaceClassification:
    """Tests for face type classification."""

    def test_classify_human(self):
        """Face value 1 = Human"""
        classification = AlienInvasionEngine.classify_dice((1,))
        assert classification[FaceType.HUMAN] == [0]
        assert len(classification[FaceType.COW]) == 0

    def test_classify_cow(self):
        """Face value 2 = Cow"""
        classification = AlienInvasionEngine.classify_dice((2,))
        assert classification[FaceType.COW] == [0]

    def test_classify_chicken(self):
        """Face value 3 = Chicken"""
        classification = AlienInvasionEngine.classify_dice((3,))
        assert classification[FaceType.CHICKEN] == [0]

    def test_classify_death_ray_from_4(self):
        """Face value 4 = Death Ray"""
        classification = AlienInvasionEngine.classify_dice((4,))
        assert classification[FaceType.DEATH_RAY] == [0]

    def test_classify_death_ray_from_5(self):
        """Face value 5 = Death Ray"""
        classification = AlienInvasionEngine.classify_dice((5,))
        assert classification[FaceType.DEATH_RAY] == [0]

    def test_classify_tank(self):
        """Face value 6 = Tank"""
        classification = AlienInvasionEngine.classify_dice((6,))
        assert classification[FaceType.TANK] == [0]

    def test_classify_mixed_dice(self):
        """Test classification of mixed roll"""
        # 1=Human, 2=Cow, 3=Chicken, 4=Ray, 5=Ray, 6=Tank
        dice = (1, 2, 3, 4, 5, 6)
        classification = AlienInvasionEngine.classify_dice(dice)
        assert classification[FaceType.HUMAN] == [0]
        assert classification[FaceType.COW] == [1]
        assert classification[FaceType.CHICKEN] == [2]
        assert classification[FaceType.DEATH_RAY] == [3, 4]
        assert classification[FaceType.TANK] == [5]

    def test_classify_multiple_same_type(self):
        """Test multiple dice of same type"""
        dice = (1, 1, 1, 6, 6)
        classification = AlienInvasionEngine.classify_dice(dice)
        assert classification[FaceType.HUMAN] == [0, 1, 2]
        assert classification[FaceType.TANK] == [3, 4]


class TestRollDice:
    """Tests for dice rolling."""

    def test_roll_default_count(self):
        """Rolling without args gives 13 dice"""
        roll = AlienInvasionEngine.roll_dice()
        assert len(roll.values) == 13
        assert roll.dice_type == DiceType.D6

    def test_roll_custom_count(self):
        """Rolling with custom count"""
        roll = AlienInvasionEngine.roll_dice(5)
        assert len(roll.values) == 5

    def test_roll_values_in_range(self):
        """All rolled values are 1-6"""
        for _ in range(10):
            roll = AlienInvasionEngine.roll_dice()
            for value in roll.values:
                assert 1 <= value <= 6


class TestAutoLockTanks:
    """Tests for automatic tank locking."""

    def test_tanks_auto_lock_on_first_roll(self):
        """Tanks automatically held on first roll"""
        state = AlienInvasionEngine.create_initial_turn_state()
        roll = DiceRoll(values=(6, 6, 1, 2, 3), dice_type=DiceType.D6)

        new_state = AlienInvasionEngine.process_roll(state, roll)

        assert 0 in new_state.held_indices  # First tank
        assert 1 in new_state.held_indices  # Second tank
        assert new_state.tanks_count == 2

    def test_tanks_auto_lock_on_subsequent_roll(self):
        """Tanks auto-lock on later rolls too"""
        # Start with some existing state
        state = AlienInvasionTurnState(
            active_dice=(1, 2, 3),
            held_indices=frozenset(),
            tanks_count=1,  # Already had 1 tank
            roll_count=1,
        )

        # Roll includes 2 more tanks
        roll = DiceRoll(values=(6, 6, 4), dice_type=DiceType.D6)
        new_state = AlienInvasionEngine.process_roll(state, roll)

        assert new_state.tanks_count == 3  # 1 previous + 2 new
        assert 0 in new_state.held_indices
        assert 1 in new_state.held_indices

    def test_no_tanks_no_auto_lock(self):
        """No auto-locking if no tanks rolled"""
        state = AlienInvasionEngine.create_initial_turn_state()
        roll = DiceRoll(values=(1, 2, 3, 4, 5), dice_type=DiceType.D6)

        new_state = AlienInvasionEngine.process_roll(state, roll)

        assert len(new_state.held_indices) == 0
        assert new_state.tanks_count == 0


class TestAvailableSelections:
    """Tests for determining available selections."""

    def test_available_selections_excludes_tanks(self):
        """Tanks never appear in available selections"""
        state = AlienInvasionTurnState(
            active_dice=(6, 6, 1, 2),
            held_indices=frozenset([0, 1]),  # Tanks held
            tanks_count=2,
            roll_count=1,
        )

        available = AlienInvasionEngine.get_available_selections(state)

        assert FaceType.TANK not in available
        assert FaceType.HUMAN in available
        assert FaceType.COW in available

    def test_available_selections_excludes_held(self):
        """Held dice don't appear in available selections"""
        state = AlienInvasionTurnState(
            active_dice=(1, 1, 1),
            held_indices=frozenset([0, 1]),  # 2 humans held
            earthlings_count=2,
            selected_types=("human",),
            roll_count=1,
        )

        available = AlienInvasionEngine.get_available_selections(state)

        # Humans already selected, so not available
        assert FaceType.HUMAN not in available

    def test_available_selections_excludes_selected_earthling_types(self):
        """Earthling types already selected don't appear"""
        state = AlienInvasionTurnState(
            active_dice=(1, 2, 3, 4),
            held_indices=frozenset(),
            selected_types=("human",),  # Humans already selected
            roll_count=1,
        )

        available = AlienInvasionEngine.get_available_selections(state)

        assert FaceType.HUMAN not in available  # Already selected
        assert FaceType.COW in available
        assert FaceType.CHICKEN in available
        assert FaceType.DEATH_RAY in available

    def test_death_rays_always_available(self):
        """Death Rays can be selected multiple times"""
        state = AlienInvasionTurnState(
            active_dice=(4, 5, 4, 5),
            held_indices=frozenset(),
            death_rays_count=5,  # Already have 5 rays
            roll_count=1,
        )

        available = AlienInvasionEngine.get_available_selections(state)

        assert FaceType.DEATH_RAY in available
        assert len(available[FaceType.DEATH_RAY]) == 4


class TestGroupSelection:
    """Tests for processing group selection."""

    def test_select_humans_group(self):
        """Selecting all Humans at once"""
        state = AlienInvasionTurnState(
            active_dice=(1, 1, 1, 2, 3),
            held_indices=frozenset(),
            roll_count=1,
        )

        new_state = AlienInvasionEngine.process_selection(
            state, FaceType.HUMAN, [0, 1, 2]
        )

        assert new_state.earthlings_count == 3
        assert "human" in new_state.selected_types
        assert 0 in new_state.held_indices
        assert 1 in new_state.held_indices
        assert 2 in new_state.held_indices

    def test_select_death_rays_group(self):
        """Selecting all Death Rays at once"""
        state = AlienInvasionTurnState(
            active_dice=(4, 5, 4, 1),
            held_indices=frozenset(),
            roll_count=1,
        )

        new_state = AlienInvasionEngine.process_selection(
            state, FaceType.DEATH_RAY, [0, 1, 2]
        )

        assert new_state.death_rays_count == 3
        assert new_state.earthlings_count == 0
        assert len(new_state.selected_types) == 0  # Rays don't add to selected types

    def test_cannot_select_tanks_manually(self):
        """Cannot manually select tanks (auto-locked only)"""
        state = AlienInvasionTurnState(
            active_dice=(6, 6, 1),
            held_indices=frozenset([0, 1]),
            tanks_count=2,
            roll_count=1,
        )

        with pytest.raises(ValueError, match="Cannot manually select tanks"):
            AlienInvasionEngine.process_selection(state, FaceType.TANK, [0])

    def test_cannot_select_same_earthling_type_twice(self):
        """Cannot select same Earthling type twice in one turn"""
        state = AlienInvasionTurnState(
            active_dice=(1, 1, 2),
            held_indices=frozenset(),
            selected_types=("human",),  # Already selected
            earthlings_count=2,
            roll_count=1,
        )

        with pytest.raises(ValueError, match="already selected"):
            AlienInvasionEngine.process_selection(state, FaceType.HUMAN, [0])

    def test_can_select_death_rays_multiple_times(self):
        """Death Rays can be selected multiple times per turn"""
        state = AlienInvasionTurnState(
            active_dice=(4, 5),
            held_indices=frozenset(),
            death_rays_count=3,  # Already have 3
            roll_count=1,
        )

        new_state = AlienInvasionEngine.process_selection(
            state, FaceType.DEATH_RAY, [0, 1]
        )

        assert new_state.death_rays_count == 5  # 3 + 2

    def test_cannot_select_held_dice(self):
        """Cannot select already held dice"""
        state = AlienInvasionTurnState(
            active_dice=(1, 1, 1),
            held_indices=frozenset([0]),
            roll_count=1,
        )

        with pytest.raises(ValueError, match="already held"):
            AlienInvasionEngine.process_selection(state, FaceType.HUMAN, [0, 1])

    def test_selection_validates_face_type(self):
        """Selection validates all indices match face type"""
        state = AlienInvasionTurnState(
            active_dice=(1, 2, 3),
            held_indices=frozenset(),
            roll_count=1,
        )

        with pytest.raises(ValueError, match="is not a"):
            # Try to select index 1 (Cow) as Human
            AlienInvasionEngine.process_selection(state, FaceType.HUMAN, [0, 1])


class TestScoring:
    """Tests for score calculation."""

    def test_score_earthlings_only(self):
        """Base scoring: 1 point per Earthling"""
        state = AlienInvasionTurnState(
            active_dice=tuple(),
            earthlings_count=5,
            death_rays_count=3,
            tanks_count=2,
        )

        result = AlienInvasionEngine.calculate_final_score(state)

        assert result.earthlings_points == 5
        assert result.diversity_bonus == 0
        assert result.total_points == 5
        assert not result.is_bust

    def test_diversity_bonus(self):
        """Diversity bonus: +3 for all 3 Earthling types"""
        state = AlienInvasionTurnState(
            active_dice=tuple(),
            earthlings_count=6,
            selected_types=("human", "cow", "chicken"),
            death_rays_count=5,
            tanks_count=2,
        )

        result = AlienInvasionEngine.calculate_final_score(state)

        assert result.earthlings_points == 6
        assert result.diversity_bonus == 3
        assert result.total_points == 9
        assert not result.is_bust

    def test_no_diversity_bonus_with_two_types(self):
        """No bonus with only 2 Earthling types"""
        state = AlienInvasionTurnState(
            active_dice=tuple(),
            earthlings_count=5,
            selected_types=("human", "cow"),
            death_rays_count=3,
            tanks_count=2,
        )

        result = AlienInvasionEngine.calculate_final_score(state)

        assert result.diversity_bonus == 0
        assert result.total_points == 5


class TestBustCondition:
    """Tests for bust condition (Tanks > Death Rays)."""

    def test_bust_when_tanks_exceed_rays(self):
        """Bust: Tanks > Death Rays → score = 0"""
        state = AlienInvasionTurnState(
            active_dice=tuple(),
            earthlings_count=10,
            selected_types=("human", "cow", "chicken"),
            death_rays_count=2,
            tanks_count=5,  # 5 tanks > 2 rays
        )

        result = AlienInvasionEngine.calculate_final_score(state)

        assert result.is_bust
        assert result.total_points == 0  # Bust negates all points
        assert not result.is_safe_to_bank

    def test_safe_when_rays_equal_tanks(self):
        """Safe: Death Rays = Tanks"""
        state = AlienInvasionTurnState(
            active_dice=tuple(),
            earthlings_count=5,
            death_rays_count=3,
            tanks_count=3,
        )

        result = AlienInvasionEngine.calculate_final_score(state)

        assert not result.is_bust
        assert result.is_safe_to_bank
        assert result.total_points == 5

    def test_safe_when_rays_exceed_tanks(self):
        """Safe: Death Rays > Tanks"""
        state = AlienInvasionTurnState(
            active_dice=tuple(),
            earthlings_count=5,
            death_rays_count=10,
            tanks_count=3,
        )

        result = AlienInvasionEngine.calculate_final_score(state)

        assert not result.is_bust
        assert result.is_safe_to_bank
        assert result.total_points == 5

    def test_bust_negates_diversity_bonus(self):
        """Bust sets total to 0 even with diversity bonus"""
        state = AlienInvasionTurnState(
            active_dice=tuple(),
            earthlings_count=10,
            selected_types=("human", "cow", "chicken"),  # Would get +3 bonus
            death_rays_count=2,
            tanks_count=5,
        )

        result = AlienInvasionEngine.calculate_final_score(state)

        assert result.earthlings_points == 10
        assert result.diversity_bonus == 3
        assert result.is_bust
        assert result.total_points == 0  # Bust overrides everything


class TestTugOfWarRatio:
    """Tests for Tug of War meter ratio calculation."""

    def test_ratio_neutral_at_start(self):
        """Ratio = 0.5 when no rays or tanks"""
        state = AlienInvasionTurnState(
            active_dice=tuple(),
            death_rays_count=0,
            tanks_count=0,
        )

        ratio = AlienInvasionEngine.get_tug_of_war_ratio(state)
        assert ratio == 0.5

    def test_ratio_low_with_only_tanks(self):
        """Ratio near 0 with only tanks"""
        state = AlienInvasionTurnState(
            active_dice=tuple(),
            death_rays_count=0,
            tanks_count=5,
        )

        ratio = AlienInvasionEngine.get_tug_of_war_ratio(state)
        assert ratio == 0.0  # 0 / (0 + 5 + 1)

    def test_ratio_high_with_many_rays(self):
        """Ratio near 1.0 with many rays"""
        state = AlienInvasionTurnState(
            active_dice=tuple(),
            death_rays_count=10,
            tanks_count=2,
        )

        ratio = AlienInvasionEngine.get_tug_of_war_ratio(state)
        assert ratio == pytest.approx(10 / 13, abs=0.01)

    def test_ratio_balanced_at_equal(self):
        """Ratio near 0.5 when equal rays and tanks"""
        state = AlienInvasionTurnState(
            active_dice=tuple(),
            death_rays_count=5,
            tanks_count=5,
        )

        ratio = AlienInvasionEngine.get_tug_of_war_ratio(state)
        assert ratio == pytest.approx(5 / 11, abs=0.01)


class TestStuckState:
    """Tests for stuck state detection (forced bust)."""

    def test_not_stuck_before_first_roll(self):
        """Not stuck before rolling"""
        state = AlienInvasionEngine.create_initial_turn_state()
        assert not AlienInvasionEngine.is_stuck(state)

    def test_stuck_with_no_selections_and_no_earthlings(self):
        """Stuck when all dice become tanks and no earthlings"""
        state = AlienInvasionTurnState(
            active_dice=(6, 6, 6),
            held_indices=frozenset([0, 1, 2]),
            tanks_count=3,
            earthlings_count=0,
            roll_count=1,
        )

        assert AlienInvasionEngine.is_stuck(state)

    def test_not_stuck_with_earthlings(self):
        """Not stuck if we have earthlings (can bank)"""
        state = AlienInvasionTurnState(
            active_dice=(6, 6, 6),
            held_indices=frozenset([0, 1, 2]),
            tanks_count=3,
            earthlings_count=5,  # Have earthlings
            roll_count=1,
        )

        assert not AlienInvasionEngine.is_stuck(state)

    def test_not_stuck_with_available_selections(self):
        """Not stuck if selections available"""
        state = AlienInvasionTurnState(
            active_dice=(1, 2, 6),
            held_indices=frozenset([2]),  # Only tank held
            tanks_count=1,
            earthlings_count=0,
            roll_count=1,
        )

        assert not AlienInvasionEngine.is_stuck(state)


class TestPotentialScore:
    """Tests for potential score calculation during turn."""

    def test_potential_score_updates_on_selection(self):
        """Turn score updates as Earthlings are selected"""
        state = AlienInvasionTurnState(
            active_dice=(1, 1, 2, 2, 3),
            held_indices=frozenset(),
            roll_count=1,
        )

        # Select Humans
        state = AlienInvasionEngine.process_selection(state, FaceType.HUMAN, [0, 1])
        assert state.turn_score == 2  # 2 earthlings

        # Select Cows
        state = AlienInvasionTurnState(
            active_dice=state.active_dice,
            held_indices=state.held_indices,
            earthlings_count=state.earthlings_count,
            selected_types=state.selected_types,
            roll_count=state.roll_count,
        )
        state = AlienInvasionEngine.process_selection(state, FaceType.COW, [2, 3])
        assert state.turn_score == 4  # 4 earthlings

        # Select Chicken (triggers diversity bonus)
        state = AlienInvasionEngine.process_selection(state, FaceType.CHICKEN, [4])
        assert state.turn_score == 8  # 5 earthlings + 3 bonus


class TestInitialState:
    """Tests for initial turn state creation."""

    def test_create_initial_state(self):
        """Initial state is empty"""
        state = AlienInvasionEngine.create_initial_turn_state()

        assert len(state.active_dice) == 0
        assert len(state.held_indices) == 0
        assert state.tanks_count == 0
        assert state.death_rays_count == 0
        assert state.earthlings_count == 0
        assert len(state.selected_types) == 0
        assert state.turn_score == 0
        assert state.roll_count == 0


class TestFullTurnScenarios:
    """Integration tests for complete turn scenarios."""

    def test_successful_turn_with_diversity_bonus(self):
        """Complete turn: collect all 3 types and bank safely"""
        state = AlienInvasionEngine.create_initial_turn_state()

        # Roll 1: Get some variety
        roll1 = DiceRoll(values=(1, 1, 2, 2, 3, 4, 4, 5, 6, 6, 6, 1, 2), dice_type=DiceType.D6)
        state = AlienInvasionEngine.process_roll(state, roll1)

        # Should have 3 tanks auto-locked
        assert state.tanks_count == 3

        # Select Humans (indices 0, 1, 11)
        state = AlienInvasionEngine.process_selection(state, FaceType.HUMAN, [0, 1, 11])
        assert state.earthlings_count == 3

        # Select Cows (indices 2, 3, 12)
        state = AlienInvasionEngine.process_selection(state, FaceType.COW, [2, 3, 12])
        assert state.earthlings_count == 6

        # Select Chicken (index 4)
        state = AlienInvasionEngine.process_selection(state, FaceType.CHICKEN, [4])
        assert state.earthlings_count == 7
        assert state.turn_score == 10  # 7 + 3 bonus

        # Select Death Rays to defend (indices 5, 6, 7)
        state = AlienInvasionEngine.process_selection(state, FaceType.DEATH_RAY, [5, 6, 7])
        assert state.death_rays_count == 3

        # Check final score (safe: 3 rays = 3 tanks)
        result = AlienInvasionEngine.calculate_final_score(state)
        assert result.is_safe_to_bank
        assert result.total_points == 10

    def test_bust_scenario(self):
        """Turn ends in bust: too many tanks"""
        state = AlienInvasionEngine.create_initial_turn_state()

        # Roll with many tanks
        roll = DiceRoll(values=(1, 2, 3, 6, 6, 6, 6, 6, 4), dice_type=DiceType.D6)
        state = AlienInvasionEngine.process_roll(state, roll)

        assert state.tanks_count == 5

        # Collect Earthlings
        state = AlienInvasionEngine.process_selection(state, FaceType.HUMAN, [0])
        state = AlienInvasionEngine.process_selection(state, FaceType.COW, [1])
        state = AlienInvasionEngine.process_selection(state, FaceType.CHICKEN, [2])

        # Get 1 Death Ray
        state = AlienInvasionEngine.process_selection(state, FaceType.DEATH_RAY, [8])

        # Final score: BUST (5 tanks > 1 ray)
        result = AlienInvasionEngine.calculate_final_score(state)
        assert result.is_bust
        assert not result.is_safe_to_bank
        assert result.total_points == 0
