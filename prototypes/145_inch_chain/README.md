# 145 — INCH CHAIN

## Source
- **game_idea_factory**: #1 (Score 32.15) — "厄災封印（暴走制御）がテーマのデッキ構築ローグライト"
- **Reinterpretation**: All 10 generated ideas clustered in deckbuilder/dice/auto-shooter
- **Hooks used**: "ログ/リプレイが資産" → ghost trail replay; "盤面が回路/パイプで可視化される（流れて増幅する）" → segmented inchworm body flow
- **Genre**: Inchworm/Caterpillar physics (untapped genre, first in collection)

## Experience Hypothesis (体験仮説)
「収縮とランジで繊細に位置を調整し、同じ色のドットを連続で食べてCOMBOを積み上げ、SUPER INCHが発動した瞬間の開放感と爆発的スコア獲得が気持ちいい」

## Mechanics Hypothesis (メカニクス仮説)
- **Mechanics**: SPACE hold/release for contract/lunge movement, same-color dot eating builds COMBO
- **Dynamics**: Risk/reward tension between aiming for same-color chain (high score, SUPER) vs playing safe (collecting any dot)
- **Aesthetics**: Relief and power fantasy when SUPER INCH activates, tension during combo building

## Core Loop
1. Dots spawn from right edge, scroll left
2. Inchworm auto-moves right; player uses SPACE to contract (slow/precision) or release to lunge (fast/risky)
3. Worm head overlaps dot → eat → same-color builds COMBO, wrong-color adds HEAT
4. COMBO ≥ 4 → SUPER INCH (5s rainbow, auto-collect all nearby, 3x score)
5. HEAT ≥ 100 → GAME OVER

## Controls
- **SPACE** (hold): Contract worm (slow, precise positioning)
- **SPACE** (release): Lunge forward (speed burst)
- **SPACE / Click**: Start game / Retry from title/game over

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single file (510 lines), typed dataclasses, Phase enum

## Dev Status
- ✅ Core gameplay loop (movement, eating, combo)
- ✅ SUPER INCH mode (auto-collect, 3x score, 5s timer)
- ✅ HEAT risk system (decay, game over at 100)
- ✅ Ghost trail replay (best run path)
- ✅ Particle effects + floating text feedback
- ✅ 3 screens (Title, Game, Game Over)
- ✅ 59 headless tests
- ✅ Web build (docs/145_inch_chain.html)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/145_inch_chain/main.py
```

## What Works Well
- Contract/lunge creates meaningful moment-to-moment decisions
- COMBO chain building feels satisfying with visual feedback
- SUPER INCH auto-collect provides powerful release
- Ghost trail gives benchmarking motivation

## Next Improvements
- Add obstacles/enemies to increase decision complexity
- More segment types (electric, spiky) with different effects
- Screen shake on SUPER activation
- Sound effects for eating/combo/SUPER
