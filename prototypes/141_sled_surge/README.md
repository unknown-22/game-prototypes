# 141 — SLED SURGE

Side-scrolling bobsled game — steer through color-coded gates, build COMBO chains, trigger SUPER BOOST.

## Source
Reinterpreted from game_idea_factory Idea #1 (score 31.05): deckbuilder with "log/replay as asset" + "hand limit = 3" hooks.
- "Log/replay as asset" → ghost sled showing best previous run path
- "Hand limit = 3" → reinterpreted as limited steering adjustments per section

All 10 generated ideas clustered in deckbuilder/dice/auto-shooter (same as previous 20+ sessions).
Bobsled/luge was the first-ever bobsled genre in the collection.

## Experience Hypothesis (体験仮説)
同じ色のゲートを連続でくぐり抜ける緊張と、SUPER BOOST発動で一気に加速する爽快感を交互に味わえる。

## Mechanics Hypothesis (メカニクス仮説)
同色連続ゲート通過（COMBO）→ SUPER BOOST（5秒虹色無敵）の報酬ループが、
色違い通過（COMBOリセット）+ 壁衝突（即死）+ ゲート取り逃し（HEAT）のリスクと釣り合い、
プレイヤーに「もっとギリギリを狙いたい」と思わせる。

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single file: main.py (604 lines)

## Gameplay
- Steer sled UP/DOWN (arrow keys or W/S)
- Gates scroll from right to left with track auto-scroll
- Same-color consecutive gate passes → COMBO+1
- COMBO ≥ 5 → SUPER BOOST (5s): rainbow sled, 3x score, auto-collect, wall immunity
- Wrong-color gate → COMBO resets to 1
- Missed gate → HEAT +20. HEAT ≥ 100 → GAME OVER
- Wall collision → instant GAME OVER
- Ghost sled shows best previous run path

## Controls
- UP/DOWN or W/S: Steer sled
- ENTER or SPACE: Start game / Retry

## Risk & Reward
- Same-color COMBO continuation → high multiplier (COMBO × 10 bonus)
- Wrong-color gate → COMBO resets to 1 (lose multiplier)
- Gates near walls → more points but higher collision risk
- Safe play (any color) → no COMBO multiplier → low score efficiency

## Screens
1. TITLE: Game title, controls, high score display
2. GAME: Track with gates, sled, HUD (score, combo, heat bar, distance, SUPER timer), ghost sled
3. GAME_OVER: Final score, best score, max combo, retry prompt

## Dev Status
- ✅ Core mechanic: gate color-match COMBO chain
- ✅ SUPER BOOST with rainbow invincibility
- ✅ HEAT risk system
- ✅ Ghost sled best-run replay
- ✅ 3 screens (Title/Game/GameOver)
- ✅ 85 headless tests (ruff + ty clean)
- ✅ Web build deployed to docs/141_sled_surge.html

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/141_sled_surge/main.py
```

## How to Test
```bash
uv run pytest prototypes/141_sled_surge/tests/test_game.py -v
```
