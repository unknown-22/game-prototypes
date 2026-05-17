# CHROMA CHASE

**Prototype #036** — Color-match maze chase (Pac-Man-like)

## Source

Reinterpreted from game idea #1 (score **32.15**):
> ダイス/バッグ構築ローグライト / 魔法学院（ルール改変）

Hooks reinterpreted:
| Original Hook | Reinterpretation |
|---|---|
| ログ/リプレイが資産 (log/replay as asset) | Player's movement trail damages ghosts when COMBO >= 2 |
| CA grid spread control | Ghosts multiply across the grid over time |

**Genre: Maze Chase** — first in the 35-prototype collection (no Pac-Man-like game existed).

## Engine

- Pyxel 2.x
- 256×256 screen, 16×16 grid (16px cells)
- 30 FPS, keyboard-only input

## Gameplay

**Core mechanic:** Eat same-colored gems consecutively to build COMBO multipliers. Your movement trail becomes a defensive weapon. Ghosts multiply — greed for combo vs. safety.

**Game loop:**
1. Navigate the grid with arrow keys (or WASD)
2. Collect colored gems — same color consecutively = COMBO multiplier
3. Avoid ghosts chasing you
4. COMBO ≥ 2: your movement trail damages ghosts
5. Power gems (flickering "P") grant 6 seconds of invincibility
6. New ghosts spawn every 20 seconds (faster as more ghosts exist)
7. Survive as long as possible, maximize score

**Risk/reward:**
- Chase same-color gems for higher combo → more score per gem, but may lead you into ghosts
- High combo makes trails dangerous to ghosts → strategic "painting" of safe zones
- Power gems give invincibility → can clear ghosts for bonus score

## Controls

| Key | Action |
|---|---|
| Arrow keys / WASD | Move (one cell per press) |
| R / Space (on game over) | Restart |

## Scoring

- Gem eaten: 10 × current combo level
- Ghost killed by trail: 25 × current combo
- Ghost killed while invincible: 50
- Power gem: 0 (grants invincibility)

## Elements

| # | Color | Pyxel Constant |
|---|---|---|
| 0 | RED | `COLOR_RED` |
| 1 | BLUE | `COLOR_LIGHT_BLUE` |
| 2 | GREEN | `COLOR_GREEN` |
| 3 | YELLOW | `COLOR_YELLOW` |
| 4 | PURPLE | `COLOR_PURPLE` |

## Dev Status

- ✅ Grid movement with obstacle collision
- ✅ Color-match gem collection with COMBO
- ✅ Ghost chase AI (simple pathfinding toward player)
- ✅ Trail defense mechanic (COMBO ≥ 2)
- ✅ Ghost multiplication (periodic spawning)
- ✅ Power gem (invincibility)
- ✅ Floating text effects
- ✅ Score tracking + max combo
- ✅ Game over + instant restart
- ✅ Headless logic tests
- ⬜ Sound effects
- ⬜ Difficulty curve tuning
- ⬜ High score persistence

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/036_chroma_chase/main.py
```

## How to Test

```bash
uv run python prototypes/036_chroma_chase/test_imports.py
```
