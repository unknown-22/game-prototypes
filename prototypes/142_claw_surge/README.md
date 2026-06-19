# CLAW SURGE — Color-Match Crane Game (Prototype 142)

## Source
- **Game Idea**: game_idea_factory #1 (Score 31.8)  
- **Hooks**: ログ/リプレイが資産 + 数値が分裂→合流→爆発
- **Reinterpretation**: クレーンゲーム（UFOキャッチャー）ジャンルへ再解釈 — 全141件中初のクレーンゲーム

## Engine
- Pyxel 2.x, 320×240, display_scale=2

## 体験仮説
「同じ色の景品を狙ってCOMBOを積み上げ、SUPER CLAWが発動して隣接する全同色景品がBFSで一気に回収される瞬間に、リスクを取った報酬の大きさと連鎖爆発の気持ちよさを感じる」

## Gameplay
- 8×6 グリッドに4色の景品（RED/GREEN/YELLOW/BLUE）が並ぶ
- クリックで景品をキャッチ
- **同色連続キャッチ** → COMBO +1、スコア = 10 + COMBO × 5
- **色違いキャッチ** → COMBO = 1 にリセット、HEAT +10
- **COMBO ≧ 4** → SUPER CLAW 発動！
  - 次のクリックでBFS flood-fill：クリックした景品と同じ色の隣接景品を全て回収
  - スコア = クラスターサイズ × 100 × COMBOボーナス
- **コラム重力**: キャッチ後、景品が下に詰まり、上部に新しい景品が補充される
- **HEAT**: 色違いキャッチで蓄積、減衰は毎回 -2。HEAT ≧ 100 でゲームオーバー
- **リスクとリターン**: 同色COMBO継続で高倍率スコア + SUPER CLAWへの道、色違いでHEAT増加 + COMBOリセット

## Controls
- マウスクリック: 景品キャッチ
- SPACE: タイトル画面でスタート / ゲームオーバー画面でリトライ

## Dev Status
- ✅ Core mechanic: click-to-grab + same-color COMBO chain
- ✅ SUPER CLAW: BFS flood-fill cluster grab at COMBO ≧ 4
- ✅ Column gravity + refill after each grab
- ✅ HEAT risk system with decay
- ✅ Particle burst + floating text feedback
- ✅ 3 screens: Title, Game, Game Over
- ✅ 45 headless tests (all pass)
- ✅ ruff / ty checks pass
- ✅ Web build (docs/142_claw_surge.html)
- ⬜ Sound effects
- ⬜ Difficulty ramping (HEAT increase rate over time)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/142_claw_surge/main.py
```

## うまくいっている点
- SUPER CLAW の BFS 一斉回収が気持ちいい（5個クラスター → COMBO 4× → 2000点）
- コラム重力による盤面の動的変化で、毎回違う配置になる
- decay-before-check バグを発見・修正（ゲームオーバー不能バグ）

## 次に改善するなら
- 難度上昇（時間経過でHEAT減衰量減少、または新規景品の色分布を偏らせる）
- 効果音（キャッチ音、COMBO音、SUPER CLAW発動音）
- ゴーストカーソル（前回のキャッチ位置の軌跡表示 = 「log/replay as asset」フックの活用）
