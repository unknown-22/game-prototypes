# Synth Surge (010)

Auto-shooter with color-match synthesis. Collect same-color shards to trigger super abilities.

**Source**: Game Idea #6 (Score 31.45) — 厄災封印/暴走制御テーマのヴァンサバ亜種
- Hooks: 効果が『合成』されて1枚に圧縮される, 戦闘は数字とアイコン中心
- Generated: 2026-05-11

## Engine

- Pyxel 2.x, 400×300, display_scale=2

## Gameplay

### Core Mechanic

Kill enemies → collect colored shards → match 3 same-color in synthesis slots → devastating super ability.

The 3-slot reactor is a FIFO queue: collecting a new shard pushes out the oldest. Your skill is choosing WHICH shards to pick up — grabbing a mismatched shard breaks your chain. Positioning matters: get close to shards you need, stay away from shards that would ruin your combo.

### The Fun Moment

Watching 3 matching shards fuse together into a screen-shaking supernova that wipes all enemies — then immediately trying to line up the next synthesis.

### Super Abilities (by color)

| Color | Name       | Effect                           |
|-------|------------|----------------------------------|
| RED   | INCINERATE | Destroy all enemies on screen    |
| BLUE  | FROST WALL | Freeze all enemies for 3 seconds |
| GREEN | REGEN      | Restore 2 HP                     |
| YELLOW| OVERRIDE   | Double fire rate for 4 seconds   |

### Risk/Reward

- Collecting the wrong shard breaks your chain — avoid shards you don't need
- RED synthesis clears the screen but costs you a potential BLUE freeze
- GREEN heals but means you gave up on an offensive synthesis
- Shards expire after ~6 seconds — don't wait too long

### Difficulty Scaling

- Enemy spawn rate increases over time (every 10 seconds)
- Enemy HP increases (multi-hit enemies appear)
- Enemy speed increases

## Controls

| Key          | Action            |
|--------------|-------------------|
| Arrow / WASD | Move player       |
| R (game over)| Retry             |
| SPACE (game over) | Retry       |

Auto-fire targets the nearest enemy.

## UI Reference

- **Top-center**: 3 synthesis slots (R/B/G/Y)
- **Top-left**: SCORE, SYNTH count
- **Top-right**: Time survived
- **Bottom-center**: HP bar (5 HP max)
- **Bottom-left/right**: Active effect timers (FREEZE/OVERRIDE)

## Dev Status

- ✅ Core auto-shooter gameplay (movement, auto-fire, enemy spawning)
- ✅ 4-color shard system with drop-on-kill
- ✅ 3-slot synthesis chain (FIFO queue)
- ✅ 4 super abilities (RED/BLUE/GREEN/YELLOW)
- ✅ Particle effects, floating text, screen shake
- ✅ Difficulty scaling over time
- ✅ Game over screen with retry
- ✅ Invulnerability frames after damage
- ⬜ Persistent high score
- ⬜ Wave/boss system
- ⬜ More enemy types

## How to Run

```bash
cd ~/repos/game-prototypes && uv run python prototypes/010_synth_surge/main.py
```
