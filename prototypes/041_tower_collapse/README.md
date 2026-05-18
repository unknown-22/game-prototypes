# 041 Tower Collapse

**Tower Collapse Puzzle** — Drop blocks onto a tower. Match 3+ same-color adjacent blocks to trigger collapse chains. Chain reactions multiply combo score. Game over if the tower reaches the danger line.

## Source

Reinterpreted from game_idea_factory idea #1 (score 32.0, "deckbuilder / hacking theme" with hooks: "effects synthesize into one card" + "values split and flow across multiple paths, converge for big damage"). Reinterpreted into a **tower stack/collapse physics puzzle** — first prototype of this genre in the collection.

## Engine

- Pyxel 2.x
- Screen: 128×160, display_scale=3
- 10×16 grid, 12px cells

## Gameplay

### Core Mechanic
Drop colored blocks onto a growing tower from the top. When 3+ same-color blocks are orthogonally adjacent, they clear simultaneously. Blocks above fall (gravity), potentially creating new matches — chain reactions score combo multipliers.

### The Best Moment
A single drop triggers a 3+ chain cascade: blocks clear, others fall, new matches form, combo multiplier climbs, and the screen shakes as the score explodes.

### Rules
- **Drop**: Blocks fall automatically at a steady rate. Press SPACE/Click to drop instantly.
- **Move**: Arrow keys or A/D to move the dropping block left/right.
- **Match**: 3+ same-color orthogonally adjacent blocks auto-clear.
- **Chain**: Cleared blocks → gravity → new matches = chain reaction (x2, x3... multiplier).
- **Combo**: Consecutive chains build combo multiplier (resets after 2 seconds).
- **Danger zone**: Top 2 rows (highlighted in dark blue). Game over if any block reaches it.
- **Scoring**: `blocks_cleared × 10 × chain_count × (1 + combo × 0.5)`

### Controls
| Input | Action |
|---|---|
| A/D or ←/→ | Move dropping block |
| SPACE / Click | Drop block instantly |
| R | Restart (game over) |
| SPACE | Start (title screen) |

## Block Colors

| Color | Pyxel ID |
|---|---|
| Red | 8 |
| Yellow | 11 |
| Green | 10 |
| Cyan | 12 |
| Pink | 14 |

## Dev Status

- ✅ Core grid + block placement
- ✅ BFS cluster detection
- ✅ Gravity cascade
- ✅ Chain reaction resolution
- ✅ Combo scoring system
- ✅ Particle burst effects
- ✅ Floating score text
- ✅ Screen shake
- ✅ Danger zone / game over
- ✅ Title screen
- ✅ Fast restart
- ✅ 33 headless logic tests

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/041_tower_collapse/main.py
```

## How to Test

```bash
uv run python prototypes/041_tower_collapse/test_imports.py
```
