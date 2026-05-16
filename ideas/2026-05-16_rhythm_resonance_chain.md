# Game Idea Factory output (2026-05-16T21:01:24)

## 1. Score 32.2 — ダイス/バッグ構築ローグライト / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのダイス/バッグ構築ローグライト。ログ/リプレイが資産（前回の行動が次回のカードになる）×UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）で、slotsとmanaの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）
- リソース: slots, mana
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Meta Progression, Synergies
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=4.0, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 2. Score 31.8 — デッキ構築ローグライト（マップノード） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのデッキ構築ローグライト（マップノード）。ログ/リプレイが資産（前回の行動が次回のカードになる）×ヒット数/チェイン数が画面全体で可視化され、加速していくで、heatとriskの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / ヒット数/チェイン数が画面全体で可視化され、加速していく
- リソース: heat, risk
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Meta Progression
- 売りの10秒: コンボ/チェインが加速して、画面全体の数字が踊り続ける10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.0, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 3. Score 31.8 — デッキ構築ローグライト（マップノード） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのデッキ構築ローグライト（マップノード）。ログ/リプレイが資産（前回の行動が次回のカードになる）×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、manaとcooldownの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: mana, cooldown
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Meta Progression
- 売りの10秒: 数値が分裂して多経路に流れ、合流点で巨大ダメージに変換される10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.0, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 4. Score 31.35 — ダイス/バッグ構築ローグライト / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのダイス/バッグ構築ローグライト。同じカードを連続で使うと効果が変質（強化/暴発）×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、manaとcooldownの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: mana, cooldown
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

## 5. Score 31.25 — デッキ構築ローグライト（マップノード） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×同時に管理できる対象が3つまで（超ミニマルUI）で、heatとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 同時に管理できる対象が3つまで（超ミニマルUI）
- リソース: heat, mana
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

## 6. Score 31.15 — デッキ構築ローグライト（マップノード） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのデッキ構築ローグライト（マップノード）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×1アクションが盤面に『痕跡』を残し、次の解決がどんどん派手になるで、comboとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 1アクションが盤面に『痕跡』を残し、次の解決がどんどん派手になる
- リソース: combo, mana
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

## 7. Score 31.05 — ヴァンサバ亜種（抽象敵・UI主導） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのヴァンサバ亜種（抽象敵・UI主導）。部分観測（敵の意図が確率でしか見えない）×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、heatとriskの管理が勝敗を決める。
- フック: 部分観測（敵の意図が確率でしか見えない） / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: heat, risk
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

## 8. Score 30.75 — ダイス/バッグ構築ローグライト / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのダイス/バッグ構築ローグライト。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×同時に管理できる対象が3つまで（超ミニマルUI）で、comboとriskの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 同時に管理できる対象が3つまで（超ミニマルUI）
- リソース: combo, risk
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

## 9. Score 30.75 — ヴァンサバ亜種（抽象敵・UI主導） / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのヴァンサバ亜種（抽象敵・UI主導）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、heatとriskの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: heat, risk
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

## 10. Score 30.6 — ダイス/バッグ構築ローグライト / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのダイス/バッグ構築ローグライト。同じカードを連続で使うと効果が変質（強化/暴発）×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、riskとcooldownの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: risk, cooldown
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
