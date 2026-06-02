# Game Idea Factory output (2026-06-03T03:04:07)

## 1. Score 31.95 — ヴァンサバ亜種（抽象敵・UI主導） / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×盤面が回路/パイプで可視化される（流れて増幅する）で、manaとslotsの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: mana, slots
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

## 2. Score 31.95 — デッキ構築ローグライト（マップノード） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのデッキ構築ローグライト（マップノード）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×コストはHPではなく『未来の手札』を消費で、cooldownとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / コストはHPではなく『未来の手札』を消費
- リソース: cooldown, mana
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

## 3. Score 31.6 — ダイス/バッグ構築ローグライト / 錬金術（合成）

- 1行ピッチ: 錬金術（合成）がテーマのダイス/バッグ構築ローグライト。効果が『合成』されて1枚に圧縮される×ヒット数/チェイン数が画面全体で可視化され、加速していくで、riskとmanaの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / ヒット数/チェイン数が画面全体で可視化され、加速していく
- リソース: risk, mana
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

## 4. Score 31.35 — デッキ構築ローグライト（マップノード） / 厄災封印（暴走制御）

- 1行ピッチ: 厄災封印（暴走制御）がテーマのデッキ構築ローグライト（マップノード）。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×盤面が回路/パイプで可視化される（流れて増幅する）で、comboとmanaの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / 盤面が回路/パイプで可視化される（流れて増幅する）
- リソース: combo, mana
- Steamタグ候補: Deckbuilder, Roguelite, Turn-Based, Strategy
- 売りの10秒: 回路/パイプに数値が流れて増幅し、連鎖で一気に盤面が崩れる10秒
- 見積: 敵8 / ボス2 / UI8 / アニメlow / ネットnone
- スコア内訳: pitch=3.4, video=3.7, feasibility=4.0, competition=3.0, replay=3.6, steamfit=4.4

コアループ:
- map node
- encounter
- reward
- deck change
- repeat

## 5. Score 31.35 — ダイス/バッグ構築ローグライト / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのダイス/バッグ構築ローグライト。各フロアでルールが1つだけ変わる（コスト/ドロー/速度など）×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、comboとheatの管理が勝敗を決める。
- フック: 各フロアでルールが1つだけ変わる（コスト/ドロー/速度など） / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: combo, heat
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

## 6. Score 31.35 — ダイス/バッグ構築ローグライト / 配送/物流（流量最適化）

- 1行ピッチ: 配送/物流（流量最適化）がテーマのダイス/バッグ構築ローグライト。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×戦闘は数字とアイコン中心（敵は抽象化）で、slotsとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 戦闘は数字とアイコン中心（敵は抽象化）
- リソース: slots, mana
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

## 7. Score 31.15 — デッキ構築ローグライト（マップノード） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのデッキ構築ローグライト（マップノード）。リソースが閾値を超えると『暴走モード』に入り、制御しながら稼ぐ×盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御するで、heatとriskの管理が勝敗を決める。
- フック: リソースが閾値を超えると『暴走モード』に入り、制御しながら稼ぐ / 盤面がセルオートマトン（感染/増殖）で埋まっていくのを制御する
- リソース: heat, risk
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

## 8. Score 30.85 — ヴァンサバ亜種（抽象敵・UI主導） / 発電所（過負荷と放電）

- 1行ピッチ: 発電所（過負荷と放電）がテーマのヴァンサバ亜種（抽象敵・UI主導）。効果が『合成』されて1枚に圧縮される×手札の上限が極端に小さい（3枚固定など）で、riskとcooldownの管理が勝敗を決める。
- フック: 効果が『合成』されて1枚に圧縮される / 手札の上限が極端に小さい（3枚固定など）
- リソース: risk, cooldown
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

## 9. Score 30.75 — ダイス/バッグ構築ローグライト / ハッキング（回路/ログ）

- 1行ピッチ: ハッキング（回路/ログ）がテーマのダイス/バッグ構築ローグライト。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×敵HPが“塊”として表示され、削るとバラけて全体が崩れるで、cooldownとmanaの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 敵HPが“塊”として表示され、削るとバラけて全体が崩れる
- リソース: cooldown, mana
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

## 10. Score 30.75 — ヴァンサバ亜種（抽象敵・UI主導） / 宇宙採掘（リソース変換）

- 1行ピッチ: 宇宙採掘（リソース変換）がテーマのヴァンサバ亜種（抽象敵・UI主導）。連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する×手札の上限が極端に小さい（3枚固定など）で、heatとriskの管理が勝敗を決める。
- フック: 連鎖条件を満たすと効果が『増殖』して盤面全体に伝播する / 手札の上限が極端に小さい（3枚固定など）
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
