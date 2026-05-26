# SPLIT BARRAGE (069_split_barrage)

## Source
Reinterpreted from game_idea_factory idea #1 (Score 32.0): alchemy deckbuilder
- Hooks: "split into multiple paths → converge → explode" + "synthesis compression"
- Reinterpreted into: split-converge artillery with color-match chain explosions

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Python 3.12+

## Gameplay
A color-match artillery game:
1. **AIM**: Click-drag on cannon to set angle (vertical drag) and power (horizontal drag)
2. **FIRE**: Release to launch projectile in parabola
3. **SPLIT**: Click mid-air to burst into 5-7 colored fragments (RED/ORANGE/YELLOW/CYAN)
4. **LAND**: Fragments fall with gravity onto a 16×5 grid
5. **EXPLODE**: When 3+ same-color fragments are adjacent → BFS chain explosion
6. **CHAIN**: Gravity compaction after each clear may trigger new clusters → recursive chain combo
7. **SCORE**: Points = cluster_size² × combo_multiplier × 10

## Controls
| Action | Input |
|--------|-------|
| Aim (angle + power) | Click-drag on cannon area |
| Fire | Release mouse |
| Split (mid-air) | Click anywhere while projectile is flying |
| Start / Restart | Click |

## Core Mechanic
The "most fun moment": 砲弾をベストなタイミングで分裂させ、色付き破片が降り注いで同色同士の連鎖爆発が連続するカタルシス。

### Risk & Reward
- **High power** → more fragments (7) but wider spread → harder to cluster same colors
- **Low power** → fewer fragments (5) but tighter grouping → easier same-color convergence
- **Early split** → wide spread → low cluster chance
- **Late split** → tight grouping → high cluster chance but risk of missing entirely
- **Same-color chain** → combo multiplier (×1.0 → ×1.5 → ×2.0 → ...)
- **Different color** → combo resets → lost multiplier

## Dev Status
- ✅ Title screen
- ✅ Aiming with trajectory preview
- ✅ Parabolic flight + gravity
- ✅ Mid-air split into colored fragments
- ✅ Grid landing with gravity fill (bottom-up per column)
- ✅ BFS cluster detection (4-direction, min 3)
- ✅ Chain reaction with gravity compaction
- ✅ Combo scoring with multiplier
- ✅ Particle effects (explosions, combo text)
- ✅ Game over + restart
- ✅ 50 headless tests (ruff/ty/pytest all pass)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/069_split_barrage/main.py
```

## Test
```bash
uv run pytest prototypes/069_split_barrage/test_imports.py -v
```
