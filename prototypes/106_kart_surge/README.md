# 106_kart_surge — Color-Match Kart Racing

## Source
Reinterpreted from game_idea_factory Idea #1 (Score 31.85):
- "log/replay as asset" → ghost car replays best lap
- "one color per turn" → same-color consecutive boost pads build COMBO

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Python 3.12+, single-file (`main.py`)

## Gameplay
Top-down kart racing on a single-screen circuit. Drive around the track collecting same-color boost pads to build COMBO chains. COMBO ≥ 5 triggers SURGE super mode (5s, 3x score, rainbow glow, 1.5× speed). Your best-lap ghost replays alongside you. Complete 3 laps for final score.

### Core Mechanic
**"One color builds COMBO"** — hitting the same color pad consecutively increments COMBO. Wrong color resets COMBO to 1. SURGE activates at COMBO ≥ 5 and doubles as a risk/reward system.

### Controls
| Key | Action |
|-----|--------|
| ↑ / W | Accelerate |
| ↓ / S | Brake/Reverse |
| ← / A | Steer left |
| → / D | Steer right |
| ENTER | Start from title |
| R | Restart (game over) |

### Phases
- **TITLE**: Press ENTER to start
- **PLAYING**: Drive, collect pads, build COMBO, complete 3 laps
- **GAME_OVER**: Show final score, best lap, max combo; press R to restart

### Scoring
- Each pad: 10 × combo multiplier
- SURGE mode: 3× score per pad
- Lap bonus: floor(600 / lap_frames × 100) for beating previous best lap

## The "Fun Moment"
Chaining same-color pads to reach COMBO ≥ 5, activating SURGE mode, and blasting through the track at 1.5× speed with 3× scoring while your ghost car fades behind you.

## Risk & Reward
- **Risk**: Wrong-color pad resets COMBO to 1, losing multiplier and SURGE progress
- **Reward**: Same-color chain builds toward SURGE (5s super mode) and multiplies score
- **Tension**: Do you take the efficient line (hitting any pad) or the COMBO line (only same-color pads)?

## Dev Status
- ✅ Core physics (angle-based movement, friction, boundary, infield collision)
- ✅ Boost pad system (spawn, collect, respawn)
- ✅ COMBO chain (same-color increments, wrong-color resets)
- ✅ SURGE super mode (activation, timer, speed/score multiplier, rainbow glow)
- ✅ Ghost replay system (best-lap recording, playback)
- ✅ Lap counting (3 laps, finish line detection, double-cross prevention)
- ✅ Particle system (collection burst, SURGE activation burst)
- ✅ Scoring (combo × pad points, SURGE 3×, lap time bonus)
- ✅ 3-screen flow (title, playing, game over)
- ✅ 51 headless tests (pytest)
- ✅ ruff & ty checks pass

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/106_kart_surge/main.py
```
