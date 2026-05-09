# 004 Circuit Breaker 🖥️⚡

> **Source**: Game Idea Factory (Score **31.2** — #3 out of 20)
> **Theme**: Hacking / Circuit / Log — netrunner-style digital warfare
> **Core hook**: Stack same-type code cards by playing them; when a stack hits its burden threshold, it **collapses** for amplified burst damage or utility.
> **Engine**: [Pyxel](https://github.com/kitao/pyxel) 2.x

## Gameplay

You are a netrunner breaching a hostile **FIREWALL v3.2.1** system. Each turn you draw 5 code cards from your deck. Play cards to build **stacks** (payloads) of the same type. When a stack reaches its threshold, it **collapses** — triggering a powerful effect.

Meanwhile, the enemy system builds **TRACE** on your location. Let it fill up and you'll be counterattacked!

**The twist**: The more cards of the same type you commit, the greater the burst — but you risk over-committing while trace climbs. The "cost" is future hands: cards you play go to the discard pile and won't be available next turn.

### Card Types

| Abbr | Name | Threshold | Collapse Effect | Color |
|------|------|-----------|-----------------|-------|
| VRS | Virus | 3 | Deal **6 DMG** | 🔴 Red |
| FWL | Firewall | 3 | Gain **6 BLK** | 🔵 Blue |
| SPD | Spider | 2 | **+2 Draw** next turn | 🟢 Green |
| DMN | Daemon | 2 | **−2 Trace** | 🟠 Orange |
| WRM | Worm | 4 | Deal **10 DMG** | 🟡 Yellow |

### Resources

| Resource | Description |
|----------|-------------|
| **HP** | Your health (20). Reach 0 = defeat. |
| **BLK** | Block absorbs enemy attack damage. |
| **TRACE** | Enemy detection meter (0→8). Fills by +2 each turn. At max, enemy attacks for 5 DMG. |

## Strategy

- **Stack management**: Don't spread too thin — focus on 2-3 element types per run.
- **Trace control**: Use Spider (+draw) and Daemon (−trace) to control pacing.
- **Worm timing**: Worm needs 4 cards to collapse but hits hard. Save them up.
- **Deck cycling**: 15 cards, draw 5 per turn = full cycle every 3 turns. Plan which elements you need.

## Controls

| Input | Action |
|-------|--------|
| 🖱️ **Click card** | Play it (adds to stack) |
| 🖱️ **Click END TURN** | End your turn |
| 🖱️ **Click / [R]** | Restart after win/loss |

## Dev Status

- ✅ Core mechanic: Stack → Collapse for 5 card types
- ✅ Turn-based combat loop (Draw → Play → Enemy)
- ✅ Trace meter with enemy attack at max
- ✅ Win/Lose conditions with restart
- ✅ Visual polish: particles, progress bars, hover highlights
- ✅ Headless import test (logic-layer)
- ✅ Web build (WASM/HTML5)
- ⬜ Sound effects / music
- ⬜ More enemy variety
- ⬜ Upgrades between rounds

## How to Run

```bash
# From project root
uv run python prototypes/004_circuit_breaker/main.py

# Or directly
cd prototypes/004_circuit_breaker && uv run python main.py
```

## Build for Web

```bash
cd ~/repos/game-prototypes
uv run pyxel package prototypes/004_circuit_breaker prototypes/004_circuit_breaker/main.py
uv run pyxel app2html 004_circuit_breaker.pyxapp
mv 004_circuit_breaker.html docs/
```
