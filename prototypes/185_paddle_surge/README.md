# PADDLE SURGE — 185_paddle_surge

カヤックスラローム × 色合わせ COMBO チェイン

## 体験仮説

「同色ゲートの COMBO チェインを川の流れが速くなる中で維持し、SUPER SURGE が炸裂する瞬間に恐怖から解放へと感情が切り替わる」

## ソース

- game_idea_factory Idea #1 (Score 32.2) — 「ログ/リプレイが資産」「UIの連鎖演出で気持ちよさを作る」
- 再解釈: デッキ構築/ダイス → カヤックスラローム（未開拓ジャンル）
- フックの変換: 「ログ/リプレイが資産」→ 航跡/wake効果、「連鎖演出」→ COMBO チェイン

## エンジン

- Pyxel 2.x, 320×240, display_scale=2
- Python 3.12+, dataclasses, Enum, math

## ゲームプレイ

- **コアメカニクス**: カヤックの色と一致するゲートを連続通過して COMBO を伸ばす
- **COMBO チェイン**: 同色連続通過で COMBO 倍率上昇（最大 x10）
- **SUPER SURGE**: COMBO ≥ 4 で発動（300フレーム、虹色モード、スコア3倍、全色自動マッチ）
- **HEAT リスク**: 色違いゲート +15, 岩衝突 +20, 川岸接触 +5 → HEAT 100 で転覆（ゲームオーバー）
- **難度上昇**: 距離に応じてスクロール速度上昇、ゲート出現間隔短縮

## 操作

| キー | 操作 |
|------|------|
| 矢印キー / WASD | カヤックを移動 |
| SPACE / ENTER | タイトル画面で開始 / ゲームオーバーでリトライ |

## 色

| 色 | Pyxel値 |
|----|--------|
| RED | 8 |
| GREEN | 3 |
| DARK_BLUE | 5 |
| YELLOW | 10 |

## 画面

1. **タイトル**: ゲーム説明 + 操作説明
2. **プレイ中**: トップダウン川スクロール、ゲート通過、岩回避
3. **ゲームオーバー**: スコア、最大COMBO、距離表示 → SPACEでリトライ

## 検証状況

- ✅ `main.py` — 466 lines
- ✅ `test_imports.py` — 93 tests, all pass
- ✅ `ruff check` — all clear
- ✅ `ty check` — all clear
- ✅ Web ビルド (`docs/185_paddle_surge.html`)
- ✅ `docs/prototypes.json` 更新済み

## 実行方法

```bash
cd ~/repos/game-prototypes
uv run python prototypes/185_paddle_surge/main.py
```

## デザイン上のポイント

- **リスク/リターン**: 同色COMBOを狙うほど高得点だが、川の流れが速くなると色違いゲートを避けるのが難しくなる
- **面白い瞬間**: COMBO x4 到達 → SUPER SURGE 発動 → 全ゲートが虹色に光りスコアが3倍で跳ね上がる
- **失敗の納得感**: HEAT ゲージが画面下部に表示され、何が原因で HEAT が上がったかが分かる

## 改善ポイント

- 川の蛇行（左右カーブ）を追加してよりダイナミックな操作に
- ウェイク/航跡のビジュアル効果を COMBO ボーナスに連動
- 水上のアイテム（回復、スコアボーナス）
