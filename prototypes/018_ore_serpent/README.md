# ORE SERPENT — Snake-like Mining Prototype

First **snake** genre in the collection. Reinterpreted from game_idea_factory idea #1 (score 32.2).

## Source

- **Original idea**: Vampire Survivors-like auto-shooter / Space mining (score 32.2)
- **Original hooks**: "log/replay as assets (past actions become next cards)", "UI chain effects (collapse/expand/compress)"
- **Reinterpretation**: Snake body = log of past positions constraining future movement. Chain-combo from consecutively eating same-color ores.
- **Why reinterpreted**: All 10 generated ideas on 2026-05-13 clustered in auto-shooter/deckbuilder/dice — all genres already well-represented. Reinterpreted into snake, a genre the collection lacked.

## Engine

- Pyxel 2.x, 320×240, display_scale=2
- Grid-based movement: 20×15 cells, 16px each

## Gameplay

**Core mechanic**: Navigate a growing drill-serpent through mineral caverns. Collect ores to build score. Same-color ores eaten consecutively multiply the combo (×1, ×2, ×3, ..., ×8 cap). Your body grows with each ore, constraining movement — longer = more risk, but combo potential rises.

**The fun moment**: Threading the needle through your own body to grab a 4th consecutive same-color ore for a ×4 COMBO payoff.

### Rules

- **Movement**: 4-directional, grid-tick-based (6 ticks/sec → 14 ticks/sec as score rises)
- **Ores**: 4 types — RUBY (red), SAPPHIRE (cyan), GOLD (yellow), EMERALD (green)
- **Combo**: Consecutive same-color → multiplier. Different color → reset to ×1
- **Score**: 10 × combo_multiplier per ore
- **Growth**: +1 body segment per ore eaten
- **Win**: Reach 500 score within 60 seconds
- **Lose**: Hit wall, hit own body, or time runs out

### Risk/Reward

- Long body = tight navigation = high risk of self-collision
- High combo = massive score but you must focus on one color (ignore others)
- Ores respawn every 3s — wait for the right color or grab what's nearby?

## Controls

| Key | Action |
|-----|--------|
| Arrow Keys / WASD | Change direction |
| SPACE / ENTER | Restart after game over |

## Dev Status

- [x] Snake grid movement with body growth
- [x] 4 ore types with combo system (×1 → ×8)
- [x] Wall and self-collision detection
- [x] 60-second timer with decreasing tick interval
- [x] Victory at 500 score
- [x] Particle effects (ore collection, death explosion)
- [x] Floating score text (+combo multiplier display)
- [x] Screen shake on high combo + death
- [x] End screen with score and max combo
- [x] Instant restart (SPACE/ENTER)
- [x] Headless logic tests (36 tests)
- [ ] Sound effects
- [ ] Difficulty modes / endless mode

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/018_ore_serpent/main.py
```

Web version: `docs/018_ore_serpent.html`

## Tests

```bash
uv run python prototypes/018_ore_serpent/test_imports.py
```
