# CELL SURGE — Grid Territory Control

**Source**: Game idea #1 (score 32.35) — Dice/bag roguelite / Delivery logistics.
Reinterpreted hooks: "synthesis compression" + "CA grid spread control" → **territory painting game**.

## Engine
- Pyxel 2.x
- Screen: 300×340 (300×300 grid + 40px UI bar)
- Display scale: 2×

## Gameplay

**Core mechanic**: Place colored seeds on a 12×12 grid. Seeds auto-spread to adjacent empty cells (cellular automaton). When a contiguous same-color region reaches **6+ cells**, it SYNTHESIZES into an indestructible NODE. Nodes resist enemy conversion and are worth 3× score.

**The most fun moment**: Watching your color chain-spread across the grid, then a massive region synthesizes into a fortress node — reclaiming territory and earning a huge score bonus.

### Rules
- **Seeds**: Place with SPACE or LEFT CLICK (costs 2 energy)
- **CA spread**: Every tick (~1 sec), all non-node player cells spread to adjacent empty cells
- **Enemy spread**: Every 2 ticks, enemy cells spread from edges, converting player cells (nodes resist)
- **Synthesis**: Contiguous same-color region ≥ 6 cells → compresses into 1 NODE; rest become empty
- **Score**: +1 per player cell, +3 per node cell per tick. +10×region_size×combo on synthesis
- **COMBO**: Consecutive syntheses multiply score; decays after 3 ticks without synthesis
- **Energy**: Regenerates 1 per tick, max 10

### Win/Lose
- **VICTORY**: Eliminate all enemy cells
- **DEFEAT**: Enemy controls ≥ 50% of grid (72 cells)

### Controls
| Input | Action |
|-------|--------|
| WASD / Arrows | Move cursor |
| SPACE | Place seed at cursor |
| LEFT CLICK | Place seed at mouse position |
| SPACE / CLICK (on game over) | Retry |

## Strategy Tips
1. **Block enemy advance**: Place seeds near enemy territory to slow their spread
2. **Build toward synthesis**: Focus on growing contiguous regions of the same color
3. **Use nodes as walls**: Nodes are immune to enemy conversion — great for defensive lines
4. **Manage energy**: Don't overspend; you need energy reserves when enemy pressure peaks
5. **Chain combos**: Time syntheses close together to stack the COMBO multiplier

## Dev Status
- ✅ Core grid with CA spread
- ✅ Enemy spread from edges
- ✅ Synthesis (6-cell → node)
- ✅ Combo system
- ✅ Energy management
- ✅ Particle effects + flash feedback
- ✅ Victory/defeat conditions
- ✅ Mouse + keyboard input
- ✅ Game over + retry
- ⬜ Difficulty scaling (enemy speed increase over time)
- ⬜ Sound effects
- ⬜ Multiple levels

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/023_cell_surge/main.py
```
