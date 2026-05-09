# 003 Magic Academy: Spell Synthesis 🧙‍♂️✨

> **Source**: Game Idea Factory (Score **31.6** — #1 out of 20)
> **Theme**: Magic Academy (rule modification) — Vampire Survivor variant adapted as turn-based battle
> **Core hook**: Playing same-type cards in one turn *synthesizes* them into a single amplified spell.
> **Engine**: [Pyxel](https://github.com/kitao/pyxel) 2.x

## Gameplay

You are a magic academy student facing the **Grimoire Golem**, a magical construct run amok.

Each turn, you draw 5 spell cards from your deck. Play spells by clicking them. **The twist**: playing a second (or third, or fourth) card of the *same element* in a single turn doesn't stack — it *synthesizes* into one super-charged spell with escalating multipliers:

| Same-type cards | Multiplier |
|---|---|
| 1 (normal) | 1× base damage |
| 2 (synthesized) | 1.5× |
| 3 | 3× |
| 4+ | 5× |

### Resources

| Resource | Description |
|---|---|
| **HEAT** | Spend to play cards (regenerates +3 per turn). Max 10. |
| **RISK** | Each card played adds +1 risk. High risk = enemy deals bonus damage. Max 10 — overflow = instant defeat! |
| **BLOCK** | Absorbs enemy damage. Gained from Earth cards. |

### Elements

| Element | Cost | Base DMG | Special Effect |
|---|---|---|---|
| 🔥 **Fire** | 3 | 5 | High damage, no frills |
| 💧 **Water** | 2 | 3 | Draws +1 extra card per play (+1/2/3 synthesized) |
| 🌍 **Earth** | 2 | 2 | Gains Block (+2/4/6/10 synthesized) |
| 🌬 **Wind** | 1 | 2 | Reduces Risk (-2/3/5/8 synthesized) |
| 🔮 **Arcane** | 4 | 6 | Highest base damage, best synthesis scaling |

### Strategy

- **Fire × 4** = 25 damage in one slot. Devastating but costs 12 HEAT.
- **Wind** reduces Risk — essential for long games.
- **Earth Block** absorbs damage efficiently.
- **Water Draw** lets you see more of your deck.
- Manage HEAT carefully — you only get 10 max, and Arcane costs 4.

## Controls

| Input | Action |
|---|---|
| **Mouse click** | Select / play a card |
| **"END TURN" button** | Click to resolve and end turn |
| **R key** | Restart game anytime |

## Screen Layout

```
┌──────────────────────────────────────────────────────┐
│ Magic Academy - Spell Synthesis    Turn 1            │
│                                                      │
│ Grimoire Golem  [████████████░░░░░] 30/30   ATK: 3  │
│                                                      │
│ HP: [████████████░░░░░] 25/25                        │
│ HEAT:[██████████░░░░░] 5/10                          │
│ RISK:[██░░░░░░░░░░░░░] 2/10   [Active Syntheses]    │
│ BLOCK: 2                       ┌───┐ ┌───┐          │
│                                │Fire│ │Wind│          │
│ Deck: 5   Discard: 5          │x2  │ │   │          │
│                                │DMG │ │DMG │          │
│                                └───┘ └───┘          │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐        │
│ │ Fire │ │Water │ │Earth │ │ Wind │ │Arcane│ [END]  │
│ │ HEAT │ │ HEAT │ │ HEAT │ │ HEAT │ │ HEAT │        │
│ │ DMG:5│ │ DMG:3│ │ DMG:2│ │ DMG:2│ │ DMG:6│        │
│ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘        │
│                                        [R] Restart   │
└──────────────────────────────────────────────────────┘
```

## Dev Status

- ✅ **Core turn system**: Draw → Play → Resolve → Enemy turn
- ✅ **Card synthesis**: Same-element cards merge with escalating multiplier
- ✅ **5 elements**: Fire, Water, Earth, Wind, Arcane with unique effects
- ✅ **Risk system**: Playing cards builds risk; high risk = more enemy damage; overflow = loss
- ✅ **Heat economy**: Spend and regenerate heat each turn
- ✅ **Block mechanic**: Earth cards generate block to absorb damage
- ✅ **Win/Lose conditions**: Enemy HP = 0 wins; player HP ≤ 0 or Risk overflow = lose
- ✅ **Particle effects**: Synthesis explosions, hit flashes, card play effects
- ✅ **Enemy scaling**: Attack increases with turn count and risk level
- ⬜ **Map/overworld**: Single battle screen only
- ⬜ **Card upgrade between turns**: Planned but not implemented
- ⬜ **More enemy types**: Currently only Grimoire Golem

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/003_magic_synthesis/main.py
```

## Build for Web

```bash
cd ~/repos/game-prototypes
uv run pyxel package prototypes/003_magic_synthesis prototypes/003_magic_synthesis/main.py
uv run pyxel app2html 003_magic_synthesis.pyxapp
mv 003_magic_synthesis.html docs/
```
