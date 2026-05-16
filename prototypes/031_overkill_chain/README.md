# OVERKILL CHAIN

Timing/precision overkill chain game. Reinterpreted from game idea #9 (score 30.8) with "overkill carryover" and "combo meter" hooks.

## Engine

- Pyxel 2.x
- Screen: 256×192

## Gameplay

Enemies march left toward your base. Click on them to attack. When an enemy dies, excess damage ripples left to the next enemy in line, creating chain reactions. Build combos by chaining kills — higher combos multiply your score.

### Core Mechanic

**Overkill Carryover**: Damage exceeding an enemy's HP carries over to the next enemy to the left, with a chain depth bonus (each step adds 20% more damage). Chain 3+ kills to trigger screen shake.

### Rules

- **Goal**: Survive as long as possible, maximize score
- **Fail condition**: HP reaches 0 (enemies that reach your base deal damage)
- **Scoring**: Base score per kill + combo multiplier + chain multiplier + danger zone bonus (closer enemies = more points)
- **Combo**: Each hit increases combo by 1. Missing or letting an enemy reach your base resets it
- **Difficulty**: Waves escalate every 10 seconds — enemies spawn faster and move quicker
- **Danger zone**: Enemies closer to your base give higher score bonus but are riskier

### Enemy Types

| Type | HP | Speed | Score | Color |
|------|----|-------|-------|-------|
| Grunt | 8 | 1.0 | 5 | Red |
| Runner | 5 | 1.5 | 8 | Orange |
| Tank | 20 | 0.6 | 15 | Brown |
| Elite | 15 | 1.0 | 20 | Pink |

## Controls

- **Mouse click**: Attack enemy at cursor position
- **SPACE / Click (title/gameover)**: Start / Restart

## Dev Status

- ✅ Core mechanic: click to attack enemies
- ✅ Overkill ripple to leftward enemies
- ✅ Combo system with multipliers
- ✅ Danger zone scoring bonus
- ✅ Wave-based difficulty escalation
- ✅ Screen shake feedback
- ✅ Particle effects on kills
- ✅ Floating score text
- ✅ Title screen and game over screen
- ✅ 45 headless logic tests

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/031_overkill_chain/main.py
```

## How to Test

```bash
uv run python prototypes/031_overkill_chain/test_imports.py
```
