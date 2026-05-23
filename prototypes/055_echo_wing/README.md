# ECHO WING (055)

**Side-scrolling shoot-em-up with color-match COMBO chains.**

## Source

Reinterpreted from game_idea_factory #1 (Score 32.15):
- "log/replay as asset" → echo orbital follows ship with delay, doubling firepower
- "CA grid spread" → CHAIN BURST: BFS propagation through same-color enemies at COMBO ≥ 3
- "one-color-per-turn" → weapon cycles through 4 colors

All 10 generated ideas clustered in deckbuilder/dice/auto-shooter — reinterpreted into side-scrolling shmup, the first of its kind in this collection.

## Engine

- Pyxel 2.x
- 256×224, 30 FPS, display_scale=2

## Gameplay

### Core mechanic
A side-scrolling shoot-em-up where you pilot a ship through waves of color-coded enemies. Your weapon fires in one of 4 colors. Kill same-color enemies consecutively to build COMBO multipliers. At COMBO ≥ 3, killing a same-color enemy triggers **CHAIN BURST** — BFS propagation that cascades through nearby same-color enemies.

### The fun moment
Building a 5+ COMBO chain and watching the BFS chain burst cascade through an entire enemy formation in one explosive moment.

### Rules
- **Auto-fire**: Ship auto-fires bullets matching current weapon color
- **COMBO**: Consecutive same-color kills build combo multiplier (×1.5 per level)
- **Wrong-color kills**: Reset combo to 1
- **CHAIN BURST** (COMBO ≥ 3): Killing a same-color enemy triggers BFS through nearby same-color enemies (radius 45px)
- **Echo Orbital**: A ghost ship follows your movement with 15-frame delay, providing secondary fire
- **HEAT**: Kills build heat (2/kill, 20/burst). At 100% heat, weapons overheat (can't fire)
- **HP**: 5 HP, invincibility frames after taking damage. Getting hit resets combo.

### Enemy types
- **NORMAL**: 1 HP, radius 10, speed ×1.0, score ×1.0
- **FAST**: 1 HP, radius 7, speed ×1.8, score ×1.5
- **TANK**: 3 HP, radius 12, speed ×0.6, score ×2.0

### Formations
Enemies spawn in formations (column, V-shape, diagonal, diamond, wave) from the right edge. Speed increases over time.

### Scoring
- Kill: `BASE_SCORE × (1 + (combo-1) × 0.5) × enemy_score_mult`
- Chain burst bonus: `burst_kills × 50 × combo`

## Controls

| Key | Action |
|---|---|
| ↑↓ or W/S | Move ship |
| Q | Cycle weapon color left |
| E or SPACE | Cycle weapon color right |
| ENTER | Restart (game over screen) |

## Dev Status

- [x] Side-scrolling with parallax starfield
- [x] 4-color weapon system with Q/E cycling
- [x] Auto-fire + echo orbital secondary fire
- [x] 3 enemy types with distinct visuals
- [x] 5 formation patterns
- [x] COMBO system (score multiplier)
- [x] CHAIN BURST: BFS same-color propagation
- [x] HEAT system (overheat at 100%)
- [x] HP system with invincibility frames
- [x] Particle explosions and floating text
- [x] HUD (score, combo, HP, heat bar, timer, weapon color)
- [x] Game Over screen with stats
- [x] 90-second survival mode

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/055_echo_wing/main.py
```
