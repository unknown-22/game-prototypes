# TICK SURGE — Hot Potato Bomb Pass

**体験仮説**: 爆弾の色と相手の色がピタリと合い、コンボが一気に連鎖してSUPER PASSで画面が虹色に輝く瞬間に「気持ちいい！」と感じさせる。

## 概要

ホットポテト（爆弾回し）をテーマにした色合わせタイミングゲーム。6人のキャラクターが円状に並び、4色の爆弾を回していく。爆弾の色と受け取るキャラクターの色が一致するとCOMBOが伸び、COMBO≥4でSUPER PASS（虹色爆弾、5秒間スコア3倍）が発動する。

## 元ネタ

- game_idea_factory #1 (Score 32.55): ハッキング/デッキ構築ローグライト
- 「ログ/リプレイが資産」→ エコーゴースト（パス通過点に残る軌跡）
- 「CAグリッド感染/増殖」→ 爆弾の圧力上昇（HEAT自然増加）

## 操作方法

- **LEFT/RIGHT**: パス先のキャラクターを選択（爆弾保持者はスキップ）
- **SPACE**: 爆弾をパス
- **RETURN/SPACE**: タイトル画面→ゲーム開始 / ゲームオーバー→再挑戦

## ゲームルール

- 爆弾の色と受け取るキャラクターの色が一致 → COMBO+1、スコア加算
- 色違い → COMBOリセット、HEAT+15
- COMBO≥4 で SUPER PASS 発動（虹色爆弾、5秒間スコア3倍、全色自動マッチ）
- HEATは時間経過で自然増加（0.1/frame）、減衰（0.05/frame）
- エコーゴースト（通過点の軌跡）付近を通過すると追加HEAT+2
- HEAT≥100 または 60秒経過でゲームオーバー

## 技術情報

- Pyxel 2.x, 320×240
- 70 headless tests
- OpenCode (opencode-go/deepseek-v4-pro) でコード生成（ファーストトライ成功）

## 実行方法

```bash
cd ~/repos/game-prototypes
uv run python prototypes/212_tick_surge/main.py
```

## Dev Status

- ✅ コアメカニクス（色合わせCOMBOチェイン）
- ✅ SUPER PASS 発動
- ✅ HEATシステム（自然増加・減衰・間違いペナルティ・ゴースト）
- ✅ エコーゴースト（軌跡）システム
- ✅ パーティクル・フローティングテキスト・画面揺れ
- ✅ 3画面（タイトル/プレイ/ゲームオーバー）
- ✅ 70 headless tests
- ✅ ruff + ty クリーン
- ✅ Webビルド
