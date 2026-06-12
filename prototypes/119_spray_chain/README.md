# 119 — SPRAY CHAIN

**Source**: game_idea_factory #1 (Score 32.75) — deckbuilder/space-mining hooks "synthesis compression + CA grid fills up" reinterpreted into graffiti/spray-paint.

**Engine**: Pyxel 2.x, 320×240, display_scale=2

## Gameplay

Graffiti spray-paint color-match game. Hold left mouse button to spray paint onto a 20×15 grid wall.

- **Same-color consecutive sprays** build COMBO
- **COMBO ≥ 4** activates **SUPER SPRAY** (5s rainbow, 5×5 pattern, 3× score)
- **Wrong-color spray** resets COMBO and adds HEAT (+15)
- **CA drip**: painted cells drip downward every 0.5s (10% chance)
- **HEAT = 100** → game over (canvas ruined)
- **60-second timer** to maximize score

## Core Mechanic

1. Move mouse to aim, hold left button to spray
2. Same-color chain → COMBO → SUPER SPRAY
3. Decide: keep same color for COMBO (risk HEAT on wrong spray) or switch colors (safe, resets COMBO)
4. Drips spread paint automatically (CA mechanic)

## Controls

| Input | Action |
|-------|--------|
| **Mouse move** | Aim spray can |
| **Left mouse button (hold)** | Spray paint |
| **Mouse wheel** | Cycle paint color |
| **1/2/3/4 keys** | Select paint color |
| **Enter** | Start / Restart |

## Risk & Reward

- **Maintain same-color COMBO** → higher score multiplier, SUPER SPRAY
- **Switch color** → COMBO reset, HEAT +15
- **HEAT decays** (-1 every 12 frames) → brief pauses let HEAT drop
- Choose between safe switch (low HEAT, low score) or risky chain (high score, possible HEAT spike)

## Dev Status

- ✅ Single-file Pyxel prototype (677 lines)
- ✅ 41 headless tests (all pass)
- ✅ ruff + ty clean
- ✅ Web build deployed
- ✅ Fully autonomous OpenCode CLI generation

## How to Run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/119_spray_chain/main.py
```

## 体験仮説

「同じ色を連続で塗り続けてCOMBOを積み、SUPER SPRAYで画面が一気に虹色に染まる爆発的爽快感」と「色を変えるか継続するかのリスク判断による緊張感」を交互に味わえる。

## 検証指標

- SUPER SPRAY発動回数
- 最大COMBO数
- 塗りつぶしカバレッジ率
- HEATゲームオーバー頻度 vs タイムアップ頻度
