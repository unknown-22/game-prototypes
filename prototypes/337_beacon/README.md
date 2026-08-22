# BEACON — Avalanche Beacon Search & Rescue

Buried skiers are invisible. Your only clue is a scalar signal-strength meter that
grows as you approach. Walk the snowfield by feel, triangulate the strongest signal,
and DIG at the exact spot to rescue victims before the avalanche closes in.

## 体験仮説 (experience hypothesis)

「場所が見えない中で信号の強さだけを頼りに進み、強くなった瞬間に掘ると、
見つけた時の安堵と得をした感じがする」— and greedy early digs feel like gambles.

## 実装したコアループ (implemented core loop)

1. **見る** — signal bar (0..100) + beep-rate pulse tells you only *how close* you are, never *where*.
2. **判断する** — dig early at a weak signal (fast, risky) vs keep triangulating (slow, safe).
3. **操作する** — ARROWS/WASD move (diagonal normalized), SPACE digs (0.5s channel, you're locked in).
4. **結果が返る** — rescue = score + combo + +5s time; miss = combo reset + -3s time.

## リスクとリターン (risk/reward)

- Digging near the victim (strong signal) gives `rescue_score(combo) = 100 × combo_multiplier`,
  builds a combo (up to 4.0×), and **extends** the avalanche timer (+5s).
- Digging blind (weak signal) resets the combo and **costs** time (-3s).
- More victims spawn over time (`spawn_interval` 720f → 300f), so the field gets harder.

## うまくいっている点 (what works)

- Partial observation is pure: `signal_strength(dist) = clamp(100 - dist*0.8, 0, 100)`,
  a scalar with no direction — the whole game rides on moving-and-watching the meter.
- Single mechanic, no color-match/COMBO/HEAT formula (continues the 323+ breakaway series).

## 次に改善するなら最初に触る点 (first thing to improve)

- Add a **directional** hint tool (a "coarse bearing" probe with a cooldown) to make the
  search feel more like real avalanche transceivers and less like pure hot/cold.

## Run

```bash
uv run python prototypes/337_beacon/main.py        # needs a display (Windows/WSL+X)
uv run pytest prototypes/337_beacon/test_imports.py # headless
```

## Source

Reinterpreted from game_idea_factory idea #1 (Score 32.15, hacking auto-shooter) — the
"partial observation" hook ("敵の意図が確率でしか見えない") → scalar signal search.
First "search & rescue / signal triangulation" genre in the collection.
