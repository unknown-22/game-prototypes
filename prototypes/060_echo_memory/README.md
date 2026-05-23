# ECHO MEMORY (060)

Color-match memory sequence game — first memory/sequence prototype in the collection.

**Reinterpreted from**: Game Idea #1 (Score 32.6) — Hacking deckbuilder: "Log/replay as asset" → memorized sequence; "Chain collapse/expansion UI" → COMBO + ECHO CHAIN.

## Experience Hypothesis
"Same-color consecutive correct presses feel satisfying. Getting into a rhythm and tapping panels in time feels great."

## Core Loop
1. **Watch**: Panels light up in a sequence (computer's turn)
2. **Reproduce**: Click panels in the exact order shown
3. **Combo**: Same-color consecutive correct presses build COMBO
4. **Echo Chain**: COMBO ≥ 3 triggers auto-completion of the next 2 positions
5. **Repeat**: Each round adds 1 to sequence length and increases speed

## Controls
- **Mouse only**: Click the colored panels to reproduce the sequence
- Colors: RED (top-left), GREEN (top-right), DARK BLUE (bottom-left), YELLOW (bottom-right)

## Scoring
- Correct press: 10 + combo × 5
- Echo chain auto-complete: 10 + combo × 10
- Round complete bonus: round × 50
- 3 lives — wrong click costs 1 life

## Difficulty
| Rounds | Speed |
|--------|-------|
| 1–3    | 1.0×  |
| 4–6    | 1.3×  |
| 7–9    | 1.6×  |
| 10+    | 2.0×  |

## Dev Status
- ✅ Core memory/sequence mechanic
- ✅ COMBO system (same-color consecutive)
- ✅ ECHO CHAIN auto-completion
- ✅ Particle effects and screen shake
- ✅ Title / Game / Game Over screens
- ✅ 24 headless logic tests
- ✅ Web build deployed

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/060_echo_memory/main.py
```

## What Works Well
- Pure-logic separation: all gameplay methods are testable without Pyxel
- Phase machine handles all transitions cleanly
- Combo injection (45% per round) ensures echo chains happen regularly

## Next Improvements
- Add audio feedback (Pyxel sound for correct/wrong/combo)
- Difficulty curve tuning (speed ramp could be smoother)
- Visual polish: combo counter animation, panel hover effects
