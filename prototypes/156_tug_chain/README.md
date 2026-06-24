# 156 TUG CHAIN — Tug of War Color-Match

## Source
Game Idea Factory #1 (Score 31.85 — ダイス/バッグ構築ローグライト / 宇宙採掘)
Reinterpreted hooks:
- 「ログ/リプレイが資産」→ 前回引いた色が次のアクティブ色になる（色巡回制約）
- 「CA感染/増殖 + risk」→ 間違った色でロープに CA フレイ（ほつれ）が隣接伝播するリスク

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Japanese font support via k8x12.bdf (copied from 054_mole_chain)

## Gameplay
Side-view tug of war. Click rhythmically to pull the rope when your active color matches the rope's center segment.

**Core mechanic**: Same-color consecutive pulls build COMBO. COMBO >= 4 triggers SUPER PULL (5s rainbow mode: all colors match, 3x score).

**Risk/Reward**: Wrong-color pull resets COMBO and frays a rope segment. Fray spreads to adjacent segments via CA (40% per frame per frayed segment). All segments frayed = rope snaps = GAME OVER.

## Controls
- Mouse click: Pull rope (click near rope center area)
- SPACE: Pull rope (alternative)
- TITLE screen: ENTER to start
- GAME OVER screen: ENTER to restart

## Display Info
- Top: Score, Timer (60s countdown), COMBO, Max Combo
- Center: Rope with colored segments + active color indicator
- Bottom: Heat/Fray bar (rope health gauge)

## Dev Status
- ✅ Core pull mechanics (match/mismatch resolution)
- ✅ COMBO system + SUPER PULL mode
- ✅ CA fray spread mechanics
- ✅ Particle effects + floating text
- ✅ Screen shake on damage
- ✅ Title screen + Game Over screen
- ✅ 3-phase state machine (TITLE, PLAYING, GAME_OVER)
- ✅ 35 headless logic tests (all pass)
- ✅ ruff + ty checks pass
- ✅ Web build deployed to docs/

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/156_tug_chain/main.py
```

## Tests
```bash
uv run pytest prototypes/156_tug_chain/tests/ -v
```
