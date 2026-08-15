# FORGE CHAIN (309)

Blacksmithing color-match COMBO chain prototype. First blacksmithing / sword-forging genre in the collection.

## 体験仮説 (Experience Hypothesis)

「同じ金属を何度も打ち込んでビレットを真っ赤に熱し、コンボとテンパーを最大化してから水に焼き入れ(QUENCH)して高得点を爆発させる瞬間」に、ギリギリまで引き延ばす緊張と、一気に確定させる解放感を味わわせたい。

## メカニクス仮説 (Mechanics Hypothesis)

- **Mechanics**: 自動巡回するハンマー色と金床上のビレット色を一致させて打撃(SPACE/CLICK)。一致で TEMPER と COMBO が伸び、スコアは `10 * combo * (1 + temper // 3)`。不一致は HEAT+15 と COMBO/TEMPER 減少。COMBO>=4 で SUPER FORGE(虹色・任意色一致・3倍)。TEMPER>=1 で QUENCH(Q) して焼き入れ確定。
- **Dynamics**: 高コンボ・高テンパーを保持して更に伸ばす「欲張り」と、焼き入れで確定報酬(=`temper*100 + combo*20`)と HEAT 冷却(-30)を得てリセットする「安全」の駆け引き。炉の HEAT は常にじわじわ上昇するので、放置するとメルトダウン(ゲームオーバー)する。
- **Aesthetics**: 鍛冶職人として「今ここで焼き入れるか、もう一打ちするか」のスリルと、焼き入れ成功時のカタルシス。

## 実装したコアループ

1. 見る → ハンマー色の巡回とビレット色を見比べる
2. 判断 → 一致タイミングで打つか、焼き入れるか
3. 操作 → SPACE/CLICK(打撃) / Q(焼き入れ)
4. 結果 → TEMPER の輝き・スパーク・スコアポップアップで即時フィードバック
5. 次の判断 → さらに伸ばすか、焼き入れるか

## うまくいっている点

- 炉の HEAT と「焼き入れで -30」がテーマと完全に一致し、HEAT システムが初めて「炉の熱」として自然に機能する。
- TEMPER という「色へのコミットを重ねるほど価値が上がる」メカニクスが、既存 308 本の単純 COMBO とは異なる新しい判断軸を生む。
- QUENCH が「コンボを犠牲に確定報酬と冷却を得る」明確なリスク/リターンの出口になっている。

## 次に改善するなら最初に触る点

- 焼き入れ(QUENCH)の報酬式 `temper*100 + combo*20` と HEAT 冷却 -30 のバランス調整(現在は焼き入れが常に得に見える可能性がある)。
- ビレットの「次の色」プレビュー(未来の手札)を出して、待ち時間の判断をより戦略的にする。
- 複数ビレット同時進行や、刀身のビジュアルがコンボに応じて成長する演出。

## 操作方法

- SPACE / CLICK: 打撃(ハンマー色とビレット色を一致させる)
- Q: 焼き入れ QUENCH (TEMPER>=1 のとき有効)
- SPACE / R / ENTER: タイトル・ゲームオーバーから再スタート

## 実行方法

```bash
cd ~/repos/game-prototypes
uv run python prototypes/309_forge_chain/main.py
```

## テスト

```bash
uv run python prototypes/309_forge_chain/test_imports.py   # 38 headless tests
```

## ソース

game_idea_factory 生成バッチ(2026-08-15)の #1 (Score 32.35, ヴァンサバ亜種/宇宙採掘)から「合成圧縮→同色COMBO→SUPER」「未来の手札を消費→焼き入れ」フックを鍛冶テーマに再解釈。
