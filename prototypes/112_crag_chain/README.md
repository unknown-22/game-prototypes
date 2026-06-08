# 112 — CRAG CHAIN

Rock climbing grid puzzle with color-match COMBO chains.

## Source

- **Idea**: #1 from 2026-06-08 generation (Score 32.0)
- **Original hooks**: "synthesis compression" + "split→converge→explode"
- **Reinterpreted into**: Rock climbing (untapped genre) — same-color consecutive handhold grabs build COMBO; COMBO≥4 triggers SUPER REACH explosion

## Engine

- Pyxel 2.x, 320×240, display_scale=2
- Grid: 8 columns × 20 rows, cell size 24×24 px

## Core Mechanic

1. Click on adjacent handholds (Manhattan distance ≤ 2) to grab and climb
2. Same color consecutive grabs → COMBO chain (+1 per grab)
3. Different color → COMBO resets to 1
4. Stamina depletes per grab: distance 1 = 5, distance 2 = 12
5. COMBO ≥ 4 → **SUPER REACH** activates: 5s, 3x score, any color counts, half stamina
6. Wall auto-scrolls upward as player climbs
7. Game over: stamina ≤ 0 or fall off bottom
8. Score: height climbed × combo multiplier

## Controls

| Input | Action |
|-------|--------|
| Mouse click | Grab adjacent hold |
| ENTER | Start game / Retry |

## Color Reference

| Index | Color | Pyxel Code |
|-------|-------|-----------|
| 0 | RED | 8 |
| 1 | GREEN | 3 |
| 2 | LIGHT_BLUE | 6 |
| 3 | YELLOW | 10 |

## Dev Status

- ✅ Core gameplay: hold grabbing, COMBO chain, SUPER REACH
- ✅ Stamina system with distance-based cost
- ✅ Auto-scrolling climbing wall
- ✅ Particle effects on grab and SUPER REACH
- ✅ Screen shake on SUPER REACH activation
- ✅ Score popup on grab
- ✅ 39 headless tests (ruff + ty pass)
- ✅ Web build deployed to docs/
- ⬜ Sound effects
- ⬜ Difficulty scaling (fewer holds, more gaps at higher rows)

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/112_crag_chain/main.py
```

## Experience Hypothesis (体験仮説)

「同色ホールドを連続で掴んでコンボが伸び、SUPER REACH で一気に壁を駆け上がるカタルシスを味わえる」

## Core Loop

見る（壁上の同色ホールドを探す）→ 判断する（遠いホールドはスタミナ消費大。同色狙うか安全に近場で済ますか）→ 操作する（クリック）→ 結果が返る（コンボ増加/リセット、パーティクル、スコアポップアップ）→ 次の判断へ

## What Works Well

- COMBO building feels satisfying with particle feedback
- SUPER REACH creates a "power moment" that changes playstyle
- Stamina risk/reward creates meaningful decisions (far jump = more stamina but better route)
- Auto-scroll creates natural urgency

## First Area to Improve

- Route visibility: add a subtle highlight showing all reachable same-color holds when hovering
- More hold variety: special holds (bonus stamina, extra points, hazards)
