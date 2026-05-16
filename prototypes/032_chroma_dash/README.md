# CHROMA DASH — Side-Scrolling Endless Runner

**Prototype #032** — Reinterpreted from game idea #1 (score 32.0)

## Source

- **Idea**: Deckbuilder roguelite (hacking/circuit) — "synthesis compression" + "chain collapse UI effects"
- **Reinterpretation**: Same-color consecutive gem collection → COMBO chain. COMBO ≥ 5 → FLUX super-mode (3x gems, 5 seconds). The "synthesis compression" translates to building and maintaining a fragile COMBO chain; "chain collapse UI effects" translates to the explosive visual feedback when FLUX activates and when COMBO resets.

## Engine

- **Pyxel 2.x**, 240×160, display_scale=3
- Python 3.12, type-hinted, single-file

## Gameplay

### Core Mechanic
Run endlessly to the right, collect colored gems, and build COMBO chains by collecting the same color consecutively. A single wrong-color gem resets your COMBO. Reach COMBO ≥ 5 to activate FLUX super-mode (5 sec, 3x gem value, rainbow aura).

### The Fun
Chain-collecting same-color gems at increasing speed to maintain a fragile COMBO, hitting FLUX mode and watching the score explode.

### Rules
- Player auto-runs right (ground scrolls left)
- **Jump** (Space/Up/W) to avoid ground spikes and jump over pits
- **Duck** (Down/S) to avoid floating bars
- Collect colored gems (FIRE=red, WATER=blue, LEAF=green, GOLD=yellow)
- Same-color consecutive = COMBO multiplier (×1, ×2, ×3, ...)
- Different color = COMBO reset
- COMBO ≥ 5 → **FLUX MODE** (5 seconds, 3x gems, rainbow aura)
- FLUX ends → COMBO resets to 0
- Obstacles: spikes (jump), bars (duck), pits (jump)
- Hit obstacle = GAME OVER
- Speed increases with distance

### Scoring
- 1 point per frame survived
- Gems: 10 base × COMBO multiplier (up to ×10)
- FLUX mode: 3x gem value

## Controls

| Key | Action |
|---|---|
| Space / Up / W | Jump |
| Down / S | Duck |
| Space / R (game over) | Retry |

## Dev Status

- ✅ Core runner mechanics (jump, duck, scroll, speed ramp)
- ✅ 4-color gem system with COMBO tracking
- ✅ FLUX super-mode (COMBO ≥ 5, 5 sec duration)
- ✅ Obstacle types: spikes, bars, pits
- ✅ Particle effects and floating text
- ✅ HUD: score, combo, flux gauge, speed
- ✅ Game over screen with retry
- ✅ Headless logic tests
- ⬜ Web build (app2html)
- ⬜ Sound effects / music
- ⬜ Difficulty curve tuning

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/032_chroma_dash/main.py
```

## Headless Tests

```bash
uv run python prototypes/032_chroma_dash/test_imports.py
```
