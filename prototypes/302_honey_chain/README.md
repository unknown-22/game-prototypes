# HONEY CHAIN (302) — Beekeeping / Pollination

- **Source**: game_idea_factory #1 (Score 32.75, 配送/物流デッキ構築 — hooks: 「合成圧縮」「CA盤面充填」) を養蜂に再解釈
- **Engine**: Pyxel 2.x, 320x240, display_scale=2, 60fps
- **Run**: `cd ~/repos/game-prototypes && uv run python prototypes/302_honey_chain/main.py`
- **Test**: `uv run python prototypes/302_honey_chain/test_imports.py`

## 体験仮説
「同じ色の花を次々に辿ってCOMBOを重ね、SUPER POLLENで虹色に咲き乱れる花畑を一気に塗り替えるのが面白い。」

## 実装したコアループ
- ミツバチを矢印キーで自由移動（斜め正規化、速度2.0）
- 蜂の「花粉色」は最後に訪れた花の色で決まる（自動巡回ではない）
- 花に触れると受粉：同色なら COMBO++（score=10*combo*倍率）、色違いなら HEAT+15 で COMBO リセット
- 触れた花は消えて後で再出現（respawn）、花粉色は常にその花の色に更新される
- COMBO>=4 で SUPER POLLEN（300f、虹色、全色マッチ、3倍、HEAT凍結）
- 花はセルオートマトンで発芽・増殖（45f→20f間隔、25%で隣接セルに同色の新芽）
- HEAT（色違い+15、減衰-0.02/f、上限100でゲームオーバー）/ 60秒タイマー
- 難度上昇：spawn 60f→30f、CA 45f→20f、最大花数 10→16

## うまくいっている点
- 「花粉色＝最後に訪れた花」により、色を変えるためにわざとミス（HEAT+15）を払うか、同色の花を探して遠回りするかのルーティング判断が生まれる
- CA増殖で盤面が混んでいくにつれ、ミスを避けるのが難しくなり自然な難度上昇になる
- 44件のヘッドレステスト、ruff/ty すべて通過、OpenCode 初回成功

## 次に改善するなら最初に触る点
- SUPER POLLEN の虹色モード中は「全色マッチ」なので、盤面が一瞬で塗り替わるカタルシスをもっと強調（画面揺れや連鎖エフェクトを強化）
- 花の CA 増殖が速すぎると理不尽に感じるため、増殖率のカーブ調整
