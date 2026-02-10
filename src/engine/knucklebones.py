"""
Devil's Dozen - Knucklebones Game Engine

A 2-player strategic dice placement game with grid-based mechanics.

Game Rules:
- 2 players, each with a 3x3 grid
- Roll single D6, must place in any non-full column
- "The Crunch": Placing a die destroys matching opponent dice in the same column
- Column scoring: Singles (face value), Pairs (sum×2), Triples (sum×3)
- Game ends when any grid is full; highest score wins
"""

import random
from collections import Counter
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class GridState:
    """
    Immutable representation of a player's 3×3 grid.

    Attributes:
        columns: Tuple of 3 columns, each containing 0-3 dice values (bottom-to-top)
                 Example: ((4, 6), (1,), (4, 4, 2)) represents:
                 Column 0: [4, 6] (bottom to top)
                 Column 1: [1]
                 Column 2: [4, 4, 2]
    """
    columns: tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]

    def __post_init__(self) -> None:
        """Validate grid structure."""
        if len(self.columns) != 3:
            raise ValueError("Grid must have exactly 3 columns")

        for i, col in enumerate(self.columns):
            if len(col) > 3:
                raise ValueError(f"Column {i} has {len(col)} dice (max 3)")
            for die_value in col:
                if not (1 <= die_value <= 6):
                    raise ValueError(f"Invalid die value {die_value} in column {i}")

    @classmethod
    def empty(cls) -> "GridState":
        """Create an empty grid."""
        return cls(columns=((), (), ()))

    @classmethod
    def from_dict(cls, data: dict) -> "GridState":
        """Create GridState from database dictionary format."""
        cols = data.get("columns", [[], [], []])
        return cls(columns=(tuple(cols[0]), tuple(cols[1]), tuple(cols[2])))

    def to_dict(self) -> dict:
        """Convert to database dictionary format."""
        return {"columns": [list(col) for col in self.columns]}

    def is_full(self) -> bool:
        """Check if all columns are full (3 dice each)."""
        return all(len(col) == 3 for col in self.columns)

    def is_column_full(self, column_index: int) -> bool:
        """Check if a specific column is full."""
        if not (0 <= column_index < 3):
            raise ValueError(f"Column index must be 0-2, got {column_index}")
        return len(self.columns[column_index]) == 3


@dataclass(frozen=True)
class PlacementResult:
    """
    Result of placing a die in a grid.

    Attributes:
        player_grid: Updated player grid after placement
        opponent_grid: Updated opponent grid after destruction
        player_score_delta: Change in player's score
        opponent_score_delta: Change in opponent's score (negative due to destruction)
        destroyed_count: Number of opponent dice destroyed
        column_index: Column where die was placed
    """
    player_grid: GridState
    opponent_grid: GridState
    player_score_delta: int
    opponent_score_delta: int
    destroyed_count: int
    column_index: int


class KnuckleboneEngine:
    """Stateless engine for Knucklebones game logic."""

    GRID_COLUMNS: ClassVar[int] = 3
    GRID_ROWS: ClassVar[int] = 3
    DIE_FACES: ClassVar[int] = 6

    @classmethod
    def roll_die(cls) -> int:
        """Roll a single D6."""
        return random.randint(1, cls.DIE_FACES)

    @classmethod
    def calculate_column_score(cls, column: tuple[int, ...]) -> int:
        """
        Calculate score for a single column.

        Scoring rules:
        - Single die: face value (e.g., [4] = 4 pts)
        - Pair (2 of kind): sum × 2 (e.g., [4, 4] = 16 pts)
        - Triple (3 of kind): sum × 3 (e.g., [4, 4, 4] = 36 pts)
        - Mixed values: sum with no multiplier (e.g., [4, 6] = 10 pts)

        Args:
            column: Tuple of 0-3 dice values

        Returns:
            Total points for the column
        """
        if not column:
            return 0

        # Count occurrences of each face value
        counts = Counter(column)
        total_score = 0

        for face_value, count in counts.items():
            if count == 3:
                # Triple: sum × 3
                total_score += (face_value * 3) * 3
            elif count == 2:
                # Pair: sum × 2
                total_score += (face_value * 2) * 2
            else:
                # Single: face value
                total_score += face_value

        return total_score

    @classmethod
    def calculate_grid_score(cls, grid: GridState) -> int:
        """
        Calculate total score for a grid (sum of all column scores).

        Args:
            grid: The grid to score

        Returns:
            Total grid score
        """
        return sum(cls.calculate_column_score(col) for col in grid.columns)

    @classmethod
    def place_die(
        cls,
        die_value: int,
        column_index: int,
        player_grid: GridState,
        opponent_grid: GridState
    ) -> PlacementResult:
        """
        Place a die in a column and apply "The Crunch" mechanic.

        Steps:
        1. Add die to player's column
        2. Destroy matching opponent dice in the same column
        3. Calculate score changes

        Args:
            die_value: Value of the die to place (1-6)
            column_index: Column to place in (0-2)
            player_grid: Current player's grid
            opponent_grid: Current opponent's grid

        Returns:
            PlacementResult with updated grids and score changes

        Raises:
            ValueError: If column is full or die_value is invalid
        """
        # Validate inputs
        if not (1 <= die_value <= cls.DIE_FACES):
            raise ValueError(f"Die value must be 1-{cls.DIE_FACES}, got {die_value}")
        if not (0 <= column_index < cls.GRID_COLUMNS):
            raise ValueError(f"Column index must be 0-{cls.GRID_COLUMNS-1}, got {column_index}")
        if player_grid.is_column_full(column_index):
            raise ValueError(f"Column {column_index} is full")

        # Calculate score before changes
        player_score_before = cls.calculate_column_score(player_grid.columns[column_index])
        opponent_score_before = cls.calculate_column_score(opponent_grid.columns[column_index])

        # Add die to player's column
        new_player_column = player_grid.columns[column_index] + (die_value,)
        new_player_columns = list(player_grid.columns)
        new_player_columns[column_index] = new_player_column
        new_player_grid = GridState(columns=tuple(new_player_columns))

        # Apply "The Crunch": Destroy matching opponent dice
        opponent_column = opponent_grid.columns[column_index]
        destroyed_count = opponent_column.count(die_value)
        new_opponent_column = tuple(v for v in opponent_column if v != die_value)
        new_opponent_columns = list(opponent_grid.columns)
        new_opponent_columns[column_index] = new_opponent_column
        new_opponent_grid = GridState(columns=tuple(new_opponent_columns))

        # Calculate score after changes
        player_score_after = cls.calculate_column_score(new_player_column)
        opponent_score_after = cls.calculate_column_score(new_opponent_column)

        return PlacementResult(
            player_grid=new_player_grid,
            opponent_grid=new_opponent_grid,
            player_score_delta=player_score_after - player_score_before,
            opponent_score_delta=opponent_score_after - opponent_score_before,
            destroyed_count=destroyed_count,
            column_index=column_index
        )

    @classmethod
    def is_game_over(cls, player1_grid: GridState, player2_grid: GridState) -> bool:
        """
        Check if the game is over (any grid is full).

        Args:
            player1_grid: Player 1's grid
            player2_grid: Player 2's grid

        Returns:
            True if either grid is completely full
        """
        return player1_grid.is_full() or player2_grid.is_full()

    @classmethod
    def get_winner(
        cls,
        player1_grid: GridState,
        player2_grid: GridState
    ) -> int | None:
        """
        Determine the winner based on final scores.

        Args:
            player1_grid: Player 1's grid
            player2_grid: Player 2's grid

        Returns:
            1 if player 1 wins, 2 if player 2 wins, None for tie
        """
        p1_score = cls.calculate_grid_score(player1_grid)
        p2_score = cls.calculate_grid_score(player2_grid)

        if p1_score > p2_score:
            return 1
        elif p2_score > p1_score:
            return 2
        else:
            return None  # Tie

    @classmethod
    def get_available_columns(cls, grid: GridState) -> list[int]:
        """
        Get list of column indices that are not full.

        Args:
            grid: The grid to check

        Returns:
            List of available column indices (0-2)
        """
        return [i for i in range(cls.GRID_COLUMNS) if not grid.is_column_full(i)]
