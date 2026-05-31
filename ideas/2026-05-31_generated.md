# Game Idea Factory output (2026-05-31T15:02:09)

## 1. Score 32.75 — デッキ構築ローグライト（マップノード） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、comboとheatの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: combo, heat
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

## 2. Score 32.0 — デッキ構築ローグライト（マップノード） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、cooldownとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: cooldown, mana
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

## 3. Score 31.35 — ダイス/バッグ構築ローグライト / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのダイス/バッグ構築ローグライト。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×戦闘は数字とアイコン中心（敵は抽象化）で、manaとslotsの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 戦闘は数字とアイコン中心（敵は抽象化）
- リソース: mana, slots
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.5, feasibility=4.2, competition=3.2, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 4. Score 31.25 — デッキ構築ローグライト（マップノード） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×同時に管理できる対象が3つまで（超ミニマルUI）で、riskとcomboの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 同時に管理できる対象が3つまで（超ミニマルUI）
- リソース: risk, combo
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

## 5. Score 30.95 — ヴァンサバ亜種（抽象敵・UI主導） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのヴァンサバ亜種（抽象敵・UI主導）。同じカードを連続で使うと効果が変質（強化/暴発）×盤面が回路/パイプで可視化される（流れて増幅する）で、slotsとmanaの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / 盤面が回路/パイプで可視化される（流れて増幅する）
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

## 6. Score 30.85 — ヴァンサバ亜種（抽象敵・UI主導） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×敵HPが“塊”として表示され、削るとバラけて全体が崩れるで、slotsとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 敵HPが“塊”として表示され、削るとバラけて全体が崩れる
- リソース: slots, mana
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

## 7. Score 30.6 — ダイス/バッグ構築ローグライト / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのダイス/バッグ構築ローグライト。同じカードを連続で使うと効果が変質（強化/暴発）×ヒット数/チェイン数が画面全体で可視化され、加速していくで、riskとcooldownの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / ヒット数/チェイン数が画面全体で可視化され、加速していく
- リソース: risk, cooldown
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based
- 売りの10秒: コンボ/チェインが加速して、画面全体の数字が踊り続ける10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.0, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 8. Score 30.6 — ヴァンサバ亜種（抽象敵・UI主導） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのヴァンサバ亜種（抽象敵・UI主導）。同じカードを連続で使うと効果が変質（強化/暴発）×ヒット数/チェイン数が画面全体で可視化され、加速していくで、heatとmanaの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / ヒット数/チェイン数が画面全体で可視化され、加速していく
- リソース: heat, mana
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist
- 売りの10秒: コンボ/チェインが加速して、画面全体の数字が踊り続ける10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.0, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 9. Score 30.6 — ダイス/バッグ構築ローグライト / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのダイス/バッグ構築ローグライト。敵を倒すほど『コンボメーター』が伸び、報酬が加速度的に増える×戦闘は数字とアイコン中心（敵は抽象化）で、heatとmanaの管理が勝敗を決める。
- フック: 敵を倒すほど『コンボメーター』が伸び、報酬が加速度的に増える / 戦闘は数字とアイコン中心（敵は抽象化）
- リソース: heat, mana
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based
- 売りの10秒: コンボ/チェインが加速して、画面全体の数字が踊り続ける10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.0, feasibility=4.2, competition=3.2, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 10. Score 30.55 — デッキ構築ローグライト（マップノード） / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのデッキ構築ローグライト（マップノード）。部分観測（敵の意図が確率でしか見えない）×戦闘は数字とアイコン中心（敵は抽象化）で、slotsとmanaの管理が勝敗を決める。
- フック: 部分観測（敵の意図が確率でしか見えない） / 戦闘は数字とアイコン中心（敵は抽象化）
- リソース: slots, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Tactical
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- 注意: チュートリアルが難しくなりがち
- スコア内訳: pitch=3.4, video=3.5, feasibility=3.8, competition=3.2, replay=3.3, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat
