# YOYO CHAIN — 215_yoyo_chain

## 体験仮説
ヨーヨーの上下運動の物理に合わせて同じ色を連続キャッチし、SUPER YOYOが発動して虹色に輝く瞬間に「溜めて爆発させる」快感を得られる。

## 実装したコアループ
- **ヨーヨー物理**: ストリングの先でGravity落下 → 底でバウンド → 戻ってくる連続ループ
- **色合わせCOMBO**: 同色連続SPACEキャッチでCOMBOが加速、スコア倍率上昇
- **SUPER YOYO**: COMBO>=4で発動（5秒間虹色、3xスコア、自動キャッチ）
- **HEATリスク**: 色違いキャッチでHEAT+15、ミスでHEAT+5。HEAT>=100でゲームオーバー
- **60秒タイマー**: 時間切れでゲームオーバー

## 操作方法
- TITLE: SPACE または ENTER で開始
- PLAYING: SPACE でヨーヨーキャッチ（手元に戻ったタイミング）
- GAME OVER: SPACE または ENTER でリトライ

## うまくいっている点
- シンプルなワンボタン操作でテンポよくプレイできる
- ヨーヨーの物理（落下→バウンド→上昇）が直感的
- SUPER YOYO発動時の虹色パーティクルとスコア爆発が気持ちいい
- 同色待ち（COMBO維持）vs 早めキャッチ（HEAT回避）のリスク/リターンが機能している

## 次に改善するなら最初に触る点
- 難易度上昇（時間経過で色サイクル高速化、キャッチウィンドウ縮小）
- エコーゴースト軌跡（前回成功時の軌跡を表示してガイドにする）
- サウンドエフェクト（キャッチ音、SUPER発動音、ミス音）

## Source
- game_idea_factory 生成: 2026-07-09, 全10件がdeckbuilder/dice/auto-shooter → Idea #1 (Score 32.0) の「合成圧縮＋チェイン可視化」フックをヨーヨーに再解釈
- Engine: Pyxel 2.x, 320x240, 60fps
- 初のヨーヨージャンル

## How to run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/215_yoyo_chain/main.py
```
