# Game Idea Factory output (2026-06-23T15:01:07)

## 1. Score 32.75 — デッキ構築ローグライト（マップノード） / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、heatとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: heat, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Synergies
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=4.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 2. Score 31.65 — ダイス/バッグ構築ローグライト / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのダイス/バッグ構築ローグライト。効果が『合成』されて1枚に圧縮される×コストはHPではなく『未来の手札』を消費で、cooldownとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / コストはHPではなく『未来の手札』を消費
- リソース: cooldown, mana
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

## 3. Score 31.6 — ダイス/バッグ構築ローグライト / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのダイス/バッグ構築ローグライト。効果が『合成』されて1枚に圧縮される×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、cooldownとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: cooldown, mana
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Synergies
- 売りの10秒: 数値が分裂して多経路に流れ、合流点で巨大ダメージに変換される10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 4. Score 31.4 — ヴァンサバ亜種（抽象敵・UI主導） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのヴァンサバ亜種（抽象敵・UI主導）。同じカードを連続で使うと効果が変質（強化/暴発）×UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）で、heatとriskの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）
- リソース: heat, risk
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

## 5. Score 31.25 — ダイス/バッグ構築ローグライト / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのダイス/バッグ構築ローグライト。ログ/リプレイが資産（前回の行動が次回のカードになる）×戦闘は数字とアイコン中心（敵は抽象化）で、comboとslotsの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 戦闘は数字とアイコン中心（敵は抽象化）
- リソース: combo, slots
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Meta Progression
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.5, feasibility=4.2, competition=3.2, replay=3.6, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 6. Score 31.2 — デッキ構築ローグライト（マップノード） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのデッキ構築ローグライト（マップノード）。リソースが閾値を超えると『暴走モード』に入り、制御しながら稼ぐ×UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）で、cooldownとmanaの管理が勝敗を決める。
- フック: リソースが閾値を超えると『暴走モード』に入り、制御しながら稼ぐ / UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）
- リソース: cooldown, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Synergies
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 7. Score 31.15 — デッキ構築ローグライト（マップノード） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのデッキ構築ローグライト（マップノード）。スタック（積み上げ）した効果が一定量で『崩壊』し、全体に波及する×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、comboとcooldownの管理が勝敗を決める。
- フック: スタック（積み上げ）した効果が一定量で『崩壊』し、全体に波及する / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: combo, cooldown
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

## 8. Score 31.05 — デッキ構築ローグライト（マップノード） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのデッキ構築ローグライト（マップノード）。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×コストはHPではなく『未来の手札』を消費で、manaとcooldownの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / コストはHPではなく『未来の手札』を消費
- リソース: mana, cooldown
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 9. Score 30.85 — ダイス/バッグ構築ローグライト / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのダイス/バッグ構築ローグライト。効果が『合成』されて1枚に圧縮される×敵HPが“塊”として表示され、削るとバラけて全体が崩れるで、manaとslotsの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 敵HPが“塊”として表示され、削るとバラけて全体が崩れる
- リソース: mana, slots
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

## 10. Score 30.85 — ヴァンサバ亜種（抽象敵・UI主導） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×1アクションが盤面に『痕跡』を残し、次の解決がどんどん派手になるで、comboとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 1アクションが盤面に『痕跡』を残し、次の解決がどんどん派手になる
- リソース: combo, mana
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist, Synergies
- 売りの10秒: 合成で1枚に圧縮された超カードが成立して、数字が爆発する10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=3.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss
