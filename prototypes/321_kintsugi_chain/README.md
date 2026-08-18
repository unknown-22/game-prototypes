# KINTSUGI CHAIN (金継ぎ)

Repair a broken ceramic vessel with gold, making it more beautiful than before the break.
A color-match COMBO chain arcade prototype. **First kintsugi genre in the collection.**

## Source
Reinterpreted from game_idea_factory #1 (Score 32.55, alchemy deckbuilder roguelite):
- hook "log/replay as asset (previous actions become next cards)" → **completed cracks become
  gold veins that amplify future completion bonuses** (your past repairs literally pay forward)
- hook "CA grid fills up (infection/growth)" → the vessel **keeps cracking over time** (new cracks
  spawn = difficulty escalation + scoring opportunity)
- resources "risk, slots" → HEAT (mismatch penalty) + a finite set of crack slots (MAX_CRACKS=6)

## Engine
Pyxel 2.x, 320×240 @ 60fps, display_scale=2, single-file `main.py` (404 lines).

## Gameplay
- 4 cracks radiate from the vessel center; each crack = 4 colored segments (RED/LIME/DARK_BLUE/PURPLE).
- A gold-brush color auto-cycles (20f→12f) through the 4 colors.
- **CLICK** an unfilled segment whose color matches the brush → it fills GOLD. Same-color
  consecutive fills = COMBO chain (score = 10×combo×mult).
- **COMBO≥4** → SUPER KINTSUGI (300f rainbow, any-color match, 3× score, HEAT frozen).
- Filling all 4 segments of a crack **COMPLETES** it → a gold vein, bonus = 50×combo×completed_veins
  (the bonus grows with how many veins you've already finished).
- Completing every crack = **VESSEL RESTORED** (+500, fresh vessel, combo preserved).
- Mismatch (wrong color) = HEAT+15 + combo reset.
- **Fail**: HEAT≥100 (VESSEL SHATTERED) or 60s timer (TIME UP).

## Controls
- **Mouse click** — fill a segment (title screen: click to start)
- **ENTER** — start from title
- **R / ENTER** — restart from game over

## Experience Hypothesis (体験仮説)
「壊れた器の割れ目を一つずつ金で継いでいくほど、あとから完成する割れ目ほど大きなボーナスになり、
最後の一継ぎで器全体に金色の流れが走って大得点が弾ける」— the "log/replay as asset" hook made
mechanical: past repairs (gold veins) amplify future rewards, so a skilled player snowballs.

## Core Loop (実装したコアループ)
見る (brush color + cracks) → 判断する (chase combo vs target a crack to bank the vein bonus) →
操作する (click) → 結果 (gold fill / vein complete / wrong) → 次の判断。

## What Works (うまくいっている点)
- The vein-network bonus (50×combo×completed_veins) cleanly realizes "log/replay as asset": every
  crack completion is strictly worth more than the last, creating a satisfying snowball.
- Vessel restoration carries the combo across a fresh board, rewarding sustained skill.
- Standard COMBO/SUPER/HEAT/timer scaffold keeps the loop tight and legible.

## First Improvement Target (次に改善するなら最初に触る点)
- The crack-completion bonus currently scales linearly with vein count only (×1,×2,×3,…); a
  super-linear reward (×1,×2,×4,…) or a visual "gold flow" that ripples through connected veins on
  each completion would amplify the "most fun moment" further.
- Vessel restoration resets `completed_veins` to 0, cutting the snowball each vessel; consider
  carrying a partial multiplier across restorations for a longer run arc.

## Dev Status
- ✅ Single-file Pyxel prototype (title / game / game-over screens)
- ✅ COMBO chain + SUPER KINTSUGI + HEAT + 60s timer
- ✅ Vein-network completion bonus (log/replay as asset)
- ✅ Vessel-restoration loop with combo carry-over
- ✅ 25 headless tests, ruff + ty clean
- ⬜ Visual "gold flow" animation on vein completion
- ⬜ Super-linear vein bonus curve

## How to Run
```bash
cd ~/repos/game-prototypes
uv run python prototypes/321_kintsugi_chain/main.py     # desktop (needs display)
uv run pytest prototypes/321_kintsugi_chain/test_imports.py
```
