# ECHO TRON

**Source:** game_idea_factory #1 (Score 32.55)
- "log/replay as asset" → movement trail becomes permanent arena walls
- "CA grid fills up, must control" → trails fill the grid, constraining space

**Genre:** Light Cycles / Tron (arena survival) — first of this genre in the collection.

**Engine:** Pyxel 2.x, 240×212, display_scale=2

## Core Mechanic

Navigate a light cycle through an arena where every movement leaves a permanent wall trail. Enemy bikes also leave trails. The arena progressively fills with walls, creating an ever-tightening death trap. Collect same-color gems consecutively to build COMBO score multipliers. Trap enemies against walls to score kills.

**The most fun moment:** 敵を壁際に追い詰め、自分のトレイルで包囲して倒す瞬間 (trapping enemies between your trail and the outer walls, watching them crash).

## Controls

| Key | Action |
|-----|--------|
| ↑ ↓ ← → | Turn light cycle (can't reverse) |
| SPACE | Restart after game over |

## Rules

- **Trail walls:** Every bike leaves a colored wall at its previous position each tick
- **No reverse:** You cannot turn 180° — must turn left, right, or go straight
- **Gem collection:** Drive over gems to collect them. Same color consecutively builds COMBO (× multiplier on gem score). Different color resets COMBO to ×1
- **Enemies:** 3 AI bikes that avoid walls and seek open space. They die on contact with any wall
- **Speed:** Game accelerates over time (tick interval decreases from 10→4 frames)
- **Victory:** Eliminate all 3 enemies (+200 base + max_combo×50 bonus)
- **Game Over:** Your bike hits any wall (your own, enemy, or boundary)

## Scoring

| Action | Points |
|--------|--------|
| Survive 1 tick | +1 |
| Collect gem (no combo) | +10 |
| Collect gem (combo×N) | +10 × N |
| Enemy kill | +100 + combo×20 |
| Player death | +max_combo×20 |
| All enemies defeated | +200 + max_combo×50 |

## HUD

- `SCORE`: Total points
- `COMBO xN`: Current same-color streak (shown when ≥2)
- `SPD:NNN%`: Current speed relative to max
- `K:N`: Enemies killed

## Resource System

- **Colors (4):** RED (8), LIME (11), CYAN (12), ORANGE (9)
- **COMBO:** Consecutive same-color gem collections — multiplier on points, resets on color change
- **Speed:** Increases with survived ticks — risk/reward tension between collecting gems and survival

## Dev Status

- ✅ Core movement + wall trail system
- ✅ 3 AI enemies with open-space pathfinding
- ✅ Gem collection + COMBO chain system
- ✅ Particle effects (death, collection)
- ✅ Screen shake on death
- ✅ Speed acceleration over time
- ✅ Head-on collision resolution
- ✅ Game over + restart
- ✅ Victory condition (all enemies dead)
- ✅ 17 headless logic tests
- ⬜ Sound effects
- ⬜ Multiple waves
- ⬜ Power-ups

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/047_echo_tron/main.py
```

## How to Test

```bash
uv run python prototypes/047_echo_tron/test_imports.py
```
