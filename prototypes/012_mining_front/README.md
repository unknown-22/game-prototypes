# Mining Front — Lane-based Tower Defense

**Prototype 012** — First tower defense in the collection.

## Source

Reinterpreted from [game_idea_factory](https://github.com/unknown-22/game_idea_factory) idea #1 (score 31.8):

| Original Hook | Reinterpretation |
|---|---|
| Same card consecutively → effect changes (strengthen/explode) | Chain Reactor towers get +50% damage per orthogonally adjacent Chain Reactor |
| Chain reaction UI (collapse/increase/compress) | Visual chain links between reactors, floating damage multipliers, screen shake |
| Space mining / resource conversion | Ore economy: earn from kills, spend on towers, earn interest between waves |

## Engine

- Pyxel 2.x, 400×300, display_scale=2
- 60 FPS

## Gameplay

**Objective:** Survive 10 waves of enemies marching left across 5 lanes.

**Core mechanic:** Place mining towers on the grid to auto-attack enemies. Chain Reactors amplify each other's damage when placed adjacent — build clusters for massive damage at the cost of high per-tower price.

### Tower Types

| # | Tower | Cost | Damage | Cooldown | Special |
|---|---|---|---|---|---|
| 1 | **LASER** | 10 | 15 | 0.8s | Basic single-target |
| 2 | **CHAIN** | 25 | 12 | 0.55s | +50% dmg per adjacent Chain Reactor |
| 3 | **SIPHON** | 15 | 8 | 1.0s | +10 bonus ore per kill |

### Enemy Types

| Enemy | HP | Speed | Reward |
|---|---|---|---|
| SCOUT (green) | 20 | 60 px/s | 5 |
| DRONE (yellow) | 45 | 38 px/s | 12 |
| TANK (purple) | 120 | 22 px/s | 30 |

### Economy

- Start with 50 ore
- Earn ore from kills
- 5% interest on saved ore between waves
- Chain Reactors are expensive but scale with adjacency

### Risk/Reward

- Save ore for Chain Reactors (powerful clusters) vs. buy cheap Lasers now
- Cover all 5 lanes vs. concentrate fire in key lanes
- Spend all ore vs. save for interest
- Chain reactor clusters can melt tanks instantly — the satisfying moment

### Rules

- 10 HP; enemy reaching left edge costs 1 HP
- HP = 0 → DEFEAT
- Survive 10 waves → VICTORY
- R to restart anytime

## Controls

| Input | Action |
|---|---|
| Mouse click (grid) | Place selected tower on empty cell |
| Mouse click (bottom buttons) | Select tower type |
| 1 / 2 / 3 | Select tower type (LASER/CHAIN/SIPHON) |
| SPACE | Start wave immediately |
| R | Restart |

## Dev Status

- ✅ Core tower defense with 3 tower types
- ✅ 3 enemy types with escalating waves
- ✅ Chain reactor adjacency amplification
- ✅ Ore economy with interest
- ✅ Particle effects, floating text, screen shake
- ✅ Victory/defeat screens with quick restart
- ✅ Headless logic tests
- ⬜ Tower selling (right-click refund)
- ⬜ Enemy path variety (zigzag lanes)
- ⬜ More tower types

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/012_mining_front/main.py
```

Requires display (X server on WSL, or run natively on Windows).
