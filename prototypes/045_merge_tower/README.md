# MERGE TOWER (045_merge_tower)

**Source**: Reinterpreted from game_idea_factory idea #1 (score 31.85)
- "synthesis compression" → 3+ same-color blocks MERGE into higher tier
- "split/converge numbers" → chain reactions cascade through tower

**Engine**: Pyxel 2.x, 220×300, 5 colors, 3 tiers

## Gameplay

**Core mechanic**: Drop colored blocks onto a 10×13 grid. When 3 or more same-color, same-tier blocks are connected (horizontally/vertically adjacent), they **MERGE** into a single block of the next tier at the cluster center. Chain reactions can cascade through the tower. If the tower reaches the top row, **GAME OVER**.

**The most fun moment**: A tier-2 merge creates a tier-3 block, which triggers another merge — chain reactions pulsing upward with particles and screen shake!

### Rules
- **Colors**: 5 colors (Red, Green, Blue, Yellow, Purple)
- **Tiers**: 3 tiers per color (Tier 1 → 2 → 3)
- **Merge**: 3+ same-color, same-tier adjacent blocks → merge to tier+1
- **COMBO**: Each chain-triggered merge in a single drop increments the COMBO multiplier
- **Scoring**: base_tier_score × COMBO multiplier (1.5× per link)
- **Risk**: Stack height — if blocks reach the top, game over

## Controls

| Key | Action |
|-----|--------|
| ← → | Move falling block |
| ↓ | Fast drop |
| Space | Instant drop |
| R | Restart (on game over) |

## Color Reference

| Color | Pyxel Constant | Hex |
|-------|---------------|-----|
| Red | COLOR_RED | #ff0040 |
| Green | COLOR_GREEN | #00a800 |
| Blue | COLOR_LIGHT_BLUE | #8090ff |
| Yellow | COLOR_YELLOW | #ffec27 |
| Purple | COLOR_PURPLE | #a22188 |

## Tier Indicators

| Tier | Visual |
|------|--------|
| 1 | Solid color rectangle |
| 2 | Colored border + "2" text |
| 3 | Gold corner markers + "3" text |

## Dev Status

- ✅ Core drop mechanic
- ✅ BFS cluster detection
- ✅ Merge animation with particles
- ✅ Chain reaction cascades
- ✅ COMBO multiplier
- ✅ Score system
- ✅ Screen shake (tier-3 merges)
- ✅ Floating score text
- ✅ Game over detection
- ✅ Restart on R
- ⬜ Sound effects
- ⬜ High score persistence
- ⬜ Tier-4 super merge

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/045_merge_tower/main.py
```
