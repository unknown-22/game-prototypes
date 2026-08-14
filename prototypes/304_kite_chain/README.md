# KITE CHAIN (304)

Color-match kite-flying arcade game. First kite-flying genre in the collection.

## Source
Reinterpreted from `game_idea_factory` idea #1 (space-mining deckbuilder, Score 31.85):
- 'synthesis compression' → same-color COMBO chain → SUPER KITE
- 'log/replay as asset' → the kite's colored ribbon trail (flight history made visible)

## Engine
Pyxel 2.x, 320×240, display_scale=2, 60 FPS. Single file `main.py`.

## Gameplay
- The kite's color auto-cycles (20f → 12f) through 4 colors (RED / LIME / DARK_BLUE / YELLOW).
- Colored wind gusts drift left across the sky. Fly the kite (arrow keys) INTO gusts.
- **Same-color** gust → COMBO +1, `score += 10 * combo * multiplier`.
- **Wrong-color** gust → HEAT +15, combo reset, screen shake.
- **COMBO ≥ 4** → SUPER KITE (300f rainbow): any color matches, score ×3, HEAT frozen.
- HEAT reaches 100 (string snaps) or the 60s timer runs out → game over.

## Controls
- Arrow keys: fly the kite (diagonal normalized, clamped to screen)
- ENTER / SPACE: start (title) / restart (game over)
- ESC: quit

## Dev status
- ✅ Core loop (fly → match gusts → combo → SUPER KITE)
- ✅ 3 screens (title / game / game over)
- ✅ Particle system + floating text + screen shake
- ✅ HEAT risk + 60s timer + difficulty escalation
- ✅ 27 headless tests, ruff + ty clean

## 体験仮説
同色の突風を次々に捉えて凧のリボン軌跡が空に虹の帯を描き、SUPER KITE の虹色で一気に風を掴んでスコアが爆発する、という爽快感を得られる。

## 実装したコアループ
見る（突風の色と凧の色）→ 判断（どの突風を追うか / 待つか）→ 操作（矢印キーで凧を操縦）→ 結果（COMBO 伸長 or HEAT 上昇）→ 次の判断。

## うまくいっている点
- 同色 COMBO → SUPER KITE のフィードバックが明確（虹色ボーダー + リボン軌跡 + パーティクル）。
- リスクとリターン（同色を追うと COMBO が伸びるが、移動中に誤色に当たる危険）が色だけで直感的に伝わる。

## 次に改善するなら最初に触る点
- 突風の密度・速度の調整（初回プレイで難しすぎないか）。
- リボン軌跡の視覚的な残り方（現在は単色ドットで、SUPER 中の虹色軌跡が弱い）。

## How to run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/304_kite_chain/main.py
```
