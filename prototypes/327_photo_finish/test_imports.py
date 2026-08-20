"""Headless logic tests for 327_photo_finish.

Run:  uv run python prototypes/327_photo_finish/test_imports.py

Tests the pure-logic methods (no pyxel input) via the `_make_game` factory,
which builds a Game through `Game.__new__` to bypass pyxel.init.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    FINISH_X,
    FORM_MAX,
    FORM_MIN,
    GAME_DURATION,
    HORSES,
    MAX_BET,
    MIN_BET,
    PADDOCK_FRAMES_MIN,
    PADDOCK_FRAMES_START,
    RACE_SPREAD_MAX,
    RACE_SPREAD_MIN,
    START_BANK,
    START_X,
    FloatingText,
    Game,
    Horse,
    Particle,
    Phase,
    _make_game,
)


def approx(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(a - b) <= tol


def fresh_game() -> Game:
    """Build a game with a seeded RNG and place it into the PADDOCK phase."""
    g = _make_game(seed=42)
    g.phase = Phase.PADDOCK
    return g


def test_dataclasses_and_constants() -> None:
    assert HORSES == 5
    assert START_BANK == 1000
    assert MIN_BET == 50
    assert MAX_BET == 1000
    assert FINISH_X == 280
    assert START_X == 24

    h = Horse(0, 8, 75.0, 4.0, 4.0, 50.0, 100.0, 0.0, 24.0)
    assert h.form == 75.0
    assert h.odds == 4.0
    assert h.pos_x == 24.0

    p = Particle(1.0, 2.0, 0.5, -0.5, 10, 8)
    assert p.life == 10
    t = FloatingText(0.0, 0.0, "WIN", 70, 11)
    assert t.text == "WIN"


def test_generate_horses_invariants() -> None:
    g = fresh_game()
    g._generate_horses()
    assert len(g.horses) == HORSES
    for h in g.horses:
        assert FORM_MIN <= h.form <= FORM_MAX
        assert 1.5 <= h.odds <= 8.0
        assert 1.5 <= h.true_odds <= 8.0
        # full uncertainty at generation time
        assert h.gauge_lo == FORM_MIN
        assert h.gauge_hi == FORM_MAX
        assert h.pos_x == float(START_X)
        assert h.race_speed == 0.0


def test_make_game_is_deterministic() -> None:
    a = _make_game(seed=7)
    b = _make_game(seed=7)
    assert [h.form for h in a.horses] == [h.form for h in b.horses]
    assert [h.odds for h in a.horses] == [h.odds for h in b.horses]


def test_gauge_band_narrows_over_paddock() -> None:
    g = fresh_game()
    g._paddock_start_frames = 240
    g.paddock_frames = 240
    assert approx(g._gauge_band(), 25.0)
    g.paddock_frames = 120
    assert approx(g._gauge_band(), 16.5)  # halfway: 25 - 17*0.5
    g.paddock_frames = 0
    assert approx(g._gauge_band(), 8.0)  # GAUGE_BAND_MIN


def test_narrow_gauges_never_reveals_exact_form() -> None:
    g = fresh_game()
    g._paddock_start_frames = 240
    g.paddock_frames = 0  # maximally narrowed
    g._generate_horses()
    for h in g.horses:
        h.form = 80.0
        h.gauge_lo = 50.0
        h.gauge_hi = 100.0
    g._narrow_gauges()
    for h in g.horses:
        # band at progress 1.0 == 8.0, so gauge is [72, 88] — form hidden
        assert h.gauge_lo < 80.0
        assert h.gauge_hi > 80.0
        assert h.gauge_lo >= 50.0
        assert h.gauge_hi <= 100.0


def test_drift_odds_moves_toward_true_odds() -> None:
    g = fresh_game()
    g._generate_horses()
    h = g.horses[0]
    h.true_odds = 3.0
    h.odds = 5.0  # overpriced (mispriced high)
    for _ in range(50):  # drift is gradual (0.004/frame) — accumulate
        g._drift_odds()
    assert h.odds < 5.0  # drifted down toward 3.0
    assert h.odds >= 3.0
    h.true_odds = 7.0
    h.odds = 2.0  # underpriced
    for _ in range(50):
        g._drift_odds()
    assert h.odds > 2.0  # drifted up toward 7.0


def test_lock_bet_deducts_stake_and_starts_race() -> None:
    g = fresh_game()
    g.bankroll = 1000
    g.stake = 200
    g.selected = 0
    odds_before = g.horses[g.selected].odds
    g._lock_bet()
    assert g.bankroll == 800
    assert g._bet_stake == 200
    assert approx(g._bet_odds, odds_before)
    assert g._bet_placed is True
    assert g.phase is Phase.RACE
    assert g.winner_lane is None
    for h in g.horses:
        assert h.race_speed != 0.0


def test_lock_bet_clamps_stake_to_bankroll() -> None:
    g = fresh_game()
    g.bankroll = 30  # below MIN_BET
    g.stake = 200
    g.selected = 0
    g._lock_bet()
    assert g._bet_stake == 30
    assert g.bankroll == 0


def test_win_payout() -> None:
    g = fresh_game()
    g.bankroll = 1000
    g.stake = 200
    g.selected = 2
    g._lock_bet()  # deducts 200 -> 800
    bank_after_lock = g.bankroll
    stake = g._bet_stake
    odds = g._bet_odds
    g.winner_lane = 2  # our horse wins
    g._resolve_result()
    assert g.bankroll == bank_after_lock + round(stake * odds)
    assert g._last_result == "WIN"
    assert g.best_bankroll >= g.bankroll
    assert g.phase is Phase.RESULT


def test_lose_payout_no_change() -> None:
    g = fresh_game()
    g.bankroll = 1000
    g.stake = 200
    g.selected = 1
    g._lock_bet()  # 800
    bank_after_lock = g.bankroll
    g.winner_lane = 3  # someone else wins
    g._resolve_result()
    assert g.bankroll == bank_after_lock  # no money returned on loss
    assert g._last_result == "LOSE"
    assert g.phase is Phase.RESULT


def test_bankrupt_goes_to_game_over() -> None:
    g = fresh_game()
    g.bankroll = 60
    g.stake = 60
    g.selected = 0
    g._lock_bet()  # bankroll -> 0
    g.winner_lane = 1  # lose
    g._resolve_result()
    assert g.phase is Phase.GAME_OVER
    assert g.game_over_reason() == "BANKRUPT"
    assert g.score == 0


def test_update_race_detects_winner() -> None:
    g = fresh_game()
    g.phase = Phase.RACE
    for h in g.horses:
        h.race_speed = 50.0
        h.pos_x = float(START_X)
    g.horses[1].pos_x = FINISH_X - 0.1
    g._update_race()
    assert g.winner_lane == 1
    assert g.phase is Phase.RESULT


def test_update_paddock_auto_locks_at_zero() -> None:
    g = fresh_game()
    g.phase = Phase.PADDOCK
    g.paddock_frames = 1
    g.bankroll = 1000
    g.stake = 100
    g.selected = 0
    g._update_paddock()
    assert g.paddock_frames <= 0
    assert g.phase is Phase.RACE  # auto-locked
    assert g.bankroll == 900


def test_update_result_advances_to_next_paddock() -> None:
    g = fresh_game()
    g.phase = Phase.RESULT
    g.result_frames = 1
    g.bankroll = 1000
    g._update_result()
    assert g.phase is Phase.PADDOCK
    assert g.winner_lane is None
    assert g._bet_placed is False


def test_race_spread_escalates() -> None:
    g = fresh_game()
    g.frame = 0
    assert approx(g._race_spread(), RACE_SPREAD_MIN)
    g.frame = GAME_DURATION
    assert approx(g._race_spread(), RACE_SPREAD_MAX)
    g.frame = GAME_DURATION // 2
    assert approx(g._race_spread(), (RACE_SPREAD_MIN + RACE_SPREAD_MAX) / 2)


def test_paddock_frames_escalates() -> None:
    g = fresh_game()
    g.frame = 0
    assert g._paddock_frames_start() == PADDOCK_FRAMES_START
    g.frame = GAME_DURATION
    assert g._paddock_frames_start() == PADDOCK_FRAMES_MIN


def test_timer_time_up() -> None:
    g = fresh_game()
    g.phase = Phase.PADDOCK
    g.frame = GAME_DURATION - 1
    g._update_timer()
    assert g.frame == GAME_DURATION
    assert g.phase is Phase.GAME_OVER
    assert g.game_over_reason() == "TIME UP"
    assert g.score == g.bankroll


def test_timer_does_not_trigger_early() -> None:
    g = fresh_game()
    g.phase = Phase.PADDOCK
    g.frame = 100
    g._update_timer()
    assert g.frame == 101
    assert g.phase is Phase.PADDOCK


def test_start_paddock_regenerates_horses() -> None:
    g = fresh_game()
    old_forms = [h.form for h in g.horses]
    g._start_paddock()
    assert g.phase is Phase.PADDOCK
    assert len(g.horses) == HORSES
    # new horses have fresh (possibly different) forms and full gauge
    for h in g.horses:
        assert h.gauge_lo == FORM_MIN
        assert h.gauge_hi == FORM_MAX
        assert h.pos_x == float(START_X)
    _ = old_forms


def _run() -> None:
    tests = [
        v
        for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {t.__name__}: {exc!r}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    _run()
