# BINGO SURGE (160_bingo_surge)

Color-match BINGO game — the first BINGO genre in the collection.

## Source

Reinterpreted from game idea #1 (score 32.35): Dice/bag builder roguelite with hacking theme.
Hooks: "synthesis compression" → COMBO compresses into SUPER BINGO; "CA grid fills up" → SUPER BINGO CA spread to adjacent same-number cells.

## Engine

- Pyxel 2.x, 320×240, display_scale=2
- Python 3.12

## Gameplay

A 5×5 BINGO card occupies the left side. Numbers are "called" as colored balls on the right. Click a cell matching BOTH the number AND color to score points and build your COMBO chain. 

- **Match** (correct number AND color): COMBO++, score (10 + combo×5), SUPER at COMBO≥5
- **Mismatch** (wrong number or color): HEAT +15, COMBO reset
- **Miss** (ball expires): HEAT +20, COMBO reset
- **SUPER BINGO**: 5 seconds of rainbow mode — auto-match all balls, 3× score, CA spread to adjacent same-number cells
- **BINGO line**: Complete a row/column/diagonal for bonus score, cells are cleared and refilled
- **HEAT ≥ 100**: Game over (card burns up!)
- **90 second timer**: Score as many points as possible

### Risk & Reward
Chase same-color consecutive matches for COMBO chains and SUPER BINGO, or play it safe and just match numbers regardless of color. Every wrong click builds HEAT — too much and you're out.

## Controls

- **Mouse click**: Mark a cell on the BINGO card (must match the called ball)
- **SPACE / RETURN**: Start from title, retry from game over

## Core Mechanic

"Mark same-color numbers on your bingo card to build COMBO chains — hit COMBO≥5 for SUPER BINGO"

## The Fun Moment

Hitting COMBO≥5 triggers SUPER BINGO — the card border explodes with rainbow colors, all balls are auto-matched, and CA spread marks every adjacent cell with the same number in a cascading chain reaction.

## Dev Status

- ✅ Core bingo grid with color-matched number clicking
- ✅ 4-color COMBO chain system
- ✅ SUPER BINGO at COMBO≥5 (5s rainbow, 3× score, CA spread)
- ✅ HEAT risk system (mismatch +15, miss +20, passive decay)
- ✅ BINGO line detection (rows, cols, diagonals) with clear + refill
- ✅ Ball call area with shrinking timer ring
- ✅ Particle effects (success, fail, bingo burst)
- ✅ 3 screens: Title, Game, Game Over
- ✅ 52 headless tests
- ⬜ Sound effects

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/160_bingo_surge/main.py
```

## Test

```bash
uv run python prototypes/160_bingo_surge/test_imports.py
```
