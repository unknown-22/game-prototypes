# SPLIT SURGE (049_split_surge)

**Zuma-style marble chain shooter** with color-match COMBO and split/reconverge mechanics.

## Source

Reinterpreted from game_idea_factory #1 (Score 32.0):
- Hook "split→converge" → matching 3+ splits the chain; same-color segment ends that touch reconverge for COMBO chain reactions.
- Hook "synthesis compression" → consecutive same-color matches build COMBO; COMBO >= 3 unlocks SUPER SHOT (rainbow marble).

All 10 generated ideas (2026-05-22) clustered in deckbuilder/dice/auto-shooter. Selected highest-scored and reinterpreted into marble chain shooter — a genre not yet in the collection.

## Engine

- Pyxel 2.x, 256×256, display_scale=2
- Python 3.12+

## Gameplay

A spiral chain of colored marbles rolls toward the center. Shoot marbles from the center cannon to match 3+ same-color marbles and pop them. Clearing marbles splits the chain — if the two ends of a split share the same color, they RECONVERGE for a bonus COMBO. Clear all marbles to advance; let any reach the center and it's game over.

### Core Mechanic

**Split & Reconverge**: Matching 3+ pops marbles, creating a gap in the chain. If the marbles immediately before and after the gap share a color, they reconverge and auto-pop for bonus points + COMBO. This can chain-react.

**COMBO System**: Consecutive matches (both regular and reconverge) increment COMBO. Score multiplies with COMBO. When no match or reconverge is found, COMBO resets to 0.

**Wave System**: Clear all marbles → next wave. Each wave: faster chain movement, shorter spawn interval, longer initial chain.

## Controls

| Input | Action |
|---|---|
| Mouse aim | Aim cannon direction |
| Left click | Shoot current-color marble |
| Keys 1-4 | Select marble color (RED/GRN/BLU/YLW) |
| Scroll wheel | Cycle marble color |
| Click / 1 (on game over) | Restart |

## Colors

| Key | Name | Color |
|---|---|---|
| 1 | RED | Red (8) |
| 2 | GRN | Green (11) |
| 3 | BLU | Dark Blue (5) |
| 4 | YLW | Yellow (10) |

## Dev Status

- [x] Core loop: shoot → match → pop → reconverge
- [x] COMBO system with reset
- [x] Wave escalation (speed, spawn rate, chain length)
- [x] Particle effects on pop/reconverge
- [x] Floating score text
- [x] Stage clear transition
- [x] Game over + restart
- [x] Mouse aim cannon
- [x] Keyboard + scroll color selection
- [x] Headless import verification
- [ ] SUPER SHOT (COMBO ≥ 3 rainbow marble) — planned
- [ ] Sound effects — planned
- [ ] Screen shake on reconverge — planned

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/049_split_surge/main.py
```
