# 163 SORT SURGE — Color-Match Conveyor Belt Sorter

**Genre:** Real-time conveyor belt sorter (first in collection)
**Engine:** Pyxel 2.x, 320x240

## Gameplay
Colored packages stream toward you on 5 conveyor belts. Click a bin to select its color, then click packages to sort them. Consecutive same-color sorts build a COMBO chain. COMBO >= 5 triggers SURGE mode (5s: auto-sort, 3x score, rainbow matching). Mistakes and missed packages fill the OVERFLOW bar — at 100, game over.

## The Fun Moment
Maintaining a combo streak while packages stack up on the conveyor creates a tense "flow state" rhythm. When SURGE activates, the screen clears rapidly with rainbow particle effects — a satisfying payoff for skilled play.

## Controls
- **Mouse left click**: Select a color bin (bottom), then click packages to sort
- **SPACE / RETURN**: Start game (title/game over screens)

## Risk & Return
- **Risk**: Sorting the wrong color resets COMBO and adds +20 OVERFLOW. Packages reaching the conveyor end add +30 OVERFLOW.
- **Reward**: Same-color consecutive sorts multiply score. COMBO >= 5 unlocks SURGE (5s, auto-sort 1pkg/sec, 3x score).
- **Decision**: Do you maintain your combo by reaching for matching packages further away (risking overflow), or break your combo to sort nearby mismatched packages (safe but low score)?

## Dev Status
- [x] Core mechanic (package spawn, move, sort)
- [x] COMBO chain system
- [x] SURGE mode (COMBO >= 5)
- [x] OVERFLOW bar + game over
- [x] Difficulty scaling (spawn interval, speed)
- [x] Particle effects + floating text
- [x] Title / Playing / Game Over screens
- [x] 52 headless tests (all passing)
- [x] ruff + ty clean
- [x] Web build deployed to docs/

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/163_sort_surge/main.py
```

## Tests
```bash
uv run python prototypes/163_sort_surge/test_imports.py
```
