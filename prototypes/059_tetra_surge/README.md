# TETRA SURGE — Color-Match Tetris with Chain Reactions

**Prototype #059** | Genre: **Tetris-like rotation puzzle** (FIRST in collection)

## Source

Reinterpreted from game_idea_factory idea #1 (Score 32.0): "Numbers split into multiple paths and converge to explode."
- **Split** → tetromino pieces "split" across columns
- **Converge** → completing a row "converges" blocks  
- **Explosion** → BFS chain reaction "explodes" clearing adjacent same-color blocks

## Engine

- Pyxel 2.x, 320×240, display_scale=2
- Python 3.12 with dataclasses and type hints

## Gameplay — Core Mechanic

Standard Tetris with a color-matching twist:

1. **7 classic tetrominoes** in 4 colors: I(CYAN), O(YELLOW), T(PURPLE), S(GREEN), Z(RED), J(LIGHT_BLUE), L(ORANGE)
2. **FALL + ROTATE + PLACE** pieces using keyboard controls
3. When a row is **completely filled** → it clears with score
4. After clearing, **BFS chain reaction** propagates from cleared cells to adjacent same-color blocks (4-dir), clearing them for multiplying combo
5. **COMBO >= 5** → next piece is a **SURGE rainbow bomb** that erases a 5×5 area
6. Game over when new piece can't spawn

## Controls

| Key | Action |
|-----|--------|
| LEFT/RIGHT | Move piece |
| UP | Rotate clockwise (SRS wall kicks) |
| DOWN | Soft drop (accelerated) |
| SPACE | Hard drop (instant) |
| ENTER | Start / Restart |

## Risk & Reward

- **Risk**: clearing a row triggers BFS that might clear valuable same-color stacks needed for building combos; SURGE bomb might clear too much
- **Reward**: higher combos give exponentially better scores; SURGE bomb enables massive chain clears
- **Risk/Reward tension**: delay placing a piece to let same-color blocks accumulate adjacent to a potential filled row → bigger chain → higher combo → SURGE activation

## 「面白い瞬間」

同色で埋めた列を消した瞬間、隣接する同色ブロックが連鎖的に消えていき、コンボが倍々に増えながらSURGEゲージが溜まっていく高揚感

## Scoring

- 1 line: 100 × (level+1) × combo
- 2 lines: 300 × (level+1) × combo
- 3 lines: 500 × (level+1) × combo
- 4 lines (Tetris): 800 × (level+1) × combo
- Chain cell: 50 × (level+1) × combo (per cell)

## Dev Status

- ✅ Core Tetris mechanics (SRS rotation, wall kicks, DAS)
- ✅ BFS chain propagation from cleared rows
- ✅ SURGE rainbow bomb
- ✅ 3 screens: Title, Game, Game Over
- ✅ Particle effects and screen shake
- ✅ 7-bag randomizer
- ✅ Level progression with speed increase
- ✅ 57 headless tests passing
- ✅ ruff + ty clean

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/059_tetra_surge/main.py
```
