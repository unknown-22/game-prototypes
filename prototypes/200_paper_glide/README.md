# 200 — PAPER GLIDE

Side-view paper airplane gliding game. Click-drag-release to aim and throw the plane through wind rings. Same-color consecutive ring passes build COMBO chain; COMBO≥4 triggers SUPER GLIDE rainbow mode. Ghost trail shows previous flight path.

**Most Fun Moment:** 狙い通りに紙飛行機を放ち、同色リングを連続通過してCOMBOが繋がり、最後にSUPER GLIDEの虹色モードで全てのリングを貫通する瞬間。

## Source
- Reinterpreted from idea #1 (Score 32.2) — dice/bag roguelite with "log/replay as asset + chain collapse" hooks
- Genre: Paper airplane / glider (first in collection)

## Engine
- Pyxel 2.x, 320×240, display_scale=2

## Controls
- SPACE: Start game / restart
- Mouse LEFT click-drag-release: Aim and throw plane (drag direction = angle, drag distance = power)

## Mechanics
- 4 ring colors: RED(8), GREEN(3), DARK_BLUE(5), YELLOW(10)
- Same-color consecutive ring passes = COMBO chain
- Score = 10 × (1 + combo × 0.5), SUPER mode ×3
- COMBO≥4 = SUPER GLIDE (300 frames rainbow, any-color match, 3× score)
- Wrong color ring = COMBO reset + HEAT +10
- Miss (plane off screen) = HEAT +5
- HEAT≥100 = game over
- 60s timer countdown
- Ghost trail stores previous throw flight path
- Particle system: pass (8), super (20), miss/mismatch (4 each)
- Sweep-based ring spawning (4-6 rings per throw, min gap 60-100px)

## Dev Status
- ✅ Main game loop (TITLE, AIMING, FLYING, GAME_OVER phases)
- ✅ Click-drag-release aiming with power + angle
- ✅ Plane physics (gravity, drag, ring collision)
- ✅ COMBO chain + SUPER GLIDE
- ✅ HEAT system (decay-before-check bug FIXED)
- ✅ Ghost trail from previous throw
- ✅ Particle system (pass, super, miss, mismatch)
- ✅ 55 headless tests
- ✅ Web build

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/200_paper_glide/main.py
```

## Known Issues
- None (OpenCode first-try success with 2 self-corrected ruff/ty issues + 1 Hermes fix for decay-before-check)
