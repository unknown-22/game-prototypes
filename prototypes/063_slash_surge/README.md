# SLASH SURGE — Prototype 063

**Source**: Idea #1 (Score 32.0) from 2026-05-24 generation — 錬金術（合成）デッキ構築
reinterpreted into color-match slashing action.

**Engine**: Pyxel 2.x, 320×240, display_scale=2

## Experience Hypothesis
「分裂した破片があふれる中で同色を狙い続け、SURGE一掃で画面が一気にクリアになるカタルシス」
(Slashing an orb and watching it split creates panic; chaining same-color slashes for a SURGE explosion creates cathartic relief.)

## Gameplay
- Colored orbs (RED/GREEN/BLUE/YELLOW) spawn from screen edges
- **Click + drag** to draw a slash line through orbs
- Each slashed regular orb **SPLITS** into 2 smaller fragments (random colors)
- Slashing same-color orbs consecutively builds **COMBO**
- Slashing a wrong color **resets** COMBO to 1
- COMBO ≥ 5 triggers **SURGE**: all same-color fragments are destroyed in a BFS chain reaction for massive bonus score
- If orb count > 25 → **OVERLOAD**: HP drains over time
- Slashing fragments removes them (reduces clutter) but still builds combo

## Controls
| Input | Action |
|---|---|
| Mouse left-click + drag | Draw slash line |
| Mouse release | Process slash (hit orbs get split/scored) |
| Click | Start game / Retry |

## Risk & Reward
- **Risk**: splitting orbs increases screen clutter → overload danger
- **Reward**: chaining same-color slashes gives higher combo multiplier (1×→2×→3×→5×)
- **Risk**: waiting for more same-color orbs to appear for a bigger SURGE
- **Reward**: SURGE destroys all same-color fragments, clearing screen + awarding bonus score
- Slashing fragments is a defensive play — removes clutter but gives single-hit score only

## Dev Status
- ✅ Core slash mechanic (mouse drag, segment-circle intersection)
- ✅ Orb split into 2 fragments
- ✅ COMBO system with multiplier scaling
- ✅ SURGE BFS chain reaction
- ✅ OVERLOAD damage mechanic
- ✅ Particle effects (slash sparks, explosion bursts)
- ✅ HUD (score, HP bar, combo, SURGE/overload warnings)
- ✅ Title → Playing → Game Over → Retry loop
- ✅ 28 headless tests
- ✅ Web build

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/063_slash_surge/main.py
```

## Next Improvements
- Screen shake on SURGE
- Sound effects
- Orb color variety / special orbs
- Score popup floating text
