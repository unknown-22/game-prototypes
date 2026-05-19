# STARFALL — Color-Match Missile Command Defense

**Prototype 043** | Reinterpreted from game_idea_factory idea #1 (score 32.0)

## Source

- **Idea #1 (score 32.0)**: Calamity Sealing (runaway control) deckbuilder roguelite
- **Hooks reinterpreted**: synthesis compression → COMBO chain multipliers; chain visualization → prominent on-screen COMBO counter that accelerates with wave intensity
- **Reinterpretation**: All 10 generated ideas clustered in deckbuilder/auto-shooter (already 30+ in collection). Picked highest-scored idea and reinterpreted into **Missile Command-like defense** (genre #30 — not yet in collection).
- **Genre**: Color-match defense / missile command

## Engine

- Pyxel 2.x, 256×256, display_scale=3, 60 FPS
- Python 3.12+, single-file (~420 lines)

## Gameplay

**Core mechanic**: Click to launch color-coded interceptors from cities. Same-color consecutive intercepts build a COMBO chain → score multiplier surges. Let stars get close for risky bonus points, or play safe and lose the chain.

- **5 cities** along the bottom, each a different color (Red, Blue, Green, Yellow, Purple)
- **Enemy stars** fall from the top with random colors and increasing speed
- **Click anywhere** to launch an interceptor from the nearest ready city
- **Same-color intercept** → COMBO +1, multiplier grows (×1.0 → ×1.5 → ×2.0 → … up to ×10.0)
- **Wrong-color intercept** → COMBO resets to 0 (star still destroyed, base score)
- **Close intercept bonus**: +80 pts for stars below y=180 (risk/reward)
- **COMBO ≥ 4** triggers SURGE mode (3 seconds): larger explosion radius, pink glow on matching stars

**Resources**:
- **City HP** (3 each): cities destroyed when stars hit them — lose all cities = game over
- **Interceptor cooldown** (6 frames): cities need time to reload between shots
- **HEAT** (0–100): builds on city hits, decays slowly. Visual indicator only (future: overheat penalty)

**Waves**: Escalating difficulty — each wave adds 2 more stars, faster spawn rate, and slightly faster star speed. Brief pause between waves.

## Controls

| Action | Input |
|---|---|
| Launch interceptor | Left-click on target point |
| Retry (game over) | Left-click or press R |

## Dev Status

- ✅ Core mechanic: color-match intercept with COMBO chain
- ✅ 5 cities, 5 colors, HP system
- ✅ Wave escalation (more stars, faster, speed ramp)
- ✅ COMBO multiplier system (up to ×10.0)
- ✅ SURGE mode (COMBO ≥ 4 → 3s big radius)
- ✅ Close intercept bonus (+80 pts for risky kills)
- ✅ Particle explosions with color feedback
- ✅ Screen shake on city hits
- ✅ Game over + instant retry
- ✅ Headless logic tests (18 tests)
- ✅ Ruff + ty pass
- ⬜ Overheat penalty mechanics (screen flash, spawn rate boost)
- ⬜ Sound effects
- ⬜ Power-up pickups between waves

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/043_starfall/main.py
```
