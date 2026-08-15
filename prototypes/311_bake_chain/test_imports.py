"""Headless logic tests for BAKE CHAIN (311_bake_chain).

Run with:  uv run python prototypes/311_bake_chain/test_imports.py
or:        uv run pytest prototypes/311_bake_chain/test_imports.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (  # noqa: E402
    COLS,
    MAX_HEAT,
    MIN_BALLS,
    SLOTS,
    SUPER_FRAMES,
    TIME_LIMIT,
    Dough,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def _make_game() -> Game:
    """Factory: bypass pyxel init via Game.__new__, pre-init __init__-only attrs, reset()."""
    g = Game.__new__(Game)
    g.best_score = 0  # only set in __init__, NOT in reset()
    g.phase = Phase.PLAYING  # reset() does not set phase
    g.reset()
    g.rng = random.Random(42)  # reset() re-seeds unseeded; seed AFTER for determinism
    return g


def _place(g: Game, index: int, color: int, rise: float = 0.0) -> None:
    """Place a dough ball at a slot (clearing any mold there first)."""
    g.grid[index] = Dough(color=color, rise=rise)
    g.mold[index] = False


# --------------------------------------------------------------------------- #
# reset / initial state                                                        #
# --------------------------------------------------------------------------- #


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == TIME_LIMIT
    assert g.elapsed == 0
    assert g.oven_color == 0
    assert g.super_timer == 0
    assert g.shake == 0
    assert g.particles == []
    assert g.floats == []
    assert len(g.grid) == SLOTS
    assert len(g.mold) == SLOTS
    assert g._count_dough() == MIN_BALLS


def test_reset_clears_previous_state() -> None:
    g = _make_game()
    # Dirty the state
    g.score = 999
    g.combo = 5
    g.heat = 90.0
    g.grid[0] = Dough(color=2, rise=0.9)
    g.mold[0] = True
    g.particles.append(Particle(1, 1, 0, 0, 5, 7))
    g.floats.append(FloatingText(1, 1, "x", 5, 7))
    g.reset()
    g.rng = random.Random(42)
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.particles == []
    assert g.floats == []
    assert not any(g.mold)
    assert g._count_dough() == MIN_BALLS


# --------------------------------------------------------------------------- #
# difficulty escalation                                                        #
# --------------------------------------------------------------------------- #


def test_cycle_interval_decreases_with_elapsed() -> None:
    g = _make_game()
    g.elapsed = 0
    assert g._cycle_interval() == 20
    g.elapsed = 600
    assert g._cycle_interval() == 15
    g.elapsed = 3600
    assert g._cycle_interval() == 12  # floor


def test_spawn_interval_decreases_with_elapsed() -> None:
    g = _make_game()
    g.elapsed = 0
    assert g._spawn_interval() == 60
    g.elapsed = 3600
    assert g._spawn_interval() == 25  # floor


def test_mold_interval_decreases_with_elapsed() -> None:
    g = _make_game()
    g.elapsed = 0
    assert g._mold_interval() == 90
    g.elapsed = 3600
    assert g._mold_interval() == 40  # floor


def test_rise_rate_increases_with_elapsed() -> None:
    g = _make_game()
    g.elapsed = 0
    assert abs(g._rise_rate() - 0.0035) < 1e-9
    g.elapsed = 3600
    assert abs(g._rise_rate() - 0.0060) < 1e-9


def test_max_balls_increases_with_elapsed() -> None:
    g = _make_game()
    g.elapsed = 0
    assert g._max_balls() == 8
    g.elapsed = 3600
    assert g._max_balls() == 14  # cap


# --------------------------------------------------------------------------- #
# value multiplier (risk/reward: bake at peak)                                 #
# --------------------------------------------------------------------------- #


def test_value_mult_thresholds() -> None:
    g = _make_game()
    assert g._value_mult(0.0) == 1
    assert g._value_mult(0.2) == 1  # < 1/3
    assert g._value_mult(0.4) == 2  # >= 1/3, < 2/3
    assert g._value_mult(0.6) == 2
    assert g._value_mult(0.7) == 3  # >= 2/3
    assert g._value_mult(1.5) == 3  # capped


def test_peak_bake_rewards_more_than_early_bake() -> None:
    """Risk/reward: a fully-risen (3x) bake must score more than an early (1x) bake."""
    g = _make_game()
    g.oven_color = 0
    # Early bake (rise 0.0 -> mult 1) at slot 0, combo pre-set to 1
    _place(g, 0, 0, rise=0.0)
    g.combo = 1
    early = g.grid[0]
    assert early is not None
    early_gain = 10 * g.combo * g._value_mult(early.rise)
    assert early_gain == 10
    # Peak bake (rise 0.9 -> mult 3) at slot 1
    _place(g, 1, 0, rise=0.9)
    g.combo = 1
    peak = g.grid[1]
    assert peak is not None
    peak_gain = 10 * g.combo * g._value_mult(peak.rise)
    assert peak_gain == 30
    assert peak_gain > early_gain


# --------------------------------------------------------------------------- #
# _bake: match / mismatch / empty                                              #
# --------------------------------------------------------------------------- #


def test_bake_match_increments_combo_and_score() -> None:
    g = _make_game()
    g.oven_color = 2
    _place(g, 5, color=2, rise=0.5)  # mult 2
    g.combo = 2
    assert g._bake(5) is True
    assert g.grid[5] is None
    assert g.combo == 3
    assert g.max_combo == 3
    assert g.score == 10 * 2 * 2  # 10 * prior_combo(2) * mult(2)


def test_bake_match_uses_value_multiplier() -> None:
    g = _make_game()
    g.oven_color = 1
    _place(g, 0, color=1, rise=0.0)  # mult 1
    g.combo = 1
    g._bake(0)  # gain = 10 * 1 * 1 = 10 (combo becomes 2, no SUPER)
    low_score = g.score
    _place(g, 1, color=1, rise=0.9)  # mult 3
    g.combo = 1
    g._bake(1)  # gain = 10 * 1 * 3 = 30
    assert g.score - low_score == 30


def test_bake_mismatch_adds_heat_and_resets_combo() -> None:
    g = _make_game()
    g.oven_color = 0
    _place(g, 3, color=1, rise=0.3)  # wrong color
    g.combo = 4
    g.max_combo = 4
    assert g._bake(3) is False
    assert g.heat == 15.0
    assert g.combo == 0
    assert g.grid[3] is None  # ball discarded (burnt)
    assert g.shake == 8


def test_bake_empty_slot_is_noop() -> None:
    g = _make_game()
    g.oven_color = 0
    g.grid[10] = None
    g.combo = 2
    score_before = g.score
    assert g._bake(10) is False
    assert g.combo == 2  # unchanged
    assert g.score == score_before
    assert g.heat == 0.0  # no mismatch heat for empty slot


# --------------------------------------------------------------------------- #
# SUPER BAKE                                                                   #
# --------------------------------------------------------------------------- #


def test_combo_4_triggers_super() -> None:
    g = _make_game()
    g.oven_color = 0
    for i in range(4):
        _place(g, i, color=0, rise=0.9)
    for i in range(4):
        g._bake(i)
    assert g.super_timer == SUPER_FRAMES


def test_super_clears_all_mold() -> None:
    g = _make_game()
    g.oven_color = 0
    g.mold[0] = True
    g.mold[5] = True
    g.mold[23] = True
    _place(g, 1, color=0)
    g.combo = 3
    g._bake(1)  # combo becomes 4 -> super
    assert g.super_timer == SUPER_FRAMES
    assert not any(g.mold)


def test_super_matches_any_color() -> None:
    g = _make_game()
    g.super_timer = 10  # super active
    g.oven_color = 0
    _place(g, 7, color=3, rise=0.5)  # different color still matches
    g.combo = 1
    assert g._bake(7) is True
    assert g.grid[7] is None
    assert g.combo == 2


def test_super_triples_score() -> None:
    g = _make_game()
    g.super_timer = 10
    g.oven_color = 2
    _place(g, 0, color=2, rise=0.5)  # mult 2
    g.combo = 1
    g._bake(0)
    assert g.score == 10 * 1 * 2 * 3  # *3 for super


def test_super_freezes_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g.super_timer = 10
    g._update_heat()
    assert g.heat == 50.0  # frozen, no decay


# --------------------------------------------------------------------------- #
# rise / over-proof collapse                                                   #
# --------------------------------------------------------------------------- #


def test_advance_rise_increments_rise() -> None:
    g = _make_game()
    _place(g, 0, color=0, rise=0.0)
    rate = g._rise_rate()
    collapsed = g._advance_rise()
    assert collapsed == 0
    d = g.grid[0]
    assert d is not None
    assert abs(d.rise - rate) < 1e-9


def test_overproof_collapses_to_mold() -> None:
    g = _make_game()
    _place(g, 2, color=1, rise=0.999)
    g.combo = 3
    collapsed = g._advance_rise()
    assert collapsed == 1
    assert g.grid[2] is None
    assert g.mold[2] is True
    assert g.heat == 10.0
    assert g.combo == 0  # combo reset on collapse


# --------------------------------------------------------------------------- #
# mold CA spread                                                               #
# --------------------------------------------------------------------------- #


def _clear_grid(g: Game) -> None:
    """Remove all dough and mold so tests can set up isolated scenarios."""
    g.grid = [None] * SLOTS
    g.mold = [False] * SLOTS


def test_spread_mold_occupies_empty_neighbor() -> None:
    g = _make_game()
    _clear_grid(g)
    g.mold[0] = True  # slot 0 is top-left; neighbors = slot 1 (right) and slot 6 (down)
    g.mold_timer = 0
    changed = g._spread_mold()
    assert changed == 2  # both empty neighbors become mold
    assert g.mold[1] is True
    assert g.mold[6] is True


def test_spread_mold_spoils_dough_neighbor() -> None:
    g = _make_game()
    _clear_grid(g)
    g.mold[0] = True
    _place(g, 1, color=2, rise=0.5)  # dough in right neighbor
    g.mold_timer = 0
    g.heat = 0.0
    changed = g._spread_mold()
    assert changed == 2  # slot 1 spoiled + slot 6 molded
    assert g.grid[1] is None  # spoiled
    assert g.heat == 5.0
    assert g.mold[6] is True


def test_spread_mold_respects_snapshot_no_cascade() -> None:
    """A newly-molded cell must NOT spread again in the same pass."""
    g = _make_game()
    _clear_grid(g)
    g.mold[0] = True  # only one source
    g.mold_timer = 0
    changed = g._spread_mold()
    # Slot 0 has neighbors 1 (right) and 6 (down) -> both become mold in same pass (snapshot only sees [0])
    assert changed == 2
    assert g.mold[1] is True
    assert g.mold[6] is True
    # But slot 2 (neighbor of 1) must NOT be mold (no cascade)
    assert g.mold[2] is False


def test_spread_mold_timer_gating() -> None:
    g = _make_game()
    _clear_grid(g)
    g.mold[0] = True
    g.mold_timer = 5  # not yet elapsed
    assert g._spread_mold() == 0
    assert g.mold_timer == 4
    assert g.mold[1] is False


# --------------------------------------------------------------------------- #
# heat / game over                                                             #
# --------------------------------------------------------------------------- #


def test_heat_decays_over_time() -> None:
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert abs(g.heat - 9.98) < 0.01


def test_heat_threshold_triggers_game_over_before_decay() -> None:
    g = _make_game()
    g.heat = MAX_HEAT  # exactly at threshold
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == g.score  # best updated
    # heat must NOT have decayed below threshold (threshold checked FIRST)
    assert g.heat == MAX_HEAT


def test_heat_clamped_at_zero() -> None:
    g = _make_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


# --------------------------------------------------------------------------- #
# oven color cycling                                                           #
# --------------------------------------------------------------------------- #


def test_oven_color_cycles_when_timer_expires() -> None:
    g = _make_game()
    g.oven_color = 0
    g.cycle_timer = 1
    g._update_oven_color()
    assert g.oven_color == 1
    assert g.cycle_timer == g._cycle_interval()


def test_oven_color_does_not_cycle_early() -> None:
    g = _make_game()
    g.oven_color = 0
    g.cycle_timer = 5
    g._update_oven_color()
    assert g.oven_color == 0
    assert g.cycle_timer == 4


# --------------------------------------------------------------------------- #
# spawning                                                                     #
# --------------------------------------------------------------------------- #


def test_spawn_ball_fills_empty_slot() -> None:
    g = _make_game()
    g.grid[0] = None
    g.mold[0] = False
    before = g._count_dough()
    assert g._spawn_ball() is True
    assert g._count_dough() == before + 1
    # the newly spawned ball has rise 0.0 and a valid color index
    spawned = [d for d in g.grid if d is not None and d.rise == 0.0]
    assert len(spawned) >= 1
    assert all(0 <= d.color < 4 for d in spawned)


def test_spawn_ball_skips_mold_slots() -> None:
    g = _make_game()
    # Fill all slots with dough, then set one slot to mold+empty
    for i in range(SLOTS):
        g.grid[i] = Dough(color=0, rise=0.0)
        g.mold[i] = False
    g.grid[3] = None
    g.mold[3] = True  # the only empty slot is mold -> cannot spawn
    assert g._spawn_ball() is False


def test_spawn_timer_resets_and_spawns_below_max() -> None:
    g = _make_game()
    g.spawn_timer = 0
    g.grid[0] = None  # make an empty slot, count drops to MIN_BALLS-1
    g._update_spawns()
    assert g._count_dough() >= MIN_BALLS  # re-filled toward max
    assert g.spawn_timer == g._spawn_interval()


# --------------------------------------------------------------------------- #
# particles / floating text                                                   #
# --------------------------------------------------------------------------- #


def test_particles_advance_and_expire() -> None:
    g = _make_game()
    g.particles.append(Particle(0, 0, 1.0, 0.5, 2, 8))
    g._update_particles()
    assert g.particles[0].x == 1.0
    assert g.particles[0].y == 0.5
    assert g.particles[0].life == 1
    g._update_particles()
    assert g.particles == []  # life hit 0 -> removed


def test_floats_advance_and_expire() -> None:
    g = _make_game()
    g.floats.append(FloatingText(1, 1, "hi", 1, 7))
    g._update_floats()
    assert g.floats == []  # life 1 -> removed same tick


# --------------------------------------------------------------------------- #
# geometry helpers                                                             #
# --------------------------------------------------------------------------- #


def test_neighbors_corners() -> None:
    g = _make_game()
    assert g._neighbors(0) == [COLS, 1]  # top-left: down + right
    assert g._neighbors(SLOTS - 1) == [SLOTS - 1 - COLS, SLOTS - 2]  # bottom-right: up + left


def test_slot_at_returns_index() -> None:
    g = _make_game()
    # Slot (0,0) center
    assert g._slot_at(40 + 18, 64 + 18) == 0
    # Outside tray
    assert g._slot_at(10, 10) is None
    assert g._slot_at(400, 400) is None


def test_slot_center_matches_geometry() -> None:
    g = _make_game()
    cx, cy = g._slot_center(0)
    assert cx == 40 + 18
    assert cy == 64 + 18


# --------------------------------------------------------------------------- #
# main guard (standalone run)                                                  #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
