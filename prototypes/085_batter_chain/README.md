# BATTER CHAIN — Baseball Batting Game (Prototype 085)

## Source
Game idea #1 (score 31.95) from 2026-05-30 generation.
Theme: Hacking/circuit/log → reinterpreted as baseball batting.
Hooks: synthesis/compression → color-match COMBO, circuit/pipe visualization → ball trail.

## 体験仮説 (Experience Hypothesis)
「ピッチャーの投げる色を見極め、ギリギリまで引きつけて同色COMBOを決め、SUPER HITでホームランをかっ飛ばす瞬間に、判断成功による快感とスコア爆発のカタルシスを感じる」

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single file: main.py (932 lines)

## Gameplay — Core Mechanic
1. Pitcher throws balls with colored trails (RED/GREEN/BLUE/YELLOW)
2. Click when ball crosses the plate to swing
3. Same color as active COMBO → COMBO +1, high score multiplier
4. COMBO ≥ 3 → **SUPER HIT** (home run, massive score burst, particles, screen shake)
5. Different color → FOUL (combo resets to 1 with new color)
6. Miss or let ball pass → STRIKE
7. 3 strikes or 10 pitches → GAME OVER

## Risk/Reward
- **Wait for right color** → high COMBO multiplier but risk STRIKES
- **Swing at anything** → safe from strikes but lower score
- **Close to center timing** → higher timing bonus score

## Controls
- Mouse click: Swing bat / Start game / Restart
- Keyboard: ENTER (same as click for title/game over)

## Game Screens
1. **TITLE**: Game title, instructions, HIGH SCORE
2. **GAME**: Field with pitcher, batter, pitch ball with colored trail, strike zone, UI (score/combo/strikes/pitches)
3. **GAME OVER**: Final score, max combo, HIGH SCORE, retry prompt

## Dev Status
- ✅ Core mechanic: color-match COMBO → SUPER HIT
- ✅ Phase machine: TITLE → WINDUP → PITCH → RESULT → GAME_OVER
- ✅ Particle system: hit, super, strike particles
- ✅ Floating text system: score popups, SUPER indicator
- ✅ Screen shake for SUPER HIT
- ✅ Difficulty scaling (pitch speed increases per pitch)
- ✅ Timing bonus (closer to center = higher score)
- ✅ Headless tests: 42 tests passing
- ✅ Web build (docs/085_batter_chain.html)
- ✅ ruff + ty checks passing
- ⬜ Sound effects (structure in place)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/085_batter_chain/main.py
```

## How to Test
```bash
uv run python prototypes/085_batter_chain/test_imports.py
```

## What's Working Well
- Clean hit zone detection with timing bonus
- SUPER HIT feels impactful (particles + shake + score burst)
- COMBO/FOUL mechanic creates real risk/reward decisions
- Rising pitch speed provides natural difficulty curve
- Code structure: dataclasses, Enum phases, separated logic from rendering

## Next Improvement
- Sound effects for hit/miss/SUPER
- Pitch variety (curve balls, speed changes)
- Animated pitcher windup variations
- Hit direction based on timing (pull vs opposite field)
