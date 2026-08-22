"""Headless logic tests for BEACON (avalanche beacon search & rescue).

Uses Game.__new__ + reset(seed=...) to bypass pyxel.init/pyxel.run.
Never calls update()/draw() or any method touching pyxel input.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    DIG_RADIUS,
    DIG_TIME,
    GAME_DURATION,
    MISS_TIME_PENALTY,
    PLAYER_RADIUS,
    RESCUE_TIME_BONUS,
    VICTIM_MAX,
    VICTIM_START,
    FloatingText,
    Game,
    Particle,
    Phase,
    Victim,
    combo_multiplier,
    rescue_score,
    signal_strength,
    spawn_interval,
)


def make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.reset(seed=seed)
    return g


# --- pure functions ----------------------------------------------------------


def test_signal_strength_bounds():
    assert signal_strength(0.0) == 100
    assert signal_strength(10.0) == 92  # 100 - 8
    assert signal_strength(125.0) == 0
    assert signal_strength(999.0) == 0  # clamped
    assert signal_strength(-5.0) == 100  # clamped


def test_signal_strength_monotonic_decreasing():
    assert signal_strength(5.0) > signal_strength(20.0) > signal_strength(50.0)


def test_combo_multiplier_caps():
    assert combo_multiplier(0) == 1.0
    assert combo_multiplier(1) == 1.5
    assert combo_multiplier(2) == 2.0
    assert combo_multiplier(6) == 4.0
    assert combo_multiplier(100) == 4.0


def test_rescue_score_scales_with_combo():
    assert rescue_score(0) == 100
    assert rescue_score(1) == 150
    assert rescue_score(6) == 400  # capped at 4.0x


def test_spawn_interval_decreases_and_has_floor():
    assert spawn_interval(0) == 720
    assert spawn_interval(6000) == 320
    assert spawn_interval(10000) == 300
    assert spawn_interval(0) > spawn_interval(5000)
    for f in (0, 1000, 5000, 10000, 100000):
        assert spawn_interval(f) >= 300


# --- reset / state -----------------------------------------------------------


def test_reset_initializes_state():
    g = make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.rescued_count == 0
    assert g.time_left == GAME_DURATION
    assert len(g.victims) == VICTIM_START
    assert g.player_x == 160 and g.player_y == 120
    assert g.dig_timer == 0
    assert len(g.rocks) == 4


def test_reset_restarts_clean():
    g = make_game()
    g.score = 999
    g.combo = 5
    g.rescued_count = 3
    g.time_left = 10
    g.reset(seed=7)
    assert g.score == 0 and g.combo == 0 and g.rescued_count == 0
    assert g.time_left == GAME_DURATION


# --- signal / distance -------------------------------------------------------


def test_nearest_distance():
    g = make_game()
    g.victims = [Victim(100.0, 100.0), Victim(200.0, 200.0)]
    assert g._nearest_distance(100.0, 100.0) == 0.0
    d = g._nearest_distance(100.0, 103.0)
    assert abs(d - 3.0) < 0.01
    # nearest is the closer victim, not the farther one
    d2 = g._nearest_distance(101.0, 101.0)
    assert abs(d2 - math.hypot(1, 1)) < 0.01


def test_nearest_distance_ignores_rescued():
    g = make_game()
    v1 = Victim(100.0, 100.0)
    v2 = Victim(200.0, 200.0, rescued=True)
    g.victims = [v1, v2]
    assert abs(g._nearest_distance(100.0, 100.0)) < 0.01


def test_signal_at_uses_nearest():
    g = make_game()
    g.victims = [Victim(160.0, 120.0)]
    assert g._signal_at(160.0, 120.0) == 100
    assert g._signal_at(160.0, 130.0) == signal_strength(10.0)


# --- dig / rescue ------------------------------------------------------------


def test_resolve_dig_rescues_within_radius():
    g = make_game()
    g.victims = [Victim(g.player_x + 5.0, g.player_y)]  # within DIG_RADIUS
    g.combo = 2
    g.max_combo = 2
    before_time = g.time_left
    g._resolve_dig()
    assert g.victims[0].rescued
    assert g.rescued_count == 1
    assert g.combo == 3
    assert g.max_combo == 3
    assert g.score == rescue_score(3)  # combo incremented first
    assert g.time_left == before_time + RESCUE_TIME_BONUS


def test_resolve_dig_miss_resets_combo_and_penalizes_time():
    g = make_game()
    g.victims = [Victim(300.0, 300.0)]  # far away
    g.combo = 4
    g.max_combo = 4
    before_time = g.time_left
    g._resolve_dig()
    assert g.combo == 0
    assert g.max_combo == 4  # max persists
    assert g.rescued_count == 0
    assert g.time_left == before_time - MISS_TIME_PENALTY


def test_dig_radius_boundary():
    g = make_game()
    g.victims = [Victim(g.player_x + float(DIG_RADIUS), g.player_y)]  # exactly at radius
    g._resolve_dig()
    assert g.victims[0].rescued


def test_dig_chain_builds_combo():
    g = make_game()
    g.victims = [Victim(160.0, 120.0)]
    g._resolve_dig()
    assert g.combo == 1 and g.max_combo == 1
    # second victim at same spot
    g.victims = [Victim(160.0, 120.0)]
    g._resolve_dig()
    assert g.combo == 2 and g.max_combo == 2


def test_start_dig_sets_timer_only_once():
    g = make_game()
    g._start_dig()
    assert g.dig_timer == DIG_TIME
    g._start_dig()
    assert g.dig_timer == DIG_TIME  # not reset while active


# --- movement ----------------------------------------------------------------


def test_move_player_straight():
    g = make_game()
    x0, y0 = g.player_x, g.player_y
    g._move_player(1, 0)
    assert g.player_x == x0 + 2.0
    assert g.player_y == y0


def test_move_player_diagonal_normalized():
    g = make_game()
    x0, y0 = g.player_x, g.player_y
    g._move_player(1, 1)
    inv = 1.0 / math.sqrt(2.0)
    assert abs(g.player_x - (x0 + 2.0 * inv)) < 0.001
    assert abs(g.player_y - (y0 + 2.0 * inv)) < 0.001


def test_move_player_clamped_to_screen():
    g = make_game()
    for _ in range(500):
        g._move_player(-1, -1)
    assert g.player_x >= PLAYER_RADIUS - 0.001
    assert g.player_y >= PLAYER_RADIUS - 0.001


def test_move_player_blocked_while_digging():
    g = make_game()
    g.dig_timer = 10
    x0, y0 = g.player_x, g.player_y
    g._move_player(1, 0)
    assert g.player_x == x0 and g.player_y == y0


def test_move_player_rock_collision():
    g = make_game()
    rock = g.rocks[0]
    # place player just above the rock, then move down into it
    g.player_x = rock.x
    g.player_y = rock.y - (PLAYER_RADIUS + rock.radius) + 1.0
    g._move_player(0, 1)
    assert math.hypot(g.player_x - rock.x, g.player_y - rock.y) >= (
        PLAYER_RADIUS + rock.radius
    ) - 0.5


# --- timers / spawn / game over ---------------------------------------------


def test_spawn_victim_respects_max():
    g = make_game()
    g.victims = []
    for _ in range(VICTIM_MAX + 5):
        g._spawn_victim()
    assert len(g.victims) == VICTIM_MAX


def test_update_timers_resolves_dig():
    g = make_game()
    g.victims = [Victim(g.player_x, g.player_y)]
    g._start_dig()
    for _ in range(DIG_TIME):
        g._update_timers()
    assert g.dig_timer == 0
    assert g.victims[0].rescued


def test_check_game_over_timeout():
    g = make_game()
    g.time_left = 1
    g._update_timers()
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_check_game_over_victory():
    g = make_game()
    for v in g.victims:
        v.rescued = True
    g._check_game_over()
    assert g.phase == Phase.VICTORY


def test_check_game_over_still_playing():
    g = make_game()
    g.time_left = 5000
    g._check_game_over()
    assert g.phase == Phase.PLAYING


# --- particles / floating text ----------------------------------------------


def test_particles_decay_and_remove():
    g = make_game()
    g.particles = [Particle(0.0, 0.0, 1.0, 0.0, 1, 8)]
    g._update_particles()
    assert len(g.particles) == 0


def test_floating_text_decays_and_removes():
    g = make_game()
    g.floating_texts = [FloatingText(0.0, 0.0, "X", 1, 7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
