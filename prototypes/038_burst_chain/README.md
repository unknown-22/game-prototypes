# Burst Chain (038_burst_chain)

Bubble shooter with chain-propagation popping.

## Source

Reinterpreted from game idea #1 (score 31.55): dice/bag roguelite with
**"chain propagation"** and **"one color per turn"** hooks.

All 10 generated ideas (2026-05-18) clustered in deckbuilder/dice/auto-shooter.
Reinterpreted into **Bubble Shooter** — a genre not yet in the collection.

## Engine

- Pyxel 2.x
- Screen: 240×320 (portrait), display_scale=2
- Language: Python 3.12

## Gameplay

### Core Mechanic
Shoot colored bubbles at the ceiling grid. Match **3+ same-color bubbles** to pop them via BFS cluster detection. Any bubbles **not connected to the top row** after a pop cascade down for bonus points.

### Risk/Reward Systems
- **COMBO**: Consecutive pops multiply score (×1.5, ×2.0, ×2.5...). Missing resets to zero.
- **HEAT**: Each pop builds heat. Heat above 70% **accelerates ceiling drops** (new rows appear faster). Heat slowly decays when you miss.
- **FLOATING CASCADE**: Smart positioning can create large floating-bubble waterfalls for massive bonus.

### Controls
| Input | Action |
|-------|--------|
| Mouse move | Aim shooter |
| Left click / Space | Shoot bubble |
| Arrow Left/Right or A/D | Fine-tune aim |
| R / Space (game over) | Retry |

### Reinterpretation Mapping
| Idea Hook | Implementation |
|-----------|---------------|
| "Chain propagation" | BFS cluster pop → floating cascade (chain reaction of unsupported bubbles) |
| "One color per turn" | You shoot one bubble at a time from the current color |
| "Combo management" | Consecutive-pop combo multiplier |
| "Heat management" | Heat accelerates ceiling; risk/reward tension |

## Dev Status

- [x] Core bubble shooter (aim, shoot, snap)
- [x] BFS same-color cluster detection
- [x] Floating bubble cascade
- [x] COMBO multiplier system
- [x] HEAT system with accelerated drops
- [x] Hex-grid neighbor calculation
- [x] Particle effects
- [x] Floating text feedback
- [x] Game over / retry
- [x] Headless import test
- [ ] pyxel package + app2html
- [ ] docs/prototypes.json manifest

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/038_burst_chain/main.py
```
