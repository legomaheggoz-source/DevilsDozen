# Devil's Dozen - Product Requirements Document

## 1. Executive Summary

**Devil's Dozen** is a medieval-themed multiplayer dice game supporting 2-4 players across two distinct game modes. The game combines risk-reward mechanics with real-time multiplayer synchronization, wrapped in an immersive tavern aesthetic.

### Vision Statement
Create an engaging, free-to-host multiplayer dice game that captures the tension of push-your-luck gameplay while providing a polished, thematic experience.

---

## 2. Game Modes

### 2.1 The Peasant's Gamble (D6 Mode)

A 6-dice game inspired by Kingdom Come: Deliverance's dice minigame.

**Objective**: First player to reach the target score wins (configurable: 3000/5000/10000 points).

**Core Mechanics**:
- Roll 6 dice, must set aside at least one scoring die
- Can continue rolling remaining dice to accumulate points
- **Bust**: Rolling no scoring dice loses all accumulated turn points
- **Hot Dice**: Scoring all 6 dice allows rolling all dice again

**Scoring Table**:
| Roll | Points |
|------|--------|
| Single 1 | 100 |
| Single 5 | 50 |
| Three 1s | 1,000 |
| Three of X | X × 100 |
| Four+ of X | Previous tier × 2 |
| 1-2-3-4-5 | 500 (Low Straight) |
| 2-3-4-5-6 | 750 (High Straight) |
| 1-2-3-4-5-6 | 1,500 (Full Straight) |

### 2.2 The Alchemist's Ascent (D20 Mode)

A tiered progression game using D20 dice with escalating risk.

**Objective**: First player to reach 250 points wins.

**Tier System**:

| Tier | Score Range | Dice | Special Rules |
|------|-------------|------|---------------|
| Red (1) | 0-100 | 8 D20s | Standard scoring |
| Green (2) | 101-200 | 3 D20s | 5× multiplier, reroll risk |
| Blue (3) | 201-250 | 1 D20 | High risk/reward finale |

**Tier 1 Scoring** (Red):
- Single 1 = 1 pt, Single 5 = 5 pts
- Pair = face value (pair of 1s = 10, pair of 5s = 20)
- Three+ of kind = sum of dice
- Sequence of 3 = 10 pts (+10 per additional)

**Tier 2 Scoring** (Green):
- Same as Tier 1 but **5× multiplier**
- Can reroll individual dice, but if new < old = BUST

**Tier 3 Scoring** (Blue):
- Roll 1 = Reset to 0 points (devastating)
- Roll 20 = Gift 20 points to last-place player
- Roll 2-19 = Face value as points

---

## 3. Multiplayer Requirements

### 3.1 Lobby System
- **Create Lobby**: Generate 6-character shareable code
- **Join Lobby**: Enter code to join existing game
- **Player Capacity**: 2-4 players
- **Player Names**: 30 character max, unique within lobby

### 3.2 Turn Flow
1. Active player's UI is enabled, others observe
2. All players see dice rolls in real-time
3. Turn ends on: Bank, Bust, or Win
4. Automatic turn progression to next player

### 3.3 Reconnection
- Players can rejoin via lobby code
- Game state persists through disconnection
- 5-minute timeout before player is marked inactive

---

## 4. User Interface Requirements

### 4.1 Core Components

**Dice Tray**
- Visual representation of all dice in current roll
- Click-to-hold interaction for setting aside dice
- Animation on roll (1-2 seconds)
- Visual distinction between held/unheld dice

**Scoreboard**
- All player names with total scores
- Current turn indicator (highlighted player)
- Score needed to win
- Current turn score (for active player)

**Controls**
- Roll button (starts turn / continues roll)
- Bank button (end turn, keep points)
- Hold selection (click dice to toggle)
- Clear visual feedback for button states

### 4.2 Theme Requirements (Medieval Tavern)
- Dark color palette (browns, golds, deep reds)
- Parchment/aged paper textures
- Gothic or medieval-style typography
- Candlelit ambiance effects

### 4.3 Animation & Audio
- Dice roll animation with physics feel
- Bust: skull icon, groan sound
- Victory: celebration, fanfare
- Audio mute toggle (persisted)

---

## 5. Technical Requirements

### 5.1 Performance
- Initial load < 5 seconds
- Dice roll animation < 2 seconds
- Turn sync latency < 500ms
- Support 4 concurrent players per lobby

### 5.2 Browser Support
- Chrome, Firefox, Safari, Edge (latest 2 versions)
- Mobile browsers (iOS Safari, Chrome Android)
- Responsive layout for mobile play

### 5.3 Accessibility
- Keyboard navigation for controls
- Sufficient color contrast (WCAG AA)
- Screen reader labels for key actions

---

## 6. Future Considerations

These features are **out of scope** for MVP but documented for future development:

- Additional game modes
- Player avatars / customization
- Persistent accounts and statistics
- Tournament mode
- Spectator mode
- Private/password lobbies
- Chat system
- Achievement system

---

## 7. Success Metrics

### Launch Criteria
- [ ] Both game modes fully playable
- [ ] 2-4 player multiplayer functional
- [ ] Medieval theme applied throughout
- [ ] Audio with mute toggle
- [ ] Mobile-responsive layout
- [ ] Deployed on Hugging Face Spaces

### Quality Targets
- Zero critical bugs in core gameplay
- All scoring calculations verified by tests
- Successful 4-player game session with 0 sync errors
