# 177_go_surge — Liberty Chain (囲碁風陣取り)

Go-like territory capture puzzle built with Pyxel.  
**Genre**: Go/Baduk territory capture — first in collection.

## Source
- Based on Idea #1 (score 31.75): "magic academy deckbuilder with rule changes + CA grid"
- Reinterpreted hooks: "rule changes" → same-color COMBO chain, "CA grid fills up" → BFS liberty capture + neutral stone spawn

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Japanese font support via k8x12.bdf

## Core Mechanic Experience Hypothesis
*「同色の石を連続配置してCOMBOを積み上げ、BFSが走って敵グループが一網打尽に捕獲され、スコアの数字が爆発的に跳ね上がる瞬間」が面白い*

## Mechanics → Dynamics → Aesthetics
- **Mechanics**: Place colored stones, same-color consecutive = COMBO, COMBO≥3 = BFS liberty capture, COMBO≥5 = SUPER STONE rainbow auto-capture
- **Dynamics**: Risk/reward — continue same-color for COMBO (safe+powerful) or switch colors to capture key territory (costs HEAT)
- **Aesthetics**: Territory domination via chain captures, score explosion on large group captures

## Gameplay
1. Place stones on a 7×7 Go-like grid by clicking intersections
2. Same-color consecutive placements build COMBO (×1, ×2, ×3...)
3. COMBO ≥ 3: BFS liberty-based capture — enemy groups with 0 liberties are removed
4. COMBO ≥ 5: SUPER STONE activates (150 frames rainbow mode, auto-captures ALL enemy groups, 3× score)
5. Switching colors (mismatch) resets COMBO and adds +20 HEAT
6. HEAT ≥ 100: Game Over
7. Neutral stones spawn every 180 frames (up to 30 on board)
8. Board full: Game Over
9. Score = captured stones × COMBO × (3 if SUPER)

## Controls
- **1/2/3/4**: Select stone color (RED/GREEN/BLUE/YELLOW)
- **Mouse click on grid**: Place stone
- **Mouse click on palette**: Select color
- **R**: Restart
- **Enter/Space**: Start / Retry

## Dev Status
- ✅ Core placement with COMBO tracking
- ✅ BFS liberty-based capture (COMBO ≥ 3)
- ✅ SUPER STONE mode (COMBO ≥ 5, 150f, 3× score)
- ✅ HEAT risk system (mismatch +20, decay, game over at 100)
- ✅ Neutral stone auto-spawn
- ✅ Particle + floating text effects
- ✅ Keyboard + mouse dual input
- ✅ Title / Playing / Game Over screens
- ✅ 67 headless tests
- ✅ Web build deployed to docs/

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/177_go_surge/main.py
```

## Web Play
Open `docs/177_go_surge.html` in a browser (or via GitHub Pages).
