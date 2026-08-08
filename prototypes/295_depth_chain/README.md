# DEPTH CHAIN — Submarine Deep-Sea Color-Match Explorer

## Source
Based on game_idea_factory #1 (Score 31.65): alchemy dice/bag roguelite
- "synthesis compression" → same-color COMBO chain → SUPER SONAR
- "future hand as cost" → depth commitment (deeper = higher risk/reward)

## Engine
- Pyxel 2.x, 320×240, 60fps
- First submarine / deep-sea exploration genre in collection

## Experience Hypothesis
「深海の高リスク地帯で同色の生物を連続採取し、SUPER SONARで広範囲を虹色自動マッチして大量スコアを爆発させる — 酸素と熱のプレッシャーの中で上昇タイミングを計るスリリングな判断」

## Core Mechanic
- Arrow keys move submarine through ocean depths
- 4 bioluminescent creature colors: RED (jellyfish), LIME (anglerfish), DARK_BLUE (squid), YELLOW (sea-star)
- Collect same-color creatures consecutively = COMBO chain
- COMBO >= 4 triggers SUPER SONAR (300f rainbow mode, any-color match, 3x score, HEAT frozen, 2x collection radius)
- Depth multiplier: 1.0x at surface → 3.0x at abyss
- HEAT risk: mismatch +15, depth pressure at depth>50, decay -0.02/f, cap 100 = game over
- 60s timer

## Controls
- Arrow keys: Move submarine
- SPACE / CLICK: Start / Restart

## Dev Status
- ✅ Complete gameplay loop: Title → Playing → GameOver → Restart
- ✅ COMBO chain + SUPER SONAR mechanic
- ✅ Depth-based risk/reward system
- ✅ HEAT risk management
- ✅ Particle system + floating text
- ✅ Difficulty escalation
- ✅ 41 headless tests (ruff + ty OK)
- ✅ Web build deployed

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/295_depth_chain/main.py
```
