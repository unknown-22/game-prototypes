# CRAWL SURGE (052)

**Centipede-like color-match arena shooter.**

Reinterpreted from game_idea_factory #1 (Score 32.0):
- "split + converge" → centipede chains split when shot mid-body
- "synthesis compression" → SURGE: BFS chain-destroy connected same-color segments

## Engine
- Pyxel 2.2+, 256×240, display_scale=3
- Python 3.12

## Gameplay

A centipede winds down from the top of the screen. You control a ship at the bottom.
Your ship's color cycles through RED → GREEN → BLUE → YELLOW.
Shoot segments with matching color to build COMBO.

### Core Rules
- **Color Match**: Shooting a segment with matching color → COMBO++ and segment destroyed
- **Color Mismatch**: Shooting with wrong color → segment destroyed but COMBO resets to 0
- **SURGE**: COMBO ≥ 3 and a matching hit → BFS destroys ALL connected same-color segments in the chain for massive bonus (500 × COMBO × count)
- **Chain Split**: Destroying a mid-body segment splits the centipede into independent chains
- **Mushrooms**: Destroyed segments may spawn mushrooms that block shots and redirect the centipede
- **Wave System**: Clear all segments → next wave with more segments and more mushrooms

### Risk/Reward
- Let the centipede come closer for easier color-matching, but risk getting touched
- High COMBO is fragile — one wrong-color shot resets it
- SURGE is powerful but resets COMBO afterward

## Controls
| Key | Action |
|-----|--------|
| ← → / A D | Move ship |
| ↑ ↓ / W S | Cycle color (manual) |
| SPACE / Z | Shoot |
| SPACE / R | Restart (after game over) |

## Dev Status
- ✅ Core mechanic: color-match shooting with COMBO
- ✅ SURGE BFS chain destruction
- ✅ Chain split mechanic
- ✅ Mushroom obstacles
- ✅ Wave escalation
- ✅ Particle effects + floating text
- ✅ Screen shake
- ✅ Auto color cycling + manual override
- ✅ Game over + restart

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/052_crawl_surge/main.py
```

## Source Idea
```
#1 Score 32.0 — Deckbuilder Roguelite / Hacking
Hooks: synthesis compression + split/converge
Reinterpreted: color-match centipede shooter with chain-split and SURGE BFS
```
