# CLIMB SURGE (245_climb_surge)

**🧗 Rock Climbing / Bouldering with Color-Match COMBO Chain**

## Source
Reinterpreted from game_idea_factory #1 (Score 32.05):
- Hook "synthesis compression" → same-color consecutive hold COMBO chain → SUPER GRIP
- Hook "one-color-per-turn" → grip color auto-cycling constraint

All 10 generated ideas were deckbuilder/dice/auto-shooter cluster. Picked "rock climbing/bouldering" from untapped genres.

## 体験仮説 (Experience Hypothesis)
「壁に取り残されそうな中で同色ホールドを連続で掴み、SUPER GRIPで一気に壁を駆け上がるカタルシス」

## Engine
- Pyxel 2.9.5, 320×240
- Python 3.13

## Gameplay
- Arrow keys / WASD to move to adjacent holds on the climbing wall
- Grip color auto-cycles among 4 colors (RED/LIME/DARK_BLUE/YELLOW) every 90f→40f
- Same-color hold grab = COMBO chain (score = 10 × combo × multiplier)
- COMBO ≥ 4 → SUPER GRIP (300f rainbow mode, any color, 3x score, HEAT gain disabled)
- HEAT risk: mismatch +15 + stun 10f, fall +25 + stun 20f, decay 0.02/f, cap 100 → game over
- 60s timer
- Hold spawn interval 60f→30f (escalation)
- Ghost path shows best climb run

## Controls
| Key | Action |
|-----|--------|
| ↑/↓/←/→ or WASD | Move to adjacent hold |
| SPACE/RETURN | Start / Restart |

## Dev Status
- ✅ Core mechanic (color-match climbing)
- ✅ COMBO chain + SUPER GRIP
- ✅ HEAT risk system
- ✅ Particle system + floating text
- ✅ Ghost path best-run replay
- ✅ 72 headless tests
- ✅ Web build (245_climb_surge.html)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/245_climb_surge/main.py
```

## First Climbing/Bouldering Genre
This is the first rock climbing / bouldering prototype in the collection.
