"""
Devil's Dozen - Alchemist's Ascent Engine (D20 Mode)

This module implements the scoring and game logic for the tiered D20 dice game.
Players progress through three tiers with escalating risk and reward.

Tier System:
    - Tier 1 (Red, 0-100 pts): 8 D20s, standard scoring
    - Tier 2 (Green, 101-200 pts): 3 D20s, 5× multiplier, risky rerolls
    - Tier 3 (Blue, 201-250 pts): 1 D20, high stakes finale

Scoring (Tier 1):
    - Single 1: 1 point
    - Single 5: 5 points
    - Pair: Face value (pair of 16s = 16 pts)
    - Pair of 1s: 10 points
    - Pair of 5s: 20 points
    - Three+ of a kind: Sum of dice values
    - Sequence of 3: 10 points (+10 per additional die)
"""

from collections import Counter
from dataclasses import dataclass
from typing import Sequence
import random

from src.engine.base import (
    DiceRoll,
    DiceType,
    ScoringBreakdown,
    ScoringCategory,
    ScoringResult,
    Tier,
    TurnState,
)
from src.engine.validators import validate_dice_values


@dataclass(frozen=True)
class RerollResult:
    """Result of a single die reroll in Tier 2."""
    old_value: int
    new_value: int
    is_bust: bool
    points_if_not_bust: int


class AlchemistsAscentEngine:
    """
    Stateless engine for the Alchemist's Ascent (D20) game mode.

    All methods are class methods operating on immutable data.
    State is passed in and returned, never stored.
    """

    # Constants
    DICE_TYPE = DiceType.D20
    TARGET_SCORE = 250

    # Tier thresholds
    TIER_1_MAX = 100
    TIER_2_MAX = 200
    TIER_3_MAX = 250

    # Dice counts per tier
    TIER_1_DICE = 8
    TIER_2_DICE = 3
    TIER_3_DICE = 1

    # Tier 2 multiplier
    TIER_2_MULTIPLIER = 5

    # Special values in Tier 3
    TIER_3_RESET_VALUE = 1
    TIER_3_KINGMAKER_VALUE = 20

    @classmethod
    def get_tier_for_score(cls, score: int) -> Tier:
        """
        Determine which tier a player is in based on their score.

        Args:
            score: Player's current total score

        Returns:
            The tier the player should use
        """
        if score <= cls.TIER_1_MAX:
            return Tier.RED
        elif score <= cls.TIER_2_MAX:
            return Tier.GREEN
        else:
            return Tier.BLUE

    @classmethod
    def get_dice_count_for_tier(cls, tier: Tier) -> int:
        """Get the number of dice to roll for a tier."""
        if tier == Tier.RED:
            return cls.TIER_1_DICE
        elif tier == Tier.GREEN:
            return cls.TIER_2_DICE
        else:
            return cls.TIER_3_DICE

    @classmethod
    def roll_dice(cls, count: int) -> DiceRoll:
        """
        Roll the specified number of D20 dice.

        Args:
            count: Number of dice to roll

        Returns:
            DiceRoll with random D20 values
        """
        values = tuple(random.randint(1, 20) for _ in range(count))
        return DiceRoll(values=values, dice_type=cls.DICE_TYPE)

    @classmethod
    def calculate_score_tier1(
        cls,
        dice: Sequence[int] | DiceRoll
    ) -> ScoringResult:
        """
        Calculate score for Tier 1 (Red) rules.

        Scoring:
            - Single 1: 1 pt, Single 5: 5 pts
            - Pair: Face value (pair of 1s = 10, pair of 5s = 20)
            - Three+ of kind: Sum of dice
            - Sequence of 3+: 10 pts per 3, +10 per additional

        Args:
            dice: Dice values to score

        Returns:
            ScoringResult with breakdown
        """
        if isinstance(dice, DiceRoll):
            values = dice.values
        else:
            values = validate_dice_values(dice, DiceType.D20, min_count=0)

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

        # Check sequences first (they consume multiple dice)
        seq_result = cls._check_sequences(values, remaining_counts)
        breakdown.extend(seq_result[0])
        scoring_indices.update(seq_result[1])

        # Check sets (pairs and three+ of a kind)
        sets_result = cls._check_sets_tier1(values, remaining_counts)
        breakdown.extend(sets_result[0])
        scoring_indices.update(sets_result[1])

        # Check remaining singles (1s and 5s only)
        singles_result = cls._check_singles_tier1(values, remaining_counts)
        breakdown.extend(singles_result[0])
        scoring_indices.update(singles_result[1])

        total_points = sum(item.points for item in breakdown)

        return ScoringResult(
            points=total_points,
            breakdown=tuple(breakdown),
            scoring_dice_indices=frozenset(scoring_indices),
            is_bust=total_points == 0
        )

    @classmethod
    def calculate_score_tier2(
        cls,
        dice: Sequence[int] | DiceRoll
    ) -> ScoringResult:
        """
        Calculate score for Tier 2 (Green) rules.

        Uses the same Tier 1 scoring rules (pairs, sequences, singles 1/5)
        but with a 5× multiplier on all points. Tier 2 never busts on a
        roll — busting only happens on a failed reroll (handled separately).

        Args:
            dice: Dice values to score

        Returns:
            ScoringResult with Tier 1 scoring × 5 multiplier
        """
        base_result = cls.calculate_score_tier1(dice)

        # Apply 5× multiplier to all points
        multiplied_breakdown = tuple(
            ScoringBreakdown(
                category=item.category,
                dice_values=item.dice_values,
                points=item.points * cls.TIER_2_MULTIPLIER,
                description=f"{item.description} (×5)"
            )
            for item in base_result.breakdown
        )

        total = base_result.points * cls.TIER_2_MULTIPLIER

        # Tier 2 never busts on a roll — player can always reroll
        return ScoringResult(
            points=total,
            breakdown=multiplied_breakdown,
            scoring_dice_indices=base_result.scoring_dice_indices,
            is_bust=False
        )

    @classmethod
    def calculate_score_tier3(
        cls,
        dice_value: int,
        current_score: int,
        last_place_player_id: str | None = None
    ) -> tuple[int, bool, bool, str | None]:
        """
        Calculate result for Tier 3 (Blue) single die roll.

        Args:
            dice_value: The value rolled (1-20)
            current_score: Player's current total score
            last_place_player_id: ID of last place player (for Kingmaker)

        Returns:
            Tuple of (points_delta, is_reset, is_kingmaker, beneficiary_id)
            - points_delta: Points to add (or negative for context)
            - is_reset: True if rolled 1 (reset to 0)
            - is_kingmaker: True if rolled 20 (give 20 to last place)
            - beneficiary_id: Player who gets Kingmaker points
        """
        if dice_value == cls.TIER_3_RESET_VALUE:
            # Devastating reset - lose ALL points
            return (-current_score, True, False, None)

        if dice_value == cls.TIER_3_KINGMAKER_VALUE:
            # Kingmaker - give 20 points to last place
            return (0, False, True, last_place_player_id)

        # Normal roll - face value as points
        return (dice_value, False, False, None)

    @classmethod
    def _check_sequences(
        cls,
        values: tuple[int, ...],
        remaining: Counter[int]
    ) -> tuple[list[ScoringBreakdown], set[int]]:
        """
        Check for sequential runs of 3+ consecutive numbers.

        Scoring:
            - Sequence of 3: 10 points
            - Sequence of 4: 20 points
            - Sequence of 5: 30 points
            - etc. (+10 per additional die)
        """
        breakdown: list[ScoringBreakdown] = []
        indices: set[int] = set()

        # Find all unique values that exist
        unique_sorted = sorted(set(remaining.keys()))

        # Find runs of consecutive numbers
        i = 0
        while i < len(unique_sorted):
            # Start a potential sequence
            seq_start = unique_sorted[i]
            seq_values = [seq_start]

            # Extend while consecutive
            j = i + 1
            while j < len(unique_sorted) and unique_sorted[j] == seq_values[-1] + 1:
                seq_values.append(unique_sorted[j])
                j += 1

            # Score if sequence is 3+ long
            if len(seq_values) >= 3:
                # Points: 10 for first 3, +10 for each additional
                points = 10 * (len(seq_values) - 2)

                # Find indices for these values
                seq_indices = cls._find_indices_for_sequence(values, seq_values)
                indices.update(seq_indices)

                # Update remaining counts
                for v in seq_values:
                    remaining[v] -= 1
                    if remaining[v] == 0:
                        del remaining[v]

                breakdown.append(ScoringBreakdown(
                    category=ScoringCategory.SEQUENCE,
                    dice_values=tuple(seq_values),
                    points=points,
                    description=f"Sequence {min(seq_values)}-{max(seq_values)}"
                ))

            i = j if j > i + 1 else i + 1

        return breakdown, indices

    @classmethod
    def _check_sets_tier1(
        cls,
        values: tuple[int, ...],
        remaining: Counter[int]
    ) -> tuple[list[ScoringBreakdown], set[int]]:
        """
        Check for pairs and three+ of a kind.

        Pairs: Face value (special: 1s = 10, 5s = 20)
        Three+: Sum of dice values
        """
        breakdown: list[ScoringBreakdown] = []
        indices: set[int] = set()

        for face_value in list(remaining.keys()):
            count = remaining[face_value]

            if count >= 3:
                # 1s and 5s: pair value doubled for each die beyond 2
                # (pair of 1s=10, three=20, four=40; pair of 5s=20, three=40, four=80)
                # Other numbers: sum of dice values
                if face_value == 1:
                    points = 10 * (2 ** (count - 2))
                elif face_value == 5:
                    points = 20 * (2 ** (count - 2))
                else:
                    points = face_value * count
                set_indices = cls._find_indices_for_value(values, face_value, count)
                indices.update(set_indices)
                remaining[face_value] = 0

                breakdown.append(ScoringBreakdown(
                    category=ScoringCategory.THREE_OF_A_KIND,
                    dice_values=tuple([face_value] * count),
                    points=points,
                    description=f"{count}× {face_value}s"
                ))

            elif count == 2:
                # Pair: face value (special cases for 1s and 5s)
                if face_value == 1:
                    points = 10
                elif face_value == 5:
                    points = 20
                else:
                    points = face_value

                pair_indices = cls._find_indices_for_value(values, face_value, 2)
                indices.update(pair_indices)
                remaining[face_value] = 0

                breakdown.append(ScoringBreakdown(
                    category=ScoringCategory.PAIR,
                    dice_values=(face_value, face_value),
                    points=points,
                    description=f"Pair of {face_value}s"
                ))

        return breakdown, indices

    @classmethod
    def _check_singles_tier1(
        cls,
        values: tuple[int, ...],
        remaining: Counter[int]
    ) -> tuple[list[ScoringBreakdown], set[int]]:
        """
        Check for remaining single 1s and 5s.

        Only 1s (1 pt) and 5s (5 pts) score as singles.
        """
        breakdown: list[ScoringBreakdown] = []
        indices: set[int] = set()

        # Single 1s
        if remaining.get(1, 0) == 1:
            idx = cls._find_indices_for_value(values, 1, 1)
            indices.update(idx)
            remaining[1] = 0

            breakdown.append(ScoringBreakdown(
                category=ScoringCategory.SINGLE_ONE,
                dice_values=(1,),
                points=1,
                description="Single 1"
            ))

        # Single 5s
        if remaining.get(5, 0) == 1:
            idx = cls._find_indices_for_value(values, 5, 1)
            indices.update(idx)
            remaining[5] = 0

            breakdown.append(ScoringBreakdown(
                category=ScoringCategory.SINGLE_FIVE,
                dice_values=(5,),
                points=5,
                description="Single 5"
            ))

        return breakdown, indices

    @classmethod
    def _find_indices_for_sequence(
        cls,
        values: tuple[int, ...],
        seq_values: list[int]
    ) -> set[int]:
        """Find one index for each value in the sequence."""
        indices: set[int] = set()
        targets_needed = list(seq_values)

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
    def process_reroll(
        cls,
        die_index: int,
        previous_values: tuple[int, ...],
        new_value: int | None = None
    ) -> RerollResult:
        """
        Process a single die reroll in Tier 2.

        In Tier 2, players can reroll individual dice, but if the new
        value is lower than the previous value, it's an immediate bust.

        Args:
            die_index: Index of the die being rerolled
            previous_values: Previous dice values
            new_value: New roll value (or None to generate)

        Returns:
            RerollResult with bust status and points
        """
        old_value = previous_values[die_index]

        if new_value is None:
            new_value = random.randint(1, 20)

        is_bust = new_value <= old_value

        # In Tier 2, every die scores face value × multiplier
        if not is_bust:
            points = new_value * cls.TIER_2_MULTIPLIER
        else:
            points = 0

        return RerollResult(
            old_value=old_value,
            new_value=new_value,
            is_bust=is_bust,
            points_if_not_bust=points
        )

    @classmethod
    def calculate_score(
        cls,
        dice: Sequence[int] | DiceRoll,
        tier: Tier
    ) -> ScoringResult:
        """
        Calculate score using the appropriate tier rules.

        Args:
            dice: Dice values to score
            tier: Current tier (determines scoring rules)

        Returns:
            ScoringResult with tier-appropriate scoring
        """
        if tier == Tier.RED:
            return cls.calculate_score_tier1(dice)
        elif tier == Tier.GREEN:
            return cls.calculate_score_tier2(dice)
        else:
            # Tier 3 is handled differently (single die, special rules)
            raise ValueError(
                "Tier 3 scoring requires calculate_score_tier3() method"
            )

    @classmethod
    def create_initial_turn_state(cls, current_score: int) -> TurnState:
        """
        Create the initial state for a new turn.

        Args:
            current_score: Player's current total score

        Returns:
            Fresh TurnState with appropriate tier
        """
        tier = cls.get_tier_for_score(current_score)

        return TurnState(
            active_dice=tuple(),
            held_indices=frozenset(),
            turn_score=0,
            roll_count=0,
            is_hot_dice=False,
            tier=tier,
            previous_dice=tuple()
        )

    @classmethod
    def process_roll(
        cls,
        state: TurnState,
        current_score: int,
        roll: DiceRoll | None = None
    ) -> tuple[TurnState, ScoringResult | tuple[int, bool, bool, str | None]]:
        """
        Process a dice roll for the current tier.

        Args:
            state: Current turn state
            current_score: Player's total score (for tier determination)
            roll: Roll to process (or None to generate)

        Returns:
            For Tiers 1-2: Tuple of (new_state, ScoringResult)
            For Tier 3: Tuple of (new_state, (points, is_reset, is_kingmaker, beneficiary))
        """
        tier = cls.get_tier_for_score(current_score)
        dice_count = cls.get_dice_count_for_tier(tier)

        if roll is None:
            roll = cls.roll_dice(dice_count)

        if tier == Tier.BLUE:
            # Tier 3: Single die with special rules
            result = cls.calculate_score_tier3(
                roll.values[0],
                current_score,
                None  # Last place player handled by caller
            )

            new_state = TurnState(
                active_dice=roll.values,
                held_indices=frozenset(),
                turn_score=result[0] if result[0] > 0 else 0,
                roll_count=state.roll_count + 1,
                is_hot_dice=False,
                tier=tier,
                previous_dice=tuple()
            )

            return new_state, result

        else:
            # Tiers 1-2: Standard scoring
            result = cls.calculate_score(roll.values, tier)

            new_state = TurnState(
                active_dice=roll.values,
                held_indices=frozenset(),
                turn_score=state.turn_score + result.points,
                roll_count=state.roll_count + 1,
                is_hot_dice=False,
                tier=tier,
                previous_dice=roll.values  # For Tier 2 reroll comparison
            )

            return new_state, result
