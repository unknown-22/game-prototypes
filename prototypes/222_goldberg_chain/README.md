# Goldberg Chain (222)

Rube Goldberg chain-reaction machine builder. Place colored nodes on a grid to create chain reactions.

## Source
Reinterpreted from game_idea_factory batch 2026-07-11, Idea #1 (Score 31.65): 
Alchemy synthesis deckbuilder with "synthesis/compression" + "one-color-per-turn" hooks.

## 体験仮説
「2つの巨大な同色クラスターを橋渡しする最後のノードを置き、BFS連鎖がグリッド全体に波及して大爆発スコアを得る瞬間が面白い」

## Engine
- Pyxel 2.x, 320×240
- 10×8 grid, CELL=20
- 4 node colors: RED/LIME/DARK_BLUE/YELLOW

## Gameplay
1. **BUILD**: Select ONE color, click grid cells to place up to 3 nodes of that color
2. **REACT**: Press SPACE or click "GO" — BFS chain reaction propagates through adjacent same-color nodes
3. **RESOLVE**: Chains of ≥2 nodes score (10 × chain_size × (combo+1)), SUPER MODE gives 3×
4. **HEAT**: Switching colors +15, untriggered isolated nodes +5 each, decays 0.02/frame
5. **GAME OVER** at HEAT≥100 or 0s timer

## Controls
- Mouse click: place node on empty grid cell / select color in palette / click "GO"
- 1/2/3/4 keys: select color
- SPACE / ENTER: trigger reaction / advance / restart

## Core Loop
Select color → Place nodes → Trigger → Watch BFS cascade → Score + COMBO → Repeat until GAME OVER

## Risk/Reward
- Keep same color = COMBO multiplier grows (+1 per turn) → SUPER MODE at 5
- Switch color = COMBO resets → HEAT+15 (pipe jam)
- Untriggered isolated nodes = HEAT+5 each (wasted components)

## Features
- BFS chain detection (4-directional adjacency)
- Step-by-step BFS animation
- Particle burst + floating score text + screen shake (≥5 nodes)
- SUPER MODE at COMBO≥5 (300f rainbow, any-color chains, 3× score)
- Escalating difficulty (2 + turns/3 new nodes per turn)
- 3 screens: Title / Build-React / Game Over

## Dev Status
- ✅ Core BFS chain mechanics
- ✅ COMBO + SUPER MODE system
- ✅ HEAT risk/reward
- ✅ Particle + floating text effects
- ✅ Screen shake
- ✅ 35 headless tests
- ✅ Ruff + ty clean
- ⬜ Sound effects
- ⬜ Difficulty tuning

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/222_goldberg_chain/main.py

# Tests
uv run pytest prototypes/222_goldberg_chain/tests/ -v
```
