# 168_magnet_chain — MAGNET CHAIN

**Source**: Game Idea Factory Idea #1 (Score 31.75) — 錬金術デッキ構築の「同カード連続使用で変質」+「CAグリッド拡散」を磁石パズルに再解釈

**Engine**: Pyxel 2.x, 320×240, display_scale=2

## 体験仮説
「同色の磁石を連続配置してCOMBOを積み上げ、SUPER FIELDが発動して全磁石が虹色に輝き、スコアが3倍に跳ね上がる爆発的な気持ちよさ」

## コアループ
1. カラーパレットから色を選ぶ（クリック or SPACE）
2. 8×6グリッドの空セルをクリックして磁石を配置
3. 同色連続配置 → COMBO上昇（スコア倍率アップ）
4. COMBO≥4 → SUPER FIELD発動（5秒間虹色、スコア3倍、毎フレーム磁場伝播）
5. 色ミスマッチ → COMBOリセット + HEAT上昇
6. HEAT≥200 → ゲームオーバー
7. 60秒制限時間でスコア最大化を目指す

## 操作方法
- **クリック**: グリッドの空セルに磁石を配置／カラーパレットで色選択
- **SPACE**: アクティブカラーを切り替え
- **Z / ENTER**: タイトルでゲーム開始／ゲームオーバーでリスタート

## メカニクス
- **N/S極性**: 磁石は極性が交互に割り当てられる（N→S→N...）
- **磁力**: 同色・同極 → 反発（field_strength増加）、同色・異極 → 引き合い（field_strength平均化）
- **CA磁場伝播**: 15フレームごとに磁場が4方向隣接セルに拡散（SUPER中は毎フレーム2段階拡散）
- **HEAT不安定化**: HEAT≥100で極性がランダム反転する可能性
- **画面揺れ**: SUPER発動時に10フレーム

## リスクとリターン
- 同色COMBO維持 → 高いスコア倍率とSUPER FIELDへの道
- 色を切り替える → COMBOリセット + HEAT蓄積
- SUPER FIELD中は超強化だが、後のHEAT管理が難しくなる

## Dev Status
- ✅ コアメカニクス（磁石配置、COMBOチェイン）
- ✅ SUPER FIELD（虹色モード、スコア3倍）
- ✅ N/S極性システム + 磁力計算
- ✅ CA磁場伝播
- ✅ HEATリスクシステム（不安定化 + ゲームオーバー）
- ✅ パーティクルシステム + フローティングテキスト
- ✅ 3画面（Title/Placing/GameOver）
- ✅ 46 headless tests
- ⬜ README執筆 ← done
- ✅ ruff/tyチェック合格

## 実行方法
```bash
cd ~/repos/game-prototypes
uv run python prototypes/168_magnet_chain/main.py
```

## テスト
```bash
uv run python prototypes/168_magnet_chain/test_imports.py
# 46 passed, 0 failed
```
