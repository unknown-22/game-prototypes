# PIPE SURGE — Pipe Connection Puzzle

Prototype 029 in the game-prototypes monorepo.

## Source

Reinterpreted from game idea #1 (score 32.2):
- **Original genre**: Dice/bag roguelite (logistics/delivery)
- **Reinterpreted as**: Pipe connection puzzle
- **Hooks used**:
  - "Log/replay as asset" → placed pipes persist as permanent infrastructure
  - "Chain collapse / amplification" → same-color adjacent pipes chain-propagate for combo multipliers

**The most fun moment**: Watching your pipe network erupt in a cascading chain reaction when you complete the path — same-colored pipes flashing one by one and then all SURGING in a burst of particles for multiplied score.

## Engine

- Pyxel 2.x
- Screen: 256×256, display_scale=2
- Framerate: 30fps

## Gameplay

Connect colored pipes from the **Source** (white arrow) to the **Drain** (green square). Same-color adjacent pipes in the completed path create a COMBO chain. COMBO ≥ 4 triggers a **SURGE** — all connected pipes explode in a particle burst and clear, awarding a massive bonus.

### Core Loop

1. **PLACING**: Place pipe tiles from your hand onto empty grid cells. Rotate tiles with `R` or right-click. Select hand tiles with `1`/`2`/`3` or click them.
2. **FLOWING**: Click FLOW (or press SPACE/ENTER). The pipes animate lighting up along the connection path.
3. **SURGING** (if COMBO ≥ 4): All connected pipes burst with particles, then clear from the grid.
4. **Next round**: New Source and Drain spawn. Your remaining pipes stay — build on them!

### Risk/Reward

- **Completing a path**: Earns base score + combo multiplier. Reduces pressure.
- **Failing to connect**: Gains 1 pressure. At 10 pressure, game over.
- **Timer**: 20 seconds per round. Timeout = +1 pressure, new source/drain.
- **SURGE (COMBO ≥ 4)**: Clears pipes for bonus score, but you lose that infrastructure.

## Controls

| Action | Input |
|---|---|
| Place tile | Click empty grid cell |
| Select hand tile | `1`/`2`/`3` or click hand tile |
| Rotate selected tile | `R` or right-click |
| Trigger FLOW | Click FLOW button, SPACE, or ENTER |
| Restart (game over) | Click or `R` |

## Pipe Types

| Shape | Opens | Description |
|---|---|---|
| H | RIGHT, LEFT | Straight horizontal |
| V | UP, DOWN | Straight vertical |
| UR | UP, RIGHT | Bend (corner) |
| RD | RIGHT, DOWN | Bend (corner) |
| DL | DOWN, LEFT | Bend (corner) |
| LU | LEFT, UP | Bend (corner) |

## Colors

| Color | Value |
|---|---|
| Red | Fire |
| Cyan | Water |
| Green | Nature |
| Yellow | Lightning |

## Scoring

- Base path score: 100 + 25 per pipe in path
- Combo multiplier: chain_size // 2 (e.g., chain of 4 → 2×, chain of 8 → 4×)
- SURGE bonus: +200 (when COMBO ≥ 4)

## Dev Status

- ✅ Core mechanic: pipe placement, BFS pathfinding, flow animation
- ✅ COMBO chain detection (adjacent same-color active pipes)
- ✅ SURGE particle burst and pipe clearing
- ✅ Source/Drain random edge placement
- ✅ Pressure system with game over
- ✅ Timer bar
- ✅ Hand UI with selection and rotation
- ✅ Floating score text
- ✅ Particle effects
- ⬜ Sound effects (pyxel.play)
- ⬜ Multiple difficulty levels

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/029_pipe_surge/main.py
```

## Headless Test

```bash
cd ~/repos/game-prototypes
uv run python prototypes/029_pipe_surge/test_imports.py
```
