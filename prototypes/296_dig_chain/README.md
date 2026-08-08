# DIG CHAIN — Archaeology Excavation

## Source
Game Idea Factory #1 (Score 32.2): Magic academy dice/bag roguelite.
Reinterpreted hooks: "log/replay as asset" → excavation history grid, "chain collapse/expansion/compression UI" → same-color COMBO chain → SUPER EXCAVATION.

## Engine
Pyxel 2.x, 320×240, 30fps

## Gameplay — Core Mechanic
Click cells on an 8×6 grid to excavate. Each cell has one of 4 dirt colors (RED/LIME/CYAN/YELLOW). Same-color consecutive digs build COMBO (score=10×combo). COMBO≥4 triggers SUPER EXCAVATION (300f: rainbow mode, any-color match, 3× score, nearby fossil hints). HEAT risk: wrong-color digs add 15 heat (cap 100 → game over). 60s timer. ~15% cells have hidden fossil bonus (+50).

### The Fun Moment
"同じ色の地層を連続で掘り当ててCOMBOが4以上になり、SUPER EXCAVATIONが発動して広範囲が虹色に光り、次々と化石ボーナスが出現してスコアが爆発する瞬間"

## Controls
- Mouse: Click grid cells to excavate
- ENTER/RETURN: Start game / Restart
- R: Restart

## Risk & Reward
- Same-color chain → high combo score + SUPER EXCAVATION
- Wrong color → combo reset + HEAT+15
- SUPER mode → any color matches, 3× score
- Fossil bonus cells → extra +50 score

## Dev Status
- [x] Core excavation mechanic
- [x] COMBO chain system
- [x] SUPER EXCAVATION mode
- [x] HEAT risk system
- [x] Timer countdown
- [x] Fossil bonus system
- [x] Particle effects
- [x] Floating text feedback
- [x] Screen shake
- [x] 3 screens (Title/Playing/GameOver)
- [x] 70 headless tests
- [x] ruff + ty OK
- [x] Web build deployed to docs/

## Hypotheses
- **Experience hypothesis**: "危険な発掘（色違いの地層）を避けて同色を連続で掘り当てる緊張感と、COMBOが繋がってSUPER EXCAVATIONに入ったときの解放感と爆発的なスコア獲得の気持ちよさ"
- **Mechanic hypothesis**: Same-color consecutive click constraint (Mechanics) → player scans grid for same-color paths (Dynamics) → tension of wrong-color risk vs. combo reward (Aesthetics)

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/296_dig_chain/main.py
```

## How to Test
```bash
uv run pytest prototypes/296_dig_chain/test_imports.py -v
```
