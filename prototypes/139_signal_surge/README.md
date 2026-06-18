# SIGNAL SURGE (139)

**Source**: Game idea #1 (score 31.65) — reinterpreted "dice/bag roguelite with synthesis compression + one-color-per-turn" hooks into a signal decoding game.

## Engine
- Pyxel 2.x, 320×240, display_scale=2, 30 FPS

## 体験仮説
「高速で流れる信号の中、同じ色を連続で正確に打ち返してCOMBOを繋ぎ、SUPER DECODEが発動した瞬間に全信号が一気に処理されてスコアが爆発する快感」

## Core Mechanic
1. Colored signals scroll from right to left across 4 horizontal lanes
2. Press Z(RED)/X(GREEN)/C(BLUE)/V(YELLOW) to decode matching-color signals
3. Same-color consecutive decodes build COMBO chain
4. COMBO ≥ 5 triggers SUPER DECODE (5s rainbow auto-decode, 3x score)
5. Wrong key = +15 HEAT, missed signal = +5 HEAT
6. HEAT ≥ 100 = SIGNAL OVERLOAD (game over)
7. Speed gradually increases with decoded count

## Risk & Reward
- Same-color COMBO chain → high score multiplier + SUPER DECODE reward
- Wrong key → COMBO reset + HEAT penalty
- Missed signals → gradual HEAT buildup (can't ignore forever)

## Controls
- TITLE: Any key (Z/X/C/V or ENTER) to start
- PLAYING: Z=RED, X=GREEN, C=BLUE, V=YELLOW
- GAME_OVER: ENTER to retry

## Dev Status
- ✅ Core decode-and-combo loop
- ✅ SUPER DECODE auto-decode mechanic
- ✅ HEAT risk system with game over
- ✅ Speed ramping difficulty
- ✅ Particle effects and floating score text
- ✅ Screen shake on game over
- ✅ 70 headless tests
- ✅ Ruff + ty clean
- ⬜ Audio (SE for decode/combo/super/overload)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/139_signal_surge/main.py
```

## うまくいっている点
- 単純なキー入力の連続がCOMBOチェインに繋がり、テンポよくプレイできる
- SUPER DECODE発動時の画面全体の虹色エフェクトと自動解読が気持ちいい
- HEATバーが視覚的に危険度を伝え、ミスが積み重なる緊張感がある

## 次に改善するなら
- 信号の出現パターンにバリエーション（連続同色ウェーブ、全色同時など）
- 音声フィードバックの追加
- 難易度カーブの調整（現在は線形）
