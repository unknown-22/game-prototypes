# CHROMA BOUNCE — Color-Match Pinball

**Source**: Game idea #1 (score 31.65) — Dice/bag roguelite / Space mining.
Reinterpreted hooks: "synthesis compression" + "one-color-per-turn" → **color-match pinball**.

## Engine
- Pyxel 2.x
- Screen: 220×320 (portrait)
- Display scale: 2×

## Gameplay

**Core mechanic**: Pinball where the ball has one color at a time. Hit same-color bumpers to build COMBO. COMBO ≥ 4 triggers SYNTHESIS super-mode (all bumpers rainbow, 3× score, no color restrictions). Wrong-color hits reset combo.

**The most fun moment**: Racking up a 4+ hit combo of same-color bumpers, watching SYNTHESIS activate — the screen flashes, all bumpers turn rainbow, and every hit scores 3× points for 5 seconds.

### Rules
- Ball starts in launcher with a random color
- Hit bumpers to score points (same color = combo, different color = combo reset)
- COMBO ≥ 4 → SYNTHESIS (300 frames / 5 seconds)
- During SYNTHESIS: all bumpers are rainbow, 3× score multiplier, ball color doesn't matter
- Ball drain → lose a life (3 lives total)
- Game over when all lives lost

### Scoring
- Same-color bumper: 10 × combo_count (×3 during SYNTHESIS)
- Different-color bumper: 5 (no multiplier, combo reset)
- Wall bounce: 0

### Controls
- **Z** or **LEFT**: Left flipper
- **M** or **RIGHT**: Right flipper
- **SPACE**: Launch ball
- **R**: Restart (on game over screen)

### COMBO / Synthesis
| Combo | Status |
|---|---|
| 1-3 | Normal scoring |
| 4+ | SYNTHESIS triggers! 3× score, rainbow bumpers |

## Dev Status
- ✅ Core pinball physics (gravity, wall bounce, flipper collision, bumper collision)
- ✅ Color-matching combo system
- ✅ SYNTHESIS super-mode with timer bar
- ✅ 16 bumpers (4 per color)
- ✅ Line-segment flipper collision with activation kick
- ✅ Particle effects on hits
- ✅ Ball color indicator + combo display
- ✅ Game over screen with stats
- ✅ High score tracking
- ⬜ Tilt/nudge mechanic
- ⬜ Multiple ball colors in play
- ⬜ Sound effects

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/024_chroma_bounce/main.py
```

## Headless Test
```bash
cd ~/repos/game-prototypes
uv run python prototypes/024_chroma_bounce/test_imports.py
```
