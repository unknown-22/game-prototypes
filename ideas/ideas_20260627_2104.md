# Game Idea Factory output (2026-06-27T21:04:17)

## 1. Score 32.05 — デッキ構築ローグライト（マップノード） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×コストはHPではなく『未来の手札』を消費で、riskとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / コストはHPではなく『未来の手札』を消費
- リソース: risk, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Synergies
- 売りの10秒: 合成で1枚に圧縮された超カードが成立して、数字が爆発する10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=4.2, video=3.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 2. Score 31.75 — ヴァンサバ亜種（抽象敵・UI主導） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのヴァンサバ亜種（抽象敵・UI主導）。ログ/リプレイが資産（前回の行動が次回のカードになる）×盤面が回路/パイプで可視化される（流れて増幅する）で、heatとriskの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: heat, risk
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist, Meta Progression
- 売りの10秒: 回路/パイプに数値が流れて増幅し、連鎖で一気に盤面が崩れる10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=3.7, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 3. Score 31.5 — デッキ構築ローグライト（マップノード） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのデッキ構築ローグライト（マップノード）。部分観測（敵の意図が確率でしか見えない）×UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）で、riskとmanaの管理が勝敗を決める。
- フック: 部分観測（敵の意図が確率でしか見えない） / UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）
- リソース: risk, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Tactical, Synergies
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- 注意: チュートリアルが難しくなりがち
- スコア内訳: pitch=3.8, video=4.0, feasibility=3.6, competition=3.0, replay=3.3, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 4. Score 31.35 — ヴァンサバ亜種（抽象敵・UI主導） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのヴァンサバ亜種（抽象敵・UI主導）。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、slotsとmanaの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: slots, mana
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 5. Score 31.35 — ダイス/バッグ構築ローグライト / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのダイス/バッグ構築ローグライト。同じカードを連続で使うと効果が変質（強化/暴発）×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、cooldownとmanaの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: cooldown, mana
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 6. Score 31.25 — デッキ構築ローグライト（マップノード） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×同時に管理できる対象が3つまで（超ミニマルUI）で、manaとcooldownの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 同時に管理できる対象が3つまで（超ミニマルUI）
- リソース: mana, cooldown
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

## 7. Score 30.65 — ヴァンサバ亜種（抽象敵・UI主導） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのヴァンサバ亜種（抽象敵・UI主導）。同じカードを連続で使うと効果が変質（強化/暴発）×コストはHPではなく『未来の手札』を消費で、slotsとmanaの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / コストはHPではなく『未来の手札』を消費
- リソース: slots, mana
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist
- 売りの10秒: 画面がアイコンの物量で埋まり、範囲効果で一掃する10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 8. Score 30.65 — ダイス/バッグ構築ローグライト / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのダイス/バッグ構築ローグライト。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×1ターンに使えるカードは『1色だけ』で、heatとriskの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / 1ターンに使えるカードは『1色だけ』
- リソース: heat, risk
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

## 9. Score 30.25 — デッキ構築ローグライト（マップノード） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのデッキ構築ローグライト（マップノード）。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×ダメージを与えると敵が強化される（逆転条件）で、comboとheatの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / ダメージを与えると敵が強化される（逆転条件）
- リソース: combo, heat
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=3.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 10. Score 30.0 — ダイス/バッグ構築ローグライト / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのダイス/バッグ構築ローグライト。オーバーキルが資産になる（余剰ダメージが次の攻撃に繰り越される）×落下/重力で『連鎖崩壊』が起きる（パズル的な崩れ方）で、comboとcooldownの管理が勝敗を決める。
- フック: オーバーキルが資産になる（余剰ダメージが次の攻撃に繰り越される） / 落下/重力で『連鎖崩壊』が起きる（パズル的な崩れ方）
- リソース: combo, cooldown
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Puzzle
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat
