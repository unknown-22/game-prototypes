# 081_CHROMA RALLY — Color-Match Tennis Rally

Side-view tennis rally game built in Pyxel 2.x (320×240).

**Source**: game_idea_factory #1 (Score 32.75) — 魔法学院/ルール改変 デッキ構築ローグライト
Reinterpreted hooks: 合成/圧縮 → COMBO chain, CA感染/増殖 → ball color cycling

## 体験仮説
「ラケットの色をボールに合わせて連続リターンし、COMBOが4に達してSUPER SHOTが炸裂する瞬間が面白い」

## コアループ
1. ボールがラケットに向かって飛んでくる
2. プレイヤーは↑↓でラケットを動かして位置取り
3. ラケット色とボール色が一致してヒット → COMBO+1、ボール色循環
4. 色不一致 → COMBO=0 リセット
5. COMBO ≥ 4 で一致ヒット → SUPER SHOT（超高速、AI反応不可）
6. ミス → 相手に得点。先に7点取った方が勝利

## 操作方法
- ↑↓: ラケットを上下に移動
- ENTER: タイトル画面で開始 / ゲームオーバーでリスタート

## リスクとリターン
- 同色COMBO継続でスコア倍率上昇・SUPER SHOT解放
- 色不一致でCOMBOリセット
- 位置取りミスで失点（ボールがラケットを通過）

## Dev Status
- ✅ ゲーム画面・タイトル・ゲームオーバー
- ✅ AI対戦相手
- ✅ パーティクルシステム
- ✅ ボール軌跡トレイル
- ✅ SUPER SHOT + 画面振動
- ✅ 40 headless tests
- ✅ Web ビルド (Pyxel app2html)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/081_chroma_rally/main.py
```

## 次に改善するなら
- サウンドエフェクト追加
- AIの難易度調整（速度・精度）
- 特殊ショット（ロブ、ドロップ）
