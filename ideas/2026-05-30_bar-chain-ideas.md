# Game Idea Factory output (2026-05-30T03:01:36)

## 1. Score 32.75 — デッキ構築ローグライト（マップノード） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、heatとriskの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: heat, risk
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

## 2. Score 31.85 — デッキ構築ローグライト（マップノード） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのデッキ構築ローグライト（マップノード）。効果が『合成』されて1枚に圧縮される×戦闘は数字とアイコン中心（敵は抽象化）で、heatとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 戦闘は数字とアイコン中心（敵は抽象化）
- リソース: heat, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Synergies
- 売りの10秒: 合成で1枚に圧縮された超カードが成立して、数字が爆発する10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.8, video=3.5, feasibility=4.2, competition=3.2, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 3. Score 31.45 — ヴァンサバ亜種（抽象敵・UI主導） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのヴァンサバ亜種（抽象敵・UI主導）。ログ/リプレイが資産（前回の行動が次回のカードになる）×コストはHPではなく『未来の手札』を消費で、manaとslotsの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / コストはHPではなく『未来の手札』を消費
- リソース: mana, slots
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

## 4. Score 31.2 — デッキ構築ローグライト（マップノード） / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのデッキ構築ローグライト（マップノード）。敵を倒すほど『コンボメーター』が伸び、報酬が加速度的に増える×コストはHPではなく『未来の手札』を消費で、manaとheatの管理が勝敗を決める。
- フック: 敵を倒すほど『コンボメーター』が伸び、報酬が加速度的に増える / コストはHPではなく『未来の手札』を消費
- リソース: mana, heat
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: コンボ/チェインが加速して、画面全体の数字が踊り続ける10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=4.0, feasibility=4.0, competition=3.0, replay=3.0, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 5. Score 31.05 — デッキ構築ローグライト（マップノード） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのデッキ構築ローグライト（マップノード）。ログ/リプレイが資産（前回の行動が次回のカードになる）×カードは『置く』だけで、後は自動で連鎖解決される（ルールエンジン型）で、riskとslotsの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / カードは『置く』だけで、後は自動で連鎖解決される（ルールエンジン型）
- リソース: risk, slots
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

## 6. Score 31.05 — デッキ構築ローグライト（マップノード） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのデッキ構築ローグライト（マップノード）。ログ/リプレイが資産（前回の行動が次回のカードになる）×1アクションが盤面に『痕跡』を残し、次の解決がどんどん派手になるで、comboとmanaの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 1アクションが盤面に『痕跡』を残し、次の解決がどんどん派手になる
- リソース: combo, mana
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

## 7. Score 30.75 — ダイス/バッグ構築ローグライト / 魔法学院（ルール改変）

- 1行ピッチ: 魔法学院（ルール改変）がテーマのダイス/バッグ構築ローグライト。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×敵HPが“塊”として表示され、削るとバラけて全体が崩れるで、manaとslotsの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 敵HPが“塊”として表示され、削るとバラけて全体が崩れる
- リソース: mana, slots
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

## 8. Score 30.75 — デッキ構築ローグライト（マップノード） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのデッキ構築ローグライト（マップノード）。部分観測（敵の意図が確率でしか見えない）×1ターンに使えるカードは『1色だけ』で、cooldownとmanaの管理が勝敗を決める。
- フック: 部分観測（敵の意図が確率でしか見えない） / 1ターンに使えるカードは『1色だけ』
- リソース: cooldown, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Tactical
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- 注意: チュートリアルが難しくなりがち
- スコア内訳: pitch=3.8, video=3.5, feasibility=3.6, competition=3.0, replay=3.3, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 9. Score 30.75 — デッキ構築ローグライト（マップノード） / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのデッキ構築ローグライト（マップノード）。部分観測（敵の意図が確率でしか見えない）×コストはHPではなく『未来の手札』を消費で、riskとheatの管理が勝敗を決める。
- フック: 部分観測（敵の意図が確率でしか見えない） / コストはHPではなく『未来の手札』を消費
- リソース: risk, heat
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy, Tactical
- 売りの10秒: 連鎖が噛み合って、敵HPバーが溶ける10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- 注意: チュートリアルが難しくなりがち
- スコア内訳: pitch=3.8, video=3.5, feasibility=3.6, competition=3.0, replay=3.3, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 10. Score 30.65 — ヴァンサバ亜種（抽象敵・UI主導） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのヴァンサバ亜種（抽象敵・UI主導）。ログ/リプレイが資産（前回の行動が次回のカードになる）×敵HPが“塊”として表示され、削るとバラけて全体が崩れるで、comboとcooldownの管理が勝敗を決める。
- フック: ログ/リプレイが資産（前回の行動が次回のカードになる） / 敵HPが“塊”として表示され、削るとバラけて全体が崩れる
- リソース: combo, cooldown
- Steamタグ候補: Roguelite, Action, Auto-Shooter, Minimalist, Meta Progression
- 売りの10秒: 画面がアイコンの物量で埋まり、範囲効果で一掃する10秒
- 見積: 敵6 / ボス2 / UI6 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.5, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.0

コアループ:
- move minimal
- auto damage
- pick upgrades
- escalate
- boss
