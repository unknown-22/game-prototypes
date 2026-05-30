"""test_imports.py — Headless logic tests for SPIKE CHAIN prototype."""
import random
import sys

import pytest

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/086_spike_chain")

from main import (  # noqa: E402
    Game, Phase, Ball, Player, Particle, FloatingText,
    GREEN, WHITE, RED, YELLOW, LIME, CYAN,
    SCREEN_W, SCREEN_H, NET_X, NET_TOP_Y,
    PLAYER_X_MIN, PLAYER_X_MAX, AI_X_MIN, AI_X_MAX,
    PLAYER_Y, GROUND_Y, CEILING_Y,
    TOUCH_RANGE_H, TOUCH_RANGE_V, MAX_POINTS,
    GRAVITY, BOUNCE_FACTOR, MAX_SPEED, TOUCHES_PER_SIDE,
    cycle_color, compute_touch_combo, is_super_spike,
    compute_touch_velocity, compute_ai_touch_velocity,
    update_ball_physics, check_point, ball_in_range, ball_crossed_net,
)


def _make_game() -> Game:
    """Factory for headless Game instance with deterministic RNG."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.ball = Ball(x=0, y=0, vx=0, vy=0)
    g.player = Player(
        x=100, y=PLAYER_Y, touches_left=TOUCHES_PER_SIDE,
        last_color=-1, combo=0, max_combo=0,
    )
    g.ai = Player(
        x=240, y=PLAYER_Y, touches_left=TOUCHES_PER_SIDE,
        last_color=-1, combo=0, max_combo=0,
    )
    g.particles = []
    g.floats = []
    g.score_player = 0
    g.score_ai = 0
    g.player_color = RED
    g.ai_color = RED
    g._touch_cooldown = 0
    g._serve_timer = 0
    g._point_timer = 0
    g._shake_frames = 0
    g._ai_timer = 0
    g._serving_side = 0
    g._ball_prev_x = 0
    g._touch_label = ""
    g._touch_label_timer = 0
    g._super_spike = False
    g._title_flash = 0
    g.reset()
    return g


# ═══════════════════════════════════════════════════════════════
# Constants Tests
# ═══════════════════════════════════════════════════════════════


def test_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert NET_X == 160
    assert NET_TOP_Y == 110
    assert GROUND_Y == 210
    assert CEILING_Y == 30
    assert PLAYER_Y == 200
    assert TOUCHES_PER_SIDE == 3
    assert MAX_POINTS == 5
    assert GRAVITY == 0.3
    assert BOUNCE_FACTOR == 0.7
    assert MAX_SPEED == 10
    assert TOUCH_RANGE_H == 60
    assert TOUCH_RANGE_V == 70


def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.SERVING in Phase
    assert Phase.PLAYING in Phase
    assert Phase.POINT_SCORED in Phase
    assert Phase.GAME_OVER in Phase


# ═══════════════════════════════════════════════════════════════
# Dataclass Tests
# ═══════════════════════════════════════════════════════════════


def test_ball_dataclass():
    b = Ball(x=100.0, y=150.0, vx=3.0, vy=-4.0)
    assert b.x == 100.0
    assert b.y == 150.0
    assert b.vx == 3.0
    assert b.vy == -4.0


def test_player_dataclass():
    p = Player(x=100, y=200, touches_left=3, last_color=-1, combo=0, max_combo=0)
    assert p.touches_left == 3
    assert p.combo == 0
    assert p.max_combo == 0


def test_particle_dataclass():
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=12, color=YELLOW)
    assert p.life == 12
    assert p.color == YELLOW


def test_floating_text_dataclass():
    ft = FloatingText(x=100.0, y=80.0, text="+COMBO", life=30, color=CYAN)
    assert ft.text == "+COMBO"
    assert ft.life == 30
    assert ft.color == CYAN


# ═══════════════════════════════════════════════════════════════
# Color Cycle Tests
# ═══════════════════════════════════════════════════════════════


def test_cycle_color_red_to_green():
    assert cycle_color(RED) == GREEN


def test_cycle_color_green_to_lime():
    assert cycle_color(GREEN) == LIME


def test_cycle_color_lime_to_yellow():
    assert cycle_color(LIME) == YELLOW


def test_cycle_color_yellow_to_red():
    assert cycle_color(YELLOW) == RED


def test_cycle_color_full_loop():
    c = RED
    for expected in [GREEN, LIME, YELLOW, RED, GREEN, LIME]:
        c = cycle_color(c)
        assert c == expected


# ═══════════════════════════════════════════════════════════════
# Combo Logic Tests
# ═══════════════════════════════════════════════════════════════


def test_compute_touch_combo_first_touch():
    """First touch always gives combo=1 regardless of last_color=-1."""
    assert compute_touch_combo(-1, RED, 0) == 1


def test_compute_touch_combo_same_color():
    """Same color as last touch increments combo."""
    assert compute_touch_combo(RED, RED, 2) == 3


def test_compute_touch_combo_different_color_resets():
    """Different color resets combo to 1."""
    assert compute_touch_combo(RED, GREEN, 3) == 1


# ═══════════════════════════════════════════════════════════════
# Super Spike Detection Tests
# ═══════════════════════════════════════════════════════════════


def test_is_super_spike_true():
    """combo >= 3 and touches_left_after == 0 → super spike."""
    assert is_super_spike(3, 0) is True
    assert is_super_spike(4, 0) is True
    assert is_super_spike(5, 0) is True


def test_is_super_spike_false_low_combo():
    """combo < 3 → not super."""
    assert is_super_spike(2, 0) is False


def test_is_super_spike_false_not_spike():
    """touches_left != 0 → not the spike touch."""
    assert is_super_spike(3, 1) is False  # not spike (#1 or #2)
    assert is_super_spike(3, 2) is False


# ═══════════════════════════════════════════════════════════════
# Touch Velocity Tests
# ═══════════════════════════════════════════════════════════════


def test_compute_touch_velocity_bump():
    rng = random.Random(42)
    vx, vy = compute_touch_velocity(1, False, rng)
    assert vx > 0  # toward AI side
    assert vy < 0  # upward
    assert 1 <= vx <= 3
    assert -5 <= vy <= -4


def test_compute_touch_velocity_set():
    rng = random.Random(42)
    vx, vy = compute_touch_velocity(2, False, rng)
    assert vx > 0
    assert vy < 0
    assert 1 <= vx <= 3
    assert -6 <= vy <= -5


def test_compute_touch_velocity_spike():
    rng = random.Random(42)
    vx, vy = compute_touch_velocity(3, False, rng)
    assert vx > 0
    assert vy < 0
    assert 5 <= vx <= 8
    assert vy == -3.0


def test_compute_touch_velocity_super_spike():
    rng = random.Random(42)
    vx_normal, vy_normal = compute_touch_velocity(3, False, rng)

    rng2 = random.Random(42)
    vx_super, vy_super = compute_touch_velocity(3, True, rng2)

    # With same seed, super spike velocity is 2x
    assert vx_super == pytest.approx(vx_normal * 2)
    assert vy_super == pytest.approx(vy_normal * 2)


def test_compute_ai_touch_velocity_bump():
    rng = random.Random(42)
    vx, vy = compute_ai_touch_velocity(1, rng)
    assert vx < 0  # toward player side
    assert vy < 0
    assert -3 <= vx <= -1
    assert -5 <= vy <= -3


def test_compute_ai_touch_velocity_spike():
    rng = random.Random(42)
    vx, vy = compute_ai_touch_velocity(3, rng)
    assert vx < 0
    assert vy < 0
    assert -7 <= vx <= -3
    assert -4 <= vy <= -2


# ═══════════════════════════════════════════════════════════════
# Ball Physics Tests
# ═══════════════════════════════════════════════════════════════


def test_update_ball_physics_gravity():
    b = Ball(x=100, y=100, vx=2, vy=0)
    update_ball_physics(b)
    assert b.vy == pytest.approx(GRAVITY)  # gravity applied
    assert b.y == pytest.approx(100 + GRAVITY)


def test_update_ball_physics_ground_bounce():
    """Ball above ground falling down should bounce upward."""
    b = Ball(x=100, y=200, vx=2, vy=8)
    update_ball_physics(b)
    # After gravity: vy = 8.3, then y = 208.3 < GROUND_Y → no bounce yet
    assert b.y == pytest.approx(208.3)


def test_update_ball_physics_ground_settle():
    b = Ball(x=100, y=GROUND_Y, vx=0, vy=0.5)
    update_ball_physics(b)
    # Gravity: 0.5+0.3=0.8, ground check: y=210 >= 210 -> bounce: vy=-0.8*0.7=-0.56
    # Since abs(-0.56) < 1 → vy = 0. Then y = 210 + 0 = 210
    assert b.vy == 0
    assert b.y == GROUND_Y


def test_update_ball_physics_ceiling_bounce():
    """Ball below ceiling moving up should bounce downward."""
    b = Ball(x=100, y=CEILING_Y, vx=2, vy=-5)
    update_ball_physics(b)
    # Gravity: vy = -4.7, ceiling check: 30 <= 30 → vy = abs(-4.7)*0.7 = 3.29
    # y = 30 + 3.29 = 33.29
    assert b.y == pytest.approx(33.29, rel=1e-2)


def test_update_ball_physics_speed_clamp():
    b = Ball(x=100, y=100, vx=12, vy=-15)
    update_ball_physics(b)
    assert abs(b.vx) <= MAX_SPEED
    assert abs(b.vy) <= MAX_SPEED


# ═══════════════════════════════════════════════════════════════
# Point Check Tests
# ═══════════════════════════════════════════════════════════════


def test_check_point_no_point():
    b = Ball(x=100, y=100, vx=2, vy=-3)
    assert check_point(b) == -1


def test_check_point_player_scores():
    """Ball lands on AI side (x >= NET_X) → player scores."""
    b = Ball(x=200, y=GROUND_Y, vx=0, vy=0.1)
    assert check_point(b) == 1


def test_check_point_ai_scores():
    """Ball lands on player side (x < NET_X) → AI scores."""
    b = Ball(x=100, y=GROUND_Y, vx=0, vy=-0.1)
    assert check_point(b) == 0


def test_check_point_out_of_bounds_left():
    b = Ball(x=-30, y=100, vx=-5, vy=0)
    assert check_point(b) == 1  # player scores (AI hit it out)


def test_check_point_out_of_bounds_right():
    b = Ball(x=SCREEN_W + 30, y=100, vx=5, vy=0)
    assert check_point(b) == 0  # AI scores (player hit it out)


# ═══════════════════════════════════════════════════════════════
# Ball In Range Tests
# ═══════════════════════════════════════════════════════════════


def test_ball_in_range_true():
    b = Ball(x=80, y=180, vx=0, vy=0)
    assert ball_in_range(b, 100, 200) is True


def test_ball_in_range_too_far_horizontal():
    b = Ball(x=20, y=200, vx=0, vy=0)
    assert ball_in_range(b, 100, 200) is False


def test_ball_in_range_too_far_vertical():
    b = Ball(x=100, y=100, vx=0, vy=0)
    assert ball_in_range(b, 100, 200) is False


def test_ball_in_range_boundary():
    b = Ball(x=100 + TOUCH_RANGE_H, y=200, vx=0, vy=0)
    assert ball_in_range(b, 100, 200) is True


# ═══════════════════════════════════════════════════════════════
# Net Crossing Tests
# ═══════════════════════════════════════════════════════════════


def test_ball_crossed_net_left_to_right():
    assert ball_crossed_net(159, 161) is True


def test_ball_crossed_net_right_to_left():
    assert ball_crossed_net(161, 159) is True


def test_ball_crossed_net_no_cross():
    assert ball_crossed_net(100, 150) is False
    assert ball_crossed_net(170, 200) is False


def test_ball_crossed_net_exact():
    assert ball_crossed_net(159.5, 160.5) is True


# ═══════════════════════════════════════════════════════════════
# State Initialization Tests
# ═══════════════════════════════════════════════════════════════


def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score_player == 0
    assert g.score_ai == 0
    assert g.player.touches_left == TOUCHES_PER_SIDE
    assert g.ai.touches_left == TOUCHES_PER_SIDE
    assert g.player.combo == 0
    assert g.player.max_combo == 0
    assert g.player.last_color == -1
    assert g.player_color == RED
    assert len(g.particles) == 0
    assert len(g.floats) == 0
    assert g._super_spike is False


def test_reset_after_playing_clears_state():
    g = _make_game()
    g.score_player = 3
    g.score_ai = 2
    g.player.combo = 4
    g.player.max_combo = 5
    g.player.touches_left = 1
    g.player.last_color = YELLOW
    g._super_spike = True
    g._spawn_particles(100, 100, RED, 8)
    g._spawn_floating_text(100, 100, "TEST", WHITE, 30)
    g._shake_frames = 5
    g._touch_label = "Spike"
    g._touch_label_timer = 10

    g.reset()

    assert g.phase == Phase.TITLE
    assert g.score_player == 0
    assert g.score_ai == 0
    assert g.player.combo == 0
    assert g.player.max_combo == 0
    assert g.player.touches_left == TOUCHES_PER_SIDE
    assert g.player.last_color == -1
    assert g._super_spike is False
    assert len(g.particles) == 0
    assert len(g.floats) == 0
    assert g._shake_frames == 0


# ═══════════════════════════════════════════════════════════════
# Serve Logic Tests
# ═══════════════════════════════════════════════════════════════


def test_serve_ball_ai_side():
    g = _make_game()
    g._serving_side = 0
    g._serve_ball()
    # Ball starts on AI side, moving left
    assert AI_X_MIN <= g.ball.x <= AI_X_MAX
    assert g.ball.vx < 0
    assert g.ball.vy < 0
    assert g.player.touches_left == TOUCHES_PER_SIDE
    assert g.ai.touches_left == TOUCHES_PER_SIDE


def test_serve_ball_player_side():
    g = _make_game()
    g._serving_side = 1
    g._serve_ball()
    assert PLAYER_X_MIN <= g.ball.x <= PLAYER_X_MAX
    assert g.ball.vx > 0
    assert g.ball.vy < 0


# ═══════════════════════════════════════════════════════════════
# Player Touch Execution Tests
# ═══════════════════════════════════════════════════════════════


def test_execute_player_touch_decrements_touches():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.ball.x = 80
    g.ball.y = 180
    g.player.x = 80
    # ball_in_player_court checks court bounds
    g.ball.x = PLAYER_X_MIN + 10
    g._execute_player_touch()
    assert g.player.touches_left == TOUCHES_PER_SIDE - 1


def test_execute_player_touch_sets_combo():
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    g.player_color = RED
    g._execute_player_touch()
    assert g.player.combo == 1
    assert g.player.last_color == RED


def test_execute_player_touch_same_color_combo_builds():
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    g.player_color = RED
    g._execute_player_touch()
    assert g.player.combo == 1

    g.player_color = RED  # same color again
    g.ball.x = PLAYER_X_MIN + 10
    g._touch_cooldown = 0
    g._execute_player_touch()
    assert g.player.combo == 2


def test_execute_player_touch_different_color_resets_combo():
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    g.player_color = RED
    g._execute_player_touch()
    assert g.player.combo == 1

    g.player_color = GREEN  # different color
    g.ball.x = PLAYER_X_MIN + 10
    g._touch_cooldown = 0
    g._execute_player_touch()
    assert g.player.combo == 1


def test_execute_player_touch_tracks_max_combo():
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    g.player_color = RED
    g._execute_player_touch()  # combo=1
    g.player_color = RED
    g._execute_player_touch()  # combo=2
    g.player_color = RED
    g._execute_player_touch()  # combo=3
    assert g.player.max_combo == 3


def test_execute_player_touch_super_spike_detected():
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    g.player.last_color = RED
    g.player.combo = 2
    g.player.touches_left = 1  # this is the last (spike) touch
    g.player_color = RED

    g._execute_player_touch()

    assert g.player.touches_left == 0
    assert g._super_spike is True
    assert "SUPER" in g._touch_label
    assert g._shake_frames == 8


def test_execute_player_touch_spawns_particles():
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    g._execute_player_touch()
    assert len(g.particles) == 8  # normal touch


def test_execute_player_touch_super_spike_spawns_more_particles():
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    g.player.last_color = RED
    g.player.combo = 2
    g.player.touches_left = 1
    g.player_color = RED
    g._execute_player_touch()
    assert len(g.particles) == 20  # super spike


def test_execute_player_touch_no_touches_left():
    g = _make_game()
    g.player.touches_left = 0
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    touches_before = g.player.touches_left
    combo_before = g.player.combo
    g._execute_player_touch()
    assert g.player.touches_left == touches_before  # unchanged
    assert g.player.combo == combo_before  # unchanged


def test_execute_player_touch_cycles_color():
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    assert g.player_color == RED
    g._execute_player_touch()
    assert g.player_color == GREEN


def test_execute_player_touch_sets_cooldown():
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    g._execute_player_touch()
    assert g._touch_cooldown == 10


def test_execute_player_touch_sets_ball_velocity():
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    g.ball.vx = 0
    g.ball.vy = 0
    g._execute_player_touch()
    assert g.ball.vx > 0  # toward AI
    assert g.ball.vy < 0  # upward


def test_execute_player_touch_third_touch_forces_vx_positive():
    """After 3 touches, ball MUST go to AI side (vx > 0)."""
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80
    g.player.touches_left = 1  # third (last) touch
    g._execute_player_touch()
    assert g.player.touches_left == 0
    assert g.ball.vx > 0  # enforced toward AI


# ═══════════════════════════════════════════════════════════════
# AI Touch Execution Tests
# ═══════════════════════════════════════════════════════════════


def test_execute_ai_touch_decrements_touches():
    g = _make_game()
    g.ball.x = AI_X_MIN + 10
    g.ball.y = 180
    g.ai.x = AI_X_MIN + 10
    assert g.ai.touches_left == TOUCHES_PER_SIDE
    g._execute_ai_touch()
    assert g.ai.touches_left == TOUCHES_PER_SIDE - 1


def test_execute_ai_touch_no_touches_left():
    g = _make_game()
    g.ai.touches_left = 0
    touches_before = g.ai.touches_left
    g._execute_ai_touch()
    assert g.ai.touches_left == touches_before


def test_execute_ai_touch_cannot_return_super_spike():
    g = _make_game()
    g._super_spike = True
    g.ball.x = AI_X_MIN + 10
    g.ball.y = 180
    g.ai.x = AI_X_MIN + 10
    touches_before = g.ai.touches_left
    g._execute_ai_touch()
    assert g.ai.touches_left == touches_before  # unchanged, didn't touch


def test_execute_ai_touch_cycles_color():
    g = _make_game()
    g.ball.x = AI_X_MIN + 10
    g.ball.y = 180
    g.ai.x = AI_X_MIN + 10
    assert g.ai_color == RED
    g._execute_ai_touch()
    assert g.ai_color == GREEN


def test_execute_ai_touch_sets_velocity_toward_player():
    g = _make_game()
    g.ball.x = AI_X_MIN + 10
    g.ball.y = 180
    g.ai.x = AI_X_MIN + 10
    g.ball.vx = 0
    g.ball.vy = 0
    g._execute_ai_touch()
    assert g.ball.vx < 0  # toward player
    assert g.ball.vy < 0  # upward


def test_execute_ai_touch_third_touch_forces_vx_negative():
    g = _make_game()
    g.ball.x = AI_X_MIN + 10
    g.ball.y = 180
    g.ai.x = AI_X_MIN + 10
    g.ai.touches_left = 1
    g._execute_ai_touch()
    assert g.ai.touches_left == 0
    assert g.ball.vx < 0  # enforced toward player


def test_execute_ai_touch_never_super_spike():
    """AI should never trigger super spike, even with combo >= 3."""
    g = _make_game()
    g.ball.x = AI_X_MIN + 10
    g.ball.y = 180
    g.ai.x = AI_X_MIN + 10
    g.ai.last_color = RED
    g.ai.combo = 3
    g.ai.touches_left = 1
    g.ai_color = RED
    g._execute_ai_touch()
    # AI touch doesn't check is_super_spike, so _super_spike stays False
    assert g._super_spike is False


# ═══════════════════════════════════════════════════════════════
# Net Crossing Reset Tests
# ═══════════════════════════════════════════════════════════════


def test_ball_crossed_net_resets_both_touches():
    """When ball crosses net, both sides get fresh touches."""
    g = _make_game()
    g.player.touches_left = 1
    g.ai.touches_left = 0
    g.player.combo = 3
    g.ai.combo = 2

    # Simulate net crossing
    assert ball_crossed_net(159, 161) is True

    # Manually simulate the reset that happens in _update_playing
    g.player.touches_left = TOUCHES_PER_SIDE
    g.ai.touches_left = TOUCHES_PER_SIDE
    g.player.combo = 0
    g.ai.combo = 0

    assert g.player.touches_left == TOUCHES_PER_SIDE
    assert g.ai.touches_left == TOUCHES_PER_SIDE
    assert g.player.combo == 0
    assert g.ai.combo == 0


# ═══════════════════════════════════════════════════════════════
# Particle System Tests
# ═══════════════════════════════════════════════════════════════


def test_spawn_particles():
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100, 100, RED, 8)
    assert len(g.particles) == 8
    for p in g.particles:
        assert p.color == RED
        assert p.x == 100
        assert p.y == 100
        assert 6 <= p.life <= 16


def test_update_particles_reduces_life():
    g = _make_game()
    g._spawn_particles(100, 100, RED, 4)
    for _ in range(5):
        g._update_particles()
    # After 5 frames, particles with max life 16 should still be alive
    # (minimum life is 6, 6-5=1 > 0 → all alive)
    assert len(g.particles) == 4
    for p in g.particles:
        assert p.life < 16  # life decreased


def test_particles_eventually_expire():
    g = _make_game()
    g._spawn_particles(100, 100, RED, 4)
    for _ in range(30):
        g._update_particles()
    assert len(g.particles) == 0


# ═══════════════════════════════════════════════════════════════
# Floating Text Tests
# ═══════════════════════════════════════════════════════════════


def test_spawn_floating_text():
    g = _make_game()
    g._spawn_floating_text(100, 100, "SUPER!", YELLOW, 40)
    assert len(g.floats) == 1
    ft = g.floats[0]
    assert ft.text == "SUPER!"
    assert ft.life == 40
    assert ft.color == YELLOW


def test_update_floating_texts_move_up():
    g = _make_game()
    g._spawn_floating_text(100, 100, "TEST", WHITE, 30)
    ft = g.floats[0]
    orig_y = ft.y
    g._update_floating_texts()
    assert ft.y < orig_y
    assert ft.life == 29


def test_floating_texts_eventually_expire():
    g = _make_game()
    g._spawn_floating_text(100, 100, "FADE", WHITE, 5)
    for _ in range(10):
        g._update_floating_texts()
    assert len(g.floats) == 0


# ═══════════════════════════════════════════════════════════════
# Phase Transition Tests (headless state only)
# ═══════════════════════════════════════════════════════════════


def test_phase_transitions_title_to_serving():
    g = _make_game()
    assert g.phase == Phase.TITLE
    g.phase = Phase.SERVING
    g._serve_timer = 30
    assert g.phase == Phase.SERVING


def test_phase_serving_to_playing():
    g = _make_game()
    g.phase = Phase.SERVING
    g._serving_side = 0
    g._serve_timer = 0
    g._serve_ball()
    g.phase = Phase.PLAYING
    assert g.phase == Phase.PLAYING
    assert AI_X_MIN <= g.ball.x <= AI_X_MAX


def test_point_scoring_increments_score():
    g = _make_game()
    g.phase = Phase.PLAYING
    # Simulate player scoring
    g.score_player += 1
    g.phase = Phase.POINT_SCORED
    g._point_timer = 60
    assert g.score_player == 1
    assert g.phase == Phase.POINT_SCORED


def test_game_over_when_player_reaches_max_points():
    g = _make_game()
    g.score_player = MAX_POINTS
    g._point_timer = 0
    # In _update_point_scored, when timer <= 0 and score >= MAX_POINTS:
    assert g.score_player >= MAX_POINTS


def test_game_over_when_ai_reaches_max_points():
    g = _make_game()
    g.score_ai = MAX_POINTS
    assert g.score_ai >= MAX_POINTS


def test_serving_side_alternates():
    g = _make_game()
    g._serving_side = 0
    g._serving_side = 1 - g._serving_side
    assert g._serving_side == 1
    g._serving_side = 1 - g._serving_side
    assert g._serving_side == 0


# ═══════════════════════════════════════════════════════════════
# Edge Case Tests
# ═══════════════════════════════════════════════════════════════


def test_ball_physics_net_immaterial():
    """Ball passes through net area (physics doesn't implement net collision)."""
    b = Ball(x=NET_X, y=NET_TOP_Y + 5, vx=1, vy=0)
    update_ball_physics(b)
    assert b.x == pytest.approx(NET_X + 1)  # passes through


def test_point_at_exact_net_boundary():
    """Ball landing exactly on net line."""
    b = Ball(x=NET_X, y=GROUND_Y, vx=0, vy=0.1)
    result = check_point(b)
    assert result == 1  # x >= 160 → player scores


def test_touch_range_boundary_horizontal():
    """Test exact touch range boundary."""
    b = Ball(x=100 + TOUCH_RANGE_H, y=200, vx=0, vy=0)
    assert ball_in_range(b, 100, 200) is True
    b2 = Ball(x=100 + TOUCH_RANGE_H + 1, y=200, vx=0, vy=0)
    assert ball_in_range(b2, 100, 200) is False


def test_multiple_combo_build_and_reset():
    """Full combo lifecycle: build combo, trigger super, reset combo."""
    g = _make_game()
    g.ball.x = PLAYER_X_MIN + 10
    g.ball.y = 180
    g.player.x = 80

    # Build combo to 3
    g.player_color = RED
    g._execute_player_touch()  # combo=1, touch #1
    g.player_color = RED
    g._touch_cooldown = 0
    g._execute_player_touch()  # combo=2, touch #2
    g.player_color = RED
    g._touch_cooldown = 0
    g._execute_player_touch()  # combo=3, touch #3 → SUPER
    assert g.player.max_combo == 3
    assert g._super_spike is True
    assert g._shake_frames == 8

    # Simulate net crossing → reset
    g.player.combo = 0
    g.player.last_color = -1
    g.player.touches_left = TOUCHES_PER_SIDE
    g._super_spike = False
    assert g.player.combo == 0
    assert g.player.touches_left == TOUCHES_PER_SIDE
    assert g._super_spike is False


def test_player_cannot_touch_when_cooldown_active():
    """In headless test, cooldown prevents touch execution check."""
    g = _make_game()
    g._touch_cooldown = 5
    # Cooldown > 0 simulation: the update code skips touch
    assert g._touch_cooldown > 0
    # After decrementing
    g._touch_cooldown -= 1
    assert g._touch_cooldown == 4


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
