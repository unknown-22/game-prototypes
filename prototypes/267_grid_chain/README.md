# GRID CHAIN — Color Sudoku Puzzle

**Source**: game_idea_factory Idea #1 (Score 31.35) — reinterpreted from dice/bag roguelite with alchemy synthesis hooks into a Sudoku-style deduction puzzle.

**Engine**: Pyxel 2.x, 320×240, 30fps

## Gameplay

A 4×4 grid where each row and column must contain all 4 colors (RED, LIME, DARK_BLUE, YELLOW) exactly once. 5 cells are pre-filled as "givens". The player selects a color and places it in an empty cell.

- **Valid placement**: color doesn't conflict with row/column → COMBO++
- **Invalid placement**: duplicate in row/column → COMBO reset + HEAT+15
- **Same-color consecutive placements**: COMBO chain (score = 10 × combo × multiplier)
- **COMBO ≥ 4**: SUPER PLACE (300f rainbow mode, all placements auto-valid, 3× score, HEAT frozen)
- **Complete grid**: bonus (500 × round), new round with fresh grid
- **HEAT**: mismatch +15, time pressure +0.05/f, decay -0.02/f, cap 100 → GAME OVER
- **Timer**: 60 seconds (1800 frames)

### The Most Fun Moment
Building a COMBO chain of 4+ same-color valid placements, triggering SUPER PLACE, and watching the rainbow-bordered grid fill up with 3× score bursts.

### Risk vs Reward
- **Risk**: same-color COMBO continuation for high multipliers + SUPER PLACE
- **Risk**: color mismatch resets COMBO and spikes HEAT
- **Reward**: SUPER PLACE auto-validates any placement for 3× score

## Controls

| Input | Action |
|-------|--------|
| Mouse click grid cell | Place selected color |
| Mouse click palette button | Select color |
| Keys 1-4 | Select color (RED/LIME/DARK_BLUE/YELLOW) |
| ENTER | Start from title / Retry from game over |
| SPACE | Continue from round clear |
| R | Restart (any phase) |

## Dev Status

- ✅ Core mechanic: 4×4 Sudoku placement with COMBO chain
- ✅ SUPER PLACE mode
- ✅ HEAT risk system
- ✅ Round progression
- ✅ Particle + floating text effects
- ✅ Three screens (Title/Playing/Game Over)
- ✅ 50 headless tests
- ✅ ruff + ty clean
- ⬜ Sound effects

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/267_grid_chain/main.py
```

## Test

```bash
uv run pytest prototypes/267_grid_chain/test_imports.py -v
```
