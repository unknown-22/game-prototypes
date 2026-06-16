# 131 — TILE CHAIN

麻雀ソリティア風の色合わせタイルマッチングゲーム。

## Source

Based on game_idea_factory idea #1 (Score 31.6) — hacking auto-shooter with "synthesis/compression" and "chain collapse UI" hooks. Reinterpreted into a tile-matching puzzle.

## Engine

- Pyxel 2.x
- 320×240, display_scale=2
- 571 lines, single file

## Gameplay

8×6 grid of colored tiles (4 colors: RED, BLUE, GREEN, YELLOW, 12 each = 48 tiles). Click two same-color tiles to remove them. Same-color consecutive matches build COMBO multiplier.

### Rules
- Match same-color pairs → score increases, combo builds
- COMBO ≥ 4 → SUPER MATCH (5s rainbow mode, 3x score, any-color pairs match)
- Wrong-color click → COMBO reset + HEAT +15
- HEAT ≥ 100 → GAME OVER
- 90 second timer → GAME OVER
- All tiles cleared → WIN (big bonus + time bonus)
- No valid pairs remaining → press R to reshuffle (+10 HEAT)

### The Fun Moment
4連続で同色タイルをマッチさせてCOMBOが4に達し、SUPER MATCHが発動して虹色に輝きながら残りのタイルを一気に消し去り、大量スコアが爆発する瞬間。

### Risk/Reward
- Chase same-color COMBO for high scores and SUPER MATCH activation
- Settle for safe mixed-color matches that reset COMBO but don't raise HEAT
- SUPER mode lets ANY pair match (maintain COMBO easily) but has a 5s timer

## Controls

| Input | Action |
|-------|--------|
| Mouse click | Select/match tiles |
| R | Reshuffle grid (costs +10 HEAT, only when no valid pairs) |
| SPACE / RETURN | Start game / retry |

## Dev Status

- ✅ Title screen
- ✅ Game screen (8×6 grid, tile matching, COMBO chain, SUPER MATCH)
- ✅ Game over screen (score, max combo, retry)
- ✅ Particle effects + floating text
- ✅ Screen shake
- ✅ HEAT risk system
- ✅ 90s timer
- ✅ Reshuffle mechanic
- ✅ 38 headless tests (all pass)
- ✅ ruff clean
- ✅ ty clean
- ✅ Web build

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/131_tile_chain/main.py
```

## How to Test

```bash
uv run pytest prototypes/131_tile_chain/test_imports.py -v
```
