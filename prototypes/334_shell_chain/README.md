# 334 — Shell Chain

**Shell Game / Color Tracking** — 320×240, Pyxel 2.x

## Concept
A Shell Game (three-cup monte) with color tracking. Cups lift to reveal colored balls, shuffle positions, then lower. You must remember which color sits under which cup and guess correctly.

## 面白い瞬間
カップの位置を追い、色を当て、同じ色が連鎖して一気に開いていく——「追えていた！」というカタルシスと連鎖の気持ちよさ。

## Core Mechanic
1. **SHOW**: cups lift, ball colors visible
2. **SHUFFLE**: cups swap positions randomly
3. **GUESS**: click a cup, press 1-4 to guess its color
4. **MATCH**: correct → combo+1, score, cup reveals → **CHAIN BURST** (BFS reveals adjacent same-color cups)
5. **COMBO≥4**: SUPER VISION (5s rainbow auto-match, 3x score, HEAT frozen)
6. **MISMATCH**: wrong color → HEAT+15, combo reset, ball color randomizes
7. All cups revealed → bonus +100×combo, cup count increases

## Controls
| Input | Action |
|---|---|
| 1/2/3/4 | Select guess color (RED/LIME/DARK_BLUE/YELLOW) |
| Mouse click | Select a cup |
| Mouse wheel | Cycle cup selection |
| ENTER | Start / Restart |

## Risk/Reward
- Track more cups for higher combo potential, but shuffle gets faster and colors multiply
- SUPER VISION rewards precision with a 5s auto-match power window
- HEAT accumulates on wrong guesses — 100 = game over

## Escalation (60s session)
| Variable | Start → End |
|---|---|
| Cup count | 3 → 10 |
| Show timer | 120f → 60f |
| Shuffle duration | 40f → 20f |
| Ball colors | 3 → 4 |

## Dev status
- ✅ main.py (472 lines)
- ✅ test_imports.py (59 tests)
- ✅ ruff + ty pass
- ✅ Web build → docs/334_shell_chain.html
- ✅ Manifest updated

## How to run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/334_shell_chain/main.py
```
