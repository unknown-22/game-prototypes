# SKIP SURGE (117) — Color-Match Stone Skipping

## Source
game_idea_factory #1 (Score 31.95) — 発電所（過負荷と放電）/ ヴァンサバ亜種
- Hooks: 合成圧縮 + 回路/パイプ可視化（流れて増幅）
- Reinterpreted: 水面の波紋 = 回路/パイプ, 石の連続ジャンプ = 流れて増幅, 同色連続 = 合成圧縮→COMBO

## Engine
- Pyxel 2.x, 320×240, display_scale=2

## Gameplay
- マウスクリック＆ホールドでパワーを溜め、リリースで石を投げる
- 水面に浮かぶ色付きの波紋（ripple）に石をスキップさせる
- **同色の波紋に連続ヒット → COMBO チェイン**
- COMBO ≥ 4 → **SUPER SKIP** 発動（5秒間：虹色、スコア3倍、バウンド力強化、全色一致）
- 違う色に当たると COMBO リセット + HEAT+2
- 全ミスで HEAT+1
- HEAT ≥ 100 または 90秒経過で GAME OVER

## Controls
- Mouse: クリック＆ホールドでパワーチャージ、リリースで投擲
- SPACE / RETURN: タイトル画面からスタート、ゲームオーバーからリトライ

## 面白い瞬間
「同じ色の波紋を連続で石がスキップし、COMBOが溜まってSUPER SKIPで石が虹色に輝きながら水面を飛び続ける爆発的爽快感」

## リスクとリターン
- RISK: 同色COMBO継続に失敗するとHEAT蓄積→ゲームオーバー
- REWARD: COMBO継続で高倍率スコア + SUPER SKIP発動

## Dev Status
- ✅ Core mechanic: stone throwing with power charge
- ✅ Ripple system: 4-color, drift, respawn
- ✅ COMBO chain + SUPER SKIP at COMBO≥4
- ✅ HEAT risk system with decay
- ✅ Particle splash effects + floating score text
- ✅ Power bar visualization
- ✅ 3 screens: TITLE, GAME, GAME_OVER
- ✅ 50 headless tests (all pass)
- ✅ ruff + ty clean
- ✅ Web build (docs/117_skip_surge.html)
- ✅ decay-before-threshold bug fixed (heat check runs before decay)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/117_skip_surge/main.py
```
