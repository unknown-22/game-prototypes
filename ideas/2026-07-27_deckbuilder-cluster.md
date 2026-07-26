# Game Idea Factory output (2026-07-27T00:03:31)

## 1. Score 32.05 — デッキ構築ローグライト（マップノード） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×1ターンに使えるカードは『1色だけ』で、riskとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 1ターンに使えるカードは『1色だけ』
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

## 2. Score 31.95 — デッキ構築ローグライト（マップノード） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのデッキ構築ローグライト（マップノード）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×コストはHPではなく『未来の手札』を消費で、slotsとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / コストはHPではなく『未来の手札』を消費
- リソース: slots, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 3. Score 31.95 — デッキ構築ローグライト（マップノード） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのデッキ構築ローグライト（マップノード）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×1ターンに使えるカードは『1色だけ』で、riskとslotsの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 1ターンに使えるカードは『1色だけ』
- リソース: risk, slots
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.5, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 4. Score 31.6 — ヴァンサバ亜種（抽象敵・UI主導） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×落下/重力で『連鎖崩壊』が起きる（パズル的な崩れ方）で、manaとslotsの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 落下/重力で『連鎖崩壊』が起きる（パズル的な崩れ方）
- リソース: mana, slots
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist, Puzzle, Synergies
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 5. Score 31.35 — ダイス/バッグ構築ローグライト / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのダイス/バッグ構築ローグライト。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、heatとmanaの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: heat, mana
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

## 6. Score 31.15 — デッキ構築ローグライト（マップノード） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのデッキ構築ローグライト（マップノード）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×手札の上限が極端に小さい（3枚固定など）で、comboとslotsの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 手札の上限が極端に小さい（3枚固定など）
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

## 7. Score 31.05 — デッキ構築ローグライト（マップノード） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのデッキ構築ローグライト（マップノード）。ログ/リプレイが資産（前回の行動が次回のカードになる）×同時に管理できる対象が3つまで（超ミニマルUI）で、cooldownとmanaの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 同時に管理できる対象が3つまで（超ミニマルUI）
- リソース: cooldown, mana
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

## 8. Score 30.65 — ヴァンサバ亜種（抽象敵・UI主導） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのヴァンサバ亜種（抽象敵・UI主導）。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×コストはHPではなく『未来の手札』を消費で、riskとmanaの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / コストはHPではなく『未来の手札』を消費
- リソース: risk, mana
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

## 9. Score 30.6 — ヴァンサバ亜種（抽象敵・UI主導） / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのヴァンサバ亜種（抽象敵・UI主導）。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×ヒット数/チェイン数が画面全体で可視化され、加速していくで、riskとheatの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / ヒット数/チェイン数が画面全体で可視化され、加速していく
- リソース: risk, heat
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

## 10. Score 30.35 — ダイス/バッグ構築ローグライト / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのダイス/バッグ構築ローグライト。オーバーキルが資産になる（余剰ダメージが次の攻撃に繰り越される）×盤面が回路/パイプで可視化される（流れて増幅する）で、manaとcooldownの管理が勝敗を決める。
- フック: オーバーキルが資産になる（余剰ダメージが次の攻撃に繰り越される） / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: mana, cooldown
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based
- 売りの10秒: 回路/パイプに数値が流れて増幅し、連鎖で一気に盤面が崩れる10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.7, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat
