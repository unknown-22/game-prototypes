# Game Idea Factory output (2026-07-01T09:05:02)

## 1. Score 31.25 — デッキ構築ローグライト（マップノード） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×1アクションが盤面に『痕跡』を残し、次の解決がどんどん派手になるで、cooldownとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 1アクションが盤面に『痕跡』を残し、次の解決がどんどん派手になる
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

## 2. Score 31.15 — デッキ構築ローグライト（マップノード） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのデッキ構築ローグライト（マップノード）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×手札の上限が極端に小さい（3枚固定など）で、slotsとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 手札の上限が極端に小さい（3枚固定など）
- リソース: slots, mana
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

## 3. Score 31.15 — デッキ構築ローグライト（マップノード） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのデッキ構築ローグライト（マップノード）。スタック（積み上げ）した効果が一定量で『崩壊』し、全体に波及する×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、comboとriskの管理が勝敗を決める。
- フック: スタック（積み上げ）した効果が一定量で『崩壊』し、全体に波及する / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: combo, risk
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

## 4. Score 31.05 — ヴァンサバ亜種（抽象敵・UI主導） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのヴァンサバ亜種（抽象敵・UI主導）。部分観測（敵の意図が確率でしか見えない）×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、cooldownとmanaの管理が勝敗を決める。
- フック: 部分観測（敵の意図が確率でしか見えない） / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: cooldown, mana
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist, Tactical
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- 注意: チュートリアルが難しくなりがち
- スコア内訳: pitch=3.4, video=4.5, feasibility=3.6, competition=3.0, replay=3.3, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 5. Score 31.05 — デッキ構築ローグライト（マップノード） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのデッキ構築ローグライト（マップノード）。ログ/リプレイが資産（前回の行動が次回のカードになる）×手札の上限が極端に小さい（3枚固定など）で、comboとheatの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 手札の上限が極端に小さい（3枚固定など）
- リソース: combo, heat
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Meta Progression
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 6. Score 30.85 — ダイス/バッグ構築ローグライト / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのダイス/バッグ構築ローグライト。効果が『合成』されて1枚に圧縮される×敵HPが“塊”として表示され、削るとバラけて全体が崩れるで、slotsとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 敵HPが“塊”として表示され、削るとバラけて全体が崩れる
- リソース: slots, mana
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Synergies
- 売りの10秒: 合成で1枚に圧縮された超カードが成立して、数字が爆発する10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=3.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 7. Score 30.75 — デッキ構築ローグライト（マップノード） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのデッキ構築ローグライト（マップノード）。オーバーキルが資産になる（余剰ダメージが次の攻撃に繰り越される）×盤面が回路/パイプで可視化される（流れて増幅する）で、heatとmanaの管理が勝敗を決める。
- フック: オーバーキルが資産になる（余剰ダメージが次の攻撃に繰り越される） / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: heat, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 回路/パイプに数値が流れて増幅し、連鎖で一気に盤面が崩れる10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.7, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 8. Score 30.75 — ダイス/バッグ構築ローグライト / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのダイス/バッグ構築ローグライト。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×手札の上限が極端に小さい（3枚固定など）で、comboとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 手札の上限が極端に小さい（3枚固定など）
- リソース: combo, mana
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

## 9. Score 30.6 — ダイス/バッグ構築ローグライト / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのダイス/バッグ構築ローグライト。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、manaとheatの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: mana, heat
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based
- 売りの10秒: 数値が分裂して多経路に流れ、合流点で巨大ダメージに変換される10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.0, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 10. Score 30.4 — デッキ構築ローグライト（マップノード） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのデッキ構築ローグライト（マップノード）。スタック（積み上げ）した効果が一定量で『崩壊』し、全体に波及する×1アクションが盤面に『痕跡』を残し、次の解決がどんどん派手になるで、cooldownとmanaの管理が勝敗を決める。
- フック: スタック（積み上げ）した効果が一定量で『崩壊』し、全体に波及する / 1アクションが盤面に『痕跡』を残し、次の解決がどんどん派手になる
- リソース: cooldown, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat
