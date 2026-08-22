"""Headless logic tests for LEVEE (336_levee).

Runs without Pyxel: imports the game module (which imports pyxel but only
calls Rust-backed functions inside draw/update/__init__, never in the tested
logic methods), and uses Game.__new__ to bypass __init__.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (  # noqa: E402
    CAPACITY,
    CLEAR_BONUS_PER_WATER,
    GATE_FLOW,
    STORM_DURATION,
    SURGE_DURATION,
    SURGE_INTERVAL,
    SURGE_WARNING,
    TANKS,
    FloatText,
    Game,
    Particle,
    Phase,
    in_surge,
    power_gain,
    rain_rate,
    surge_warning,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.best_score = 0
    g.reset()
    return g


# --- Pure module-level functions ---


def test_in_surge_boundaries():
    assert in_surge(0) is False
    assert in_surge(419) is False
    assert in_surge(420) is True  # SURGE_INTERVAL - SURGE_DURATION
    assert in_surge(599) is True
    assert in_surge(600) is False  # cycle resets
    assert in_surge(600 + 420) is True  # second cycle


def test_surge_warning_boundaries():
    warn_start = SURGE_INTERVAL - SURGE_DURATION - SURGE_WARNING
    warn_end = SURGE_INTERVAL - SURGE_DURATION
    assert surge_warning(warn_start - 1) is False
    assert surge_warning(warn_start) is True
    assert surge_warning(warn_end - 1) is True
    assert surge_warning(warn_end) is False
    assert surge_warning(0) is False


def test_rain_rate_base_ramp():
    # frame 0: minimum rain, no surge.
    assert rain_rate(0) == 1.0
    # ramp grows with frame, stays above the minimum.
    mid = rain_rate(STORM_DURATION // 2)
    assert 1.0 < mid < 2.0


def test_rain_rate_surge_multiplier():
    # During a surge, rain is tripled relative to the un-surged base ramp.
    f = 420  # first surge window
    base = 1.0 + (2.0 - 1.0) * (f / STORM_DURATION)
    assert rain_rate(f) == pytest_approx(base * 3.0)


def test_power_gain_head_pressure():
    assert power_gain(5.0, 0.0) == 5
    assert power_gain(5.0, 50.0) == 7  # int(5 * 1.5)
    assert power_gain(5.0, 100.0) == 10  # int(5 * 2.0)
    assert power_gain(0.0, 100.0) == 0
    assert power_gain(5.0, 100.0) == power_gain(5.0, 100.0)  # deterministic


# --- Game state / reset ---


def test_reset_initializes_state():
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.frame == 0
    assert g.levels == [0.0] * TANKS
    assert g.gates == [False] * TANKS
    assert g.power == 0.0
    assert g.score == 0
    assert g.cleared is False
    assert g.particles == []
    assert g.floats == []


def test_toggle_gate_flips():
    g = _make_game()
    assert g.gates[0] is False
    g._toggle_gate(0)
    assert g.gates[0] is True
    g._toggle_gate(0)
    assert g.gates[0] is False
    g._toggle_gate(2)
    assert g.gates[2] is True
    assert g.gates[1] is False


# --- Breach detection ---


def test_check_breach_boundary():
    g = _make_game()
    g.levels = [CAPACITY, 0.0, 0.0]
    assert g._check_breach() is False  # exactly at capacity is NOT a breach
    g.levels = [CAPACITY + 0.01, 0.0, 0.0]
    assert g._check_breach() is True
    g.levels = [0.0, 0.0, CAPACITY + 1.0]
    assert g._check_breach() is True


# --- Simulation ticks ---


def test_apply_tick_rain_fills_top_tank():
    g = _make_game()
    g.frame = 0
    g._apply_tick()
    assert g.levels[0] == pytest_approx(rain_rate(0))
    assert g.levels[1] == 0.0
    assert g.levels[2] == 0.0


def test_apply_tick_gate_cascades_downward():
    g = _make_game()
    g.frame = 0
    g.levels = [10.0, 0.0, 0.0]
    g.gates = [True, True, False]
    g._apply_tick()
    # rain (+1.0) -> tank0 = 11, gate0 moves 5 to tank1, gate1 moves 5 to tank2.
    assert g.levels == [6.0, 0.0, 5.0]


def test_apply_tick_gate_flow_capped_by_source():
    g = _make_game()
    g.frame = 0
    g.levels = [3.0, 0.0, 0.0]
    g.gates = [True, False, False]
    g._apply_tick()
    # rain (+1.0) -> 4.0, gate0 moves min(5, 4) = 4 down.
    assert g.levels == [0.0, 4.0, 0.0]


def test_apply_tick_gate2_generates_power_with_head():
    g = _make_game()
    g.frame = 0
    g.levels = [0.0, 0.0, 100.0]
    g.gates = [False, False, True]
    g._apply_tick()
    # head captured at 100 -> power_gain(5, 100) = 10; tank2 drops to 95.
    assert g.power == 10.0
    assert g.levels[2] == 95.0


def test_apply_tick_empty_tanks_no_power():
    g = _make_game()
    g.frame = 0
    g.levels = [0.0, 0.0, 0.0]
    g.gates = [True, True, True]
    g._apply_tick()
    # rain adds 1.0 to tank0; gate0 moves min(5,1)=1 to tank1; gate1 moves 1 to
    # tank2; gate2 head=1 -> power_gain(1, 1) = int(1 * 1.01) = 1.
    assert g.levels == [0.0, 0.0, 0.0]
    assert g.power == 1.0


def test_apply_tick_full_cascade_in_one_tick():
    g = _make_game()
    g.frame = 0
    g.levels = [50.0, 0.0, 0.0]
    g.gates = [True, True, True]
    g._apply_tick()
    # 51 -> gate0 (5) -> 46/5 -> gate1 (5) -> 46/0/5 -> gate2 head=5 -> power_gain(5,5)=5.
    assert g.levels == [46.0, 0.0, 0.0]
    assert g.power == 5.0


# --- Game-over transitions via _update_playing ---


def test_update_playing_breach_sets_game_over():
    g = _make_game()
    g.frame = 0
    g.levels = [101.0, 0.0, 0.0]
    g.gates = [False, False, False]
    g._update_playing()
    assert g.phase == Phase.GAME_OVER
    assert g.cleared is False
    assert g.shake_frames > 0
    assert g.flash_frames > 0


def test_update_playing_clear_awards_bonus():
    g = _make_game()
    g.frame = STORM_DURATION - 1
    g.levels = [10.0, 10.0, 10.0]
    g.gates = [False, False, False]
    g._update_playing()
    assert g.phase == Phase.GAME_OVER
    assert g.cleared is True
    # Bonus = sum(remaining levels) * CLEAR_BONUS_PER_WATER (levels include one
    # more rain tick since _apply_tick runs before the clear check).
    assert g.power == pytest_approx(sum(g.levels) * CLEAR_BONUS_PER_WATER)
    # best_score is captured at game-over when score exceeds the prior best.
    assert g.score == int(g.power)
    assert g.best_score == g.score


def test_update_playing_score_tracks_power():
    g = _make_game()
    g.frame = 0
    g.levels = [0.0, 0.0, 100.0]
    g.gates = [False, False, True]
    g._update_playing()
    assert g.power == 10.0
    assert g.score == 10
    # best_score is only captured at game-over; during play it holds prior best.
    assert g.best_score == 0


def test_update_playing_best_score_persists():
    g = _make_game()
    g.best_score = 50
    g.frame = 0
    g.levels = [0.0, 0.0, 100.0]
    g.gates = [False, False, True]
    g._update_playing()
    # power (10) < best (50): best unchanged.
    assert g.best_score == 50


# --- Particle / float text lifecycle ---


def test_update_particles_decay_and_removed():
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=0)]
    g._update_particles()
    assert g.particles == []  # life 1 -> 0 -> removed same call


def test_update_particles_survives_with_life_two():
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=2, color=0)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 1


def test_update_floats_decay_and_removed():
    g = _make_game()
    g.floats = [FloatText(x=0.0, y=0.0, text="+1", life=1, color=0)]
    g._update_floats()
    assert g.floats == []


def test_update_floats_survives_with_life_two():
    g = _make_game()
    g.floats = [FloatText(x=0.0, y=0.0, text="+1", life=2, color=0)]
    g._update_floats()
    assert len(g.floats) == 1
    assert g.floats[0].life == 1


# --- Gate-flow constant sanity ---


def test_gate_flow_within_capacity():
    assert 0.0 < GATE_FLOW <= CAPACITY


# --- Runner ---


def pytest_approx(value, rel=1e-6, abs=1e-6):
    """Approximation check without importing pytest (keeps the script runnable)."""

    return _Approx(value, rel, abs)


class _Approx:
    __slots__ = ("value", "rel", "abs")

    def __init__(self, value, rel, abs_):
        self.value = value
        self.rel = rel
        self.abs = abs_

    def __eq__(self, other):

        tol = self.abs + self.rel * abs(self.value)
        return abs(other - self.value) <= tol

    def __repr__(self):
        return f"{self.value} +/- {self.abs}"


def _run_all() -> None:
    tests = [
        test_in_surge_boundaries,
        test_surge_warning_boundaries,
        test_rain_rate_base_ramp,
        test_rain_rate_surge_multiplier,
        test_power_gain_head_pressure,
        test_reset_initializes_state,
        test_toggle_gate_flips,
        test_check_breach_boundary,
        test_apply_tick_rain_fills_top_tank,
        test_apply_tick_gate_cascades_downward,
        test_apply_tick_gate_flow_capped_by_source,
        test_apply_tick_gate2_generates_power_with_head,
        test_apply_tick_empty_tanks_no_power,
        test_apply_tick_full_cascade_in_one_tick,
        test_update_playing_breach_sets_game_over,
        test_update_playing_clear_awards_bonus,
        test_update_playing_score_tracks_power,
        test_update_playing_best_score_persists,
        test_update_particles_decay_and_removed,
        test_update_particles_survives_with_life_two,
        test_update_floats_decay_and_removed,
        test_update_floats_survives_with_life_two,
        test_gate_flow_within_capacity,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS  {test.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {test.__name__}: {e!r}")
    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    _run_all()
