# CHUTE CHAIN — Parachute Skydiving Color-Match COMBO Game

**Prototype**: 158

**Source**: Game Idea Factory #1 (score 31.95) — "効果の合成圧縮 + 回路/パイプ可視化" hooks reinterpreted as parachute skydiving COMBO chain.

**一押しの瞬間**: 同色リングを連続でくぐり抜けてCOMBOが4に達し、SUPER CHUTEが発動して虹色に輝きながら全てのリングを自動回収しスコアが爆発する瞬間。

## 体験仮説
「同じ色のリングを狙って危険を選び、COMBOを積み上げてSUPER CHUTEを発動させた時、リスクを取った報酬として圧倒的なスコア爆発の快感を得られる」

## メカニクス仮説
- Mechanics: 落下しながら上昇する色付きリングを通過。同色連続でCOMBO増加、色違いでHEAT蓄積+COMBOリセット
- Dynamics: どのリングを狙うか（同色=COMBO継続、別色=HEAT上昇）、パラシュート展開タイミングの判断
- Aesthetics: 連鎖の快感、リスクとリターンの緊張、SUPER CHUTEの爆発的カタルシス

## 実装したコアループ
1. 落下しながらリング通過 → 同色でCOMBO +1、スコア加算
2. COMBO >= 4 → SUPER CHUTE発動（5秒、全色マッチ、3xスコア）
3. 色違い → COMBOリセット + HEAT +15
4. リング取り逃し → HEAT +5
5. HEAT >= 100 → ゲームオーバー
6. パラシュート展開(SPACE) → 落下速度低下、操作性向上
7. 60秒/5000ftで地上到達、パラシュート未展開→墜落

## 操作
- 矢印キー / A,D: 左右移動
- SPACE: パラシュート開閉
- ENTER: タイトル画面で開始 / ゲームオーバーでリトライ

## うまくいっている点
- リスクとリターンのバランス：同色COMBO継続の高倍率 vs HEAT蓄積の恐怖
- SUPER CHUTE発動時のビジュアルフィードバック（虹色、パーティクル倍増）
- パラシュート展開の戦略的判断（速く落ちるか遅く精密に操作するか）
- 58 headless tests passing

## 次に改善するなら最初に触る点
- 風システムをプレイヤー移動に影響させる（現在はリングのみ）
- パラシュート展開回数の制限制
- スコアランキング / ハイスコア永続化

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/158_chute_chain/main.py
```

## Engine
- Pyxel 2.x
- 320×240, display_scale=2
