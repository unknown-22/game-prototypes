# GOMOKU SURGE (173_gomoku_surge)

色合わせ五目並べ（Gomoku）× COMBOチェイン。

## 体験仮説
同色の石を連続で置いてCOMBOを5まで積み上げ、SUPER STONEが炸裂して虹色で任意の場所に置け、一気に5連を作って勝利する瞬間に「溜めて解放する」快感を感じられる。

## コアループ
1. 盤面を見て、現在の自分の色を確認する
2. 空いているセルをクリックして石を置く
3. 同色→COMBO増加、色違い→COMBOリセット＋HEAT上昇
4. COMBO >= 5 で SUPER STONE 発動（5秒間虹色、3倍スコア、自由配置）
5. AIの手番 → AIが応手
6. 5連ができたら勝利、HEAT >= 100 か盤面が埋まったら敗北

## 操作
- マウスクリック: 石を置く
- SPACE / RETURN: スタート / リスタート

## 仕様
- エンジン: Pyxel 2.x, 320×240, display_scale=2
- 盤面: 8×8, セルサイズ 28px
- 色: プレイヤー 4色 (RED/GREEN/DARK_BLUE/YELLOW), AI GRAY
- SUPER STONE: COMBO >= 5, 300フレーム (5秒), スコア3倍, +200ボーナス/石
- HEAT: 色ミスマッチ +15, 減衰 0.005/フレーム, 上限100でゲームオーバー
- AI: 4段階優先度 (勝利 > 4連ブロック > 3連ブロック > 戦略的配置)

## ソース
ゲームアイデアファクトリー Idea #1 (Score 32.2) の再解釈:
- 「ログ/リプレイが資産」→ 前回の移動のゴーストハイライト
- 「連鎖崩壊/増加/圧縮」→ COMBOチェイン + SUPER STONE 解放

## Dev Status
- ✅ コアメカニクス (色合わせCOMBO + SUPER STONE + AI対戦)
- ✅ 勝利検出 (4方向カウント)
- ✅ HEAT リスクシステム
- ✅ AI 対戦相手 (4優先度ロジック)
- ✅ パーティクル + フローティングテキスト
- ✅ 3画面 (Title / Playing / Victory+GameOver)
- ✅ 32 headless tests
- ✅ ruff / ty パス
- ✅ Webビルド

## 改善するなら
- BDFフォント対応（日本語表示）
- AI難易度設定の追加
- サウンドエフェクト
- 盤面サイズ選択 (8×8 / 10×10 / 15×15)

## 実行方法
```bash
cd ~/repos/game-prototypes
uv run python prototypes/173_gomoku_surge/main.py
```
