"""
Devil's Dozen - Input Validation Utilities

Provides validation functions for game engine inputs. All validators
either return validated data or raise descriptive ValueError exceptions.
"""

from typing import Sequence

from src.engine.base import DiceType


def validate_dice_values(
    values: Sequence[int],
    dice_type: DiceType = DiceType.D6,
    min_count: int = 1,
    max_count: int | None = None
) -> tuple[int, ...]:
    """
    Validate and normalize dice values.

    Args:
        values: Sequence of dice values to validate
        dice_type: Type of dice (determines valid range)
        min_count: Minimum number of dice required
        max_count: Maximum number of dice allowed (None = no limit)

    Returns:
        Validated values as a tuple

    Raises:
        ValueError: If validation fails
    """
    if not values:
        if min_count > 0:
            raise ValueError(f"At least {min_count} dice required.")
        return tuple()

    values_tuple = tuple(values)
    count = len(values_tuple)

    if count < min_count:
        raise ValueError(f"At least {min_count} dice required, got {count}.")

    if max_count is not None and count > max_count:
        raise ValueError(f"At most {max_count} dice allowed, got {count}.")

    max_value = dice_type.value
    for i, value in enumerate(values_tuple):
        if not isinstance(value, int):
            raise ValueError(f"Die value at index {i} must be an integer, got {type(value).__name__}.")
        if not (1 <= value <= max_value):
            raise ValueError(
                f"Die value at index {i} is {value}, must be between 1 and {max_value} for {dice_type.name}."
            )

    return values_tuple


def validate_held_indices(
    indices: Sequence[int] | frozenset[int] | set[int],
    dice_count: int
) -> frozenset[int]:
    """
    Validate indices of held dice.

    Args:
        indices: Collection of dice indices that are held
        dice_count: Total number of dice in the roll

    Returns:
        Validated indices as a frozenset

    Raises:
        ValueError: If any index is out of range
    """
    if not indices:
        return frozenset()

    indices_set = frozenset(indices)

    for idx in indices_set:
        if not isinstance(idx, int):
            raise ValueError(f"Held index must be an integer, got {type(idx).__name__}.")
        if not (0 <= idx < dice_count):
            raise ValueError(
                f"Held index {idx} is out of range. Must be between 0 and {dice_count - 1}."
            )

    return indices_set


def validate_score(score: int, allow_negative: bool = False) -> int:
    """
    Validate a score value.

    Args:
        score: Score to validate
        allow_negative: Whether negative scores are allowed

    Returns:
        Validated score

    Raises:
        ValueError: If score is invalid
    """
    if not isinstance(score, int):
        raise ValueError(f"Score must be an integer, got {type(score).__name__}.")

    if not allow_negative and score < 0:
        raise ValueError(f"Score cannot be negative, got {score}.")

    return score


def validate_player_count(count: int) -> int:
    """
    Validate number of players.

    Args:
        count: Number of players

    Returns:
        Validated count

    Raises:
        ValueError: If count is not 2-4
    """
    if not isinstance(count, int):
        raise ValueError(f"Player count must be an integer, got {type(count).__name__}.")

    if not (2 <= count <= 4):
        raise ValueError(f"Player count must be 2-4, got {count}.")

    return count


def validate_target_score(score: int, valid_options: set[int] | None = None) -> int:
    """
    Validate target score for a game.

    Args:
        score: Target score to validate
        valid_options: Set of valid score options (None = any positive)

    Returns:
        Validated score

    Raises:
        ValueError: If score is invalid
    """
    if not isinstance(score, int):
        raise ValueError(f"Target score must be an integer, got {type(score).__name__}.")

    if score <= 0:
        raise ValueError(f"Target score must be positive, got {score}.")

    if valid_options is not None and score not in valid_options:
        raise ValueError(f"Target score must be one of {valid_options}, got {score}.")

    return score
