# COIN SURGE — 138

**コインプッシャーアーケード × 色合わせCOMBOチェイン**

## Source
- Game Idea Factory #1 (Score 32.55) — デッキ構築ローグライト（魔法学院/ルール改変）
- Hooks reinterpreted: 「ログ/リプレイが資産」→ coins build up as future push force, 「CA盤面充填」→ coins spread and push each other
- First **coin pusher arcade** genre in collection

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single file: `main.py` (~700 lines)

## Gameplay

### Core Mechanic
4色のコインをテーブルに落とし、同色コインを隣接させてCOMBOを繋ぐ。コインは物理演算で押し合い、下端から押し出されたコインがスコアに。

**面白い瞬間**: 「詰まったコインの隙間に同じ色のコインを落とし、連鎖的に同色コインが押されて一気に複数枚が落下し、COMBOが4に達してSUPER DROPが発動する瞬間」

### リスクとリターン
- **同色隣接**: COMBO +1, HEAT -5 — 高スコアを狙うパス
- **色違い隣接**: COMBOリセット, HEAT +15 — リスク
- **SUPER DROP** (COMBO >= 4): 5秒間虹色、全色一致扱い、3倍スコア
- **OVERHEAT** (HEAT >= 100): 5秒間落下位置がランダムに揺れる

## Controls
- **Mouse X**: コイン落下位置（左右移動）
- **Left Click**: コインを落とす
- **KEY_RETURN**: タイトルからスタート / ゲームオーバーからリトライ

## Dev Status
- ✅ 単一ファイルmain.py (~700行)
- ✅ テスト56件 (test_imports.py)
- ✅ ruff/tyチェック通過
- ✅ Webビルド (138_coin_surge.html)
- ✅ 3画面 (TITLE / GAME / GAME_OVER)
- ✅ コイン物理演算（重力、衝突、押し出し）
- ✅ COMBOチェイン + SUPER DROP
- ✅ HEAT/OVERHEAT リスクシステム
- ✅ パーティクルエフェクト + スクリーンシェイク

## 体験仮説
「色を考えてコインを落とし、同色の連鎖的な押し出しでCOMBOが跳ね上がる瞬間に、『次の一手を見極めて高得点を稼いだ』という達成感が得られる」

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/138_coin_surge/main.py
```

## Test
```bash
uv run pytest prototypes/138_coin_surge/test_imports.py -v
```
