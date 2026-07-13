# 230_rope_chain — Jump Rope Color-Match COMBO Chain

## Source
- Generated from: game_idea_factory, Idea #1 (Score 32.35)
- Original idea: デッキ構築ローグライト（マップノード）/ 発電所（過負荷と放電）
- Reinterpretation: "効果が合成されて圧縮" → 同色連続ジャンプがCOMBOチェインに圧縮、"回路/パイプで可視化（流れて増幅）" → ロープの弧が可視化する流れ
- Date: 2026-07-13

## Engine
- Pyxel 2.x, 320×240

## 体験仮説
「ロープのリズムに合わせて同色ジャンプを成功させ続ける緊張感と、COMBOが溜まってSUPER JUMPが発動した時の爽快感」

## Gameplay
- Side-view jump rope game
- Pendulum rope swings in an arc (max angle π/3)
- Press SPACE to jump over the rope
- 4 colors (RED/LIME/DARK_BLUE/YELLOW) cycle every 90f→40f (escalation)
- Same-color consecutive jumps build COMBO chain (score = 10 × combo × super_mult)
- COMBO >= 4 triggers SUPER JUMP (300f rainbow, 3x score, auto-jump + invincible)
- Mismatch (wrong color): combo reset, HEAT +15
- Rope hit: HEAT +25, stun 20f, combo reset
- HEAT >= 100 or 60s timer → game over

## Risk & Reward
- Chase same-color jumps to build COMBO → SUPER JUMP (high score, auto-play)
- Skip mismatched colors to stay safe (low score, no heat)
- Rope speed increases (0.04→0.10 rad/f), color cycles faster (90f→40f) over 60s

## Controls
- SPACE: Jump
- RETURN: Start game / Restart

## Dev Status
- ✅ Core mechanic: pendulum rope physics + color-match jump
- ✅ COMBO chain + SUPER JUMP
- ✅ HEAT risk system
- ✅ Difficulty escalation (speed, color interval)
- ✅ 3 screens (Title/Playing/GameOver)
- ✅ Particle system + floating text
- ✅ 53 headless tests
- ✅ ruff + ty passing
- ⬜ Sound effects

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/230_rope_chain/main.py
```
