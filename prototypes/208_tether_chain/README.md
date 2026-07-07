# TETHER CHAIN — Prototype 208

Top-down tetherball arcade game.

## Source
- **Game Idea**: #1 (Score 32.2) — 発電所（過負荷と放電）テーマのダイス/バッグ構築ローグライト
- **Reinterpretation**: ログ/リプレイ + 連鎖崩壊 hooks → テザーボール with color-match COMBO chain
- **New genre**: Tetherball (初のテザーボールジャンル)

## Experience Hypothesis (体験仮説)
加速するボールを同じ色で連続ヒットしてSUPER HITが発動し、虹色になったボールを打ち続けてスコアが爆発的に伸びる瞬間が面白い。

## Mechanics Hypothesis
- **Mechanics**: 4色サイクルのボール打ち分け、同色連続COMBO、HEATリスク
- **Dynamics**: ボールが来るまで待って同色COMBO継続を狙うか、色が変わったら安全に空振りするか
- **Aesthetics**: タイミングの緊張感とCOMBO増加の快感、SUPER発動の爆発的爽快感

## Core Loop
1. ボールが円周上を回転し、色が定期的に変化
2. ボールが自陣（下半分）に入ったらSPACEキーで打つ
3. 同色連続ヒットでCOMBO増加、スコア倍率上昇
4. COMBO>=4でSUPER HIT（虹色5秒、3倍スコア）
5. 色違いでCOMBOリセット+HEAT
6. HEAT>=100または60秒経過でゲームオーバー

## Controls
- `SPACE`: Hit ball (when in player half)

## Tech
- Pyxel 2.x, 320×240, display_scale=2
- Single file: main.py (395 lines)
- 61 headless tests

## Status
- ✅ Core mechanic: tetherball orbit + color-match COMBO chain
- ✅ SUPER HIT activation + refresh
- ✅ HEAT system with wrong-hit + miss-pass + decay
- ✅ 60s timer + difficulty ramp (ball speed acceleration)
- ✅ Particle burst + floating text feedback
- ✅ 3 screens: Title, Playing, GameOver
- ✅ Web build deployed to docs/208_tether_chain.html

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/208_tether_chain/main.py
```

## What Works
- Ball physics (circular orbit, angle wrapping, speed acceleration)
- Color cycle every 90 frames
- COMBO chain (same-color consecutive hits, score scales with combo)
- SUPER HIT at COMBO≥4 (rainbow ball, 3x score, 5s duration)
- HEAT system (wrong hit +15, miss pass +5, decay 0.05/frame)
- Game over at HEAT≥100 or timer=0
- OpenCode first-try success with no --thinking (395 lines, ruff+ty clean)

## What to Improve Next
- Add AI opponent that also hits from the top half
- Visual rope wrapping effect (rope winds around pole as combo grows)
- Screen shake on SUPER activation
- Difficulty modes (faster/slower speed, smaller hit window)
