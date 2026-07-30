# ALPINE CHAIN (261)

## Source
Reinterpreted from game_idea_factory Idea #2 (Score 31.4):
- "ログ/リプレイが資産（前回の行動が次回のカードになる）" → ghost trail best-run display
- "数値が『分裂』して複数経路に飛び、最終的に合流して爆発する" → split gate lanes → COMBO chain → SUPER SKI

## Engine
Pyxel 2.x, 320×240, 30fps

## Experience Hypothesis
「ギリギリまで待って同色のゲートを連続でくぐり抜け、COMBOが爆発してSUPER SKIに突入する瞬間が気持ちいい」

## Core Loop
1. Player (skier) auto-scrolls down the slope
2. Colored gates approach from above
3. Arrow keys to move left/right to pass through matching-color gates
4. Same-color consecutive passes = COMBO chain (score = 100 × combo)
5. COMBO≥4 = SUPER SKI (300f rainbow, any-color match, 3x score, HEAT frozen)
6. Wrong color = COMBO reset + HEAT+15 + screen shake
7. Miss gate = COMBO reset + HEAT+5
8. HEAT≥100 = WIPEOUT (game over)
9. 60s timer → game over, saves ghost trail if new best score

## Controls
- Arrow keys: Move skier (LEFT/RIGHT/UP/DOWN, speed 3.0 px/f)
- SPACE/RETURN: Start/restart

## Risk & Reward
- Match same color → build COMBO for high score + SUPER SKI
- Wrong color / miss → COMBO reset + HEAT buildup
- Higher speed over time → harder to navigate, higher scoring potential

## Status
- ✅ Title screen with high score display
- ✅ Playing screen with COMBO chain, SUPER SKI, ghost trail
- ✅ Game over screen with score/combo display
- ✅ HEAT risk system (decay, mismatch, miss)
- ✅ Difficulty escalation (scroll speed + spawn rate)
- ✅ 14 headless tests
- ✅ ruff + ty all pass
- ✅ Web build (docs/261_alpine_chain.html)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/261_alpine_chain/main.py
```

## If Making Improvements
- Add split gates (two gates at same Y, one left one right — pass through both for super combo)
- Add obstacles (trees, rocks) to dodge
- Add sound effects (whoosh for gate pass, crunch for mismatch)
- Add visual slope gradient / parallax background
- Add slalom pole flags animation
