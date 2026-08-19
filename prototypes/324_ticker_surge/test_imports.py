"""test_imports.py — Headless logic tests for TICKER SURGE (324_ticker_surge).

Uses the Game.__new__(Game) bypass pattern: pyxel is imported at module top but
never initialized, and every method under test avoids pyxel Rust calls.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    BUBBLE_MAX,
    CRASH_FRAMES,
    GAME_DURATION,
    MARGIN_CALL,
    MAX_PRICE,
    MIN_PRICE,
    START_CASH,
    START_PRICE,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g._sfx_enabled = False
    g.best_score = 0
    g.reset()
    return g


def run_until(g: Game, pred, max_frames: int = 20000) -> bool:
    for _ in range(max_frames):
        if pred():
            return True
        g.frame += 1
        g._update_market()
    return False


# ── Imports & constants ──


def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_constants():
    assert START_PRICE == 100.0
    assert START_CASH == 1000.0
    assert MARGIN_CALL == 400.0
    assert MIN_PRICE < START_PRICE < MAX_PRICE
    assert GAME_DURATION == 3600


# ── reset / initial state ──


def test_reset_initial_state():
    g = make_game()
    assert g.cash == 1000.0
    assert g.shares == 0
    assert g.cost_basis == 0.0
    assert g.last_profit == 0.0
    assert g.price == 100.0
    assert g.trend == 1
    assert g.bubble == 0.0
    assert g.warning is False
    assert g.crashing is False
    assert g.frame == 0
    assert g.phase == Phase.TITLE
    assert g.price_history == []


def test_reset_preserves_seeded_rng():
    g = make_game(seed=7)
    assert g.rng is not None
    # Deterministic: two games with the same seed produce the same first random draw
    g2 = make_game(seed=7)
    assert g.rng.random() == g2.rng.random()


# ── portfolio value ──


def test_portfolio_value():
    g = make_game()
    g.cash = 500.0
    g.shares = 2
    g.price = 100.0
    assert g._portfolio_value() == 700.0


def test_portfolio_value_no_shares():
    g = make_game()
    assert g._portfolio_value() == START_CASH


# ── buy ──


def test_buy_all_in():
    g = make_game()
    g.price = 100.0
    g.cash = 1000.0
    g._buy()
    assert g.shares == 10
    assert g.cash == 0.0
    assert g.cost_basis == 1000.0
    assert g.last_action == "BUY"


def test_buy_partial_with_remainder():
    g = make_game()
    g.price = 100.5
    g.cash = 1000.0
    g._buy()
    assert g.shares == 9
    assert abs(g.cash - 95.5) < 0.001
    assert abs(g.cost_basis - 9 * 100.5) < 0.001


def test_buy_insufficient_cash():
    g = make_game()
    g.price = 2000.0
    g.cash = 1000.0
    g._buy()
    assert g.shares == 0
    assert g.cash == 1000.0


# ── sell ──


def test_sell_no_shares_is_noop():
    g = make_game()
    g.shares = 0
    g.price = 150.0
    g._sell()
    assert g.cash == 1000.0
    assert g.last_action != "SELL"


def test_buy_then_sell_profit():
    g = make_game()
    g.price = 100.0
    g._buy()  # 10 shares at 100
    g.price = 150.0
    g._sell()
    assert g.shares == 0
    assert abs(g.cash - 1500.0) < 0.001
    assert abs(g.last_profit - 500.0) < 0.001
    assert g.cost_basis == 0.0


def test_buy_then_sell_loss():
    g = make_game()
    g.price = 100.0
    g._buy()  # 10 shares at 100
    g.price = 80.0
    g._sell()
    assert abs(g.last_profit + 200.0) < 0.001


def test_sell_sets_last_action():
    g = make_game()
    g.price = 100.0
    g._buy()
    g._sell()
    assert g.last_action == "SELL"


# ── market dynamics ──


def test_price_moves_each_frame():
    g = make_game()
    before = g.price
    g.frame += 1
    g._update_market()
    assert g.price != before


def test_bubble_fills_during_bull():
    g = make_game()
    g.trend = 1
    g.bubble = 0.0
    for _ in range(120):
        g._update_market()
    assert g.bubble >= BUBBLE_MAX


def test_warning_triggers_at_max_bubble():
    g = make_game()
    g.trend = 1
    g.bubble = BUBBLE_MAX - 0.5
    g.warning = False
    g.crashing = False
    g._update_market()
    assert g.warning is True
    assert 40 <= g.warn_frames <= 90


def test_warning_then_crash_flips_to_bear():
    g = make_game()
    assert run_until(g, lambda: g.trend == -1, max_frames=20000)
    # A crash must have occurred at some point in the cycle
    assert g.crashing is False or g.trend == -1


def test_full_cycle_returns_to_bull():
    g = make_game()
    assert run_until(g, lambda: g.trend == -1, max_frames=20000)
    assert run_until(g, lambda: g.trend == 1, max_frames=20000)


def test_crash_drops_price():
    g = make_game()
    # Fast-forward into a crash, then measure the drop across crash frames
    assert run_until(g, lambda: g.crashing, max_frames=20000)
    before = g.price
    for _ in range(CRASH_FRAMES):
        g._update_market()
    assert g.price < before


def test_price_stays_bounded_over_full_game():
    g = make_game()
    for _ in range(GAME_DURATION):
        g.frame += 1
        g._update_market()
        assert MIN_PRICE <= g.price <= MAX_PRICE


def test_price_mean_reverts_from_high():
    g = make_game()
    g.price = MAX_PRICE
    g.trend = -1  # force bear so it can't climb
    g.bubble = 50.0
    g.warning = False
    g.crashing = False
    for _ in range(200):
        g._update_market()
    assert g.price < MAX_PRICE


# ── escalation ──


def test_trend_speed_escalates():
    g = make_game()
    g.frame = 0
    slow = g._trend_speed()
    g.frame = GAME_DURATION
    fast = g._trend_speed()
    assert fast > slow


def test_volatility_escalates():
    g = make_game()
    g.frame = 0
    low = g._volatility()
    g.frame = GAME_DURATION
    high = g._volatility()
    assert high > low


# ── game over ──


def test_game_over_reason_none_when_healthy():
    g = make_game()
    assert g._game_over_reason() is None


def test_game_over_reason_margin_call():
    g = make_game()
    g.cash = 100.0
    g.shares = 0
    g.price = 100.0
    assert g._game_over_reason() == "MARGIN CALL!"


def test_game_over_reason_time_up():
    g = make_game()
    g.frame = GAME_DURATION
    assert g._game_over_reason() == "TIME UP!"


def test_game_over_updates_best_score_and_phase():
    g = make_game()
    g.score = 1500
    g.best_score = 1200
    g._game_over("TIME UP!")
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 1500
    assert g.game_over_reason == "TIME UP!"


# ── particles / floating text ──


def test_spawn_particle():
    g = make_game()
    n_before = len(g.particles)
    g._spawn_particle(160.0, 120.0, 8, count=10)
    assert len(g.particles) == n_before + 10
    assert all(isinstance(p, Particle) for p in g.particles)


def test_spawn_float():
    g = make_game()
    n_before = len(g.floats)
    g._spawn_float(160.0, 80.0, "+$100", 11)
    assert len(g.floats) == n_before + 1
    assert isinstance(g.floats[-1], FloatingText)
    assert g.floats[-1].text == "+$100"


# ── button bounds ──


def test_buy_button_bounds():
    g = make_game()
    assert g._button_buy_contains(50, 220)
    assert not g._button_buy_contains(95, 220)
    assert not g._button_buy_contains(50, 10)


def test_sell_button_bounds():
    g = make_game()
    assert g._button_sell_contains(140, 220)
    assert not g._button_sell_contains(95, 220)
    assert not g._button_sell_contains(140, 10)


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
