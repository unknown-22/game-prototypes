# TUG CHAIN

## Source
Game idea #1 from 2026-06-06 generation (Score 32.6): Calamity sealing deckbuilder with "log/replay as asset" + "chain collapse/expansion/compression" hooks.
Reinterpreted into **tug of war** — the first prototype in this genre for the collection.

## Engine
Pyxel 2.x, 320×240, display_scale=2

## Core Mechanic
Side-view tug of war with colored rope segments. Press SPACE when the grip zone color matches your pull color.
- Same-color consecutive pulls → COMBO +1, pull force increases
- COMBO >= 4 → SUPER PULL (3x force, rainbow effect, screen shake)
- Ghost trails of past pulls amplify current pull force (log/replay as asset)
- Wrong color or missed timing → COMBO reset, HEAT +2/+3, AI pulls back
- HEAT >= 10 → OVERHEAT (game over)
- Win: pull rope past left edge
- 60-second time limit

## Experience Hypothesis
綱引きで同じ色の節を連続でリズムよく引き、COMBOが4以上に達してSUPER PULLが発動し、相手を一気に引きずり込んで勝つ瞬間が面白い。

## Mechanics → Dynamics → Aesthetics
- **Mechanics**: Color-matched timed pulls, COMBO chain, SUPER PULL multiplier, ghost trail amplification, HEAT risk, AI opponent
- **Dynamics**: Risk/reward of maintaining color chain vs. reset safety; timing pressure; ghost trail accumulation for escalating force
- **Aesthetics**: Rhythmic pull satisfaction, explosive SUPER PULL power, screen shake feedback

## Controls
- SPACE: Pull (must match grip zone color with pull color)
- SPACE/RETURN: Navigate menus

## Dev Status
- [x] Core pull mechanic
- [x] COMBO chain system
- [x] SUPER PULL (combo >= 4, 3x force, rainbow)
- [x] Ghost trail amplification
- [x] HEAT risk system
- [x] AI opponent
- [x] Timer (60 seconds)
- [x] Win/lose conditions
- [x] Particle effects
- [x] Screen shake
- [x] 49 headless tests
- [x] ruff + ty clean
- [x] Web build

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/104_tug_chain/main.py
```

## What Works Well
- The COMBO → SUPER PULL escalation feels rewarding
- Ghost trails provide visual feedback and mechanical amplification
- HEAT risk creates genuine tension between safe play and combo-chasing
- Simple one-button input makes the core loop accessible

## Next Improvement
- Add pull color visual countdown for better timing feedback
- Add more rope segment animation (stretch/wobble)
- Add difficulty progression (faster AI, faster color cycling)
- Add sound effects for pulls, combos, SUPER activation
