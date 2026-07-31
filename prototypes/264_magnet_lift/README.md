# MAGNET LIFT

> 廃棄場のマグネットクレーン色合わせCOMBOアクションゲーム

## 体験仮説
「流れるスクラップから同色を連続で吸い上げ、COMBOが伸びてSUPER MAGNETが発動する緊張と快感のコントラストが面白い」

## Source
- game_idea_factory #1 (Score 32.2): ダイス/バッグ構築ローグライト・魔法学院
- Hooks reinterpreted: 「ログ/リプレイが資産」→ 磁場トレイル、「UIの連鎖演出」→ COMBO→SUPER MAGNET
- Generated: 2026-07-29 (ideas_cron_255.md)
- **初のクレーンゲームジャンル**

## Core Loop
1. コンベア上をスクラップが流れる（下→上、速度1.0→3.0px/f）
2. プレイヤーはクレーンを左右移動（A/D or ←→）し、SPACEでマグネットを降下
3. 同色スクラップを連続キャッチ → COMBO+1、スコア加算
4. 色違い → COMBOリセット + HEAT+15
5. スクラップ取り逃し → HEAT+5
6. COMBO≥4 → SUPER MAGNET（300f、虹色全色一致、スコア3倍、HEAT凍結）
7. HEAT≥100 または 60秒タイマー満了 → ゲームオーバー

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Python 3.12+, single-file (main.py, 639 lines)

## Controls
| Key | Action |
|---|---|
| ←→ / A D | クレーン左右移動 |
| SPACE (hold) | マグネット降下 |
| SPACE (release) | マグネット上昇 |
| SPACE / RETURN | タイトル→開始 / リトライ |

## Status
- ✅ 3 screens (Title/Playing/GameOver)
- ✅ 4-color scrap system (RED/LIME/DARK_BLUE/YELLOW)
- ✅ COMBO chain + SUPER MAGNET
- ✅ HEAT risk + timer escalation
- ✅ Particle system + trail dots + screen shake + floating text
- ✅ 78 headless tests (pytest)
- ✅ ruff zero errors
- ✅ ty zero errors

## うまくいっている点
- マグネットの物理感（降下/上昇の速度差、移動速度制限）が操作にリズムを生む
- 同色を狙うCOMBOリスクと安全に拾うトレードオフが明確

## 改善するなら
- スクラップの形状バリエーション（タイヤ、冷蔵庫、自転車など）
- 複数マグネット同時操作
- ベルト速度が画面外からも視認できるUI

## How to run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/264_magnet_lift/main.py
```
