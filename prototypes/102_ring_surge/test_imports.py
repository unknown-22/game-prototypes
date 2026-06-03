"""test_imports.py -- Headless logic tests for 102_ring_surge."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from main import (
    COMBO_BONUS_MULT,
    DARK_BLUE,
    GREEN,
    HEAT_PER_MISMATCH,
    HEAT_PER_PUSH,
    MAX_HEAT,
    OPPONENT_COLOR,
    OPPONENT_RADIUS,
    OPPONENT_SPEED_BASE,
    OPPONENT_SPEED_PER_ROUND,
    OVERHEAT_DURATION,
    Particle,
    Phase,
    PLAYER_COLOR,
    PLAYER_RADIUS,
    PUSH_FORCE,
    RED,
    RING_CX,
    RING_CY,
    RING_OUT_SCORE,
    RING_OUT_TIMER,
    RING_RADIUS,
    SCREEN_H,
    SCREEN_W,
    SHAKE_FRAMES,
    SUPER_COMBO,
    SUPER_DURATION,
    SUPER_FORCE_MULT,
    YELLOW,
    ZONE_ANGLE,
    ZONE_OFFSET,
    Wrestler,
    Game,
)


def _make_game() -> Game:
    """Factory: create a Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.max_combo = 0
    g.combo = 0
    g.round_num = 1
    g.prev_zone_color = None
    g.super_push_timer = 0
    g.heat = 0.0
    g.overheat_timer = 0
    g.player = Wrestler(x=RING_CX, y=RING_CY - 60, radius=PLAYER_RADIUS, color=PLAYER_COLOR)
    g.opponent = Wrestler(x=RING_CX, y=RING_CY + 60, radius=OPPONENT_RADIUS, color=OPPONENT_COLOR)
    g.particles = []
    g.ring_out_timer = 0
    g.shake_frames = 0
    g.player_pushing = False
    g.color_zones = []
    g._init_zones()
    g.reset()
    # reset() sets phase to TITLE; set to PLAYING for tests
    g.phase = Phase.PLAYING
    return g


class TestConstants:
    def test_screen_size(self) -> None:
        assert SCREEN_W == 320
        assert SCREEN_H == 240

    def test_ring_center(self) -> None:
        assert RING_CX == 160.0
        assert RING_CY == 120.0
        assert RING_RADIUS == 100

    def test_zone_config(self) -> None:
        assert ZONE_ANGLE == 80
        assert ZONE_OFFSET == 5

    def test_super_threshold(self) -> None:
        assert SUPER_COMBO == 4
        assert SUPER_DURATION == 150  # 5s at 30fps

    def test_overheat_duration(self) -> None:
        assert OVERHEAT_DURATION == 45  # 1.5s at 30fps


class TestColorZones:
    def test_zone_count(self) -> None:
        g = _make_game()
        assert len(g.color_zones) == 4

    def test_color_zone_at_angle_detection(self) -> None:
        g = _make_game()
        # Zone 0: RED at 5°-85°
        assert g._color_zone_at_angle(45) == RED
        # Zone 1: GREEN at 95°-175°
        assert g._color_zone_at_angle(135) == GREEN
        # Zone 2: DARK_BLUE at 185°-265°
        assert g._color_zone_at_angle(225) == DARK_BLUE
        # Zone 3: YELLOW at 275°-355°
        assert g._color_zone_at_angle(315) == YELLOW

    def test_color_zone_at_boundary(self) -> None:
        g = _make_game()
        # Exact start of zones
        assert g._color_zone_at_angle(ZONE_OFFSET) == RED  # 5°
        assert g._color_zone_at_angle(ZONE_OFFSET + 90) == GREEN  # 95°
        assert g._color_zone_at_angle(ZONE_OFFSET + 180) == DARK_BLUE  # 185°
        assert g._color_zone_at_angle(ZONE_OFFSET + 270) == YELLOW  # 275°

    def test_color_zone_at_gap(self) -> None:
        g = _make_game()
        # Gap between zones (85°-95°)
        assert g._color_zone_at_angle(90) is None


class TestAngleAndDistance:
    def test_angle_right(self) -> None:
        g = _make_game()
        # Point to the right (0°)
        angle = g._angle_from_center(RING_CX + 50, RING_CY)
        assert 0 <= angle < 1 or 359 < angle <= 360

    def test_angle_up(self) -> None:
        g = _make_game()
        # Point upward (90° in screen coords, -y)
        angle = g._angle_from_center(RING_CX, RING_CY - 50)
        assert 85 < angle < 95  # ~90°

    def test_angle_left(self) -> None:
        g = _make_game()
        angle = g._angle_from_center(RING_CX - 50, RING_CY)
        assert 175 < angle < 185  # ~180°

    def test_angle_down(self) -> None:
        g = _make_game()
        angle = g._angle_from_center(RING_CX, RING_CY + 50)
        assert 265 < angle < 275  # ~270°

    def test_dist_from_center(self) -> None:
        g = _make_game()
        assert g._dist_from_center(RING_CX, RING_CY) == 0.0
        assert g._dist_from_center(RING_CX + 30, RING_CY) == 30.0
        assert g._dist_from_center(RING_CX + 40, RING_CY + 30) == 50.0

    def test_is_at_edge(self) -> None:
        g = _make_game()
        # Exactly at edge: dist + radius = RING_RADIUS
        pos = RING_RADIUS - PLAYER_RADIUS
        assert g._is_at_edge(RING_CX + pos, RING_CY, PLAYER_RADIUS)

    def test_is_at_edge_not(self) -> None:
        g = _make_game()
        # Well inside ring
        assert not g._is_at_edge(RING_CX, RING_CY, PLAYER_RADIUS)

    def test_is_outside(self) -> None:
        g = _make_game()
        # Player center at RING_RADIUS + margin + 1
        pos = RING_RADIUS + 11 - PLAYER_RADIUS
        assert g._is_outside(RING_CX + pos, RING_CY, PLAYER_RADIUS)

    def test_is_outside_not(self) -> None:
        g = _make_game()
        # At edge but not past the 10px margin
        pos = RING_RADIUS + 5 - PLAYER_RADIUS
        assert not g._is_outside(RING_CX + pos, RING_CY, PLAYER_RADIUS)


class TestClampToRing:
    def test_clamp_inside(self) -> None:
        g = _make_game()
        w = Wrestler(x=RING_CX, y=RING_CY, radius=10)
        g._clamp_to_ring(w)
        # Should remain at center
        assert w.x == RING_CX
        assert w.y == RING_CY

    def test_clamp_beyond(self) -> None:
        g = _make_game()
        w = Wrestler(x=RING_CX + 200, y=RING_CY, radius=10)
        g._clamp_to_ring(w)
        # Should be clamped to RING_RADIUS - radius from center
        dist = g._dist_from_center(w.x, w.y)
        assert abs(dist - (RING_RADIUS - w.radius)) < 0.5

    def test_clamp_direction_preserved(self) -> None:
        g = _make_game()
        # Push beyond ring to the right and slightly down
        w = Wrestler(x=RING_CX + 200, y=RING_CY + 50, radius=10)
        g._clamp_to_ring(w)
        # Direction should be approximately preserved
        angle = g._angle_from_center(w.x, w.y)
        # atan2(-50, 200) normalized to [0,360) ≈ 345.96° (bottom-right quadrant)
        assert 335 < angle < 360


class TestMoveWrestler:
    def test_move_player_right(self) -> None:
        g = _make_game()
        orig_x = g.player.x
        g._move_wrestler(g.player, 1, 0)
        assert g.player.x > orig_x
        assert g.player.y == RING_CY - 60

    def test_move_player_diagonal(self) -> None:
        g = _make_game()
        g._move_wrestler(g.player, 1, 1)
        assert g.player.x > RING_CX
        assert g.player.y > RING_CY - 60

    def test_move_zero(self) -> None:
        g = _make_game()
        orig_x = g.player.x
        orig_y = g.player.y
        g._move_wrestler(g.player, 0, 0)
        assert g.player.x == orig_x
        assert g.player.y == orig_y

    def test_clamped_at_ring(self) -> None:
        g = _make_game()
        # Move player far to the right
        g.player.x = RING_CX + RING_RADIUS - PLAYER_RADIUS  # at edge
        g.player.y = RING_CY
        g._move_wrestler(g.player, 1, 0)
        # Should be clamped, not moved further
        dist = g._dist_from_center(g.player.x, g.player.y)
        assert dist <= RING_RADIUS - PLAYER_RADIUS + 0.1

    def test_opponent_speed_round_1(self) -> None:
        g = _make_game()
        assert g._opponent_speed() == OPPONENT_SPEED_BASE

    def test_opponent_speed_round_3(self) -> None:
        g = _make_game()
        g.round_num = 3
        expected = OPPONENT_SPEED_BASE + 2 * OPPONENT_SPEED_PER_ROUND
        assert abs(g._opponent_speed() - expected) < 0.01


class TestPushOpponent:
    def test_push_when_colliding(self) -> None:
        g = _make_game()
        # Place player right next to opponent
        g.player.x = RING_CX
        g.player.y = RING_CY + 60 - PLAYER_RADIUS - OPPONENT_RADIUS + 1
        g.opponent.x = RING_CX
        g.opponent.y = RING_CY + 60
        orig_opp_y = g.opponent.y
        g._push_opponent(0, 1)  # push down
        assert g.opponent.y > orig_opp_y  # moved down

    def test_no_push_when_not_colliding(self) -> None:
        g = _make_game()
        # Player far from opponent
        g.player.x = RING_CX - 80
        g.player.y = RING_CY
        g.opponent.x = RING_CX + 80
        g.opponent.y = RING_CY
        orig_opp_x = g.opponent.x
        orig_opp_y = g.opponent.y
        g._push_opponent(1, 0)
        assert g.opponent.x == orig_opp_x
        assert g.opponent.y == orig_opp_y

    def test_push_during_overheat_blocked(self) -> None:
        g = _make_game()
        g.overheat_timer = 30
        g.player.x = RING_CX
        g.player.y = RING_CY + 60 - PLAYER_RADIUS - OPPONENT_RADIUS + 1
        g.opponent.x = RING_CX
        g.opponent.y = RING_CY + 60
        orig_opp_y = g.opponent.y
        g._push_opponent(0, 1)
        # Should NOT move opponent during overheat
        assert g.opponent.y == orig_opp_y

    def test_super_push_force_multiplier(self) -> None:
        g = _make_game()
        g.super_push_timer = 100  # activate super
        g.player.x = RING_CX
        g.player.y = RING_CY + 60 - PLAYER_RADIUS - OPPONENT_RADIUS + 1
        g.opponent.x = RING_CX
        g.opponent.y = RING_CY + 60
        orig_opp_y = g.opponent.y
        g._push_opponent(0, 1)
        # Super mode: force = PUSH_FORCE * SUPER_FORCE_MULT (3x)
        expected_delta = PUSH_FORCE * SUPER_FORCE_MULT
        actual_delta = g.opponent.y - orig_opp_y
        assert abs(actual_delta - expected_delta) < 0.1

    def test_normal_push_force(self) -> None:
        g = _make_game()
        g.player.x = RING_CX
        g.player.y = RING_CY + 60 - PLAYER_RADIUS - OPPONENT_RADIUS + 1
        g.opponent.x = RING_CX
        g.opponent.y = RING_CY + 60
        orig_opp_y = g.opponent.y
        g._push_opponent(0, 1)
        actual_delta = g.opponent.y - orig_opp_y
        assert abs(actual_delta - PUSH_FORCE) < 0.1


class TestComboAndStrike:
    def test_combo_increment_same_color(self) -> None:
        g = _make_game()
        g.prev_zone_color = RED
        g._handle_opponent_strike(RED)
        assert g.combo == 1
        assert g.max_combo == 1

    def test_combo_builds_to_super(self) -> None:
        g = _make_game()
        g.prev_zone_color = RED
        # 4 same-color strikes → super
        for _ in range(4):
            g._handle_opponent_strike(RED)
        assert g.combo == 4
        assert g.max_combo == 4
        assert g.super_push_timer == SUPER_DURATION

    def test_combo_reset_different_color(self) -> None:
        g = _make_game()
        g.prev_zone_color = RED
        g._handle_opponent_strike(RED)  # combo=1
        assert g.combo == 1
        g._handle_opponent_strike(GREEN)  # different → reset
        assert g.combo == 0

    def test_prev_zone_updates(self) -> None:
        g = _make_game()
        g._handle_opponent_strike(RED)
        assert g.prev_zone_color == RED
        g._handle_opponent_strike(GREEN)
        assert g.prev_zone_color == GREEN

    def test_first_strike_with_none_prev(self) -> None:
        g = _make_game()
        assert g.prev_zone_color is None
        g._handle_opponent_strike(RED)
        # First strike: prev is None, so "match" check doesn't run
        # combo stays 0, prev becomes RED
        assert g.combo == 0
        assert g.prev_zone_color == RED

    def test_heat_increases_on_mismatch(self) -> None:
        g = _make_game()
        g.prev_zone_color = RED
        g._handle_opponent_strike(GREEN)
        # Mismatch: heat += HEAT_PER_MISMATCH (8)
        # Also heat += HEAT_PER_PUSH (2) always
        # Total: 10
        assert abs(g.heat - (HEAT_PER_MISMATCH + HEAT_PER_PUSH)) < 0.01

    def test_heat_increases_on_match(self) -> None:
        g = _make_game()
        g.prev_zone_color = RED
        g._handle_opponent_strike(RED)
        # Match: no mismatch heat, just push heat
        assert abs(g.heat - HEAT_PER_PUSH) < 0.01

    def test_heat_caps_at_max(self) -> None:
        g = _make_game()
        g.heat = 99.0
        g.prev_zone_color = RED
        g._handle_opponent_strike(GREEN)  # adds 10 heat
        assert g.heat == MAX_HEAT

    def test_overheat_triggers_at_max_heat(self) -> None:
        g = _make_game()
        g.heat = 98.0
        g.prev_zone_color = RED
        g._handle_opponent_strike(RED)  # adds HEAT_PER_PUSH=2 → 100.0
        assert g.heat >= MAX_HEAT
        assert g.overheat_timer == OVERHEAT_DURATION


class TestOverheat:
    def test_overheat_decrements(self) -> None:
        g = _make_game()
        g.overheat_timer = 10
        g._update_overheat()
        assert g.overheat_timer == 9

    def test_overheat_completes_resets_heat(self) -> None:
        g = _make_game()
        g.overheat_timer = 1
        g.heat = 50.0
        g._update_overheat()
        assert g.overheat_timer == 0
        assert g.heat == 0.0

    def test_heat_decays_when_not_pushing(self) -> None:
        g = _make_game()
        g.heat = 10.0
        g.player_pushing = False
        g._update_overheat()
        assert g.heat < 10.0
        assert g.heat > 0

    def test_heat_does_not_decay_when_pushing(self) -> None:
        g = _make_game()
        g.heat = 10.0
        g.player_pushing = True
        g._update_overheat()
        assert g.heat == 10.0

    def test_heat_not_below_zero(self) -> None:
        g = _make_game()
        g.heat = 0.01
        g.player_pushing = False
        g._update_overheat()
        assert g.heat >= 0.0


class TestSuperPush:
    def test_super_timer_decrements(self) -> None:
        g = _make_game()
        g.super_push_timer = 100
        g._update_super_push()
        assert g.super_push_timer == 99

    def test_super_timer_stops_at_zero(self) -> None:
        g = _make_game()
        g.super_push_timer = 1
        g._update_super_push()
        assert g.super_push_timer == 0
        g._update_super_push()
        assert g.super_push_timer == 0

    def test_is_super_active(self) -> None:
        g = _make_game()
        g.super_push_timer = 50
        assert g._is_super()
        g.super_push_timer = 0
        assert not g._is_super()


class TestRingOut:
    def test_ring_out_opponent_score(self) -> None:
        g = _make_game()
        g.combo = 5
        g.max_combo = 5
        g.phase = Phase.PLAYING
        # Place opponent outside
        g.opponent.x = RING_CX + RING_RADIUS + 20
        g.opponent.y = RING_CY
        assert g._is_outside(g.opponent.x, g.opponent.y, g.opponent.radius)
        g._ring_out_opponent()
        expected_score = RING_OUT_SCORE + 5 * COMBO_BONUS_MULT
        assert g.score == expected_score
        assert g.phase == Phase.RING_OUT

    def test_ring_out_opponent_resets_state(self) -> None:
        g = _make_game()
        g.combo = 3
        g.heat = 80.0
        g.super_push_timer = 50
        g.overheat_timer = 30
        g.opponent.x = RING_CX + RING_RADIUS + 20
        g.opponent.y = RING_CY
        g._ring_out_opponent()
        assert g.combo == 0
        assert g.prev_zone_color is None
        assert g.heat == 0.0
        assert g.super_push_timer == 0
        assert g.overheat_timer == 0

    def test_ring_out_opponent_increments_round(self) -> None:
        g = _make_game()
        g.opponent.x = RING_CX + RING_RADIUS + 20
        g.opponent.y = RING_CY
        g._ring_out_opponent()
        assert g.round_num == 2

    def test_ring_out_opponent_sets_timers(self) -> None:
        g = _make_game()
        g.opponent.x = RING_CX + RING_RADIUS + 20
        g.opponent.y = RING_CY
        g._ring_out_opponent()
        assert g.ring_out_timer == RING_OUT_TIMER
        assert g.shake_frames == SHAKE_FRAMES

    def test_ring_out_player(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g._ring_out_player()
        assert g.phase == Phase.GAME_OVER
        assert g.shake_frames == SHAKE_FRAMES

    def test_advance_round_transition(self) -> None:
        g = _make_game()
        g.ring_out_timer = 10
        g.phase = Phase.RING_OUT
        # Timer needs to reach 0
        for _ in range(10):
            g._advance_round()
        assert g.ring_out_timer <= 0
        assert g.phase == Phase.PLAYING


class TestOpponentAI:
    def test_ai_moves_toward_player(self) -> None:
        g = _make_game()
        g.player.x = RING_CX
        g.player.y = RING_CY - 60
        g.opponent.x = RING_CX
        g.opponent.y = RING_CY + 60
        orig_dist = math.hypot(g.player.x - g.opponent.x, g.player.y - g.opponent.y)
        g._update_opponent_ai()
        new_dist = math.hypot(g.player.x - g.opponent.x, g.player.y - g.opponent.y)
        assert new_dist < orig_dist

    def test_ai_pushes_player(self) -> None:
        g = _make_game()
        # Place them touching
        g.player.x = RING_CX
        g.player.y = RING_CY - 60
        g.opponent.x = RING_CX
        g.opponent.y = RING_CY - 60 + PLAYER_RADIUS + OPPONENT_RADIUS - 1
        orig_py = g.player.y
        g._update_opponent_ai()
        # Player should have been pushed away
        assert abs(g.player.y - orig_py) > 0

    def test_ai_clamped_to_ring(self) -> None:
        g = _make_game()
        # Place opponent at edge of ring
        g.opponent.x = RING_CX + RING_RADIUS - OPPONENT_RADIUS
        g.opponent.y = RING_CY
        g.player.x = RING_CX + RING_RADIUS + 50  # far away (forces AI toward edge)
        g.player.y = RING_CY
        g._update_opponent_ai()
        dist = g._dist_from_center(g.opponent.x, g.opponent.y)
        assert dist <= RING_RADIUS - OPPONENT_RADIUS + 0.1


class TestParticles:
    def test_spawn_particles(self) -> None:
        g = _make_game()
        assert len(g.particles) == 0
        g._spawn_particles(100, 100, RED, 10)
        assert len(g.particles) == 10
        for p in g.particles:
            assert isinstance(p, Particle)
            assert p.color == RED
            assert 20 <= p.life <= 40

    def test_update_particles_reduces_life(self) -> None:
        g = _make_game()
        g._spawn_particles(100, 100, RED, 1)
        assert g.particles[0].life > 0
        initial_life = g.particles[0].life
        g._update_particles()
        assert g.particles[0].life == initial_life - 1

    def test_update_particles_gravity(self) -> None:
        g = _make_game()
        g._spawn_particles(100, 100, RED, 1)
        orig_vy = g.particles[0].vy
        g._update_particles()
        assert g.particles[0].vy > orig_vy  # gravity added (0.05 per frame)

    def test_particles_removed_when_life_zero(self) -> None:
        g = _make_game()
        # Seed RNG produces specific life value; just set it directly
        g.particles = [Particle(x=100, y=100, vx=0.5, vy=-1.0, life=1, max_life=1, color=RED)]
        g._update_particles()
        assert len(g.particles) == 0  # life was 1, decremented to 0, removed


class TestReset:
    def test_reset_initial_state(self) -> None:
        g = _make_game()
        # Already reset via factory, but test explicitly
        g.score = 500
        g.combo = 8
        g.heat = 90.0
        g.round_num = 5
        g.super_push_timer = 30
        g.reset()
        g.phase = Phase.PLAYING  # reset() sets to TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.round_num == 1
        assert g.super_push_timer == 0
        assert g.prev_zone_color is None

    def test_reset_places_wrestlers(self) -> None:
        g = _make_game()
        # Force wrestlers far apart
        g.player.x = 10000
        g.player.y = 10000
        g.opponent.x = -10000
        g.opponent.y = -10000
        g.reset()
        assert g.player.x == RING_CX
        assert g.player.y == RING_CY - 60
        assert g.opponent.x == RING_CX
        assert g.opponent.y == RING_CY + 60

    def test_reset_clears_particles(self) -> None:
        g = _make_game()
        g._spawn_particles(100, 100, RED, 5)
        assert len(g.particles) == 5
        g.reset()
        g.phase = Phase.PLAYING
        assert len(g.particles) == 0


class TestCheckStrike:
    def test_check_strike_opponent_at_edge_match(self) -> None:
        g = _make_game()
        g.prev_zone_color = RED
        # Place opponent at ring edge in RED zone (angle ~45 in top-right)
        # Add tiny epsilon to guarantee edge detection despite floating-point
        angle_rad = math.radians(45)
        edge_dist = RING_RADIUS - g.opponent.radius + 0.01
        edge_x = RING_CX + math.cos(angle_rad) * edge_dist
        edge_y = RING_CY - math.sin(angle_rad) * edge_dist
        g.opponent.x = edge_x
        g.opponent.y = edge_y
        assert g._is_at_edge(g.opponent.x, g.opponent.y, g.opponent.radius)
        g.phase = Phase.PLAYING
        g._check_strike()
        assert g.combo == 1

    def test_check_strike_player_at_edge(self) -> None:
        g = _make_game()
        # Place player at ring edge in RED zone
        angle_rad = math.radians(45)
        edge_x = RING_CX + math.cos(angle_rad) * (RING_RADIUS - g.player.radius)
        edge_y = RING_CY - math.sin(angle_rad) * (RING_RADIUS - g.player.radius)
        g.player.x = edge_x
        g.player.y = edge_y
        assert g._is_at_edge(g.player.x, g.player.y, g.player.radius)
        g.phase = Phase.PLAYING
        g._check_strike()
        assert g.phase == Phase.GAME_OVER


class TestPhaseMachine:
    def test_title_phase(self) -> None:
        g = _make_game()
        g.phase = Phase.TITLE
        assert g.phase == Phase.TITLE

    def test_playing_phase(self) -> None:
        g = _make_game()
        assert g.phase == Phase.PLAYING

    def test_game_over_phase(self) -> None:
        g = _make_game()
        g.phase = Phase.GAME_OVER
        assert g.phase == Phase.GAME_OVER

    def test_ring_out_phase(self) -> None:
        g = _make_game()
        g.phase = Phase.RING_OUT
        assert g.phase == Phase.RING_OUT


class TestDifficultyScaling:
    def test_opponent_speed_increases(self) -> None:
        g = _make_game()
        spd_r1 = g._opponent_speed()
        g.round_num = 5
        spd_r5 = g._opponent_speed()
        assert spd_r5 > spd_r1

    def test_opponent_size_constant(self) -> None:
        g = _make_game()
        assert g.opponent.radius == OPPONENT_RADIUS
        g.round_num = 10
        assert g.opponent.radius == OPPONENT_RADIUS


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
