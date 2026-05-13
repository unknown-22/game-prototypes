# 022 — CALAMITY SIEGE

Space-invaders style gallery shooter. First fixed-shooter prototype in the collection.

## Source

Reinterpreted from [game_idea_factory](https://github.com/unknown-22/game_idea_factory) idea #1:
- **Score**: 32.05
- **Theme**: Calamity Sealing (Runaway Control) / Deckbuilder Roguelite
- **Hooks**: Effect fusion/compression, cost = future hand
- **Reinterpretation**: "Runaway control" → enemies march down; if they reach the bottom, they ESCAPE and return as stronger elites. "Fusion/compression" → consecutive same-color kills build COMBO; at 5+ COMBO, next shot becomes PIERCE laser.

## Engine

- Pyxel 2.x, 256×256, display_scale=2
- Single-file Python (~500 lines)

## Gameplay

**Core mechanic**: Contain the enemy formation before they breach. Same-color consecutive kills build COMBO. At COMBO 5+, your next shot is a PIERCE laser that passes through all enemies in its column.

**Risk/reward**: Enemies closer to the bottom = higher score per kill. But if they reach the escape line, they BREACH — removed from formation and returned as elite enemies (2 HP, worth 2× points).

**Dive attacks**: Random enemies dive-bomb toward the player. Dodge or shoot them down.

**Heat system**: Each shot generates heat (shown as bar, top-right). Overheat blocks firing until cooled down. Forces tactical pauses — spam loses to precision.

**Phases**: TITLE → PLAYING (waves) → WAVE_CLEAR → GAME_OVER → retry

**Most fun moment**: Letting enemies accumulate near the bottom, building a same-color COMBO chain, then unleashing a PIERCE shot that clears multiple enemies in one sweep for a score explosion.

## Controls

| Key | Action |
|---|---|
| ← → / A D | Move player left/right |
| SPACE / Z | Fire (hold for auto-fire) |
| SPACE / ENTER | Start game / Continue to next wave |
| R | Retry after game over |

## Element Reference

| Color | Pyxel Constant | Visual |
|---|---|---|
| RED | `COLOR_RED` | Red enemy block |
| CYAN | `COLOR_CYAN` | Cyan enemy block |
| YELLOW | `COLOR_YELLOW` | Yellow enemy block |
| LIME | `COLOR_LIME` | Green enemy block |

## Dev Status

- ✅ Single-screen gallery shooter loop
- ✅ Enemy formation movement (side-to-side + step-down)
- ✅ Escape/breach mechanic (elite respawn)
- ✅ Same-color COMBO chain (5 → PIERCE shot)
- ✅ Heat system with cooldown (12 max)
- ✅ Dive attack AI
- ✅ Particle effects + float text
- ✅ Screen shake on player hit
- ✅ Wave system with difficulty scaling
- ✅ Starfield background
- ✅ Headless import/unit tests
- ⬜ Sound effects
- ⬜ Enemy bullets (return fire)
- ⬜ Power-ups / items
- ⬜ Meta-progression between runs

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/022_calamity_siege/main.py
```
