# Seesaw Chain (135)

色合わせCOMBOチェインを組み合わせたシーソーバランスパズル。

## Source
- **game_idea_factory #1** (Score 31.65): ヴァンサバ亜種×魔法学院ルール改変
- **Reinterpretation**: 「合成圧縮」→ 同色連続COMBO、「未来の手札を消費」→ 次色プリコミット
- Genre gap: 全134プロトタイプ中初の**物理バランスパズル**（シーソー/トルク力学）

## 体験仮説
「不安定なバランスの中で同色の重りを狙い続ける緊張と、SUPER BALANCEが発動して一気に安定する解放感」

## Engine
- Pyxel 2.x, 320×240
- Python 3.12+

## Gameplay

### Core Mechanic
シーソーのビームに色付きの重りを置いていく。同色を連続で置くとCOMBOが上昇し、COMBO >= 4でSUPER BALANCE（虹色、3倍スコア、自動安定化）が発動する。

### 操作
| 操作 | 効果 |
|------|------|
| マウス左クリック（画面左半分） | 左側に重りを配置 |
| マウス左クリック（画面右半分） | 右側に重りを配置 |
| マウスホイール | 色切替（赤・緑・青・黄） |
| 下部の色ボタンクリック | 色選択 |
| 右クリック | 次色にコミット（1.5倍ボーナス） |
| SPACE | タイトルから開始 |
| R | ゲームオーバーから再挑戦 |

### リスクとリターン
- **同色COMBO継続** → 高倍率スコア + SUPER BALANCE発動の高報酬
- **色切替え** → COMBOリセット + HEAT蓄積（+15）
- **次色コミット** → 成功で1.5倍、失敗でHEAT+10
- **重い重り** → 高スコアだが傾きやすい

### ゲームオーバー条件
1. ビームの傾きが30°を超える
2. HEATが100に達する
3. 90秒の制限時間切れ

## Dev Status
- ✅ コアメカニクス（色配置 + COMBO + SUPER BALANCE）
- ✅ シーソー物理（トルク計算 + 角度制限）
- ✅ コミットメントメカニクス（次色プレビュー + ボーナス/ペナルティ）
- ✅ HEATリスクシステム
- ✅ パーティクル/フローティングテキスト演出
- ✅ 3画面（タイトル / ゲーム / ゲームオーバー）
- ✅ 55 headless tests（全通過）
- ⬜ Webビルド完成

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/135_seesaw_chain/main.py
```

## Tests
```bash
uv run pytest prototypes/135_seesaw_chain/test_imports.py -v
```
