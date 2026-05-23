# PULSE REACTOR

Power plant reactor control rhythm game.

## Experience Hypothesis

Hitting same-colored beats in rhythm to build a COMBO chain creates tension.
When overload kicks in at COMBO 8, the HP drain pressure builds until the
player discharges for a massive score bomb — a classic risk/reward squeeze.

## Core Loop

1. Colored beats approach from 4 screen edges toward the center reactor
2. Press corresponding arrow key to intercept in the strike zone
3. Same-color consecutive hits → COMBO → SYNTHESIS multiplier increases
4. COMBO >= 8 → OVERLOAD (periodic HP drain)
5. Press SPACE to DISCHARGE (combo * 200 bonus, resets overload)
6. Miss or wrong color → HP -1, combo reset
7. Survive 60 seconds with HP > 0

## What Works Well

- Immediate feedback on hit/miss/wrong with particles and floating text
- Clear visual distinction between perfect hit, hit, wrong color, miss
- Overload tension forces a risk/reward decision: hold combo for higher discharge bonus vs discharge early to stop HP drain
- Difficulty ramps smoothly: more colors unlock, speed increases, spawn rate increases
- Screen shake on discharge creates satisfying payoff moment

## Next Improvements

- Add a combo-based beat sequence (predefined patterns) rather than purely random
- Add sound effects for hits, combo milestones, and discharge
- Add visual trail/afterimage on fast beats for readability
- Consider a "fever" mode after discharge for bonus scoring window
