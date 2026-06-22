# POGO SURGE — 150_pogo_surge

**Color-match pogo stick bouncing game — 初のポゴスティックジャンル**

## Source
- **game_idea_factory**: #1 (Score 32.55) — "厄災封印（暴走制御）がテーマのデッキ構築ローグライト"
- **Reinterpretation**: All 10 generated ideas clustered in deckbuilder/dice/auto-shooter
- **Hooks used**: "ログ/リプレイが資産" → ghost trail of previous bounce height; "CA grid fills up" → lava mist rising from bottom
- **Genre**: Pogo stick (first in collection — untapped genre from existing-genres.md)

## 体験仮説
「バネをギリギリまで縮めて狙った同色パッドに着地し、COMBOが5に達してSUPER POGOが炸裂、虹色の軌跡を描きながら自動バウンドで次々とスコアを稼ぐ爆発的カタルシス」

## メカニクス仮説
- **Mechanics**: SPACE hold to charge spring → release to bounce. Arrow keys for air control. Land on same-color pads for COMBO chain.
- **Dynamics**: Risk/reward between aiming for same-color pad (high COMBO → SUPER) vs safe landing on any pad. Higher bounce = more aiming time but also more fall risk.
- **Aesthetics**: Tension during charge-and-aim, catharsis when SUPER POGO activates and auto-bounces through pads.

## Core Loop
1. Player stands on a pad. Hold SPACE to charge spring.
2. Release SPACE to bounce upward. Arrow keys steer left/right in air.
3. Land on a pad → same color = COMBO++ and score; wrong color = COMBO reset + HEAT+15.
4. COMBO >= 5 → SUPER POGO (5s rainbow stick, all pads auto-match, 3x score, auto-bounce).
5. HEAT >= 100 or fall off screen → GAME OVER.
6. Lava mist rises from bottom, pushing pads up and constraining play area.

## Controls
- **SPACE**: hold to charge spring (on ground) / start game / retry
- **← →**: air control (horizontal movement)

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Font: k8x12.bdf for Japanese text support

## Dev Status
- ✅ Core mechanic (charge → bounce → land → COMBO)
- ✅ 4-color pad system
- ✅ COMBO chain + SUPER POGO
- ✅ HEAT risk system with decay
- ✅ Lava mist rising pressure
- ✅ Particle effects + floating text feedback
- ✅ 3 screens (Title / Game / GameOver)
- ✅ 24 headless tests (all passing)
- ✅ ruff + ty clean
- ✅ Web build deployed to docs/

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/150_pogo_surge/main.py
```

## OpenCode Delegation
✅ **OpenCode CLI used for coding** — `opencode run 'Write the full file now...' -f /tmp/design_150.txt --model opencode-go/deepseek-v4-pro` (no `--thinking`)
- First-try success with self-correction of 7 failing tests
- OpenCode autonomously wrote main.py (19.6KB), test_main.py (24 tests), copied k8x12.bdf, updated docs/prototypes.json
