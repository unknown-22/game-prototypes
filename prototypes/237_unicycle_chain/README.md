# UNICYCLE CHAIN (237)

Side-view unicycle physics-balance color-match COMBO chain game.

## Source
Reinterpreted from game_idea_factory idea #1 (Score 31.85): "発電所（過負荷と放電）デッキ構築"
- "ログ/リプレイが資産" → ghost trail showing best balance run
- "未来の手札を消費" → STAMINA system (aggressive pedaling drains future stability)

## Experience Hypothesis (体験仮説)
「ギリギリのバランスで連続コンボを決めてSUPER BALANCEが発動し、無敵状態でリングを次々に通過してスコアが爆発的に伸びる瞬間」が面白い。

## Core Loop
1. LEFT/RIGHT keys to balance unicycle (physics-based tilt with gravity)
2. Colored rings (RED/LIME/DARK_BLUE/YELLOW) scroll from right
3. Pass through same-color ring consecutively → COMBO chain
4. COMBO>=4 → SUPER BALANCE (300f rainbow mode: auto-balance, any-color match, 3x score)
5. UP key pedals fast (drains STAMINA, speed 1.3x)
6. Manage HEAT (mismatch +15, fall +25, decay 0.02/f) and STAMINA (100 max)

## Controls
- LEFT/RIGHT: Balance tilt
- UP: Aggressive pedaling (drains stamina, boosts speed)
- SPACE: Start / Restart

## Engine
- Pyxel 2.x, 320×240, display_scale=2

## Dev Status
- ✅ Single-file main.py (637 lines)
- ✅ Physics-based tilt balance with gravity
- ✅ Color-match COMBO chain (4 colors)
- ✅ SUPER BALANCE at COMBO>=4 (300f rainbow, 3x score)
- ✅ STAMINA system (drain/recharge, low-stamina penalty)
- ✅ HEAT risk (mismatch, fall, decay)
- ✅ Fall detection (tilt>0.55 for 30f → fall +25 heat)
- ✅ Ghost trail (best-run tilt history)
- ✅ Difficulty escalation (speed, spawn interval, color cycle)
- ✅ Particle system, floating text, screen shake
- ✅ 79 headless tests (all pass)
- ✅ ruff + ty clean
- ✅ English-only text

## What Works Well
- Physics tilt creates genuine skill-based balance challenge
- Multi-layer risk: color matching + stamina management + balance
- Ghost trail provides clear improvement feedback
- SUPER BALANCE as satisfying power spike

## Next Improvements
- Add sound effects (pyxel.play)
- Tweak balance physics constants based on playtesting
- Add visual polish (rider animation, background scenery)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/237_unicycle_chain/main.py
```
