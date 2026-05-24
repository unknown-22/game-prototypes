# NETWORK SURGE (062_network_surge)

**Source**: Game Idea Factory #1 (Score 32.0, 魔法学院デッキ構築)
- Original hooks: "効果が『合成』されて1枚に圧縮" + "UIの連鎖演出"
- Reinterpreted as: same-color consecutive hacks → COMBO → SURGE BFS chain reaction
- **Genre**: Hacking network intrusion (Uplink-style) — FIRST in collection

## Engine
- Pyxel 2.x, 320×240, display_scale=2

## Gameplay

**体験仮説**: 「次はどの色をハックするか選ぶ緊張感と、SURGEが発動して一気にノードが連鎖感染する爽快感」

**Core mechanic**: Click same-color DATA nodes consecutively to build COMBO. COMBO ≥ 4 triggers SURGE (BFS chain reaction auto-hacking all reachable same-color nodes).

### Rules
- 8×6 grid of nodes: DATA (colored, hackable), ICE (trace threat), FIREWALL (blocks BFS)
- Same-color consecutive hacks → COMBO increases, score multiplier grows
- Wrong-color hack → COMBO resets to 0, TRACE +5%
- COMBO ≥ 4 → SURGE: BFS auto-hack all reachable same-color DATA nodes
- TRACE fills over time (+1%/sec) and from ICE nodes
- TRACE ≥ 100% → GAME OVER (DETECTED!)
- All DATA nodes hacked → VICTORY (NETWORK SECURED!)

### Risk/Reward
- **Risk**: wrong color → COMBO reset + TRACE penalty; waiting → TRACE rises
- **Reward**: same-color chain → multiplier ×2, ×3, ×4; COMBO 4+ → SURGE (500 pts/node)

## Controls
| Input | Action |
|---|---|
| Mouse click | Select and hack a DATA node |
| SPACE | Start game from title |
| R / Mouse click | Retry from game over |

## Node Types
| Type | Color | Hackable | Effect |
|---|---|---|---|
| DATA | RED/GREEN/CYAN/YELLOW | Yes | Score + COMBO |
| ICE | GRAY | No | +0.3%/sec TRACE each |
| FIREWALL | DARK BLUE | No | Blocks SURGE BFS |

## Scoring
- Each DATA hack: 100 × COMBO multiplier
- SURGE auto-hack: +500 per node
- Max COMBO tracked for leaderboard

## Dev Status
- ✅ Core hacking mechanic with COMBO tracking
- ✅ SURGE BFS chain reaction with FIREWALL blocking
- ✅ TRACE system (time + ICE + penalty)
- ✅ Title / Playing / Surge Anim / Game Over / Victory phases
- ✅ Particle system + floating text + screen shake
- ✅ 28 headless tests
- ✅ ruff + ty clean
- ✅ Web build deployed

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/062_network_surge/main.py
```
