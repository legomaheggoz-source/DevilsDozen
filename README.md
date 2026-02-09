---
title: Devil's Dozen
emoji: 🎲
colorFrom: red
colorTo: yellow
sdk: streamlit
app_file: src/ui/app.py
python_version: "3.12"
pinned: false
---

# Devil's Dozen 🎲

A medieval-themed multiplayer dice game supporting 2-4 players across two distinct game modes.

## Game Modes

### The Peasant's Gamble (D6)
A 6-dice push-your-luck game inspired by Kingdom Come: Deliverance. Roll dice, set aside scoring combinations, and decide whether to bank your points or risk it all for more.

- **Goal**: First to reach target score (3000/5000/10000)
- **Mechanics**: Hot Dice, Bust detection, Straights & Sets

### The Alchemist's Ascent (D20)
A tiered progression game using D20 dice with escalating risk across three tiers.

- **Goal**: First to reach 250 points
- **Tier 1** (Red): 8 dice, standard scoring
- **Tier 2** (Green): 3 dice, 5x multiplier with risky rerolls
- **Tier 3** (Blue): 1 die, high stakes finale

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| Backend | Pure Python 3.11+ |
| Database | Supabase (PostgreSQL) |
| Real-time | Supabase Realtime |
| Hosting | Hugging Face Spaces |

## Project Structure

```
DevilsDozen/
├── docs/                    # Documentation
│   ├── PRD.md              # Product requirements
│   ├── ARCHITECTURE.md     # Technical architecture
│   └── CONTEXT_*.md        # Module-specific context files
├── src/
│   ├── engine/             # Pure game logic
│   ├── database/           # Supabase integration
│   ├── realtime/           # WebSocket sync
│   ├── ui/                 # Streamlit interface
│   └── config/             # Settings and logging
├── tests/                  # Test suite
├── assets/                 # Dice images, sounds, animations
└── requirements.txt        # Python dependencies
```

## Quick Start

### Prerequisites
- Python 3.11+
- Supabase account (free tier)

### Installation

```bash
# Clone the repository
git clone https://github.com/legomaheggoz-source/DevilsDozen.git
cd DevilsDozen

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your Supabase credentials
```

### Run Locally

```bash
streamlit run src/ui/app.py
```

### Run Tests

```bash
pytest tests/ -v --cov=src
```

## Documentation

- [Product Requirements](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Game Engine Context](docs/CONTEXT_GAME_ENGINE.md)
- [Database Context](docs/CONTEXT_DATABASE.md)
- [UI Context](docs/CONTEXT_UI.md)
- [Testing Strategy](docs/TESTING_STRATEGY.md)

## Development

This project uses modular context files to enable focused development within Claude Code's context limits. Each module has its own context file documenting patterns, integration points, and discovered learnings.

### Session Workflow
1. Load relevant `CONTEXT_*.md` file
2. Implement within module scope
3. Test changes
4. Update "Discovered Context" section
5. Commit with descriptive message

## License

MIT
