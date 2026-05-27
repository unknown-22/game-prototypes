# CHAIN CLIMB (074)

Vertical climbing game with color-match COMBO chain. Reinterpreted from deckbuilder idea #1 (Score 32.35).

## Concept

Doodle Jump-style vertical climber. Jump on colored platforms to climb higher. Landing on the **same color** as your previous landing builds a COMBO chain. COMBO x3 triggers **SYNTHESIS** — a super jump mode with 3x score and visual flash.

## Most Fun Moment

> 同色プラットフォームを狙ってCOMBOを積み、SYNTHESISで画面が光り一気に高く跳び上がるカタルシス

## Risk/Reward

- **Chase same-color** → high COMBO + score, but the platform may be far away (risk of falling)
- **Safe landing** → nearby different-color platform is safe, but COMBO resets

## Controls

| Key | Action |
|-----|--------|
| ← → / A D | Move left/right |
| ENTER / SPACE | Start game / Restart |

## Mechanics

- 4 platform colors: RED, GREEN, DARK_BLUE, YELLOW
- Same-color consecutive landing → COMBO +1, score = BASE + COMBO × BONUS
- Different color landing → COMBO resets to 1, score = BASE only
- COMBO ≥ 3 → SYNTHESIS (60 frames): super jump, 3x score, particles ×2
- SYNTHESIS overrides wrong-color reset — all landings extend combo
- Camera scrolls upward continuously (speed increases with score)
- Player wraps at left/right screen edges
- Fall off bottom = GAME OVER

## Scoring

- Base score per landing: 10
- Combo bonus: 15 per combo level
- SYNTHESIS multiplier: 3×
- Score formula: `(10 + combo × 15) × (3 if SYNTHESIS else 1)`

## Phase Machine

```
TITLE → (ENTER/SPACE) → PLAYING → (fall death) → GAME_OVER → (ENTER/SPACE) → TITLE
```

## Dev Status

- ✅ Core gameplay (climbing, combo, synthesis)
- ✅ 4-color platform system
- ✅ SYNTHESIS super mode with visual effects
- ✅ Particle system
- ✅ Title / Game / Game Over screens
- ✅ HUD (score, combo, speed, synthesis timer bar)
- ✅ Progressive difficulty (scroll speed increases)
- ✅ 44 headless tests
- ✅ ruff + ty clean

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/074_chain_climb/main.py
```

## Tech

- Engine: Pyxel 2.x, 320×240, display_scale=2
- Language: Python 3.12+ with type hints
- Source: 534 lines single-file
- Test: `uv run python prototypes/074_chain_climb/test_imports.py`

## Source

Generated from game_idea_factory (2026-05-27, Score 32.35): deckbuilder roguelite with synthesis compression + circuit/pipe visualization hooks, reinterpreted as vertical climbing game — the **first vertical climber** in the collection.

## Design Hypothesis

- **Experience**: "上昇速度が上がる中で同色プラットフォームを連続で選び抜き、COMBOが3に達してSYNTHESISのスーパージャンプで一気に高得点を稼ぐ瞬間が面白い"
- **Mechanics → Dynamics**: Color-match constraint → risk/reward platform selection → SYNTHESIS power spike → score multiplication
- **Verification**: 30s play reaches COMBO 3+, SYNTHESIS triggers with visible flash/super jump
