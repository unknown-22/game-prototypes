# PAIR CHAIN — Color-Match Concentration Memory Game

**Source**: game_idea_factory #1 (Score 32.35) — "魔法学院（ルール改変）" reinterpreted
- "synthesis compression" → matching two cards = synthesis
- "CA grid spread/control" → chain reveal auto-flip propagation

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- Single-file: `main.py` (543 lines)
- Headless tests: `test_imports.py` (47 tests)

## Gameplay
6×6 grid concentration (memory match) card game with color-match COMBO chain reactions.

**Core mechanic**: Flip two face-down cards per turn. Same color = MATCH + COMBO. COMBO ≥ 3 triggers CHAIN REVEAL: BFS auto-flips adjacent face-down cards — matching colors stay, non-matching flip back.

**Most fun moment**: 「同色カードを連続で引き当て、CHAIN REVEALで盤面の同色カードが次々と自動めくれていく連鎖の快感」

**Risk/reward**: Commit to same-color chains for COMBO multipliers vs. safe diverse clicking. WILD cards (rainbow) match any color.

## Controls
- Mouse click: Flip cards
- SPACE/ENTER: Start from title
- R: Restart from game over

## Card Reference
| Color | Pyxel | Pairs | Cards |
|-------|-------|-------|-------|
| RED | 8 | 4 | 8 |
| GREEN | 3 | 4 | 8 |
| DARK_BLUE | 5 | 4 | 8 |
| YELLOW | 10 | 4 | 8 |
| WILD (PEACH) | 15 | 2 | 4 |
| **Total** | | **18** | **36** |

## Scoring
- Match: 100 × combo multiplier
- Chain reveal bonus: 50 per auto-match
- All clear bonus: +500
- 90-second timer

## Dev Status
- ✅ Grid + card data model
- ✅ Flip-first / flip-second phase machine
- ✅ Same-color match & miss detection
- ✅ WILD card matching
- ✅ COMBO tracking + max_combo
- ✅ BFS chain reveal at combo ≥ 3
- ✅ Particle effects
- ✅ Title screen (instructions)
- ✅ Game over screen (score, max combo, pairs)
- ✅ HUD (score, timer, combo)
- ✅ Timer countdown + game over
- ✅ All-clear victory detection
- ✅ Headless tests (47 pass)
- ✅ Web build (docs/072_pair_chain.html)
- ⬜ Sound effects

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/072_pair_chain/main.py
```

## Testing
```bash
uv run pytest prototypes/072_pair_chain/test_imports.py -v
```
