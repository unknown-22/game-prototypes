# SEED SURGE — Mancala Color-Combo Chain (Prototype #183)

**Source**: game_idea_factory Idea #6 (Score 30.85), reinterpreted into Mancala (seed sowing).

## 体験仮説

「同色のピットを連続でキャプチャしてCOMBOがx4に達し、SUPER SOWで隣接ピットが一気に消え去るカスケードが爽快」

## 実装したコアループ

1. 自分のピットをクリック → 種を反時計回りに播く（Mancalaルール）
2. 最後の種の着地ピット色 == 開始ピット色 → CAPTURE（着地ピット＋対面ピットの種を獲得）
3. 同色連続キャプチャ → COMBO増加（x2, x3, x4...）
4. COMBO≥4 → SUPER SOW（隣接する同色ピットを自動キャプチャ、60f持続）
5. 色違い着地 → COMBOリセット + HEAT増加
6. HEAT≥100 → Game Over
7. AIのターン → プレイヤーターン繰り返し

## 操作

- マウスクリック: 自分のピットを選択して種まき
- タイトル/ゲームオーバー画面: クリックで開始/リスタート

## うまくいっている点

- Mancalaの種まきメカニクスと色合わせCOMBOの自然な融合
- SUPER SOWによる盤面一掃のカスケード演出
- AIのカウンターピックによる駆け引き
- HEATシステムによるリスク管理

## 次に改善するなら最初に触る点

- 種まきアニメーションの視覚化（現在は即時反映）
- AIの戦略強化（ミニマックスなど）
- サウンドエフェクト追加
- チュートリアル表示

## 実行方法

```bash
cd ~/repos/game-prototypes
uv run python prototypes/183_seed_surge/main.py
```

## テスト

```bash
uv run python prototypes/183_seed_surge/test_imports.py
```
