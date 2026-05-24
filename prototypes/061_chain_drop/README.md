# CHAIN DROP — Column-Drop Chain Reaction Game

**Prototype 061** | Source: Game Idea #1 (Score 31.35)

## 体験仮説
「最後の1手で盤面の半分が連鎖反応で消え去るカタルシス」 — 同じ色を連続で落とすCOMBO戦略と、一か八かのSUPER DISCが生む爆発的な連鎖が面白い。

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Python 3.12+, single-file (~542 lines)

## Gameplay
Connect Four風のカラムドロップパズルに色合わせ連鎖反応を組み合わせたゲーム。

- **Core mechanic**: 7列×6行のグリッドに色付きディスクを落とし、4つ以上同じ色が揃うと消える
- **COMBO system**: 同じ色を連続で落とすとCOMBOが伸び、COMBO 4+でSUPER DISC（虹色ワイルドカード）が出現
- **SUPER DISC**: 全色にマッチする特殊ディスク。クリア時にスコア3倍
- **Grid Pressure**: 5ターンごとにグリッド下部からランダムな列にディスクが湧き出る
- **Chain Reaction**: ディスク消去 → 重力圧縮 → 新たなマッチ → 連鎖反応ループ

## リスクとリターン
- **リスク**: 色を変えるとCOMBOがリセットされる → 欲張って同じ色を狙い続けるか、安全に色を変えるかの判断
- **リターン**: COMBOが高いほどスコア倍率が上がり、SUPER DISCの大爆発につながる
- **Grid Pressure**: 時間経過でグリッドが埋まるプレッシャーが「早く消さなければ」という緊張を生む

## 面白い瞬間
盤面が危機的な状況で、SUPER DISCを投入 → 半分以上のディスクが連鎖反応で消え去り、大量スコアが飛び出す瞬間。

## Controls
- **LEFT / RIGHT**: 列の選択
- **SPACE / RETURN**: ディスクを落とす
- **R**: ゲームオーバー時にリスタート

## Scoring
- 基本: 消したディスク1つにつき10点
- 同時マッチグループ数 × 基本点
- COMBOボーナス: combo × 50点
- SUPER DISC: スコア3倍
- 連鎖反応: 2回目以降の連鎖で+50%ずつ倍率上昇

## Dev Status
- ✅ Core mechanic: column-drop with match-4 detection (horizontal/vertical/both diagonals)
- ✅ COMBO system with SUPER DISC
- ✅ Chain reaction via gravity compaction
- ✅ Grid pressure mechanic
- ✅ Particle effects, floating text, screen shake
- ✅ Title / Game / Game Over screens
- ✅ 43 headless logic tests
- ✅ ruff + ty checks pass
- ✅ Web build (docs/061_chain_drop.html)

## 次に改善するなら
- 落下アニメーションの滑らかさ向上（連鎖反応時の視認性）
- 効果音（drop, clear, combo, super）
- 難易度曲線の調整（grid pressureの頻度を段階的に上げる）
- スコアのハイスコア保存

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/061_chain_drop/main.py
```
