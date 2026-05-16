# 033 — Resonance Chain

**Rhythm-action game with colored note chain reactions.**

## Source

Based on game_idea_factory output (Score 32.2): "UI chain collapse effects + hit/combo chain visualization" hooks reinterpreted into a rhythm game genre — the first rhythm prototype in the collection.

## Engine

- Pyxel 2.x
- Screen: 256×240
- 4 lanes, keyboard input

## Gameplay

Colored notes fall in 4 lanes toward a timing zone at the bottom. Press the matching key (Z/X/C/V) when notes reach the hit zone.

### Core Mechanic: Resonance Chain

Consecutive hits on the **same lane** (same color) build a **resonance counter**:
- **1-2 hits**: Normal scoring
- **3+ hits**: 2x score multiplier
- **5+ hits**: 3x multiplier + **chain clear** — all active notes of that color are automatically cleared for bonus points

Misses reset both combo and resonance, creating a risk/reward loop: stay on one lane for chain clears, or switch lanes for variety.

### Scoring

- **PERFECT** hit (±10px): 20 base × multiplier
- **GOOD** hit (±25px): 10 base × multiplier
- Combo multiplier: +1x per 10 consecutive hits
- Resonance multiplier: 2x at 3+, 3x at 5+
- Chain clear bonus: 50pts per auto-cleared note

### Rules

- 5 health hearts — each miss loses 1
- Game over at 0 health
- Difficulty increases over time (faster notes, more frequent spawns)
- Max ~60 seconds before difficulty maxes out

## Controls

| Key | Lane |
|-----|------|
| Z | Red (left) |
| X | Blue |
| C | Green |
| V | Yellow (right) |
| Space | Start / Restart |
| Mouse click | Start / Restart |

## Dev Status

- ✅ Core note falling + hit detection
- ✅ PERFECT/GOOD timing windows
- ✅ Combo system
- ✅ Resonance chain (same-color streaks)
- ✅ Chain clear at threshold
- ✅ Particle effects + floating text feedback
- ✅ Health system + game over
- ✅ Difficulty scaling
- ✅ Title screen + restart
- ✅ 25 headless tests
- ✅ ruff + ty clean

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/033_resonance_chain/main.py
```

On Windows: run directly. On WSL: `export DISPLAY=:0` first.

## How to Test

```bash
uv run python prototypes/033_resonance_chain/test_imports.py
```
