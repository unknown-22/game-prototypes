# 101 — Chop Chain (チョップチェイン)

空手の板割りアーケードゲーム。

## 体験仮説
同じ色の板を連続で割ってCOMBOを積み上げ、SUPER CHOPで全色の板を一気に粉砕する爆発的爽快感が、プレイヤーに「次はもっとコンボを伸ばしたい」と思わせる。

## メカニクス仮説
- **Mechanics**: 4列に色付きの板が積み上がる。SPACEキーで板を割る。同色連続割りでCOMBO増加。
- **Dynamics**: 高COMBOを狙うほど間違った色を割るリスクが高まる（HEAT蓄積）。SUPER CHOP（COMBO≥5）は5秒間の無敵時間。
- **Aesthetics**: 「リスクを取ってコンボを伸ばす緊張感」→「SUPER CHOP発動の解放感」

## コアループ
1. 板が積み上がる（時間経過で加速）
2. プレイヤーが列を選びSPACEで板を割る
3. 結果が即時フィードバック（スコア、COMBO、パーティクル）
4. 次に割る色を判断（同色狙うかリセットするか）
5. HEAT満タンまたはオーバーフローでゲームオーバー

## 操作
- LEFT/RIGHT: 列選択
- SPACE: 板を割る
- TITLE/GAME OVER画面: SPACEで開始/再挑戦

## ルール
- 同色連続割り → COMBO+1、スコア = 10 × COMBO
- 異色 → HEAT+2、COMBOリセット
- 空列 → HEAT+3
- COMBO ≥ 5 → SUPER CHOP（5秒間、全色受付、スコア3倍、HEAT無効）
- HEAT ≥ 10 または板のオーバーフロー → GAME OVER
- HEAT: 2秒ごとに1自然回復

## 面白い瞬間
COMBO 5でSUPER CHOPが発動し、5秒間全色の板を一気に粉砕する爆発的連鎖

## 開発状況
- ✅ コアメカニクス（板割り＋COMBO連鎖）
- ✅ SUPER CHOP発動・満了
- ✅ HEATリスクシステム
- ✅ パーティクル＋フローティングテキスト
- ✅ 画面シェイク
- ✅ 難度上昇（スポーン間隔短縮）
- ✅ 66 headless tests
- ⬜ サウンド
- ⬜ 板の見た目のバリエーション

## 次に改善するなら
- 板割りのタイミング要素（パワーメーター）追加
- 空手家キャラクターの描画
- ハイスコア保存

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/101_chop_chain/main.py
```

## Source
- Game Idea Factory #1 (score 31.8): 「発電所（過負荷と放電）／デッキ構築ローグライト」
- フック: 「連鎖演出（崩壊/増加/圧縮）」「heat管理」を空手板割りに再解釈
- 初の空手/板割りプロトタイプ
