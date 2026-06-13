# 121 LIFT CHAIN — Color-Match Olympic Weightlifting

**Source**: game_idea_factory #1 (Score 32.75) — alchemy deckbuilder → reinterpreted into weightlifting

- Hooks: "synthesis/compression" → COMBO compresses into SUPER LIFT, "CA infection/growth" → heat spreads from bad lifts, "heat/risk" → risk heavier weight for more points
- **First weightlifting prototype in the collection!**

**Engine**: Pyxel 2.x, 320×240, display_scale=2, fps=30

## 体験仮説
「同じ色の重量を連続成功させ、COMBOが4に達してSUPER LIFTが発動し、虹色バーベルで自動完美リフトが決まる瞬間が面白い」

## ゲームプレイ
- SPACE長押しでパワーメーターを溜める
- グリーンゾーンで離す = PERFECT、イエロー = OK、外す = MISS
- 前回と同じ色のプレートを成功 = COMBO++
- 違う色 = コンボリセット + HEAT増加
- COMBO ≥ 4 = SUPER LIFT（5秒間、虹色、自動PERFECT、3倍スコア）
- HEAT ≥ 100 = GAME OVER

## 操作
- SPACE: 押す（パワー溜め開始）/ 離す（リフト実行）
- R: GAME OVERからリトライ

## リスクとリターン
- 重量はコンボに応じて増加（100kg → 最大）
- 重いほど的ゾーンが狭くなる（高リスク高リターン）
- 同じ色を保つか、ランダムに任せるかの判断

## 開発状況
- ✅ コアメカニクス（パワーメーター、タイミング判定）
- ✅ COMBOシステム + SUPER LIFT
- ✅ HEATリスク管理
- ✅ パーティクルエフェクト
- ✅ タイトル/ゲーム/ゲームオーバー画面
- ✅ 49 headless tests（ruff✅ ty✅ pytest✅）
- ✅ Webビルド完了

## 実行方法
```bash
cd ~/repos/game-prototypes
uv run python prototypes/121_lift_chain/main.py
```

## OpenCode
- **First-try success** with `opencode run -f /tmp/design_121.txt --model opencode-go/deepseek-v4-pro` (no --thinking)
- OpenCode autonomously: wrote code, fixed ruff/ty, found+fixed decay-before-check ordering bug, ran tests, self-corrected
