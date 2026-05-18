# ECHO STEALTH (042)

**Source:** game_idea_factory idea #1 (score 31.85)
- Hook "one-color-per-turn" → one guard color has vision per frequency phase
- Hook "log/replay as asset" → echoes left when caught act as distractions for same-color guards

**Genre:** Top-down grid stealth (first stealth game in the collection)

**Engine:** Pyxel 2.x, 256x256, display_scale=3, 30 FPS

## Gameplay

You are a thief trapped in a room full of patrolling guards. Only one color of guard can **see** at any time — the "active frequency" cycles every 3 seconds. Your goal: reach the green EXIT door before time runs out.

### Core Mechanic: Color-Cycle Stealth

- **4 guard colors**: RED, GREEN, BLUE, YELLOW
- **Active frequency**: cycles every 3 seconds (90 frames)
- Only guards matching the active color have **vision cones** — other colors are blind
- Time your movement with the color cycle to slip past blind guards

### Echo Distraction

- When a guard catches you, you leave an **ECHO** behind (ghost afterimage)
- You respawn at the start with brief invulnerability (1 second)
- The echo distracts **same-color** guards for 2 full phases (6 seconds)
- Distracted guards abandon their patrol and move toward the echo
- Strategic use: get caught deliberately near one color of guard to pull them away from a critical corridor

### Risk / Reward

- **Gems** are scattered around the room (50 pts each)
- Gems matching the active color give **2x bonus** (100 pts)
- Collecting gems requires navigating into dangerous areas
- Time bonus: remaining seconds × 10 at exit

## Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move (8-directional) |
| R | Restart (any time) |

## Rules

- **Goal**: Reach the green EXIT tile in the bottom-right area
- **HP**: 3 hearts (shown as `HP:III`)
- **Timer**: 60 seconds
- **Failure**: HP reaches 0 OR time runs out
- **Success**: Reach exit → time bonus added to score
- **Color cycle**: visible in top-left HUD + phase timer bar (top-right)

## Dev Status

- [x] Grid-based level generation (walls, guard patrols, gems, exit)
- [x] Guard patrol AI with direction reversal at bounds
- [x] Color-cycle frequency system (4 colors, 3-sec phases)
- [x] Vision cone rendering (semi-transparent overlay)
- [x] Line-of-sight wall occlusion
- [x] Echo distraction mechanic (guards pulled toward echoes)
- [x] Gem collection with active-color bonus
- [x] HP system with caught invulnerability
- [x] Particle effects and floating score text
- [x] Victory / Defeat screens with score display
- [x] 17 headless logic tests
- [ ] Multiple rooms / levels
- [ ] Sound effects
- [ ] Difficulty scaling

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/042_echo_stealth/main.py
```

## How to Test

```bash
cd ~/repos/game-prototypes
uv run python prototypes/042_echo_stealth/test_imports.py
```
