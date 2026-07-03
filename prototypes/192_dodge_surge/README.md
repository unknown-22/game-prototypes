# 192_dodge_surge — DODGE SURGE

## Source
Generated from game_idea_factory batch (2026-07-03), Idea #1 (score 32.55).
Hooks reinterpreted: "log/replay as asset" → ghost ball trails, "CA grid fills up" → danger zone spread on court.
Genre: Dodgeball (first dodgeball prototype in collection).

## Engine
Pyxel 2.x, 320x240, display_scale=2, 60fps.

## Gameplay
Top-down dodgeball court. Player moves on bottom half, catching colored balls and throwing them at 3 AI opponents on the top half.

### Core Mechanic
**Same-color consecutive catches build COMBO chain → SUPER THROW at COMBO≥4.**

Catching a ball updates your held color. Catching the same color again increments COMBO. Different colors reset COMBO to 1. At COMBO≥4, SUPER THROW activates: rainbow ball, auto-aim at all opponents, 3x score for 5 seconds.

### Risk & Return
- Catching same-color balls = high COMBO = high score + SUPER THROW
- Getting hit by opponent balls = HEAT +15 + COMBO reset
- HEAT >= 100 = game over (heat decays 0.05/frame)
- CA danger zones spread on the court from ball bounces — standing on them slows you down
- Difficulty increases every 15s: opponents throw faster and gain more HP

### Scoring
- Catch: `10 * (1 + combo * 0.5) * (3 if SUPER else 1)`
- Eliminate opponent: `100 * (1 + combo * 0.5) * (3 if SUPER else 1)`

## Controls
- **Arrow Keys / WASD**: Move player
- **SPACE**: Throw held ball at nearest opponent
- **ENTER**: Start / Restart

## Color Reference
| Key | Color | Gameplay |
|-----|-------|----------|
| Any catch | RED (8) | Ball/COMBO color 1 |
| Any catch | GREEN (3) | Ball/COMBO color 2 |
| Any catch | DARK_BLUE (5) | Ball/COMBO color 3 |
| Any catch | YELLOW (10) | Ball/COMBO color 4 |

## Dev Status
- [x] Core catch/throw mechanics
- [x] COMBO chain system
- [x] SUPER THROW auto-aim mode
- [x] HEAT risk system
- [x] CA danger grid with spread
- [x] Ghost ball trails
- [x] 3 AI opponents with throw AI
- [x] Difficulty scaling
- [x] Particle system + floating text
- [x] Screen shake
- [x] 3 screens (Title/Playing/GameOver)
- [x] 54 headless tests (all pass)
- [x] Web build
- [x] ruff + ty clean

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/192_dodge_surge/main.py
```

## How to Test
```bash
uv run pytest prototypes/192_dodge_surge/test_imports.py -v
```
