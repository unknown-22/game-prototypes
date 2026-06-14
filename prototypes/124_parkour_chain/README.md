# 124 — Parkour Chain

**Source**: Game Idea #1 (Score 32.6) — "Hacking (circuit/log)" reinterpreted into parkour genre
- Hook 1: "ログ/リプレイが資産" → Echo trail: player's past path creates future scoring opportunities
- Hook 2: "UIの連鎖演出" → Color-match COMBO chain with SUPER FLOW rainbow mode

## Engine
- Pyxel 2.x, 320×240, display_scale=2

## Gameplay
Side-scrolling parkour runner. Player auto-runs right and jumps between colored platforms.

**Core mechanic**: Landing on same-color platforms consecutively builds a COMBO chain. The player leaves an **echo trail** — colored markers of past positions. Re-crossing your own echo trail while landing on a matching-color platform grants an ECHO BONUS (2x multiplier).

**COMBO ≥ 4** → SUPER FLOW activates (5 seconds): rainbow mode, all platforms auto-match, 3x score, invincibility, walk on air.

**Risk/Reward**: Maintain same-color COMBO for high multipliers, or switch colors to reach better platforms. Stamina limits jumps — manage your energy wisely. Fall off screen = game over.

## Controls
- **SPACE / UP / RETURN**: Jump (costs stamina)
- Auto-runs right at constant speed

## Resources
- **Stamina** (100 max): Jump costs 10. Regenerates 0.5/frame on platforms
- **COMBO**: Consecutive same-color landings
- **Score**: Distance + landing bonus × combo × echo × super multipliers

## Colors
| Color | Pyxel Constant | Value |
|-------|---------------|-------|
| Red | COLOR_RED | 8 |
| Green | COLOR_GREEN | 3 |
| Blue | COLOR_DARK_BLUE | 5 |
| Yellow | COLOR_YELLOW | 10 |

## Dev Status
- ✅ Core mechanic: color-match COMBO chain
- ✅ Echo trail system with ECHO BONUS
- ✅ SUPER FLOW (COMBO ≥ 4)
- ✅ Stamina management
- ✅ Platform auto-generation
- ✅ Particle effects (landing, echo, super, death)
- ✅ Screen shake
- ✅ Background parallax
- ✅ 3 screens: Title, Game, Game Over
- ✅ 62 headless tests (all pass)
- ✅ Web build and manifest updated

## 体験仮説
「自分の移動軌跡（エコートレイル）が未来の得点機会になる」という「ログ/リプレイが資産」の感覚と、同色連続着地によるCOMBO連鎖の爽快感が組み合わさり、「次はもっと良いルートを通ろう」という再挑戦意欲が生まれる。

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/124_parkour_chain/main.py
# or web: open docs/124_parkour_chain.html
```
