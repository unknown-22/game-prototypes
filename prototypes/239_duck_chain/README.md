# DUCK CHAIN (239)

Top-down Duck Duck Goose circle-chase game with color-match COMBO chain mechanics.

## Source
Reinterpreted from game_idea_factory #1 (Score 31.85): "合成で1枚に圧縮" → COMBO chain → SUPER GOOSE.

## Engine
- Pyxel 2.x, 320×240
- OpenCode CLI (opencode-go/deepseek-v4-pro) — first-try success

## Gameplay
Walk around a circle of 12 colored ducks. Tag matching ducks to build COMBO.
At COMBO >= 4, trigger GOOSE CHASE: race the tagged duck to its empty spot.
Reach the spot → SUPER GOOSE (rainbow mode, 3x score). Get caught → HEAT penalty.

## Controls
- LEFT/RIGHT: Walk around circle
- SPACE: Tag nearest duck
- CHASE phase: Arrow keys to run

## Core Loop
1. Walk → Position behind duck
2. Tag matching color → COMBO++
3. COMBO >= 4 → GOOSE CHASE!
4. Race to spot → SUPER GOOSE bonus
5. Repeat until 60s or HEAT >= 100

## Risk & Reward
- Chain matching ducks = high COMBO → SUPER GOOSE (3x)
- Mismatch or getting caught = COMBO reset + HEAT

## Difficulty
- Color cycle interval: 90f → 50f
- Duck color shuffle: 600f → 300f

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/239_duck_chain/main.py
```

## Tests
```bash
uv run pytest prototypes/239_duck_chain/tests/ -v
```

## Status
✅ Core loop complete (tag → combo → chase → super → repeat)
✅ 33 headless tests
✅ ruff + ty passing
✅ Web build deployed to docs/239_duck_chain.html
