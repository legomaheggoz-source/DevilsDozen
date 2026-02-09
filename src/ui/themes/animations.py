"""CSS injection and HTML animation helpers for medieval theme."""

from pathlib import Path

import streamlit as st


def load_css() -> None:
    """Inject the medieval CSS theme into the Streamlit app."""
    css_path = Path(__file__).parent / "medieval.css"
    css_text = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)


def render_bust_animation() -> None:
    """Render the bust overlay with shake animation."""
    st.markdown(
        '<div class="bust-overlay">'
        "<h2>BUST!</h2>"
        "<p>No scoring dice — your turn score is lost.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_victory_animation(name: str) -> None:
    """Render the victory overlay with glow animation."""
    st.markdown(
        '<div class="victory-overlay">'
        '<span class="crown">&#9813;</span>'
        f"<h1>{name} Wins!</h1>"
        "<p>The realm bows before the champion.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_hot_dice_animation() -> None:
    """Render the hot dice banner with pulse animation."""
    st.markdown(
        '<div class="hot-dice-banner">'
        "&#9876; HOT DICE! All dice scored — roll again! &#9876;"
        "</div>",
        unsafe_allow_html=True,
    )


def render_score_popup(points: int) -> None:
    """Render an animated score popup."""
    st.markdown(
        f'<div class="score-popup">+{points}</div>',
        unsafe_allow_html=True,
    )


def render_tier_indicator(name: str, color: str) -> None:
    """Render a colored tier indicator badge.

    Args:
        name: Tier display name (e.g., "Red", "Green", "Blue").
        color: CSS class suffix ("red", "green", or "blue").
    """
    st.markdown(
        f'<div class="tier-indicator tier-{color}">{name} Tier</div>',
        unsafe_allow_html=True,
    )
