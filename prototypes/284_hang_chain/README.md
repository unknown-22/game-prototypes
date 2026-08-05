# HANG CHAIN — Color-Match Hangman (284_hang_chain)

## Source
Reinterpreted from game_idea_factory dice/bag roguelite idea #1 (Score 32.2):
- "log/replay as asset (previous actions become next cards)" → previously guessed letters displayed as reference bar
- "chain collapse/expansion/compression UI" → same-color COMBO chain → SUPER SOLVE

## Engine
- Pyxel 2.x, 320×240, 30fps
- Keyboard-only input (A-Z + ENTER)

## Core Mechanic
Hangman word-guessing with color-match COMBO chain.
- Each letter position in the hidden word has a random color (RED/LIME/DARK_BLUE/YELLOW)
- Correct guess reveals the letter. If its color matches the PREVIOUS correct guess → COMBO builds
- COMBO >= 4 → **SUPER SOLVE**: auto-reveals letters every 60f, 3x score, rainbow mode, 10 seconds
- Wrong guess → HEAT +15, combo reset
- HEAT >= 100 → game over
- 60s timer

## 一番面白い瞬間
COMBOを4以上まで積み上げてSUPER SOLVEを発動し、単語全体が一気に自動開示される爽快感。

## リスクとリターン
- 同色COMBO継続 → 高スコア + SUPER SOLVEの高報酬
- ミスマッチ → COMBOリセット + HEAT急増（+15）
- SUPER SOLVE中は全色マッチで安全だが、終了後にCOMBOがリセットされる

## Controls
- A-Z: guess letter
- ENTER/RETURN: start game (from title) / restart (from game over)

## Dev Status
- ✅ Core gameplay loop (guess → reveal → combo → super solve)
- ✅ 52 headless tests
- ✅ Three screens (Title / Playing / Game Over)
- ✅ Hangman figure, particle effects, floating text
- ✅ Web build (docs/284_hang_chain.html)
- ✅ ruff + ty clean

## 体験仮説
「推理で正解を積み重ね、同じ色が連続した時にCOMBOが加速し、ついにSUPER SOLVEで一気に解ける快感」が生まれる。

## 次に改善するなら
- 難易度設定（単語長さの範囲調整）
- カテゴリ別単語プール（動物、食べ物など）
- ヒント機能（1文字だけ無償開示）

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/284_hang_chain/main.py
```
