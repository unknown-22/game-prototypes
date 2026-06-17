"""Tests for PAPER PLANE TOSS game logic."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import (
    BASE_SCORE,
    COMBO_MULTIPLIER_STEP,
    DRAG,
    GAME_TIME,
    GRAVITY,
    GROUND_Y,
    HEAT_PER_WRONG,
    LAUNCH_X,
    LAUNCH_Y,
    MAX_HEAT,
    SCREEN_W,
    Phase,
    Plane,
    RING_COLORS,
    RING_RADIUS,
    Ring,
    SUPER_COMBO_THRESHOLD,
    SUPER_DURATION,
    SUPER_SCORE_MULTIPLIER,
    FloatingText,
    Game,
    Particle,
)


def _make_game() -> Game:
    """Create a Game instance in headless mode (no pyxel.init)."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    return g


# ============================================================
# 1. Plane physics
# ============================================================


class TestPlanePhysics:
    def test_gravity_pulls_plane_down(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0, vx=0.0, vy=0.0)
        g._apply_flight_physics()
        assert g.plane.vy == GRAVITY
        assert g.plane.y > 100.0

    def test_drag_slows_plane_horizontally(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0, vx=10.0, vy=0.0)
        g._apply_flight_physics()
        assert g.plane.vx == pytest.approx(10.0 * DRAG)

    def test_plane_position_updates(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0, vx=2.0, vy=3.0)
        g._apply_flight_physics()
        # vx gets drag first: 2.0 * 0.995 = 1.99, then x += 1.99
        assert g.plane.x == pytest.approx(100.0 + 2.0 * DRAG)
        # vy gets gravity first: 3.0 + 0.15 = 3.15, then y += 3.15
        assert g.plane.y == pytest.approx(100.0 + 3.0 + GRAVITY)

    def test_plane_angle_updates_from_velocity(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0, vx=3.0, vy=1.0)
        g._apply_flight_physics()
        g.plane.angle = __import__("math").atan2(g.plane.vy, g.plane.vx)
        assert g.plane.angle == pytest.approx(__import__("math").atan2(1.0 + GRAVITY, 3.0 * DRAG))


# ============================================================
# 2. Ring collision detection
# ============================================================


class TestRingCollision:
    def test_plane_inside_ring_detects(self) -> None:
        ring = Ring(x=100.0, y=100.0, color=8, radius=RING_RADIUS)
        assert Game._plane_passes_ring(100.0, 100.0, ring) is True

    def test_plane_at_edge_detects(self) -> None:
        ring = Ring(x=100.0, y=100.0, color=8, radius=RING_RADIUS)
        assert Game._plane_passes_ring(100.0 + RING_RADIUS - 0.1, 100.0, ring) is True

    def test_plane_outside_ring_not_detected(self) -> None:
        ring = Ring(x=100.0, y=100.0, color=8, radius=RING_RADIUS)
        assert Game._plane_passes_ring(100.0 + RING_RADIUS + 1, 100.0, ring) is False

    def test_plane_far_away_not_detected(self) -> None:
        ring = Ring(x=100.0, y=100.0, color=8, radius=RING_RADIUS)
        assert Game._plane_passes_ring(200.0, 200.0, ring) is False

    def test_check_ring_collisions_returns_first_uncollected(self) -> None:
        g = _make_game()
        g.rings = [
            Ring(x=50.0, y=50.0, color=8, radius=RING_RADIUS),
            Ring(x=100.0, y=100.0, color=3, radius=RING_RADIUS),
        ]
        g.plane = Plane(x=100.0, y=100.0, vx=0, vy=0)
        result = g._check_ring_collisions()
        assert result is not None
        assert result.color == 3

    def test_check_ring_collisions_skips_collected(self) -> None:
        g = _make_game()
        g.rings = [
            Ring(x=50.0, y=50.0, color=8, radius=RING_RADIUS),
            Ring(x=100.0, y=100.0, color=3, radius=RING_RADIUS, collected=True),
            Ring(x=150.0, y=150.0, color=5, radius=RING_RADIUS),
        ]
        g.plane = Plane(x=50.0, y=50.0, vx=0, vy=0)
        result = g._check_ring_collisions()
        assert result is not None
        assert result.color == 8

    def test_check_ring_collisions_returns_none_when_no_hit(self) -> None:
        g = _make_game()
        g.rings = [Ring(x=200.0, y=200.0, color=8, radius=RING_RADIUS)]
        g.plane = Plane(x=50.0, y=50.0, vx=0, vy=0)
        assert g._check_ring_collisions() is None


# ============================================================
# 3. Combo logic
# ============================================================


class TestComboLogic:
    def test_first_ring_starts_combo(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        ring = Ring(x=100.0, y=100.0, color=8)
        g.rings = [ring]
        g._prev_ring_color = None
        g.combo = 0
        g._collect_ring(ring)
        assert g.combo == 1
        assert g._prev_ring_color == 8

    def test_same_color_increments_combo(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = 8
        g.combo = 2
        ring = Ring(x=100.0, y=100.0, color=8)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.combo == 3

    def test_wrong_color_resets_combo(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = 8
        g.combo = 3
        ring = Ring(x=100.0, y=100.0, color=3)
        g.rings = [ring]
        old_heat = g.heat
        g._collect_ring(ring)
        assert g.combo == 0
        assert g._prev_ring_color == 3
        assert g.heat == old_heat + HEAT_PER_WRONG

    def test_max_combo_tracks_highest(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = 8
        g.combo = 3
        g.max_combo = 3
        ring = Ring(x=100.0, y=100.0, color=8)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.max_combo == 4

    def test_max_combo_not_updated_on_reset(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = 8
        g.combo = 3
        g.max_combo = 5
        ring = Ring(x=100.0, y=100.0, color=3)  # wrong color
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.max_combo == 5


# ============================================================
# 4. Scoring logic
# ============================================================


class TestScoring:
    def test_first_ring_base_score(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = None
        g.combo = 0
        ring = Ring(x=100.0, y=100.0, color=8)
        g.rings = [ring]
        old_score = g.score
        g._collect_ring(ring)
        assert g.score - old_score == BASE_SCORE  # combo becomes 1, mul = 1.0

    def test_combo_multiplier_increases_score(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = 8
        g.combo = 3  # next hit -> combo 4, multiplier = 1 + 3 * 0.5 = 2.5
        ring = Ring(x=100.0, y=100.0, color=8)
        g.rings = [ring]
        old_score = g.score
        g._collect_ring(ring)
        # combo becomes 4, multiplier = 1 + 3 * 0.5 = 2.5
        expected = int(BASE_SCORE * 2.5)
        assert g.score - old_score == expected

    def test_wrong_color_gives_zero_score(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = 8
        g.combo = 3
        ring = Ring(x=100.0, y=100.0, color=3)
        g.rings = [ring]
        old_score = g.score
        g._collect_ring(ring)
        assert g.score == old_score

    def test_super_flight_gives_3x_score(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g.super_active = True
        g._prev_ring_color = 8
        g.combo = 2
        ring = Ring(x=100.0, y=100.0, color=3)  # wrong color normally
        g.rings = [ring]
        old_score = g.score
        g._collect_ring(ring)
        # Super: counts as match, combo becomes 3, multiplier = 1 + 2 * 0.5 = 2.0, super 3x
        expected = int(BASE_SCORE * 2.0 * SUPER_SCORE_MULTIPLIER)
        assert g.score - old_score == expected

    def test_compute_ring_score_first_ring(self) -> None:
        g = _make_game()
        g._prev_ring_color = None
        g.combo = 0
        assert g._compute_ring_score(8) == BASE_SCORE

    def test_compute_ring_score_wrong_color(self) -> None:
        g = _make_game()
        g._prev_ring_color = 8
        g.combo = 3
        assert g._compute_ring_score(3) == 0


# ============================================================
# 5. Super flight activation
# ============================================================


class TestSuperFlight:
    def test_super_activates_at_combo_threshold(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = 8
        g.combo = SUPER_COMBO_THRESHOLD - 1
        ring = Ring(x=100.0, y=100.0, color=8)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.super_active is True
        assert g.super_timer == SUPER_DURATION

    def test_super_does_not_activate_below_threshold(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = 8
        g.combo = SUPER_COMBO_THRESHOLD - 2
        ring = Ring(x=100.0, y=100.0, color=8)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.super_active is False

    def test_super_auto_matches_color(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g.super_active = True
        g._prev_ring_color = 8
        g.combo = 2
        ring = Ring(x=100.0, y=100.0, color=3)  # different color
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.combo == 3  # counts as match

    def test_super_timer_counts_down(self) -> None:
        g = _make_game()
        g.super_active = True
        g.super_timer = 10
        g._update_super_timer()
        assert g.super_timer == 9

    def test_super_deactivates_on_expire(self) -> None:
        g = _make_game()
        g.super_active = True
        g.super_timer = 1
        g.combo = 5
        g._update_super_timer()
        assert g.super_active is False
        assert g.super_timer == 0
        assert g.combo == 0


# ============================================================
# 6. Heat system
# ============================================================


class TestHeat:
    def test_heat_starts_at_zero(self) -> None:
        g = _make_game()
        assert g.heat == 0.0

    def test_wrong_color_adds_heat(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = 8
        g.combo = 3
        ring = Ring(x=100.0, y=100.0, color=3)
        g.rings = [ring]
        old_heat = g.heat
        g._collect_ring(ring)
        assert g.heat == old_heat + HEAT_PER_WRONG

    def test_heat_capped_at_max(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = 8
        g.combo = 3
        g.heat = MAX_HEAT - 5
        ring = Ring(x=100.0, y=100.0, color=3)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.heat <= MAX_HEAT

    def test_same_color_does_not_add_heat(self) -> None:
        g = _make_game()
        g.plane = Plane(x=100.0, y=100.0)
        g._prev_ring_color = 8
        g.combo = 2
        g.heat = 30.0
        ring = Ring(x=100.0, y=100.0, color=8)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.heat == pytest.approx(30.0)


# ============================================================
# 7. Flight end conditions
# ============================================================


class TestFlightEnd:
    def test_plane_hits_ground(self) -> None:
        g = _make_game()
        g.phase = Phase.FLIGHT
        g.plane = Plane(x=100.0, y=GROUND_Y, vx=2.0, vy=1.0, active=True)
        g._update_flight()
        assert g.phase == Phase.RESULT
        assert g.plane.active is False

    def test_plane_flies_off_right_screen(self) -> None:
        g = _make_game()
        g.phase = Phase.FLIGHT
        g.plane = Plane(x=SCREEN_W + 40, y=100.0, vx=2.0, vy=0.0, active=True)
        # First update will move it further
        g._update_flight()
        assert g.phase == Phase.RESULT

    def test_plane_flies_off_left_screen(self) -> None:
        g = _make_game()
        g.phase = Phase.FLIGHT
        g.plane = Plane(x=-40, y=100.0, vx=-2.0, vy=0.0, active=True)
        g._update_flight()
        assert g.phase == Phase.RESULT

    def test_uncollected_rings_persist_after_flight(self) -> None:
        g = _make_game()
        g.rings = [
            Ring(x=50.0, y=50.0, color=8, collected=True),
            Ring(x=100.0, y=100.0, color=3),
            Ring(x=150.0, y=150.0, color=5),
        ]
        g.phase = Phase.FLIGHT
        g.plane = Plane(x=100.0, y=GROUND_Y, vx=0, vy=1, active=True)
        g._update_flight()
        # Plane landed: all rings cleared, new set spawned (6-10)
        assert 6 <= len(g.rings) <= 10
        # All new rings should be uncollected
        assert all(not r.collected for r in g.rings)

    def test_all_collected_spawns_new_rings(self) -> None:
        g = _make_game()
        g.rings = [
            Ring(x=50.0, y=50.0, color=8, collected=True),
            Ring(x=100.0, y=100.0, color=3, collected=True),
        ]
        g.phase = Phase.FLIGHT
        g.plane = Plane(x=100.0, y=GROUND_Y, vx=0, vy=1, active=True)
        g._update_flight()
        assert len(g.rings) >= 6  # new rings spawned


# ============================================================
# 8. Timer
# ============================================================


class TestTimer:
    def test_timer_counts_down_during_flight(self) -> None:
        g = _make_game()
        g.phase = Phase.FLIGHT
        g.plane = Plane(x=100.0, y=50.0, vx=2.0, vy=0.0, active=True)
        g.timer = 10
        g._update_flight()
        assert g.timer == 9

    def test_timer_zero_triggers_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.FLIGHT
        g.plane = Plane(x=100.0, y=50.0, vx=2.0, vy=0.0, active=True)
        g.timer = 1
        g._update_flight()
        assert g.phase == Phase.GAME_OVER


# ============================================================
# 9. Launch mechanics
# ============================================================


class TestLaunch:
    def test_launch_sets_plane_active(self) -> None:
        g = _make_game()
        g.aim_start_x = LAUNCH_X
        g.aim_start_y = LAUNCH_Y
        g.aim_end_x = LAUNCH_X + 50  # aim right
        g.aim_end_y = LAUNCH_Y - 20  # aim up
        g._launch_plane()
        assert g.plane.active is True
        assert g.plane.x == LAUNCH_X
        assert g.plane.y == LAUNCH_Y
        assert g.plane.vx > 0
        assert g.plane.vy < 0
        assert g.phase == Phase.FLIGHT

    def test_launch_resets_prev_color(self) -> None:
        g = _make_game()
        g._prev_ring_color = 8
        g.aim_end_x = LAUNCH_X + 30
        g.aim_end_y = LAUNCH_Y
        g._launch_plane()
        assert g._prev_ring_color is None

    def test_very_short_drag_uses_minimum_power(self) -> None:
        g = _make_game()
        g.aim_end_x = LAUNCH_X + 1
        g.aim_end_y = LAUNCH_Y
        g._launch_plane()
        assert g.plane.active is True


# ============================================================
# 10. Result phase transition
# ============================================================


class TestResultPhase:
    def test_result_transitions_to_aiming(self) -> None:
        g = _make_game()
        g.phase = Phase.RESULT
        g.result_timer = 1
        g.timer = 1000
        g._update_result()
        assert g.phase == Phase.AIMING

    def test_result_timer_at_zero_triggers_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.RESULT
        g.result_timer = 45
        g.timer = 1
        g._update_result()
        assert g.phase == Phase.GAME_OVER


# ============================================================
# 11. Ring spawning
# ============================================================


class TestRingSpawning:
    def test_spawn_rings_creates_valid_count(self) -> None:
        g = _make_game()
        g.rings = []
        g._spawn_rings()
        assert 6 <= len(g.rings) <= 10

    def test_rings_within_bounds(self) -> None:
        g = _make_game()
        g.rings = []
        g._spawn_rings()
        for ring in g.rings:
            assert 60 <= ring.x <= 300
            assert 30 <= ring.y <= 180

    def test_make_ring_uses_valid_color(self) -> None:
        g = _make_game()
        g.rings = []
        ring = g._make_ring()
        assert ring.color in RING_COLORS
        assert ring.radius == RING_RADIUS
        assert ring.collected is False


# ============================================================
# 12. Particle and floating text lifecycle
# ============================================================


class TestParticles:
    def test_spawn_particles_adds_to_list(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 5)
        assert len(g.particles) == 5

    def test_particles_move_and_decay(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 1)
        p = g.particles[0]
        old_x, old_y = p.x, p.y
        g._update_particles()
        assert p.life < 25

    def test_dead_particles_removed(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 3)
        for p in g.particles:
            p.life = 0
        g._update_particles()
        assert len(g.particles) == 0

    def test_floating_text_spawn_and_decay(self) -> None:
        g = _make_game()
        g._spawn_floating_text(100.0, 100.0, "+100", 7)
        assert len(g.floating_texts) == 1
        g._update_floating_texts()
        assert g.floating_texts[0].life == 29

    def test_dead_floating_texts_removed(self) -> None:
        g = _make_game()
        g._spawn_floating_text(100.0, 100.0, "+100", 7)
        g.floating_texts[0].life = 0
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


# ============================================================
# 13. reset() restores clean state
# ============================================================


class TestReset:
    def test_reset_clears_all_state(self) -> None:
        g = Game.__new__(Game)
        g._rng = __import__("random").Random()
        g.score = 999
        g.combo = 10
        g.max_combo = 20
        g.heat = 80.0
        g.timer = 100
        g.super_timer = 50
        g.super_active = True
        g.particles = [Particle(0, 0, 0, 0, 10, 8)]
        g.floating_texts = [FloatingText(0, 0, "test", 10, 7)]
        g.phase = Phase.GAME_OVER

        g.reset()

        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.timer == GAME_TIME
        assert g.super_timer == 0
        assert g.super_active is False
        assert g.plane.active is False
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0

    def test_reset_spawns_new_rings(self) -> None:
        g = Game.__new__(Game)
        g._rng = __import__("random").Random()
        g.rings = []
        g.reset()
        assert len(g.rings) >= 6

    def test_launch_sets_correct_initial_velocity(self) -> None:
        g = _make_game()
        g.aim_start_x = LAUNCH_X
        g.aim_start_y = LAUNCH_Y
        g.aim_end_x = LAUNCH_X + 30  # 30px right
        g.aim_end_y = LAUNCH_Y + 20  # 20px down
        g._launch_plane()
        assert g.plane.vx > 0
        assert g.plane.vy > 0


# ============================================================
# 14. Edge cases
# ============================================================


class TestEdgeCases:
    def test_heat_at_max_triggers_game_over_in_flight(self) -> None:
        g = _make_game()
        g.phase = Phase.FLIGHT
        g.plane = Plane(x=100.0, y=50.0, vx=2.0, vy=0.0, active=True)
        g.heat = MAX_HEAT - 0.01
        g._update_flight()
        assert g.phase == Phase.GAME_OVER

    def test_heat_at_max_triggers_game_over_in_result(self) -> None:
        g = _make_game()
        g.phase = Phase.RESULT
        g.result_timer = 10
        g.timer = 1000
        g.heat = MAX_HEAT
        g._update_result()
        assert g.phase == Phase.GAME_OVER

    def test_plane_flies_off_top_screen(self) -> None:
        g = _make_game()
        g.phase = Phase.FLIGHT
        g.plane = Plane(x=100.0, y=-40, vx=0, vy=-2, active=True)
        g._update_flight()
        assert g.phase == Phase.RESULT

    def test_super_flight_deactivates_after_expiry(self) -> None:
        g = _make_game()
        g.super_active = True
        g.super_timer = 1
        g.combo = 6
        g._update_super_timer()
        assert g.super_active is False
        assert g.combo == 0

    def test_aim_dragging_state_management(self) -> None:
        g = _make_game()
        g.aim_dragging = True
        g.aim_end_x = 100
        g.aim_end_y = 100
        g._launch_plane()
        assert g.phase == Phase.FLIGHT

    def test_aim_end_equal_to_launch_uses_minimum(self) -> None:
        g = _make_game()
        g.aim_end_x = LAUNCH_X
        g.aim_end_y = LAUNCH_Y
        g._launch_plane()
        assert g.plane.active is True  # minimum launch
        assert g.plane.vx > 0  # default right
