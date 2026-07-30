# MOTO CHAIN (259)

Side-scrolling motocross dirt bike racing with color-match COMBO chains.

## Source
Reinterpreted from game_idea_factory Idea #1 (Score 32.2):
- "ログ/リプレイが資産" → ghost trail of best run
- "UIの連鎖演出（崩壊/増加/圧縮）" → COMBO chain → SUPER MOTO

## 体験仮説
「同じ色のリングを空中で連続通過してCOMBOが加速し、SUPER MOTOが発動して虹色のバイクですべてのリングを自動的に駆け抜ける瞬間に、爽快感と達成感を感じる」

## Engine
- Pyxel 2.x, 320×240@30fps

## Gameplay
- Auto-scroll rightward over sine-wave terrain (speed 2.0→5.0 over 60s)
- UP/SPACE to jump (vy=-7.5, gravity=0.4)
- Bike color auto-cycles (RED/LIME/DARK_BLUE/YELLOW) every 20 frames
- Colored rings spawn from right edge — pass through matching color for COMBO
- Same-color consecutive passes = COMBO chain (score = 100 + combo × 50)
- Mismatch = COMBO reset, HEAT+15, stun 15f
- Hard landing (vy > 3) = COMBO reset, HEAT+25, stun 20f
- COMBO≥4 triggers SUPER MOTO (300f/10s): rainbow mode, any-color match, 3x score, auto-throttle
- HEAT≥100 → GAME OVER
- 60s timer → GAME OVER

## Controls
- SPACE / UP: Jump
- SPACE / Click: Start / Retry

## Dev Status
- ✅ Core terrain + bike physics
- ✅ Ring spawning + color-match combo
- ✅ SUPER MOTO mode
- ✅ HEAT risk system + stun
- ✅ Ghost trail replay
- ✅ Particle bursts + floating text
- ✅ Three screens (Title/Playing/GameOver)
- ✅ 62 headless tests
- ✅ Ruff + ty checks pass
- ✅ Web build deployed

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/259_moto_chain/main.py
```

## Web Build
```bash
uv run pyxel package prototypes/259_moto_chain prototypes/259_moto_chain/main.py
uv run pyxel app2html 259_moto_chain.pyxapp
mv 259_moto_chain.html docs/
```
