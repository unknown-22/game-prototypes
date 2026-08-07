# FLASH CHAIN (293)

**First photography/camera genre in the collection.**

## Source
Game Idea Factory #1 (Score 32.75) — 厄災封印（暴走制御）デッキ構築  
Reinterpreted hooks: "synthesis compression" → same-color COMBO → SUPER FLASH, "CA grid fills up" → fog spread control

## Engine
- Pyxel 2.x, 320×240, display_scale=2, 30fps
- 8×6 grid viewfinder (32px cells)

## Core Mechanic
1. Colored subjects appear on the viewfinder grid
2. Fog spreads from edges (CA metaphor) — fogged cells can't be photographed
3. Click to photograph visible subjects
4. Same-color consecutive photos = COMBO chain (score = 10 × combo × multiplier)
5. Wrong-color photo = HEAT +15, combo reset
6. COMBO ≥ 4 triggers SUPER FLASH (300f rainbow mode: any-color match, 3× score, clears ALL fog)
7. HEAT ≥ 100 or timer ≤ 0 = GAME OVER
8. Difficulty escalates: fog spreads faster, subjects spawn faster, lifetime decreases

## Controls
- Mouse click: photograph subject at clicked cell
- SPACE / ENTER: start game / retry
- Q / ESC: quit

## Experience Hypothesis (体験仮説)
「フォグが迫る中、同色の被写体を連続で撮影してCOMBOを伸ばし、SUPER FLASHで画面全体が光り輝いて一気にフォグが消える瞬間が面白い」

## Working Well
- Fog CA spread creates genuine time pressure
- COMBO → SUPER FLASH reward loop is tight and satisfying
- First-click safety (no combo penalty) allows immediate engagement
- Heat decay provides passive relief between mismatches

## Next Improvements
- Add subject variety (shapes/icons beyond circles)
- Camera shake on SUPER FLASH
- Score popups (+score numbers floating up)
- High score persistence between sessions

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/293_flash_chain/main.py
```

## Dev Status
- ✅ Core photography click + COMBO chain
- ✅ Fog CA edge-spread system
- ✅ SUPER FLASH mode with flash animation
- ✅ HEAT risk system
- ✅ 60s timer with difficulty escalation
- ✅ Particle system (match / super / mismatch)
- ✅ Title / Playing / Game Over screens
- ✅ 49 headless tests
- ✅ ruff + ty pass
- ✅ Web build (docs/293_flash_chain.html)
- ⬜ Score popup floating text
- ⬜ Subject visual variety
- ⬜ High score persistence
