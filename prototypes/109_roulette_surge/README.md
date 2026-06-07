# ROULETTE SURGE (109)

**Source**: Idea #1 (Score 31.85) from 2026-05-30 generation — "log/replay as asset" + "future hand as cost" hooks reinterpreted into color-match roulette.

**Engine**: Pyxel 2.x, 320×240, display_scale=2

## Gameplay

Color-match roulette / fortune wheel. A wheel with 8 segments in 4 alternating colors. Bet on a color, watch the wheel spin, and if it lands on your color your COMBO grows. Same-color consecutive wins build toward SUPER MODE.

### Core Mechanic
- **8-segment wheel**: 4 colors (RED, GREEN, LIGHT_BLUE, YELLOW), 2 segments each
- **Bet & Spin**: Select a color (keys 1-4 or click buttons) → wheel spins with deceleration
- **Match**: COMBO +1, score += 100 × (1 + combo × 0.5)
- **Mismatch**: COMBO reset, HEAT +15
- **SUPER MODE** (COMBO ≥ 5): 5 turns of guaranteed wins, 3× score multiplier
- **FORESIGHT** (SPACE key): Preview next 2 results (costs 1 token, max 3)
- **HEAT**: Reaching 100 = game over
- **Timer**: 60 seconds to maximize score

### "Most Fun Moment"
The wheel decelerating, tension building, and it lands on your color — COMBO grows, SUPER MODE activates, and points pour in.

### Risk/Reward
- Use FORESIGHT for guaranteed wins (safe, costs tokens)
- Bet without foresight for COMBO chain potential (risky, free)
- Push COMBO deeper in SUPER MODE vs. playing safe

## Controls

| Key | Action |
|-----|--------|
| 1/2/3/4 | Bet on color R/G/B/Y |
| SPACE | Use foresight token |
| ENTER | Start / Restart |
| Mouse click | Click colored bet buttons |

## Dev Status

- ✅ Core loop: bet → spin → result → repeat
- ✅ COMBO chain with SUPER MODE
- ✅ FORESIGHT token system
- ✅ HEAT risk / game over
- ✅ 60-second timer
- ✅ Title / Game / Game Over screens
- ✅ Particle effects on match/SUPER
- ✅ 32 headless tests, all passing
- ✅ ruff + ty clean
- ✅ Web build deployed

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/109_roulette_surge/main.py
```

Web: `docs/109_roulette_surge.html`

## 体験仮説
「ホイールが減速し、賭けた色に止まるかどうかの緊張 — 的中してCOMBOが伸びる快感」が短いループで何度も味わえる。

## 実装したコアループ
bet → spin (deceleration) → result evaluation → combo/heat update → repeat. 32 headless tests covering all mechanics.

## うまくいっている点
- テンポの速いbet-spin-result ループ
- COMBO→SUPER MODE の爆発力
- FORESIGHT トークンのリソース管理が判断を生む

## 次に改善するなら
- ベット額の可変 (賭け金システム)
- 複数色同時賭け
- イベントセグメント (ボーナス、ペナルティ)
