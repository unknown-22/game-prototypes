# CUE CHAIN — Color-Match Billiards

**Prototype ID:** 044_cue_chain  
**Source:** Reinterpreted from game_idea_factory #1 (score 31.8, deckbuilder roguelite)  
**Hooks reused:** "same card consecutively use mutates" → same-color ball pocketed consecutively = COMBO; "chain collapse UI" → COMBO ≥ 3 triggers CHAIN BREAK

## Engine

- Pyxel 2.x
- Screen: 256×256, display_scale=2
- Language: Python 3.12

## Gameplay

**Core mechanic:** Aim-and-shoot billiards on a top-down pool table. Pocket balls of the same color consecutively to build COMBO multipliers.

**Most fun moment:** Sinking 3+ same-color balls in a chain, triggering CHAIN BREAK, and watching the rainbow cue ball ricochet for 3x score.

### Rules

1. Click-and-drag from the white cue ball to aim (drag opposite of where you want to shoot)
2. Release to shoot — longer drag = more power
3. Pocket a ball → score = 100 × COMBO multiplier
4. Same color consecutively → COMBO increases
5. Different color → COMBO resets to 1
6. COMBO ≥ 3 → **CHAIN BREAK** (next shot is rainbow: matches any color, 3x score)
7. Time limit: 60 seconds
8. Pocketed balls are replaced automatically

### Risk/Reward

- Going for same-color balls builds COMBO but may require harder shots
- Breaking COMBO by pocketing a different color resets your multiplier
- CHAIN BREAK gives one shot of freedom (any color counts) with 3x multiplier
- Hard shots close to pockets risk scratching (cue ball in pocket)

## Controls

| Action | Input |
|---|---|
| Aim | Click-drag from cue ball (drag backward) |
| Shoot | Release mouse button |
| Retry (game over) | Click or press R |

## Dev Status

- ✅ Billiards physics (elastic collision, friction, wall bounce)
- ✅ 6-pocket table
- ✅ Click-drag-release aim + power system
- ✅ 4-color balls with COMBO system
- ✅ CHAIN BREAK super-mode (COMBO ≥ 3)
- ✅ 60-second timer + scoring
- ✅ Headless import tests
- ⬜ Sound effects (pocket, collision, chain break)
- ⬜ Particle effects on pocket
- ⬜ Cue ball scratch penalty

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/044_cue_chain/main.py
```

## Headless Tests

```bash
uv run python prototypes/044_cue_chain/test_imports.py
```
