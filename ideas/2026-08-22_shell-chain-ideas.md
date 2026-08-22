# Game Idea Factory output (2026-08-22T03:01:01)

## 1. Score 32.35 — デッキ構築ローグライト（マップノード） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×盤面が回路/パイプで可視化される（流れて増幅する）で、slotsとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: slots, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Synergies
- 売りの10秒: 回路/パイプに数値が流れて増幅し、連鎖で一気に盤面が崩れる10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=4.2, video=3.7, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 2. Score 31.6 — ダイス/バッグ構築ローグライト / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのダイス/バッグ構築ローグライト。効果が『合成』されて1枚に圧縮される×ヒット数/チェイン数が画面全体で可視化され、加速していくで、slotsとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / ヒット数/チェイン数が画面全体で可視化され、加速していく
- リソース: slots, mana
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Synergies
- 売りの10秒: コンボ/チェインが加速して、画面全体の数字が踊り続ける10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 3. Score 31.25 — デッキ構築ローグライト（マップノード） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×同時に管理できる対象が3つまで（超ミニマルUI）で、slotsとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 同時に管理できる対象が3つまで（超ミニマルUI）
- リソース: slots, mana
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

## 4. Score 31.2 — デッキ構築ローグライト（マップノード） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのデッキ構築ローグライト（マップノード）。スタック（積み上げ）した効果が一定量で『崩壊』し、全体に波及する×1ターンに使えるカードは『1色だけ』で、comboとriskの管理が勝敗を決める。
- フック: スタック（積み上げ）した効果が一定量で『崩壊』し、全体に波及する / 1ターンに使えるカードは『1色だけ』
- リソース: combo, risk
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

## 5. Score 31.15 — デッキ構築ローグライト（マップノード） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのデッキ構築ローグライト（マップノード）。リソースが閾値を超えると『暴走モード』に入り、制御しながら稼ぐ×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、cooldownとmanaの管理が勝敗を決める。
- フック: リソースが閾値を超えると『暴走モード』に入り、制御しながら稼ぐ / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
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

## 6. Score 31.1 — ダイス/バッグ構築ローグライト / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのダイス/バッグ構築ローグライト。部分観測（敵の意図が確率でしか見えない）×UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）で、heatとriskの管理が勝敗を決める。
- フック: 部分観測（敵の意図が確率でしか見えない） / UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）
- リソース: heat, risk
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

## 7. Score 31.05 — デッキ構築ローグライト（マップノード） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのデッキ構築ローグライト（マップノード）。同じカードを連続で使うと効果が変質（強化/暴発）×1ターンに使えるカードは『1色だけ』で、comboとslotsの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / 1ターンに使えるカードは『1色だけ』
- リソース: combo, slots
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

## 8. Score 31.0 — デッキ構築ローグライト（マップノード） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのデッキ構築ローグライト（マップノード）。同じカードを連続で使うと効果が変質（強化/暴発）×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、cooldownとmanaの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: cooldown, mana
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

## 9. Score 30.85 — ヴァンサバ亜種（抽象敵・UI主導） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×手札の上限が極端に小さい（3枚固定など）で、manaとslotsの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 手札の上限が極端に小さい（3枚固定など）
- リソース: mana, slots
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

## 10. Score 30.75 — ヴァンサバ亜種（抽象敵・UI主導） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのヴァンサバ亜種（抽象敵・UI主導）。リソースが閾値を超えると『暴走モード』に入り、制御しながら稼ぐ×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、comboとmanaの管理が勝敗を決める。
- フック: リソースが閾値を超えると『暴走モード』に入り、制御しながら稼ぐ / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: combo, mana
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
