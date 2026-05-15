# CHROMA DRIVE

**Prototype 030** — Top-down color-match putting game.

## Source

Reinterpreted from [game_idea_factory](https://github.com/unknown-22/game_idea_factory) idea #1 (score **31.85**):

> Magic Academy deckbuilder with "log/replay as assets" + "one color per turn" hooks.

**Reinterpretation**: The color of the last hole you sank becomes your next ball's color — creating a constraint-driven risk/reward loop. Sink matching-color holes for COMBO multipliers; break the chain to reset.

## Engine

- **Pyxel** 2.x
- Screen: 256×256, display_scale=3
- Python 3.12+

## Gameplay

**Core mechanic**: Putt the colored ball into holes on the green. The ball's color matches the last hole sunk. Sinking a hole of the same color builds COMBO (×2, ×3, …), multiplying score. Sinking a different-color hole gives base score but resets COMBO. Missed putts reset COMBO to zero.

**One sentence pitch**: *Choosing between a safe color-mismatch hole and a risky far-away matching hole for that x4 COMBO is the most fun moment.*

### Rules

1. **Aim & Putt**: Move mouse to aim (farther = more power), left-click to putt.
2. **Color match**: Ball color (shown bottom-left) must match hole color for COMBO.
3. **COMBO chain**: Consecutive same-color sinks multiply score: ×1, ×2, ×3, ×4, …
4. **Miss penalty**: Ball stopping outside any hole resets COMBO to zero.
5. **9 putts total**: Maximize score in 9 putts.

### Resources

| Resource | Description |
|---|---|
| **Ball Color** | Determined by last hole sunk; constrains COMBO options |
| **COMBO** | Multiplier for matching-color sinks; resets on mismatch/miss |
| **Putts** | 9 total; counts down each putt (holed or missed) |
| **Score** | Cumulative points; COMBO-matched sinks = 100 × combo |

## Controls

| Input | Action |
|---|---|
| Mouse move | Aim direction + power |
| Left click | Putt ball |
| R key | Retry (on game over) |

## Color Reference

| Color | Pyxel Index | Hex |
|---|---|---|
| RED | 8 | `#FF0000` |
| BLUE | 6 | `#0000FF` |
| GREEN | 11 | `#00FF00` |
| YELLOW | 10 | `#FFFF00` |

## Dev Status

- ✅ Core putting with mouse aim + power
- ✅ Wall bounce physics with friction
- ✅ Hole detection + color-matching COMBO
- ✅ Score popup animation
- ✅ Particle burst on sink
- ✅ Game over + retry
- ✅ Headless import test (30+ tests)
- ⬜ Screen shake on high combo (optional)
- ⬜ Sound effects
- ⬜ Hole color preview

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/030_chroma_drive/main.py
```

## Tests

```bash
uv run python prototypes/030_chroma_drive/test_imports.py
```
