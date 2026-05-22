# VEIN BREAK

**Prototype 053** — Color-chain drilling game (Dig Dug / Mr. Driller inspired)

## Source

Reinterpreted from [game_idea_factory](https://github.com/unknown-22/game_idea_factory) #1 (Score 32.35):
- "circuit/pipe visualization (flow + amplify)" → color veins in the rock grid
- "synthesis compression" → BFS chain-clearing connected same-color blocks, gravity compaction

**First drilling/mining game in the collection** — all 10 generated ideas clustered in deckbuilder/dice/auto-shooter; reinterpreted into a mechanically novel genre.

## Engine

- Pyxel 2.x, 200×240, display_scale=2
- Python 3.12+, single-file

## Gameplay

You control a drill at the top of a 10×10 grid of colored blocks. Select a column and drill through the topmost block. **Consecutive same-color drills build COMBO.** At COMBO ≥ 3, drilling into a connected same-color cluster triggers **CHAIN BREAK** — all adjacent same-color blocks are destroyed in a cascading BFS flood-fill. Cleared columns compact via gravity, and new blocks spawn from above.

### Core loop (5–15 seconds per cycle)
1. **Scan** — Look at the grid, spot same-color veins
2. **Decide** — Pick which column to drill for maximum chain potential
3. **Drill** — Press SPACE/DOWN to drill the topmost block
4. **React** — If COMBO triggers, watch the chain reaction cascade
5. **Adapt** — New blocks spawn, gravity shifts the grid — repeat

### Most fun moment
Spotting a large same-color vein, building COMBO to 3, then triggering CHAIN BREAK that clears a massive connected cluster — watching blocks explode in sequence while the score multiplier climbs.

## Controls

| Key | Action |
|---|---|
| ← → / A D | Move drill left/right |
| ↓ / SPACE / S | Drill (destroys topmost block in column) |
| SPACE (game over) | Retry |

## Resources

| Resource | Description |
|---|---|
| **FUEL** | Starts at 100. Each drill costs 3. Blocks have 20% chance to drop +15 fuel. Runs out = game over. |
| **COMBO** | Increments on consecutive same-color drills. Resets to 1 on color mismatch. |
| **Score** | Base 10 per block × combo multiplier (1 + (combo-1) × 0.5). Chain blocks: ×1.5 bonus. |

## Scoring

- **Drill score**: `10 × (1 + (combo - 1) × 0.5)`
- **Chain break score**: `10 × combo_mult × 1.5` per chain-cleared block
- **Fuel pickups**: 20% chance per drilled block (+15F), 10% per chain block (+7F)

## Difficulty

- New blocks spawn every 150 frames (2 per spawn)
- Fuel depletes 3 per drill — aggressive drilling without chains drains fast
- COMBO incentivizes finding same-color veins; breaking combo wastes fuel efficiency

## Dev Status

- [x] Grid rendering with colored blocks
- [x] Drill movement (LEFT/RIGHT) and drilling (DOWN/SPACE)
- [x] COMBO system (consecutive same-color tracking)
- [x] CHAIN BREAK (BFS flood-fill, COMBO ≥ 3)
- [x] Gravity compaction after clearing
- [x] Fuel management with pickups
- [x] Particle effects (drill burst + chain explosions)
- [x] Floating text feedback (score, fuel, chain messages)
- [x] Screen shake on chain complete
- [x] Game over + retry
- [x] Combo glow indicator
- [x] Headless logic tests
- [ ] Sound effects (future)
- [ ] Level progression (future)

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/053_vein_break/main.py
```

## How to Test

```bash
cd ~/repos/game-prototypes
uv run python prototypes/053_vein_break/test_imports.py
```
