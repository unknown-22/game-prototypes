# ZIP SURGE (144)

Color-match zipline action game — the first zipline prototype in the collection.

## Source
Reinterpreted from game_idea_factory Idea #1 (Score 31.85):
- **Hook**: "Log/replay as asset" → ghost trail showing best-run path
- **Hook**: "Cost is future hand" → heat accumulates from wrong-color landings (risk/reward)

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single file: `main.py` (867 lines)

## Experience Hypothesis (体験仮説)
「同じ色のジップラインを連続で乗り継いでCOMBOを積み重ね、SUPER ZIPが発動した瞬間に虹色のラインが次々と自動接続されてスコアが爆発する高揚感」

## Gameplay
- Player rides colored ziplines (RED/GREEN/BLUE/YELLOW) spanning across the screen
- Press SPACE/UP/Z to jump off current zipline toward the next
- LEFT/RIGHT/A/D to steer while airborne
- Same-color consecutive landings build COMBO chain
- COMBO >= 4 triggers SUPER ZIP: 5s rainbow mode (all lines auto-match, 3x score, auto-connect)
- Wrong-color landing: COMBO resets, HEAT +15
- HEAT >= 100 = GAME OVER
- Fall off screen = GAME OVER
- Speed increases over time

## Controls
| Key | Action |
|-----|--------|
| SPACE / UP / Z | Jump off zipline |
| LEFT / A | Steer left (airborne) |
| RIGHT / D | Steer right (airborne) |
| SPACE / RETURN | Start / Retry |

## Risk & Reward
- **Risk**: Chasing same-color ziplines for COMBO multiplier vs taking any safe landing
- **Risk**: Delaying jump for better line alignment vs jumping early to avoid falling
- **Reward**: COMBO x4+ = SUPER ZIP (3x score, auto-connect)
- **Reward**: Base score + COMBO × 5 per same-color land

## Dev Status
- [x] Core mechanic: zipline riding + jumping + steering
- [x] COMBO chain system with same-color detection
- [x] SUPER ZIP mode (rainbow, 3x, auto-connect)
- [x] HEAT risk system (wrong-color penalty, decay)
- [x] Game over: heat >= 100 or fall off screen
- [x] Speed ramping difficulty
- [x] Ghost trail (best-run replay)
- [x] Particle burst + floating text + screen shake feedback
- [x] 3 screens: Title, Game, Game Over
- [x] Headless tests (64 pass)
- [x] ruff + ty checks pass
- [x] Web build deployed

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/144_zip_surge/main.py
```

## What Works
- Zipline physics (riding, jumping, gravity, steering)
- COMBO chain: same-color consecutive landings increment combo
- SUPER ZIP: COMBO >= 4 activates 5s rainbow auto-connect mode
- Heat/risk: wrong-color resets combo and adds HEAT (game over at 100)
- Visual feedback: particles, floating text, screen shake, ghost trail
- Balance: speed ramps up over time, forcing faster decisions

## Next Improvements
- Add obstacles (birds, branches) to dodge while airborne
- Wind gusts that affect steering
- Multiple zipline slope angles (uphill/downhill)
- Score milestones unlock new zipline skins
