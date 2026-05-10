# Fork Bomb — Dice-Splitting Circuit Battler

**Source:** game_idea_factory idea #1 (Score 31.6)
Theme: Hacking (circuit/log)
Hook: Numbers split into multiple paths and recombine for explosion.

## Engine

- Pyxel 2.x
- 400×300, display_scale=2
- Python 3.12+

## Gameplay

### Core Mechanic

Roll signal dice and route them through 3 parallel circuit lanes.
**Split** dice to fill more lanes at the cost of RISK.
When adjacent lanes carry the **same value**, they **RECOMBINE**
for multiplied burst damage.

### Rules

1. **ROLL**: 4 dice (values 1-8) appear each turn.
2. **ROUTE**: Click a die, then click a lane to place it.
   Click a placed die to **SPLIT** it into halves on adjacent lanes (+2 RISK).
3. **FIRE**: Click FIRE! to send all placed signals at the enemy.
4. **RECOMBINE**: Matching adjacent values multiply:
   - 2-lane match: **x2 multiplier**
   - 3-lane match (TRIPLE RECOMBINE): **x4 multiplier**
5. **RESOLVE**: Damage applied, enemy counterattacks, risk decays by 1.
6. Repeat until enemy HP reaches 0 or player HP reaches 0.

### Resources

| Resource | Description |
|---|---|
| HP (100) | Player health. Reaching 0 = defeat. |
| RISK (0-10) | Increases with splitting. Enemy attack scales with risk. Decays 1/turn. |
| COMBO | Consecutive turns with at least one recombine. Multiplies score. |
| SCORE | Cumulative: damage dealt × (1 + combo). |

### Enemy

- **Node Guard**: 150 HP, ATK = 6 + turn + risk.
- Defeat the Node Guard within 12 turns to win.

### Most Fun Moment

All 3 lanes converge with the **same value** → **TRIPLE RECOMBINE x4 burst**!

## Controls

| Action | Input |
|---|---|
| Select die | Click die in pool |
| Place die on lane | Click empty lane |
| Split placed die | Click filled lane (no die selected) |
| Fire! | Click FIRE button (bottom-right) |
| Restart | Press R |

## Card/Die Reference

| Element | N/A — dice have numeric values 1-8, no element types. |
|---|---|

## Dev Status

- ✅ Core phase machine (ROLL → ROUTE → FIRE → RESOLVE)
- ✅ Dice rolling and lane placement
- ✅ Split mechanic with risk cost
- ✅ Recombine detection (adjacent same-value lanes)
- ✅ Combo tracking and score system
- ✅ Particle effects (fire, damage numbers, split flash)
- ✅ Victory/defeat screens
- ✅ Headless import test
- ⬜ Sound effects
- ⬜ More enemy types
- ⬜ Persistent high score

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/008_fork_bomb/main.py
```

### Headless Test

```bash
uv run python prototypes/008_fork_bomb/test_imports.py
```
