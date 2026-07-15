# 238 — LIFT CHAIN

## Source
Reinterpreted from game_idea_factory #1 (Score 32.0: デッキ構築ローグライト / 宇宙採掘).
Hooks: 「合成圧縮」(synthesis compression) → COMBO chain, 「落下/重力で連鎖崩壊」(gravity/collapse chain) → barbell physics.

## Engine
- Pyxel 2.x, 320×240
- Python 3.12+

## Gameplay — Core Mechanic
**Weightlifting (Clean & Jerk)** with color-match COMBO chain.

1. Hold SPACE to build power (power meter: GREEN→YELLOW→RED)
2. Release SPACE to execute the lift — barbell launches upward with physics
3. Barbell rises with initial velocity, gravity pulls it back down
4. If barbell crosses LIFT_LINE (y=75) = successful lift
5. Match barbell plate color with attempt color → COMBO increments, score = 10 × combo
6. Mismatch resets COMBO, adds HEAT
7. COMBO >= 4 triggers **SUPER LIFT** (300f rainbow mode, auto-lift, any-color match, 3x score)
8. 60-second challenge with escalating difficulty

## Controls
| Key | Action |
|-----|--------|
| SPACE (hold) | Build power |
| SPACE (release) | Execute lift |
| SPACE / R | Restart from Title/Game Over |

## Risk & Reward
- **Same-color COMBO** → high scores + SUPER LIFT (3x multiplier)
- **Mismatch** → HEAT+10, COMBO reset
- **Missed lift** → HEAT+15, COMBO reset
- **HEAT >= 100** → Game Over
- Timer runs out → Game Over

## Dev Status
- ✅ Core game loop (power → lift → resolve)
- ✅ COMBO chain + SUPER LIFT
- ✅ HEAT risk system
- ✅ 60s timer + difficulty escalation
- ✅ 3 screens (Title/Playing/Game Over)
- ✅ Particle system + floating text
- ✅ 46 headless tests
- ✅ ruff + ty clean

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/238_lift_chain/main.py
```

## Run Tests
```bash
uv run pytest prototypes/238_lift_chain/test_imports.py -v
```
