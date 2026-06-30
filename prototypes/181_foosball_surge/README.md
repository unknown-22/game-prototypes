# FOOSBALL SURGE (#181)

Top-down table football with color-match COMBO chains.

## Source
Reinterpreted from Game Idea Factory Idea #1 (Score 32.75): "synthesis compression + CA grid fills up" hooks → foosball sports genre.

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single file: `main.py` (626 lines)

## Gameplay

Two teams face off across a foosball table with 4 vertical rods (2 per side). Each rod carries 3 figures that share a color. Hit the ball with same-color figures consecutively to build COMBO. At COMBO≥4, trigger SUPER SHOT — an unstoppable rainbow ball worth 3x points.

### Core Mechanics
- **Color-match COMBO**: Ball takes the color of the last figure it hit. Same-color consecutive hits → COMBO+1. Different color → COMBO reset + HEAT+15.
- **SUPER SHOT**: COMBO≥4 activates SUPER (180 frames): ball speed ×2, rainbow trail, 3x score on goal.
- **HEAT system**: Different-color hits add HEAT. HEAT≥100 → game over.
- **Goal scoring**: Base 100 pts, 300 during SUPER. First to 5 goals wins.
- **Rod color cycling**: Rod colors shift after each goal (keeps the match dynamic).

### 面白い瞬間 (Most Fun Moment)
同色のフィギュアで連続ヒットを決めてCOMBOを4まで積み上げ、SUPER SHOTが炸裂して虹色のボールが超高速で相手ゴールに突き刺さり、スコアが3倍に跳ね上がる瞬間。

## Controls
- **W / S**: Move defense rod up/down
- **↑ / ↓**: Move forward rod up/down
- **ENTER**: Start game / Restart

## Dev Status
- ✅ Core foosball physics (ball bounce, wall/goal detection, figure collision)
- ✅ Color-match COMBO chain
- ✅ SUPER SHOT mechanic
- ✅ HEAT system
- ✅ AI opponent with jitter tracking
- ✅ Particle system (hit, goal, SUPER)
- ✅ Floating text feedback
- ✅ Screen shake on goals/SUPER
- ✅ 3 screens: Title, Playing, Game Over
- ✅ 70 headless tests
- ✅ Web build deployed to docs/

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/181_foosball_surge/main.py
```

## Tests
```bash
uv run pytest prototypes/181_foosball_surge/test_imports.py -v
```
