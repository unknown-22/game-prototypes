# Game Prototypes 🎮

ゲームアイデアの生成とプロトタイプ作成を行うモノレポ。

[Webプレビュー　Game Prototypes](https://unknown-22.github.io/game-prototypes/)

## 使い方

```bash
# 依存関係インストール
uv sync

# プロトタイプ実行例
uv run python prototypes/001_alchemy_deckbuilder/main.py

# app/webビルド、docs/への配置
uv run pyxel package prototypes/001_alchemy_deckbuilder prototypes/001_alchemy_deckbuilder/main.py
uv run pyxel app2html 001_alchemy_deckbuilder.pyxapp
mv 001_alchemy_deckbuilder.html docs/
# docs/prototypes.json の更新もお忘れなく
```

## プロトタイプ一覧

| プロトタイプ | 元アイデア | スコア | 状態 |
|---|---|---|---|
| 001_alchemy_deckbuilder | 錬金術デッキ構築ローグライト | 31.85 | ✅ バトルプロト完了 |
| 002_logistics_flow | 配送/物流（流量最適化）デッキ構築 | 32.75 | ✅ バトルプロト完了 |

## 関連リポジトリ

- [game_idea_factory](https://github.com/unknown-22/game_idea_factory) — ゲームアイデア生成ツール
