"""
Tests for Knucklebones game engine.
"""

import pytest

from src.engine.knucklebones import GridState, KnuckleboneEngine, PlacementResult


class TestGridState:
    """Tests for GridState dataclass."""

    def test_empty_grid(self):
        """Test creating an empty grid."""
        grid = GridState.empty()
        assert grid.columns == ((), (), ())
        assert not grid.is_full()

    def test_grid_validation_columns_count(self):
        """Test grid must have exactly 3 columns."""
        with pytest.raises(ValueError, match="must have exactly 3 columns"):
            GridState(columns=((), ()))

    def test_grid_validation_column_size(self):
        """Test column cannot have more than 3 dice."""
        with pytest.raises(ValueError, match="has 4 dice"):
            GridState(columns=((1, 2, 3, 4), (), ()))

    def test_grid_validation_die_values(self):
        """Test dice must be 1-6."""
        with pytest.raises(ValueError, match="Invalid die value 7"):
            GridState(columns=((1, 7), (), ()))

        with pytest.raises(ValueError, match="Invalid die value 0"):
            GridState(columns=((0,), (), ()))

    def test_is_full_empty_grid(self):
        """Test empty grid is not full."""
        grid = GridState.empty()
        assert not grid.is_full()

    def test_is_full_partial_grid(self):
        """Test partially filled grid is not full."""
        grid = GridState(columns=((1, 2, 3), (4, 5), (6,)))
        assert not grid.is_full()

    def test_is_full_complete_grid(self):
        """Test completely filled grid is full."""
        grid = GridState(columns=((1, 2, 3), (4, 5, 6), (1, 2, 3)))
        assert grid.is_full()

    def test_is_column_full(self):
        """Test checking if specific columns are full."""
        grid = GridState(columns=((1, 2, 3), (4,), ()))
        assert grid.is_column_full(0)
        assert not grid.is_column_full(1)
        assert not grid.is_column_full(2)

    def test_is_column_full_invalid_index(self):
        """Test invalid column index raises error."""
        grid = GridState.empty()
        with pytest.raises(ValueError, match="Column index must be 0-2"):
            grid.is_column_full(3)

    def test_from_dict(self):
        """Test creating grid from dictionary."""
        data = {"columns": [[1, 2], [3], []]}
        grid = GridState.from_dict(data)
        assert grid.columns == ((1, 2), (3,), ())

    def test_from_dict_empty(self):
        """Test creating empty grid from empty dict."""
        grid = GridState.from_dict({})
        assert grid.columns == ((), (), ())

    def test_to_dict(self):
        """Test converting grid to dictionary."""
        grid = GridState(columns=((1, 2), (3,), ()))
        data = grid.to_dict()
        assert data == {"columns": [[1, 2], [3], []]}


class TestKnuckleboneEngineRollDie:
    """Tests for die rolling."""

    def test_roll_die_range(self):
        """Test rolled die is in valid range."""
        for _ in range(100):
            die = KnuckleboneEngine.roll_die()
            assert 1 <= die <= 6

    def test_roll_die_distribution(self):
        """Test die roll produces all values over many rolls."""
        rolls = {KnuckleboneEngine.roll_die() for _ in range(1000)}
        assert rolls == {1, 2, 3, 4, 5, 6}


class TestKnuckleboneEngineColumnScoring:
    """Tests for column scoring logic."""

    def test_empty_column(self):
        """Test empty column scores 0."""
        assert KnuckleboneEngine.calculate_column_score(()) == 0

    def test_single_die(self):
        """Test single die scores face value."""
        assert KnuckleboneEngine.calculate_column_score((4,)) == 4
        assert KnuckleboneEngine.calculate_column_score((1,)) == 1
        assert KnuckleboneEngine.calculate_column_score((6,)) == 6

    def test_pair_same_value(self):
        """Test pair scores sum × 2."""
        # Two 4s: (4 + 4) × 2 = 16
        assert KnuckleboneEngine.calculate_column_score((4, 4)) == 16
        # Two 1s: (1 + 1) × 2 = 4
        assert KnuckleboneEngine.calculate_column_score((1, 1)) == 4
        # Two 6s: (6 + 6) × 2 = 24
        assert KnuckleboneEngine.calculate_column_score((6, 6)) == 24

    def test_triple_same_value(self):
        """Test triple scores sum × 3."""
        # Three 4s: (4 + 4 + 4) × 3 = 36
        assert KnuckleboneEngine.calculate_column_score((4, 4, 4)) == 36
        # Three 1s: (1 + 1 + 1) × 3 = 9
        assert KnuckleboneEngine.calculate_column_score((1, 1, 1)) == 9
        # Three 6s: (6 + 6 + 6) × 3 = 54
        assert KnuckleboneEngine.calculate_column_score((6, 6, 6)) == 54

    def test_mixed_two_dice(self):
        """Test two different dice score sum with no multiplier."""
        # [4, 6] = 4 + 6 = 10
        assert KnuckleboneEngine.calculate_column_score((4, 6)) == 10
        # [1, 5] = 1 + 5 = 6
        assert KnuckleboneEngine.calculate_column_score((1, 5)) == 6

    def test_mixed_three_dice(self):
        """Test three different dice score sum with no multiplier."""
        # [1, 2, 3] = 1 + 2 + 3 = 6
        assert KnuckleboneEngine.calculate_column_score((1, 2, 3)) == 6
        # [4, 5, 6] = 4 + 5 + 6 = 15
        assert KnuckleboneEngine.calculate_column_score((4, 5, 6)) == 15

    def test_pair_plus_single(self):
        """Test pair with different third die."""
        # [4, 4, 6] = (4 + 4) × 2 + 6 = 16 + 6 = 22
        assert KnuckleboneEngine.calculate_column_score((4, 4, 6)) == 22
        # [1, 1, 5] = (1 + 1) × 2 + 5 = 4 + 5 = 9
        assert KnuckleboneEngine.calculate_column_score((1, 1, 5)) == 9


class TestKnuckleboneEngineGridScoring:
    """Tests for total grid scoring."""

    def test_empty_grid(self):
        """Test empty grid scores 0."""
        grid = GridState.empty()
        assert KnuckleboneEngine.calculate_grid_score(grid) == 0

    def test_partial_grid(self):
        """Test grid with some dice."""
        # Column 0: [4] = 4
        # Column 1: [1, 1] = 4
        # Column 2: [6] = 6
        # Total: 4 + 4 + 6 = 14
        grid = GridState(columns=((4,), (1, 1), (6,)))
        assert KnuckleboneEngine.calculate_grid_score(grid) == 14

    def test_full_grid(self):
        """Test completely filled grid."""
        # Column 0: [4, 4, 4] = 36
        # Column 1: [1, 2, 3] = 6
        # Column 2: [6, 6] = 24
        # Total: 36 + 6 + 24 = 66
        grid = GridState(columns=((4, 4, 4), (1, 2, 3), (6, 6)))
        assert KnuckleboneEngine.calculate_grid_score(grid) == 66


class TestKnuckleboneEnginePlacement:
    """Tests for die placement mechanics."""

    def test_place_die_in_empty_column(self):
        """Test placing a die in an empty column."""
        player_grid = GridState.empty()
        opponent_grid = GridState.empty()

        result = KnuckleboneEngine.place_die(4, 0, player_grid, opponent_grid)

        assert result.player_grid.columns[0] == (4,)
        assert result.opponent_grid.columns[0] == ()
        assert result.player_score_delta == 4
        assert result.opponent_score_delta == 0
        assert result.destroyed_count == 0

    def test_place_die_stack_same_column(self):
        """Test placing multiple dice in same column."""
        player_grid = GridState(columns=((4,), (), ()))
        opponent_grid = GridState.empty()

        result = KnuckleboneEngine.place_die(4, 0, player_grid, opponent_grid)

        # Column 0: [4, 4] = 16 (was 4, delta = 12)
        assert result.player_grid.columns[0] == (4, 4)
        assert result.player_score_delta == 12

    def test_place_die_creates_triple(self):
        """Test placing a die that creates a triple."""
        player_grid = GridState(columns=((4, 4), (), ()))
        opponent_grid = GridState.empty()

        result = KnuckleboneEngine.place_die(4, 0, player_grid, opponent_grid)

        # Column 0: [4, 4, 4] = 36 (was 16, delta = 20)
        assert result.player_grid.columns[0] == (4, 4, 4)
        assert result.player_score_delta == 20

    def test_place_die_destroys_single_opponent_die(self):
        """Test 'The Crunch' destroys matching opponent die."""
        player_grid = GridState.empty()
        opponent_grid = GridState(columns=((4,), (), ()))

        result = KnuckleboneEngine.place_die(4, 0, player_grid, opponent_grid)

        # Player places 4 in column 0
        assert result.player_grid.columns[0] == (4,)
        assert result.player_score_delta == 4

        # Opponent's 4 is destroyed
        assert result.opponent_grid.columns[0] == ()
        assert result.opponent_score_delta == -4
        assert result.destroyed_count == 1

    def test_place_die_destroys_multiple_opponent_dice(self):
        """Test destroying multiple matching opponent dice."""
        player_grid = GridState.empty()
        opponent_grid = GridState(columns=((4, 4, 2), (), ()))

        result = KnuckleboneEngine.place_die(4, 0, player_grid, opponent_grid)

        # Opponent had [4, 4, 2] = 18, now has [2] = 2
        assert result.opponent_grid.columns[0] == (2,)
        assert result.opponent_score_delta == -16
        assert result.destroyed_count == 2

    def test_place_die_no_destruction_different_value(self):
        """Test placing die doesn't destroy different values."""
        player_grid = GridState.empty()
        opponent_grid = GridState(columns=((1, 2, 3), (), ()))

        result = KnuckleboneEngine.place_die(6, 0, player_grid, opponent_grid)

        # Opponent's dice unchanged
        assert result.opponent_grid.columns[0] == (1, 2, 3)
        assert result.opponent_score_delta == 0
        assert result.destroyed_count == 0

    def test_place_die_different_columns_no_effect(self):
        """Test placement only affects specified column."""
        player_grid = GridState(columns=((1,), (2,), ()))
        opponent_grid = GridState(columns=((4,), (4,), (4,)))

        result = KnuckleboneEngine.place_die(4, 2, player_grid, opponent_grid)

        # Only column 2 affected
        assert result.player_grid.columns[0] == (1,)
        assert result.player_grid.columns[1] == (2,)
        assert result.player_grid.columns[2] == (4,)

        assert result.opponent_grid.columns[0] == (4,)
        assert result.opponent_grid.columns[1] == (4,)
        assert result.opponent_grid.columns[2] == ()  # Destroyed

    def test_place_die_full_column_raises_error(self):
        """Test cannot place in full column."""
        player_grid = GridState(columns=((1, 2, 3), (), ()))
        opponent_grid = GridState.empty()

        with pytest.raises(ValueError, match="Column 0 is full"):
            KnuckleboneEngine.place_die(4, 0, player_grid, opponent_grid)

    def test_place_die_invalid_value_raises_error(self):
        """Test invalid die value raises error."""
        player_grid = GridState.empty()
        opponent_grid = GridState.empty()

        with pytest.raises(ValueError, match="Die value must be 1-6"):
            KnuckleboneEngine.place_die(0, 0, player_grid, opponent_grid)

        with pytest.raises(ValueError, match="Die value must be 1-6"):
            KnuckleboneEngine.place_die(7, 0, player_grid, opponent_grid)

    def test_place_die_invalid_column_raises_error(self):
        """Test invalid column index raises error."""
        player_grid = GridState.empty()
        opponent_grid = GridState.empty()

        with pytest.raises(ValueError, match="Column index must be 0-2"):
            KnuckleboneEngine.place_die(4, 3, player_grid, opponent_grid)

        with pytest.raises(ValueError, match="Column index must be 0-2"):
            KnuckleboneEngine.place_die(4, -1, player_grid, opponent_grid)


class TestKnuckleboneEngineGameOver:
    """Tests for game over detection."""

    def test_game_not_over_empty_grids(self):
        """Test game not over with empty grids."""
        p1 = GridState.empty()
        p2 = GridState.empty()
        assert not KnuckleboneEngine.is_game_over(p1, p2)

    def test_game_not_over_partial_grids(self):
        """Test game not over with partial grids."""
        p1 = GridState(columns=((1, 2), (3,), ()))
        p2 = GridState(columns=((4,), (5, 6), ()))
        assert not KnuckleboneEngine.is_game_over(p1, p2)

    def test_game_over_player1_full(self):
        """Test game over when player 1's grid is full."""
        p1 = GridState(columns=((1, 2, 3), (4, 5, 6), (1, 2, 3)))
        p2 = GridState(columns=((1,), (), ()))
        assert KnuckleboneEngine.is_game_over(p1, p2)

    def test_game_over_player2_full(self):
        """Test game over when player 2's grid is full."""
        p1 = GridState(columns=((1,), (), ()))
        p2 = GridState(columns=((1, 2, 3), (4, 5, 6), (1, 2, 3)))
        assert KnuckleboneEngine.is_game_over(p1, p2)

    def test_game_over_both_full(self):
        """Test game over when both grids are full."""
        p1 = GridState(columns=((1, 2, 3), (4, 5, 6), (1, 2, 3)))
        p2 = GridState(columns=((4, 5, 6), (1, 2, 3), (4, 5, 6)))
        assert KnuckleboneEngine.is_game_over(p1, p2)


class TestKnuckleboneEngineWinner:
    """Tests for winner determination."""

    def test_winner_player1_higher_score(self):
        """Test player 1 wins with higher score."""
        # P1: [4, 4, 4] + [6, 6] + [1] = 36 + 24 + 1 = 61
        # P2: [1, 2, 3] + [4] + [5] = 6 + 4 + 5 = 15
        p1 = GridState(columns=((4, 4, 4), (6, 6), (1,)))
        p2 = GridState(columns=((1, 2, 3), (4,), (5,)))
        assert KnuckleboneEngine.get_winner(p1, p2) == 1

    def test_winner_player2_higher_score(self):
        """Test player 2 wins with higher score."""
        # P1: [1] + [2] + [3] = 1 + 2 + 3 = 6
        # P2: [6, 6, 6] + [5, 5] + [4] = 54 + 20 + 4 = 78
        p1 = GridState(columns=((1,), (2,), (3,)))
        p2 = GridState(columns=((6, 6, 6), (5, 5), (4,)))
        assert KnuckleboneEngine.get_winner(p1, p2) == 2

    def test_winner_tie(self):
        """Test tie returns None."""
        # Both: [3, 3] + [2] + [] = 12 + 2 + 0 = 14
        p1 = GridState(columns=((3, 3), (2,), ()))
        p2 = GridState(columns=((3, 3), (2,), ()))
        assert KnuckleboneEngine.get_winner(p1, p2) is None

    def test_winner_empty_grids(self):
        """Test tie with empty grids."""
        p1 = GridState.empty()
        p2 = GridState.empty()
        assert KnuckleboneEngine.get_winner(p1, p2) is None


class TestKnuckleboneEngineAvailableColumns:
    """Tests for getting available columns."""

    def test_all_columns_available(self):
        """Test all columns available in empty grid."""
        grid = GridState.empty()
        assert KnuckleboneEngine.get_available_columns(grid) == [0, 1, 2]

    def test_some_columns_available(self):
        """Test some columns available."""
        grid = GridState(columns=((1, 2, 3), (4,), ()))
        assert KnuckleboneEngine.get_available_columns(grid) == [1, 2]

    def test_no_columns_available(self):
        """Test no columns available in full grid."""
        grid = GridState(columns=((1, 2, 3), (4, 5, 6), (1, 2, 3)))
        assert KnuckleboneEngine.get_available_columns(grid) == []


class TestKnuckleboneEngineIntegration:
    """Integration tests simulating full game scenarios."""

    def test_simple_game_flow(self):
        """Test a simple game from start to finish."""
        p1_grid = GridState.empty()
        p2_grid = GridState.empty()

        # Player 1 places 4 in column 0
        result = KnuckleboneEngine.place_die(4, 0, p1_grid, p2_grid)
        p1_grid = result.player_grid
        assert KnuckleboneEngine.calculate_grid_score(p1_grid) == 4

        # Player 2 places 6 in column 0
        result = KnuckleboneEngine.place_die(6, 0, p2_grid, p1_grid)
        p2_grid = result.player_grid
        assert KnuckleboneEngine.calculate_grid_score(p2_grid) == 6

        # Player 1 places another 4 in column 0 (now has pair)
        result = KnuckleboneEngine.place_die(4, 0, p1_grid, p2_grid)
        p1_grid = result.player_grid
        assert KnuckleboneEngine.calculate_grid_score(p1_grid) == 16  # (4+4)×2

        # Game not over yet
        assert not KnuckleboneEngine.is_game_over(p1_grid, p2_grid)

    def test_destruction_chain(self):
        """Test strategic destruction of opponent dice."""
        p1_grid = GridState.empty()
        p2_grid = GridState(columns=((4, 4), (), ()))  # P2 has pair of 4s

        # P2 score before: 16
        assert KnuckleboneEngine.calculate_grid_score(p2_grid) == 16

        # P1 places 4 in column 0, destroys both of P2's 4s
        result = KnuckleboneEngine.place_die(4, 0, p1_grid, p2_grid)
        p1_grid = result.player_grid
        p2_grid = result.opponent_grid

        assert result.destroyed_count == 2
        assert p2_grid.columns[0] == ()
        assert KnuckleboneEngine.calculate_grid_score(p2_grid) == 0

    def test_fill_grid_game_over(self):
        """Test filling entire grid triggers game over."""
        # Start with nearly full grid (8 dice)
        p1_grid = GridState(columns=((1, 2, 3), (4, 5, 6), (1, 2)))
        p2_grid = GridState.empty()

        assert not KnuckleboneEngine.is_game_over(p1_grid, p2_grid)

        # Fill last spot in column 2
        result = KnuckleboneEngine.place_die(3, 2, p1_grid, p2_grid)
        p1_grid = result.player_grid

        assert p1_grid.is_full()
        assert KnuckleboneEngine.is_game_over(p1_grid, p2_grid)
