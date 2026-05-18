# CHAIN CROSS — Color-match traffic intersection manager

**Source**: Reinterpreted from game_idea_factory #1 (score 32.35)
- Original: Dice/bag-building roguelite / Space mining
- Hooks reinterpreted: "synthesis compression" → batch same-color clear; "CA grid spread" → congestion heat

**Engine**: Pyxel 2.x, 240×240, display_scale=2, 60fps

## Gameplay

You manage a 4-way traffic intersection. Colored cars approach from all 4 directions.
Your job: change the signal light color to match the approaching cars so they pass safely.

### Core mechanic

- **Match**: Same-color car passes safely → score + COMBO
- **Crash**: Wrong-color car hits intersection → lose HP, reset COMBO
- **COMBO ≥ 3**: Activates **SUPER CLEAR** (2 seconds, 3x score, rainbow signal)
- **Heat (CA spread)**: Crashes increase congestion heat; high heat spawns MORE cars faster

### Rules

- 5 colors: RED, BLUE, GREEN, YELLOW, PURPLE
- Each safe passage: `10 × COMBO × (3 if SUPER else 1)` points
- Each crash: -1 HP, COMBO resets to 0
- HP starts at 5, game over at 0

## Controls

| Key | Action |
|-----|--------|
| `1`/`Q` | Set signal to RED |
| `2`/`W` | Set signal to BLUE |
| `3`/`E` | Set signal to GREEN |
| `4`/`R` | Set signal to YELLOW |
| `5`/`T` | Set signal to PURPLE |
| `R` (game over) | Retry |

## Dev Status

- [x] Core intersection mechanics
- [x] 5-color signal system
- [x] COMBO chain scoring with multiplier
- [x] SUPER CLEAR mode (combo ≥ 3, 2s duration)
- [x] Heat/congestion system (CA spread reimagined)
- [x] Particle effects (pass/crash/super bursts)
- [x] Floating score/combo text
- [x] Screen shake on crash
- [x] HUD: score, combo, max combo, HP, heat bar
- [x] Game over screen with retry

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/040_chain_cross/main.py
```
