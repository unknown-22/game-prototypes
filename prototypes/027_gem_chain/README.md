# GEM CHAIN — Color-Match Swap Puzzle

**Prototype 027** | Match-3 swap puzzle with chain-reaction spread.

## Source

Reinterpreted from game idea #1 (score 32.75):
- Hook "synthesis compression" → chain cascade multiplier
- Hook "CA spread" → BFS color propagation
- Resources: combo, heat

All 10 generated ideas (seed 42, 2026-05-15) clustered in deckbuilder/dice/auto-shooter.
Match-3 swap is novel for this collection — only falling-block puzzle (011) is adjacent.

## Engine

- **Pyxel 2.x** — 256×280, 30 FPS
- Python 3.12, single-file (~420 lines)
- Type hints throughout, ruff/ty compatible

## Gameplay

### Core Mechanic
Swap adjacent colored gems to create lines of 3+ same color.
Matching triggers BFS spread: adjacent same-color gems also clear.
Each cascade wave increases the COMBO multiplier and builds HEAT.

### The Fun Moment
Setting off a cascading chain that sweeps the entire board —
watching the combo counter climb, score multiply, and gems explode.

### Rules
1. Click a gem to select it (yellow highlight)
2. Click an adjacent gem to swap
3. If the swap creates a match (3+ in a row), gems clear
4. Adjacent same-color gems also clear via BFS spread
5. Remaining gems fall down, new gems fill from top
6. If new matches form, COMBO increases and the cascade continues
7. Invalid swaps flash red and revert

### Risk/Reward
- **COMBO**: Each cascade wave increases multiplier (x2, x3, x4...)
- **HEAT**: Grows with each wave — at threshold (80/100), a QUAKE randomly swaps two gems
- **Timer**: 60 seconds. Maximize score before time runs out
- **No valid moves**: Board auto-shuffles

### Scoring
`points = gems_cleared × 10 × wave_multiplier × (1 + combo)`
Where wave_multiplier = 1 + cascade_wave × 0.5

## Controls

| Input | Action |
|-------|--------|
| Mouse click | Select gem / swap |
| R | Restart (game over screen) |

## Gem Types

| Color | Name | Pyxel Color |
|-------|------|-------------|
| Red | FIRE | COLOR_RED |
| Cyan | ICE | COLOR_CYAN |
| Lime | NATR | COLOR_LIME |
| Yellow | LITE | COLOR_YELLOW |
| Purple | VOID | COLOR_PURPLE |

## Dev Status

- [x] Core match-3 board logic (Board class)
- [x] BFS spread on match
- [x] Cascade chain loop
- [x] Swap animation
- [x] Clear animation + particles
- [x] COMBO multiplier
- [x] HEAT / quake system
- [x] Timer (60s)
- [x] Game over + high score
- [x] Board shuffle on no valid moves
- [x] Headless logic tests (test_imports.py)
- [ ] Web build (HTML)

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/027_gem_chain/main.py
```

## Test

```bash
uv run python prototypes/027_gem_chain/test_imports.py
```
