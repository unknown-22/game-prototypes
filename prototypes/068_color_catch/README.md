# COLOR CATCH (068)

Color-match catcher game — the first catcher/arcade-collector prototype in the collection.

## Source
Reinterpreted from game_idea_factory idea #1 (Score 32.55):
- "ログ/リプレイが資産" → echo particles from previous catches
- "CAグリッド拡散" → objects proliferate and saturate the screen over time

## Engine
- Pyxel 2.x, 320×240, display_scale=2, FPS=30

## Core Mechanic
Move a catcher at the bottom to catch falling colored objects (4 colors).
- **Same-color consecutive catches** = COMBO multiplier (1 + combo × 0.5)
- **Different color catch** = COMBO resets to 1
- **Miss (object falls off screen)** = COMBO resets + MISS count +1
- **5 MISSES = GAME OVER**
- **COMBO ≥ 5 = SUPER CATCH** (5 seconds): catcher widens 2×, all catches auto-match, score ×3

## Controls
- LEFT/RIGHT arrows or A/D: Move catcher
- SPACE / RETURN: Start game / Restart

## The Most Fun Moment
「同色を狙い続けてCOMBOを積み、SUPER CATCHで一気に大量得点する爆発力」

## Risk/Reward
Chase same-color for high combo multiplier (high reward) vs. catch any color safely (low reward but avoids MISS). The tension between greed and safety drives every catch decision.

## Dev Status
- ✅ Core game loop (TITLE → PLAYING → GAME_OVER)
- ✅ 4-color object spawning with difficulty scaling
- ✅ COMBO system with SUPER CATCH mode
- ✅ Particle system for catches/misses
- ✅ HUD (score, combo, misses, super timer bar)
- ✅ Headless tests (30+ passing)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/068_color_catch/main.py
```
