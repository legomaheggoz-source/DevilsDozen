"""
Tug of War Meter Component for Alien Invasion

Visualizes the balance between Death Rays (defense) and Tanks (threat).
"""

import streamlit as st


def render_tug_of_war_meter(
    death_rays_count: int,
    tanks_count: int,
    ratio: float
) -> None:
    """
    Render the Tug of War meter showing Death Rays vs Tanks balance.

    The meter uses a horizontal gradient bar (red → orange → green) with
    a position indicator showing the current balance.

    Args:
        death_rays_count: Number of death rays collected
        tanks_count: Number of tanks collected
        ratio: Position ratio from 0.0 (all tanks) to 1.0 (all rays)
    """
    # Determine status based on counts
    if tanks_count > death_rays_count:
        status_icon = "⚠️"
        status_text = "BUST ZONE"
        status_color = "#ff2e2e"
    elif tanks_count == death_rays_count and tanks_count > 0:
        status_icon = "⚖️"
        status_text = "NEUTRAL"
        status_color = "#c9a84c"
    elif death_rays_count > tanks_count:
        status_icon = "✅"
        status_text = "SAFE TO BANK"
        status_color = "#4ecca3"
    else:
        status_icon = "⚖️"
        status_text = "START ROLLING"
        status_color = "#a09080"

    # Convert ratio to percentage for CSS positioning
    position_pct = ratio * 100

    # Render meter HTML — NO blank lines between tags (Streamlit's markdown
    # parser splits HTML at blank lines, causing partial raw-text rendering).
    meter_html = (
        f'<div class="tug-of-war-container">'
        f'<div class="tug-of-war-header">'
        f'<span class="tow-status" style="color: {status_color};">'
        f'{status_icon} {status_text}'
        f'</span>'
        f'</div>'
        f'<div class="tug-of-war-meter">'
        f'<div class="tug-of-war-bar">'
        f'<div class="tug-of-war-indicator" style="left: {position_pct}%;"></div>'
        f'</div>'
        f'</div>'
        f'<div class="tug-of-war-counts">'
        f'<span class="tow-count tow-tanks">🔺 Tanks: {tanks_count}</span>'
        f'<span class="tow-count tow-rays">⚡ Death Rays: {death_rays_count}</span>'
        f'</div>'
        f'</div>'
    )

    st.markdown(meter_html, unsafe_allow_html=True)
