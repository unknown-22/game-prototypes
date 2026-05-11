# 011_alchemy_drop — Alchemy Drop

**Genre:** Falling-block puzzle
**Engine:** Pyxel 2.x, 256×256, display_scale=3

## Source

Based on game_idea_factory idea #2 (Score 31.4):
- **Theme:** Alchemy (synthesis)
- **Hook:** Gravity/collapse chain reactions, puzzle-like crumbling
- **Core loop:** Drop → match → chain → repeat
- Reinterpreted from dice/bag-builder to **falling-block puzzle** — a genre absent from existing prototypes

## Gameplay

Match **3 or more** identical elemental blocks in a horizontal or vertical line to clear them. Cleared blocks leave gaps; blocks above fall down (gravity), potentially creating new matches — **chain reactions**.

Each chain step multiplies the score:
- First match: ×1 (base score)
- Second match (chain): ×2
- Third match: ×3
- ...and so on

The core thrill: **stack blocks near the top, then trigger a massive chain that cascades through the entire board.**

## Elements

| Element | Color  | Label | Description |
|---------|--------|-------|-------------|
| FIRE    | Red    | FIR   | Basic element |
| WATER   | Blue   | WTR   | Basic element |
| EARTH   | Tan    | ERT   | Basic element |
| AIR     | White  | AIR   | Basic element |
| AETHER  | Purple | ATH   | Basic element |

All elements match equally — no type advantages. The depth comes from chain-building, not element selection.

## Controls

| Key | Action |
|-----|--------|
| ← → / A D | Move block horizontally |
| ↓ / S | Soft drop (faster fall, +1 point per step) |
| SPACE | Hard drop (instant place, +2 points per step skipped) |
| R | Restart after game over |
| Q | Quit |

## Scoring

- **10 pts** per block cleared (base)
- **× chain multiplier** for consecutive chain steps
- **+1 pt** per soft-drop step
- **+2 pts** per hard-drop step skipped
- Level up every **200 points** (drop speed increases)

## Difficulty

- Starts at 40 frames per drop step (~1.5 sec)
- Speeds up by 3 frames per level
- Minimum speed: 6 frames per drop step (~0.1 sec)
- Game over when blocks reach the top of the grid

## Dev Status

- ✅ Core falling-block mechanics
- ✅ Element matching (horizontal + vertical 3+)
- ✅ Chain reaction system with multiplier
- ✅ Gravity after clears
- ✅ Level/speed progression
- ✅ Particle effects on clear
- ✅ Combo text popups
- ✅ Hard drop + soft drop
- ✅ Game over + restart
- ✅ Info panel (score, level, next, legend)
- ⬜ Sound effects
- ⬜ Element synthesis (matching 4+ creates upgraded element)
- ⬜ High score persistence
- ⬜ More element types / special blocks

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/011_alchemy_drop/main.py
```
