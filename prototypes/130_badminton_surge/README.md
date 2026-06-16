# 130 Badminton Surge (バドミントンサージ)

サイドビューバドミントンラリー × 色合わせCOMBOチェイン。

## 体験仮説

「シャトルの色を見極めてCOMBOを溜め、SUPER SMASHで相手を圧倒する瞬間が何度も味わえる」

## コアループ

1. AIが色付きシャトルをサーブ
2. プレイヤーがマウスでラケットを上下に動かし、クリックで打ち返す
3. ラケット色＝シャトル色 → COMBO継続 (+1)
4. ラケット色≠シャトル色 → HEAT蓄積 + COMBOリセット
5. COMBO ≥ 4 → SUPER SMASH発動（5秒間全色一致、スコア3倍）
6. 90秒でスコア最大化を目指す

## 操作

- **マウス上下**: ラケット移動
- **左クリック**: シャトルを打つ
- **マウスホイール**: ラケット色の手動切替
- ラケット色はヒット成功時に自動でも切り替わる

## 特徴

- シャトルコック物理（重力＋空気抵抗＝減速）によるバドミントン特有の軌道
- 前ラリーのゴースト軌跡を通過するとボーナススコア
- HEATが100でゲームオーバー
- SUPER SMASH時の画面揺れ＋大量パーティクル

## 技術情報

- Pyxel 2.x, 320×240
- 699行 main.py
- 56 headless tests
- OpenCode CLI (opencode-go/deepseek-v4-pro) による完全自律生成

## 実行

```bash
cd ~/repos/game-prototypes
uv run python prototypes/130_badminton_surge/main.py
```

## 元アイデア

game_idea_factory #1 (Score 32.15) — 発電所（過負荷と放電）
- 回路/パイプ可視化 → COMBO連鎖のバドミントンラリー
- 過負荷/放電 → HEAT蓄積/SUPER SMASH放電
- ログ/リプレイが資産 → ゴースト軌跡ボーナス

## 開発ステータス

- ✅ 完全なゲームループ（タイトル→プレイ→ゲームオーバー）
- ✅ COMBO連鎖 + SUPER SMASH
- ✅ HEATリスクシステム
- ✅ ゴースト軌跡ボーナス
- ✅ 56 headless tests (全通過)
- ✅ ruff + ty チェック通過
- ✅ Webビルド完了
