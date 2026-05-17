# ECHO ARC — Color-Match Trajectory Launcher

**Source:** Reinterpreted from game_idea_factory idea #1 (score 31.85)  
**Session:** 2026-05-17  
**Engine:** Pyxel 2.x, 256×256, display_scale=2

## Gameplay

Aim and launch colored projectiles from a slingshot at the bottom of the screen. Match projectile color to target color for COMBO multipliers. Each successful hit leaves an **ECHO RING** — subsequent shots passing through same-color echo rings get bonus amplification. Build COMBO≥4 to trigger **SUPER SHOT** (rainbow mode: matches ALL colors for 3 seconds).

### Core Hooks
- **"One color per turn"** → Only the active color deals full combo damage. Switch with SPACE or wait for auto-cycle (5s).
- **"Log/replay as asset"** → Every hit creates a persistent echo ring. Rings amplify future shots (damage ×1.5) and refresh when triggered.

## Controls

| Input | Action |
|-------|--------|
| Mouse click + hold | Start aiming, charge power |
| Mouse move | Set aim angle |
| Mouse release | Launch projectile |
| SPACE | Switch active color (manual) |
| R | Restart (on game over) |

## Mechanics

- **4 Colors**: FIRE (red), ICE (cyan), LIGHT (yellow), NATR (lime)
- **COMBO**: Same-color consecutive hits. COMBO≥4 = SUPER SHOT
- **SUPER SHOT**: 3 seconds of rainbow mode — matches ALL target colors
- **Echo Rings**: Max 8 rings. Fade after 3 seconds. Refresh + grow when triggered
- **Timer**: 60 seconds to maximize score
- **Scoring**: Base(10) × combo_mult(1+.5×combo) × distance_mult(1+.5×y_dist)
- **Miss penalty**: Combo resets to 0
- **Auto-cycle**: Active color changes every 5 seconds

## Dev Status

- [x] Slingshot aim + launch (click-drag-release)
- [x] Color-matching COMBO system
- [x] Echo ring creation and amplification
- [x] SUPER SHOT rainbow mode (COMBO≥4)
- [x] Particle effects + floating text
- [x] Timer + score + game over
- [x] Headless import tests
- [ ] Web deployment

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/037_echo_arc/main.py
```

## Headless Test

```bash
cd ~/repos/game-prototypes
uv run python prototypes/037_echo_arc/test_imports.py
```
