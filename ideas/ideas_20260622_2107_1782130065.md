# Game Idea Factory output (2026-06-22T21:07:45)

## 1. Score 32.0 — デッキ構築ローグライト（マップノード） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、manaとslotsの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: mana, slots
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Synergies
- 売りの10秒: 数値が分裂して多経路に流れ、合流点で巨大ダメージに変換される10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 2. Score 31.6 — ダイス/バッグ構築ローグライト / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのダイス/バッグ構築ローグライト。効果が『合成』されて1枚に圧縮される×落下/重力で『連鎖崩壊』が起きる（パズル的な崩れ方）で、riskとslotsの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 落下/重力で『連鎖崩壊』が起きる（パズル的な崩れ方）
- リソース: risk, slots
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Puzzle, Synergies
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 3. Score 31.55 — ヴァンサバ亜種（抽象敵・UI主導） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのヴァンサバ亜種（抽象敵・UI主導）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×コストはHPではなく『未来の手札』を消費で、comboとheatの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / コストはHPではなく『未来の手札』を消費
- リソース: combo, heat
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 4. Score 31.25 — デッキ構築ローグライト（マップノード） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×敵HPが“塊”として表示され、削るとバラけて全体が崩れるで、comboとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 敵HPが“塊”として表示され、削るとバラけて全体が崩れる
- リソース: combo, mana
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

## 5. Score 31.1 — ダイス/バッグ構築ローグライト / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのダイス/バッグ構築ローグライト。部分観測（敵の意図が確率でしか見えない）×UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）で、heatとmanaの管理が勝敗を決める。
- フック: 部分観測（敵の意図が確率でしか見えない） / UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）
- リソース: heat, mana
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Tactical, Synergies
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- 注意: チュートリアルが難しくなりがち
- スコア内訳: pitch=3.8, video=4.0, feasibility=3.6, competition=3.0, replay=3.3, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 6. Score 31.0 — デッキ構築ローグライト（マップノード） / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのデッキ構築ローグライト（マップノード）。同じカードを連続で使うと効果が変質（強化/暴発）×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、comboとheatの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: combo, heat
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 数値が分裂して多経路に流れ、合流点で巨大ダメージに変換される10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.0, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 7. Score 30.85 — ダイス/バッグ構築ローグライト / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのダイス/バッグ構築ローグライト。効果が『合成』されて1枚に圧縮される×ダメージを与えると敵が強化される（逆転条件）で、heatとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / ダメージを与えると敵が強化される（逆転条件）
- リソース: heat, mana
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

## 8. Score 30.75 — ヴァンサバ亜種（抽象敵・UI主導） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのヴァンサバ亜種（抽象敵・UI主導）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、manaとslotsの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: mana, slots
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

## 9. Score 30.65 — ダイス/バッグ構築ローグライト / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのダイス/バッグ構築ローグライト。同じカードを連続で使うと効果が変質（強化/暴発）×1ターンに使えるカードは『1色だけ』で、comboとheatの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / 1ターンに使えるカードは『1色だけ』
- リソース: combo, heat
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 10. Score 30.65 — ヴァンサバ亜種（抽象敵・UI主導） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのヴァンサバ亜種（抽象敵・UI主導）。部分観測（敵の意図が確率でしか見えない）×盤面が回路/パイプで可視化される（流れて増幅する）で、slotsとmanaの管理が勝敗を決める。
- フック: 部分観測（敵の意図が確率でしか見えない） / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: slots, mana
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist, Tactical
- 売りの10秒: 回路/パイプに数値が流れて増幅し、連鎖で一気に盤面が崩れる10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- 注意: チュートリアルが難しくなりがち
- スコア内訳: pitch=3.8, video=3.7, feasibility=3.6, competition=3.0, replay=3.3, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss
