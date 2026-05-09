# Calamity Dice — Dice Battler Prototype

**Source**: Game Idea Factory #1 (Score 31.45)
- Theme: Calamity Sealing (runaway control)
- Hook: Log/replay as asset (previous actions become next dice)
- Hook: One element per turn constraint

**Engine**: Pyxel 2.x, 400×300, display_scale=2, 30fps

## Gameplay

You are a **Calamity Sealer** fighting elemental disasters with unstable dice magic.

Each turn:
1. **Roll** — 3+ dice are rolled, each showing an element (FIRE/WATR/ERTH/AIR/AETHR) and a value (1-6)
2. **Pick ONE element** — click the element button to channel all dice of that element
3. **Deal damage** — each channeled die deals damage equal to its value × 2
4. **Log grows** — channeled dice enter your "log" and come back as bonus dice next turn!
5. **Heat builds** — channeling generates heat. Too much heat = feedback damage
6. **Enemy attacks** — survive and defeat all 3 waves

### Core Mechanic: Log/Replay

The dice you channel this turn return as **bonus dice** next turn. Pick the same element consecutively to build an unstoppable dice avalanche — but channeling builds HEAT, forcing you to manage risk vs. reward.

### Heat System

- **+3 heat** base per turn
- **+5 heat** per channeled die
- **-15 heat** natural cooling after enemy attacks
- Heat ≥ 70: Warning zone
- Heat ≥ 90: DANGER — take 4 overheat damage

### Risk & Reward

- Streak bonus: channel the same element 3+ turns for visual feedback
- Score = total damage dealt + survival bonuses
- Defeat an enemy quickly for higher score

## Controls

| Action | Input |
|--------|-------|
| Select element | Click element button (FIRE/WATR/ERTH/AIR/AETHR) |
| Restart (game over) | Click anywhere |

## Enemy Waves

| Wave | Enemy | HP | ATK |
|------|-------|-----|------|
| 1 | Flame Sprite | 35 | 3 |
| 2 | Tidal Wyrm | 55 | 5 |
| 3 | Earth Titan | 80 | 7 |

Enemy attack scales +1 every 5 turns.

## Dev Status

- [x] Dice rolling with 5 elements
- [x] Log/replay mechanic (channeled dice return next turn)
- [x] Heat system with warning/danger thresholds
- [x] Phase machine (ROLL → SELECT → ANIMATE → ENEMY → CHECK)
- [x] 3 enemy waves with scaling attack
- [x] Particle effects for damage/heal
- [x] Message system
- [x] Victory/defeat screens with score
- [x] Streak tracking
- [ ] Dice re-roll mechanic (risk system)
- [ ] Sound effects
- [ ] Enemy visual variety
- [ ] Elemental weakness/resistance

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/005_calamity_dice/main.py
```
