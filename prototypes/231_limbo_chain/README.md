# LIMBO CHAIN — 231

Color-match limbo dance game. Duck under the bar with matching colors to build combos.

## Source
Reinterpreted from game_idea_factory Idea #1 (Score 31.95):
- "Chain propagation" → same-color consecutive ducks build COMBO chain → SUPER LIMBO
- "Collapse/expand/compress" → bar descent + SUPER LIMBO bar raise

## Engine
- Pyxel 2.x, 320×240, 60fps
- Single-file: `main.py`

## Core Mechanic
A horizontal bar descends with each successful duck. Match your duck color to the bar color for COMBO chains. COMBO ≥ 4 triggers SUPER LIMBO (rainbow mode, auto-duck, 3x score, bar raises 15px).

### The Fun Moment
Chaining 4+ consecutive same-color ducks under an impossibly low bar and watching SUPER LIMBO activate with rainbow particles — the risk/reward squeeze of trying for one more duck when the bar is at its lowest.

## Controls
- `SPACE`: Duck under the limbo bar

## Rules
- 4 colors: RED, LIME, DARK_BLUE, YELLOW
- Same-color consecutive ducks = COMBO (score = BASE × combo × super_multiplier)
- COMBO ≥ 4 → SUPER LIMBO (300 frames, rainbow, auto-duck, bar +15px)
- Wrong color: COMBO reset, HEAT +15
- Bar hit (miss): COMBO reset, HEAT +25
- HEAT ≥ 100 or 60s timer → Game Over
- Difficulty escalation: attempt interval 120f→45f, color cycle 90f→40f, bar descent increases

## Screens
1. **Title**: "LIMBO CHAIN", controls, press SPACE to start
2. **Playing**: Main game with bar, player, HUD
3. **Game Over**: Final score, max combo, press SPACE to retry

## Dev Status
- ✅ Core mechanic: color-match ducking with COMBO chain
- ✅ SUPER LIMBO mode with auto-duck and bar raise
- ✅ HEAT risk/reward system
- ✅ Difficulty escalation (interval, color cycle, descent rate)
- ✅ Particle system and floating text
- ✅ Screen shake feedback
- ✅ 3 screens (Title/Playing/GameOver)
- ✅ 29 headless tests (ruff + ty passing)
- ✅ Web build deployed
- ⬜ Sound effects
- ⬜ Character sprite animation

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/231_limbo_chain/main.py
```

## Experience Hypothesis
緊張と緩和のリンボーダンス — バーがどんどん低くなる中で同色くぐりを成功させ続ける緊張と、COMBO が溜まって SUPER LIMBO が発動する瞬間の開放感が面白い。

## Implemented Core Loop
1. Bar color cycles → Player decides to duck or wait
2. Color match → COMBO increases, bar descends
3. COMBO ≥ 4 → SUPER LIMBO (auto-duck, bar raises, rainbow)
4. Mismatch → HEAT + COMBO reset
5. Game over: HEAT ≥ 100 or timer expires → immediate restart

## What Works
- Clean timing-based risk/reward: wait for matching color (risks bar hit) vs duck immediately (risks HEAT)
- SUPER LIMBO provides satisfying payoff after building COMBO
- Difficulty escalation is smooth and visible (bar position, color speed)

## Next Improvement
- Add sound effects (duck swoosh, combo chime, SUPER activation fanfare)
- Character sprite animation (standing/ducking/walking)
- High score persistence between sessions
