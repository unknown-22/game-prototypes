# Game Idea Factory output (2026-05-12T09:01:05)

## 1. Score 31.65 — ダイス/バッグ構築ローグライト / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのダイス/バッグ構築ローグライト。効果が『合成』されて1枚に圧縮される×コストはHPではなく『未来の手札』を消費で、manaとcooldownの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / コストはHPではなく『未来の手札』を消費
- リソース: mana, cooldown
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

## 2. Score 31.4 — ヴァンサバ亜種（抽象敵・UI主導） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのヴァンサバ亜種（抽象敵・UI主導）。同じカードを連続で使うと効果が変質（強化/暴発）×UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）で、slotsとmanaの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）
- リソース: slots, mana
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist, Synergies
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.0, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 3. Score 31.15 — デッキ構築ローグライト（マップノード） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのデッキ構築ローグライト（マップノード）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、comboとslotsの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: combo, slots
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

## 4. Score 31.15 — デッキ構築ローグライト（マップノード） / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのデッキ構築ローグライト（マップノード）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×敵HPが“塊”として表示され、削るとバラけて全体が崩れるで、slotsとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 敵HPが“塊”として表示され、削るとバラけて全体が崩れる
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

## 5. Score 30.95 — ヴァンサバ亜種（抽象敵・UI主導） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのヴァンサバ亜種（抽象敵・UI主導）。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×盤面が回路/パイプで可視化される（流れて増幅する）で、slotsとmanaの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: slots, mana
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist
- 売りの10秒: 回路/パイプに数値が流れて増幅し、連鎖で一気に盤面が崩れる10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.7, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 6. Score 30.75 — ヴァンサバ亜種（抽象敵・UI主導） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのヴァンサバ亜種（抽象敵・UI主導）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×同時に管理できる対象が3つまで（超ミニマルUI）で、riskとcomboの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 同時に管理できる対象が3つまで（超ミニマルUI）
- リソース: risk, combo
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 7. Score 30.75 — ヴァンサバ亜種（抽象敵・UI主導） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのヴァンサバ亜種（抽象敵・UI主導）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×カードは『置く』だけで、後は自動で連鎖解決される（ルールエンジン型）で、heatとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / カードは『置く』だけで、後は自動で連鎖解決される（ルールエンジン型）
- リソース: heat, mana
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 8. Score 30.65 — ダイス/バッグ構築ローグライト / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのダイス/バッグ構築ローグライト。ログ/リプレイが資産（前回の行動が次回のカードになる）×手札の上限が極端に小さい（3枚固定など）で、cooldownとmanaの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 手札の上限が極端に小さい（3枚固定など）
- リソース: cooldown, mana
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Meta Progression
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 9. Score 30.6 — ダイス/バッグ構築ローグライト / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのダイス/バッグ構築ローグライト。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、comboとriskの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: combo, risk
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

## 10. Score 30.6 — ヴァンサバ亜種（抽象敵・UI主導） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのヴァンサバ亜種（抽象敵・UI主導）。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、comboとriskの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: combo, risk
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist
- 売りの10秒: 数値が分裂して多経路に流れ、合流点で巨大ダメージに変換される10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.0, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss
