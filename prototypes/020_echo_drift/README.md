# ECHO DRIFT — Grid Racer Prototype

**Prototype #020** — Top-down grid-based racer with echo trail mechanics.

## Source

Reinterpreted from game idea #1 (score 32.15, generated 2026-05-13):
- Original: auto-shooter / power plant overload with cellular automaton grid
- Hooks repurposed: "log/replay as assets" → echo trail coloring, "CA grid fills up" → trail becomes volatile and spreads, "overload/discharge" → heat management + screen clear

**Genre gap**: No racing prototype existed in the collection (all 19 prior prototypes were deckbuilder/dice/auto-shooter/puzzle/TD/platformer/snake/shooter variants).

## Engine

- **Pyxel** 2.x
- Screen: 256×256, display_scale=3
- 30 FPS
- Python 3.12+ with full type hints

## Gameplay

**The Most Fun Moment**: Threading the needle at high combo, color-matching your own echo trail for chain multipliers, then discharging just before the volatile track consumes you.

### Core Mechanic

Drive a car on a closed oval track grid (16×16 cells). Each cell you leave behind gets colored with your car's current elemental affinity. When you re-enter a colored cell:

- **SAME color** → **COMBO!** Score multiplier increases, speed boost, particles erupt
- **DIFFERENT color** → **CLASH!** Lose 1 HP, combo resets, screen shakes

Combos build **HEAT**. When heat exceeds the volatile threshold (80%), all colored trail cells become **VOLATILE** — they damage you regardless of color matching.

**DISCHARGE** (D key) clears all heat and resets the entire trail, but has a 1-second cooldown.

### Resources

| Resource | Description |
|---|---|
| **HP** (5 max) | Lost on clashes and volatile cells. Game over at 0. |
| **Heat** (0-100) | Builds from combos. High heat makes trail volatile. Decays slowly. |
| **Combo** | Consecutive same-color matches. Multiplies score per match. |
| **Score** | Distance + combo bonuses + lap bonuses |

### Risk & Reward

- **Keep combo going** → huge score but builds heat dangerously fast
- **Discharge early** → safe but resets all trail progress and combo
- **Ride the edge** → stay just below volatile threshold for maximum efficiency
- **Lap bonus**: +100 per completed lap

### Difficulty Scaling

- Heat builds faster at higher combo levels (combo × 0.5 extra heat per match)
- Color auto-rotates every 3 seconds — must adapt or clash
- After discharge, you must rebuild trail from scratch while heat decays

## Controls

| Key | Action |
|---|---|
| ↑ ↓ ← → | Move one cell in that direction (also changes facing) |
| **D** | DISCHARGE — clear heat and trail (1s cooldown) |
| **R** | Restart (on game over screen) |
| **Q** | Quit |

## Visual Feedback

- Element-colored trail cells on the track
- Pulsing VOLATILE cells (purple ↔ red flash)
- Combo glow border on car (at combo ≥ 3)
- Particle bursts on combos, clashes, and discharge
- Floating score/combo text (+bonus, COMBO xN)
- Screen shake on clashes
- Heat bar with color change at volatile threshold
- Blinking "VOLATILE!" warning

## Dev Status

- [x] Grid track with 4-directional movement
- [x] Echo trail coloring (4 elements)
- [x] Same-color COMBO system with score multiplier
- [x] CLASH damage system
- [x] HEAT accumulation from combos
- [x] VOLATILE trail conversion at high heat
- [x] DISCHARGE mechanic with cooldown
- [x] Lap detection and bonus
- [x] Auto color cycling (3s interval)
- [x] Particle system (combo/clash/discharge bursts)
- [x] Floating text feedback
- [x] Screen shake
- [x] HP system with heart display
- [x] Score tracking with max combo
- [x] Game over screen with stats
- [x] Instant restart
- [x] Headless import tests
- [ ] Speed tiers based on combo (visual only currently)
- [ ] Sound effects (Pyxel BGM/SE)
- [ ] Multiple track layouts
- [ ] Enemy AI racers

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/020_echo_drift/main.py
```

## Headless Testing

```bash
uv run python prototypes/020_echo_drift/test_imports.py
```
