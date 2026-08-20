# Rune Break (魔法解析)

Mastermind-style code-deduction arcade game. Break hidden rune-locks by logically
deducing a secret 4-rune sequence from guess feedback.

## Source

Reinterpreted from game_idea_factory idea #1 (Score 31.75, 魔法学院/ルール改変 ダイス/バッグ構築):

- Hook "ログ/リプレイが資産（前回の行動が次回のカードになる）" → the guess history
  board IS the deduction aid (every past guess + its feedback stays on screen).
- The "ルール改変" theme → escalating difficulty (more rune colors per lock).

This is the **first pure logic-deduction / code-breaking genre** in the collection,
and the 8th in the 323-329 "breakaway" series that deliberately abandons the
saturated color-match COMBO/HEAT formula: no color matching reflex, no COMBO, no
HEAT — pure deduction + a limited-resource hint trade.

## Experience hypothesis (体験仮説)

「限られたフィードバックから隠された符呪の並びを推理し、候補が1つに絞り込めた
瞬間に解錠する快感」

## Engine

Pyxel 2.x, 320×240 @60fps, single file `main.py`.

## Gameplay

- A hidden code of 4 distinct runes (sampled from the available color palette).
- You make guesses; each guess returns feedback:
  - **exact** (white squares) = runes that are the right color in the right position
  - **misplaced** (gray circles) = right color, wrong position
- Deduce the code before your **8 guesses per lock** run out.
- **3 lives**. Fail a lock (8 guesses) → lose a life; 3 lives lost → game over.

## Risk / reward

- **ORACLE HINT (H)**: spend 1 guess to reveal the true rune at the cursor slot.
  Revealed slots lock and show the true color. Spending a guess both lowers the
  solve bonus AND brings you one step closer to failing the lock — guaranteed
  information vs a shrinking budget.
- **Solve bonus scales with efficiency**: `(8 - guesses_used + 1) × 150 + streak × 100`.
  Solving in 1 guess = 1300, in 8 guesses = 250.

## Difficulty escalation

Codes broken: 0 → 4 colors, 1 → 5 colors, 2+ → 6 colors (still distinct per code).

## Controls

| Input | Action |
|---|---|
| ← → / A D | move cursor between rune slots |
| 1–6 | place the numbered palette color into the cursor slot |
| SPACE / ENTER | submit guess |
| H | oracle hint (reveal cursor-slot rune, costs 1 guess) |
| X / BACKSPACE | clear cursor slot |
| Mouse | click slots / swatches / SUBMIT / HINT |

## Dev status

- ✅ Title / Playing / Game Over screens
- ✅ Mastermind feedback (exact / misplaced)
- ✅ Oracle hint risk/reward
- ✅ Escalating color count
- ✅ Lives + per-lock guess budget
- ✅ Streak + efficiency scoring
- ✅ Particle burst + floating text + screen shake
- ✅ 31 headless tests, ruff + ty pass
- ⬜ Sound effects

## How to run

```bash
cd ~/repos/game-prototypes
uv run python prototypes/330_rune_break/main.py
```
