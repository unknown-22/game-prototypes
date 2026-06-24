"""Headless tests for SAIL CHAIN game logic."""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (  # type: ignore[import-untyped]
    BUOY_COLORS,
    COMBO_THRESHOLD,
    GAME_TIMER_FRAMES,
    GREEN,
    MAX_HEAT,
    RED,
    SAIL_MAX,
    SAIL_MIN,
    SUPER_DURATION,
    WIND_ANGLES,
    Buoy,
    Game,
    GhostPoint,
    Particle,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    """Factory for a fresh headless Game instance."""
    return Game._make_game(seed)


# ------------------------------------------------------------------
# Initial State
# ------------------------------------------------------------------
class TestInitialState:
    def test_phase_is_playing(self) -> None:
        g = _make_game()
        assert g.phase == Phase.PLAYING

    def test_buoys_count(self) -> None:
        g = _make_game()
        assert len(g.buoys) == 8

    def test_two_buoys_per_color(self) -> None:
        g = _make_game()
        for c in BUOY_COLORS:
            count = sum(1 for b in g.buoys if b.color == c)
            assert count == 2

    def test_stats_are_zero(self) -> None:
        g = _make_game()
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0
        assert g.super_timer == 0
        assert g.game_timer == GAME_TIMER_FRAMES
        assert g.last_buoy_color == -1

    def test_no_ghost_trail_initially(self) -> None:
        g = _make_game()
        assert len(g.best_ghost) == 0
        assert len(g.ghost_recording) == 0


# ------------------------------------------------------------------
# Physics
# ------------------------------------------------------------------
class TestPhysics:
    def test_boat_moves_forward(self) -> None:
        g = _make_game()
        g.boat_angle = 0.0  # right
        g.boat_x = 100.0
        g.boat_y = 100.0
        g._update_physics()
        assert g.boat_x > 100.0
        assert abs(g.boat_y - 100.0) < 0.1

    def test_boat_moves_downward(self) -> None:
        g = _make_game()
        g.boat_angle = math.pi / 2  # down
        g.boat_x = 100.0
        g.boat_y = 100.0
        g._update_physics()
        assert g.boat_y > 100.0
        assert abs(g.boat_x - 100.0) < 0.1

    def test_rudder_turns_boat(self) -> None:
        g = _make_game()
        g.boat_angle = 0.0
        g.rudder_input = 1.0  # turn right
        g._update_physics()
        assert g.boat_angle > 0.0

    def test_sail_angle_clamped(self) -> None:
        g = _make_game()
        g.sail_angle = SAIL_MIN
        g.sail_input = -1.0
        g._update_physics()
        assert g.sail_angle >= SAIL_MIN

        g.sail_angle = SAIL_MAX
        g.sail_input = 1.0
        g._update_physics()
        assert g.sail_angle <= SAIL_MAX

    def test_boat_wraps_vertically_top(self) -> None:
        g = _make_game()
        g.boat_y = -20.0
        g.boat_angle = -math.pi / 2  # up
        g._update_physics()
        assert g.boat_y > 0

    def test_boat_wraps_vertically_bottom(self) -> None:
        g = _make_game()
        from main import SCREEN_H  # type: ignore[import-untyped]

        g.boat_y = SCREEN_H + 20.0
        g.boat_angle = math.pi / 2  # down
        g._update_physics()
        assert g.boat_y < SCREEN_H


# ------------------------------------------------------------------
# Wind
# ------------------------------------------------------------------
class TestWind:
    def test_wind_changes_direction(self) -> None:
        g = _make_game()
        g.wind_timer = 1
        g._update_wind()
        g._update_wind()  # second tick should change
        assert g.wind_angle in WIND_ANGLES
        # After change, new angle should be one of the valid angles
        assert g.wind_angle in WIND_ANGLES

    def test_wind_no_change_in_super(self) -> None:
        g = _make_game()
        g.super_timer = 100
        initial = g.wind_timer
        g._update_wind()
        assert g.wind_timer == initial  # unchanged in super


# ------------------------------------------------------------------
# Buoy Rounding — Combo
# ------------------------------------------------------------------
class TestCombo:
    def test_first_buoy_starts_combo(self) -> None:
        g = _make_game()
        buoy = Buoy(x=g.boat_x, y=g.boat_y, color=RED, rounded=False)
        g.buoys = [buoy]
        g.combo = 0
        g.last_buoy_color = -1
        g._round_buoy(buoy, False)
        assert g.combo == 1
        assert g.last_buoy_color == RED
        assert g.score > 0

    def test_same_color_increases_combo(self) -> None:
        g = _make_game()
        g.combo = 2
        g.last_buoy_color = RED
        buoy = Buoy(x=g.boat_x, y=g.boat_y, color=RED, rounded=False)
        g.buoys = [buoy]
        score_before = g.score
        g._round_buoy(buoy, False)
        assert g.combo == 3
        assert g.score > score_before

    def test_wrong_color_resets_combo_and_adds_heat(self) -> None:
        g = _make_game()
        g.combo = 3
        g.last_buoy_color = RED
        g.heat = 1
        buoy = Buoy(x=g.boat_x, y=g.boat_y, color=GREEN, rounded=False)
        g.buoys = [buoy]
        g._round_buoy(buoy, False)
        assert g.combo == 0
        assert g.heat == 2
        assert g.last_buoy_color == GREEN

    def test_combo_threshold_activates_super(self) -> None:
        g = _make_game()
        g.combo = COMBO_THRESHOLD - 1  # 3
        g.last_buoy_color = RED
        buoy = Buoy(x=g.boat_x, y=g.boat_y, color=RED, rounded=False)
        g.buoys = [buoy]
        g._round_buoy(buoy, False)
        assert g.combo == COMBO_THRESHOLD
        assert g.super_timer == SUPER_DURATION

    def test_max_combo_tracks_peak(self) -> None:
        g = _make_game()
        g.last_buoy_color = RED
        # Build combo to 3
        for i in range(3):
            b = Buoy(x=g.boat_x, y=g.boat_y, color=RED, rounded=False)
            g.buoys = [b]
            g._round_buoy(b, False)
        assert g.max_combo == 3


# ------------------------------------------------------------------
# Super Mode
# ------------------------------------------------------------------
class TestSuperMode:
    def test_super_mode_is_super_returns_true(self) -> None:
        g = _make_game()
        g.super_timer = 100
        assert g._is_super()

    def test_super_mode_is_super_returns_false(self) -> None:
        g = _make_game()
        g.super_timer = 0
        assert not g._is_super()

    def test_super_timer_decrements(self) -> None:
        g = _make_game()
        g.super_timer = 10
        g._update_super()
        assert g.super_timer == 9

    def test_super_expires(self) -> None:
        g = _make_game()
        g.super_timer = 1
        g._update_super()
        assert g.super_timer == 0
        assert not g._is_super()

    def test_super_collects_any_color(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.last_buoy_color = RED
        g.combo = 5
        buoy = Buoy(x=g.boat_x, y=g.boat_y, color=GREEN, rounded=False)
        g.buoys = [buoy]
        combo_before = g.combo
        g._round_buoy(buoy, True)
        assert g.combo > combo_before  # Super always increases combo

    def test_super_has_3x_score_multiplier(self) -> None:
        g = _make_game()
        g.combo = 2
        buoy = Buoy(x=0, y=0, color=RED)
        normal_pts = g._compute_score(buoy, False)
        super_pts = g._compute_score(buoy, True)
        assert super_pts == normal_pts * 3


# ------------------------------------------------------------------
# Heat and Game Over
# ------------------------------------------------------------------
class TestGameOver:
    def test_heat_at_max_triggers_game_over(self) -> None:
        g = _make_game()
        g.heat = MAX_HEAT
        assert g._check_game_over()

    def test_heat_below_max_no_game_over(self) -> None:
        g = _make_game()
        g.heat = MAX_HEAT - 1
        g.game_timer = 100
        assert not g._check_game_over()

    def test_timer_zero_triggers_game_over(self) -> None:
        g = _make_game()
        g.game_timer = 0
        assert g._check_game_over()

    def test_timer_positive_no_game_over(self) -> None:
        g = _make_game()
        g.game_timer = 1
        g.heat = 0
        assert not g._check_game_over()

    def test_timer_decrements(self) -> None:
        g = _make_game()
        g.game_timer = 10
        g._update_timer()
        assert g.game_timer == 9

    def test_on_game_over_sets_phase(self) -> None:
        g = _make_game()
        g.score = 100
        g._on_game_over()
        assert g.phase == Phase.GAME_OVER

    def test_on_game_over_updates_high_score(self) -> None:
        g = _make_game()
        g.score = 500
        g.high_score = 100
        g._on_game_over()
        assert g.high_score == 500

    def test_on_game_over_saves_best_ghost(self) -> None:
        g = _make_game()
        g.score = 500
        g.high_score = 100
        g.ghost_recording = [
            GhostPoint(x=10.0, y=20.0, angle=0.0),
            GhostPoint(x=11.0, y=21.0, angle=0.5),
        ]
        g._on_game_over()
        assert len(g.best_ghost) == 2


# ------------------------------------------------------------------
# Ghost Recording
# ------------------------------------------------------------------
class TestGhost:
    def test_ghost_records_position(self) -> None:
        g = _make_game()
        g._update_ghost()
        assert len(g.ghost_recording) == 1
        assert g.ghost_recording[0].x == g.boat_x
        assert g.ghost_recording[0].y == g.boat_y

    def test_ghost_grows_over_time(self) -> None:
        g = _make_game()
        for _ in range(5):
            g._update_ghost()
        assert len(g.ghost_recording) == 5


# ------------------------------------------------------------------
# Scoring
# ------------------------------------------------------------------
class TestScoring:
    def test_compute_score_base(self) -> None:
        g = _make_game()
        g.combo = 1
        b = Buoy(x=0, y=0, color=RED)
        pts = g._compute_score(b, False)
        assert pts == 10 * (1 + g.combo)

    def test_compute_score_increases_with_combo(self) -> None:
        g = _make_game()
        b = Buoy(x=0, y=0, color=RED)
        g.combo = 1
        pts1 = g._compute_score(b, False)
        g.combo = 3
        pts2 = g._compute_score(b, False)
        assert pts2 > pts1

    def test_compute_score_super_multiplier(self) -> None:
        g = _make_game()
        g.combo = 2
        b = Buoy(x=0, y=0, color=RED)
        normal = g._compute_score(b, False)
        super_pts = g._compute_score(b, True)
        assert super_pts == normal * 3


# ------------------------------------------------------------------
# Particles
# ------------------------------------------------------------------
class TestParticles:
    def test_particles_age_and_remove(self) -> None:
        g = _make_game()
        g.particles = [
            Particle(x=0, y=0, vx=0, vy=0, life=1, color=7),
            Particle(x=0, y=0, vx=0, vy=0, life=5, color=7),
        ]
        g._update_particles()
        assert len(g.particles) == 1

    def test_particles_move(self) -> None:
        g = _make_game()
        g.particles = [
            Particle(x=0, y=0, vx=1.0, vy=0.5, life=10, color=7),
        ]
        g._update_particles()
        assert g.particles[0].x == 1.0
        assert g.particles[0].y == 0.5
        assert g.particles[0].vy == 0.55  # gravity applied to vy

    def test_collect_particles_spawned(self) -> None:
        g = _make_game()
        initial_count = len(g.particles)
        g._spawn_collect_particles(50, 50, RED, 5)
        assert len(g.particles) == initial_count + 5

    def test_wrong_particles_spawned(self) -> None:
        g = _make_game()
        initial_count = len(g.particles)
        g._spawn_wrong_particles(50, 50, RED)
        assert len(g.particles) > initial_count

    def test_activate_super_spawns_burst(self) -> None:
        g = _make_game()
        initial_count = len(g.particles)
        g._activate_super()
        assert len(g.particles) > initial_count
        assert g.super_timer == SUPER_DURATION


# ------------------------------------------------------------------
# Nearest Buoy
# ------------------------------------------------------------------
class TestNearestBuoy:
    def test_finds_nearest_buoy(self) -> None:
        g = _make_game()
        g.boat_x = 100.0
        g.boat_y = 100.0
        g.buoys = [
            Buoy(x=50.0, y=50.0, color=RED, rounded=False),  # far
            Buoy(x=102.0, y=100.0, color=GREEN, rounded=False),  # near
        ]
        g._update_nearest_buoy()
        assert g.nearest_buoy_idx == 1

    def test_ignores_rounded_buoys(self) -> None:
        g = _make_game()
        g.boat_x = 100.0
        g.boat_y = 100.0
        g.buoys = [
            Buoy(x=102.0, y=100.0, color=RED, rounded=True),  # near but rounded
            Buoy(x=50.0, y=50.0, color=GREEN, rounded=False),
        ]
        g._update_nearest_buoy()
        assert g.nearest_buoy_idx == 1


# ------------------------------------------------------------------
# Reset
# ------------------------------------------------------------------
class TestReset:
    def test_reset_clears_state(self) -> None:
        g = _make_game()
        g.score = 500
        g.combo = 10
        g.max_combo = 10
        g.heat = 4
        g.super_timer = 100
        g.game_timer = 100
        g.last_buoy_color = RED
        g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=7)]
        g.ghost_recording = [GhostPoint(x=0, y=0, angle=0)]
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0
        assert g.super_timer == 0
        assert g.game_timer == GAME_TIMER_FRAMES
        assert g.last_buoy_color == -1
        assert len(g.particles) == 0
        assert len(g.ghost_recording) == 0
        assert len(g.buoys) == 8
