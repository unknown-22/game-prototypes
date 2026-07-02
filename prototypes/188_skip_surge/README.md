# SKIP SURGE

## Source
Game Idea Factory #1 from 2026-07-02 generation (Score 31.95 — ヴァンサバ亜種 / 魔法学院ルール改変).
Reinterpreted hooks:
- 「効果が合成されて1枚に圧縮」→ COMBO chain compresses into SUPER JUMP
- 「盤面が回路/パイプで可視化される（流れて増幅する）」→ rope rotates as a "flow pipe" with colored segments

**First jump rope / skipping rope prototype in the collection.**

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Font: k8x12.bdf (copied for BDF font support)

## Core Mechanic
Side-view jump rope. A rope with 4 colored segments (RED=8, GREEN=3, DARK_BLUE=5, YELLOW=10) rotates around the player. Press SPACE to jump over the rope.

- Same-color consecutive jumps → COMBO +1
- COMBO >= 4 → SUPER JUMP (5s rainbow mode: all colors match, 3x score, auto-jump)
- Miss timing (jump too early/late) → HEAT +10, COMBO reset
- HEAT >= 100 → GAME OVER
- Rope speed increases over time (every 100 frames)
- Wrong-color jump resets COMBO (no HEAT penalty)

## Experience Hypothesis
縄跳びで同じ色の縄を連続でリズムよく跳び、COMBOが4以上に達してSUPER JUMPが発動し、自動で跳び続けてスコアが3倍で加速する瞬間が面白い。

## Mechanics → Dynamics → Aesthetics
- **Mechanics**: Color-matched timed jumps, COMBO chain, SUPER JUMP multiplier + auto-jump, HEAT risk, rope speed ramping
- **Dynamics**: Risk/reward of maintaining color chain vs. reset safety; timing pressure from increasing speed; SUPER JUMP creates a power fantasy window
- **Aesthetics**: Rhythmic jump satisfaction, explosive SUPER JUMP rainbow effects, screen shake on miss

## Controls
- SPACE / Mouse Click: Jump
- SPACE / ENTER / Mouse Click: Navigate menus (Title → Play, Game Over → Title)

## Display Info
- Top-left: Score
- Top-center: COMBO counter (color-coded: GRAY < 2, ORANGE >= 2, YELLOW >= SUPER)
- Top-right: Max COMBO
- SUPER indicator: flashing "SUPER! Ns" when active
- Bottom: HEAT bar (GREEN < 30, ORANGE < 60, RED >= 60)
- Rainbow border during SUPER mode

## Dev Status
- ✅ Core jump mechanic with gravity physics
- ✅ 4-color rotating rope with segment detection
- ✅ COMBO chain system (same-color consecutive → combo up)
- ✅ SUPER JUMP (combo >= 4, 5s rainbow, 3x score, auto-jump)
- ✅ HEAT risk system (miss +10, decay 0.025/frame, cap 100)
- ✅ Rope speed ramping (0.03 → 0.10 over time)
- ✅ Particle effects (jump, miss, SUPER)
- ✅ Floating text (+score, COMBO, MISS!, SUPER!)
- ✅ Screen shake on miss
- ✅ 3-phase state machine (TITLE, PLAYING, GAME_OVER)
- ✅ 60 headless logic tests (all pass)
- ✅ ruff + ty checks pass
- ✅ Web build deployed to docs/

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/188_skip_surge/main.py
```

## Tests
```bash
uv run python prototypes/188_skip_surge/test_imports.py
```

## What Works Well
- The COMBO → SUPER JUMP escalation feels rewarding
- Color-matching adds strategic depth to a simple timing mechanic
- HEAT system creates genuine tension between safe play and combo-chasing
- Auto-jump during SUPER mode creates a satisfying power-fantasy moment
- Speed ramping provides natural difficulty progression

## Next Improvement
- Add sound effects for jumps, combos, SUPER activation
- Add visual rope stretch/bounce animation
- Add difficulty levels or speed presets
- Add a high-score persistence
- Tune HEAT decay to give more recovery time
