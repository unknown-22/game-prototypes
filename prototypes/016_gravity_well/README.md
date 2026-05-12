# 016 Gravity Well — Orbit & Collapse

**Source**: Reinterpretation of game_idea_factory idea #1 (dice/bag roguelite, score 32.2).
All 10 generated ideas clustered in deckbuilder/dice/auto-shooter — reinterpreted hooks into
a novel gravity-well orbital survival genre not yet in the collection.

| Hook from idea #1 | Reinterpretation |
|---|---|
| "Log/replay as asset" | Resonance echoes from movement trail attract mass |
| "Chain collapse" | Orbital mass implosion with chain combo scoring |
| mana | Energy resource for gravity pulse ability |
| heat | Risk meter — too much orbiting mass = overheat = game over |

**Engine**: Pyxel 2.x, 400×300, display_scale=1

## Gameplay

You control a **gravity core**. Colorful mass particles drift in from screen edges.
Mass within your gravity radius is pulled in and enters orbit around you.
Press **SPACE** to collapse all orbiting mass — each piece scores based on its value
multiplied by its chain position. The more mass you collapse at once, the bigger the
chain multiplier!

**Risk**: Each orbiting mass generates **Heat**. If Heat reaches 100%, game over.
Collapsing orbiting mass reduces Heat. Manage the tension between building a big
orbital swarm (risky!) and collapsing early (safe but lower score).

**Energy**: Builds over time. Spend 40 energy (E key) for a **Gravity Pulse** —
temporarily expands capture radius to 150px for 10 frames.

**Resonance Echoes**: Your movement trail leaves behind fading gravity wells that
also attract drifting mass — your path becomes an asset!

**Combo**: Consecutive collapses without dying earn a combo multiplier bonus.

## Controls

| Key | Action |
|---|---|
| WASD / Arrow keys | Move gravity core |
| SPACE | Collapse all orbiting mass (chain combo) |
| E | Gravity Pulse (costs 40 energy, expands capture radius) |
| R | Restart after game over |

## Core Loop

1. Mass drifts in from edges
2. Move to capture mass into orbit
3. Build orbital swarm (risk: heat builds)
4. SPACE → collapse for chain combo score
5. Manage heat / energy / spawn rate

## Dev Status

- ✅ Core mechanic: gravity capture + orbital collapse
- ✅ Chain combo scoring
- ✅ Heat risk system
- ✅ Energy + gravity pulse ability
- ✅ Resonance echoes (movement trail)
- ✅ Particle burst + floating text effects
- ✅ Difficulty ramp (spawn rate increases)
- ✅ Game over + quick restart
- ✅ High score tracking
- ⬜ Sound effects
- ⬜ Enemy entities that threaten the player
- ⬜ Multiple mass types with special effects

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/016_gravity_well/main.py
```
