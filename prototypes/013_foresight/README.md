# 013 FORESIGHT — Grid Survival

**Source**: Game Idea Factory #4 (Score 31.45) — 「コストはHPではなく『未来の手札』を消費」
Reinterpreted from dice/bag roguelite into **top-down grid survival** — a new genre for the collection.

**Engine**: Pyxel 2.x, 320×256, display_scale=2

## Gameplay

"Spend future knowledge to attack. Your vision of upcoming enemy spawns is the resource you spend."

- **Core loop**: See future spawns → Move (WASD) → Attack (SPACE) → End turn (E) → Enemies move toward you → New spawns arrive
- **Risk/reward**: Attacking costs 1 Future Card (you lose vision of an upcoming enemy spawn). The more you attack, the less you can predict. When future runs out, you must dodge blindly.
- **Kill bonus**: 50% chance to regain a Future Card on kill — rewards aggressive play
- **Escalation**: Enemy spawn rate increases every 8 turns
- **Goal**: Survive as many turns as possible, maximize score

## Controls

| Key | Action |
|-----|--------|
| WASD / Arrows | Move player (one step per press) |
| SPACE | Attack all adjacent enemies (costs 1 Future) |
| E | End turn |
| R | Restart (on game over) |

## Enemy Movement

Enemies move toward the player each turn with randomized axis priority (Manhattan distance, prefer x or y randomly each step). Multiple enemies can attack in the same turn.

## UI Reference

- **Cyan circles**: Future spawn previews (number = turns until spawn)
- **Yellow circles**: Imminent spawns (1 turn away)
- **Red circles**: Active enemies on grid
- **Green circle (@)**: Player
- **Cyan dots**: Remaining Future Cards
- **Green/Red bar**: HP

## Dev Status

- ✅ Core mechanic: future-as-resource attack system
- ✅ Grid movement (WASD)
- ✅ Enemy pursuit AI (randomized axis priority)
- ✅ Future card preview + countdown
- ✅ Escalating difficulty
- ✅ Kill-to-regain-future reward mechanic
- ✅ Particle effects (attack, damage, spawn)
- ✅ Floating damage/score text
- ✅ Game over + restart
- ⬜ Sound effects
- ⬜ Multiple enemy types
- ⬜ Power-ups / items
- ⬜ High score persistence

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/013_foresight/main.py
```
