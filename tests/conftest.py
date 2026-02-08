"""
Devil's Dozen - Test Configuration and Fixtures

Common fixtures and test data for all test modules.
"""

import pytest
from typing import Any


# =============================================================================
# D6 SCORING TEST DATA (Peasant's Gamble)
# =============================================================================

@pytest.fixture
def d6_scoring_rolls() -> dict[str, tuple[tuple[int, ...], int, str]]:
    """
    Common D6 roll patterns with expected scores.

    Returns:
        Dict mapping name to (dice_values, expected_points, description)
    """
    return {
        # Singles
        "single_one": ((1,), 100, "Single 1"),
        "single_five": ((5,), 50, "Single 5"),
        "two_ones": ((1, 1), 200, "Two 1s"),
        "two_fives": ((5, 5), 100, "Two 5s"),
        "one_and_five": ((1, 5), 150, "One 1 and one 5"),

        # Non-scoring singles
        "single_two": ((2,), 0, "Single 2 (bust)"),
        "single_three": ((3,), 0, "Single 3 (bust)"),
        "single_four": ((4,), 0, "Single 4 (bust)"),
        "single_six": ((6,), 0, "Single 6 (bust)"),

        # Three of a kind
        "three_ones": ((1, 1, 1), 1000, "Three 1s"),
        "three_twos": ((2, 2, 2), 200, "Three 2s"),
        "three_threes": ((3, 3, 3), 300, "Three 3s"),
        "three_fours": ((4, 4, 4), 400, "Three 4s"),
        "three_fives": ((5, 5, 5), 500, "Three 5s"),
        "three_sixes": ((6, 6, 6), 600, "Three 6s"),

        # Four of a kind (double three of a kind)
        "four_ones": ((1, 1, 1, 1), 2000, "Four 1s"),
        "four_twos": ((2, 2, 2, 2), 400, "Four 2s"),
        "four_fours": ((4, 4, 4, 4), 800, "Four 4s"),
        "four_fives": ((5, 5, 5, 5), 1000, "Four 5s"),

        # Five of a kind
        "five_ones": ((1, 1, 1, 1, 1), 4000, "Five 1s"),
        "five_fours": ((4, 4, 4, 4, 4), 1600, "Five 4s"),

        # Six of a kind
        "six_ones": ((1, 1, 1, 1, 1, 1), 8000, "Six 1s"),
        "six_fours": ((4, 4, 4, 4, 4, 4), 3200, "Six 4s"),

        # Straights
        "low_straight": ((1, 2, 3, 4, 5), 500, "Low straight 1-5"),
        "high_straight": ((2, 3, 4, 5, 6), 750, "High straight 2-6"),
        "full_straight": ((1, 2, 3, 4, 5, 6), 1500, "Full straight 1-6"),

        # Straights with different order
        "low_straight_shuffled": ((5, 3, 1, 4, 2), 500, "Low straight shuffled"),
        "full_straight_shuffled": ((6, 4, 2, 5, 3, 1), 1500, "Full straight shuffled"),

        # Mixed combinations
        "three_ones_plus_five": ((1, 1, 1, 5), 1050, "Three 1s + single 5"),
        "three_fours_plus_one": ((4, 4, 4, 1), 500, "Three 4s + single 1"),
        "bust_roll": ((2, 3, 4, 6), 0, "Bust roll"),
    }


@pytest.fixture
def d6_bust_rolls() -> list[tuple[int, ...]]:
    """Rolls that should result in a bust."""
    return [
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
    ]


@pytest.fixture
def d6_hot_dice_rolls() -> list[tuple[int, ...]]:
    """Rolls where all dice score (hot dice)."""
    return [
        (1, 2, 3, 4, 5, 6),  # Full straight
        (1, 1, 1, 5, 5, 5),  # Two three-of-a-kinds
        (1, 1, 1, 1, 5, 5),  # Four 1s + two 5s
        (1, 5, 1, 5, 1, 5),  # Alternating
    ]


# =============================================================================
# D20 SCORING TEST DATA (Alchemist's Ascent)
# =============================================================================

@pytest.fixture
def d20_tier1_rolls() -> dict[str, tuple[tuple[int, ...], int, str]]:
    """
    D20 Tier 1 (Red) roll patterns with expected scores.

    Returns:
        Dict mapping name to (dice_values, expected_points, description)
    """
    return {
        # Singles
        "single_one": ((1,), 1, "Single 1"),
        "single_five": ((5,), 5, "Single 5"),
        "single_other": ((7,), 0, "Single 7 (no score)"),

        # Pairs
        "pair_of_ones": ((1, 1), 10, "Pair of 1s (special)"),
        "pair_of_fives": ((5, 5), 20, "Pair of 5s (special)"),
        "pair_of_sixteens": ((16, 16), 16, "Pair of 16s"),
        "pair_of_twenties": ((20, 20), 20, "Pair of 20s"),

        # Three of a kind (sum)
        "three_eighteens": ((18, 18, 18), 54, "Three 18s = 54"),
        "three_fours": ((4, 4, 4), 12, "Three 4s = 12"),
        "five_fours": ((4, 4, 4, 4, 4), 20, "Five 4s = 20"),

        # Sequences
        "seq_three": ((3, 4, 5), 10, "Sequence of 3"),
        "seq_four": ((9, 10, 11, 12), 20, "Sequence of 4"),
        "seq_six": ((9, 10, 11, 12, 13, 14), 40, "Sequence of 6"),
        "seq_high": ((17, 18, 19), 10, "High sequence"),
    }


@pytest.fixture
def d20_tier2_multiplier() -> int:
    """Tier 2 multiplier value."""
    return 5


# =============================================================================
# GAME STATE FIXTURES
# =============================================================================

@pytest.fixture
def empty_turn_state() -> dict[str, Any]:
    """Initial empty turn state."""
    return {
        "active_dice": tuple(),
        "held_indices": frozenset(),
        "turn_score": 0,
        "roll_count": 0,
        "is_hot_dice": False,
    }
