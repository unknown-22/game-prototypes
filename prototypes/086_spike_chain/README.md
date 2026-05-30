# SPIKE CHAIN — 086_spike_chain

**Volleyball Color-Match Combo Prototype**

## Source
Reinterpreted from game_idea_factory #1 (Score 31.95): Dice/Bag Roguelite / Hacking
Hooks: "synthesis compression" + "circuit visualization (flow and amplify)"
→ Volleyball: same-color consecutive touches build COMBO chain → SYNTHESIS SUPER SPIKE

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single-file main.py (788 lines)
- 83 headless tests

## 体験仮説
「同色を狙ってCOMBOを積み重ね、満を持してSUPER SPIKEを決める瞬間が気持ちいい」
→ 連続同色タッチでCOMBOが伸びるが、色が変わるリスクもある。無理せず返球するか、COMBOを狙って粘るかの判断が生まれる。

## メカニクス仮説
- Mechanics: 同色連続タッチ → COMBO上昇。COMBO x3以上のスパイク → SUPER SPIKE（AIブロック貫通、画面揺れ、パーティクル）
- Dynamics: ラリー中に「今の色と次のボールの色は合うか？」「無理して同色を待つか安全に返すか」の駆け引き
- Aesthetics: SUPER SPIKEの爽快感と達成感

## Core Loop
1. サーブ → ラリー開始
2. プレイヤー：マウス移動でポジショニング、クリックでバンプ/セット/スパイク
3. AI：自動で返球
4. ボールが相手コートの地面に落ちる → ポイント
5. 5点先取で試合終了 → リスタート

## Controls
- マウス移動：プレイヤー横移動（左コート内）
- マウスクリック：ボールにタッチ（バンプ/セット/スパイク）
- SPACE：タイトル画面から開始、ゲームオーバーから再挑戦
- R：リスタート

## Color System
4色：RED(8) → GREEN(3) → LIME(11) → YELLOW(10) → RED...
タッチするたびに色が自動循環。前回と同じ色でタッチするとCOMBO+1。異なる色だとCOMBOリセット。

## Dev Status
- ✅ コアメカニクス：同色COMBO → SUPER SPIKE
- ✅ タイトル画面 + ゲーム画面 + ゲームオーバー画面
- ✅ パーティクルシステム + フローティングテキスト
- ✅ 画面揺れ（pyxel.camera）
- ✅ 83 headless tests (pytest, ruff, ty all pass)
- ✅ Webビルド済み

## うまくいっている点
- SUPER SPIKEの演出（画面揺れ + 大量パーティクル）が気持ちいい
- COMBO継続 vs 安全返球のリスク/リターン判断が明確
- AIの自動返球がテンポよくラリーを成立させる

## Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/086_spike_chain/main.py
```
