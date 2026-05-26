# DUNGEON CHAIN (071_dungeon_chain)

Color-match roguelike dungeon crawler — first dungeon crawler in the collection.

## Source

Reinterpreted from game_idea_factory #1 (Score 32.0):
- "split into multiple paths → converge → explode" → dungeon branching → same-color kill chains → ROOM SURGE
- "synthesis compression" → COMBO x4 triggers BFS chain clear

## Engine

Pyxel 2.x, 320×240, display_scale=2

## Core Mechanic

Navigate a grid-based dungeon. Kill same-color enemies consecutively to build COMBO chains.
- COMBO >= 4 triggers **ROOM SURGE**: BFS chain-kills all same-color enemies in the current room
- Wrong-color kill when COMBO active = 1 damage + COMBO reset
- Risk/reward: commit to one color for chains, or play safe with lower score

## Controls

| Key | Action |
|-----|--------|
| WASD / Arrows | Move |
| SPACE | Attack nearest adjacent enemy |
| Mouse click | Attack adjacent enemy under cursor |
| ENTER | Start game from title |
| R | Restart from game over/victory |

## Game Flow

1. **Title** — Press ENTER to start
2. **Playing** — Explore 3-room dungeon, collect key, unlock door, reach exit
3. **Game Over** — HP reaches 0 (damage from wrong-color attacks or enemy contact)
4. **Victory** — Reach exit with key

## Resources

- **HP**: 5 hearts. Lost on wrong-color attack or enemy contact. Brief invulnerability after hit.
- **COMBO**: Builds with consecutive same-color kills. Resets on wrong color.
- **Key**: Found in room 2. Needed to unlock exit door.

## Dev Status

- ✅ Core movement and dungeon navigation
- ✅ Combat system with color-matching COMBO
- ✅ ROOM SURGE BFS chain kill
- ✅ Enemy AI (chase within range)
- ✅ 3-screen flow: Title → Playing → Game Over / Victory
- ✅ Headless tests (test_imports.py)
- ✅ Web build (pyxel app2html)

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/071_dungeon_chain/main.py
```

## Experience Hypothesis

「同色の敵を連続で倒してCOMBOを積み、ROOM SURGEで部屋中の同色敵が一瞬で全滅する爆発的カタルシス」
