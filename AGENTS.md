# instructions

**日本語で返答してください**

ゲームアイデアの生成とプロトタイプ作成を行うモノレポ。
prototypes/ 以下に 001_<プロトタイプ名>/main.py という構成でプロトタイプを配置してください。

## 主要技術スタック・コーディング規約

- 言語: Python 3.12
- フレームワーク: pyxel

**プロジェクトルール**

- python 3.12のモダンな機能を活用する
- 型ヒントを積極的に使用する
- ruff(lint)とty(type checker)を活用してコード品質を保つ
- 適切な単位でモジュール化・クラス化を行う
- ロジック部分はクラス化・関数化してテスト可能にする
- linterや型チェックで関数・引数ミスが出たら inspect モジュールで関数シグネチャを確認するワンライナーを都度作成し、調査と修正を繰り返す
- 作成後に docs/prototypes.json を更新する

## 開発環境とコマンド

### 基本コマンド

uvを利用します

```bash
# 実行
uv run python main.py

# pytest実行
uv run pytest tests/
uv run pytest tests/test_module.py

# Ruff実行
uv run ruff check
uv run ruff check <file_name> --fix

# 型チェック(ty)
uv run ty check
uv run ty check <file_name>

# app/webビルド、docs/への配置
uv run pyxel package prototypes/001_alchemy_deckbuilder prototypes/001_alchemy_deckbuilder/main.py
uv run pyxel app2html 001_alchemy_deckbuilder.pyxapp
mv 001_alchemy_deckbuilder.html docs/
```

### Pyxel Tips

Pyxel利用時に気をつけるべきことを完結に記載する

- フォントの制約のため、描画するテキストは半角英数字と一部の記号に限定される
- 日本語や絵文字は描画できないため、ゲーム内のテキストは英語で統一する

