# BULLSEYE CHAIN

**Color-match dart throwing with gravity arcs and chain combos.**

| Aspect | Detail |
|---|---|
| Source | game_idea_factory #1 (Score 31.8), reinterpreted |
| Hooks | "log/replay as asset" → ghost trails of previous throws; "gravity/collapse chain" → gravity-arc physics + COMBO chain burst |
| Engine | Pyxel 2.x, 256×256, display_scale=2 |
| Genre | Darts / target shooting (first in collection) |

## Core Mechanic

**"One-color-per-throw → build COMBO → trigger SUPER DART"**

Throw colored darts at colored targets. Same-color consecutive hits build COMBO for score multipliers. Wrong-color hits reset combo. COMBO ≥ 4 triggers SUPER DART (rainbow, auto-seeks nearest target, 3x score).

## Gameplay

- Throw darts by **click-drag-release**: drag away from the dart to set power and angle, release to throw
- Each dart follows a **gravity arc** (parabolic trajectory)
- Score points by hitting targets — higher value for smaller targets
- **Same-color hit** = COMBO +1, score = points × combo multiplier
- **Wrong-color hit** = COMBO reset to 0, base points only
- **COMBO ≥ 4** = SUPER DART activated (3 seconds, rainbow color, 3x multiplier)
- **Miss** = COMBO reset
- **Ghost trails** of your last 3 throws help you adjust aim
- **Predicted trajectory** shown during aim

## Controls

| Input | Action |
|---|---|
| Mouse drag | Aim dart (drag away from dart = throw direction) |
| Mouse release | Throw dart |
| SPACE | Cycle dart color (before throwing) |
| R | Retry (game over screen) |

## Scoring

| Target Tier | Radius | Points |
|---|---|---|
| BULL (bullseye) | 5px | 50 × combo |
| INNER (inner ring) | 9px | 25 × combo |
| OUTER (outer ring) | 13px | 10 × combo |

## Resource System

- **Darts**: 30 per round (darts remaining shown as `D:##`)
- **Timer**: 60 seconds (shown as `T:##`)
- **COMBO multiplier**: ×1 to ×N, resets on wrong color or miss
- **SUPER DART**: 3-second window, rainbow color, 3× score

## Dev Status

- ✅ Core mechanic: dart throwing with gravity arcs
- ✅ Color-match COMBO system
- ✅ SUPER DART rainbow mode
- ✅ Ghost trails (log/replay as asset)
- ✅ Target spawning with 3 tiers
- ✅ Particle effects on hit
- ✅ Floating score text
- ✅ Aim prediction line
- ✅ Power bar indicator
- ✅ HUD: score, combo, timer, darts, next color
- ✅ Game over + retry
- ⬜ Sound effects
- ⬜ Difficulty escalation (targets get smaller over time)
- ⬜ High score persistence

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/048_bullseye_chain/main.py
```
