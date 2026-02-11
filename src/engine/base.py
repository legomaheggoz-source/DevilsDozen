"""
Devil's Dozen - Game Engine Base Classes

This module defines the foundational data structures and enums used throughout
the game engine. All classes are immutable (frozen dataclasses) to ensure
thread-safety and predictable behavior.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Sequence


class DiceType(Enum):
    """Type of dice used in the game."""
    D6 = 6
    D20 = 20


class GameMode(Enum):
    """Available game modes."""
    PEASANTS_GAMBLE = "peasants_gamble"
    ALCHEMISTS_ASCENT = "alchemists_ascent"
    KNUCKLEBONES = "knucklebones"
    ALIEN_INVASION = "alien_invasion"
    PIG = "pig"


class Tier(Enum):
    """Tiers for Alchemist's Ascent mode."""
    RED = 1    # 0-100 points, 8 dice
    GREEN = 2  # 101-200 points, 3 dice
    BLUE = 3   # 201-250 points, 1 die


class ScoringCategory(Enum):
    """Categories of scoring combinations."""
    SINGLE_ONE = auto()
    SINGLE_FIVE = auto()
    THREE_OF_A_KIND = auto()
    FOUR_OF_A_KIND = auto()
    FIVE_OF_A_KIND = auto()
    SIX_OF_A_KIND = auto()
    LOW_STRAIGHT = auto()      # 1-2-3-4-5
    HIGH_STRAIGHT = auto()     # 2-3-4-5-6
    FULL_STRAIGHT = auto()     # 1-2-3-4-5-6
    PAIR = auto()              # D20 mode
    SEQUENCE = auto()          # D20 mode
    TIER_BONUS = auto()        # D20 mode multipliers


@dataclass(frozen=True)
class ScoringBreakdown:
    """
    A single scoring component within a roll.

    Attributes:
        category: The type of scoring combination
        dice_values: The dice that contributed to this score
        points: Points awarded for this combination
        description: Human-readable description
    """
    category: ScoringCategory
    dice_values: tuple[int, ...]
    points: int
    description: str


@dataclass(frozen=True)
class ScoringResult:
    """
    Complete scoring result for a dice roll.

    Attributes:
        points: Total points scored
        breakdown: List of individual scoring components
        scoring_dice_indices: Indices of dice that scored
        is_bust: Whether no dice scored (automatic bust)
    """
    points: int
    breakdown: tuple[ScoringBreakdown, ...]
    scoring_dice_indices: frozenset[int]
    is_bust: bool = False

    @property
    def has_scoring_dice(self) -> bool:
        """Returns True if at least one die scored."""
        return len(self.scoring_dice_indices) > 0

    def __str__(self) -> str:
        if self.is_bust:
            return "BUST! No scoring dice."
        lines = [f"Total: {self.points} points"]
        for item in self.breakdown:
            lines.append(f"  - {item.description}: {item.points}")
        return "\n".join(lines)


@dataclass(frozen=True)
class DiceRoll:
    """
    Immutable representation of a dice roll.

    Attributes:
        values: Tuple of dice face values
        dice_type: Type of dice (D6 or D20)
    """
    values: tuple[int, ...]
    dice_type: DiceType = DiceType.D6

    def __post_init__(self) -> None:
        """Validate dice values are within valid range."""
        max_value = self.dice_type.value
        for value in self.values:
            if not (1 <= value <= max_value):
                raise ValueError(
                    f"Invalid die value {value} for {self.dice_type.name}. "
                    f"Must be between 1 and {max_value}."
                )

    def __len__(self) -> int:
        return len(self.values)

    def __getitem__(self, index: int) -> int:
        return self.values[index]

    @classmethod
    def from_sequence(
        cls,
        values: Sequence[int],
        dice_type: DiceType = DiceType.D6
    ) -> "DiceRoll":
        """Create a DiceRoll from any sequence type."""
        return cls(values=tuple(values), dice_type=dice_type)


@dataclass(frozen=True)
class TurnState:
    """
    Complete state of a player's turn.

    Attributes:
        active_dice: Current dice values in play
        held_indices: Indices of dice that have been held
        turn_score: Points accumulated this turn (not yet banked)
        roll_count: Number of rolls taken this turn
        is_hot_dice: Whether all dice have scored (can roll all again)
        tier: Current tier (Alchemist's Ascent only)
        previous_dice: Previous roll for reroll comparison (Tier 2)
    """
    active_dice: tuple[int, ...]
    held_indices: frozenset[int] = field(default_factory=frozenset)
    turn_score: int = 0
    roll_count: int = 0
    is_hot_dice: bool = False
    tier: Tier = Tier.RED
    previous_dice: tuple[int, ...] = field(default_factory=tuple)

    @property
    def available_dice_count(self) -> int:
        """Number of dice that can still be rolled."""
        return len(self.active_dice) - len(self.held_indices)

    @property
    def held_dice_values(self) -> tuple[int, ...]:
        """Values of the held dice."""
        return tuple(self.active_dice[i] for i in sorted(self.held_indices))

    @property
    def unheld_dice_values(self) -> tuple[int, ...]:
        """Values of dice not yet held."""
        return tuple(
            v for i, v in enumerate(self.active_dice)
            if i not in self.held_indices
        )


@dataclass(frozen=True)
class GameConfig:
    """
    Configuration for a game session.

    Attributes:
        mode: Game mode (Peasant's Gamble or Alchemist's Ascent)
        target_score: Score needed to win
        num_players: Number of players (2-4)
    """
    mode: GameMode
    target_score: int
    num_players: int = 2

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.mode == GameMode.KNUCKLEBONES:
            # Knucklebones is strictly 2-player
            if self.num_players != 2:
                raise ValueError("Knucklebones requires exactly 2 players.")
        elif self.mode == GameMode.PIG:
            # Pig supports 2-10 players
            if not 2 <= self.num_players <= 10:
                raise ValueError("Number of players for Pig must be between 2 and 10.")
        else:
            # Other modes support 2-4 players
            if not 2 <= self.num_players <= 4:
                raise ValueError("Number of players must be between 2 and 4.")

        if self.mode == GameMode.PEASANTS_GAMBLE:
            valid_targets = {3000, 5000, 10000}
            if self.target_score not in valid_targets:
                raise ValueError(
                    f"Target score for Peasant's Gamble must be one of {valid_targets}."
                )
        elif self.mode == GameMode.ALCHEMISTS_ASCENT:
            if self.target_score != 250:
                raise ValueError("Target score for Alchemist's Ascent must be 250.")
        elif self.mode == GameMode.KNUCKLEBONES:
            # Target score is not used in Knucklebones (game ends on full grid)
            pass
        elif self.mode == GameMode.ALIEN_INVASION:
            valid_targets = {25, 50, 75}
            if self.target_score not in valid_targets:
                raise ValueError(
                    f"Target score for Alien Invasion must be one of {valid_targets}."
                )
        elif self.mode == GameMode.PIG:
            valid_targets = {50, 100, 250}
            if self.target_score not in valid_targets:
                raise ValueError(
                    f"Target score for Pig must be one of {valid_targets}."
                )
