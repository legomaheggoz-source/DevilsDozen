"""
Devil's Dozen - Peasant's Gamble Engine (D6 Mode)

This module implements the scoring and game logic for the D6 dice game
inspired by Kingdom Come: Deliverance. All methods are stateless class
methods that operate on immutable inputs.

Scoring Rules:
    - Single 1: 100 points
    - Single 5: 50 points
    - Three 1s: 1,000 points
    - Three of X (2-6): X × 100 points
    - Four+ of a kind: Previous tier × 2
    - 1-2-3-4-5 (Low Straight): 500 points
    - 2-3-4-5-6 (High Straight): 750 points
    - 1-2-3-4-5-6 (Full Straight): 1,500 points
"""

from collections import Counter
from typing import Sequence
import random

from src.engine.base import (
    DiceRoll,
    DiceType,
    ScoringBreakdown,
    ScoringCategory,
    ScoringResult,
    TurnState,
)
from src.engine.validators import validate_dice_values, validate_held_indices


class PeasantsGambleEngine:
    """
    Stateless engine for the Peasant's Gamble (D6) game mode.

    All methods are class methods operating on immutable data.
    State is passed in and returned, never stored.
    """

    # Constants
    NUM_DICE = 6
    DICE_TYPE = DiceType.D6

    # Scoring values
    SINGLE_ONE_POINTS = 100
    SINGLE_FIVE_POINTS = 50
    THREE_ONES_POINTS = 1000
    LOW_STRAIGHT_POINTS = 500
    HIGH_STRAIGHT_POINTS = 750
    FULL_STRAIGHT_POINTS = 1500

    @classmethod
    def roll_dice(cls, count: int = NUM_DICE) -> DiceRoll:
        """
        Roll the specified number of D6 dice.

        Args:
            count: Number of dice to roll (default: 6)

        Returns:
            DiceRoll with random values
        """
        values = tuple(random.randint(1, 6) for _ in range(count))
        return DiceRoll(values=values, dice_type=cls.DICE_TYPE)

    @classmethod
    def calculate_score(
        cls,
        dice: Sequence[int] | DiceRoll
    ) -> ScoringResult:
        """
        Calculate the score for a given dice roll.

        This method identifies all scoring combinations in the roll and
        returns a complete breakdown. Order of detection matters:
        straights are checked before sets to avoid partial consumption.

        Args:
            dice: Dice values to score (sequence or DiceRoll)

        Returns:
            ScoringResult with total points, breakdown, and scoring indices
        """
        if isinstance(dice, DiceRoll):
            values = dice.values
        else:
            values = validate_dice_values(dice, DiceType.D6, min_count=0)

        if not values:
            return ScoringResult(
                points=0,
                breakdown=tuple(),
                scoring_dice_indices=frozenset(),
                is_bust=True
            )

        breakdown: list[ScoringBreakdown] = []
        scoring_indices: set[int] = set()
        remaining_counts = Counter(values)

        # Check straights first (they consume multiple dice)
        straight_result = cls._check_straights(values, remaining_counts)
        if straight_result:
            breakdown.append(straight_result[0])
            scoring_indices.update(straight_result[1])

        # Check for sets (three or more of a kind)
        sets_result = cls._check_sets(values, remaining_counts)
        breakdown.extend(sets_result[0])
        scoring_indices.update(sets_result[1])

        # Check remaining singles (1s and 5s)
        singles_result = cls._check_singles(values, remaining_counts)
        breakdown.extend(singles_result[0])
        scoring_indices.update(singles_result[1])

        total_points = sum(item.points for item in breakdown)
        is_bust = len(scoring_indices) == 0

        return ScoringResult(
            points=total_points,
            breakdown=tuple(breakdown),
            scoring_dice_indices=frozenset(scoring_indices),
            is_bust=is_bust
        )

    @classmethod
    def _check_straights(
        cls,
        values: tuple[int, ...],
        remaining: Counter[int]
    ) -> tuple[ScoringBreakdown, set[int]] | None:
        """
        Check for straight combinations.

        Straights are mutually exclusive - only one can be scored.
        Full straight takes precedence, then high, then low.

        Returns:
            Tuple of (breakdown, indices) or None if no straight found
        """
        sorted_unique = sorted(set(values))

        # Full straight: 1-2-3-4-5-6
        if sorted_unique == [1, 2, 3, 4, 5, 6] and len(values) == 6:
            indices = set(range(6))
            for v in [1, 2, 3, 4, 5, 6]:
                remaining[v] -= 1
            return (
                ScoringBreakdown(
                    category=ScoringCategory.FULL_STRAIGHT,
                    dice_values=(1, 2, 3, 4, 5, 6),
                    points=cls.FULL_STRAIGHT_POINTS,
                    description="Full Straight (1-2-3-4-5-6)"
                ),
                indices
            )

        # High straight: 2-3-4-5-6
        if all(remaining[v] >= 1 for v in [2, 3, 4, 5, 6]):
            indices = cls._find_indices_for_values(values, [2, 3, 4, 5, 6])
            if len(indices) == 5:
                for v in [2, 3, 4, 5, 6]:
                    remaining[v] -= 1
                return (
                    ScoringBreakdown(
                        category=ScoringCategory.HIGH_STRAIGHT,
                        dice_values=(2, 3, 4, 5, 6),
                        points=cls.HIGH_STRAIGHT_POINTS,
                        description="High Straight (2-3-4-5-6)"
                    ),
                    indices
                )

        # Low straight: 1-2-3-4-5
        if all(remaining[v] >= 1 for v in [1, 2, 3, 4, 5]):
            indices = cls._find_indices_for_values(values, [1, 2, 3, 4, 5])
            if len(indices) == 5:
                for v in [1, 2, 3, 4, 5]:
                    remaining[v] -= 1
                return (
                    ScoringBreakdown(
                        category=ScoringCategory.LOW_STRAIGHT,
                        dice_values=(1, 2, 3, 4, 5),
                        points=cls.LOW_STRAIGHT_POINTS,
                        description="Low Straight (1-2-3-4-5)"
                    ),
                    indices
                )

        return None

    @classmethod
    def _check_sets(
        cls,
        values: tuple[int, ...],
        remaining: Counter[int]
    ) -> tuple[list[ScoringBreakdown], set[int]]:
        """
        Check for three or more of a kind.

        Points double for each additional die beyond three.
        Special case: Three 1s = 1000 points.
        """
        breakdown: list[ScoringBreakdown] = []
        indices: set[int] = set()

        for face_value in range(1, 7):
            count = remaining[face_value]
            if count >= 3:
                # Calculate base points for three of a kind
                if face_value == 1:
                    base_points = cls.THREE_ONES_POINTS
                else:
                    base_points = face_value * 100

                # Double for each additional die
                points = base_points
                for _ in range(count - 3):
                    points *= 2

                # Determine category
                if count == 3:
                    category = ScoringCategory.THREE_OF_A_KIND
                elif count == 4:
                    category = ScoringCategory.FOUR_OF_A_KIND
                elif count == 5:
                    category = ScoringCategory.FIVE_OF_A_KIND
                else:
                    category = ScoringCategory.SIX_OF_A_KIND

                # Find indices
                set_indices = cls._find_indices_for_value(values, face_value, count)
                indices.update(set_indices)
                remaining[face_value] = 0

                breakdown.append(ScoringBreakdown(
                    category=category,
                    dice_values=tuple([face_value] * count),
                    points=points,
                    description=f"{count}x {face_value}s"
                ))

        return breakdown, indices

    @classmethod
    def _check_singles(
        cls,
        values: tuple[int, ...],
        remaining: Counter[int]
    ) -> tuple[list[ScoringBreakdown], set[int]]:
        """
        Check for remaining single 1s and 5s.

        Only 1s and 5s score as singles.
        """
        breakdown: list[ScoringBreakdown] = []
        indices: set[int] = set()

        # Check for 1s
        ones_count = remaining[1]
        if ones_count > 0:
            points = ones_count * cls.SINGLE_ONE_POINTS
            ones_indices = cls._find_indices_for_value(values, 1, ones_count, exclude=indices)
            indices.update(ones_indices)
            remaining[1] = 0

            breakdown.append(ScoringBreakdown(
                category=ScoringCategory.SINGLE_ONE,
                dice_values=tuple([1] * ones_count),
                points=points,
                description=f"{ones_count}x Single 1{'s' if ones_count > 1 else ''}"
            ))

        # Check for 5s
        fives_count = remaining[5]
        if fives_count > 0:
            points = fives_count * cls.SINGLE_FIVE_POINTS
            fives_indices = cls._find_indices_for_value(values, 5, fives_count, exclude=indices)
            indices.update(fives_indices)
            remaining[5] = 0

            breakdown.append(ScoringBreakdown(
                category=ScoringCategory.SINGLE_FIVE,
                dice_values=tuple([5] * fives_count),
                points=points,
                description=f"{fives_count}x Single 5{'s' if fives_count > 1 else ''}"
            ))

        return breakdown, indices

    @classmethod
    def _find_indices_for_values(
        cls,
        values: tuple[int, ...],
        target_values: list[int]
    ) -> set[int]:
        """Find one index for each target value."""
        indices: set[int] = set()
        targets_needed = list(target_values)

        for i, v in enumerate(values):
            if v in targets_needed and i not in indices:
                targets_needed.remove(v)
                indices.add(i)

        return indices

    @classmethod
    def _find_indices_for_value(
        cls,
        values: tuple[int, ...],
        target: int,
        count: int,
        exclude: set[int] | None = None
    ) -> set[int]:
        """Find `count` indices with the target value."""
        indices: set[int] = set()
        exclude = exclude or set()
        found = 0

        for i, v in enumerate(values):
            if v == target and i not in exclude and found < count:
                indices.add(i)
                found += 1

        return indices

    @classmethod
    def is_bust(cls, dice: Sequence[int] | DiceRoll) -> bool:
        """
        Check if a roll is a bust (no scoring dice).

        Args:
            dice: Dice values to check

        Returns:
            True if the roll contains no scoring combinations
        """
        result = cls.calculate_score(dice)
        return result.is_bust

    @classmethod
    def is_hot_dice(
        cls,
        dice: Sequence[int] | DiceRoll,
        held_indices: frozenset[int] | set[int] | None = None
    ) -> bool:
        """
        Check if all dice have scored (hot dice).

        Hot dice means the player can pick up all dice and roll again.
        This occurs when every die in the roll contributes to scoring.

        Args:
            dice: Dice values to check
            held_indices: Already held dice indices (optional)

        Returns:
            True if all dice have scored
        """
        if isinstance(dice, DiceRoll):
            values = dice.values
        else:
            values = tuple(dice)

        if not values:
            return False

        result = cls.calculate_score(values)

        # All dice scored if scoring indices equals total dice count
        return len(result.scoring_dice_indices) == len(values)

    @classmethod
    def get_minimum_score_to_bank(cls) -> int:
        """
        Get the minimum score required to bank points.

        In standard rules, there is no minimum - any score can be banked.
        This is included for potential house rules.
        """
        return 0

    @classmethod
    def create_initial_turn_state(cls) -> TurnState:
        """
        Create the initial state for a new turn.

        Returns:
            Fresh TurnState with 6 unrolled dice
        """
        return TurnState(
            active_dice=tuple(),
            held_indices=frozenset(),
            turn_score=0,
            roll_count=0,
            is_hot_dice=False
        )

    @classmethod
    def process_roll(
        cls,
        state: TurnState,
        roll: DiceRoll | None = None
    ) -> tuple[TurnState, ScoringResult]:
        """
        Process a dice roll and return updated state.

        Args:
            state: Current turn state
            roll: Roll to process (or None to generate new roll)

        Returns:
            Tuple of (new_state, scoring_result)
        """
        # Determine how many dice to roll
        if state.roll_count == 0 or state.is_hot_dice:
            dice_count = cls.NUM_DICE
        else:
            dice_count = state.available_dice_count

        # Generate roll if not provided
        if roll is None:
            roll = cls.roll_dice(dice_count)

        result = cls.calculate_score(roll.values)

        # Check for bust
        if result.is_bust:
            new_state = TurnState(
                active_dice=roll.values,
                held_indices=frozenset(),
                turn_score=0,  # Lose all accumulated points
                roll_count=state.roll_count + 1,
                is_hot_dice=False
            )
            return new_state, result

        # Check for hot dice
        is_hot = cls.is_hot_dice(roll.values)

        new_state = TurnState(
            active_dice=roll.values,
            held_indices=frozenset(),  # Reset held indices for new roll
            turn_score=state.turn_score,  # Keep previous score
            roll_count=state.roll_count + 1,
            is_hot_dice=is_hot
        )

        return new_state, result

    @classmethod
    def process_hold(
        cls,
        state: TurnState,
        indices_to_hold: frozenset[int] | set[int]
    ) -> tuple[TurnState, ScoringResult]:
        """
        Process holding dice and add their score to turn total.

        Args:
            state: Current turn state
            indices_to_hold: Indices of dice to hold

        Returns:
            Tuple of (new_state, scoring_result for held dice)
        """
        indices = validate_held_indices(indices_to_hold, len(state.active_dice))

        # Get values of dice being held
        held_values = tuple(state.active_dice[i] for i in sorted(indices))

        # Calculate score for held dice only
        result = cls.calculate_score(held_values)

        # Validate that held dice actually score
        if result.is_bust:
            raise ValueError("Cannot hold non-scoring dice.")

        new_held = state.held_indices | frozenset(indices)
        new_score = state.turn_score + result.points

        # Check if all dice are now held (hot dice)
        all_held = len(new_held) == len(state.active_dice)
        is_hot = all_held

        new_state = TurnState(
            active_dice=state.active_dice,
            held_indices=new_held,
            turn_score=new_score,
            roll_count=state.roll_count,
            is_hot_dice=is_hot
        )

        return new_state, result
