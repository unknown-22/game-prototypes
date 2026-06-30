# POKER SURGE — 5-Card Draw Poker COMBO Chain

**Prototype #180** | Idea #1 (Score 32.2) reinterpreting "log/replay as asset + chain collapse UI" hooks

## 体験仮説
「同じスートで連続勝利し、COMBOが4に達してSUPER HANDが炸裂し、5ハンド連続で虹色モードになって一気に大量チップを稼ぐ爆発的快感」

## 実装したコアループ
- 5-card draw poker: deal → hold cards → redraw (max 2) → dealer reveal → compare hands
- 4 suits = 4 colors: ♥=RED, ♣=GREEN, ♠=DARK_BLUE, ♦=YELLOW
- Same-suit consecutive WINS build COMBO chain (x1→x2→x3→x4...)
- COMBO>=4 triggers SUPER MODE: 5 hands of rainbow (any suit auto-wins, 3x score)
- HEAT from folding (+10) or losing (+15), decays 0.02/frame, cap 100 = GAME OVER
- Chip economy: start 100, bet 10/hand, poker hand multiplier for payouts
- Full poker hand evaluation: High Card through Royal Flush

## うまくいっている点
- Poker hand evaluation is pure logic, fully testable (58 headless tests)
- SUPER MODE creates exciting "run" feeling — stacking COMBO then exploding
- RISK/REWARD: chase same suit for COMBO vs switch colors for safety

## 次に改善するなら最初に触る点
- Add AI opponent with betting strategy (currently just reveal-and-compare)
- Add bluffing mechanic
- Add more betting options (raise, check)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/180_poker_surge/main.py
```

## Controls
- Mouse click: toggle HOLD on cards, click CONFIRM BET button
- SPACE: confirm bet, redraw, advance phases
- F: fold hand
- R: restart from game over
