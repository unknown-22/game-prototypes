# CLOCK CHAIN — Clock Repair / Watchmaker Prototype (300)

色合わせCOMBO連鎖 × 「未来の手札をコストに」する時計修理ゲーム。

## 一番面白い瞬間（1文）

歯車の色が合わずCOMBOが途切れそうな瞬間、未来の手札（時間と次の歯車）を消費して巻き戻すか、素直にミスを受け入れるか迷う駆け引き。

## Source

- 生成元: game_idea_factory ダイス/バッグ構築ローグライト案 #1（Score 31.65）
  - フック: 「効果が合成されて1枚に圧縮される」「コストはHPではなく未来の手札を消費」
- 再解釈:
  - 合成圧縮 → 同色連続修理のCOMBO連鎖 → SUPER REPAIR（虹色・スコア3倍）
  - 未来の手札をコスト → REWIND（時間2秒＋歯車1個を消費してミスを回避）
- ジャンル: 時計修理／時計職人（コレクション初）

## Engine

- Pyxel 2.x, 320x240, 60fps, display_scale=2

## Gameplay

- 歯車のキュー（先頭=修理対象、次の3個=未来の手札プレビュー）が画面下部に並ぶ
- プレイヤーの工具色は自動で巡回（20f→12fに加速）
- SPACE/クリックで先頭歯車を修理:
  - 工具色と一致 → COMBO+1、`score += 10*combo*倍率`（虹色モード中は3倍）
  - 不一致 → HEAT+15、COMBOリセット
- COMBO>=4 → SUPER REPAIR（300f、全色マッチ、スコア3倍、HEAT凍結）
- R（REWIND）: 未来の手札を消費。時間2秒と歯車1個を失う代わりに、COMBOを維持したままミスを回避
- 失敗条件: HEAT>=100（オーバーヒート）または60秒タイムアップ

## Controls

| キー | 動作 |
|---|---|
| SPACE / クリック | 修理（REPAIR） |
| R | 巻き戻し（REWIND、-2秒） |
| ENTER | 開始 / リスタート |
| ESC | 終了 |

## 体験仮説（MDA）

- Mechanics: 工具色の自動巡回 + 先頭歯車の色合わせ + REWIND（時間/歯車を消費）
- Dynamics: COMBOを守るために未来の手札を切るか、安全にミスを受け入れるかの駆け引き
- Aesthetics: 「ギリギリでCOMBOを繋いだ」という読みと判断の快感

## 実装したコアループ

見る（先頭歯車色 vs 工具色、未来プレビュー）→ 判断（REPAIR or REWIND）→ 操作 → 結果（+score/COMBO か +HEAT）→ 次の判断

## うまくいっている点

- REWIND が「未来の手札をコスト」を直訳した明確なリスク/リターン選択になっている
- 未来プレビュー（次の3個）で先読みの腕前が出る
- ロジックがPyxel入力から完全分離されており、ヘッドレステスト47件が全て通る

## 次に改善するなら最初に触る点

- REWINDのプレイヤー選択肢を増やす（巻き戻す歯車を明示選択できる等）
- 歯車のティア合成（同色3個→上位歯車）を足して合成圧縮をより直接的に表現

## How to run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/300_clock_chain/main.py
```

## Dev status

- ✅ タイトル / ゲーム / ゲームオーバー画面
- ✅ 色合わせCOMBO連鎖 + SUPER REPAIR
- ✅ REWIND（未来の手札をコスト）
- ✅ HEATリスク + 60秒タイマー
- ✅ パーティクル / フローティングテキスト / 画面シェイク
- ✅ ヘッドレステスト47件（ruff / ty パス）
- ✅ Webビルド（docs/300_clock_chain.html）
