# MOLE CHAIN — Color-match Whack-a-Mole

**Prototype 054** — Reinterpreted from [game_idea_factory](https://github.com/unknown-22/game_idea_factory) idea #1 (Score 31.45).

## Reinterpretation

All 10 generated ideas (2026-05-23) clustered in deckbuilder/dice/auto-shooter genres.
Idea #1 hooks were reinterpreted into a **Whack-a-Mole** game — a genre missing from the collection.

| Hook (original) | Reinterpreted as |
|---|---|
| Log/replay as asset | Echo ghosts of previous whacks guide next hits |
| One-color-per-turn | Only same-color consecutive whacks build COMBO chain |

## One-sentence Fun

**Rhythmically whacking same-colored moles as the COMBO multiplier accelerates ×2, ×3, ×4 — score explodes.**

## Engine

- **Pyxel 2.x**, 256×256, `display_scale=2`, 30 FPS
- Python 3.12+, type hints, ruff/ty quality checks

## Gameplay

- **4×3 grid** of holes. Colorful moles pop up randomly.
- **Click matching-color moles** consecutively to build COMBO chain.
- **Wrong color click** → COMBO breaks to 0.
- **Click empty hole** → COMBO breaks.
- **COMBO ≥ 4** → triggers **SUPER** mode: all visible moles auto-whacked for 2× bonus!
- **Echo ghosts** (log replay) mark your previous whacks — they fade slowly.
- **60-second timer**. Difficulty ramps: more moles, faster pop-ups.

## Colors

| # | Name | Pyxel Constant | Hex |
|---|---|---|---|
| 0 | RED | `COLOR_RED` (8) | #FF0000 |
| 1 | GREEN | `COLOR_GREEN` (11) | #00FF00 |
| 2 | YELLOW | `COLOR_YELLOW` (10) | #FFFF00 |
| 3 | CYAN | `COLOR_CYAN` (12) | #00FFFF |

## Controls

| Input | Action |
|---|---|
| Mouse click | Whack mole (click matching color for COMBO) |
| Enter / Click | Restart (on game over screen) |

## Scoring

- **Base whack**: 100 pts × combo multiplier
- **SUPER whack**: 200 pts × combo multiplier
- Combo multiplier: `1.0 + (combo − 1) × 0.5` (1.0×, 1.5×, 2.0×, 2.5×, ...)

## Risk/Reward

- **Safe**: click any mole, reset combo. Low score.
- **Risky**: wait for same-color moles. High combo = big score, but risk of timeout.
- **Greed**: hold combo for SUPER trigger at the risk of missing.

## Dev Status

- ✅ Core mechanic: color-match whack with COMBO chain
- ✅ SUPER mode: auto-whack all visible moles
- ✅ Echo ghost system (log/replay as asset)
- ✅ Particle effects + floating score text
- ✅ Screen shake on SUPER
- ✅ Difficulty scaling (more moles, faster over time)
- ✅ Game over screen with stats
- ✅ Headless logic tests
- ⬜ Sound effects
- ⬜ Mole variety (speed, double-score, bomb moles)

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/054_mole_chain/main.py
```

## Headless Tests

```bash
cd ~/repos/game-prototypes
uv run python prototypes/054_mole_chain/test_imports.py
```
