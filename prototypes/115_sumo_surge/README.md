# SUMO SURGE — 色合わせ相撲

**Source**: game_idea_factory #1 (Score 32.0)
- Hooks: "synthesis/compression" → COMBO→SUPER SUMO, "split/converge/explode" → dodge→corner trap→ring-out
- Reinterpreted from deckbuilder/dice/auto-shooter cluster into **sumo wrestling** (first in collection!)

## Engine
- Pyxel 2.x, 320×240, 60fps

## Gameplay
Top-down color-match sumo wrestling in a circular dohyo (ring).

- **Core mechanic**: Push the AI opponent. Same-color consecutive pushes build COMBO.
- **SUPER SUMO**: COMBO ≥ 4 triggers 5s rainbow super mode (3x push power, all pushes match).
- **HEAT risk**: Wrong-color push resets COMBO and adds HEAT. HEAT ≥ 100 = stun (1.5s).
- **Win**: Push opponent outside the ring.
- **Lose**: Get pushed out OR 90-second timer expires.
- **Score**: COMBO × 100 + time bonus on ring-out.

## Controls
- Arrow keys (or WASD): Move player rikishi
- Push happens automatically on contact
- SPACE: Start / Restart

## Color System (4 colors)
| Color | Pyxel Constant | Int |
|-------|---------------|-----|
| RED | COLOR_RED | 8 |
| GREEN | COLOR_GREEN | 3 |
| BLUE | COLOR_DARK_BLUE | 5 |
| YELLOW | COLOR_YELLOW | 10 |

## Dev Status
- ✅ Core push + color-match COMBO
- ✅ SUPER SUMO mode
- ✅ HEAT stun risk system
- ✅ Ring-out victory/defeat
- ✅ Timer (90s)
- ✅ Particle effects
- ✅ 43 headless tests
- ✅ Web build (docs/115_sumo_surge.html)
- ⬜ AI difficulty levels
- ⬜ Sound effects

## How to Run
```bash
uv run python prototypes/115_sumo_surge/main.py
```

## How to Test
```bash
uv run pytest prototypes/115_sumo_surge/test_imports.py -v
```
