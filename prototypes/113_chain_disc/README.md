# CHAIN DISC — Disc Golf with Color-Match COMBO Chain

**Source**: game_idea_factory #1 (Score 32.35) reinterpreted — dice/bag roguelite "synthesis compression + CA grid fills up" hooks → disc golf

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single file: `main.py` (502 lines)

## 体験仮説
遠くの同色バスケットを連続で狙い当ててCOMBOが爆発し、SUPER DISCが障害物を貫通してコースを一掃する瞬間に爽快感を得られる。

## Gameplay
Top-down disc golf where you aim and throw discs at colored basket targets.  
Same-color consecutive hits build a COMBO chain → SUPER DISC (rainbow, 3x score, obstacle pierce) at COMBO ≥ 4.  
Obstacles (trees) spread via CA-style growth after every throw.  
90-second time limit. HEAT system: miss or wrong-color hit increases HEAT; game over at MAX_HEAT (10).

## Core Loop
1. AIMING: Click-drag from player to set direction + power (farther = more power)
2. FLYING: Disc flies, bounces off screen edges, checks basket/obstacle collisions
3. RESOLVE: Combo/heat/score update, particles, obstacle spread, basket replacement
4. Repeat until timer runs out or HEAT maxes out

## Controls
- Mouse drag-and-release: aim and throw disc
- Click / ENTER: advance from TITLE and GAME_OVER screens

## Risk & Reward
- **Risk**: aiming for same-colored baskets builds COMBO but requires precision; miss = HEAT + 2, combo reset
- **Risk**: wrong-color hit resets combo and adds HEAT  
- **Reward**: COMBO multiplier increases score per hit; COMBO ≥ 4 triggers SUPER DISC (5s, 3x score, pierce obstacles)

## Scoring
- `score += basket.value * combo * multiplier`  
- multiplier = 3 (SUPER mode) or 1 (normal)

## Dev Status
- ✅ Core mechanic: color-match COMBO chain
- ✅ SUPER DISC at COMBO ≥ 4
- ✅ CA-style obstacle spread
- ✅ HEAT risk system
- ✅ 90-second timer
- ✅ Edge bounce physics
- ✅ Particle effects (hit, super, miss)
- ✅ Basket replacement on hit
- ✅ 58 headless tests passing
- ✅ Ruff + ty clean
- ✅ Web build (docs/113_chain_disc.html)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/113_chain_disc/main.py
```

## How to Test
```bash
cd ~/repos/game-prototypes
uv run pytest prototypes/113_chain_disc/test_imports.py -v
```
