# SNOW CHAIN — Snowboard Color-Match COMBO Chain

## Source
Reinterpreted from game_idea_factory #1 (Score 32.15): Hacking/Auto-shooter
- "Log/replay as asset" → ghost snowboarder trail (best-run replay)
- "CA grid fills up" → avalanche danger spreading from left edge

## Engine
- Pyxel 2.x, 320×240, display_scale=2, 30fps

## Gameplay
Side-scrolling snowboard game. Auto-ride rightward down a snowy slope. Colored gates appear ahead — match the snowboarder's color to the gate color to build COMBO chain. Avalanche chases from the left edge.

**Core mechanic**: Same-color consecutive gate passes build COMBO → COMBO≥4 triggers SUPER CARVE (rainbow mode, any-color match, 3x score, 10 seconds).

**Risk/Reward**:
- Match gate color → COMBO++, score × combo × super_mult
- Wrong color gate → COMBO reset, HEAT+15
- Rock collision → HEAT+25, COMBO reset (jump to avoid!)
- Avalanche catch → HEAT+30
- HEAT≥100 → game over

**The most fun moment**: Same-color gates in rapid succession, COMBO hits 4, SUPER CARVE activates — snowboarder glows rainbow, all gates auto-match, score explodes at 3x, and you blast ahead of the avalanche.

## Controls
- SPACE: Jump (avoid rocks)
- RETURN/ENTER: Start game (title screen)
- R: Retry (game over screen)

## Dev Status
- ✅ Core gameplay loop (gates, COMBO, SUPER CARVE)
- ✅ Avalanche CA system
- ✅ Rock obstacles with jump avoidance
- ✅ Ghost trail (best-run replay)
- ✅ Difficulty escalation (speed, spawn intervals, color cycles)
- ✅ HEAT risk system
- ✅ Snow particles + mountain parallax background
- ✅ Screen shake + particle bursts + floating text
- ✅ 3 screens (Title/Playing/GameOver)
- ✅ 63 headless tests
- ✅ ruff + ty checks pass

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/274_snow_chain/main.py
```
