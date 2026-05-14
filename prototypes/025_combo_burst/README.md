# COMBO BURST — Color-Match Target Shooting Gallery

**Prototype 025** — Reinterpreted from game_idea_factory #1 (score 31.8, "space-mining deckbuilder with floor rule changes + chain collapse").

| Aspect | Detail |
|---|---|
| **Genre** | Target shooting / reaction gallery |
| **Engine** | Pyxel 2.x, 256×256, 60fps, display_scale=2 |
| **Core mechanic** | Maintain same-color streak → COMBO ≥ 3 triggers CHAIN BURST |
| **Input** | Mouse aim + left click to shoot |
| **Hooks transferred** | "floor rule changes" → color-locked combo constraint; "chain collapse/amplify/compress" → chain burst explosions |

## Gameplay

Click same-colored targets consecutively to build your COMBO multiplier. At COMBO ≥ 3, every hit triggers a CHAIN BURST — an explosion that cascades through nearby same-colored targets for massive score.

- Same-color hit → COMBO +1, score × COMBO
- Different color hit → COMBO resets (you can start a new chain)
- Miss (click empty space) → COMBO resets
- Targets that survive 3 seconds → escape and cost 1 HP
- Rapid fire builds HEAT — at ≥70 heat, score is doubled but spawns accelerate

## Win/Lose

- **Victory**: Survive 60 seconds with HP > 0
- **Defeat**: HP reaches 0

## Controls

- **Mouse move**: Aim crosshair
- **Left click**: Shoot at crosshair position
- **Title/Game Over**: Click or Space to start/restart

## Scoring

- Base: 10 pts × combo × heat_bonus
- Chain burst targets: 15 pts × (combo + chain_count) × heat_bonus
- Heat bonus: ×2 when heat ≥ 70

## Dev Status

- ✅ Core shooting + combo system
- ✅ Chain burst propagation
- ✅ Particle effects
- ✅ Floating score text
- ✅ Screen shake on big chains
- ✅ Heat system with risk/reward
- ✅ HUD (score, combo, HP, timer, heat bar)
- ✅ Title screen + game over screen
- ✅ Headless logic tests
- ⬜ Sound effects
- ⬜ Wave modifiers (rule-shifting per wave)

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/025_combo_burst/main.py
```

## Source Idea

Generated 2026-05-14 by game_idea_factory (seed: timestamp-based).
Original idea: Space mining deckbuilder roguelite (score 31.8).
Hooks: each floor changes one rule; chain collapse/amplify/compress UI effects.
