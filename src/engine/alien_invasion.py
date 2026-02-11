"""
Devil's Dozen - Alien Invasion Engine (Martian Dice Mode)

This module implements the scoring and game logic for the Alien Invasion mode,
inspired by Martian Dice. All methods are stateless class methods that operate
on immutable inputs.

Game Mechanics:
    - 13 D6 dice with custom face mappings
    - Tanks (face 6) auto-lock when rolled
    - Group selection: click a type to select ALL dice of that type
    - Earthling types (Human/Cow/Chicken) can only be selected ONCE per turn
    - Death Rays can be selected multiple times to build defense
    - Bust if Tanks > Death Rays at end of turn (score = 0)

Face Mapping:
    - Face 1: Human (Earthling)
    - Face 2: Cow (Earthling)
    - Face 3: Chicken (Earthling)
    - Faces 4 & 5: Death Ray (Defense)
    - Face 6: Tank (Auto-locked threat)

Scoring:
    - 1 point per Earthling (Human/Cow/Chicken)
    - +3 bonus if all three Earthling types collected
    - 0 points if Tanks > Death Rays (bust)
"""

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Sequence
import random

from src.engine.base import DiceRoll, DiceType
from src.engine.validators import validate_dice_values, validate_held_indices


class FaceType(Enum):
    """Face types for Alien Invasion dice."""
    HUMAN = "human"          # Face 1
    COW = "cow"              # Face 2
    CHICKEN = "chicken"      # Face 3
    DEATH_RAY = "death_ray"  # Faces 4 & 5
    TANK = "tank"            # Face 6


@dataclass(frozen=True)
class AlienInvasionTurnState:
    """
    Complete state of a player's turn in Alien Invasion mode.

    Attributes:
        active_dice: Current dice values in play
        held_indices: Indices of dice that have been held (includes auto-locked tanks)
        tanks_count: Total number of tanks collected this turn
        death_rays_count: Total number of death rays collected this turn
        earthlings_count: Total number of earthlings collected this turn
        selected_types: List of Earthling types already selected this turn
        turn_score: Potential points accumulated this turn (not yet banked)
        roll_count: Number of rolls taken this turn
    """
    active_dice: tuple[int, ...]
    held_indices: frozenset[int] = frozenset()
    tanks_count: int = 0
    death_rays_count: int = 0
    earthlings_count: int = 0
    selected_types: tuple[str, ...] = tuple()  # Earthling type names already selected
    turn_score: int = 0
    roll_count: int = 0

    @property
    def available_dice_count(self) -> int:
        """Number of dice available to roll (not held)."""
        return len(self.active_dice) - len(self.held_indices)


@dataclass(frozen=True)
class AlienInvasionScoringResult:
    """
    Scoring result for Alien Invasion mode.

    Attributes:
        earthlings_points: Base points from collected Earthlings (1 pt each)
        diversity_bonus: Bonus points for collecting all 3 Earthling types (+3)
        total_points: Final score (0 if bust)
        is_bust: True if Tanks > Death Rays
        is_safe_to_bank: True if Death Rays >= Tanks (safe to bank without bust)
    """
    earthlings_points: int
    diversity_bonus: int
    total_points: int
    is_bust: bool
    is_safe_to_bank: bool


class AlienInvasionEngine:
    """
    Stateless engine for the Alien Invasion (Martian Dice) game mode.

    All methods are class methods operating on immutable data.
    State is passed in and returned, never stored.
    """

    # Constants
    NUM_DICE = 13
    DICE_TYPE = DiceType.D6
    DIVERSITY_BONUS = 3

    # Face type mapping
    FACE_MAPPING = {
        1: FaceType.HUMAN,
        2: FaceType.COW,
        3: FaceType.CHICKEN,
        4: FaceType.DEATH_RAY,
        5: FaceType.DEATH_RAY,
        6: FaceType.TANK,
    }

    # Earthling face types (can only be selected once per turn)
    EARTHLING_TYPES = {FaceType.HUMAN, FaceType.COW, FaceType.CHICKEN}

    @classmethod
    def roll_dice(cls, count: int = NUM_DICE) -> DiceRoll:
        """
        Roll the specified number of D6 dice.

        Args:
            count: Number of dice to roll (default: 13)

        Returns:
            DiceRoll with random values
        """
        values = tuple(random.randint(1, 6) for _ in range(count))
        return DiceRoll(values=values, dice_type=cls.DICE_TYPE)

    @classmethod
    def classify_dice(cls, dice: Sequence[int] | DiceRoll) -> dict[FaceType, list[int]]:
        """
        Classify dice by their face type.

        Args:
            dice: Dice values to classify

        Returns:
            Dictionary mapping FaceType to list of indices with that type
        """
        if isinstance(dice, DiceRoll):
            values = dice.values
        else:
            values = tuple(dice)

        classification: dict[FaceType, list[int]] = {
            FaceType.HUMAN: [],
            FaceType.COW: [],
            FaceType.CHICKEN: [],
            FaceType.DEATH_RAY: [],
            FaceType.TANK: [],
        }

        for i, value in enumerate(values):
            face_type = cls.FACE_MAPPING[value]
            classification[face_type].append(i)

        return classification

    @classmethod
    def get_available_selections(
        cls,
        state: AlienInvasionTurnState
    ) -> dict[FaceType, list[int]]:
        """
        Get available dice that can be selected for the current roll.

        Rules:
        - Tanks are auto-locked and cannot be selected
        - Earthling types already selected this turn cannot be selected again
        - Death Rays can always be selected (can be picked multiple times)
        - Only unheld dice are available

        Args:
            state: Current turn state

        Returns:
            Dictionary mapping FaceType to available indices
        """
        # Classify all dice
        all_classified = cls.classify_dice(state.active_dice)

        # Filter to unheld dice only
        available: dict[FaceType, list[int]] = {}

        for face_type, indices in all_classified.items():
            # Skip tanks (auto-locked, not selectable)
            if face_type == FaceType.TANK:
                continue

            # Filter to unheld indices
            unheld_indices = [i for i in indices if i not in state.held_indices]

            # Check if this Earthling type was already selected
            if face_type in cls.EARTHLING_TYPES:
                if face_type.value in state.selected_types:
                    # Already selected this type, skip
                    continue

            # Add available indices
            if unheld_indices:
                available[face_type] = unheld_indices

        return available

    @classmethod
    def process_roll(
        cls,
        state: AlienInvasionTurnState,
        roll: DiceRoll | None = None
    ) -> AlienInvasionTurnState:
        """
        Process a dice roll and return updated state with tanks auto-locked.

        Args:
            state: Current turn state
            roll: Roll to process (or None to generate new roll)

        Returns:
            New turn state with tanks auto-locked
        """
        # Determine how many dice to roll
        if state.roll_count == 0:
            # First roll: all 13 dice
            dice_count = cls.NUM_DICE
        else:
            # Subsequent rolls: only unheld dice
            dice_count = state.available_dice_count

        # Generate roll if not provided
        if roll is None:
            roll = cls.roll_dice(dice_count)

        # Classify dice to find tanks
        classification = cls.classify_dice(roll.values)
        tank_indices = classification[FaceType.TANK]

        # Auto-lock tanks
        new_held = frozenset(tank_indices)
        new_tanks_count = state.tanks_count + len(tank_indices)

        new_state = AlienInvasionTurnState(
            active_dice=roll.values,
            held_indices=new_held,
            tanks_count=new_tanks_count,
            death_rays_count=state.death_rays_count,
            earthlings_count=state.earthlings_count,
            selected_types=state.selected_types,
            turn_score=state.turn_score,
            roll_count=state.roll_count + 1,
        )

        return new_state

    @classmethod
    def process_selection(
        cls,
        state: AlienInvasionTurnState,
        face_type: FaceType,
        indices: Sequence[int]
    ) -> AlienInvasionTurnState:
        """
        Process a group selection and return updated state.

        Args:
            state: Current turn state
            face_type: Type of face being selected
            indices: Indices of dice to hold

        Returns:
            New turn state with selected dice held

        Raises:
            ValueError: If selection is invalid
        """
        # Validate face type is not a tank
        if face_type == FaceType.TANK:
            raise ValueError("Cannot manually select tanks (auto-locked)")

        # Validate Earthling type not already selected
        if face_type in cls.EARTHLING_TYPES:
            if face_type.value in state.selected_types:
                raise ValueError(f"{face_type.value} already selected this turn")

        # Validate indices are unheld
        indices_set = frozenset(indices)
        if indices_set & state.held_indices:
            raise ValueError("Cannot select already held dice")

        # Validate all indices have the correct face type
        for i in indices:
            if i >= len(state.active_dice):
                raise ValueError(f"Index {i} out of range")
            face_value = state.active_dice[i]
            if cls.FACE_MAPPING[face_value] != face_type:
                raise ValueError(f"Index {i} is not a {face_type.value}")

        # Update counts
        count = len(indices)
        new_death_rays = state.death_rays_count
        new_earthlings = state.earthlings_count
        new_selected_types = state.selected_types

        if face_type == FaceType.DEATH_RAY:
            new_death_rays += count
        elif face_type in cls.EARTHLING_TYPES:
            new_earthlings += count
            new_selected_types = tuple(list(state.selected_types) + [face_type.value] * count)

        # Calculate potential score
        new_score = cls._calculate_potential_score(
            new_earthlings,
            new_selected_types
        )

        # Hold the selected dice
        new_held = state.held_indices | indices_set

        new_state = AlienInvasionTurnState(
            active_dice=state.active_dice,
            held_indices=new_held,
            tanks_count=state.tanks_count,
            death_rays_count=new_death_rays,
            earthlings_count=new_earthlings,
            selected_types=new_selected_types,
            turn_score=new_score,
            roll_count=state.roll_count,
        )

        return new_state

    @classmethod
    def _calculate_potential_score(
        cls,
        earthlings_count: int,
        selected_types: tuple[str, ...]
    ) -> int:
        """
        Calculate potential score (before bust check).

        Args:
            earthlings_count: Number of Earthlings collected
            selected_types: List of Earthling type names selected

        Returns:
            Potential score (1 pt per Earthling + diversity bonus)
        """
        base_points = earthlings_count

        # Check for diversity bonus (all 3 Earthling types)
        has_all_types = len(set(selected_types)) == 3
        diversity_bonus = cls.DIVERSITY_BONUS if has_all_types else 0

        return base_points + diversity_bonus

    @classmethod
    def calculate_final_score(
        cls,
        state: AlienInvasionTurnState
    ) -> AlienInvasionScoringResult:
        """
        Calculate final score with bust check.

        Bust condition: Tanks > Death Rays → score = 0
        Safe to bank: Death Rays >= Tanks

        Args:
            state: Current turn state

        Returns:
            AlienInvasionScoringResult with bust check applied
        """
        # Calculate base score
        earthlings_points = state.earthlings_count

        # Check for diversity bonus
        has_all_types = len(set(state.selected_types)) == 3
        diversity_bonus = cls.DIVERSITY_BONUS if has_all_types else 0

        # Check for bust
        is_bust = state.tanks_count > state.death_rays_count
        is_safe = state.death_rays_count >= state.tanks_count

        # Apply bust: score = 0 if tanks > rays
        total_points = 0 if is_bust else (earthlings_points + diversity_bonus)

        return AlienInvasionScoringResult(
            earthlings_points=earthlings_points,
            diversity_bonus=diversity_bonus,
            total_points=total_points,
            is_bust=is_bust,
            is_safe_to_bank=is_safe,
        )

    @classmethod
    def get_tug_of_war_ratio(cls, state: AlienInvasionTurnState) -> float:
        """
        Calculate Tug of War meter position (0.0 = all tanks, 1.0 = all rays).

        The ratio represents the balance between Death Rays and Tanks:
        - 0.0: No Death Rays, only Tanks (maximum danger)
        - 0.5: Equal Death Rays and Tanks (neutral)
        - 1.0: Many Death Rays, few/no Tanks (maximum safety)

        Formula: rays / (rays + tanks + 1)
        The +1 prevents division by zero and keeps ratio < 1.0

        Args:
            state: Current turn state

        Returns:
            Float between 0.0 and 1.0
        """
        total = state.death_rays_count + state.tanks_count
        if total == 0:
            return 0.5  # Neutral if no rays or tanks yet

        # Ratio: 0.0 (all tanks) → 0.5 (equal) → 1.0 (all rays)
        ratio = state.death_rays_count / (total + 1)
        return ratio

    @classmethod
    def is_stuck(cls, state: AlienInvasionTurnState) -> bool:
        """
        Check if player is stuck (no available selections and no earthlings).

        A stuck state occurs when:
        - All remaining dice become tanks (auto-locked)
        - No selections available
        - No earthlings collected yet

        This forces a bust.

        Args:
            state: Current turn state

        Returns:
            True if stuck (forced bust)
        """
        # If we haven't rolled yet, not stuck
        if state.roll_count == 0:
            return False

        # Get available selections
        available = cls.get_available_selections(state)

        # Stuck if no selections available and no earthlings collected
        return len(available) == 0 and state.earthlings_count == 0

    @classmethod
    def create_initial_turn_state(cls) -> AlienInvasionTurnState:
        """
        Create the initial state for a new turn.

        Returns:
            Fresh AlienInvasionTurnState with 13 unrolled dice
        """
        return AlienInvasionTurnState(
            active_dice=tuple(),
            held_indices=frozenset(),
            tanks_count=0,
            death_rays_count=0,
            earthlings_count=0,
            selected_types=tuple(),
            turn_score=0,
            roll_count=0,
        )
