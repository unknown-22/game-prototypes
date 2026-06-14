# 125_snowboard_chain — SNOWBOARD CHAIN

**Source:** game_idea_factory #1 (Score 31.8) — 厄災封印デッキ構築からの再解釈  
**Engine:** Pyxel 2.x, 320×240, display_scale=2, 30fps

## 体験仮説

「スロープが分岐した時、どちらのレーンを選ぶか迷い、選んだ先で COMBO がつながり、ゴーストがもう一方を成功させて SURGE 爆発した瞬間に "読みが当たった！" という快感を得る」

## コアループ

1. スノーボーダーが自動下降（ゲートが上から降ってくる）
2. 同色ゲート連続ヒット → COMBO 増加（×0.2 スコア倍率）
3. COMBO ≥ 5 → SUPER MODE（5秒、スコア3倍、虹色無敵）
4. 分岐ゾーン（SPLIT）→ 左右レーン選択 → ゴーストが他方を走行
5. 両方ヒット → SURGE ボーナス（+200点、HEAT -30）
6. 別色ゲート → COMBO リセット + HEAT +15
7. HEAT ≥ 100 または HP = 0 → GAME OVER

## 操作

- ← → : 左右移動
- SPACE : スタート / リスタート
- 分岐ゾーン中: ← で左レーン、→ で右レーン

## うまくいっている点

- ✅ 分岐/合流（SPLIT/CONVERGE）メカニクスが新鮮（既存 124 プロトタイプにない）
- ✅ 53 headless tests 全通過
- ✅ ruff / ty クリーン
- ✅ OpenCode が完全自律実行（コード生成→テスト→修正→マニフェスト更新）
- ✅ SUPER MODE + SURGE の二段階ボーナスで「たまる→爆発する」快感

## 次に改善するなら最初に触る点

- ゴーストの視覚表現を充実させる（半透明トレイルなど）
- 分岐ゾーンの頻度・難度バランス調整
- 岩/木の障害物バリエーション追加
- スノーボーダーのアニメーション（傾き表現）

## 実行方法

```bash
cd ~/repos/game-prototypes
uv run python prototypes/125_snowboard_chain/main.py
```
