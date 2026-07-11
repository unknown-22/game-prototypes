# SLINKY CHAIN (224_slinky_chain)

Side-view slinky (spring toy) descending a staircase with color-match COMBO chain mechanics.

## Concept

A slinky toy walks down colored steps. Press SPACE to flip the slinky onto the next step. If the slinky's color matches the step color, COMBO builds. Wrong color resets COMBO and adds HEAT. COMBO>=4 triggers SUPER SLINKY (rainbow mode: auto-flip, 3x score, 5 seconds).

## How to Run

```bash
uv run python prototypes/224_slinky_chain/main.py
```

## Controls

| Key | Action |
|-----|--------|
| SPACE / ENTER | Flip slinky to next step |
| R | Restart |

## Rules

- **Color Match**: Slinky color must match step color to build COMBO
- **COMBO Chain**: Same-color consecutive matches build COMBO multiplier (score = 10 × COMBO × multiplier)
- **SUPER SLINKY**: COMBO ≥ 4 activates rainbow mode (5s): auto-flip, all colors match, 3× score
- **HEAT**: Mismatch adds +15 HEAT. HEAT ≥ 100 = game over
- **Idle Timer**: Not flipping for too long → slinky wobbles → falls off stairs → game over
- **Timer**: 60 seconds to maximize score

## Game Over Conditions

- HEAT reaches 100 (overheat)
- Slinky falls off stairs (idle too long)
- Timer runs out (survived! — time victory)

## Design

- **Source**: Game Idea Factory #1 (Score 32.2) — deckbuilder idea reinterpreted
  - "log/replay as asset" → ghost trail of best run
  - "UI chain collapse/expansion" → COMBO → SUPER SLINKY
- **Genre**: First slinky/spring-toy genre in collection
- **Engine**: Pyxel 2.x, 320×240

## Experience Hypothesis

「同じ色の階段を狙って待つ緊張感と、COMBOが決まってSUPER SLINKYで一気に階段を駆け降りる爽快感」

## Core Loop

1. Watch slinky color cycle + step color
2. Decide: flip now (risk mismatch) or wait (risk idle fall)
3. Match → COMBO builds → SUPER SLINKY activates
4. Mismatch → COMBO resets + HEAT rises
5. Repeat until game over

## What Works Well

- Clear risk/reward: wait for matching color vs. flip early to avoid falling
- Visual slinky rendering with zigzag spring pattern
- SUPER SLINKY auto-flip provides satisfying payoff
- Ghost trail shows improvement over runs

## Next Improvements

- Add difficulty scaling (faster color cycle, shorter idle time)
- Add more step variety (narrow steps, moving steps)
- Sound effects for match/mismatch/SUPER
