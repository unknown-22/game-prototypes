# DODGE CHAIN (134_dodge_chain)

トップダウンドッジボールアリーナ × 色合わせCOMBOチェイン

## 体験仮説
敵の投球をギリギリで回避してエコー軌跡を回収し、一気に強化されたSUPER THROWで敵全員を吹き飛ばす瞬間が面白い。

## 遊びの核（コアループ）
1. WASDで移動、マウス照準＋クリックで4色ボールを投げる
2. 同色の相手に連続命中 → COMBO上昇
3. COMBO≥5で SUPER THROW 発動（5秒間虹色全自動命中、スコア3倍）
4. 敵の投球をギリギリ回避 → エコー軌跡が出現 → 回収でスタミナ回復＋次投球ダメージ2倍
5. 被弾でHEAT蓄積、HEAT≥100 または時間切れでゲームオーバー
6. 90秒間で最大スコアを目指す

## 操作
- WASD / 矢印キー: 移動
- マウス: 照準
- 左クリック: 投球
- マウスホイール: 色変更（2秒ごとに自動変更も）
- ENTER / クリック: タイトル・リトライ

## リスクとリターン
- 相手に近づく → 命中しやすいが回避しにくい（ハイリスク・ハイリターン）
- エコー軌跡を回収するために回避位置へ移動 → 危険だが次の投球が超強化
- COMBO継続でSUPER THROWの高報酬、色ミスでCOMBOリセット

## 面白い瞬間
敵の投球をギリギリで回避 → エコー回収 → SUPER THROW発動 → 虹色ボール連発で相手を一掃 → スコア爆発

## ソース
- 元アイデア: game_idea_factory #1 (Score 32.2, 発電所/過負荷と放電)
- フック再解釈: ログ/リプレイが資産 → 回避位置がエコー軌跡に
- フック再解釈: UI連鎖演出 → COMBO連鎖＋SUPER THROW爆発

## 技術
- Pyxel 2.x, 320×240, display_scale=2
- Phase: TITLE → PLAYING → GAME_OVER
- データクラス: Player, Opponent, Ball, EchoTrail, Particle, FloatingText
- 4色 (RED, GREEN, LIGHT_BLUE, YELLOW)
- 85 headless tests

## 開発ステータス
- ✅ タイトル画面
- ✅ ゲーム画面
- ✅ ゲームオーバー画面
- ✅ 4色投球＋COMBOチェイン
- ✅ SUPER THROW (COMBO≥5)
- ✅ エコー軌跡（回避→回収→強化）
- ✅ HEATリスクシステム
- ✅ 難易度スケーリング（時間経過）
- ✅ パーティクル＋フローティングテキスト
- ✅ 画面揺れ
- ✅ 85 headless tests

## 実行方法
```bash
cd ~/repos/game-prototypes
uv run python prototypes/134_dodge_chain/main.py
```

## 次に改善するなら
- 複数相手の同時回避によるマルチECHOチェイン
- キャッチ（ボール受け止め）メカニクス
- サウンドエフェクト
