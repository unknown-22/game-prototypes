# CHAIN PUSH — Sokoban x Synthesis

**Prototype 051** | Sokoban-style block pushing puzzle with synthesis merge and CA chain spread.

## Source

Reinterpreted from game_idea_factory idea #1 (Score 32.75):
- **Original**: Alchemy synthesis deckbuilder roguelite
- **Transfer hooks**: "synthesis compression" → same-color block merge; "CA grid spread" → merged block color propagation

## Engine

- Pyxel 2.x, 256×256, display_scale=2
- Python 3.12, single-file (~750 lines)
- Type hints, ruff, ty checked

## Gameplay

**Core mechanic**: Push same-color blocks together to merge (SYNTHESIS) and trigger
color-spread chain reactions across adjacent blocks.

### The most fun moment

_"Pushing a block to trigger a cascading chain reaction — merge → spread → merge — that clears multiple targets in one satisfying cascade"_

### Rules

1. Move with Arrow keys or WASD on an 8×8 grid
2. Push blocks by moving into them (Sokoban-style: landing cell must be empty)
3. When 2+ same-color blocks are adjacent, they **MERGE** into a higher tier
4. Merged blocks **SPREAD** their color to adjacent blocks (4 directions for T1/T2, 8 directions for T3)
5. Color changes may trigger more merges → **chain reaction**!
6. Cover all target cells (diamond markers) with matching-color blocks to clear the level
7. Each push costs 1 move — plan carefully for maximum combos

### Resources

| Resource | Description |
|---|---|
| Tiers | T1 (small), T2 (medium), T3 (large, super-spread) |
| Score | Points per merge, multiplied by combo chain depth |
| Combo | Consecutive merges in one chain; resets between pushes |
| Targets | Diamond markers: colored (must match) or white (any color) |

### Risk & Reward

- **Risk**: Chain reactions are unpredictable — a spread might fill spaces you needed for subsequent pushes
- **Reward**: Deep chains create massive combo multipliers (score × (1 + combo × 0.5))
- **T3 Super-spread**: Creating a T3 block unleashes 8-direction color spread, potentially clearing the board

### Difficulty progression

| Level | Name | Mechanic |
|---|---|---|
| 1 | First Merge | Push + merge (1 push) |
| 2 | Chain Spread | Merge → spread → merge → T3 (2-step chain) |
| 3 | T3 Supernova | T3 8-direction diagonal spread |
| 4 | Tactical Planning | 4 color pairs, choose order |
| 5 | Grand Cascade | Many blocks, potential huge chains |
| 6+ | Endless | Procedurally generated levels |

## Controls

| Key | Action |
|---|---|
| Arrow keys / WASD | Move / push blocks |
| R | Restart current level |
| Space / Enter | Start game / continue |

## Dev Status

- [x] Core push mechanic
- [x] BFS merge group detection
- [x] 2-tier merge system (T1→T2→T3)
- [x] Color spread (4-dir for T1/T2, 8-dir for T3)
- [x] Cascading chain reactions
- [x] Target/goal system (colored + any-color)
- [x] 5 predefined levels
- [x] Procedural level generation (level 6+)
- [x] Score + combo tracking
- [x] Particle effects for merges/spreads
- [x] Win/loss detection
- [x] Quick restart (R key)
- [x] 27 headless logic tests
- [ ] Sound effects (SE)
- [ ] Level editor

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/051_chain_push/main.py
```

## Testing

```bash
uv run python prototypes/051_chain_push/test_imports.py
```
