# New Game Mode Template

Use this template to define a new game mode for Devil's Dozen. Fill out each section, then open Claude Code and say:

> "I want to add a new game mode to Devil's Dozen. Here is the completed template: [paste or reference this file]."

Claude will use this template along with the existing `CONTEXT_*.md` docs to build the engine, wire up the UI, and add audio support.

---

## 1. Mode Identity

| Field | Value |
|-------|-------|
| **Display Name** | _(e.g., "Pirate's Plunder")_ |
| **Internal Key** | _(e.g., `pirates_plunder` — lowercase, underscores, used in code + DB)_ |
| **Dice Type** | _(e.g., D6 / D10 / D12 / D20 / mixed)_ |
| **Number of Dice** | _(e.g., 5)_ |
| **Min Players** | _(e.g., 2)_ |
| **Max Players** | _(e.g., 4)_ |
| **Target Score / Win Condition** | _(e.g., "First to 5,000 points" or "Survive 10 rounds")_ |
| **Configurable Win Conditions?** | _(e.g., "Yes — 3000 / 5000 / 10000" or "No — fixed at 250")_ |

---

## 2. Turn Structure

Describe what happens on a single player's turn from start to finish.

```
Example (Peasant's Gamble):
1. Player rolls all 6 D6 dice
2. Must hold at least one scoring die
3. Can choose to roll remaining dice or bank
4. If no scoring dice on a roll → BUST (lose all unbanked turn points)
5. If all dice score → HOT DICE (roll all 6 fresh, keep accumulated points)
6. Bank ends the turn and adds turn score to total
```

**Your turn structure:**
```
1. ...
2. ...
3. ...
```

---

## 3. Scoring Rules

### 3.1 Basic Scoring

List every scoring combination, its point value, and which dice participate.

| Combo | Points | Example |
|-------|--------|---------|
| _(e.g., Single 1)_ | _(e.g., 100)_ | _(e.g., rolling a 1 among other dice)_ |
| _(e.g., Three of a kind)_ | _(e.g., face value x 100)_ | _(e.g., three 4s = 400)_ |

### 3.2 Special Combos (if any)

| Combo | Points | Notes |
|-------|--------|-------|
| _(e.g., Straight 1-6)_ | _(e.g., 1500)_ | _(e.g., must be all 6 dice)_ |

### 3.3 Bust Condition

When does the player bust? _(e.g., "No scoring dice on a roll" / "Rolling a 1" / "Never busts")_

### 3.4 Hot Dice / Re-roll Condition (if any)

When does the player get to re-roll all dice fresh? _(e.g., "All dice are scoring" / "Not applicable")_

---

## 4. Tiers / Phases (if applicable)

Does the game have tiers, phases, or stages that change the rules as the player progresses?

If **no tiers**: Write "Single phase — rules are constant throughout."

If **yes**:

| Tier | Name | Score Range | Dice Count | Rule Changes |
|------|------|-------------|------------|-------------|
| 1 | _(e.g., Red)_ | _(e.g., 0-100)_ | _(e.g., 8)_ | _(e.g., Standard scoring)_ |
| 2 | _(e.g., Green)_ | _(e.g., 101-200)_ | _(e.g., 3)_ | _(e.g., Score x5, per-die reroll)_ |

---

## 5. Special Mechanics

Describe any unique mechanics not covered above:

- _(e.g., "Kingmaker: Rolling a 20 in Tier 3 gives 20 points to last-place player")_
- _(e.g., "Steal: Rolling triples lets you steal 50 points from another player")_
- _(e.g., "Curse: Rolling snake eyes resets your score to zero")_

If none: Write "No special mechanics."

---

## 6. Player-Facing Rules Summary

Write a concise version of the rules as you'd want players to see it in the sidebar during gameplay. Use markdown. Aim for <=20 lines. This will be displayed directly in the app.

```markdown
**Goal:** ...

**Rolling:**
- ...
- ...

**Scoring:**
| Combo | Points |
|---|---|
| ... | ... |
```

---

## 7. Audio

### 7.1 Background Music

Provide or describe the background music track for this mode.

| Field | Value |
|-------|-------|
| **Filename** | _(e.g., `pirates_theme.mp3` — place in `assets/sounds/`)_ |
| **Music dict key** | _(must match the internal key from Section 1, e.g., `pirates_plunder`)_ |
| **Vibe / Description** | _(e.g., "Upbeat tavern shanty with fiddle and accordion")_ |
| **Provided?** | _(Yes — file attached / No — generate or find one)_ |

### 7.2 New Sound Effects (if any)

List any NEW SFX this mode needs beyond the existing set. Existing SFX that can be reused:

| Existing SFX | Trigger |
|---|---|
| `dice_roll` | On any dice roll |
| `bust` | On bust |
| `bank` | On banking score |
| `hot_dice` | On hot dice / re-roll all |
| `victory` | On game win |
| `tier_advance` | On tier/phase change |

**New SFX needed:**

| SFX Name | Filename | Trigger | Description |
|----------|----------|---------|-------------|
| _(e.g., `steal`)_ | _(e.g., `steal.mp3`)_ | _(e.g., "When player steals points")_ | _(e.g., "Coin clinking sound")_ |

If none: Write "No new SFX — reusing existing set."

---

## 8. UI Considerations

### 8.1 Dice Display

How should the dice look? _(e.g., "Same as D6 but with pirate skull on 1" / "Standard D20 with tier colors" / "Custom D10 faces")_

### 8.2 Hold / Interaction Pattern

Which pattern should this mode use?

- [ ] **Auto-hold scoring** (like current D6/D20 Tier 1) — scoring dice default to held, player unchecks to release
- [ ] **Per-die reroll** (like D20 Tier 2) — each die has a Reroll button
- [ ] **Auto-apply** (like D20 Tier 3) — roll result is applied automatically, no player choice
- [ ] **Other** — describe: _____________

### 8.3 Special UI Elements

Any special animations, indicators, or displays needed?

- _(e.g., "Show a 'steal target' selector when triples are rolled")_
- _(e.g., "Tier indicator like Alchemist's Ascent")_
- _(e.g., "Round counter at the top")_

If none: Write "Standard UI — no special elements."

---

## 9. Integration Checklist

_Claude will handle these, but this is the work involved for reference:_

### Engine (`src/engine/`)
- [ ] New engine class (e.g., `pirates_plunder.py`) with `roll_dice()`, `calculate_score()`, bust/hot-dice logic
- [ ] Scoring result dataclass with `points`, `is_bust`, `scoring_dice_indices`, `breakdown`
- [ ] Unit tests covering all scoring combos, edge cases, bust, and hot dice

### Database
- [ ] Add mode key to `game_mode` column allowed values
- [ ] Any new `game_state` columns? _(e.g., "round_number" / "steal_target")_

### UI
- [ ] Add to home page mode selector
- [ ] Wire into `game.py` roll/hold/bank handlers
- [ ] Add scoring indices helper in `game.py`
- [ ] Add rules text to `app.py` (`_XX_RULES` constant + sidebar render)
- [ ] Add background music entry to `_MUSIC_FILES` in `sounds.py`
- [ ] Add any new SFX entries to `_SFX_FILES` in `sounds.py`
- [ ] Add win condition options if configurable

### Assets
- [ ] Background music file in `assets/sounds/`
- [ ] Any new SFX files in `assets/sounds/`
- [ ] Update `.gitattributes` for LFS tracking if new MP3s added

---

## 10. Example: Filling This Out for Peasant's Gamble

<details>
<summary>Click to expand worked example</summary>

### 1. Mode Identity

| Field | Value |
|-------|-------|
| **Display Name** | Peasant's Gamble |
| **Internal Key** | `peasants_gamble` |
| **Dice Type** | D6 |
| **Number of Dice** | 6 |
| **Min/Max Players** | 2–4 |
| **Target Score** | First to target score |
| **Configurable?** | Yes — 3,000 / 5,000 / 10,000 |

### 2. Turn Structure

```
1. Roll all 6 dice
2. Must hold at least one scoring die
3. Roll remaining dice or bank turn score
4. No scoring dice = BUST (lose turn score)
5. All dice score = HOT DICE (roll all 6 fresh)
6. Bank adds turn score to total, ends turn
```

### 3. Scoring Rules

| Combo | Points |
|---|---|
| Single 1 | 100 |
| Single 5 | 50 |
| Three 1s | 1,000 |
| Three 2s–6s | Face x 100 |
| Four+ of a kind | Previous tier x 2 |
| 1-2-3-4-5 | 500 |
| 2-3-4-5-6 | 750 |
| 1-2-3-4-5-6 | 1,500 |

**Bust:** No scoring dice on a roll.
**Hot Dice:** All 6 dice are scoring.

### 4. Tiers

Single phase — rules are constant throughout.

### 7. Audio

| Field | Value |
|-------|-------|
| **Filename** | `d6_theme.mp3` |
| **Music key** | `peasants_gamble` |
| **Vibe** | Medieval tavern with lute and drums |
| **Provided?** | Yes |

No new SFX — reusing existing set.

### 8. UI

- Auto-hold scoring dice
- No special elements beyond standard dice tray + scoreboard

</details>
