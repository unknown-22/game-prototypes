"""test_imports.py — Headless logic tests for ANTIQUE AUCTION (326_antique_auction).

Uses the Game.__new__(Game) bypass pattern: pyxel is imported at module top but
never initialized, and every method under test avoids pyxel Rust calls.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    BAND_HI_START,
    BAND_LO_START,
    GAME_DURATION,
    LOT_FRAMES,
    MAX_V,
    MIN_V,
    OBSERVE_FRAMES,
    PRICE_END,
    PRICE_START,
    RESIDUAL,
    START_BANKROLL,
    FloatingText,
    Game,
    Lot,
    Particle,
    Phase,
)


def make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.best_bankroll = 0
    g.reset()
    return g


# ── Imports & constants ──


def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_constants():
    assert MIN_V == 40 and MAX_V == 200
    assert BAND_LO_START == 10 and BAND_HI_START == 230
    assert RESIDUAL == 25
    assert PRICE_START == 120 and PRICE_END == 220
    assert OBSERVE_FRAMES == 90 and LOT_FRAMES == 150
    assert START_BANKROLL == 1000 and GAME_DURATION == 3600


# ── reset / initial state ──


def test_reset_initial_state():
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.frame == 0
    assert g.bankroll == START_BANKROLL
    assert g.lots_bid == 0
    assert g.lots_passed == 0
    assert isinstance(g.lot, Lot)
    assert g.lot.age == 0
    assert MIN_V <= g.lot.value <= MAX_V
    assert g.particles == []
    assert g.floats == []
    assert g.results == []
    assert g.shake == 0 and g.flash == 0


def test_reset_preserves_seeded_rng():
    g1 = make_game(seed=7)
    g2 = make_game(seed=7)
    assert g1.lot is not None and g2.lot is not None
    assert g1.lot.value == g2.lot.value


# ── escalation (pure) ──


def test_residual_escalation():
    g = make_game()
    assert g._residual(0) == RESIDUAL
    assert g._residual(GAME_DURATION) == 40
    assert RESIDUAL <= g._residual(1800) <= 40


def test_lot_frames_escalation():
    g = make_game()
    assert g._lot_frames(0) == LOT_FRAMES
    assert g._lot_frames(GAME_DURATION) == 100
    assert 100 <= g._lot_frames(1800) <= 150


def test_observe_frames_escalation():
    g = make_game()
    assert g._observe_frames(0) == OBSERVE_FRAMES
    assert g._observe_frames(GAME_DURATION) == 50
    assert 50 <= g._observe_frames(1800) <= 90


# ── band math ──


def test_band_initial_wide():
    g = make_game()
    g.lot = Lot(value=120, age=0)
    lo, hi = g._band(g.lot, 0)
    assert lo == BAND_LO_START
    assert hi == BAND_HI_START


def test_band_narrowed_at_full_observe():
    g = make_game()
    g.lot = Lot(value=120, age=OBSERVE_FRAMES)
    lo, hi = g._band(g.lot, 0)
    assert lo == 120 - RESIDUAL
    assert hi == 120 + RESIDUAL


def test_band_never_reveals_exact_value():
    g = make_game()
    g.lot = Lot(value=120, age=10_000)
    lo, hi = g._band(g.lot, 0)
    assert lo < 120 < hi
    assert hi - lo == RESIDUAL * 2


def test_band_lo_hi_helpers():
    g = make_game()
    g.lot = Lot(value=120, age=OBSERVE_FRAMES)
    assert g._band_lo(g.lot, 0) == 120 - RESIDUAL
    assert g._band_hi(g.lot, 0) == 120 + RESIDUAL


def test_band_narrows_monotonically():
    g = make_game()
    g.lot = Lot(value=120, age=0)
    widths = []
    for age in (0, 30, 60, 90):
        g.lot.age = age
        lo, hi = g._band(g.lot, 0)
        widths.append(hi - lo)
    assert widths == sorted(widths, reverse=True)


# ── price math ──


def test_price_starts_low():
    g = make_game()
    g.lot = Lot(value=120, age=0)
    assert g._current_price(g.lot, 0) == PRICE_START


def test_price_climbs_toward_end():
    g = make_game()
    g.lot = Lot(value=120, age=0)
    p0 = g._current_price(g.lot, 0)
    g.lot.age = LOT_FRAMES // 2
    pmid = g._current_price(g.lot, 0)
    g.lot.age = LOT_FRAMES
    pend = g._current_price(g.lot, 0)
    assert p0 < pmid < pend


def test_price_capped_at_end():
    g = make_game()
    g.lot = Lot(value=120, age=LOT_FRAMES)
    assert g._current_price(g.lot, 0) == PRICE_END
    g.lot.age = LOT_FRAMES + 100
    assert g._current_price(g.lot, 0) == PRICE_END


def test_price_can_exceed_value():
    g = make_game()
    g.lot = Lot(value=MIN_V, age=LOT_FRAMES)
    assert g._current_price(g.lot, 0) > MIN_V


# ── bid ──


def test_bid_early_cheap_but_blind():
    g = make_game()
    g.phase = Phase.PLAYING
    g.lot = Lot(value=200, age=0)
    g._bid()
    assert g.bankroll == START_BANKROLL + (200 - PRICE_START)
    assert g.lots_bid == 1
    assert g.lots_passed == 0


def test_bid_late_loss():
    g = make_game()
    g.phase = Phase.PLAYING
    g.lot = Lot(value=40, age=LOT_FRAMES)
    before = g.bankroll
    g._bid()
    assert g.bankroll < before
    assert g.shake == 8
    assert g._last_profit < 0


def test_instant_bid_on_low_value_loses():
    # Regression: PRICE_START must exceed MIN_V so a blind instant bid on a
    # low-value lot is a real loss. (If PRICE_START <= MIN_V, mashing BID at
    # age 0 always profits and the "read the narrowing band" risk/reward dies.)
    g = make_game()
    g.phase = Phase.PLAYING
    g.lot = Lot(value=MIN_V, age=0)
    g._bid()
    assert g._last_profit < 0
    assert g.bankroll < START_BANKROLL


def test_bid_zero_profit_is_deal():
    g = make_game()
    g.phase = Phase.PLAYING
    g.lot = Lot(value=PRICE_END, age=LOT_FRAMES)
    g._bid()
    assert g._last_profit == 0
    assert g.bankroll == START_BANKROLL


def test_bid_records_result_and_new_lot():
    g = make_game()
    g.phase = Phase.PLAYING
    g.lot = Lot(value=200, age=0)
    g._bid()
    assert g.results == [200 - PRICE_START]
    assert g.lot.age == 0
    assert g._reveal_timer == 45
    assert g._reveal_value == 200


def test_bid_noop_outside_playing():
    g = make_game()
    g.phase = Phase.TITLE
    g.lot = Lot(value=200, age=0)
    g._bid()
    assert g.lots_bid == 0
    assert g.bankroll == START_BANKROLL


def test_bid_bankrupt():
    g = make_game()
    g.phase = Phase.PLAYING
    g.bankroll = 30
    g.lot = Lot(value=40, age=LOT_FRAMES)
    g._bid()
    assert g.bankroll <= 0
    assert g.phase == Phase.GAME_OVER
    assert g._game_over_reason_str == "BANKRUPT"


# ── sold to rival ──


def test_sold_to_rival():
    g = make_game()
    g.phase = Phase.PLAYING
    g.lot = Lot(value=120, age=LOT_FRAMES)
    g._resolve_sold_to_rival()
    assert g.lots_passed == 1
    assert g.lots_bid == 0
    assert g.bankroll == START_BANKROLL
    assert g.results == [None]
    assert g.lot.age == 0


# ── game over reason ──


def test_game_over_reason():
    g = make_game()
    g.bankroll = 0
    assert g._game_over_reason() == "BANKRUPT"
    g.bankroll = 500
    assert g._game_over_reason() == "TIME UP"


def test_game_over_updates_best():
    g = make_game()
    g.bankroll = 1500
    g.best_bankroll = 1200
    g._game_over("TIME UP")
    assert g.best_bankroll == 1500
    assert g.phase == Phase.GAME_OVER
    g.best_bankroll = 2000
    g.bankroll = 100
    g._game_over("BANKRUPT")
    assert g.best_bankroll == 2000


# ── results strip trimming ──


def test_results_trimmed_to_max():
    g = make_game()
    for _ in range(20):
        g._record_result(10)
    assert len(g.results) == 12


# ── particles / floating text ──


def test_burst_adds_particles():
    g = make_game()
    g._burst(160, 80, 11, 12, 2.0, 20, 40)
    assert len(g.particles) == 12
    assert all(isinstance(p, Particle) for p in g.particles)


def test_spawn_float():
    g = make_game()
    g._spawn_float(160, 80, "+$50", 11)
    assert isinstance(g.floats[-1], FloatingText)
    assert g.floats[-1].text == "+$50"
    assert g.floats[-1].life == 30


def test_update_particles_removes_dead():
    g = make_game()
    g._spawn_particle(160, 80, 11, 1.0, 1, 1)
    g._update_particles()
    assert g.particles == []


def test_update_floats_removes_dead():
    g = make_game()
    g._spawn_float(160, 80, "+$1", 11)
    g.floats[-1].life = 1
    g._update_floats()
    assert g.floats == []


# ── button bounds ──


def test_bid_button_bounds():
    g = make_game()
    assert g._button_bid_contains(240, 210)
    assert not g._button_bid_contains(10, 10)


# ── scale mapping ──


def test_scale_x_endpoints():
    g = make_game()
    assert g._scale_x(0) == 40
    assert g._scale_x(250) == 280


if __name__ == "__main__":
    tests = [
        (k, v)
        for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS {name}")
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    if passed != len(tests):
        sys.exit(1)
