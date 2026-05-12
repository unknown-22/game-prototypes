# Element Drop — Pachinko Synthesis Prototype

**Prototype 015** — A Pachinko/Peggle-style ball-drop game with alchemy synthesis combos.

## Source

Reinterpreted from game_idea_factory idea #1 (Score 31.65):

| Hook | Reinterpretation |
|---|---|
| "Effects synthesize into one compressed card" | Same-element peg chains double the combo multiplier (x1→x2→x4→x8) |
| "Cost is future hand, not HP" | Future ball preview (3 upcoming elements) limits planning |
| Theme: Alchemy synthesis | 5 element pegs + golden target pegs |

**Why this genre?** All 10 generated ideas clustered in dice/deckbuilder/Vampire-Survivors genres, all overlapping with existing prototypes (001-014). This Pachinko/Peggle reinterpretation adds a physics-based aim-and-shoot genre to the collection — mechanically distinct from all 14 prior prototypes.

## Engine

- Pyxel 2.x, 256×256, display_scale=2
- Python 3.12 with type hints

## Gameplay

**Core mechanic:** Drop balls through a field of elemental pegs. Consecutive hits on same-element pegs SYNTHESIZE — each hit doubles the score multiplier (x1, x2, x4, x8, x16...). Hitting a different element resets the multiplier. Clear all golden TARGET pegs to win.

**The most fun moment:** Dropping a ball through a tight corridor of same-element pegs and watching the multiplier explode as the ball carves a path of destruction.

### Rules

1. Aim with mouse (horizontal position at top of screen)
2. Click to drop ball — it falls with gravity and bounces off pegs
3. The ball has an element (shown at bottom). Hitting pegs of the **same element** builds a SYNTHESIS chain
4. Each consecutive same-element hit **doubles** the multiplier
5. Hitting a **different** element resets the multiplier to x1
6. **Golden pegs** are TARGETS — must all be cleared to win
7. You have **10 balls** per game
8. The **next 3 ball elements** are previewed at top-right — plan your sequence!

### Scoring

| Event | Base Points |
|---|---|
| Same-element peg hit | 10 × multiplier |
| Different-element peg hit | 5 |
| Target peg cleared | 30 × multiplier |
| All targets cleared (bonus) | 500 |

### Risk/Reward

- **Safe:** Drop through scattered pegs for guaranteed points
- **Risky:** Aim through dense same-color clusters for massive combo chains
- **Strategic:** Use future ball preview to plan element sequences — drop a WATER ball where WATER pegs are clustered

## Controls

| Action | Input |
|---|---|
| Aim | Move mouse horizontally |
| Drop ball | Left click |
| Restart (game over) | R key or left click |

## Dev Status

- ✅ Core mechanic: ball drop + peg bounce + element synthesis
- ✅ 5 elements (FIRE, WATER, EARTH, AIR, AETHER) + target pegs
- ✅ Combo system: consecutive same-element hits double multiplier
- ✅ Particle burst effects + floating score text
- ✅ Future ball preview (3 upcoming elements)
- ✅ Board regeneration on restart
- ✅ Minimum 6 target pegs guaranteed
- ✅ High score tracking
- ✅ Quick restart (R or click)
- ⬜ Sound effects (Pyxel audio)
- ⬜ Multiple board layouts / levels
- ⬜ Special ball types (multiball, pierce, etc.)
- ⬜ Screen shake on big combos

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/015_element_drop/main.py
```

## Idea Traceability

- **Generated:** 2026-05-12 09:01 UTC (seed: timestamp-based)
- **Archived:** `ideas/2026-05-12_pachinko-reinterpret.md`
- **Source idea:** #1 — Dice/Bag Roguelite / Alchemy (synthesis), Score 31.65
- **Key hooks transferred:** synthesis/compression → combo multiplier doubling, future hand cost → ball element preview
