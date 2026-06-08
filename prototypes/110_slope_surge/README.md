# 110_slope_surge — Slope Surge

色合わせスラロームゲート × スキー下山アクション

## Source
- Generated idea #1 (score 31.75): ダイス/バッグ構築ローグライト / 発電所（過負荷と放電）
- Hooks reinterpreted into skiing:
  - "ログ/リプレイが資産" → Ghost skier replays best run
  - "盤面が回路/パイプで可視化される" → Gates scroll upward, chain amplification

## Engine
- Pyxel 2.x, 320×240, display_scale=2, fps=60

## Core Mechanic
Side-scrolling downhill skiing. Must pass through color-coded slalom gates (4 colors: RED, GREEN, DARK_BLUE, YELLOW). Same-color consecutive gates build COMBO chain. Different color resets combo. COMBO≥5 triggers SUPER MODE (rainbow, invincible to obstacles, auto-pass all gates, 3x score, 5 seconds).

**一番面白い瞬間**: 同じ色のゲートを連続通過してコンボを重ね、SUPER MODEで無敵になりながら一気に滑り降りる瞬間

## Controls
- LEFT / A: Move left
- RIGHT / D: Move right
- SPACE / RETURN: Start game / Retry

## Mechanics
- **COMBO**: Same-color consecutive gates increment combo. Score = 10 × (combo + 1)
- **SUPER MODE**: COMBO≥5 activates 5-second SUPER MODE (300 frames). Rainbow skier, all gates auto-pass, 3x score, invincible to obstacles
- **HEAT**: Missing a gate adds 1.2 heat. Obstacle collision adds 2.0 heat. Heat≥5.0 → GAME OVER. Passive decay: 0.01/frame (not during SUPER)
- **Obstacles**: Trees/rocks scroll upward. Collision adds heat + resets combo. Knocks player through obstacle
- **Ghost Trail**: Best run's player positions saved as trail. Displayed as translucent dots during subsequent runs
- **Scroll Speed**: Starts at 1.5 px/frame, increases 0.3 every 10 seconds, caps at 4.0

## Dev Status
- ✅ Single-file Pyxel implementation (560 lines)
- ✅ Phase machine (TITLE, PLAYING, GAME_OVER)
- ✅ Gate passing + combo chain + SUPER MODE
- ✅ Heat system + obstacle collision + knockback
- ✅ Particle system + floating text
- ✅ Ghost trail replay
- ✅ Scroll speed escalation
- ✅ 66 headless tests, ruff + ty passing
- ✅ Web build deployed to docs/

## Experience Hypothesis
高速で迫る色付きゲートを判断しながら同じ色を選び続け、コンボが溜まってSUPER MODEに突入する爽快感

## Risk & Reward
- 同じ色を追いかけると高コンボ・高得点だが、別の色のゲートや障害物に近づくリスクがある
- SUPER MODEは無敵で大量得点だが、終了後にコンボがリセットされる

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/110_slope_surge/main.py
```
