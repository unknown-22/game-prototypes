# 019 CHAIN REACTOR — Top-Down Arena Shooter

> **Source:** Reinterpreted from idea #1 (score 31.95) — "chain propagation" and "same-color synergy" hooks applied to a top-down arena shooter genre (not present in existing prototypes).

## Engine

- **Pyxel** 2.x, 400×300, display_scale=2
- Python 3.12, single-file, ~460 lines

## Gameplay

**Core mechanic:** Destroy one enemy to trigger a **cascading chain reaction** through all same-color enemies within range. The longer the chain, the higher the score multiplier (chain² × base).

The fun moment: *Watching a single well-placed shot trigger a cascading chain reaction through a dense cluster of same-colored enemies — all exploding in rapid succession.*

### Rules

- **4 element colors:** FIRE (red), ICE (cyan), LIGHTNING (yellow), NATURE (lime)
- **Chain propagation:** Killing an enemy propagates damage to all same-color enemies within **55px radius**, continuing recursively
- **Heat system:** Each shot builds heat (2.5/shot). At **100 HEAT**, you **OVERHEAT** — can't shoot for 50 frames, enemies keep moving
- **HP = 3:** Contact with enemies deals 1 damage + brief invulnerability (90 frames)
- **Waves escalate:** Each wave spawns more/faster enemies (up to 40 on screen)
- **Score:** 10 pts per kill; chains earn `10 × chain_length²` bonus

## Controls

| Input | Action |
|---|---|
| WASD / Arrow keys | Move player |
| Mouse move | Aim |
| Mouse left button (held) | Shoot toward cursor |
| SPACE / Click | Start game / Retry |

## Risk & Reward

- **Cluster enemies together** before shooting → bigger chains, higher score
- **BUT** more enemies near you = higher risk of collision
- **Rapid fire** builds heat fast → risk of overheat stun at critical moments
- **Heat decays** slowly (0.4/frame) — pace your shots

## Visual Feedback

- Chain combo counter flashes at screen center
- Screen shake proportional to chain size
- Particle explosions for every killed enemy
- Floating score popups ("CHAIN x5!", "+250")
- Overheat: red flash overlay + "Can't shoot!" warning
- Invulnerability: player blinks after taking damage

## Dev Status

- ✅ Core: enemy spawning, movement, player movement, shooting
- ✅ Chain reaction BFS propagation system
- ✅ Heat/overheat system with visual feedback
- ✅ Particle system and floating text
- ✅ Screen shake
- ✅ Wave escalation
- ✅ HP, score, combo display HUD
- ✅ Title screen, game over screen, retry loop
- ✅ Headless tests (import + logic verification)
- ⬜ Sound effects
- ⬜ Power-ups / special abilities
- ⬜ High score persistence

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/019_chain_reactor/main.py
```

## Run Tests

```bash
uv run python prototypes/019_chain_reactor/test_imports.py
```
