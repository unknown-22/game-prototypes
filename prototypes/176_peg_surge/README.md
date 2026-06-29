# PEG SURGE — Color-Match Peg Solitaire

## Source
Reinterpreted from Game Idea Factory Idea #1 (Score 32.0, 2026-06-29):
- Original: Deckbuilder roguelite / Power plant — "effects synthesized into one card" + "numbers split into multiple paths, converge to explode"
- Reinterpretation: Same-color COMBO chain compression (= synthesis), multi-jump chains split across board (= split paths), COMBO>=4 converge into SUPER JUMP (= explode)

## Experience Hypothesis (体験仮説)
「同色ペグを連続で飛び越えてCOMBOを積み上げ、SUPER JUMPが炸裂した瞬間に圧倒的気持ち良さを感じる」

## Core Loop
1. Click a peg to select it
2. Click an empty hole 2 cells away (orthogonal) to jump
3. The middle peg is captured — color match determines COMBO/HEAT
4. Same peg can chain-jump (multi-jump)
5. COMBO >= 4 triggers SUPER JUMP (rainbow, 5s, 3x score)
6. Repeat until no moves or HEAT >= 100

## Controls
- Mouse click: select peg / execute jump
- ENTER: start / restart
- R: restart
- ESC: quit

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- 7×7 English peg solitaire cross board (33 valid cells)
- 32 colored pegs (RED/GREEN/DARK_BLUE/YELLOW, 8 each)

## Dev Status
- ✅ Core peg solitaire mechanics
- ✅ COMBO chain system
- ✅ SUPER JUMP mode
- ✅ HEAT risk system
- ✅ Particle effects
- ✅ Floating text feedback
- ✅ Screen shake on SUPER activation
- ✅ 3 screens (Title/Playing/GameOver)
- ✅ 52 headless tests
- ✅ Web build (docs/176_peg_surge.html)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/176_peg_surge/main.py
```
