from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (
    FloatingText,
    Game,
    Particle,
    Phase,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.particles = []
    g.floating_texts = []
    g.reset()
    return g


def test_reset_state() -> None:
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.max_combo = 7
    g.heat = 80.0
    g.balls_remaining = 10
    g.super_mode = True
    g.last_color = Game.RED
    g.score_flash = 10
    g.shake_frames = 8
    g.balls_thrown = 15
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.balls_remaining == Game.MAX_BALLS
    assert g.super_mode is False
    assert g.last_color is None
    assert g.ball_active is False
    assert g.charging is False
    assert g.power == 0.0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.score_flash == 0
    assert g.shake_frames == 0
    assert g.balls_thrown == 0


def test_charge_power_clamps_at_one() -> None:
    g = _make_game()
    g.power = 0.99
    g._charge_power()
    assert g.power == 1.0
    g._charge_power()
    assert g.power == 1.0


def test_charge_power_increases() -> None:
    g = _make_game()
    g.power = 0.0
    g._charge_power()
    assert g.power == Game.POWER_CHARGE_RATE


def test_launch_ball_sets_velocity() -> None:
    g = _make_game()
    g.power = 0.75
    g.aim_x = 180.0
    g.charging = True
    g._launch_ball()
    assert g.ball_vx == (180.0 - Game.BALL_START_X) * 0.15
    assert g.ball_vy == -0.75 * 12.0
    assert g.power == 0.0
    assert g.charging is False


def test_launch_ball_aim_center_no_horizontal() -> None:
    g = _make_game()
    g.power = 0.5
    g.aim_x = Game.BALL_START_X
    g.charging = True
    g._launch_ball()
    assert g.ball_vx == 0.0


def test_spawn_ball_normal() -> None:
    g = _make_game()
    g.super_mode = False
    g._spawn_ball()
    assert g.ball_active is True
    assert g.ball_x == Game.BALL_START_X
    assert g.ball_y == Game.BALL_START_Y
    assert g.ball_color == Game.WHITE
    assert g.ball_super is False


def test_spawn_ball_super_mode_consumes_super() -> None:
    g = _make_game()
    g.super_mode = True
    g._spawn_ball()
    assert g.ball_active is True
    assert g.ball_color == Game.PINK
    assert g.ball_super is True
    assert g.super_mode is False


def test_update_ball_movement() -> None:
    g = _make_game()
    g.ball_active = True
    g.ball_x = 160.0
    g.ball_y = 210.0
    g.ball_vx = 2.0
    g.ball_vy = -8.0
    g._update_ball()
    assert g.ball_x == 162.0
    assert g.ball_y == 202.0
    assert g.ball_vy > -8.0


def test_update_ball_gravity() -> None:
    g = _make_game()
    g.ball_active = True
    g.ball_vx = 0.0
    g.ball_vy = 0.0
    g._update_ball()
    assert g.ball_vy == Game.GRAVITY


def test_update_ball_left_wall_bounce() -> None:
    g = _make_game()
    g.ball_active = True
    g.ball_x = float(Game.RAMP_LEFT + Game.BALL_RADIUS - 1)
    g.ball_y = 150.0
    g.ball_vx = -3.0
    g.ball_vy = 0.0
    g._update_ball()
    assert g.ball_x == float(Game.RAMP_LEFT + Game.BALL_RADIUS)
    assert g.ball_vx == 3.0 * 0.6


def test_update_ball_right_wall_bounce() -> None:
    g = _make_game()
    g.ball_active = True
    g.ball_x = float(Game.RAMP_RIGHT - Game.BALL_RADIUS + 1)
    g.ball_y = 150.0
    g.ball_vx = 3.0
    g.ball_vy = 0.0
    g._update_ball()
    assert g.ball_x == float(Game.RAMP_RIGHT - Game.BALL_RADIUS)
    assert g.ball_vx == -3.0 * 0.6


def test_update_ball_inactive_no_op() -> None:
    g = _make_game()
    g.ball_active = False
    g.ball_x = 160.0
    g._update_ball()
    assert g.ball_x == 160.0


def test_check_ring_hit_inactive() -> None:
    g = _make_game()
    g.ball_active = False
    assert g._check_ring_hit() is None


def test_check_ring_hit_center_inner_ring() -> None:
    g = _make_game()
    g.ball_active = True
    g.ball_x = 160.0
    g.ball_y = 60.0
    hit = g._check_ring_hit()
    assert hit == 4


def test_check_ring_hit_between_rings() -> None:
    g = _make_game()
    g.ball_active = True
    g.ball_x = 160.0
    g.ball_y = 60.0 + 33.0
    hit = g._check_ring_hit()
    assert hit == 0


def test_check_ring_hit_outside_all() -> None:
    g = _make_game()
    g.ball_active = True
    g.ball_x = 160.0
    g.ball_y = 112.0
    hit = g._check_ring_hit()
    assert hit is None


def test_check_ring_hit_off_center() -> None:
    g = _make_game()
    g.ball_active = True
    g.ball_x = 150.0
    g.ball_y = 62.0
    hit = g._check_ring_hit()
    assert hit is not None


def test_score_ring_first_throw_combo_one() -> None:
    g = _make_game()
    g.combo = 0
    g.last_color = None
    g.ball_super = False
    g.ring_colors = [Game.RED, Game.GREEN, Game.YELLOW, Game.LIGHT_BLUE, Game.RED]
    ring_idx = 0
    points = g._score_ring(ring_idx)
    assert g.combo == 1
    assert g.last_color == Game.RED
    assert points == Game.RING_SCORES[ring_idx]


def test_score_ring_same_color_combo() -> None:
    g = _make_game()
    g.combo = 1
    g.last_color = Game.RED
    g.ball_super = False
    g.ring_colors = [Game.RED, Game.GREEN, Game.YELLOW, Game.LIGHT_BLUE, Game.RED]
    g.score = 0
    points = g._score_ring(0)
    assert g.combo == 2
    assert g.last_color == Game.RED
    assert points == Game.RING_SCORES[0]
    assert g.score == points


def test_score_ring_combo_multiplier_applies() -> None:
    g = _make_game()
    g.combo = 2
    g.last_color = Game.RED
    g.ball_super = False
    g.ring_colors = [Game.RED, Game.GREEN, Game.YELLOW, Game.LIGHT_BLUE, Game.RED]
    g.score = 0
    points = g._score_ring(0)
    assert g.combo == 3
    assert points == int(Game.RING_SCORES[0] * 1.5)


def test_score_ring_different_color_resets_combo() -> None:
    g = _make_game()
    g.combo = 3
    g.last_color = Game.RED
    g.ball_super = False
    g.ring_colors = [Game.RED, Game.GREEN, Game.YELLOW, Game.LIGHT_BLUE, Game.RED]
    g.score = 0
    points = g._score_ring(1)
    assert g.combo == 1
    assert g.last_color == Game.GREEN
    assert points == Game.RING_SCORES[1]


def test_score_ring_super_activates_at_combo_five() -> None:
    g = _make_game()
    g.combo = 4
    g.last_color = Game.RED
    g.ball_super = False
    g.ring_colors = [Game.RED, Game.GREEN, Game.YELLOW, Game.LIGHT_BLUE, Game.RED]
    g.super_mode = False
    g._score_ring(0)
    assert g.combo == 5
    assert g.super_mode is True


def test_score_ring_super_ball_all_rings() -> None:
    g = _make_game()
    g.ball_super = True
    g.super_mode = True
    g.combo = 5
    g.score = 0
    g.last_color = Game.RED
    points = g._score_ring(0)
    expected = sum(
        s * Game.SUPER_MULTIPLIER for s in Game.RING_SCORES
    )
    assert g.score == expected
    assert points == expected
    assert g.combo == 0
    assert g.last_color is None
    assert g.super_mode is False


def test_score_ring_combo_four_to_five_activates_super() -> None:
    g = _make_game()
    g.combo = 4
    g.last_color = Game.RED
    g.ball_super = False
    g.ring_colors = [Game.RED, Game.GREEN, Game.YELLOW, Game.LIGHT_BLUE, Game.RED]
    g.super_mode = False
    g._score_ring(0)
    assert g.super_mode is True


def test_apply_combo_zero() -> None:
    g = _make_game()
    g.combo = 0
    assert g._apply_combo() == 1.0


def test_apply_combo_one() -> None:
    g = _make_game()
    g.combo = 1
    assert g._apply_combo() == 1.0


def test_apply_combo_three() -> None:
    g = _make_game()
    g.combo = 3
    assert g._apply_combo() == 2.0


def test_apply_combo_five() -> None:
    g = _make_game()
    g.combo = 5
    assert g._apply_combo() == 3.0


def test_max_combo_tracking() -> None:
    g = _make_game()
    g.max_combo = 0
    g.combo = 3
    g.last_color = Game.RED
    g.ball_super = False
    g.ring_colors = [Game.RED, Game.GREEN, Game.YELLOW, Game.LIGHT_BLUE, Game.RED]
    g._score_ring(0)
    assert g.max_combo == 4
    g._score_ring(0)
    assert g.max_combo == 5


def test_update_heat_increase() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat(20.0)
    assert g.heat == 70.0


def test_update_heat_clamp_max() -> None:
    g = _make_game()
    g.heat = 95.0
    g._update_heat(10.0)
    assert g.heat == 100.0


def test_update_heat_clamp_min() -> None:
    g = _make_game()
    g.heat = 3.0
    g._update_heat(-10.0)
    assert g.heat == 0.0


def test_update_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat(-0.05)
    assert g.heat == 49.95


def test_rotate_ring_colors() -> None:
    g = _make_game()
    g.ring_colors = [Game.RED, Game.GREEN, Game.YELLOW, Game.LIGHT_BLUE, Game.RED]
    g._rotate_ring_colors()
    assert g.ring_colors == [
        Game.RED,
        Game.RED,
        Game.GREEN,
        Game.YELLOW,
        Game.LIGHT_BLUE,
    ]


def test_rotate_ring_colors_wraps() -> None:
    g = _make_game()
    g.ring_colors = [Game.RED, Game.GREEN, Game.YELLOW, Game.LIGHT_BLUE, Game.RED]
    for _ in range(5):
        g._rotate_ring_colors()
    assert g.ring_colors == [Game.RED, Game.GREEN, Game.YELLOW, Game.LIGHT_BLUE, Game.RED]


def test_rotate_ring_colors_empty() -> None:
    g = _make_game()
    g.ring_colors = []
    g._rotate_ring_colors()
    assert g.ring_colors == []


def test_spawn_particles_count() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, Game.RED, 12)
    assert len(g.particles) == 12
    for p in g.particles:
        assert p.color == Game.RED
        assert 10 <= p.life <= 30


def test_spawn_super_particles_count() -> None:
    g = _make_game()
    g._spawn_super_particles(160.0, 60.0)
    assert len(g.particles) == 30
    for p in g.particles:
        assert p.color in Game.RING_COLORS_POOL
        assert 15 <= p.life <= 40


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100.0, 100.0, "+100", Game.YELLOW)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "+100"
    assert ft.color == Game.YELLOW
    assert ft.life == 30


def test_update_particles_moves_and_decays() -> None:
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=1.0, vy=-1.0, life=20, color=Game.RED),
        Particle(x=10.0, y=10.0, vx=2.0, vy=-2.0, life=1, color=Game.GREEN),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].x == 1.0
    assert g.particles[0].y == -1.0
    assert g.particles[0].life == 19


def test_update_floating_texts_moves_and_decays() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=0.0, y=100.0, text="+100", life=30, color=Game.YELLOW),
        FloatingText(x=10.0, y=100.0, text="MISS", life=1, color=Game.RED),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].y == 99.0
    assert g.floating_texts[0].life == 29


def test_ring_color_rotation_schedule() -> None:
    g = _make_game()
    g.balls_thrown = 7
    original = list(g.ring_colors)
    g.balls_thrown = 8
    g._rotate_ring_colors()
    assert g.ring_colors != original


def test_score_accumulation() -> None:
    g = _make_game()
    g.ball_super = False
    g.ring_colors = [Game.RED, Game.GREEN, Game.YELLOW, Game.LIGHT_BLUE, Game.RED]
    g.score = 0
    g._score_ring(0)
    first_score = g.score
    g.last_color = Game.RED
    g.ball_super = False
    g._score_ring(3)
    g.last_color = Game.RED
    g._score_ring(4)
    assert g.score > first_score


def test_balls_remaining_after_throw() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g.balls_remaining = 30
    assert g.balls_remaining == 30


def test_power_gauge_color() -> None:
    g = _make_game()
    g.power = 0.0
    assert g.power < 0.5
    g.power = 0.6
    assert 0.5 <= g.power < 0.8
    g.power = 0.9
    assert g.power >= 0.8


def test_heat_does_not_change_phase_directly() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g.heat = 50
    g._update_heat(40)
    assert g.phase == Phase.AIMING


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
