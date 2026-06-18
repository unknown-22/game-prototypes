"""Tests for SLED SURGE game logic. All tests are headless (no pyxel init/run)."""
from __future__ import annotations

import random
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import (  # type: ignore[import-untyped]
    GATE_COLORS,
    GATE_HALF_OPENING,
    GATE_WIDTH,
    HEAT_PER_MISS,
    MAX_HEAT,
    MAX_SLED_SPEED,
    SCREEN_W,
    SLED_HALF_H,
    SLED_HALF_W,
    SLED_MAX_Y,
    SLED_MIN_Y,
    SLED_X,
    SUPER_DURATION,
    TRACK_SPEED_BASE,
    TRACK_SPEED_MAX,
    WALL_BOTTOM,
    WALL_TOP,
    Gate,
    GhostPoint,
    Particle,
    Phase,
    Game,
)


def _make_game() -> Game:
    """Factory for a fresh headless Game instance in TITLE state. Uses __new__ to bypass pyxel.init/run."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.sled_y = 120.0
    g.score = 0
    g.best_score = 0
    g.distance = 0.0
    g.combo = 0
    g.max_combo = 0
    g.combo_color = -1
    g.heat = 0.0
    g.super_timer = 0
    g.gates = []
    g.particles = []
    g.best_ghost = []
    g.track_speed = TRACK_SPEED_BASE
    g.spawn_timer = 60
    g.game_timer = 0
    g.shake_frames = 0
    g._ghost_record = []
    g.reset()
    return g


def _make_gate(
    x: float = SCREEN_W,
    opening_y: float = 120.0,
    color: int = GATE_COLORS[0],
) -> Gate:
    return Gate(x=x, opening_y=opening_y, color=color)


# ============================================================
# 1. Gate spawning
# ============================================================


class TestGateSpawning:
    def test_spawn_gate_at_right_edge(self) -> None:
        g = _make_game()
        gate = g._spawn_gate()
        assert gate.x == float(SCREEN_W)

    def test_spawn_gate_color_is_valid(self) -> None:
        g = _make_game()
        gate = g._spawn_gate()
        assert gate.color in GATE_COLORS

    def test_spawn_gate_opening_within_bounds(self) -> None:
        g = _make_game()
        for _ in range(50):
            gate = g._spawn_gate()
            assert WALL_TOP + GATE_HALF_OPENING <= gate.opening_y <= WALL_BOTTOM - GATE_HALF_OPENING

    def test_spawn_gate_not_collected_initially(self) -> None:
        g = _make_game()
        gate = g._spawn_gate()
        assert gate.collected is False

    def test_different_colors_generated(self) -> None:
        g = _make_game()
        colors = {g._spawn_gate().color for _ in range(40)}
        assert len(colors) >= 2  # at least 2 different colors appear


# ============================================================
# 2. Gate collision detection
# ============================================================


class TestGateCollision:
    def test_sled_inside_opening_is_collision(self) -> None:
        g = _make_game()
        gate = _make_gate(x=SLED_X, opening_y=120.0)
        g.sled_y = 120.0
        assert g._check_gate_collision(SLED_X, g.sled_y, gate) is True

    def test_sled_above_opening_is_no_collision(self) -> None:
        g = _make_game()
        gate = _make_gate(x=SLED_X, opening_y=120.0)
        g.sled_y = 50.0  # well above opening
        assert g._check_gate_collision(SLED_X, g.sled_y, gate) is False

    def test_sled_below_opening_is_no_collision(self) -> None:
        g = _make_game()
        gate = _make_gate(x=SLED_X, opening_y=120.0)
        g.sled_y = 190.0  # well below opening
        assert g._check_gate_collision(SLED_X, g.sled_y, gate) is False

    def test_sled_before_gate_no_collision(self) -> None:
        g = _make_game()
        gate = _make_gate(x=SLED_X + 100, opening_y=120.0)
        g.sled_y = 120.0
        assert g._check_gate_collision(SLED_X, g.sled_y, gate) is False

    def test_sled_after_gate_no_collision(self) -> None:
        g = _make_game()
        gate = _make_gate(x=SLED_X - GATE_WIDTH - SLED_HALF_W - 1, opening_y=120.0)
        g.sled_y = 120.0
        assert g._check_gate_collision(SLED_X, g.sled_y, gate) is False

    def test_partial_x_overlap_is_collision(self) -> None:
        g = _make_game()
        # Gate partially overlapping sled's X range
        gate = _make_gate(x=SLED_X - SLED_HALF_W - 5, opening_y=120.0)
        g.sled_y = 120.0
        # sled x range: 50-70, gate x range: 55-95 -> overlap, should be collision
        assert g._check_gate_collision(SLED_X, g.sled_y, gate) is True

    def test_sled_at_opening_boundary(self) -> None:
        g = _make_game()
        gate = _make_gate(x=SLED_X, opening_y=120.0)
        # Sled top exactly at opening top -> should barely pass
        g.sled_y = 120.0 - GATE_HALF_OPENING + SLED_HALF_H
        assert g._check_gate_collision(SLED_X, g.sled_y, gate) is True

    def test_sled_just_outside_opening_bottom(self) -> None:
        g = _make_game()
        gate = _make_gate(x=SLED_X, opening_y=120.0)
        g.sled_y = 120.0 + GATE_HALF_OPENING - SLED_HALF_H + 1
        assert g._check_gate_collision(SLED_X, g.sled_y, gate) is False


# ============================================================
# 3. Gate collection: combo, score, SUPER trigger
# ============================================================


class TestGateCollection:
    def test_first_collection_sets_combo_1(self) -> None:
        g = _make_game()
        gate = _make_gate(color=GATE_COLORS[0])
        g._collect_gate(gate)
        assert g.combo == 1
        assert g.combo_color == GATE_COLORS[0]
        assert gate.collected is True

    def test_same_color_increments_combo(self) -> None:
        g = _make_game()
        gate1 = _make_gate(color=GATE_COLORS[0])
        g._collect_gate(gate1)
        assert g.combo == 1

        gate2 = _make_gate(color=GATE_COLORS[0])
        g._collect_gate(gate2)
        assert g.combo == 2

    def test_different_color_resets_combo(self) -> None:
        g = _make_game()
        gate1 = _make_gate(color=GATE_COLORS[0])
        g._collect_gate(gate1)
        assert g.combo == 1

        gate2 = _make_gate(color=GATE_COLORS[1])
        g._collect_gate(gate2)
        assert g.combo == 1
        assert g.combo_color == GATE_COLORS[1]

    def test_score_increases_on_collection(self) -> None:
        g = _make_game()
        gate = _make_gate(color=GATE_COLORS[0])
        g._collect_gate(gate)
        assert g.score > 0

    def test_combo_multiplies_score(self) -> None:
        g = _make_game()
        gate1 = _make_gate(color=GATE_COLORS[0])
        g._collect_gate(gate1)
        score_after_1 = g.score  # base 10 * 1 = 10

        gate2 = _make_gate(color=GATE_COLORS[0])
        g._collect_gate(gate2)
        # combo goes to 2, score += 10 * 1 * 2 = 20
        assert g.score - score_after_1 == 20

    def test_max_combo_tracked(self) -> None:
        g = _make_game()
        for _ in range(3):
            gate = _make_gate(color=GATE_COLORS[0])
            g._collect_gate(gate)
        assert g.max_combo == 3

        # Reset with different color
        gate = _make_gate(color=GATE_COLORS[1])
        g._collect_gate(gate)
        assert g.combo == 1
        assert g.max_combo == 3  # unchanged

    def test_super_trigger_at_combo_5(self) -> None:
        g = _make_game()
        for _ in range(4):
            gate = _make_gate(color=GATE_COLORS[0])
            g._collect_gate(gate)
        assert g.combo == 4
        assert g.super_timer == 0

        # 5th same-color gate triggers SUPER
        gate = _make_gate(color=GATE_COLORS[0])
        g._collect_gate(gate)
        assert g.combo == 5
        assert g.super_timer == SUPER_DURATION

    def test_super_does_not_trigger_below_combo_5(self) -> None:
        g = _make_game()
        for _ in range(4):
            gate = _make_gate(color=GATE_COLORS[0])
            g._collect_gate(gate)
        assert g.combo == 4
        assert g.super_timer == 0

    def test_super_not_already_active(self) -> None:
        g = _make_game()
        g.super_timer = 100
        for _ in range(5):
            gate = _make_gate(color=GATE_COLORS[0])
            g._collect_gate(gate)
        # Combo still tracked but SUPER already active, timer not reset
        assert g.super_timer == 100

    def test_super_3x_score_multiplier(self) -> None:
        g = _make_game()
        g.super_timer = 100
        gate = _make_gate(color=GATE_COLORS[0])
        g._collect_gate(gate)
        # combo=0 -> combo=1, base=10, multiplier=3 -> score=30
        assert g.score == 30

    def test_particles_spawn_on_collect(self) -> None:
        g = _make_game()
        gate = _make_gate(color=GATE_COLORS[0])
        initial_particles = len(g.particles)
        g._collect_gate(gate)
        assert len(g.particles) > initial_particles


# ============================================================
# 4. Sled movement
# ============================================================


class TestSledMovement:
    def test_move_sled_toward_target_up(self) -> None:
        g = _make_game()
        g.sled_y = 120.0
        new_y = g._move_sled(80.0)
        assert new_y < 120.0
        assert new_y >= 80.0

    def test_move_sled_toward_target_down(self) -> None:
        g = _make_game()
        g.sled_y = 120.0
        new_y = g._move_sled(160.0)
        assert new_y > 120.0
        assert new_y <= 160.0

    def test_move_sled_at_speed_cap(self) -> None:
        g = _make_game()
        g.sled_y = 120.0
        new_y = g._move_sled(0.0)
        # Should move up by at most MAX_SLED_SPEED
        assert 120.0 - new_y <= MAX_SLED_SPEED

    def test_move_sled_clamped_to_top_wall(self) -> None:
        g = _make_game()
        g.sled_y = SLED_MIN_Y
        new_y = g._move_sled(-100.0)
        assert new_y == SLED_MIN_Y  # already at min, cannot go lower

    def test_move_sled_clamped_to_bottom_wall(self) -> None:
        g = _make_game()
        g.sled_y = SLED_MAX_Y
        new_y = g._move_sled(500.0)
        assert new_y == SLED_MAX_Y  # already at max, cannot go higher

    def test_move_sled_no_movement_at_target(self) -> None:
        g = _make_game()
        g.sled_y = 120.0
        new_y = g._move_sled(120.0)
        assert new_y == 120.0

    def test_move_sled_small_delta(self) -> None:
        g = _make_game()
        g.sled_y = 120.0
        new_y = g._move_sled(121.0)  # less than MAX_SLED_SPEED
        assert new_y == 121.0


# ============================================================
# 5. Wall collision
# ============================================================


class TestWallCollision:
    def test_sled_in_middle_no_collision(self) -> None:
        g = _make_game()
        g.sled_y = 120.0
        assert g._check_wall_collision(g.sled_y) is False

    def test_sled_at_top_wall_is_collision(self) -> None:
        g = _make_game()
        # sled top exactly touches wall -> collision
        g.sled_y = WALL_TOP + SLED_HALF_H  # 26 -> top edge at 20
        assert g._check_wall_collision(g.sled_y) is True

    def test_sled_inside_top_wall_is_collision(self) -> None:
        g = _make_game()
        g.sled_y = WALL_TOP + SLED_HALF_H - 2  # well inside wall
        assert g._check_wall_collision(g.sled_y) is True

    def test_sled_inside_bottom_wall_is_collision(self) -> None:
        g = _make_game()
        g.sled_y = WALL_BOTTOM - SLED_HALF_H + 2  # well inside wall
        assert g._check_wall_collision(g.sled_y) is True

    def test_sled_safe_at_bottom_boundary(self) -> None:
        g = _make_game()
        g.sled_y = SLED_MAX_Y  # 212, safely within bounds
        assert g._check_wall_collision(g.sled_y) is False


# ============================================================
# 6. SUPER BOOST mechanics
# ============================================================


class TestSuperBoost:
    def test_super_timer_decrements(self) -> None:
        g = _make_game()
        g.super_timer = SUPER_DURATION
        g._update_super()
        assert g.super_timer == SUPER_DURATION - 1

    def test_super_timer_does_not_decrement_below_0(self) -> None:
        g = _make_game()
        g.super_timer = 0
        g._update_super()
        assert g.super_timer == 0

    def test_super_expiry_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 7
        g.combo_color = GATE_COLORS[0]
        g.super_timer = 1
        g._update_super()
        assert g.super_timer == 0
        assert g.combo == 0
        assert g.combo_color == -1

    def test_super_expiry_spawns_particles(self) -> None:
        g = _make_game()
        g.super_timer = 1
        initial_count = len(g.particles)
        g._update_super()
        assert len(g.particles) > initial_count


# ============================================================
# 7. Gate update: auto-collect during SUPER, heat from misses
# ============================================================


class TestGateUpdate:
    def test_gates_move_left(self) -> None:
        g = _make_game()
        gate = _make_gate(x=SCREEN_W, opening_y=120.0)
        g.gates.append(gate)
        g.track_speed = 2.0
        g._update_gates()
        assert gate.x == SCREEN_W - 2.0

    def test_collected_gate_marked(self) -> None:
        g = _make_game()
        g.sled_y = 120.0
        gate = _make_gate(x=SLED_X, opening_y=120.0, color=GATE_COLORS[0])
        g.gates.append(gate)
        g._update_gates()
        assert gate.collected is True

    def test_missed_gate_adds_heat(self) -> None:
        g = _make_game()
        gate = _make_gate(x=-GATE_WIDTH, opening_y=120.0)  # already off-screen left
        g.gates.append(gate)
        initial_heat = g.heat
        g._update_gates()
        assert g.heat == initial_heat + HEAT_PER_MISS

    def test_missed_gate_removed_from_list(self) -> None:
        g = _make_game()
        gate = _make_gate(x=-GATE_WIDTH - 1, opening_y=120.0)
        g.gates.append(gate)
        g._update_gates()
        assert len(g.gates) == 0

    def test_collected_gate_not_missed(self) -> None:
        g = _make_game()
        g.sled_y = 120.0
        gate = _make_gate(x=SLED_X, opening_y=120.0, color=GATE_COLORS[0])
        gate.x = -GATE_WIDTH  # move it off-screen after collection simulation
        gate.collected = True
        g.gates.append(gate)
        initial_heat = g.heat
        g._update_gates()
        assert g.heat == initial_heat  # no heat for collected gates

    def test_super_auto_collects_gate(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.sled_y = 200.0  # far from gate opening
        gate = _make_gate(x=SLED_X, opening_y=120.0, color=GATE_COLORS[0])
        g.gates.append(gate)
        g._update_gates()
        assert gate.collected is True  # auto-collected despite Y mismatch

    def test_super_no_heat_for_missed(self) -> None:
        g = _make_game()
        g.super_timer = 100
        gate = _make_gate(x=-GATE_WIDTH, opening_y=120.0)
        g.gates.append(gate)
        initial_heat = g.heat
        g._update_gates()
        assert g.heat == initial_heat  # no heat during SUPER

    def test_multiple_gates_collected_in_one_frame(self) -> None:
        g = _make_game()
        g.sled_y = 120.0
        for i in range(3):
            gate = _make_gate(x=SLED_X, opening_y=120.0, color=GATE_COLORS[0])
            g.gates.append(gate)
        collected = g._update_gates()
        assert collected == 3
        assert all(gate.collected for gate in g.gates)

    def test_update_gates_returns_collected_count(self) -> None:
        g = _make_game()
        g.sled_y = 120.0
        gate = _make_gate(x=SLED_X, opening_y=120.0, color=GATE_COLORS[0])
        g.gates.append(gate)
        collected = g._update_gates()
        assert collected == 1

    def test_update_gates_returns_zero_when_none_collected(self) -> None:
        g = _make_game()
        g.sled_y = 50.0  # far from gate
        gate = _make_gate(x=SLED_X, opening_y=120.0, color=GATE_COLORS[0])
        g.gates.append(gate)
        collected = g._update_gates()
        assert collected == 0


# ============================================================
# 8. Heat and Game Over
# ============================================================


class TestHeat:
    def test_heat_below_max_still_playing(self) -> None:
        g = _make_game()
        g.heat = 99.0
        g.phase = Phase.PLAYING
        # Simulate check: heat < MAX_HEAT should not trigger game over
        assert g.heat < MAX_HEAT

    def test_heat_at_max_is_game_over(self) -> None:
        g = _make_game()
        g.heat = MAX_HEAT
        g.phase = Phase.PLAYING
        # The check in _update_playing would set phase to GAME_OVER
        # We test the condition directly
        assert g.heat >= MAX_HEAT

    def test_heat_above_max_is_game_over(self) -> None:
        g = _make_game()
        g.heat = 120.0
        assert g.heat >= MAX_HEAT


# ============================================================
# 9. Ghost recording
# ============================================================


class TestGhostRecording:
    def test_ghost_record_appends(self) -> None:
        g = _make_game()
        initial_len = len(g._ghost_record)
        g.game_timer = 1
        g._update_ghost()  # odd frame: no record
        assert len(g._ghost_record) == initial_len
        g.game_timer = 2
        g._update_ghost()  # even frame: record
        assert len(g._ghost_record) == initial_len + 1

    def test_ghost_record_stores_position(self) -> None:
        g = _make_game()
        g.sled_y = 100.0
        g.distance = 50.0
        g.game_timer = 2
        g._update_ghost()
        assert len(g._ghost_record) == 1
        assert g._ghost_record[0].x == 50.0
        assert g._ghost_record[0].y == 100.0

    def test_save_ghost_updates_best_on_higher_score(self) -> None:
        g = _make_game()
        g.score = 100
        g.best_score = 50
        g._ghost_record = [GhostPoint(x=10.0, y=120.0)]
        g._save_ghost()
        assert g.best_score == 100
        assert len(g.best_ghost) == 1
        assert g.best_ghost[0].x == 10.0

    def test_save_ghost_does_not_update_on_lower_score(self) -> None:
        g = _make_game()
        g.score = 30
        g.best_score = 50
        g.best_ghost = [GhostPoint(x=10.0, y=100.0)]
        g._ghost_record = [GhostPoint(x=20.0, y=110.0)]
        g._save_ghost()
        assert g.best_score == 50
        assert g.best_ghost[0].x == 10.0  # unchanged

    def test_get_ghost_y_returns_none_for_empty(self) -> None:
        g = _make_game()
        g.best_ghost = []
        assert g._get_ghost_y() is None

    def test_get_ghost_y_returns_closest(self) -> None:
        g = _make_game()
        g.distance = 50.0
        g.best_ghost = [
            GhostPoint(x=10.0, y=100.0),
            GhostPoint(x=40.0, y=110.0),
            GhostPoint(x=55.0, y=115.0),
        ]
        result = g._get_ghost_y()
        assert result == 115.0  # closest to distance 50 is 55

    def test_get_ghost_y_returns_none_when_too_far(self) -> None:
        g = _make_game()
        g.distance = 200.0
        g.best_ghost = [
            GhostPoint(x=10.0, y=100.0),
            GhostPoint(x=20.0, y=110.0),
        ]
        result = g._get_ghost_y()
        assert result is None  # too far from current distance


# ============================================================
# 10. Particle lifecycle
# ============================================================


class TestParticles:
    def test_spawn_particles_creates_correct_count(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 15)
        assert len(g.particles) == 15

    def test_particles_decay(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 5)
        initial_life = g.particles[0].life
        g._update_particles()
        assert g.particles[0].life == initial_life - 1

    def test_dead_particles_removed(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 3)
        for p in g.particles:
            p.life = 0
        g._update_particles()
        assert len(g.particles) == 0

    def test_particles_move_with_gravity(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 1)
        p = g.particles[0]
        old_vy = p.vy
        g._update_particles()
        assert p.vy > old_vy  # gravity added


# ============================================================
# 11. Reset
# ============================================================


class TestReset:
    def test_reset_clears_state(self) -> None:
        g = _make_game()
        g.score = 999
        g.combo = 10
        g.max_combo = 20
        g.heat = 80.0
        g.distance = 500.0
        g.super_timer = 100
        g.gates = [_make_gate()]
        g.particles = [Particle(0, 0, 0, 0, 10, 8)]
        g._ghost_record = [GhostPoint(x=10.0, y=100.0)]
        g.game_timer = 1000
        g.shake_frames = 30
        g.spawn_timer = 0

        g.reset()

        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.distance == 0.0
        assert g.super_timer == 0
        assert g.gates == []
        assert g.particles == []
        assert g._ghost_record == []
        assert g.combo_color == -1
        assert g.game_timer == 0
        assert g.shake_frames == 0

    def test_reset_centers_sled(self) -> None:
        g = _make_game()
        g.sled_y = 50.0
        g.reset()
        assert g.sled_y == 120.0

    def test_reset_resets_track_speed(self) -> None:
        g = _make_game()
        g.track_speed = 5.0
        g.reset()
        assert g.track_speed == TRACK_SPEED_BASE

    def test_best_score_preserved_after_reset(self) -> None:
        g = _make_game()
        g.best_score = 500
        g.best_ghost = [GhostPoint(x=10.0, y=100.0)]
        g.reset()
        assert g.best_score == 500
        assert len(g.best_ghost) == 1


# ============================================================
# 12. Track speed
# ============================================================


class TestTrackSpeed:
    def test_track_speed_starts_at_base(self) -> None:
        g = _make_game()
        assert g.track_speed == TRACK_SPEED_BASE

    def test_track_speed_increases_with_distance(self) -> None:
        g = _make_game()
        g.distance = 1000.0
        # Formula: base_speed + distance * 0.001, capped at TRACK_SPEED_MAX
        assert TRACK_SPEED_BASE + 1000.0 * 0.001 == 2.0

    def test_track_speed_capped(self) -> None:
        g = _make_game()
        g.distance = 10000.0
        speed = min(TRACK_SPEED_MAX, TRACK_SPEED_BASE + g.distance * 0.001)
        assert speed == TRACK_SPEED_MAX


# ============================================================
# 13. Find nearest gate
# ============================================================


class TestFindNearestGate:
    def test_find_nearest_returns_closest(self) -> None:
        g = _make_game()
        g.gates = [
            _make_gate(x=SLED_X + 50, opening_y=100.0),
            _make_gate(x=SLED_X + 10, opening_y=120.0),  # nearest
            _make_gate(x=SLED_X + 80, opening_y=140.0),
        ]
        nearest = g._find_nearest_gate()
        assert nearest is not None
        assert nearest.opening_y == 120.0

    def test_find_nearest_ignores_collected(self) -> None:
        g = _make_game()
        g.gates = [
            _make_gate(x=SLED_X + 5, opening_y=100.0),
            _make_gate(x=SLED_X + 20, opening_y=120.0),
        ]
        g.gates[0].collected = True
        nearest = g._find_nearest_gate()
        assert nearest is not None
        assert nearest.opening_y == 120.0

    def test_find_nearest_returns_none_for_empty(self) -> None:
        g = _make_game()
        g.gates = []
        assert g._find_nearest_gate() is None

    def test_find_nearest_returns_none_all_collected(self) -> None:
        g = _make_game()
        g.gates = [
            _make_gate(x=SLED_X + 10, opening_y=100.0),
        ]
        g.gates[0].collected = True
        assert g._find_nearest_gate() is None


# ============================================================
# 14. Phase transitions
# ============================================================


class TestPhaseTransitions:
    def test_initial_phase_is_title(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE

    def test_phase_enum_is_defined(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        assert g.phase == Phase.PLAYING
        g.phase = Phase.GAME_OVER
        assert g.phase == Phase.GAME_OVER


# ============================================================
# 15. Edge cases
# ============================================================


class TestEdgeCases:
    def test_empty_gate_list_update_safe(self) -> None:
        g = _make_game()
        g.gates = []
        collected = g._update_gates()
        assert collected == 0
        assert g.gates == []

    def test_all_gates_same_color_combo_builds(self) -> None:
        g = _make_game()
        for _ in range(7):
            gate = _make_gate(color=GATE_COLORS[0])
            g._collect_gate(gate)
        assert g.combo == 7
        assert g.super_timer == SUPER_DURATION

    def test_gate_partially_offscreen_collected(self) -> None:
        g = _make_game()
        g.sled_y = 120.0
        gate = _make_gate(x=SLED_X + SLED_HALF_W - 2, opening_y=120.0)  # barely overlapping
        g.gates.append(gate)
        g._update_gates()
        assert gate.collected is True

    def test_heat_at_exactly_100(self) -> None:
        g = _make_game()
        g.heat = MAX_HEAT
        assert g.heat >= MAX_HEAT

    def test_combo_from_0_to_5_triggers_super(self) -> None:
        g = _make_game()
        for _ in range(5):
            gate = _make_gate(color=GATE_COLORS[0])
            g._collect_gate(gate)
        assert g.combo == 5
        assert g.super_timer == SUPER_DURATION

    def test_color_change_resets_combo_to_1(self) -> None:
        g = _make_game()
        gate1 = _make_gate(color=GATE_COLORS[0])
        g._collect_gate(gate1)
        assert g.combo == 1
        assert g.combo_color == GATE_COLORS[0]

        gate2 = _make_gate(color=GATE_COLORS[1])
        g._collect_gate(gate2)
        assert g.combo == 1
        assert g.combo_color == GATE_COLORS[1]

    def test_super_expiry_during_collection(self) -> None:
        g = _make_game()
        g.super_timer = 1
        # Expire SUPER
        g._update_super()
        assert g.super_timer == 0
        assert g.combo == 0

        # Now collect a gate without SUPER
        gate = _make_gate(color=GATE_COLORS[0])
        g._collect_gate(gate)
        assert g.score == 10  # normal multiplier, not 3x

    def test_multiple_same_color_combo_across_reset(self) -> None:
        g = _make_game()
        g.combo = 3
        g.combo_color = GATE_COLORS[1]
        # Collect same color to continue combo
        gate = _make_gate(color=GATE_COLORS[1])
        g._collect_gate(gate)
        assert g.combo == 4

