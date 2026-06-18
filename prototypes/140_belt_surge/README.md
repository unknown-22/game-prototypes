# BELT SURGE

Conveyor belt color-match chain reaction game.

## Source
- **Idea**: Game Idea Factory #1 (Score 31.8) — 厄災封印（暴走制御）デッキ構築
- **Reinterpretation**: "各フロアでルールが1つだけ変わる" + "UIの連鎖演出（崩壊/増加/圧縮）" + "heat/risk" hooks → conveyor belt factory puzzle
- **Genre**: Conveyor belt / Factory puzzle (first in collection)

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Python 3.12+

## Experience Hypothesis (体験仮説)
「スキャナーゲートを右端ギリギリに置いてリスクを最大化し、高速で流れる同色アイテムを連続タグしてCOMBO>=5でSURGEが発動、ベルト上の全タグ付きアイテムが一斉に爆発してスコアが跳ね上がる瞬間に、リスクを取った者だけが得られる高揚感を味わえる」

## Mechanics → Dynamics → Aesthetics
- **Mechanics**: Items flow left→right on belt. Scanner gate positioned by player. Matching-color items passing through gate are tagged. Consecutive same-color tags = COMBO chain. COMBO>=5 = SURGE (all tagged items burst, massive score). Score increases with item x-position at tag time (risk/reward). Untagged items reaching right edge = HEAT. HEAT>=100 = GAME OVER.
- **Dynamics**: Player must balance gate position: closer to right edge = higher score per tag but higher risk of items escaping untagged. Color cycling adds adaptation pressure. Speed increases over time force faster decision-making.
- **Aesthetics**: "Risk-it-for-the-biscuit" thrill when SURGE triggers after holding the gate at extreme right edge. Satisfying particle burst + screen shake on SURGE.

## Core Loop
1. Items spawn on left, flow right
2. Player positions gate (LEFT/RIGHT) and chooses color (1-4)
3. Matching items get tagged → COMBO builds
4. COMBO>=5 → SURGE: all tagged items burst for massive score
5. Untagged items → HEAT
6. HEAT>=100 → GAME OVER
7. Every 300 points: gate color auto-cycles (rule changes)
8. Speed increases every 15 seconds

## Controls
| Key | Action |
|-----|--------|
| LEFT/RIGHT | Move scanner gate |
| 1 | RED gate |
| 2 | GREEN gate |
| 3 | BLUE gate |
| 4 | YELLOW gate |
| SPACE | Start / Retry |

## Scoring
- Tag score = `10 × (1 + item_x / 320)` — items tagged closer to right edge worth more
- SURGE bonus = `COMBO × 100 × (1 + tagged_count × 0.5)`

## What's Working Well
- Risk/reward gate positioning creates meaningful choices
- SURGE chain reaction is visually and mechanically satisfying
- Auto color cycle adds "rule changes" flavor from original idea
- Simple, quick restart loop (30-90 second play sessions)

## Next Improvement Targets
- Add sound effects (pyxel.play)
- Boss waves at score milestones
- Multiple belt lanes for more complex routing
- Visual conveyor belt animation (moving arrows)

## Dev Status
- ✅ Core gameplay loop
- ✅ Title / Game / Game Over screens
- ✅ Combo chain + SURGE mechanic
- ✅ Heat risk system
- ✅ Difficulty ramping (speed)
- ✅ Auto color cycle
- ✅ Particle system + popup text
- ✅ Screen shake on SURGE
- ✅ Headless tests (51 pass)
- ✅ Web build (docs/140_belt_surge.html)
- ⬜ Sound effects

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/140_belt_surge/main.py
```
