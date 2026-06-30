# RAFT SURGE (182)

White water rafting color-match COMBO chain game.

## Source
Reinterprets game_idea_factory Idea #1 (Score 31.8):
- "chain collapse" → rock turbulence cascade
- "gravity" → river current
- "log/replay as asset" → ghost raft trail of best run

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single file: `main.py` (657 lines)

## Gameplay
Top-down river scrolling downward. Steer the raft (LEFT/RIGHT arrow keys) through rapids, passing through colored buoys and avoiding rocks.

**Core Loop:**
1. Steer raft to hit same-color buoys → build COMBO
2. COMBO≥4 → SUPER PADDLE (180f rainbow mode: 3x score, auto-avoid rocks, any-color auto-match)
3. Hit rocks → HEAT +20, 10f stun
4. Wrong-color buoy → COMBO reset, HEAT +10
5. HEAT≥100 or timer 0 → Game Over

**Risk/Reward:** Same-color COMBO chain gives exponential score growth and SUPER PADDLE, but wrong-color hits reset COMBO and add HEAT. Rocks create dangerous turbulence near high-value buoy lanes.

**Most Fun Moment:** 同色のブイを4連続で通過してSUPER PADDLEが炸裂し、虹色のラフトが岩を自動回避しながら全てのブイを吸い込み、スコアが3倍に跳ね上がる瞬間。

## Controls
- TITLE: SPACE or ENTER → start
- PLAYING: LEFT/RIGHT or A/D → steer raft
- GAME OVER: SPACE or ENTER → retry

## Colors
- Buoys: RED(8), GREEN(3), DARK_BLUE(5), YELLOW(10)
- Raft: CYAN(12), SUPER: rainbow cycling
- Rocks: BROWN(4)
- Ghost trail: PINK(14)
- Heat bar: GREEN→YELLOW→ORANGE→RED gradient

## Dev Status
- ✅ Core gameplay (steer, buoys, rocks, COMBO chain, SUPER PADDLE)
- ✅ HEAT risk system (check-before-decay)
- ✅ Difficulty scaling (speed +0.1 every 600f)
- ✅ Ghost trail best-run replay
- ✅ Particle system (splash, crash, SUPER aura, water trail)
- ✅ Floating text (score, COMBO, SUPER, CRASH)
- ✅ 60s timer
- ✅ 3 screens (Title / Playing / Game Over)
- ✅ 103 headless tests
- ✅ ruff + ty clean
- ✅ Web build (docs/182_raft_surge.html)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/182_raft_surge/main.py
```

## Next Improvement
Add river width variation (narrow sections create risk/reward pinch points) and difficulty-based buoy speed increase.
