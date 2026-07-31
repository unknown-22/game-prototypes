# WAKE CHAIN — Jet Ski Color-Match COMBO Racer

## Source
Generated 2026-07-31 from game_idea_factory Idea #1 (Score 32.15).
Reinterpreted hooks: "log/replay as asset" → wake trail, "circuit/pipe visualization" → water current flow lines.

## Engine
- Pyxel 2.x, 320×240, display_scale=2, 30fps
- Python 3.13, uv-managed

## 体験仮説
「同じ色のブイを連続で回収してCOMBOを伸ばす緊張感と、SUPER WAKE発動で全てのブイがマッチになる爽快感のコントラストが面白い」

## コアループ
1. ブイが上から流れてくる
2. プレイヤーはジェットスキーを左右に動かし、自分の色と同じブイを回収
3. 同色連続回収でCOMBO上昇 → COMBO≥4でSUPER WAKE発動（虹色モード、全色マッチ、スコア3倍、HEAT凍結）
4. 色不一致でCOMBOリセット＋HEAT上昇、HEAT≥100でゲームオーバー
5. 60秒間スコアを競う

## 操作
- ←→ / A D : 移動
- クリック / SPACE : タイトルから開始、ゲームオーバーからリスタート

## うまくいっている点
- ジェットスキー（未開拓ジャンル）の追加
- ウェイクトレイルによるベストラン軌跡の可視化
- 水流ラインによる演出
- 43件のヘッドレステスト（全通過）
- OpenCode CLI 一発生成成功（セルフ修正含む）

## 次に改善するなら最初に触る点
- ブイの種類に応じた特殊効果（スロー、スピードアップなど）
- 障害物（岩、渦）の追加
- ウェイクの見た目の強化（波紋エフェクト）
