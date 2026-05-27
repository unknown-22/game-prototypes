# CHROMA ROUTE (076_chroma_route)

Flight Control風の航路描画ゲーム。

## Source
- game_idea_factory 2026-05-28 generation
- Idea #1 (Score 31.65) を再解釈: デッキ構築 → 航路描画
- フック: 「合成圧縮」→同色COMBO連鎖, 「回路/パイプ可視化」→描かれた航路そのもの

## Engine
- Pyxel 2.x, 320×240, FPS=30
- Python 3.12+

## 体験仮説
プレイヤーは複数の艦船の航路を同時に描き分ける緊張感の中で、同色連続着陸のCOMBOが爆発的にスコアを伸ばす快感を味わう。

## Gameplay
- 4色の艦船（赤/緑/水色/黄）が画面端に出現
- 艦船をクリック＆ドラッグで航路を描き、同色の滑走路へ誘導
- 同色連続着陸でCOMBO構築（+COMBO×100点）
- COMBO >= 5 で SURGE 発動（3秒間全着陸が正解扱い・スコア2倍）
- 色違い着陸: COMBOリセット、-50点
- 船同士の衝突: COMBOリセット、-100点、両船破壊
- 90秒の時間制限内でスコア最大化

## Controls
- マウスクリック: 艦船を選択
- ドラッグ: 航路（ウェイポイント）を描画
- リリース: 艦船が航路に沿って飛行開始

## Dev Status
- ✅ タイトル画面
- ✅ ゲーム画面（航路描画・COMBO・SURGE）
- ✅ ゲームオーバー画面
- ✅ パーティクルシステム
- ✅ フローティングテキスト
- ✅ 難度上昇（出現間隔短縮・速度上昇・最大船数増加）
- ✅ 34 ヘッドレステスト
- ✅ ruff / ty クリア

## 一番面白い瞬間
複数の船の航路を同時に描き分け、同色連続着陸のコンボが爆発的にスコアを伸ばす瞬間。

## How to run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/076_chroma_route/main.py
```
