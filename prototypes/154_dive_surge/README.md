# DIVE SURGE — 154 (Cliff Diving / High Diving)

## Source
Reinterpreted from game_idea_factory Idea #1 (Score 31.8, deckbuilder roguelite with alchemy/synthesis theme).
Hooks transferred:
- **Log/replay as asset** → Ghost echo trail of previous dive trajectory
- **Chain visualization accelerating** → Same-color splash zone COMBO chain

## Engine
- Pyxel 2.x, 320×240, display_scale=2
- 30 FPS

## Gameplay
**Core mechanic**: Jump from increasingly higher platforms, control rotation mid-air, and land in color-coded splash zones. Same-color consecutive landings build COMBO; COMBO ≥ 5 triggers SUPER DIVE (rainbow, 3x score, auto-match).

**"Most Fun Moment"**: ギリギリの高さから飛び降りて、空中で回転をコントロールし、同じ色の着水ゾーンにピタリと着地してCOMBOが加速する瞬間

**Risk/Reward**: Chase same-color zones for COMBO multiplier but risk missing and accumulating HEAT. HEAT ≥ 100 = game over. Play it safe on any zone or risk for the COMBO chain.

## Controls
- **SPACE**: Jump from platform / Start game / Retry
- **LEFT**: Rotate counter-clockwise (in air)
- **RIGHT**: Rotate clockwise (in air)

## Mechanics
- 4 color zones: GREEN, RED, LIGHT_BLUE, YELLOW
- COMBO: Same color consecutively = COMBO++; different color = reset
- HEAT: +25 for missing all zones; decays at 0.05/frame
- SUPER DIVE: COMBO ≥ 5 → 5 seconds rainbow mode (3x score, auto-match)
- Ghost trail: Previous dive positions shown as fading circles
- Platform rises 8px each dive (starts y=60, min y=15)
- Splash particles on landing

## Dev Status
- ✅ Core mechanics (jump, rotate, land, combo, super)
- ✅ Particle system (splash effects)
- ✅ Ghost trail echo
- ✅ HEAT risk system
- ✅ Title / Game / Game Over screens
- ✅ 61 headless tests (all pass)
- ✅ Web build (docs/154_dive_surge.html)
- ✅ Type hints + ruff + ty pass

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/154_dive_surge/main.py
```

## Genre Note
First **cliff diving / high diving** prototype in the collection (untapped genre #diving).
