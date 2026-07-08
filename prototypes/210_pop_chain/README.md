# POP CHAIN — Bubble Wrap Popping Game

**Source**: Game Idea Factory #1 (Score 32.75) — deckbuilder idea reinterpreted into bubble wrap popping
- "CA infection/growth fills the board" → bubble inflation via CA spread
- "synthesis/compression" → COMBO chain → SUPER POP
- "risk/heat management" → frustration HEAT from wrong-color pops

**Engine**: Pyxel 2.x, 320×240, single-file

## Gameplay

Pop bubbles on a 10×8 grid. Bubbles continuously inflate via cellular automaton spread — each bubble has a chance to "inflate" adjacent empty cells. Your active pop-color cycles every 1.5 seconds.

- **Click** matching-color bubbles to pop them and build COMBO
- **COMBO chain**: Same-color consecutive pops. Score = 10 × (1 + combo × 0.5)
- **SUPER POP**: COMBO ≥ 4 triggers 5-second rainbow mode — any color pop succeeds, 3× score, all existing bubbles auto-pop
- **HEAT**: Wrong-color pop adds frustration heat (+15). HEAT ≥ 100 = game over
- **Timer**: 60 seconds to maximize your score

### The Most Fun Moment
Letting bubbles spread to form large same-color clusters, then triggering a SUPER POP that cascades through the entire grid in a rainbow burst.

## Controls

| Action | Input |
|--------|-------|
| Pop bubble | Mouse click |
| Start / Restart | Enter (KEY_RETURN) |

## Mechanics Reference

| Constant | Value |
|----------|-------|
| Grid | 10×8 (CELL=24px) |
| Colors | RED(8), GREEN(3), DARK_BLUE(5), YELLOW(10) |
| CA inflation | Every 120 frames (2s), 40% chance |
| Color cycle | Every 90 frames (1.5s) |
| SUPER duration | 300 frames (5s) |
| Bubble max | 32 |
| HEAT max | 100 |

## Dev Status

- ✅ Core popping + COMBO chain
- ✅ CA bubble inflation
- ✅ SUPER POP mode (rainbow, 3× score)
- ✅ HEAT risk system
- ✅ 60s timer
- ✅ Particle + floating text feedback
- ✅ Title / Playing / Game Over screens
- ✅ 56 headless tests
- ✅ Ruf + ty checks pass

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/210_pop_chain/main.py
```

## Tests

```bash
uv run pytest prototypes/210_pop_chain/test_imports.py -v
```
