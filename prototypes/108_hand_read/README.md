# 108_hand_read — Hand Read (じゃんけん予測バトル)

## Source
Reinterpretation of Idea #1 (score 31.85) — ハッキングテーマのデッキ構築ローグライト
- Hook: "ログ/リプレイが資産（前回の行動が次回のカードになる）" → AIがプレイヤーの履歴から次の手を予測
- Hook: "コストはHPではなく『未来の手札』を消費" → 3手先までプリコミット

## Genre
Rock-Paper-Scissors / Prediction (初の予測ジャンル)

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- OpenCode CLI (opencode-go/deepseek-v4-pro) による自動生成

## Gameplay
- プレイヤーは3手先までキューに予約（ロック/ペーパー/シザース）
- 毎ターン先頭の手が自動プレイ。AIが履歴から頻度分析で次の手を予測
- AIの予測を外すとCOMBO。同じ手で連勝するとCOMBO加速
- COMBO≥4でSUPER MODE（5ターン、全手に勝つ3倍ダメージ）
- エネルギー（最大3）を使ってキューの手を入れ替え可能

## Controls
- マウスクリック: キュー内の手を入れ替え（エネルギー1消費）
- マウスクリック: END TURN ボタンでバトルに進む
- SPACE: タイトル開始 / リスタート

## Hand Types
| 手 | 色 | 勝つ | 負ける |
|----|----|------|--------|
| ROCK | RED(8) | SCISSORS | PAPER |
| PAPER | LIME(11) | ROCK | SCISSORS |
| SCISSORS | CYAN(12) | PAPER | ROCK |

## Dev Status
- ✅ コアメカニクス: 3手キュー、AI予測、COMBO、SUPER MODE
- ✅ 3画面: TITLE, GAME (QUEUE/BATTLE/RESULT), GAME_OVER
- ✅ パーティクルエフェクト、画面シェイク
- ✅ 33 headless tests 通過
- ✅ ruff / ty チェック通過
- ✅ Webビルド (docs/108_hand_read.html)

## 体験仮説
「AIが自分の手を読んでいるのを感じながら、あえてパターンを崩してCOMBOを積み、SUPER MODEで一気に逆転する知的駆け引きが面白い」

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/108_hand_read/main.py
```
