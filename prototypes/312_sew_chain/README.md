# SEW CHAIN

Tailor / sewing color-match COMBO chain prototype. First sewing/tailor genre in the collection.

## Source

Reinterpreted from `game_idea_factory` idea #1 (Score 31.8, 2026-08-16 batch):
"same card consecutively → mutate (strengthen/explode)" + "future hand as cost" hooks,
mapped onto a tailor's workshop:
- "synthesis compression" → same-color COMBO → SUPER STITCH
- "future hand as cost" → finite THREAD spool + RETHREAD (spend safety now vs. keep stitching)

## Engine

- Pyxel 2.x, 320x240 @ 60fps
- 8 fabric patches in a horizontal row (24x24, y=110, x=16+i*36)

## Gameplay

- **Needle color** auto-cycles (20f→12f over 60s).
- **CLICK** a patch to sew it: match (patch color == needle color) → `combo+1`,
  `score += 10*combo*mult`, patch respawns with a new color. Mismatch → `HEAT+15`,
  combo reset, thread wasted (patch stays).
- **COMBO ≥ 4** → SUPER STITCH (300f rainbow needle, any-color match, 3x score,
  HEAT frozen, thread NOT consumed).
- **Finite THREAD spool** (THREAD_MAX=12): every sew consumes 1 thread. At 0 you
  cannot sew. Press **R** to RETHREAD — a 120f pause that restores thread to max,
  resets combo, +5 HEAT.
- **HEAT** risk: mismatch +15, rethread +5, decay −0.02/f (frozen in SUPER/RETHREAD).
  HEAT ≥ 100 → "NEEDLE SNAPPED" game over. 60s timer → "TIME UP".

### Experience hypothesis

「針の色が合う布パッチを次々に縫ってCOMBOを伸ばし、SUPER STITCHの虹色で一気に縫い上げる快感。ただし糸は有限で、尽きると縫えない。糸を巻き直す(RETHREAD)タイミング＝安全な色巡回の隙を狙う駆け引きが生まれる」

### The "most fun moment"

Same-color patches sewn consecutively explode into a rainbow SUPER STITCH, while a
finite thread spool forces a "re-thread now (safe) vs keep stitching (greedy)" decision.

## Controls

- **CLICK** — sew a patch
- **R** — rethread (restore thread, reset combo)
- **SPACE** — start / retry

## Dev status

- ✅ Core loop: sew → combo → SUPER STITCH → thread/rethread decision
- ✅ 3 screens: Title / Playing (+ RETHREADING) / Game Over
- ✅ Particle system + floating text + screen shake
- ✅ 34 headless tests (Game.__new__ bypass pattern), ruff + ty clean
- ✅ Web build at `docs/312_sew_chain.html`

## How to run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/312_sew_chain/main.py
```

## Tests

```bash
uv run pytest prototypes/312_sew_chain/test_imports.py -q
```
