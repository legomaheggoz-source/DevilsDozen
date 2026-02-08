# Context: UI/UX Layer

## Quick Summary

Streamlit-based interface with medieval tavern aesthetic. Features heavy CSS theming, Lottie animations, interactive dice components, and optional sound effects. Designed for both desktop and mobile play.

---

## Files in This Module

| File | Purpose |
|------|---------|
| `src/ui/__init__.py` | Public exports |
| `src/ui/app.py` | Main Streamlit entrypoint |
| **Components** ||
| `src/ui/components/dice_tray.py` | Interactive dice display with click-to-hold |
| `src/ui/components/scoreboard.py` | Player scores panel |
| `src/ui/components/turn_controls.py` | Roll, Bank, Hold buttons |
| `src/ui/components/lobby.py` | Join/Create lobby interface |
| **Themes** ||
| `src/ui/themes/medieval.css` | Custom dark theme CSS |
| `src/ui/themes/animations.py` | Lottie and CSS animation helpers |
| **Pages** ||
| `src/ui/pages/home.py` | Landing/lobby selection page |
| `src/ui/pages/game.py` | Active game page |
| `src/ui/pages/results.py` | Victory/end game screen |

---

## Dependencies

### External Packages
- `streamlit`: UI framework
- `streamlit-lottie`: Lottie animation support
- `Pillow`: Image processing for dice visuals

### Internal Imports
- From `engine`: `PeasantsGambleEngine`, `AlchemistsAscentEngine`, scoring classes
- From `database`: `LobbyManager`, `PlayerManager`, `GameStateManager`
- From `realtime`: `RealtimeManager`, `GameEvent`
- From `config`: `Settings`

---

## Exports

```python
from src.ui import (
    # Main entry
    run_app,              # Start Streamlit application

    # Components (for testing/composition)
    DiceTray,
    Scoreboard,
    TurnControls,
    LobbyPanel,
)
```

---

## Current State

- [ ] `app.py` - Main entrypoint with routing
- [ ] `themes/medieval.css` - Theme implementation
- [ ] `themes/animations.py` - Animation helpers
- [ ] `components/dice_tray.py` - Dice display
- [ ] `components/scoreboard.py` - Score panel
- [ ] `components/turn_controls.py` - Game controls
- [ ] `components/lobby.py` - Lobby management
- [ ] `pages/home.py` - Landing page
- [ ] `pages/game.py` - Game page
- [ ] `pages/results.py` - Victory screen
- [ ] Mobile responsiveness
- [ ] Sound integration with mute toggle

---

## Medieval Theme Design

### Color Palette

```css
:root {
    /* Backgrounds */
    --bg-dark: #1a1510;           /* Deep brown-black (main bg) */
    --bg-medium: #2d261e;         /* Aged wood (cards, panels) */
    --bg-light: #3d3428;          /* Lighter wood (hover states) */

    /* Text */
    --text-gold: #d4a84b;         /* Candlelit gold (headings) */
    --text-light: #e8dcc8;        /* Parchment (body text) */
    --text-muted: #8a7f6d;        /* Faded ink (secondary) */

    /* Accents */
    --accent-red: #8b3a3a;        /* Dried blood (danger, bust) */
    --accent-green: #3a6b4f;      /* Oxidized copper (success) */
    --accent-blue: #3a5a8b;       /* Deep sapphire (info) */

    /* Dice Tiers (Alchemist's Ascent) */
    --tier-red: #c94c4c;          /* Tier 1 dice */
    --tier-green: #4caf50;        /* Tier 2 dice */
    --tier-blue: #2196f3;         /* Tier 3 dice */

    /* Borders */
    --border-dark: #4a3f32;       /* Dark wood grain */
    --border-gold: #8b7355;       /* Tarnished brass */
}
```

### Typography

```css
/* Import medieval-style fonts */
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');

body {
    font-family: 'Crimson Text', Georgia, serif;
    font-size: 18px;
    line-height: 1.6;
}

h1, h2, h3 {
    font-family: 'Cinzel', 'Times New Roman', serif;
    font-weight: 700;
    color: var(--text-gold);
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
}
```

### Component Styling

```css
/* Parchment-style cards */
.stCard {
    background: var(--bg-medium);
    border: 2px solid var(--border-dark);
    border-radius: 4px;
    box-shadow:
        inset 0 0 20px rgba(0,0,0,0.3),
        0 4px 8px rgba(0,0,0,0.4);
}

/* Medieval buttons */
.stButton > button {
    background: linear-gradient(180deg, var(--bg-light) 0%, var(--bg-medium) 100%);
    border: 2px solid var(--border-gold);
    color: var(--text-gold);
    font-family: 'Cinzel', serif;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    background: linear-gradient(180deg, var(--bg-medium) 0%, var(--bg-dark) 100%);
    box-shadow: 0 0 10px var(--text-gold);
}
```

---

## Component Specifications

### Dice Tray

```python
# src/ui/components/dice_tray.py
import streamlit as st

def render_dice_tray(
    dice: list[int],
    held_indices: set[int],
    on_toggle: Callable[[int], None],
    dice_type: str = "d6",
    tier_color: str | None = None  # For Alchemist's Ascent
) -> None:
    """
    Render interactive dice display.

    Args:
        dice: List of dice values
        held_indices: Set of indices that are held
        on_toggle: Callback when die is clicked
        dice_type: "d6" or "d20"
        tier_color: "red", "green", or "blue" for D20 tiers
    """
    cols = st.columns(len(dice))
    for i, (col, value) in enumerate(zip(cols, dice)):
        with col:
            is_held = i in held_indices
            css_class = "die held" if is_held else "die"

            if st.button(
                str(value),
                key=f"die_{i}",
                help="Click to hold/unhold"
            ):
                on_toggle(i)
```

### Scoreboard

```python
# src/ui/components/scoreboard.py
def render_scoreboard(
    players: list[Player],
    current_turn_index: int,
    turn_score: int,
    target_score: int
) -> None:
    """
    Render player scores with turn indicator.
    """
    st.markdown(f"### Target: {target_score:,} points")

    for i, player in enumerate(players):
        is_current = i == current_turn_index
        icon = "▶" if is_current else " "

        st.markdown(
            f"{icon} **{player.username}**: {player.total_score:,}"
            + (f" (+{turn_score})" if is_current and turn_score > 0 else "")
        )
```

---

## Asset Requirements

### Dice Images

| Asset | Path | Description |
|-------|------|-------------|
| D6 Faces | `assets/dice/d6/1.png` - `6.png` | Stone/parchment texture |
| D20 Faces | `assets/dice/d20/1.png` - `20.png` | Metal/gem texture |
| Held State | `assets/dice/held_overlay.png` | Gold border overlay |

### Animations (Lottie JSON)

| Asset | Path | Trigger |
|-------|------|---------|
| Dice Roll | `assets/animations/roll.json` | On roll button click |
| Bust | `assets/animations/bust.json` | On bust detection |
| Victory | `assets/animations/victory.json` | On game win |
| Candle Flicker | `assets/animations/candle.json` | Ambient (optional) |

### Audio Files

| Asset | Path | Trigger |
|-------|------|---------|
| Dice Roll | `assets/sounds/dice_roll.mp3` | On roll |
| Bust | `assets/sounds/bust.mp3` | On bust |
| Victory | `assets/sounds/victory.mp3` | On win |
| Tavern Ambient | `assets/sounds/tavern.mp3` | Background loop |
| Button Click | `assets/sounds/click.mp3` | On button press |

---

## Streamlit Configuration

### Page Config

```python
# src/ui/app.py
import streamlit as st

st.set_page_config(
    page_title="Devil's Dozen",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="collapsed"
)
```

### Custom CSS Injection

```python
def load_custom_css():
    with open("src/ui/themes/medieval.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
```

---

## Mobile Responsiveness

### Breakpoints

```css
/* Mobile-first approach */
.dice-tray {
    display: grid;
    grid-template-columns: repeat(3, 1fr);  /* 3 dice per row on mobile */
    gap: 8px;
}

@media (min-width: 768px) {
    .dice-tray {
        grid-template-columns: repeat(6, 1fr);  /* All 6 dice on desktop */
    }
}

@media (min-width: 1024px) {
    .dice-tray {
        grid-template-columns: repeat(8, 1fr);  /* For D20 mode with 8 dice */
    }
}
```

---

## Testing Notes

### Run Streamlit Locally
```bash
streamlit run src/ui/app.py
```

### Visual Testing Checklist
- [ ] Theme renders correctly in Chrome, Firefox, Safari
- [ ] Dice are clickable and show held state
- [ ] Animations play smoothly
- [ ] Sound toggle works and persists
- [ ] Mobile layout is usable

---

## Discovered Context

> This section is updated during implementation. Check here before starting work.

[Empty until implementation begins]
