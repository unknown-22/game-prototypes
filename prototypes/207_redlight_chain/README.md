# REDLIGHT CHAIN — 207_redlight_chain

Color-match "Red Light Green Light" timing game.

## Source
Reinterpreted from game_idea_factory idea #9 (score 30.75, deckbuilder batch):
- "partial observation (probabilistic enemy intent)" + "cost is future hand"
- Reinterpreted as: "traffic light uncertainty → timing risk/reward"

## Engine
- Pyxel 2.x, 320×240
- Single file: main.py (463 lines)

## Gameplay — Core Mechanic

A traffic light cycles through 4 colors (RED → GREEN → YELLOW → BLUE).
Gems of matching colors scroll from the right. Collect gems matching the current
light color to build a COMBO chain. Wrong-color gems reset your COMBO and add HEAT.

**The fun moment:** The tension between waiting for the right color and rushing
to collect gems before the timer runs out.

- COMBO ≥ 4 activates SUPER MODE (180 frames): all gems count as matching, 3× score
- HEAT ≥ 100 → game over (player "caught")
- 60 second time limit

## Controls
| Key | Action |
|-----|--------|
| ← → | Move player left/right |
| SPACE / ENTER | Start / Retry |

## Risk & Reward
- **Safe**: Wait for the matching light color before collecting
- **Risky**: Collect during wrong color → COMBO reset + HEAT +15
- **Reward**: Chain COMBO → SUPER MODE → 3× score, rainbow gems

## Scoring
- Normal hit: 10 + combo × 5 points
- SUPER hit: (10 + combo × 5) × 3 points

## Dev Status
- ✅ Core mechanic: color-match timing with light cycle
- ✅ COMBO chain + SUPER MODE
- ✅ HEAT system with decay
- ✅ Particle burst + floating text feedback
- ✅ Screen shake on miss
- ✅ 3 screens (Title / Playing / Game Over)
- ✅ 51 headless tests
- ✅ Web build deployed to docs/

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/207_redlight_chain/main.py
```

## OpenCode Delegation
- ✅ OpenCode CLI used (`opencode-go/deepseek-v4-pro`)
- ✅ First-try success with `-f /tmp/design_207.txt`
- ✅ `--thinking` NOT used (per pitfall)
- ✅ OpenCode self-corrected ruff issues
