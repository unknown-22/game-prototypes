# Game Prototypes 🎮

ゲームアイデアの生成とプロトタイプ作成を行うモノレポ。

## 構成

```
game-prototypes/
├── pyproject.toml          # uv プロジェクトルート
├── ideas/                  # Game Idea Factory の生成結果
│   ├── 2026-05-08_first5.md
│   └── 2026-05-08_game_ideas.md
└── prototypes/
    ├── 001_alchemy_deckbuilder/ # 錬金術デッキ構築 (31.85)
    │   └── main.py
    └── 002_logistics_flow/      # 物流流量最適化 (32.75)
        └── main.py
```

## 使い方

```bash
# 依存関係インストール
uv sync

# プロトタイプ実行
uv run python prototypes/001_alchemy_deckbuilder/main.py

# または
uv run python prototypes/002_logistics_flow/main.py
```

> **WSL2 で実行する場合**: Pyxel は GUI が必要です。
> Windows 側で VcXsrv (XLaunch) などを起動し、`export DISPLAY=:0` を設定してください。

## プロトタイプ一覧

| プロトタイプ | 元アイデア | スコア | 状態 |
|---|---|---|---|
| 001_alchemy_deckbuilder | 錬金術デッキ構築ローグライト | 31.85 | ✅ バトルプロト完了 |
| 002_logistics_flow | 配送/物流（流量最適化）デッキ構築 | 32.75 | ✅ バトルプロト完了 |

## 関連リポジトリ

- [game_idea_factory](https://github.com/unknown-22/game_idea_factory) — ゲームアイデア生成ツール
