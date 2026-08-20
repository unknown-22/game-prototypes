# EYEBALL — Carnival Estimation Arcade

Prototype **329_eyeball**. A quick-estimation arcade game.

## 体験仮説 (Experience hypothesis)

「一瞬しか見えない量（点の数・バーの割合）を素早く見積もり、RISKY（自信あり）で賭けて
ズバリ的中させたときの快感」— eyeball a flashed quantity, bet RISKY, and nail it for a 3x PERFECT.

## 実装したコアループ (Core loop)

1. **SHOW** — 刺激（点の数、またはバーの充填%）が一瞬表示される（40f→12f と短くなる）。
2. **GUESS** — スライダーで見積もり値を決め、自信 SAFE(1x, ±4) / RISKY(3x, ±1) を選んで LOCK。
3. **REVEAL** — 正誤判定・得点・ストリーク更新。一致なら PERFECT! (+30)、許容内なら HIT!、
   外れなら MISS（ストリーク 0）。

得点 = `20 × 倍率 + ストリーク × 10`（完全一致で +30）。60 秒で TIME UP、スコアとベストを表示。

## リスクとリターン (Risk / reward)

- RISKY は 3 倍だが許容 ±1。1 ずれただけで 0 点になりストリークも失う。
- SAFE は 1 倍だが ±4 まで許容。安定して稼げる。
- 熟考しすぎるとタスク消化数が減り、スコア機会を逃す（タスクあたり解答時間も 260f→120f に短縮）。

## うまくいっている点

- 判定ロジック（`_score_guess` / `_flash_frames` / `_count_range` / `_solve_window` /
  `_tolerance_for`）は pyxel 非依存の純関数で、21 件のヘッドレステストで検証済み。
- `getattr` ガード付き `reset()` により `Game.__new__` で最小限の初期化からテスト可能。
- 色合わせ COMBO 方式を意図的に破棄（323〜328 のブレイクアウェイシリーズ第 7 弾）:
  色マッチなし・COMBO なし・HEAT なし — 純粋な「見積もり精度 × 自信」のキャリブレーション。

## 次に改善するなら最初に触る点

- ゲームオーバー後の再スタートが TITLE を経由する 2 押しになっている（1 押しで直接 PLAYING に）。
- タスク種類は COUNT / FRACTION の 2 種。3 種目（線分の長さ・角度）を追加すると変化が増える。
- タイムアウト時に MISS 演出（フロートテキスト）を出していない。

## 操作方法 (Controls)

- タイトル: SPACE / クリックで開始
- GUESS: ←→ / A D でスライダー調整、↑↓ / W S で自信切替、SPACE / ENTER / LOCK クリックで確定
- マウス: スライダーをクリックで値セット、SAFE/RISKY ボタン、LOCK ボタン
- ゲームオーバー: SPACE / クリックで再挑戦

## 実行方法 (How to run)

```bash
cd ~/repos/game-prototypes
uv run python prototypes/329_eyeball/main.py
```

テスト: `uv run python prototypes/329_eyeball/test_imports.py`
