# GRIP CHAIN (292)

**Rock Climbing × Color-Match COMBO Chain**

## 体験仮説 (Experience Hypothesis)
「壁面に自分のクライミング履歴が残り、次の一手を考えさせられる」— ホールドを掴むたびに壁の色が変わり、自分の軌跡（ログ）が次の判断材料になる面白さ。

## 実装したコアループ
1. 矢印キーで8×10グリッド上のホールド間を移動
2. 移動先のホールド色と自分の色が一致 → COMBO+1、スコア加算、ホールド色が自分の色に変化
3. COMBO>=4 → SUPER GRIP (300f レインボーモード、全色一致、3xスコア)
4. 色不一致 → HEAT+15、COMBOリセット
5. HEAT>=100 またはタイマー0 → ゲームオーバー
6. 60秒間のスコアを競う

## うまくいっている点
- ログ/リプレイの資産化：「掴んだホールドの色変化」がクライミング履歴として可視化される
- COMBO chain → SUPER GRIP の気持ちよさ
- HEATリスクとCOMBOリターンのバランス
- 難度上昇（色巡回速度、ホールド再出現速度）

## 次に改善するなら最初に触る点
- 壁面の自動スクロール（上方向）を追加して「登っている」感を強化
- 特殊ホールド（ボーナス、トラップ）の追加
- 複数ルートの選択肢（左ルート/右ルートでリスク差）

## 操作方法
- 矢印キー: カーソル移動
- ENTER: タイトル→開始 / ゲームオーバー→再挑戦

## 実行方法
```bash
cd ~/repos/game-prototypes
uv run python prototypes/292_grip_chain/main.py
```

## Build
```bash
uv run pyxel package prototypes/292_grip_chain prototypes/292_grip_chain/main.py
uv run pyxel app2html 292_grip_chain.pyxapp
```

## Source
- Game Idea Factory #1 (Score 32.2): 魔法学院ダイス/バッグ構築ローグライト
  - Hook 1: ログ/リプレイが資産 → 壁面に掴んだホールドの色が残る
  - Hook 2: UI連鎖演出 → COMBO chain + SUPER GRIP
- Engine: Pyxel 2.x, 320×240, 30fps
- Tests: 77 headless tests (pytest, ruff, ty)
- Coding: OpenCode CLI (opencode-go/deepseek-v4-pro), first-try success, 18 self-corrections
