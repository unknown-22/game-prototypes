# BLACKJACK SURGE — Prototype 179

Color-match Blackjack with COMBO chain and HEAT risk system.

## 体験仮説
「同色の勝ちを連続で重ねてSUPER BLACKJACKが炸裂し、5ハンド連続で全色自動マッチ＋3倍スコアで一気にチップが跳ね上がる爆発的爽快感」

## 実装したコアループ
- 4色（赤/緑/紺/黄）からベットカラーを選ぶ
- HIT(SPACE)でカード追加、STAND(RETURN)で勝負
- 同色連続勝利でCOMBOチェイン構築
- COMBO>=4でSUPER BLACKJACK発動（5ハンドレインボーモード、3倍スコア）
- バストでHEAT+20、負けでHEAT+10、HEAT>=100でゲームオーバー
- チップが0でもゲームオーバー

## Controls
- 1/2/3/4 keys: select active color
- SPACE: HIT (draw card) / Start / Restart
- ENTER/RETURN: STAND
- Mouse click: color palette buttons

## Source
- Game Idea Factory #1 (Score 31.45): "ログ/リプレイが資産" + "1ターン1色だけ" 
- Reinterpreted into Blackjack casino genre (first in collection)

## Dev Status
- ✅ 3 screens (Title/Game/GameOver)
- ✅ 6-phase machine (TITLE/BETTING/PLAYING/STAND/RESOLVE/GAME_OVER)
- ✅ Soft ace handling, Blackjack 1.5x payout
- ✅ COMBO chain + SUPER BLACKJACK mode
- ✅ HEAT risk system with decay
- ✅ Chip system (100 chips, 10 bet)
- ✅ Particle + floating text systems
- ✅ 67 headless tests
- ✅ ruff clean, ty clean
- ⬜ Sound effects

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/179_blackjack_surge/main.py
```
