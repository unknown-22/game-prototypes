# CHAIN VAULT — 017_chain_vault

**Source**: Reinterpreted from game idea #1 (score 31.55)
- Original: Hacking auto-shooter with chain propagation + one-color constraint
- Hooks transferred: chain propagation (→ color-chain SHATTER), one-color constraint (→ chain resets on color change)
- Genre: **Platformer** — first in the prototypes collection

**Engine**: Pyxel 2.x, 256×256, 60fps, single-file

## Gameplay

A fast-paced climbing platformer. Jump between colored platforms, chain same-colored landings, and trigger cascading SHATTERs for massive score.

### Core Mechanic
1. **Climb**: Jump between platforms in a vertically scrolling world
2. **Chain**: Landing on the same color consecutively builds a CHAIN counter
3. **Shatter**: At chain count ≥ 3, all platforms of that color SHATTER — launching you upward with a score explosion
4. **Risk**: Landing on a different color resets the chain. High heat (from chaining) causes random platforms to crumble

### Resources
| Resource | Description |
|----------|-------------|
| Chain count | Builds by landing on same-color platforms; resets on color change |
| Score | Earned from shatters: `(shattered_count + 1) × 50 × chain_multiplier` |
| Heat | Increases with each shatter; at ≥85, random platforms crumble. Decays over time |

## Controls

| Input | Action |
|-------|--------|
| ← → / A D | Move left/right |
| Space / ↑ / W | Jump (when on platform) |
| Space / Enter / Z | Restart (from game over) |

## Dev Status

- [x] Core platformer physics (gravity, collision, movement)
- [x] Color-chain system with 3 colors (RED, BLUE, GREEN)
- [x] SHATTER mechanic with particle burst + screen shake
- [x] Heat system with overload crumbling
- [x] Procedural platform generation (infinite scroll)
- [x] Score, high score, shatter count tracking
- [x] Height tracker
- [x] Game over + instant retry
- [x] Camera system with smooth follow
- [x] Floating score text
- [x] Crumbling platform warning (flicker)
- [x] Headless logic tests
- [ ] Difficulty ramp (faster scroll, tighter gaps)
- [ ] Power-ups / special platforms
- [ ] Sound effects (pyxel sounds)

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/017_chain_vault/main.py
```

## How to Test

```bash
uv run python prototypes/017_chain_vault/test_imports.py
```
