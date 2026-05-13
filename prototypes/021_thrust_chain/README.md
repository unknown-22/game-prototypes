# THRUST CHAIN

**Lunar Lander with Color-Matched Combo Chains**

## Source

Reinterpreted from game idea #1 (Score 32.15):
- Original: "Deckbuilder roguelite — delivery/logistics (flow optimization)"
- Hooks mapped:
  - "circuit/pipe flow visible" → colored landing pad chain system
  - "split values converge and explode" → COMBO multiplier escalates with consecutive matched landings
  - "log/replay as assets" → ghost trail from previous best run

All 10 generated ideas (2026-05-13) clustered in deckbuilder/dice/auto-shooter genres. This is a creative reinterpretation into the **lunar-lander/thrust** genre, which was not represented in the existing 20 prototypes.

## Engine

- Pyxel 2.x, 256×256, display_scale=2, 60 FPS
- Python 3.12+

## Gameplay

### The Most Fun Moment

Aiming for the next same-color pad with barely enough fuel, landing precisely to keep the combo chain alive — watching the multiplier climb higher and higher as you thread the needle through dangerous terrain.

### Core Mechanic

1. **Fly the lander**: Rotate with LEFT/RIGHT, thrust with UP. Gravity constantly pulls you down.
2. **Land on pads**: Guide the ship onto colored landing pads on the cavern floor.
3. **Match colors**: If your ship's color matches the pad's color, you build a COMBO chain — each consecutive same-color landing multiplies your score.
4. **Mismatch risk**: Landing on a wrong-color pad resets your COMBO to zero and damages your HP.
5. **Survive**: Manage fuel (refuel on landing), HP (avoid walls and wrong pads), and keep the combo alive as long as possible.

### Risk & Reward

- **Same-color streak**: COMBO multiplier increases (×1 → ×2 → ×3 ...), making each subsequent landing more valuable. But miss once and it all resets.
- **Fuel management**: Thrust costs fuel. Land to refuel — but rushing to land can cause crashes.
- **Wall danger**: Touching cavern walls deals 15 damage. Tight maneuvering increases risk.
- **Landing precision**: Must land upright (±35°) and slow (speed < 1.8). Crashing deals 30 damage.

### Escalation

Pads refresh after each landing. Higher-value pads (10-25 pts) spawn randomly. The ship auto-launches after landing, requiring quick reorientation for the next target.

## Controls

| Key | Action |
|-----|--------|
| LEFT / A | Rotate counter-clockwise |
| RIGHT / D | Rotate clockwise |
| UP / W | Thrust (uses fuel) |
| Z / X | Cycle ship color |
| R | Restart (on game over) |
| Q | Quit |

## Elements

| Color | Name | Pyxel |
|-------|------|-------|
| RED | Fire | COLOR_RED |
| BLUE | Water | COLOR_CYAN |
| GREEN | Earth | COLOR_GREEN |
| YELLOW | Air | COLOR_YELLOW |

## HUD

- **Top bar**: FUEL gauge, HP gauge, SCORE, COMBO multiplier
- **Bottom**: Current ship COLOR, control hints
- **In-world**: Floating score/damage text, landing particles, crash effects, screen shake

## Dev Status

- ✅ Core physics (gravity, thrust, rotation, damping)
- ✅ Landing pad system with color matching
- ✅ COMBO chain multiplier
- ✅ 4 color types with manual cycling
- ✅ Fuel management with landing refuel
- ✅ HP system with wall/crash/wrong-color damage
- ✅ Particle effects (thrust, celebration burst, crash)
- ✅ Floating score/damage text
- ✅ Screen shake on damage
- ✅ Ghost trail from best run
- ✅ Game over screen with RETRY
- ✅ Quick restart (R key)
- ⬜ Sound effects
- ⬜ Progressive difficulty (faster gravity, fewer pads)
- ⬜ High score persistence

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/021_thrust_chain/main.py
```

## Headless Tests

```bash
uv run python prototypes/021_thrust_chain/test_imports.py
```
