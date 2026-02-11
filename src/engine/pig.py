"""
Devil's Dozen - Pig Engine

Simple single-die push-your-luck game. Roll a D6: 2-6 adds face value
to turn score, rolling 1 = bust (lose all turn points). Bank anytime.
First to target wins.

All methods are stateless class methods operating on immutable data.
"""

import random

from src.engine.base import DiceRoll, DiceType, ScoringResult, ScoringBreakdown, ScoringCategory


class PigEngine:
    """
    Stateless engine for the Pig game mode.

    All methods are class methods operating on immutable data.
    State is passed in and returned, never stored.
    """

    NUM_DICE = 1
    DICE_TYPE = DiceType.D6

    @classmethod
    def roll_dice(cls) -> DiceRoll:
        """Roll a single D6.

        Returns:
            DiceRoll with one random value (1-6)
        """
        value = random.randint(1, 6)
        return DiceRoll(values=(value,), dice_type=cls.DICE_TYPE)

    @classmethod
    def is_bust(cls, dice: DiceRoll | tuple[int, ...]) -> bool:
        """Check if a roll is a bust (rolled a 1).

        Args:
            dice: A DiceRoll or tuple of dice values

        Returns:
            True if the die shows 1
        """
        values = dice.values if isinstance(dice, DiceRoll) else dice
        return values[0] == 1

    @classmethod
    def calculate_score(cls, dice: DiceRoll | tuple[int, ...]) -> ScoringResult:
        """Calculate score for a single die roll.

        Rolling 1 = bust (0 points). Rolling 2-6 = face value.

        Args:
            dice: A DiceRoll or tuple of dice values

        Returns:
            ScoringResult with points and bust status
        """
        values = dice.values if isinstance(dice, DiceRoll) else tuple(dice)
        value = values[0]

        if value == 1:
            return ScoringResult(
                points=0,
                breakdown=(),
                scoring_dice_indices=frozenset(),
                is_bust=True,
            )

        return ScoringResult(
            points=value,
            breakdown=(
                ScoringBreakdown(
                    category=ScoringCategory.SINGLE_FIVE,  # Reuse; Pig has no unique category
                    dice_values=(value,),
                    points=value,
                    description=f"Rolled {value}",
                ),
            ),
            scoring_dice_indices=frozenset({0}),
            is_bust=False,
        )

    @classmethod
    def process_roll(
        cls,
        turn_score: int,
        roll: DiceRoll | None = None,
    ) -> tuple[int, DiceRoll, bool]:
        """Process a complete roll: roll dice, check bust, update turn score.

        Args:
            turn_score: Current accumulated turn score
            roll: Optional pre-determined roll (for testing)

        Returns:
            Tuple of (new_turn_score, dice_roll, is_bust)
        """
        if roll is None:
            roll = cls.roll_dice()

        if cls.is_bust(roll):
            return (0, roll, True)

        new_score = turn_score + roll.values[0]
        return (new_score, roll, False)
