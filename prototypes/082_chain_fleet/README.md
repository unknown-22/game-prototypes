# CHAIN FLEET (082_chain_fleet)

Battleship-style grid deduction puzzle with color-match COMBO chains.

## Source
- Based on game_idea_factory idea #1 (score 32.75): デッキ構築ローグライト / 厄災封印（暴走制御）
- Hooks reinterpreted: synthesis/compression → same-color COMBO chain, CA infection/growth → BFS surge spread, heat/risk → miss penalty
- Genre: **Battleship** (first in collection)

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single-file: main.py (~21KB)

## Gameplay — Core Mechanic
Click a 10×8 grid to find hidden enemy ships. Each ship cell has one of 4 colors.
- **Same-color consecutive hits** build COMBO (×2, ×3, ...)
- **Different-color hit** resets COMBO
- **COMBO ≥ 3** triggers **SURGE**: BFS flood-fill reveals all orthogonally adjacent same-color ship cells
- **Miss** builds HEAT; when HEAT maxes out → enemy counter-attacks (-1 HP)

## The "Most Fun Moment"
Same-color cell 3 consecutive hits → SURGE activates → half the fleet cascades open in one chain reaction.

## Risk & Reward
- **Risk**: Going for same-color chains risks missing (HEAT → enemy strike) or breaking COMBO on wrong color
- **Reward**: COMBO multiplies score (10 × COMBO), SURGE reveals multiple cells instantly (15 × COMBO each)

## Controls
- Mouse click: fire at grid cell
- Keyboard: ENTER/RETURN to start/retry

## Resources
- COMBO: builds on same-color hits, resets on miss/different color
- HEAT: builds on misses, at 8 → enemy attacks (-1 HP)
- HP: 3 lives
- Score: accumulates with COMBO multiplier

## Fleet Composition
5 ships: sizes [4, 3, 3, 2, 2] = 14 total ship cells
4 colors: RED, GREEN, BLUE, YELLOW

## Dev Status
- ✅ Core mechanic: click-to-reveal with COMBO tracking
- ✅ SURGE: BFS flood-fill at COMBO ≥ 3
- ✅ HEAT system: miss penalty + enemy counter-attack
- ✅ Particle effects + floating text
- ✅ Win/lose conditions
- ✅ Headless tests: 26 passing
- ✅ Web build: 082_chain_fleet.html
- ⬜ Sound effects

## Hypotheses
- **Experience**: "Risking same-color chains for SURGE cascade feels thrilling; breaking COMBO feels like a strategic mistake"
- **Mechanic**: Same-color hit = COMBO → SURGE BFS reveals adjacent same-color cells; different color/miss = COMBO reset + HEAT

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/082_chain_fleet/main.py
```

## Test
```bash
uv run pytest prototypes/082_chain_fleet/test_imports.py -v
```
