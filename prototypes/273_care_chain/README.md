# CARE CHAIN — Virtual Pet Care Game (Prototype #273)

## Source
Reinterpreted from game_idea_factory #1 (Score 32.75): 錬金術デッキ構築
Hooks: "合成圧縮" → same-action COMBO chain, "CA感染/増殖" → stat boundary spread
First **Virtual Pet / Tamagotchi** genre in the collection.

## 体験仮説
「同じケア行動を連続成功させてCOMBOを繋ぎ、ペットが一気にご機嫌になってSUPER MODEに進化する瞬間が面白い」

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single-file prototype (~640 lines)

## Core Loop
1. Click one of 4 colored action buttons: FEED (GRAY), PLAY (LIME), REST (CYAN), TRAIN (ORANGE)
2. Same-color consecutive clicks build COMBO chain (score multiplier increases)
3. Different-color click resets COMBO and causes screen shake
4. COMBO >= 4 activates SUPER MODE (300 frames, all effects 3x, pet evolves into rainbow form)
5. 4 stats (HAPPINESS, HUNGER, ENERGY, STRESS) respond to actions and decay over time
6. Stats hitting 0 or 100 trigger CA spread to adjacent stats
7. STRESS >= 100 or timer reaches 0 = GAME OVER

## Risk/Reward
- **Chase COMBO** → same-action chain yields high-score multiplier + SUPER MODE
- **Balance stats** → neglect causes CA spread cascade and stress explosion
- Core dilemma: greed for combo vs. survival through balanced care

## Controls
- Mouse click: select action button
- SPACE (Title): start game
- R (Game Over): restart

## Dev Status
- ✅ Single-file main.py with phase machine (TITLE/PLAYING/GAME_OVER)
- ✅ 4 action buttons with color-coded stats system
- ✅ COMBO chain + SUPER MODE (rainbow evolution, 3x effects)
- ✅ CA spread across stats at boundaries
- ✅ Pixel pet face with expressions
- ✅ Particle system + floating text + screen shake
- ✅ 78 headless tests, ruff + ty clean
- ✅ Web build deployed to docs/273_care_chain.html

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/273_care_chain/main.py
```

## How to Test
```bash
uv run pytest prototypes/273_care_chain/test_imports.py -v
```
