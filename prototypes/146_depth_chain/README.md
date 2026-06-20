# DEPTH CHAIN

**Free-diving pearl collection game — 初の素潜り（アプネアダイビング）プロトタイプ**

## 体験仮説

「深海の闇と酸素の制約の中で、同色の真珠を見極めて連続回収し、COMBOを積み上げて SUPER BREATH を発動させた瞬間に、息を止めていた緊張から一気に解放されるカタルシスを感じる」

## メカニクス仮説

- **Mechanics**: 4色の真珠が降ってくる中、同色連続回収で COMBO チェイン構築。COMBO >= 4 で SUPER BREATH 発動
- **Dynamics**: 色を見極める判断、深く潜るリスク（深度倍率 vs 酸素消費）、SPACE浮上 vs 自然降下の選択
- **Aesthetics**: 窒息寸前の緊張 → SUPER BREATH 爆発的スコア獲得のカタルシス → 次の COMBO を狙う中毒性

## 実装したコアループ

1. ダイバーが自動降下、左右キーで移動、SPACE で浮上
2. 画面上部から4色の真珠が降ってくる
3. 同色真珠に接触 → COMBO +1、スコア加算（深度倍率あり）
4. 色違い真珠に接触 → COMBO リセット + HEAT +15
5. COMBO >= 4 → SUPER BREATH（5秒間虹色、全真珠自動回収、スコア3倍、酸素補充）
6. 酸素ゼロ or HEAT >= 100 → GAME OVER
7. 海底から闇（水圧）が上昇、闇の中では酸素消費4倍

## 面白い瞬間

COMBO 4 で SUPER BREATH が発動し、虹色ダイバーが周囲の全真珠を自動回収してスコアが爆発する瞬間

## リスクとリターン

| 選択 | リスク | リターン |
|------|--------|----------|
| 深く潜る（自然降下） | 酸素消費増加、闇接近 | 深度倍率で高スコア |
| SPACE 浮上 | 酸素消費増加（1.7倍） | 闇から脱出、安全確保 |
| 同色 COMBO 継続 | 色選択を誤ると HEAT +15 | COMBO 倍率 + SUPER BREATH |
| 安全に色無視で回収 | COMBO 倍率なし | HEAT 増加なし |

## コントロール

- ← → または A/D: 左右移動
- SPACE: 浮上（酸素消費増加）
- ENTER: タイトルでスタート / ゲームオーバーでリトライ

## エンジン

- Pyxel 2.x, 320×240, display_scale=2
- Python 3.12

## 開発ステータス

- ✅ 3画面（タイトル / ゲーム / ゲームオーバー）
- ✅ 4色真珠 COMBO チェイン
- ✅ SUPER BREATH スーパーモード
- ✅ 酸素 + HEAT 二重リスクシステム
- ✅ 闇（水圧）上昇メカニクス
- ✅ 深度倍率スコア計算
- ✅ パーティクル + フローティングテキスト
- ✅ 65 headless tests (全PASS)
- ✅ ruff + ty チェッククリア
- ✅ Web ビルド (docs/146_depth_chain.html)

## 実行方法

```bash
cd ~/repos/game-prototypes
uv run python prototypes/146_depth_chain/main.py
```

## ソース

Game Idea Factory #1 (Score 32.75) より:
- 「合成圧縮」→ 同色 COMBO → SUPER BREATH
- 「CAグリッド増殖」→ 海底からの闇/水圧上昇

## 次に改善するなら

- 酸素タンクアイテム（回収で酸素回復）
- 敵（サメ/クラゲ）の追加
- 深度記録の永続化（ベスト深度）
- BGM/SE 追加
