# HOOK CHAIN (034_hook_chain)

Color-match fishing combo game — time your strikes to chain same-colored fish catches.

## Source

- **Generated**: 2026-05-17 from `game_idea_factory` (seed timestamp-based)
- **Original idea**: #1 (score 32.0) — Deckbuilder roguelite / Logistics flow optimization
- **Reinterpretation**: All 10 generated ideas clustered in deckbuilder/dice/auto-shooter genres. Reinterpreted into **fishing** (genre #28, first in collection):
  - "Synthesis compression" → same-color consecutive catches build COMBO → SUPER CATCH at combo 3+
  - "Chain visualization across screen" → combo meter + particle bursts + floating score text
  - "Flow optimization" → choose which color to target, manage heat/cooldown timing

## Engine

- Pyxel 2.x, 256×240, display_scale=2, 60 FPS

## Gameplay

**Objective**: Score as many points as possible in 90 seconds by catching fish and building same-color combos.

### Core Mechanic: Color-Match Chain Fishing

1. **Move hook**: UP/DOWN (or W/S) to position the hook vertically in the water
2. **Select color**: Keys 1-4 or mouse scroll wheel to choose target color
3. **Strike**: SPACE or Z to cast the line — catches the nearest fish within 50px range
4. **Combo**: Catching same-color fish consecutively builds COMBO (×1.5 multiplier per level)
5. **SUPER MODE**: COMBO ≥ 3 unlocks SUPER mode (5s rainbow hook, auto-catches ALL fish of caught color)
6. **MEGA SUPER**: COMBO ≥ 6 doubles SUPER duration

### Resources

| Resource | Max | Description |
|---|---|---|
| HEAT | 100 | +14 per cast. At 100, overheat = 2s cooldown (no casting). Regenerates slowly. |
| TIMER | 90s | Game over when timer expires |
| COMBO | ∞ | Consecutive same-color catches. Resets on miss or wrong color |

### Risk/Reward

- **Chase the combo**: Stick with one color for big multipliers, but one wrong catch resets it
- **Super gamble**: Build to combo 3 for SUPER mode, but heat builds with every cast
- **Golden fish**: Rare (8%), worth 2× base score — always worth chasing

### Scoring

- Matching color catch: 100 × combo_multiplier (combo 1 = 1×, combo 3 = 2×, combo 5 = 3×)
- Wrong color catch: 50 (resets combo, changes target color)
- Golden fish: 2× base score
- SUPER mode: 200 × combo × min(combo, 5)
- SUPER auto-catch bonus: 100 per extra fish

## Controls

| Input | Action |
|---|---|
| UP / DOWN (W/S) | Move hook vertically |
| SPACE / Z | Cast line |
| 1 / 2 / 3 / 4 | Select target color (RED/BLUE/GREEN/YELLOW) |
| Mouse wheel | Cycle target color |
| R / SPACE (game over) | Restart |
| SPACE / Click (title) | Start game |

## Color Reference

| Color | Key | Pyxel Color |
|---|---|---|
| RED | 1 | COLOR_RED (8) |
| BLUE | 2 | COLOR_DARK_BLUE (5) |
| GREEN | 3 | COLOR_GREEN (3) |
| YELLOW | 4 | COLOR_YELLOW (10) |

## Dev Status

- ✅ Core hook movement and fish spawning
- ✅ Color-match catch + combo system
- ✅ SUPER mode at combo ≥ 3 (rainbow hook + auto-catch)
- ✅ MEGA SUPER at combo ≥ 6 (2× duration)
- ✅ HEAT/overheat cooldown mechanic
- ✅ 90-second timed run
- ✅ Golden fish (rare, double score)
- ✅ Floating score popups + particle effects
- ✅ Fish rendering with directional sprites
- ✅ Title screen + game over screen with stats
- ✅ Difficulty scaling (faster spawns over time)
- ✅ 36 headless logic tests
- ✅ ruff + ty clean
- ⬜ Sound effects (SE)
- ⬜ Background music
- ⬜ High score persistence
- ⬜ Fish depth variation (sine wave swimming)
- ⬜ Multiple hook types / upgrades

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/034_hook_chain/main.py
```

## How to Test

```bash
uv run python prototypes/034_hook_chain/test_imports.py
```
