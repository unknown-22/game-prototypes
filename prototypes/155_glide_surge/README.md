# 155 GLIDE SURGE

## Source
Reinterpreted from game_idea_factory idea #1 (score 31.95): ダイス/バッグ構築ローグライト / 魔法学院（ルール改変）
- Hook "synthesis compression" → COMBO → SUPER GLIDE
- Hook "circuit/pipe visualization" → thermal columns as flow paths

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single file: main.py (~612 lines)

## Gameplay
Color-match hang glider side-scroller. Fly through colored thermal lift zones (RED/GREEN/BLUE/YELLOW). Same-color consecutive thermal entries build COMBO. COMBO ≥ 5 triggers SUPER GLIDE (rainbow mode, 2x score, no descent, auto-collect rings). Collect bonus rings. Avoid birds (add heat). Heat ≥ 100 triggers TURBULENCE (screen shake, knockback). Altitude = life — hit ground = game over.

### Core Mechanic
1. Glider descends slowly (gravity). Auto-scroll right.
2. Thermal columns rise from bottom — enter match-color thermals to gain altitude and COMBO.
3. COMBO ≥ 5 → SUPER GLIDE (5s rainbow, 2x score, no descent, immune to heat, auto-collects rings).
4. Wrong-color thermal → COMBO=0, HEAT+15.
5. Bird collision → HEAT+20.
6. HEAT ≥ 100 → TURBULENCE (2s shake, knockback, combo reset, heat reset).
7. Player color cycles every 3 seconds.
8. Game over when altitude reaches ground.

## Controls
- Arrow keys / WASD: Fly (4-directional)
- SPACE / RETURN: Start / Restart

## Resources
- Altitude: Player Y position (0 = top, ground = game over)
- Heat: 0-100 (triggers TURBULENCE at 100)
- COMBO: 0+ (resets on wrong color or turbulence)
- Score: Points from thermals (100 × combo) and rings (50)

## Risk/Reward
- Chaining same-color thermals → higher COMBO → higher score per thermal
- COMBO ≥ 5 → SUPER GLIDE (massive score potential, 2x)
- Wrong color → combo reset + heat (risk of turbulence)
- Birds → instant heat + particle loss

## Most Fun Moment (面白い瞬間)
同じ色の上昇気流を次々に掴んでコンボを伸ばし、SUPER GLIDEが発動して一気に高度を稼ぎ、大量のリングを吸い込む瞬間。

## Dev Status
- ✅ Core mechanic: thermal collision, COMBO, SUPER GLIDE
- ✅ Heat system + TURBULENCE
- ✅ Ring collection (normal + super auto-collect)
- ✅ Bird obstacles
- ✅ Mountain terrain
- ✅ Particle effects
- ✅ Screen shake
- ✅ 3 screens: TITLE, PLAYING, GAME_OVER
- ✅ 60 headless tests (all pass)
- ✅ ruff + ty clean
- ✅ Web build

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/155_glide_surge/main.py
```

## How to Test
```bash
uv run python prototypes/155_glide_surge/test_imports.py
```
