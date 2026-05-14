# COLOR FLUX — One-Button Color-Matching Flyer

**Prototype 026** | Reinterpreted from game idea #1 (score 31.65)

## Source

Generated from `game_idea_factory` (2026-05-15 batch). All 10 generated ideas were dice/deckbuilder roguelites — all overlapped with existing prototypes. Per the reinterpretation protocol, the highest-scored idea (#1, 31.65) was reimagined into a **one-button flyer**:

- **"Effects synthesize and compress into 1 card"** → consecutive same-color gates build COMBO, reaching threshold triggers SYNTHESIS super-mode
- **"One color per turn"** → bird has one active color at a time; only matching-color gates build COMBO
- **"Heat and mana management"** → heat system (wrong colors + misses lead to overheat); score/combo as reward resource

## Engine

- **Pyxel** 2.x, 256×256, display_scale=3, 60 FPS
- Python 3.12 with type hints throughout

## Gameplay

### Core Mechanic

> **Flap through colored gates, matching your bird's color to build COMBO. Reach COMBO 5 to trigger SYNTHESIS — a super-mode where every gate auto-matches for 3x score.**

### The Most Fun Moment

> Hitting COMBO 4 and desperately flapping toward the next matching gate — one more and SYNTHESIS triggers, turning the screen gold and sending your score soaring.

### Rules

1. **Flap**: Press SPACE to keep the bird airborne. Gravity pulls you down constantly.
2. **Match Colors**: Fly through gates matching your active color to build COMBO. Each matching gate adds base score + combo bonus.
3. **Wrong Colors**: Passing through a non-matching gate resets COMBO and adds heat.
4. **Miss Gates**: Letting a gate pass off-screen without flying through it adds heat.
5. **SYNTHESIS** (COMBO ≥ 5): Enter super-mode for 2 seconds. All gates auto-match with 3x score multiplier. COMBO resets when synthesis ends.
6. **Heat Death**: Heat reaches 10 → game over.
7. **Collision Death**: Hitting a gate pillar, ceiling, or floor → game over.
8. **Color Shift**: Bird's active color changes periodically (~3 seconds).

### Risk/Reward

- **Risk**: Chasing matching-color gates may require dangerous positioning near pillars. Wrong-color gates are safer but kill your COMBO.
- **Reward**: High COMBO dramatically increases score per gate. SYNTHESIS mode multiplies everything by 3.

## Controls

| Input | Action |
|---|---|
| SPACE | Flap upward |
| SPACE (game over) | Restart |
| R (game over) | Restart |

## Element Reference

| Color | Pyxel Constant | Visual |
|---|---|---|
| RED | `COLOR_RED` | Red gates |
| GREEN | `COLOR_GREEN` | Green gates |
| YELLOW | `COLOR_YELLOW` | Yellow gates |
| CYAN | `COLOR_CYAN` | Cyan gates |

## Scoring

| Event | Points |
|---|---|
| Matching gate | 10 + COMBO × 5 |
| Wrong-color gate | 10 (flat, COMBO resets) |
| Synthesis gate | (10 + COMBO × 5) × 3 |
| Miss gate | 0 (+1 heat) |

## Dev Status

- ✅ Core flyer physics (gravity, flap, boundaries)
- ✅ Colored gate spawning with variable gaps
- ✅ Color-matching COMBO system
- ✅ SYNTHESIS super-mode (2s, 3x score, rainbow gates)
- ✅ Heat system with visual bar
- ✅ Particle effects (flap, score popups, death burst)
- ✅ Game over screen with stats
- ✅ Instant restart
- ✅ Background speed lines
- ✅ Synthesis visual overlay (pulsing border, flashing text)
- ⬜ Sound effects
- ⬜ Difficulty scaling (faster gates over time)
- ⬜ High score persistence

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/026_color_flux/main.py
```

## Headless Test

```bash
uv run python prototypes/026_color_flux/test_imports.py
```
