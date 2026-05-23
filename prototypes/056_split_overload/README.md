# SPLIT OVERLOAD (056)

**Split-path power surge arena action.**

## Source

Selected from `ideas/2026-05-22_chain-push-reinterpretation.md`:

- Score 31.6
- Vampire Survivors-like abstract action
- Power plant overload/discharge theme
- Hook: synthesized power splits through multiple paths, then converges into an explosion

## Core Fun

Lure enemies close, spend stored charge, and watch three split lightning paths collapse into a single high-damage convergence blast.

## Rules

- Survive for 90 seconds.
- Move with arrows or WASD.
- The core auto-fires at the nearest enemy.
- Kills and hits build `CHARGE`.
- `SPACE` spends charge to fire `SPLIT OVERLOAD`.
- Overload targets up to 3 nearby enemies, then creates a convergence blast at their center.
- Tighter enemy clusters produce a larger, stronger blast.
- Blast hits can chain to nearby enemies.
- Heat rises from firing and overloads. At full heat, auto-fire pauses until it cools.
- Contact damage removes HP and resets combo.

## Controls

| Key | Action |
|---|---|
| Arrow / WASD | Move |
| Space | Split Overload |
| Enter | Start / retry |
| R | Retry on game over |

## Dev Status

- [x] 320x240 Pyxel prototype
- [x] Title, game, game-over screens
- [x] Auto-fire survival loop
- [x] Charge and heat resources
- [x] Split-path overload targeting
- [x] Convergence blast with tight-cluster reward
- [x] Chain damage, score, combo, particles, floating text
- [x] Headless logic tests
