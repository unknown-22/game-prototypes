# ROW SURGE (153_row_surge)

## 体験仮説
プレイヤーは「リズムに乗って同じ色のストロークを連続で決める緊張感と、COMBOが溜まってSUPER STROKEが爆発するカタルシス」を感じる。

## メカニクス仮説
- Mechanics: SPACEキーでストローク（漕ぐ）。ストローク色は20フレームごとに自動循環（RED→GREEN→BLUE→YELLOW）。同色連続ストロークでCOMBO構築、色違いでCOMBOリセット+HEAT上昇
- Dynamics: 同色を待つか（安全にCOMBOを伸ばす）、色を気にせず漕ぐか（タイムロス回避）の駆け引き。ウェイクトレイルのECHOボーナス狙いで位置取りの判断。CA伝播する障害物の回避
- Aesthetics: COMBO≧4でSUPER STROKE発動→虹色グロー＋スコア3倍＋速度1.5倍の爆発的爽快感

## 実装したコアループ
1. SPACEで漕ぐ → 同色連続でCOMBO上昇
2. COMBO≧4でSUPER STROKE発動（5秒間）
3. ウェイクトレイルを横切ってECHOボーナス（+50%スコア）
4. 水上障害物（CA伝播で増殖）を回避
5. HEAT≧100または60秒経過でGAME OVER

## うまくいっている点
- リズムゲーム的な操作感と色判断の駆け引き
- ECHOシステムで位置取りに意味がある
- CA障害物伝播が徐々にプレッシャーを高める
- SUPER STROKEの爆発的フィードバック

## 次に改善するなら最初に触る点
- カラーパレットの視認性（水上で色を見分けやすく）
- 難度カーブの調整（障害物の出現頻度と速度）
- サウンドエフェクトの追加

## 操作
- SPACE: ストローク（漕ぐ）
- 自動で色が循環するので、狙った色でSPACEを押す

## 実行方法
```bash
cd ~/repos/game-prototypes
uv run python prototypes/153_row_surge/main.py
```

## ソースアイデア
Game Idea Factory #1 (Score 32.55) — デッキ構築ローグライト/ハッキングの
「ログ/リプレイが資産」→ ウェイクトレイルECHOシステム
「盤面がセルオートマトンで埋まっていく」→ 障害物CA伝播
をローイング（ボート競技）に再解釈

## 技術
- Engine: Pyxel 2.x, 320×240, display_scale=2
- Python 3.12+, 型ヒント付き
- Phase machine: TITLE → PLAYING → GAME_OVER
- Headless tests: 54 tests, Game.__new__ bypass pattern
