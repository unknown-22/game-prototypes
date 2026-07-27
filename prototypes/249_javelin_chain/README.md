# 249_javelin_chain — Javelin Throw Color-Match COMBO Chain

やり投げ × 色合わせ COMBO チェイン。

## 体験仮説

「風を読んで狙いを定め、同色ゾーンに連続で命中させた時、投げる直前に"今だ！"と決める緊張感が面白い」

## 実装したコアループ

1. **AIMING**: マウス長押しでパワーチャージ、マウス位置で投擲角度を決める
2. **FLYING**: 重力＋風の影響を受けながらやりが飛行
3. **SCORING**: 着地ゾーン判定 → 同色ならCOMBO継続、色違いでCOMBOリセット＋HEAT

COMBO>=4 で SUPER THROW (300f虹色モード、全色一致、3xスコア、HEAT無効)

## 操作方法

- マウス長押し: パワーチャージ（最大60fで100%）
- マウス位置: 投擲角度（右上方向）
- マウス離す: 投擲！

## リスクとリターン

- 同色連続命中 → COMBOチェイン (100 * combo * multiplier)
- 色違い命中 → COMBOリセット + HEAT +15
- 場外 (FAULT) → HEAT +20
- スタミナ制 (max 100, -25/投擲, +0.15/f 回復) で連投制限
- SUPERモード中はHEAT増加無効、全色一致、3倍スコア

## うまくいっている点

- パワー×角度の物理ベース投擲操作が直感的
- 風システムが「読む」要素を追加し、毎投ごとの判断を生む
- SUPER THROW発動時の虹色エフェクト＋常時最大パワーが爽快
- スタミナによる連投制限がリソース管理の面白さを作る

## 次に改善するなら最初に触る点

- 着地ゾーンの間隔確保アルゴリズム（フォールバックで重なる問題）
- 風の可視化を強化（現在は小さな矢印のみ）
- やり投げの軌跡予測線（放物線のプレビュー）

## How to run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/249_javelin_chain/main.py
```

## Source

game_idea_factory Idea #1 (Score 31.95) — 宇宙採掘デッキ構築ローグライト
- 「連鎖増殖」→ 同色連続命中 COMBO chain → SUPER THROW
- 「未来の手札がコスト」→ STAMINA 制
- 「heat/risk」→ HEAT リスクシステム

## Engine

Pyxel 2.x, 320×240, Python 3.12+
