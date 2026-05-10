# OVERLOAD — Power Core Survival Auto-Shooter

**Prototype 007** | Based on Game Idea #2 (Score 31.4)

> "Unleashing a chain-reaction overload that cascades through every enemy
> on screen is the most satisfying moment."

## Source

- **Idea**: ヴァンサバ亜種（抽象敵・UI主導）/ 発電所（過負荷と放電）
- **Score**: 31.4 (pitch=3.4, video=4.0, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0)
- **Hooks**: ログ/リプレイが資産 / 落下/重力で連鎖崩壊
- **Generated**: 2026-05-10

## Engine

- **Pyxel 2.x**, 400×300, display_scale=2, 60 FPS
- Pure Python 3.12, single-file

## Gameplay

OVERLOAD is a **Vampire Survivors-like auto-shooter**. You control a power core
that drifts through space, auto-firing at nearby enemies. Defeated enemies drop
energy orbs that fill your **Charge meter**. High charge boosts your fire rate,
but when charge hits 100 you can trigger **OVERLOAD** — a screen-clearing
explosion that costs 15 HP.

### Core Mechanic: Risk/Reward Charge Management

- **Charge builds passively** from energy orbs dropped by killed enemies
- **High charge** = faster auto-fire (0.5s → 0.2s between shots)
- **At 100 charge**: press SPACE to OVERLOAD
  - Massive AOE damage to all enemies (50 + wave×5 base), chain reactions
  - Costs **15 HP** — every time
  - Chain kill propagation: killed enemies deal 50% damage to enemies within 60px
- **Decision**: hold charge for DPS boost, or spend it + HP for screen clear?

### Wave System

- Each wave lasts 30 seconds
- Enemies gain more HP and speed per wave
- Spawn rate increases per wave (45f → 12f minimum)
- Wave clear grants +10 HP (up to max 100)

### Scoring

- 1 point per enemy killed by bullets (× wave multiplier)
- 10 points per enemy killed by overload chain (× wave multiplier)
- Goal: maximize score across waves

## Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move power core |
| SPACE | Trigger OVERLOAD (when charge ≥ 100) |
| R | Restart (on game over screen) |

## Dev Status

- ✅ Core movement + auto-fire
- ✅ Enemy spawning (edge-based) + AI (move toward player)
- ✅ Energy orb drops + collection
- ✅ Charge meter with fire rate scaling
- ✅ OVERLOAD ability with chain reactions
- ✅ Wave system with scaling difficulty
- ✅ HP system with contact damage
- ✅ Particle effects + floating damage numbers
- ✅ Screen shake on hit/overload
- ✅ Game over screen with score
- ✅ Fast restart (R key)
- ⬜ Sound effects (pyxel.play)
- ⬜ Enemy type variety
- ⬜ Power-up pickups
- ⬜ High score persistence

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/007_overload/main.py
```

## Headless Test

```bash
cd ~/repos/game-prototypes
uv run python prototypes/007_overload/test_imports.py
```
