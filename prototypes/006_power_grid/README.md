# Power Grid — Overload Chain Prototype

**Source**: Game Idea Factory run 2026-05-10, Idea #6 (Score 31.15)
**Theme**: Power Plant (overload/discharge)
**Engine**: Pyxel 2.x, 400×300, display_scale=2

## Core Mechanic

> **"Manage 3 generators. Push heat to critical levels to trigger chain overloads — the most fun moment is when all 3 reactors explode in sequence, multiplying your score."**

- 3 generator slots (Reactor A, Turbine B, Solar C) with different output/heat profiles
- Play cards from hand to boost power output or manage heat
- When heat exceeds overload threshold, generator OVERLOADS — dealing burst damage that chains to neighbors
- Chain multiplier increases with each successive overload

## Rules

| Aspect | Detail |
|---|---|
| Turns | 12 turns to survive |
| Cards per turn | 4 randomly drawn |
| Power demand | Starts at 30, increases +5/turn |
| HP | Start 100, lose HP from unmet demand and overload damage |
| Win condition | Survive all 12 turns |
| Lose condition | HP reaches 0 |
| Score | Total power produced × chain multiplier |

## Cards

| Card | Abbr | Effect |
|---|---|---|
| Fuel Rod | FUL | +15 power, +25 heat |
| Coolant | COL | -30 heat |
| Boost | BST | +5 power, ×1.5 output, +15 heat |
| Surge | SRG | +25 power, +10 heat |
| HeatDump | DMP | Convert heat→power, -20 heat |
| Vent | VNT | -5 heat to ALL generators |

## Controls

- **Mouse click**: Select a card, then click a generator to assign it
- **TICK button**: Skip remaining cards and resolve turn
- **SPACE / R**: Retry after game over

## Generators

| Generator | Base Output | Overload Threshold | Character |
|---|---|---|---|
| Reactor A | 10 | 100 | High output, high capacity |
| Turbine B | 8 | 80 | Balanced |
| Solar C | 5 | 60 | Low output, overloads fast |

## Dev Status

- [x] Core game loop (draw → play → resolve → demand → end turn)
- [x] Card system (6 types with distinct effects)
- [x] Overload chain mechanic (propagation to adjacent generators)
- [x] Heat visualization (color-coded bars)
- [x] Particle effects on overload
- [x] Power demand system with scaling difficulty
- [x] Score with chain multiplier
- [x] HP system with defeat condition
- [x] Fast restart (SPACE to retry)
- [ ] Sound effects (pyxel built-in)
- [ ] Card hover tooltips
- [ ] Boss encounters
- [ ] Generator upgrade system

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/006_power_grid/main.py
```
