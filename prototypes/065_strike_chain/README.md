# STRIKE CHAIN (065_strike_chain)

Color-match bowling prototype. First sports genre in the collection.

## Source
Reinterpreted from game_idea_factory idea #1 (Score 31.15):
- 「連鎖伝播」→ 同色連続ストライク COMBO
- 「3つまで管理」→ 3ミスでヒート危険域、5ヒートでゲームオーバー
- 「risk/heat」→ ガター/ミスで HEAT 蓄積、レーンオイル劣化

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Python 3.12, dataclasses, type hints

## 体験仮説
「ピンの色を見極め、同色ストライクを連続させて COMBO を伸ばし、STRIKE SURGE で残りピンが一掃される瞬間にカタルシスを感じる」

## Gameplay
- 4色のピン（RED, GREEN, DARK_BLUE, YELLOW）がボウリングピン配置
- マウスで照準角度を決め、長押しでパワーチャージ、離してボールを転がす
- 同色ピンを連続で倒すと COMBO が伸び、スコア倍率が上がる
- COMBO 5以上で STRIKE SURGE（次球が虹色、全ピン同色扱い、スコア3倍）
- ガター/全ミスで HEAT +1。HEAT 3でボールがランダムドリフト。HEAT 5で強制ゲームオーバー
- 全10フレーム

## Controls
- マウスX: 照準角度 (AIMING フェーズ)
- 左クリック押下: パワーチャージ開始
- 左クリック解放: ボール発射
- SPACE: タイトルからスタート
- R: ゲームオーバーからリトライ

## コアループ
1. ピン配置を見る
2. ボール色を確認し、狙うピンを判断する（リスク：同色狙いはボーナス大だが外すと HEAT）
3. 照準 → パワー → 発射
4. 結果（スコア/COMBO/HEAT のフィードバック）
5. 次のフレームへ

## リスクとリターン
- 同色ピンのみ狙う → COMBO UP、高スコアだが全ミスのリスク大
- 安全にどのピンも狙う → COMBO リセット、スコアは伸びにくい
- STRIKE SURGE を温存するタイミング判断（HEAT 高いときに使うか、早めに使うか）

## Dev Status
- ✅ 全フェーズ実装 (TITLE/AIMING/ROLLING/SCORING/GAME_OVER)
- ✅ パーティクルシステム、フローティングテキスト
- ✅ 55 headless tests (pytest)
- ✅ ruff + ty クリーン
- ✅ Web ビルド (docs/065_strike_chain.html)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/065_strike_chain/main.py
```
