# PONG SURGE

**Prototype #039** — Color-match Pong rally.

## Source

Reinterpreted from game idea #1 (score 32.6, 2026-05-18):
- "Log/replay as asset" → rally history builds COMBO
- "Chain collapse/expansion/compression" → SURGE mode with screen shake & double points

**Genre gap filled**: First Pong variant in the collection. All 10 generated ideas clustered in deckbuilder/dice/auto-shooter; reinterpreted hooks into classic Pong with color-match twist.

## Engine

- **Pyxel** 2.x
- **Screen**: 256×192, display_scale=3
- **FPS**: 60

## Gameplay

Classic Pong with a color-matching twist. The ball and both paddles have one of 4 colors (RED, GREEN, YELLOW, CYAN).

- **Same-color hit**: COMBO +1, ball speed increases, score multiplier applies
- **Wrong-color hit**: COMBO resets to 0, ball speed resets
- **COMBO ≥ 5**: SURGE mode activates (3 seconds)
  - 3× score multiplier
  - Screen shake on activation
  - Glowing ball with pulse effect
  - Background color shift
- **Pass the AI**: +10 bonus points, ball resets
- **Ball passes player**: GAME OVER

### Risk/Reward

Higher COMBO = faster ball = harder to defend, but SURGE gives massive score rewards. Decide whether to play safe (reset COMBO intentionally) or push for SURGE.

## Controls

| Key | Action |
|---|---|
| ↑ / W | Move paddle up |
| ↓ / S | Move paddle down |
| SPACE / E | Cycle paddle color |
| R | Restart (game over screen) |

## Color Reference

| Color | Paddle/ball appearance |
|---|---|
| RED (pyxel.COLOR_RED, 8) | Fire |
| GREEN (pyxel.COLOR_GREEN, 11) | Nature |
| YELLOW (pyxel.COLOR_YELLOW, 10) | Lightning |
| CYAN (pyxel.COLOR_CYAN, 13) | Ice |

## Dev Status

- ✅ Core Pong physics (ball bounce, paddle collision)
- ✅ Color-match COMBO system
- ✅ SURGE mode (double score, particles, screen shake)
- ✅ AI opponent with color cycling
- ✅ Particle effects (hit sparks, SURGE burst, score celebration)
- ✅ HUD (score, combo, max combo, rally hits, speed %)
- ✅ Game over / restart flow
- ✅ Headless import tests (test_imports.py)
- ⬜ Web build (pyxel app2html)
- ⬜ AI difficulty scaling with rally length

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/039_pong_surge/main.py
```

Run headless tests:

```bash
uv run python prototypes/039_pong_surge/test_imports.py
```
