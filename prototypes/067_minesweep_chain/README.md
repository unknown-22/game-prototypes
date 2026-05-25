# MINESWEEP CHAIN — Prototype 067

**Source**: Reinterpreted from game_idea_factory idea #1 (Score 32.0)
- Original: デッキ構築ローグライト / 宇宙採掘（リソース変換）
- Hooks: "synthesis compression" + "chain collapse UI" + "space mining"
- Reinterpretation: First minesweeper-like deduction puzzle in the collection

**Engine**: Pyxel 2.x, 320×240, display_scale=2

## Gameplay

A Minesweeper-like deduction puzzle with color-matching combo chains.

- **Grid**: 10×8 cells on an asteroid surface
- **Goal**: Reveal all 12 colored ore cells before the 90-second timer runs out
- **Left click**: Reveal a cell
- **Right click**: Flag/unflag a suspected mine cell
- **Mine**: Game over immediately
- **Ore**: Shows color (RED/BLUE/GREEN/YELLOW), adds to combo
- **Empty**: Shows multi-color numbers indicating adjacent ore counts per color
- **COMBO**: Consecutive same-color ore reveals increment the combo counter
- **SYNTHESIS**: When COMBO ≥ 3, triggers a BFS chain reaction that auto-reveals all adjacent same-color ore cells
- **Score**: 10 × combo level per ore revealed

## Core Mechanic

"同じ色の鉱石を推理で連続発見し、COMBOが3に達した瞬間SYNTHESISで隣接する同色鉱石が連鎖的に自動解放されるカタルシス"

The best moment: deducing and revealing same-color ore consecutively, then at COMBO=3 watching SYNTHESIS cascade through adjacent same-color ore in a satisfying BFS chain reaction.

## Risk/Reward

- Chase same-color combos for explosive SYNTHESIS bursts (high risk, high reward)
- Play safe with mixed colors (low score, but safer from mines)
- Spend time flagging mines (safer but costs timer)
- SYNTHESIS requires 3 consecutive same-color — one wrong click resets the counter

## Controls

| Input | Action |
|-------|--------|
| Left Click | Reveal cell |
| Right Click | Flag/Unflag cell |
| SPACE | Start game / Restart |

## Dev Status

- ✅ Core deduction mechanic
- ✅ 4-color ore system with combo chain
- ✅ BFS SYNTHESIS chain reaction
- ✅ Multi-color number clues on empty cells
- ✅ Mine detection (game over)
- ✅ Flag system
- ✅ 90-second timer
- ✅ Particle effects + floating score text
- ✅ Screen shake on mine hit
- ✅ Flash effect on synthesis
- ✅ Win condition (all 12 ores revealed)
- ✅ Title / Game / Game Over screens
- ✅ Headless logic tests (40 tests)
- ✅ ruff + ty clean

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/067_minesweep_chain/main.py
```

```bash
# Headless tests
uv run python prototypes/067_minesweep_chain/test_imports.py
```
