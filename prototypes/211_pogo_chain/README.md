# POGO CHAIN — Pogo Stick Bouncing Game

**Source**: Game Idea Factory #1 (Score 31.75) — deckbuilder idea reinterpreted into pogo stick bouncing
- "Chain propagation + CA grid fills up" → COMBO chain + SUPER BOUNCE auto-collect
- "Synthesis/compression" → SUPER BOUNCE at COMBO ≥ 5
- "Risk/heat management" → HEAT from wrong-color gems

**Engine**: Pyxel 2.x, 320×240, single-file

## Gameplay

Bounce on a pogo stick through colored gems floating in the air. Collect same-color gems consecutively to build COMBO chain and trigger SUPER BOUNCE.

- **Auto-bounce**: Pogo stick bounces automatically (BOUNCE_HEIGHT=80, BOUNCE_SPEED=3.0)
- **Movement**: Arrow keys or A/D to move left/right
- **COMBO chain**: Same-color consecutive gem collections. Score = 10 × (1 + combo × 0.5)
- **SUPER BOUNCE**: COMBO ≥ 5 triggers 5-second rainbow mode — any gem matches, 3× score, auto-collect all on-screen gems
- **HEAT**: Wrong-color gem adds frustration heat (+15). HEAT ≥ 100 = game over (pogo stick breaks)
- **Timer**: 60 seconds to maximize your score

### The Most Fun Moment
Bouncing through a tight cluster of same-color gems, building a big COMBO, then triggering SUPER BOUNCE that auto-collects everything on screen in a rainbow burst.

## Controls

| Action | Input |
|--------|-------|
| Move left | Arrow Left / A |
| Move right | Arrow Right / D |
| Start / Restart | Enter (KEY_RETURN) |

## Mechanics Reference

| Constant | Value |
|----------|-------|
| Screen | 320×240 |
| Colors | RED(8), GREEN(3), DARK_BLUE(5), YELLOW(10) |
| Bounce height | 80px |
| Super duration | 300 frames (5s) |
| Max gems | 12 |
| HEAT max | 100 |
| Timer | 3600 frames (60s) |
| COMBO threshold | 5 |

## Dev Status

- ✅ Auto-bounce physics + player movement
- ✅ Gem spawning, descent, sine wobble
- ✅ COMBO chain scoring with multiplier
- ✅ SUPER BOUNCE mode (rainbow, 3× score, auto-collect)
- ✅ HEAT risk system + screen shake
- ✅ 60s timer
- ✅ Particle + floating text feedback
- ✅ Title / Playing / Game Over screens
- ✅ 55 headless tests
- ✅ Ruff + ty checks pass

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/211_pogo_chain/main.py
```

## Tests

```bash
uv run python prototypes/211_pogo_chain/test_imports.py
```
