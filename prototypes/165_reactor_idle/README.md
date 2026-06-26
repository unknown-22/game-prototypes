# CHAIN REACTOR — 165_reactor_idle

**Idle/Incremental Reactor Grid** — first idle/incremental clicker genre in the collection.

## Source
Reinterpreted from Idea #1 (Score 31.75): ハッキング（回路/ログ）ヴァンサバ亜種
- "ログ/リプレイが資産" → past production adds permanent passive bonus
- "回路/パイプで可視化（流れて増幅する）" → energy flows through connected reactor chains

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Python 3.12+ with type hints

## Gameplay
Place reactors on a 4×4 grid. Adjacent same-color reactors form COMBO chains that multiply auto-production. Energy accumulates passively every 0.5 seconds (30 frames).

- **Win**: Reach 1000 total energy
- **Lose**: Heat reaches 100 (reactors generate heat per tick)
- **SUPER MODE**: COMBO ≥ 5 consecutive same-color placements → 5 seconds of 3× production
- **Cooling**: Right-click or SPACE to spend 30 energy and reduce heat by 20

### Core Mechanic
"The most fun moment": placing a reactor that completes a 5+ same-color chain, triggering SUPER MODE where production explodes 3× — the screen fills with particles and soaring energy numbers.

### Risk & Reward
More reactors = more production but also more heat. Spend energy on cooling to stay safe, or push your luck to reach 1000 faster. SUPER MODE gives 3× production but heat still accumulates normally.

## Controls
- **Left click**: Place reactor (empty cell) or upgrade tier (existing reactor)
- **Right click / SPACE**: Emergency cooling (-20 heat, costs 30 energy)
- **R / Click**: Retry from game over screen

## Reactor Tiers
| Tier | Production/Tick | Upgrade Cost |
|------|----------------|--------------|
| 1    | 1              | —            |
| 2    | 3              | 20 energy    |
| 3    | 7              | 60 energy    |

## Dev Status
- ✅ Core gameplay: placement, production, combo, super mode
- ✅ Heat/overheat risk system
- ✅ Cooling mechanic
- ✅ Tier upgrade system
- ✅ Particle + floating text systems
- ✅ 3 screens: Title, Playing, Game Over
- ✅ 61 headless tests
- ✅ Web build (docs/165_reactor_idle.html)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/165_reactor_idle/main.py
```

Web version: open `docs/165_reactor_idle.html` in a browser.
