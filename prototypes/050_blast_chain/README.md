# Blast Chain — Bomberman-style Color-Chain Grid Action

**Source:** Reinterpreted from Idea #1 (Score 31.95) — dice/bag roguelite "logistics/flow optimization"
- Transfer hook: "synthesis compression" → same-color bomb chain reactions
- Transfer hook: "circuit/pipe visualization" → chain blast propagation paths

**Genre:** Bomberman-like / grid action (NEW to the collection)

**Engine:** Pyxel 2.x, 256×200, display_scale=3

## Gameplay

### Core Mechanic
Place bombs on a grid. Bombs have 5 colors (randomly assigned). When a bomb explodes, any same-color bomb caught in the blast radius triggers a **CHAIN** — exploding with a bigger radius and adding to the combo multiplier. Clear all enemies to advance waves.

### Most Fun Moment
Setting up 3+ same-color bombs in a cluster and watching the chain cascade rip through the arena, wiping out enemies and racking up a 5x+ combo.

### Rules
- Move freely within the grid (Arrow keys / WASD)
- Place bombs with SPACE / Z / X (max 3 bombs out at once)
- Bombs explode after ~1.5 seconds (90 frames)
- **Same-color chain**: bombs of matching color detonate each other → COMBO++ → bigger blast radius
- **Different color**: still detonates but no combo bonus
- Enemies wander randomly and speed up each wave
- Touching an enemy = lose a life
- Caught in any explosion = lose a life
- 3 lives, game over at 0

### Risk/Reward
- Higher combos = more points per enemy kill
- But chaining means more explosions near you — don't get greedy!
- Place bombs strategically so chain paths don't intersect your position

### Progression
- Wave 1: 3 slow enemies
- Each wave: +1 enemy (max 10), enemies get faster
- Wave clear bonus: 50 × wave number
- Score formula: (10 + combo×8) × (combo//2 + 1) per enemy

## Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move |
| SPACE / Z / X | Place bomb |
| SPACE / Z / R | Start / Retry |

## Dev Status

- ✅ Core grid movement + bomb placement
- ✅ 5-color bomb system
- ✅ Same-color chain reaction with combo multiplier
- ✅ Chain blast radius amplification
- ✅ Enemy AI (random wander + wave escalation)
- ✅ Player death (enemy contact + explosion)
- ✅ Wave system with escalation
- ✅ 3-life system with respawn
- ✅ Particle effects (death + enemy kills)
- ✅ Explosion animation (expanding ring)
- ✅ HUD (score, wave, lives, combo, max combo, color legend)
- ✅ Title screen / Game Over screen
- ✅ Ruff + ty checks passing
- ⬜ Sound effects
- ⬜ Power-ups (extra bomb, speed, blast range)
- ⬜ Destructible walls

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/050_blast_chain/main.py
```
