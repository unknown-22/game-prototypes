# Game Idea Factory output (2026-06-28T09:00:19)

## 1. Score 32.75 — デッキ構築ローグライト（マップノード） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、manaとslotsの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: mana, slots
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

## 2. Score 31.95 — ヴァンサバ亜種（抽象敵・UI主導） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×盤面が回路/パイプで可視化される（流れて増幅する）で、slotsとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: slots, mana
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist, Synergies
- 売りの10秒: 回路/パイプに数値が流れて増幅し、連鎖で一気に盤面が崩れる10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=4.2, video=3.7, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 3. Score 31.6 — ヴァンサバ亜種（抽象敵・UI主導） / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）で、heatとriskの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）
- リソース: heat, risk
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist, Synergies
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 4. Score 31.6 — ヴァンサバ亜種（抽象敵・UI主導） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×数値が『分裂』して複数経路に飛び、最終的に合流して爆発するで、heatとriskの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 数値が『分裂』して複数経路に飛び、最終的に合流して爆発する
- リソース: heat, risk
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist, Synergies
- 売りの10秒: 数値が分裂して多経路に流れ、合流点で巨大ダメージに変換される10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 5. Score 31.55 — ダイス/バッグ構築ローグライト / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのダイス/バッグ構築ローグライト。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）で、cooldownとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）
- リソース: cooldown, mana
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Synergies
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 6. Score 30.95 — ヴァンサバ亜種（抽象敵・UI主導） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのヴァンサバ亜種（抽象敵・UI主導）。同じカードを連続で使うと効果が変質（強化/暴発）×盤面が回路/パイプで可視化される（流れて増幅する）で、heatとriskの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: heat, risk
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

## 7. Score 30.85 — ヴァンサバ亜種（抽象敵・UI主導） / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×ダメージを与えると敵が強化される（逆転条件）で、cooldownとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / ダメージを与えると敵が強化される（逆転条件）
- リソース: cooldown, mana
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

## 8. Score 30.75 — ダイス/バッグ構築ローグライト / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのダイス/バッグ構築ローグライト。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×手札の上限が極端に小さい（3枚固定など）で、slotsとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 手札の上限が極端に小さい（3枚固定など）
- リソース: slots, mana
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

## 9. Score 30.75 — ダイス/バッグ構築ローグライト / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのダイス/バッグ構築ローグライト。オーバーキルが資産になる（余剰ダメージが次の攻撃に繰り越される）×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、heatとriskの管理が勝敗を決める。
- フック: オーバーキルが資産になる（余剰ダメージが次の攻撃に繰り越される） / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: heat, risk
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

## 10. Score 30.75 — ヴァンサバ亜種（抽象敵・UI主導） / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのヴァンサバ亜種（抽象敵・UI主導）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×カードは『置く』だけで、後は自動で連鎖解決される（ルールエンジン型）で、heatとmanaの管理が勝敗を決める。
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
