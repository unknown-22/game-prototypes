# SKI SURGE (136)

Downhill slalom skiing with color-match COMBO chain mechanics.

## Experience Hypothesis
Steering through colored gates at high speed, chaining same-color passes for escalating COMBO, creates a tense flow state where the player constantly weighs "push for combo" vs "play safe."

## Core Mechanic
- Steer skier (UP/DOWN arrows) through colored gates
- Same-color consecutive gate passes build COMBO (1→2→3→...)
- COMBO >= 5 triggers **SUPER SURGE**: 5 seconds of rainbow auto-pass, 3x score
- Wrong-color gate: COMBO resets to 0, HEAT +15
- HEAT reaches 100: GAME OVER (avalanche)
- Scoring: `10 × (1 + combo × 0.5)` per gate, ×3 in SUPER mode

## Risk/Reward
- Same-color chain = high score multiplier
- Wrong color = combo lost + avalanche danger
- Speed up = more gates but less reaction time

## Controls
| Key | Action |
|-----|--------|
| UP | Move skier up |
| DOWN | Move skier down |
| ENTER | Start / Restart |

## Source
Game Idea Factory #1 (Score 31.75): Deckbuilder/logistics — hooks "same card consecutive → mutation" + "CA grid infection/growth" reinterpreted as "same-color consecutive gates → COMBO chain" + "HEAT avalanche danger."

## Dev Status
- ✅ Core gameplay loop (steer → pass gates → score)
- ✅ COMBO chain system
- ✅ SUPER SURGE super mode
- ✅ HEAT risk/reward system
- ✅ Particle effects
- ✅ 3 screens: Title, Playing, Game Over
- ✅ 46 headless tests
- ✅ Web build

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/136_ski_surge/main.py
```
