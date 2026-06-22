# PAINT SURGE — 148_paint_surge

**Paintball Arena Shooter** — first paintball/laser-tag genre in the collection.

## Source
Reinterpreted from game_idea_factory #1 (Score 32.15):
- Hook 1: "Log/replay as asset" → paint grid persists between rounds as ghost terrain
- Hook 2: "CA grid fills up" → paint splashes spread via cellular automaton

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single file: `main.py` (547 lines)

## Gameplay
Top-down arena shooter with color-match COMBO chain mechanics.

### Core Loop
1. Move with WASD, aim with mouse, shoot with left-click (0.3s cooldown)
2. Colored targets spawn from screen edges and drift inward
3. Hit same-color targets consecutively to build COMBO
4. COMBO >= 5 → SUPER SHOT (5s rainbow mode: all targets match, 3x score, auto-aim)
5. Paint splashes on grid, spreading via CA to adjacent empty cells
6. Player moves faster on own-color paint (1.3x), slower on others (0.7x)
7. Wrong-color hits add +15 HEAT, escaped targets add +5 HEAT
8. HEAT >= 100 = GAME OVER; survive 90s = VICTORY

### Risk & Reward
- Same-color COMBO chain → high score multiplier + SUPER SHOT
- Wrong-color hit → COMBO reset + HEAT buildup
- Paint terrain strategy: stay on own color for speed, or repaint areas

## Controls
| Input | Action |
|-------|--------|
| WASD | Move player |
| Mouse | Aim crosshair |
| Left-click | Shoot paintball |
| SPACE/Click | Start / Restart |

## Screens
1. **TITLE** — Game title, controls summary, ghost grid from previous round
2. **PLAYING** — Arena with paint grid, targets, HUD (score/combo/timer/HEAT bar)
3. **GAME_OVER** — Final score, max combo, retry prompt

## "Most Fun Moment" (面白い瞬間)
同じ色の的を連続で撃ち抜いてCOMBOが5に達し、SUPER SHOTが発動して虹色のペイント弾が自動照準で全方向に飛び交い、画面中の敵的が一掃される瞬間。

## Dev Status
- ✅ Core mechanic: 4-color COMBO chain + SUPER SHOT
- ✅ HEAT risk system with decay
- ✅ Paint grid with CA spread
- ✅ Terrain movement speed modifier
- ✅ Ghost grid persistence between rounds
- ✅ Particle effects + sound feedback
- ✅ Speed ramping difficulty
- ✅ 37 headless tests
- ✅ Web build deployed

## How to Run
```bash
cd ~/repos/game-prototypes
uv run pyxel package prototypes/148_paint_surge prototypes/148_paint_surge/main.py
uv run python prototypes/148_paint_surge/main.py  # requires X server
# Or open docs/148_paint_surge.html in browser
```
