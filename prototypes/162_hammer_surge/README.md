# HAMMER SURGE (162)

## Source
Reinterpreted from game_idea_factory Idea #1 (Score 32.6 — 厄災封印/暴走制御 dice/bag roguelite)
- Hook "ログ/リプレイが資産" → ghost echo trails of previous 3 throws
- Hook "UIの連鎖演出で気持ちよさ" → COMBO chain → SUPER THROW

## Engine
- Pyxel 2.x, 320×240, display_scale=2

## 体験仮説
「COMBOを積むために同じ色のゾーンを精密に狙うか、HEATを避けて安全に投げるか」の判断が緊張を生み、SUPER THROW発動時のカタルシスが面白い。

## Gameplay
- **Core mechanic**: Arrow keys aim, SPACE hold = charge power, release = throw hammer
- **Landing zones**: 4 colored vertical zones on the right (RED/GREEN/BLUE/YELLOW)
- **Same-color hit**: COMBO +1, score multiplier increases
- **Wrong-color**: COMBO reset, HEAT +15
- **SUPER THROW**: COMBO ≥ 4 → 5s rainbow mode (auto-match, 3x score)
- **HEAT**: decays 0.02/frame, cap 100, ≥ 100 = game over (FOUL)
- **Rounds**: 15 throws total, each throw costs 1

## Controls
- LEFT/RIGHT: Adjust aim angle
- SPACE (hold): Build power (0 to 1 over ~0.8s)
- SPACE (release): Throw hammer
- SPACE (press): Start game / restart

## Dev Status
- ✅ Core mechanic: power-aim-throw loop
- ✅ Phase machine: TITLE → POWERING → FLYING → RESULT → GAME_OVER
- ✅ COMBO chain + SUPER THROW
- ✅ HEAT risk system
- ✅ Ghost echo trails
- ✅ Particle + floating text feedback
- ✅ Screen shake on SUPER activation
- ✅ 65 headless tests (all pass)
- ✅ ruff clean, ty clean
- ✅ Web build deployed

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/162_hammer_surge/main.py
```
