# SCORCH CHAIN (070)

Worms/Scorched Earth-style turn-based artillery battle with color-matching chain mechanics.

## 体験仮説

「角度と威力を見極めて放った砲弾が敵の足元を崩し、連鎖する地形崩壊で敵が落下して一撃必殺する瞬間に、読みが当たった時の痛快さを感じる」

## コアループ

1. PLAYER AIM — 矢印キーで角度調整、SPACE長押しでパワーチャージ、離して発射
2. PROJECTILE — 重力弾道で砲弾が飛び、地形に命中
3. EXPLOSION — 爆発範囲内の地形セルを破壊
4. COMBO — 同じ色の地形を連続破壊するとコンボ上昇（x3でSUPER SHELL）
5. GRAVITY COLLAPSE — 破壊後、上の地形が落下して詰まる（戦車も落下する可能性）
6. ENEMY TURN — AIが角度と威力を選んで反撃
7. どちらかのHPが0になるまで交互にターンを繰り返す

## 操作方法

- ← → : 角度調整
- SPACE 長押し : パワーチャージ（離して発射）
- ENTER : タイトル画面で開始 / ゲームオーバーでリトライ

## メカニクス

- **4色地形**: 赤(8)・緑(3)・青(5)・黄(10)。破壊色の連続でコンボ成立
- **COMBO**: 同色連続破壊で+1。色が変わるとリセット
- **SUPER SHELL**: COMBO>=3で発動。2倍ダメージ、2倍爆発範囲、虹色演出
- **重力崩壊**: 爆発後、浮いたブロックが落下。戦車直下の地形がなくなると戦車も落下＝即死

## うまくいっている点

- 51 headless tests が全通過
- ターン制砲撃戦はコレクション初のジャンル（Worms/Scorched Earth風）
- グリッドベースの地形破壊＋重力崩壊で戦略性が生まれている
- COMBOチェインによるリスクとリターン（同色狙い vs 直撃狙い）

## 次に改善するなら最初に触る点

- 地形生成のバリエーション（橋や洞窟など）
- 風（wind）要素の追加
- AIの精度向上（放物線計算による正確な照準）
- 複数武器タイプの追加

## How to run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/070_scorch_chain/main.py
```
