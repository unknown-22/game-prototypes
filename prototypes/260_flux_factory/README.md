# FLUX FACTORY (260_flux_factory)

**Source:** game_idea_factory #1 (Score 31.95) — ハッキング（回路/ログ）Auto-shooter
**Reinterpreted hooks:** "synthesis compression" → same-color items combine at belt junctions; "circuit/pipe visualization" → conveyor belt grid with visible item flow

**Engine:** Pyxel 2.x, 320×240, 30fps

## 体験仮説

「色の異なるアイテムがベルト上を流れる中、ジャンクションに同色を誘導して合成コンボを発生させる時に、配置した自分の工場が上手く機能している喜びと、異色衝突のリスクを天秤にかける緊張感が生まれる」

## Core Mechanic

Colored items (RED, LIME, DARK_BLUE, YELLOW) flow on a 6×5 grid of conveyor belts. Click cells to cycle belt directions (N→E→S→W→JUNCTION→EMPTY). Same-color items meeting at a junction SYNTHESIZE (COMBO chain, score = 100 × combo). Different-color items collide → HEAT +15, COMBO reset. COMBO ≥ 4 triggers SUPER FLUX (10s rainbow mode, any-color synthesis, 3x score, HEAT frozen).

## Controls

| Input | Action |
|-------|--------|
| Mouse Left Click | Cycle cell direction forward |
| SPACE / RETURN | Start game / Restart |
| R | Restart anytime |

## Rules

- **Grid:** 6 columns × 5 rows, CELL = 40px
- **Item Flow:** Items enter from left edge, exit right for +10 points
- **Empty Cell:** Items lost, HEAT +5
- **Junction:** Items pause 10f before proceeding
- **Synthesis:** 2+ same-color items at same cell → COMBO++, score
- **Mismatch:** Different colors collide → HEAT +15, COMBO reset
- **SUPER FLUX:** COMBO ≥ 4 → 300f rainbow mode (any-color synthesis, 3x score, HEAT frozen)
- **HEAT ≥ 100:** Game Over
- **Timer:** 60 seconds
- **Escalation:** Spawn interval 60f → 30f, tick interval 30f → 15f over 60s

## Dev Status

- ✅ Core mechanic: conveyor belt routing with color-match synthesis
- ✅ Phase machine: Title → Playing → GameOver
- ✅ Particle system + floating text feedback
- ✅ SUPER FLUX rainbow mode
- ✅ HEAT risk system with decay
- ✅ Difficulty escalation
- ✅ 45 headless tests (all pass)
- ✅ ruff + ty clean
- ✅ Web build (docs/260_flux_factory.html)
- ⬜ JUNCTION output direction selection (currently fixed)
- ⬜ Belt cost system (limit total belt placements)

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/260_flux_factory/main.py

# Tests
uv run pytest prototypes/260_flux_factory/ -v

# Web version
open docs/260_flux_factory.html
```
