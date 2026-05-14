# Game Idea Factory output (2026-05-15T03:00:39)

## 1. Score 31.65 — ダイス/バッグ構築ローグライト / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのダイス/バッグ構築ローグライト。効果が『合成』されて1枚に圧縮される×1ターンに使えるカードは『1色だけ』で、heatとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 1ターンに使えるカードは『1色だけ』
- リソース: heat, mana
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Synergies
- 売りの10秒: 合成で1枚に圧縮された超カードが成立して、数字が爆発する10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=4.2, video=3.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 2. Score 31.55 — ダイス/バッグ構築ローグライト / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのダイス/バッグ構築ローグライト。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×コストはHPではなく『未来の手札』を消費で、comboとriskの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / コストはHPではなく『未来の手札』を消費
- リソース: combo, risk
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 3. Score 31.45 — ダイス/バッグ構築ローグライト / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのダイス/バッグ構築ローグライト。ログ/リプレイが資産（前回の行動が次回のカードになる）×コストはHPではなく『未来の手札』を消費で、comboとslotsの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / コストはHPではなく『未来の手札』を消費
- リソース: combo, slots
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Meta Progression
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=3.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 4. Score 31.35 — デッキ構築ローグライト（マップノード） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのデッキ構築ローグライト（マップノード）。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×盤面が回路/パイプで可視化される（流れて増幅する）で、riskとcomboの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: risk, combo
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 回路/パイプに数値が流れて増幅し、連鎖で一気に盤面が崩れる10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.7, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 5. Score 31.25 — デッキ構築ローグライト（マップノード） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×手札の上限が極端に小さい（3枚固定など）で、cooldownとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 手札の上限が極端に小さい（3枚固定など）
- リソース: cooldown, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Synergies
- 売りの10秒: 合成で1枚に圧縮された超カードが成立して、数字が爆発する10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=3.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 6. Score 31.2 — デッキ構築ローグライト（マップノード） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのデッキ構築ローグライト（マップノード）。スタック（積み上げ）した効果が一定量で『崩壊』し、全体に波及する×1ターンに使えるカードは『1色だけ』で、cooldownとmanaの管理が勝敗を決める。
- フック: スタック（積み上げ）した効果が一定量で『崩壊』し、全体に波及する / 1ターンに使えるカードは『1色だけ』
- リソース: cooldown, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 7. Score 31.15 — デッキ構築ローグライト（マップノード） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのデッキ構築ローグライト（マップノード）。敵を倒すほど『コンボメーター』が伸び、報酬が加速度的に増える×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、cooldownとmanaの管理が勝敗を決める。
- フック: 敵を倒すほど『コンボメーター』が伸び、報酬が加速度的に増える / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: cooldown, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 8. Score 30.8 — ダイス/バッグ構築ローグライト / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのダイス/バッグ構築ローグライト。リソースが閾値を超えると『暴走モード』に入り、制御しながら稼ぐ×UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）で、manaとheatの管理が勝敗を決める。
- フック: リソースが閾値を超えると『暴走モード』に入り、制御しながら稼ぐ / UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）
- リソース: mana, heat
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Synergies
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 9. Score 30.75 — ダイス/バッグ構築ローグライト / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのダイス/バッグ構築ローグライト。オーバーキルが資産になる（余剰ダメージが次の攻撃に繰り越される）×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、manaとslotsの管理が勝敗を決める。
- フック: オーバーキルが資産になる（余剰ダメージが次の攻撃に繰り越される） / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: mana, slots
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 10. Score 30.75 — デッキ構築ローグライト（マップノード） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのデッキ構築ローグライト（マップノード）。部分観測（敵の意図が確率でしか見えない）×1ターンに使えるカードは『1色だけ』で、heatとriskの管理が勝敗を決める。
- フック: 部分観測（敵の意図が確率でしか見えない） / 1ターンに使えるカードは『1色だけ』
- リソース: heat, risk
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Tactical
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- 注意: チュートリアルが難しくなりがち
- スコア内訳: pitch=3.8, video=3.5, feasibility=3.6, competition=3.0, replay=3.3, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat
