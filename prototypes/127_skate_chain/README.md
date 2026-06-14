# 127 — SKATE CHAIN (Skateboarding Vert Ramp)

Color-match skateboarding vert ramp prototype — the first skateboarding game in the collection.

## Source

Reinterpreted from Idea #1 (Score 31.65 — ヴァンサバ亜種 / 宇宙採掘リソース変換) from 2026-06-15 generation:
- Hook "synthesis compression" → same-color consecutive trick COMBO builds to SUPER COMBO
- Hook "future hand as cost" → pre-commit mechanic: bet on the NEXT trick color before seeing it for 2x bonus

## Engine

- Pyxel 2.x, 320×240, display_scale=2, 60 FPS
- Single file: `main.py` (~557 lines)
- No external dependencies beyond pyxel

## 体験仮説 (Experience Hypothesis)

コンボを積み重ねてSUPER COMBOを発動させ、虹色エフェクトの中で全トリックが自動成功してスコアが爆発する瞬間に爽快感を感じる。また、次のトリック色を予測してプリコミットするか安全に待つかの「未来の手札を賭ける」判断が緊張感を生む。

## メカニクス仮説 (Mechanics Hypothesis)

- **Mechanics**: 4色(Z/X/C/V)トリックマッチング、半円弧オシレーション物理、COMBO/SUPER COMBO連鎖、HEATリスク、プリコミット判定
- **Dynamics**: プレイヤーはコンボ継続のために正確なタイミングと色判断を行う。コンボが伸びるとオシレーションが加速し難易度が上昇。SUPER発動の5秒間は無敵状態でスコアを稼ぎ放題。プリコミットは2倍ボーナスのチャンスだが失敗時のHEAT+30が痛い
- **Aesthetics**: コンボ加速の爽快感、SUPER発動の達成感、プリコミット成功の「読んだ！」という満足感、HEATが溜まる緊張感

## Core Loop

1. Skater auto-oscillates on halfpipe (sinusoidal x-motion, y follows U-curve)
2. At each apex, a trick color appears (RED=Z, GREEN=X, BLUE=C, YELLOW=V)
3. Player presses matching key → combo +1, score += 100 * combo, heat -5
4. COMBO ≥ 5 → SUPER COMBO: 5s rainbow mode, 3x score, auto-match all tricks, heat immunity
5. Wrong key / no input → combo reset, heat up
6. Pre-commit: press key BEFORE trick zone → if correct next color, 2x bonus; if wrong, +30 heat
7. Game over: heat ≥ 100 OR 60s timer expires

## Controls

| Key | Action |
|-----|--------|
| Z | RED trick |
| X | GREEN trick |
| C | BLUE trick |
| V | YELLOW trick |
| SPACE | Start game / Restart |

## Risk & Reward

- **Safe**: Match colors conservatively, slow combo building
- **Risky**: Pre-commit to next color for 2x combo multiplier (wrong = +30 heat)
- **Super**: COMBO ≥ 5 unleashes 5s of rainbow auto-match with 3x score

## Dev Status

- [x] Halfpipe physics (oscillation + ramp curve)
- [x] 4-color trick matching (Z/X/C/V keys)
- [x] COMBO chain (combo, max_combo tracking)
- [x] SUPER COMBO (5s rainbow, 3x score, auto-match)
- [x] Pre-commit risk/reward (2x bonus or +30 heat)
- [x] HEAT risk system (decay, game over at 100)
- [x] 60s timer
- [x] Particle system (burst on tricks, super, wipeout)
- [x] Floating text (combo numbers, SUPER!, MISS, BONUS)
- [x] Screen shake (super activation, wipeout)
- [x] 3 screens: TITLE, PLAYING, GAME_OVER
- [x] 51 headless tests (all pass)
- [x] ruff + ty clean
- [x] Web build (HTML)

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/127_skate_chain/main.py
```

Web: open `docs/127_skate_chain.html` in browser.

## Test Results

```
51 passed in 0.12s
ruff: All checks passed!
ty: All checks passed!
```

## うまくいっている点 (What Works)

- 短いプレイループ: 数秒でトリック判断→結果→次の判断のサイクルが回る
- SUPER COMBO発動時の爽快感: 虹色エフェクト + 3xスコア + 自動成功でスコアが爆発
- プリコミットのリスク判断: 2倍ボーナス vs +30 HEATの緊張感
- HEATシステム: 減衰が遅いので積み重なりが怖い、SUPER中は免疫
- OpenCodeが完全自律でコード・テスト・修正・マニフェスト更新まで完了

## 次に改善するなら (Next Improvements)

- オシレーション速度に加えてハーフパイプ形状も時間経過で変化させる
- トリック種類を増やす（GRAB、FLIP、SPINなど複数ボタン同時押し）
- コンボカウンターの視覚的フィードバック強化（数字の大きさ変化）
- 着地失敗アニメーションの改善
