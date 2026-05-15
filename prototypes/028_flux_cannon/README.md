# FLUX CANNON (028_flux_cannon)

Artillery chain-combo prototype — aim, fire, and chain same-color hits for SUPER shots.

## Source

- **Generated**: 2026-05-15 from `game_idea_factory` (seed timestamp-based)
- **Original idea**: #1 (score 32.05) — Deckbuilder with synthesis compression + cost is future hand
- **Reinterpretation**: Reinterpreted into **artillery/aiming** (genre not yet in collection):
  - "Synthesis compression" → Color-match chain COMBO → SUPER SHOT (AOE burst)
  - "Cost is future hand" → FOCUS meter drains on high-power shots, reducing accuracy on future shots

## Engine

- Pyxel 2.x, 400×300, display_scale=2, 60 FPS

## Gameplay

**Objective**: Score as many points as possible in 60 seconds by hitting colored targets with matching cannon shots.

### Core Mechanic

1. **Aim**: Move mouse to set cannon angle (trajectory preview arc shown as dotted line)
2. **Power**: Scroll wheel adjusts shot power (40–130). Higher power = more range but more FOCUS drain
3. **Fire**: Left-click to launch a colored projectile
4. **Combo**: Hitting same-color targets consecutively builds COMBO. COMBO ≥ 3 unlocks **SUPER SHOT**
5. **SUPER SHOT**: Larger projectile that AOE-bursts on hit — destroys ALL same-color targets within 90px radius
6. **Miss/Wrong Color**: Resets combo to 0

### Resources

| Resource | Max | Description |
|---|---|---|
| FOCUS | 100 | Accuracy stat. Regenerates slowly. Drains on shots (more drain at higher power). Below 25 = aim wobble (random angle perturbation). +15 on hit |
| HEAT | 100 | Builds +14 per shot. At 100, cannon overheats (2.5s cooldown), combo resets |

### Risk/Reward

- **Chase the combo**: Continue shooting same color for big multipliers, but miss = reset
- **Power shots**: More damage range but drain focus → future shots become inaccurate
- **Super gamble**: Build to combo 3 for SUPER, but overheat looms

## Controls

| Input | Action |
|---|---|
| Mouse move | Aim cannon angle |
| Scroll wheel | Adjust power (up = more power) |
| Left click | Fire |
| R | Restart after game over |

## Scoring

- Base: 100 per hit
- Combo multiplier: `1 + (combo - 1) × 0.5` (e.g., combo 5 = 3× multiplier)
- SUPER shot: 2× score on direct hit + bonus on AOE hits
- Game Over shows hit accuracy %

## Element Reference

| Color | Pyxel Color | Abbr |
|---|---|---|
| RED | COLOR_RED (8) | R |
| BLUE | COLOR_DARK_BLUE (5) | B |
| GREEN | COLOR_GREEN (3) | G |
| YELLOW | COLOR_YELLOW (10) | Y |
| PURPLE | COLOR_PURPLE (2) | P |

## Dev Status

- ✅ Core artillery aiming + firing with trajectory preview
- ✅ Color-match combo system (same-color chain)
- ✅ SUPER shot at combo ≥ 3 (AOE burst + screen shake)
- ✅ FOCUS accuracy mechanic (wobble when low)
- ✅ HEAT overheat mechanic with cooldown
- ✅ 60-second timed run
- ✅ Floating score popups
- ✅ Particle effects + screen shake
- ✅ Target drift for dynamic aiming
- ✅ Color legend HUD
- ✅ Headless test suite (28 tests)
- ⬜ Sound effects (SE)
- ⬜ Background music
- ⬜ Difficulty escalation (more targets over time)
- ⬜ High score persistence

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/028_flux_cannon/main.py
```

## Test

```bash
cd ~/repos/game-prototypes
uv run python prototypes/028_flux_cannon/test_imports.py
```
