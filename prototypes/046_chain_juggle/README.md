# CHAIN JUGGLE — Color-Match Juggling Game

**046_chain_juggle** — Keep-up juggling with color-match combos, compression, and rising hazard.

## Source

Reinterpreted from **game_idea_factory #1** (Score 31.25, alchemy deckbuilder):
- **"Synthesis compression"** → same-color COMBO compresses all same-color balls into a SUPER BALL
- **"Damage strengthens enemies"** → each same-color hit speeds up the ball (harder to juggle next time)
- Missed balls grow a hazard zone from below → game over when it reaches the paddle

All 10 generated ideas clustered in deckbuilder/dice/auto-shooter — a **keep-up/juggling** genre was selected to diversify the collection (no existing juggling prototype among 001-045).

## Engine

- Pyxel 2.x, 240×300, display_scale=2, 30fps
- Single-file `main.py`, ~480 lines

## Gameplay

### Core Mechanic
Juggle colored balls by bouncing them off your paddle. Consecutive same-color hits build COMBO for score multipliers. Missed balls cause the hazard floor to rise. When the hazard reaches your paddle, it's game over.

### Rules
- **Move** the paddle left/right to keep balls from falling
- **Same-color consecutive hits**: COMBO increases (+score × combo multiplier)
- **Speed risk**: Each same-color hit makes that ball 12% faster
- **Wrong-color hit**: COMBO resets to 1 (color switches)
- **COMPRESSION** (COMBO ≥ 4): All same-color non-super balls merge into one SUPER BALL
- **Super Ball**: 2× radius, 3× score, immune to speed increase for 3 seconds
- **Missed ball**: Hazard floor rises 10px, COMBO resets to 0
- **Game Over**: Hazard zone reaches paddle, OR more than 5 balls active

### Resources
| Resource | Description |
|---|---|
| COMBO | Consecutive same-color hits (score = 10 × combo) |
| Score | Points; super ball hits give 3× |
| Max Combo | Best combo this round (displayed on game over) |
| Hazard Y | Rising floor; starts off-screen, rises per miss |
| Balls Active | New ball spawns every 5 seconds, max 5 |

### Risk & Reward
- **Risk**: Same-color chain → faster ball → harder to juggle
- **Risk**: Ignoring a ball → hazard rises → less room to miss
- **Reward**: High combo → more points → compression → super ball → even more points
- **Reward**: Compression clears screen of same-color balls, creates massive score opportunity

### Difficulty Scaling
- Balls spawn every 5 seconds (up to 5 active)
- Each same-color hit accelerates the ball by 12%
- Speed increases compound — long chains make balls dangerously fast
- Hazard zone permanently reduces play area

## Controls

| Input | Action |
|---|---|
| ← → Arrow keys | Move paddle left/right |
| A / D | Alternate move keys |
| Space / Enter | Restart after game over |

## Color Reference

| Name | Pyxel Constant | Index |
|---|---|---|
| RED | `COLOR_RED` (8) | 0 |
| LIME | `COLOR_LIME` (11) | 1 |
| CYAN | `COLOR_CYAN` (12) | 2 |
| YELW | `COLOR_YELLOW` (10) | 3 |

## Dev Status

- [x] Core juggling physics (gravity, paddle bounce, wall bounce)
- [x] Color-match combo system (same-color chains, color switching)
- [x] Speed scaling (risk on same-color hits)
- [x] Compression mechanic (COMBO ≥ 4 → SUPER BALL)
- [x] Super ball (2× radius, 3× score, speed immunity, 3s timer)
- [x] Hazard zone (rising lava floor on misses)
- [x] Particle effects (hit bursts, miss explosions)
- [x] Screen shake on compression
- [x] Game over screen with stats
- [x] Fast restart (Space/Enter)
- [x] HUD (combo, score, active color, ball count, max combo)
- [x] 34 headless logic tests
- [ ] Build to Web (pyxel app2html)

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/046_chain_juggle/main.py
```

Headless tests:
```bash
cd ~/repos/game-prototypes
uv run python prototypes/046_chain_juggle/test_imports.py
```
