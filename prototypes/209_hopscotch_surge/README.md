# HOPSCOTCH SURGE (209)

石蹴り（Hopscotch）をテーマにした色合わせCOMBOチェインゲーム。

## 体験仮説

「同じ色のマスに連続で着地してCOMBOを爆発させ、SUPER HOPで虹色に輝きながら石蹴りを駆け抜けるのが気持ちいい」

## 実装したコアループ

- SPACEキーで前方のマスに跳ぶ（ホップ）
- 現在のマスと同じ色に着地 → COMBO継続
- 異なる色に着地 → COMBOリセット + HEAT+15
- タイムアウトで自動着地 → HEAT+5
- COMBO >= 4 → SUPER HOP（5秒間、全色マッチ、スコア3倍）
- HEAT >= 100 または60秒経過 → ゲームオーバー
- 時間経過でホップ間隔が短縮（難度上昇）

## 操作方法

- SPACE: ホップ
- TITLE画面: SPACEでスタート
- GAME OVER画面: SPACE/Rでリスタート

## リスクとリターン

同色COMBOを狙うと高倍率スコアとSUPER HOPが得られるが、色を見誤るとCOMBOリセット＋HEAT上昇。タイムアウト前に早く跳ぶか、色が変わるのを待って安全に自動着地を選ぶかの判断。

## うまくいっている点

- シンプルな1ボタン操作でテンポよく遊べる
- ホップ間隔の段階的短縮で適度な難度上昇
- SUPER HOP発動の視覚的フィードバック（虹色エフェクト）

## 次に改善するなら最初に触る点

- マスの視覚的変化（跳ぶ前の予告表示、着地時のアニメーション強化）
- スコア履歴の永続化（ハイスコア保存）

## 実行方法

```bash
cd ~/repos/game-prototypes
uv run python prototypes/209_hopscotch_surge/main.py
```

## Source

game_idea_factory #1 (Score 32.05) — 「合成圧縮 + 1色制約」フックを石蹴りに再解釈

## Engine

Pyxel 2.x, 320×240

## Dev Status

- ✅ 基本プレイループ（タイトル → プレイ → ゲームオーバー → リスタート）
- ✅ COMBOチェイン + SUPER HOP
- ✅ HEATリスクシステム
- ✅ 難度スケーリング（ホップ間隔短縮）
- ✅ パーティクル + フローティングテキスト
- ✅ 27 headless tests
- ⬜ ハイスコア保存
- ⬜ BGM/SE
