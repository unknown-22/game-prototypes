# CHROMA CROSS (057_chroma_cross)

**Color-match lane crossing game** — Crossy Road / Frogger reinterpreted with alchemy synthesis mechanics.

## Source

Reinterpreted from **game_idea_factory #1** (Score 32.0):
- **Original**: Alchemy synthesis deckbuilder roguelite
- **Hooks reused**:
  - "Synthesis/compression" → COMBO chain building → SYNTHESIS super mode
  - "Split/converge across paths → explode" → crossing lanes with branching obstacle patterns

**Why reinterpretation**: All 10 generated ideas clustered in deckbuilder/dice/auto-shooter genres (all already represented in the collection). Picked the highest-scored idea with the most transferable hooks and reinterpreted into a **lane crossing** game — a genre not yet built in this monorepo.

## Engine

- **Pyxel** 2.x
- Screen: 256×256
- Python 3.12+

## Gameplay

### Core Mechanic

Cross 8 colored lanes from bottom to top. Each lane has moving colored obstacles. Match your player's color to the obstacle color to pass safely and build COMBO chains. Reach the top to level up — difficulty increases each level.

### The "One Fun Moment"

> Threading through a dense lane, color-matching obstacle after obstacle at high speed, triggering SYNTHESIS super mode, and blasting through the final lanes invincible — that's the peak.

### Rules

1. **Move** with Arrow keys or WASD
2. **Cycle color** with SPACE (cycles RED → GREEN → YELLOW → BLUE)
3. **Matching obstacles** (same color as player): safe passage, COMBO +1
4. **Wrong color obstacles**: -1 HP, COMBO reset, brief invincibility
5. **COMBO >= 5**: Activates **SYNTHESIS** super mode (3 seconds)
   - All colors become safe
   - 3× score multiplier
   - Rainbow visual effects
6. **Reach the top lane**: Score bonus, level up, reset to bottom
7. **HP = 0**: Game Over

### Risk/Reward

- **Stay on one color** to build COMBO → SYNTHESIS faster, but risk wrong-color hits
- **Change colors frequently** for safety but slower COMBO buildup
- **Go for top quickly** for level-up points, or **farm COMBO** in current lane pattern
- **SYNTHESIS mode**: time window to aggressively push for top

### Difficulty Scaling

- Level 1: 1–2 obstacles per lane, slow speed
- Level 4+: 2–3 obstacles per lane
- Level 7+: 3–4 obstacles per lane, faster speed
- Speed scales +15% per level

## Controls

| Key | Action |
|-----|--------|
| Arrow Keys / WASD | Move player |
| SPACE | Cycle player color (RED→GREEN→YELLOW→BLUE) |
| SPACE / ENTER | Start game / Retry |

## Color Reference

| Name | Pyxel Color | Value |
|------|-------------|-------|
| RED | `pyxel.COLOR_RED` | 8 |
| GREEN | `pyxel.COLOR_GREEN` | 3 |
| YELLOW | `pyxel.COLOR_YELLOW` | 10 |
| BLUE (LIGHT) | `pyxel.COLOR_LIGHT_BLUE` | 6 |

## Dev Status

- [x] Core lane crossing mechanic
- [x] 4-color system with SPACE cycling
- [x] COMBO chain building with timer
- [x] SYNTHESIS super mode (COMBO >= 5)
- [x] DAMAGE_COOLDOWN invincibility frames
- [x] HP system (5 hearts)
- [x] Level-up on reaching top
- [x] Difficulty scaling (obstacle count + speed)
- [x] Particle effects (hit, super activation, level up)
- [x] Floating score text
- [x] Obstacle wrapping
- [x] Diagonal movement normalization
- [x] Game over screen with stats
- [x] Title screen with instructions
- [x] 43 headless logic tests
- [x] HTML build deployed to docs/

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/057_chroma_cross/main.py
```

### Headless Tests

```bash
uv run python prototypes/057_chroma_cross/test_imports.py
```

## Architecture

Single-file Pyxel game (~470 lines). Structure:

- `Phase` enum: TITLE, PLAYING, GAME_OVER
- `Obstacle` dataclass: lane obstacles with position, size, color, speed
- `Particle` / `FloatingText` dataclasses: visual effects
- `Game` class: all game logic and rendering
  - `_init_state()`: reset mutable state (called by `__init__` and `reset`)
  - `_update_player()`: input handling, movement, color cycling, boundary clamping
  - `_update_obstacles()`: horizontal movement + screen wrapping
  - `_update_collisions()`: AABB overlap checks, color-matching, damage, COMBO
  - `_update_timers()`: combo timeout, damage cooldown, super mode duration
  - `_check_goal()`: top-lane detection → level up + score
  - `draw()`: title screen, lane lines, obstacles, player, particles, floating texts, HUD, game over overlay
