"""
Knucklebones grid board component.

Displays dual 3×3 grids with column scores and placement controls.
"""

import streamlit as st

from src.engine.knucklebones import GridState, KnuckleboneEngine


def render_knucklebones_board(
    player1_grid: dict,
    player2_grid: dict,
    my_turn_order: int,
    player1_name: str,
    player2_name: str,
) -> None:
    """
    Render the Knucklebones game board (grids only, no controls).

    Args:
        player1_grid: Player 1's grid dictionary
        player2_grid: Player 2's grid dictionary
        my_turn_order: Turn order of current user (0 or 1)
        player1_name: Player 1's username
        player2_name: Player 2's username
    """
    # Convert dicts to GridState objects
    p1_grid = GridState.from_dict(player1_grid)
    p2_grid = GridState.from_dict(player2_grid)

    # Determine which grid belongs to current user
    my_grid = p1_grid if my_turn_order == 0 else p2_grid
    opponent_grid = p2_grid if my_turn_order == 0 else p1_grid
    my_name = player1_name if my_turn_order == 0 else player2_name
    opponent_name = player2_name if my_turn_order == 0 else player1_name

    # Opponent's grid (top section)
    st.markdown(f"#### 🎯 {opponent_name}'s Grid (Score: {KnuckleboneEngine.calculate_grid_score(opponent_grid)})")
    _render_grid_display(opponent_grid, flipped=True)

    # Smaller divider between grids
    st.markdown('<div style="margin: 8px 0; border-top: 1px solid var(--gold-dark); opacity: 0.3;"></div>', unsafe_allow_html=True)

    # My grid (bottom section)
    st.markdown(f"#### 🎯 {my_name}'s Grid (Score: {KnuckleboneEngine.calculate_grid_score(my_grid)})")
    _render_grid_display(my_grid, flipped=False)


def _render_grid_display(grid: GridState, flipped: bool = False) -> None:
    """
    Render a single 3×3 grid with column scores.

    Args:
        grid: GridState to display
        flipped: If True, show as opponent's view (inverted)
    """
    # Calculate column scores
    col_scores = [
        KnuckleboneEngine.calculate_column_score(grid.columns[i])
        for i in range(3)
    ]

    # Build HTML table
    html = '<div class="knucklebones-grid"><table>'

    # Column scores header (top for opponent, bottom for player)
    if flipped:
        html += '<tr class="column-scores">'
        for score in col_scores:
            html += f'<td><strong>{score} pts</strong></td>'
        html += '</tr>'

    # Grid rows (top to bottom = position 2 to 0)
    for row in range(2, -1, -1):
        html += '<tr>'
        for col_idx in range(3):
            column = grid.columns[col_idx]
            if row < len(column):
                die_value = column[row]
                # Display as number (matching D6 style)
                html += f'<td><div class="die grid-die">{die_value}</div></td>'
            else:
                html += '<td><div class="die grid-die empty">-</div></td>'
        html += '</tr>'

    # Column scores footer (bottom for player, top for opponent)
    if not flipped:
        html += '<tr class="column-scores">'
        for score in col_scores:
            html += f'<td><strong>{score} pts</strong></td>'
        html += '</tr>'

    html += '</table></div>'

    st.markdown(html, unsafe_allow_html=True)
