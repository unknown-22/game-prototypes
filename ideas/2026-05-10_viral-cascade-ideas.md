# Game Idea Factory output (2026-05-10T21:01:05)

## 1. Score 32.55 — デッキ構築ローグライト（マップノード） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのデッキ構築ローグライト（マップノード）。ログ/リプレイが資産（前回の行動が次回のカードになる）×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、heatとriskの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: heat, risk
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Meta Progression
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 2. Score 31.85 — デッキ構築ローグライト（マップノード） / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのデッキ構築ローグライト（マップノード）。ログ/リプレイが資産（前回の行動が次回のカードになる）×1ターンに使えるカードは『1色だけ』で、manaとheatの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 1ターンに使えるカードは『1色だけ』
- リソース: mana, heat
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Meta Progression
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=3.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 3. Score 31.75 — デッキ構築ローグライト（マップノード） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのデッキ構築ローグライト（マップノード）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×戦闘は数字とアイコン中心（敵は抽象化）で、manaとslotsの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 戦闘は数字とアイコン中心（敵は抽象化）
- リソース: mana, slots
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 増殖/感染が連鎖して盤面が一気に塗り替わり、最後にまとめて回収する10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.0, video=4.5, feasibility=4.2, competition=3.2, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 4. Score 31.6 — ヴァンサバ亜種（抽象敵・UI主導） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）で、cooldownとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / UIの連鎖演出で気持ちよさを作る（崩壊/増加/圧縮）
- リソース: cooldown, mana
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

## 5. Score 31.45 — ヴァンサバ亜種（抽象敵・UI主導） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのヴァンサバ亜種（抽象敵・UI主導）。ログ/リプレイが資産（前回の行動が次回のカードになる）×1ターンに使えるカードは『1色だけ』で、riskとmanaの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 1ターンに使えるカードは『1色だけ』
- リソース: risk, mana
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist, Meta Progression
- 売りの10秒: 画面がアイコンの物量で埋まり、範囲効果で一掃する10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=3.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss

## 6. Score 31.4 — ダイス/バッグ構築ローグライト / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのダイス/バッグ構築ローグライト。ログ/リプレイが資産（前回の行動が次回のカードになる）×落下/重力で『連鎖崩壊』が起きる（パズル的な崩れ方）で、riskとcooldownの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 落下/重力で『連鎖崩壊』が起きる（パズル的な崩れ方）
- リソース: risk, cooldown
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based, Meta Progression, Puzzle
- 売りの10秒: 積み上げた盤面が連鎖崩壊して、数字と報酬が雪崩のように出る10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.0, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 7. Score 30.95 — ダイス/バッグ構築ローグライト / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのダイス/バッグ構築ローグライト。同じカードを連続で使うと効果が変質（強化/暴発）×盤面が回路/パイプで可視化される（流れて増幅する）で、comboとriskの管理が勝敗を決める。
- フック: 同じカードを連続で使うと効果が変質（強化/暴発） / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: combo, risk
- Steamタグ候補: Roguelite, Dice, Strategy, Turn-Based
- 売りの10秒: 回路/パイプに数値が流れて増幅し、連鎖で一気に盤面が崩れる10秒
- 見積: 敵7 / ボス2 / UI7 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.7, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- roll/draw
- allocate
- resolve
- improve pool
- repeat

## 8. Score 30.85 — ヴァンサバ亜種（抽象敵・UI主導） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×同時に管理できる対象が3つまで（超ミニマルUI）で、riskとheatの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 同時に管理できる対象が3つまで（超ミニマルUI）
- リソース: risk, heat
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

## 9. Score 30.75 — デッキ構築ローグライト（マップノード） / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのデッキ構築ローグライト（マップノード）。敵を倒すほど『コンボメーター』が伸び、報酬が加速度的に増える×盤面が回路/パイプで可視化される（流れて増幅する）で、cooldownとmanaの管理が勝敗を決める。
- フック: 敵を倒すほど『コンボメーター』が伸び、報酬が加速度的に増える / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: cooldown, mana
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

## 10. Score 30.75 — ダイス/バッグ構築ローグライト / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのダイス/バッグ構築ローグライト。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×ダメージを与えると敵が強化される（逆転条件）で、slotsとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / ダメージを与えると敵が強化される（逆転条件）
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
