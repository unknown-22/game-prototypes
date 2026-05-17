# SPLIT CHAIN

**Prototype 035** — Asteroids-like shooter with color-match chain splitting.

## Source

Reinterpreted from game_idea_factory idea #1 (score 31.85):
- **"log/replay as asset"** → COMBO carries forward into split behavior (higher COMBO = more asteroid fragments)
- **"one-color-per-turn"** → bullet color cycling constraint (shoot matching-color asteroid for COMBO)
- Also incorporates idea #3's **"split across paths → converge → explode"** hook

**Why reinterpretation?** All 10 generated ideas clustered in deckbuilder/auto-shooter/dice genres. Asteroids-like is a classic arcade genre not yet in the prototype collection (34 prototypes, none are rotate+thrust ship shooters).

## Engine

- **Pyxel 2.x**, 256×256, display_scale=2, 60 FPS
- Python 3.12+ with type hints

## Gameplay

### Core Mechanic: Color-Match Chain Splitting

Your ship's bullet color cycles through 4 elements (RED, YELLOW, LIME, CYAN). Press **C** to cycle. Shoot same-color asteroids to build COMBO — each consecutive same-color kill increases your score multiplier and triggers extra fragment splitting at COMBO 3+.

**The most fun moment**: Chaining through a dense cluster of same-colored asteroids, watching them split into extra fragments that cascade into more kills.

### Rules

1. **Asteroid Splitting**: LARGE → 2 MEDIUM, MEDIUM → 2 SMALL, SMALL → destroyed
2. **COMBO Bonus**: COMBO ≥ 3 → split produces +1 extra child (more chaos, more score potential)
3. **COMBO Burst**: COMBO ≥ 5 → particle explosion on kill
4. **Wrong Color**: Shooting wrong-colored asteroid resets COMBO to 0, no extra split bonus
5. **Color Change**: Changing bullet color (C) resets COMBO
6. **3 Lives**: Ship destruction costs a life, respawns at center with 1.5s invulnerability
7. **Difficulty Scaling**: New asteroids spawn every 10 seconds, increasing in frequency over time

### Scoring

| Asteroid Size | Base Score |
|---|---|
| LARGE (r=14) | 100 |
| MEDIUM (r=9) | 50 |
| SMALL (r=5) | 20 |

Score multiplier = 1 + COMBO × 0.5 (COMBO 1 = 1.5x, COMBO 5 = 3.5x)

### Resources

- **Lives**: Start with 3, game over at 0
- **COMBO**: Chain same-color kills for multiplier
- **Screen space**: Manage asteroid density — more splits = more danger

### Risk & Reward

- Building COMBO means hunting same-color asteroids while ignoring others — they accumulate
- Higher COMBO creates MORE fragments (3 children instead of 2), increasing screen danger
- COMBO resets on wrong-color kill or color change, forcing commitment to one color

## Controls

| Key | Action |
|---|---|
| ← → or A/D | Rotate ship |
| ↑ or W | Thrust |
| Z or Space | Shoot (12-frame cooldown) |
| C | Cycle bullet color |

## Dev Status

- ✅ Core mechanic: color-match asteroid splitting with COMBO chain
- ✅ Asteroid types: LARGE/MEDIUM/SMALL with jagged polygon rendering
- ✅ Ship: rotate+thrust physics, screen wrapping, invulnerability blink
- ✅ Particle system: death explosions, COMBO burst effects
- ✅ Thrust flame visual
- ✅ HUD: score, high score, lives, COMBO indicator, bullet color indicator
- ✅ Title screen with instructions
- ✅ Game over screen with retry
- ✅ Progressive difficulty (spawn rate increases)
- ✅ Headless logic tests (30+ tests)
- ⬜ Sound effects
- ⬜ Screen shake on death
- ⬜ UFO/saucer enemy
- ⬜ Power-ups

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/035_split_chain/main.py
```

## Headless Tests

```bash
uv run python prototypes/035_split_chain/test_imports.py
```
