"""test_imports.py — Headless logic tests for Tether Chain."""
import math
import sys
import os

# Add prototype dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import Game, Phase, Particle, FloatingText


def _make_game() -> Game:
    """Factory: create a Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    # Pre-init all mutable containers
    g.particles = []
    g.floating_texts = []
    g.reset()
    return g


# ── Phase enum ──

def test_phase_values():
    assert Phase.TITLE is not Phase.PLAYING
    assert Phase.PLAYING is not Phase.GAME_OVER


# ── Dataclasses ──

def test_particle_dataclass():
    p = Particle(10.0, 20.0, 1.5, -0.5, 15, 8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -0.5
    assert p.life == 15
    assert p.color == 8


def test_floating_text_dataclass():
    ft = FloatingText(100.0, 50.0, "+50", 30, 9, -1.0)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+50"
    assert ft.life == 30
    assert ft.color == 9
    assert ft.vy == -1.0


# ── Game class constants ──

def test_game_constants():
    assert Game.CENTER_X == 160
    assert Game.CENTER_Y == 120
    assert Game.ROPE_LENGTH == 90
    assert Game.BALL_RADIUS == 10
    assert Game.POLE_RADIUS == 6
    assert Game.COLOR_CYCLE_INTERVAL == 90
    assert Game.SUPER_DURATION == 300
    assert Game.GAME_DURATION == 3600
    assert Game.HEAT_MAX == 100.0
    assert Game.HEAT_WRONG == 15.0
    assert Game.HEAT_MISS == 5.0
    assert Game.HEAT_DECAY == 0.05
    assert Game.SPEED_INITIAL == 0.02
    assert Game.SPEED_ACCEL == 0.001
    assert Game.HIT_COOLDOWN_FRAMES == 10
    assert Game.BALL_COLORS == [8, 3, 5, 10]
    assert len(Game.RAINBOW_COLORS) == 6


# ── reset() ──

def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == Game.GAME_DURATION
    assert g.ball_angle == 0.0
    assert g.ball_speed == Game.SPEED_INITIAL
    assert g.ball_color == 0
    assert g.color_timer == Game.COLOR_CYCLE_INTERVAL
    assert g.super_timer == 0
    assert g.prev_color is None
    assert g.last_hit_in_half is False
    assert g.last_angle == 0.0
    assert g.hit_cooldown == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.shake_frames == 0
    assert g.frame == 0


def test_reset_clears_mutable_state():
    g = _make_game()
    g.particles.append(Particle(0, 0, 0, 0, 10, 8))
    g.floating_texts.append(FloatingText(0, 0, "test", 10, 7, -1.0))
    g.score = 500
    g.combo = 10
    g.reset()
    assert g.particles == []
    assert g.floating_texts == []
    assert g.score == 0
    assert g.combo == 0


# ── _is_ball_in_player_half ──

def test_ball_in_player_half_at_0():
    g = _make_game()
    g.ball_angle = 0.0
    assert g._is_ball_in_player_half() is True


def test_ball_in_player_half_at_pi():
    g = _make_game()
    g.ball_angle = math.pi
    assert g._is_ball_in_player_half() is True


def test_ball_in_player_half_at_mid():
    g = _make_game()
    g.ball_angle = math.pi / 2
    assert g._is_ball_in_player_half() is True


def test_ball_not_in_player_half_below_pi():
    g = _make_game()
    g.ball_angle = math.pi + 0.01
    assert g._is_ball_in_player_half() is False


def test_ball_not_in_player_half_at_2pi():
    g = _make_game()
    g.ball_angle = math.pi * 2 - 0.01
    assert g._is_ball_in_player_half() is False


# ── _update_ball ──

def test_update_ball_advances_angle():
    g = _make_game()
    g.ball_speed = 0.1
    old_angle = g.ball_angle
    g._update_ball()
    assert g.ball_angle > old_angle


def test_update_ball_wraps_angle():
    g = _make_game()
    g.ball_angle = math.pi * 2 - 0.01
    g.ball_speed = 0.1
    g._update_ball()
    assert g.ball_angle < math.pi  # Should wrap around


def test_update_ball_color_cycle():
    g = _make_game()
    g.color_timer = 1
    old_color = g.ball_color
    g._update_ball()
    assert g.ball_color == (old_color + 1) % len(Game.BALL_COLORS)
    assert g.color_timer == Game.COLOR_CYCLE_INTERVAL


def test_update_ball_color_timer_decrements():
    g = _make_game()
    old_timer = g.color_timer
    g._update_ball()
    assert g.color_timer == old_timer - 1


def test_update_ball_speed_increases():
    g = _make_game()
    old_speed = g.ball_speed
    g._update_ball()
    assert g.ball_speed > old_speed


def test_update_ball_super_timer_decrements():
    g = _make_game()
    g.super_timer = 100
    g._update_ball()
    assert g.super_timer == 99


def test_update_ball_super_timer_stops_at_zero():
    g = _make_game()
    g.super_timer = 1
    g._update_ball()
    assert g.super_timer == 0


# ── _player_hit ──

def test_player_hit_first_hit():
    g = _make_game()
    g.ball_angle = math.pi / 2  # In player half
    g.ball_color = 0  # RED = 8
    g.prev_color = None
    g._player_hit()
    assert g.prev_color == Game.BALL_COLORS[0]  # 8
    assert g.combo == 0  # First hit has no prev to match
    assert g.score == 0
    assert g.hit_cooldown == Game.HIT_COOLDOWN_FRAMES


def test_player_hit_same_color_combo():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.ball_color = 0
    g.prev_color = Game.BALL_COLORS[0]  # Same as current
    g._player_hit()
    assert g.combo == 1
    assert g.score > 0
    assert g.max_combo >= 1


def test_player_hit_combo_chain():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.ball_color = 0
    g.prev_color = Game.BALL_COLORS[0]
    g.combo = 2
    g.max_combo = 2
    g._player_hit()
    assert g.combo == 3
    assert g.max_combo == 3
    pts = int(10 * (1 + 3 * 0.5))
    assert g.score == pts


def test_player_hit_wrong_color():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.ball_color = 1  # GREEN = 3
    g.prev_color = Game.BALL_COLORS[0]  # RED = 8
    g.heat = 0.0
    g._player_hit()
    assert g.combo == 0
    assert g.heat == Game.HEAT_WRONG  # 15.0
    assert g.prev_color == Game.BALL_COLORS[1]  # updated


def test_player_hit_wrong_color_game_over():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.ball_color = 1
    g.prev_color = Game.BALL_COLORS[0]
    g.heat = Game.HEAT_MAX - 5.0  # Adding HEAT_WRONG (15) exceeds max
    g._player_hit()
    assert g.heat >= Game.HEAT_MAX
    assert g.phase == Phase.GAME_OVER


def test_player_hit_super_activation():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.ball_color = 0
    g.prev_color = Game.BALL_COLORS[0]
    g.combo = 3  # Next hit = combo 4 → SUPER
    g._player_hit()
    assert g.combo == 4
    assert g.super_timer == Game.SUPER_DURATION


def test_player_hit_super_maintained():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.super_timer = 150  # Already in super
    g.combo = 4
    g.prev_color = Game.BALL_COLORS[0]
    g.ball_color = 0
    old_score = g.score
    g._player_hit()
    assert g.super_timer == Game.SUPER_DURATION  # Refreshed
    assert g.combo == 5
    assert g.score > old_score


def test_player_hit_super_any_color():
    """In super mode, any color hit works — scores 3x."""
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.super_timer = 100
    g.combo = 5
    g.prev_color = Game.BALL_COLORS[0]  # RED
    g.ball_color = 2  # BLUE — wouldn't match but super overrides
    g._player_hit()
    # Super mode: scores 30 (10*3), combo increments
    assert g.score == 30  # 10 * 3 = 30
    assert g.combo == 6
    # prev_color is NOT updated in super path (method returns early before setting prev_color)
    # Let's check: actually in super path, there's an early return — prev_color NOT set
    # That's fine, the design spec says super mode any-color counts


def test_player_hit_particle_spawn_on_combo():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.ball_color = 0
    g.prev_color = Game.BALL_COLORS[0]
    g.combo = 1
    old_particles = len(g.particles)
    g._player_hit()
    assert len(g.particles) > old_particles


def test_player_hit_particle_spawn_on_wrong():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.ball_color = 1
    g.prev_color = Game.BALL_COLORS[0]
    old_particles = len(g.particles)
    g._player_hit()
    assert len(g.particles) > old_particles


def test_player_hit_floating_text_spawn_on_combo():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.ball_color = 0
    g.prev_color = Game.BALL_COLORS[0]
    g.combo = 1
    old_texts = len(g.floating_texts)
    g._player_hit()
    # Expect score text + combo text = 2 floating texts
    assert len(g.floating_texts) == old_texts + 2


# ── _update_heat ──

def test_update_heat_decays():
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat < 10.0


def test_update_heat_floors_at_zero():
    g = _make_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_no_decay_at_zero():
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


# ── _check_game_over ──

def test_check_game_over_heat():
    g = _make_game()
    g.heat = Game.HEAT_MAX
    assert g._check_game_over() is True


def test_check_game_over_timer():
    g = _make_game()
    g.timer = 0
    assert g._check_game_over() is True


def test_check_game_over_not():
    g = _make_game()
    g.heat = 0.0
    g.timer = 600
    assert g._check_game_over() is False


def test_check_game_over_heat_exceeds():
    g = _make_game()
    g.heat = Game.HEAT_MAX + 50.0
    assert g._check_game_over() is True


# ── Particle system ──

def test_spawn_particles_count():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 8, 10)
    assert len(g.particles) == 10


def test_spawn_particles_zero_count():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 8, 0)
    assert len(g.particles) == 0


def test_spawn_particles_bound_in_circle():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 8, 50)
    for p in g.particles:
        # Velocity magnitude should be <= 2.5
        speed = math.hypot(p.vx, p.vy)
        assert 0.5 <= speed <= 2.5
        # Position should be at spawn point
        assert p.x == 100.0
        assert p.y == 100.0


def test_update_particles_removes_dead():
    g = _make_game()
    g.particles = [
        Particle(0, 0, 1, 1, 1, 8),   # Will die after update
        Particle(10, 10, 1, 1, 5, 8),  # Will survive
        Particle(20, 20, 1, 1, 0, 8),  # Already dead
    ]
    g._update_particles()
    assert len(g.particles) == 1
    # Particle moved: x=10+1=11, y=10+1=11
    assert g.particles[0].x == 11.0
    assert g.particles[0].life == 4
    assert g.particles[0].y == 11.0  # Position updated


def test_update_particles_moves():
    g = _make_game()
    g.particles = [Particle(100.0, 100.0, 2.0, -1.0, 10, 8)]
    g._update_particles()
    assert abs(g.particles[0].x - 102.0) < 0.01
    assert abs(g.particles[0].y - 99.0) < 0.01
    assert g.particles[0].life == 9


# ── Floating text system ──

def test_spawn_floating_text():
    g = _make_game()
    g._spawn_floating_text(100.0, 50.0, "+50", 9)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+50"
    assert ft.life == 30
    assert ft.color == 9
    assert ft.vy == -1.0


def test_update_floating_texts_removes_dead():
    g = _make_game()
    g.floating_texts = [
        FloatingText(0, 0, "a", 1, 7, -1.0),   # Will die
        FloatingText(10, 10, "b", 5, 7, -1.0),  # Will survive
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "b"
    assert g.floating_texts[0].life == 4


def test_update_floating_texts_moves_up():
    g = _make_game()
    g.floating_texts = [FloatingText(100.0, 50.0, "test", 10, 7, -1.0)]
    g._update_floating_texts()
    assert abs(g.floating_texts[0].y - 49.0) < 0.01
    assert g.floating_texts[0].life == 9


# ── _get_ball_pos ──

def test_get_ball_pos_at_0():
    g = _make_game()
    g.ball_angle = 0.0
    x, y = g._get_ball_pos()
    assert abs(x - Game.CENTER_X) < 0.01
    assert abs(y - (Game.CENTER_Y + Game.ROPE_LENGTH)) < 0.01  # cos(0)=1, below center


def test_get_ball_pos_at_pi_half():
    g = _make_game()
    g.ball_angle = math.pi / 2  # 90 deg — ball to the right
    x, y = g._get_ball_pos()
    assert abs(x - (Game.CENTER_X + Game.ROPE_LENGTH)) < 0.01
    assert abs(y - Game.CENTER_Y) < 0.01


def test_get_ball_pos_at_pi():
    g = _make_game()
    g.ball_angle = math.pi  # 180 deg — ball above center
    x, y = g._get_ball_pos()
    assert abs(x - Game.CENTER_X) < 0.01
    assert abs(y - (Game.CENTER_Y - Game.ROPE_LENGTH)) < 0.01


def test_get_ball_pos_at_3pi_half():
    g = _make_game()
    g.ball_angle = math.pi * 3 / 2  # 270 deg — ball to the left
    x, y = g._get_ball_pos()
    assert abs(x - (Game.CENTER_X - Game.ROPE_LENGTH)) < 0.01
    assert abs(y - Game.CENTER_Y) < 0.01


# ── Edge cases ──

def test_heat_clamped_to_max():
    g = _make_game()
    g.heat = Game.HEAT_MAX
    g._player_hit()  # Should not add more, but _player_hit only modifies on wrong hit
    # Actually _player_hit only changes heat on wrong color
    g.ball_angle = math.pi / 2
    g.ball_color = 1
    g.prev_color = Game.BALL_COLORS[0]
    g.heat = 95.0
    g._player_hit()
    assert g.heat == Game.HEAT_MAX  # Clamped to 100, not 110


def test_score_formula_positive():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.ball_color = 0
    g.prev_color = Game.BALL_COLORS[0]
    # _player_hit increments combo first, then scores: combo 0→1, pts = 10*(1+1*0.5)=15
    g._player_hit()
    assert g.score == 15


def test_score_formula_with_combo():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.ball_color = 0
    g.prev_color = Game.BALL_COLORS[0]
    g.combo = 4
    g.max_combo = 4
    old_score = g.score
    g._player_hit()
    expected_pts = int(10 * (1 + 5 * 0.5))  # combo becomes 5
    assert g.score == old_score + expected_pts


def test_combo_reset_preserves_max_combo():
    g = _make_game()
    g.combo = 10
    g.max_combo = 10
    g.ball_angle = math.pi / 2
    g.ball_color = 1  # Different from prev
    g.prev_color = Game.BALL_COLORS[0]  # RED
    g._player_hit()
    assert g.combo == 0
    assert g.max_combo == 10  # Preserved


def test_hit_cooldown_set():
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.hit_cooldown = 0
    g._player_hit()
    assert g.hit_cooldown == Game.HIT_COOLDOWN_FRAMES


def test_super_does_not_update_prev_color():
    """In super mode, prev_color is NOT updated (early return before assignment)."""
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.super_timer = 100
    old_prev = g.prev_color
    g._player_hit()
    assert g.prev_color == old_prev  # Unchanged in super mode


def test_ball_angle_at_boundary_zero():
    """Ball at exactly 0 rad is in player half."""
    g = _make_game()
    g.ball_angle = 0.0
    assert g._is_ball_in_player_half() is True


def test_ball_angle_at_boundary_pi():
    """Ball at exactly pi rad is in player half."""
    g = _make_game()
    g.ball_angle = math.pi
    assert g._is_ball_in_player_half() is True


def test_ball_angle_just_above_pi():
    """Ball just past pi is NOT in player half."""
    g = _make_game()
    g.ball_angle = math.pi + 0.001
    assert g._is_ball_in_player_half() is False


# ── Integration-style tests ──

def test_full_combo_to_super():
    """Simulate 4 consecutive same-color hits to trigger SUPER."""
    g = _make_game()
    g.ball_angle = math.pi / 2

    # Set up deterministic colors: all RED
    g.ball_color = 0  # RED
    g.prev_color = Game.BALL_COLORS[0]  # RED

    # _player_hit increments combo FIRST, then scores.
    # Hit 1: combo 0→1, pts = 10*(1+1*0.5)=15, total=15
    g._player_hit()
    assert g.combo == 1
    assert g.score == 15

    # Hit 2: combo 1→2, pts = 10*(1+2*0.5)=20, total=35
    g._player_hit()
    assert g.combo == 2
    assert g.score == 35

    # Hit 3: combo 2→3, pts = 10*(1+3*0.5)=25, total=60
    g._player_hit()
    assert g.combo == 3
    assert g.score == 60

    # Hit 4: combo 3→4, SUPER activates, pts = 10*(1+4*0.5)=30, total=90
    g._player_hit()
    assert g.combo == 4
    assert g.super_timer == Game.SUPER_DURATION
    assert g.score == 90
    assert g.max_combo == 4


def test_heat_game_over_path():
    """Wrong hits accumulate heat to game over."""
    g = _make_game()
    g.ball_angle = math.pi / 2

    # Need 7 wrong hits: 7 * 15 = 105 > 100
    for i in range(7):
        g.ball_color = i % 4
        if g.prev_color is not None:
            # Make sure current differs from prev
            while g.ball_color == Game.BALL_COLORS.index(g.prev_color):
                g.ball_color = (g.ball_color + 1) % 4
        else:
            g.prev_color = 99  # Non-matching sentinel
            g.ball_color = 0

        g._player_hit()
        if g.phase == Phase.GAME_OVER:
            break

    assert g.phase == Phase.GAME_OVER


def test_timer_game_over():
    """Timer reaching 0 triggers game over."""
    g = _make_game()
    g.timer = 0
    assert g._check_game_over() is True


def test_super_refreshes_duration():
    """Hitting in super mode refreshes super timer."""
    g = _make_game()
    g.ball_angle = math.pi / 2
    g.super_timer = 50  # 50 frames remaining
    g.combo = 4
    g.prev_color = Game.BALL_COLORS[0]
    g.ball_color = 0

    g._player_hit()
    assert g.super_timer == Game.SUPER_DURATION  # Refreshed to full 300


if __name__ == "__main__":
    import pytest

    # Run all tests
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)
