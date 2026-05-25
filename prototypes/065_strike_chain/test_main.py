"""test_main.py — Headless logic tests for 065_strike_chain."""
import sys
import math
import pytest
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/065_strike_chain")
from main import (
    Game, Pin, Ball, Particle, FloatingText,
    LANE_LEFT, LANE_RIGHT, LANE_CENTER,
    BALL_RADIUS, PIN_RADIUS, BALL_START_Y,
    PIN_COLORS, PIN_VALUES, MAX_FRAMES, MAX_HEAT, SURGE_THRESHOLD,
    HEAT_DRIFT_START, ANGLE_MAX, POWER_MIN_SPEED, POWER_MAX_SPEED,
    GUTTER_X_MARGIN,
)
import random


def _make_game(seed: int = 42) -> Game:
    """Factory: create Game bypassing __init__ (no pyxel.init needed)."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.pins = []
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8)
    g.particles = []
    g.floating_texts = []
    g.phase = "aiming"
    g.frame = 1
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0
    g.power = 0.0
    g.aim_angle = 0.0
    g.charging = False
    g.hit_order_counter = 0
    g.phase_timer = 0
    g.is_surge_ball = False
    g.frame_score = 0
    g.frame_knocked_count = 0
    g.frame_combo_text = ""
    g.total_frames_played = 0
    g.reset()
    return g


def _make_blank_game(seed: int = 42) -> Game:
    """Factory: create blank Game (all empty) without reset()."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.pins = []
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8)
    g.particles = []
    g.floating_texts = []
    g.phase = "aiming"
    g.frame = 1
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0
    g.power = 0.0
    g.aim_angle = 0.0
    g.charging = False
    g.hit_order_counter = 0
    g.phase_timer = 0
    g.is_surge_ball = False
    g.frame_score = 0
    g.frame_knocked_count = 0
    g.frame_combo_text = ""
    g.total_frames_played = 0
    return g


# ── Dataclass tests ──

def test_pin_dataclass():
    p = Pin(x=100.0, y=150.0, color=8)
    assert p.x == 100.0
    assert p.y == 150.0
    assert p.color == 8
    assert p.alive
    assert p.vy == 0.0
    assert p.vx == 0.0
    assert p.hit_order == -1


def test_ball_dataclass():
    b = Ball(x=160.0, y=24.0, color=3)
    assert b.x == 160.0
    assert b.y == 24.0
    assert b.color == 3
    assert b.vy == 0.0
    assert b.vx == 0.0
    assert not b.rolling


def test_particle_dataclass():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8


def test_floating_text_dataclass():
    ft = FloatingText(x=100.0, y=50.0, text="COMBO!", life=30, color=7)
    assert ft.x == 100.0
    assert ft.text == "COMBO!"
    assert ft.life == 30
    assert ft.color == 7


# ── Pin initialization ──

def test_init_pins_creates_10_pins():
    g = _make_game(42)
    assert len(g.pins) == 10
    for pin in g.pins:
        assert pin.alive
        assert pin.color in PIN_COLORS
        assert pin.hit_order == -1


def test_init_pins_positions():
    g = _make_game(42)
    # Row 0: 1 pin at center
    assert g.pins[0].y == 130
    assert g.pins[0].x == LANE_CENTER
    # Row 1: 2 pins
    assert g.pins[1].y == 148
    assert g.pins[2].y == 148
    # Row 2: 3 pins
    assert g.pins[3].y == 166
    assert g.pins[4].y == 166
    assert g.pins[5].y == 166
    # Row 3: 4 pins
    assert g.pins[6].y == 184
    assert g.pins[7].y == 184
    assert g.pins[8].y == 184
    assert g.pins[9].y == 184


def test_init_pins_random_colors_different():
    # With seed 99, check that not all pins have the same color
    g = _make_game(99)
    colors = {p.color for p in g.pins}
    # Should have at least 2 different colors
    assert len(colors) >= 2


# ── Ball rolling ──

def test_roll_ball_straight():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8)
    g._roll_ball(0.0, 0.5)
    assert g.ball.rolling
    speed = POWER_MIN_SPEED + 0.5 * (POWER_MAX_SPEED - POWER_MIN_SPEED)
    assert g.ball.vy == pytest.approx(speed)
    assert g.ball.vx == pytest.approx(0.0, abs=0.01)


def test_roll_ball_angled_right():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8)
    g._roll_ball(20.0, 1.0)
    speed = POWER_MAX_SPEED
    assert g.ball.vx > 0  # Should go right
    assert g.ball.vy > 0  # Should go down
    # vx = speed * sin(20°), vy = speed * cos(20°)
    assert g.ball.vx == pytest.approx(speed * math.sin(math.radians(20)))
    assert g.ball.vy == pytest.approx(speed * math.cos(math.radians(20)))


def test_roll_ball_angled_left():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8)
    g._roll_ball(-15.0, 0.3)
    assert g.ball.vx < 0  # Should go left
    assert g.ball.vy > 0  # Should go down


def test_roll_ball_min_power():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8)
    g._roll_ball(0.0, 0.0)
    assert g.ball.vy == POWER_MIN_SPEED


def test_roll_ball_max_power():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8)
    g._roll_ball(0.0, 1.0)
    assert g.ball.vy == POWER_MAX_SPEED


# ── Collision detection ──

def test_check_collision_hit():
    g = _make_blank_game(42)
    ball = Ball(x=100.0, y=100.0, color=8)
    pin = Pin(x=100.0, y=100.0, color=8)
    assert g._check_collision(ball, pin)


def test_check_collision_miss():
    g = _make_blank_game(42)
    ball = Ball(x=100.0, y=100.0, color=8)
    pin = Pin(x=200.0, y=200.0, color=8)
    assert not g._check_collision(ball, pin)


def test_check_collision_edge_distance():
    g = _make_blank_game(42)
    ball = Ball(x=100.0, y=100.0, color=8)
    pin = Pin(x=100.0 + BALL_RADIUS + PIN_RADIUS - 0.5, y=100.0, color=8)
    assert g._check_collision(ball, pin)

    pin2 = Pin(x=100.0 + BALL_RADIUS + PIN_RADIUS + 1.0, y=100.0, color=8)
    assert not g._check_collision(ball, pin2)


# ── Update ball movement ──

def test_update_ball_not_rolling_no_op():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8)
    g.ball.rolling = False
    result = g._update_ball()
    assert not result
    assert g.ball.x == LANE_CENTER
    assert g.ball.y == BALL_START_Y


def test_update_ball_moves_down():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8, rolling=True)
    g.ball.vy = 5.0
    g.ball.vx = 0.0
    g.pins = []  # No pins to hit
    g._update_ball()
    assert g.ball.y > BALL_START_Y
    assert g.ball.x == LANE_CENTER


def test_update_ball_past_pins_returns_true():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=230, color=8, rolling=True)
    g.ball.vy = 5.0
    g.pins = []
    result = g._update_ball()
    assert result


def test_update_ball_gutter_left_returns_true():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_LEFT - GUTTER_X_MARGIN - 1, y=100, color=8,
                  rolling=True, vy=1.0)
    g.pins = []
    result = g._update_ball()
    assert result


def test_update_ball_gutter_right_returns_true():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_RIGHT + GUTTER_X_MARGIN + 1, y=100, color=8,
                  rolling=True, vy=1.0)
    g.pins = []
    result = g._update_ball()
    assert result


def test_update_ball_hits_pin():
    g = _make_blank_game(42)
    g.ball = Ball(x=100, y=100, color=8, rolling=True, vy=5.0, vx=0.0)
    pin = Pin(x=100, y=105, color=8, alive=True)
    g.pins = [pin]
    g._update_ball()
    assert not pin.alive
    assert pin.hit_order >= 0
    assert abs(pin.vy) > 0.1  # Should have knockback


def test_update_ball_hit_order_increments():
    g = _make_blank_game(42)
    g.ball = Ball(x=100, y=90, color=8, rolling=True, vy=3.0, vx=0.0)
    pin1 = Pin(x=100, y=100, color=8, alive=True)
    pin2 = Pin(x=100, y=140, color=8, alive=True)
    g.pins = [pin1, pin2]
    g.hit_order_counter = 0

    # First update: hits pin1
    g._update_ball()
    assert not pin1.alive
    assert pin1.hit_order == 0
    assert g.hit_order_counter == 1

    # Run updates until pin2 is hit (ball moves at vy=3 per frame)
    for _ in range(30):
        done = g._update_ball()
        if not pin2.alive:
            break
        if done:
            break

    assert not pin2.alive
    assert pin2.hit_order == 1
    assert g.hit_order_counter == 2


# ── Pin animation ──

def test_update_pins_knocked_pin_gravity():
    g = _make_blank_game(42)
    pin = Pin(x=100.0, y=100.0, color=8, alive=False, vy=-2.0, vx=1.0)
    g.pins = [pin]
    old_vy = pin.vy
    g._update_pins()
    assert pin.vy > old_vy  # Gravity increases downward velocity


def test_update_pins_alive_pin_stays():
    g = _make_blank_game(42)
    pin = Pin(x=100.0, y=100.0, color=8, alive=True)
    g.pins = [pin]
    old_x, old_y = pin.x, pin.y
    g._update_pins()
    assert pin.x == old_x
    assert pin.y == old_y


def test_update_pins_friction():
    g = _make_blank_game(42)
    pin = Pin(x=100.0, y=100.0, color=8, alive=False, vx=10.0, vy=0.0)
    g.pins = [pin]
    g._update_pins()
    assert abs(pin.vx) < 10.0  # Friction applied


# ── Combo evaluation ──

def test_evaluate_combo_no_pins():
    g = _make_blank_game(42)
    g.combo = 3
    new_combo, score, is_miss, text = g._evaluate_combo([], 8)
    assert new_combo == 0
    assert score == 0
    assert is_miss
    assert text == "MISS!"


def test_evaluate_combo_same_color_increases():
    g = _make_blank_game(42)
    g.combo = 2
    pins = [
        Pin(x=100, y=100, color=8, alive=False, hit_order=0),
        Pin(x=110, y=100, color=8, alive=False, hit_order=1),
    ]
    new_combo, score, is_miss, text = g._evaluate_combo(pins, 8)
    assert new_combo == 3
    assert score > 0
    assert not is_miss
    assert "COMBO 3" in text


def test_evaluate_combo_different_color_resets():
    g = _make_blank_game(42)
    g.combo = 5
    pins = [
        Pin(x=100, y=100, color=3, alive=False, hit_order=0),  # GREEN, different
    ]
    new_combo, score, is_miss, text = g._evaluate_combo(pins, 8)
    assert new_combo == 1
    assert not is_miss
    assert "RESET" in text


def test_evaluate_combo_multiplier():
    g = _make_blank_game(42)
    g.combo = 0
    pins = [
        Pin(x=100, y=100, color=8, alive=False, hit_order=0),  # RED=8
    ]
    new_combo, score1, _, _ = g._evaluate_combo(pins, 8)
    assert new_combo == 1
    # multiplier = 1 + (1-1)*0.5 = 1.0, value = 8 * 1 = 8
    assert score1 == 8

    g.combo = 3
    new_combo, score2, _, _ = g._evaluate_combo(pins, 8)
    assert new_combo == 4
    # multiplier = 1 + (4-1)*0.5 = 2.5, value = 8 * 2.5 = 20
    assert score2 == 20


def test_evaluate_combo_surge_always_matches():
    g = _make_blank_game(42)
    g.combo = 2
    g.is_surge_ball = True
    pins = [
        Pin(x=100, y=100, color=3, alive=False, hit_order=0),  # GREEN
        Pin(x=110, y=100, color=10, alive=False, hit_order=1),  # YELLOW
    ]
    new_combo, score, is_miss, text = g._evaluate_combo(pins, 8)
    assert new_combo == 3
    assert "SURGE" in text
    # multiplier = 1 + (3-1)*0.5 = 2.0
    # score = (3 + 10) * 2.0 * 3 = 78
    assert score == 78
    assert not is_miss


def test_evaluate_combo_multiple_pins_score():
    g = _make_blank_game(42)
    g.combo = 0
    pins = [
        Pin(x=100, y=100, color=8, alive=False, hit_order=0),   # RED=8
        Pin(x=110, y=100, color=8, alive=False, hit_order=1),   # RED=8
        Pin(x=120, y=100, color=8, alive=False, hit_order=2),   # RED=8
    ]
    new_combo, score, _, _ = g._evaluate_combo(pins, 8)
    assert new_combo == 1
    # multiplier = 1 + 0 = 1.0, sum = (8+8+8)*1 = 24
    assert score == 24


# ── Gutter detection ──

def test_is_gutter_left():
    g = _make_blank_game(42)
    g.ball.x = LANE_LEFT - GUTTER_X_MARGIN - 1
    assert g._is_gutter()


def test_is_gutter_right():
    g = _make_blank_game(42)
    g.ball.x = LANE_RIGHT + GUTTER_X_MARGIN + 1
    assert g._is_gutter()


def test_is_gutter_in_lane():
    g = _make_blank_game(42)
    g.ball.x = LANE_CENTER
    assert not g._is_gutter()


# ── Knocked pins tracking ──

def test_get_knocked_pins_empty():
    g = _make_blank_game(42)
    assert len(g._get_knocked_pins()) == 0


def test_get_knocked_pins_returns_only_hit():
    g = _make_blank_game(42)
    p1 = Pin(x=100, y=100, color=8, alive=False, hit_order=0)
    p2 = Pin(x=110, y=100, color=8, alive=True, hit_order=-1)
    p3 = Pin(x=120, y=100, color=8, alive=False, hit_order=1)
    g.pins = [p1, p2, p3]
    knocked = g._get_knocked_pins()
    assert len(knocked) == 2
    assert p2 not in knocked


# ── Particles ──

def test_spawn_particles_creates_particles():
    g = _make_blank_game(42)
    assert len(g.particles) == 0
    g._spawn_particles(100, 100, 8, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == 8
        assert p.life > 0


def test_update_particles_moves_and_decays():
    g = _make_blank_game(42)
    g._spawn_particles(100, 100, 8, 3)
    old_x = [p.x for p in g.particles]
    old_y = [p.y for p in g.particles]
    old_life = [p.life for p in g.particles]
    g._update_particles()
    for i, p in enumerate(g.particles):
        assert p.x != old_x[i] or p.y != old_y[i]
        assert p.life == old_life[i] - 1


def test_update_particles_removes_dead():
    g = _make_blank_game(42)
    g.particles = [
        Particle(x=0, y=0, vx=0, vy=0, life=1, color=8),
        Particle(x=0, y=0, vx=0, vy=0, life=2, color=8),
    ]
    g._update_particles()
    assert len(g.particles) == 1


# ── Floating text ──

def test_spawn_floating_text():
    g = _make_blank_game(42)
    g._spawn_floating_text(100, 50, "COMBO!", 7, 30)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "COMBO!"
    assert g.floating_texts[0].color == 7
    assert g.floating_texts[0].life == 30


def test_update_floating_texts_float_up_and_decay():
    g = _make_blank_game(42)
    g._spawn_floating_text(100, 50, "Test", 7, 30)
    old_y = g.floating_texts[0].y
    g._update_floating_texts()
    assert g.floating_texts[0].y < old_y
    assert g.floating_texts[0].life == 29


def test_update_floating_texts_removes_dead():
    g = _make_blank_game(42)
    g.floating_texts = [
        FloatingText(x=0, y=0, text="A", life=1, color=7),
        FloatingText(x=0, y=0, text="B", life=2, color=7),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1


# ── Reset ──

def test_reset_clears_state():
    g = _make_game(42)
    g.score = 9999
    g.combo = 10
    g.heat = 4
    g.frame = 8
    g.phase = "rolling"
    g.total_frames_played = 5
    g.max_combo = 8

    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0
    assert g.frame == 1
    assert g.phase == "title"
    assert g.total_frames_played == 0
    assert g.max_combo == 0
    assert len(g.pins) == 10
    assert not g.ball.rolling
    assert not g.charging
    assert not g.is_surge_ball


def test_reset_all_pins_alive():
    g = _make_game(42)
    for p in g.pins:
        p.alive = False
        p.hit_order = 5
    g.reset()
    for p in g.pins:
        assert p.alive
        assert p.hit_order == -1


# ── Launch ball (simulate _launch_ball behavior) ──

def test_launch_ball_starts_rolling():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8)
    g.pins = [Pin(x=LANE_CENTER, y=200, color=8)]
    g.aim_angle = 0.0
    g.power = 0.5
    g.charging = True
    g.combo = 2
    g.hit_order_counter = 99

    g._launch_ball()
    assert not g.charging
    assert g.ball.rolling
    assert g.ball.x == LANE_CENTER
    assert g.ball.y == BALL_START_Y
    assert g.hit_order_counter == 0
    assert g.phase == "rolling"
    assert not g.is_surge_ball  # combo 2 < 5


def test_launch_ball_with_surge():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8)
    g.pins = [Pin(x=LANE_CENTER, y=200, color=8)]
    g.aim_angle = 0.0
    g.power = 0.5
    g.charging = True
    g.combo = 5  # Surge threshold reached

    g._launch_ball()
    assert g.is_surge_ball


# ── Heat drift ──

def test_heat_drift_applies_at_heat_3():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8, rolling=True, vy=5.0, vx=0.0)
    g.heat = 3
    g.pins = []  # No pins to interfere

    # Run update_ball multiple times and verify vx eventually changes
    drifted = False
    for _ in range(50):
        if g._update_ball():
            break
        if g.ball.vx != 0.0:
            drifted = True
            break
    # Heat drift should cause some change
    assert drifted


def test_no_heat_drift_below_3():
    g = _make_blank_game(42)
    g.ball = Ball(x=LANE_CENTER, y=BALL_START_Y, color=8, rolling=True, vy=5.0, vx=0.0)
    g.heat = 2
    g.pins = []

    # Run update_ball multiple times
    for _ in range(20):
        if g._update_ball():
            break
    # vx should remain 0 without drift
    assert g.ball.vx == 0.0


# ── Any pins animating ──

def test_any_pins_animating_true():
    g = _make_blank_game(42)
    g.pins = [Pin(x=100, y=100, color=8, alive=False, vx=1.0, vy=-2.0)]
    assert g._any_pins_animating()


def test_any_pins_animating_false():
    g = _make_blank_game(42)
    g.pins = [Pin(x=100, y=100, color=8, alive=True, vx=0.0, vy=0.0)]
    assert not g._any_pins_animating()


def test_any_pins_animating_dead_stationary():
    g = _make_blank_game(42)
    g.pins = [Pin(x=100, y=100, color=8, alive=False, vx=0.0, vy=0.0)]
    assert not g._any_pins_animating()


# ── Surge particles ──

def test_spawn_surge_particles():
    g = _make_blank_game(42)
    assert len(g.particles) == 0
    g._spawn_surge_particles()
    assert len(g.particles) == 35


# ── Ball color assignment ──

def test_assign_random_ball_color():
    g = _make_blank_game(42)
    g._assign_random_ball_color()
    assert g.ball.color in PIN_COLORS


# ── Constants ──

def test_constants():
    assert MAX_FRAMES == 10
    assert MAX_HEAT == 5
    assert SURGE_THRESHOLD == 5
    assert HEAT_DRIFT_START == 3
    assert ANGLE_MAX == 28.0
    assert len(PIN_COLORS) == 4
    assert all(c in PIN_VALUES for c in PIN_COLORS)


# ── PIN_VALUES ──

def test_pin_values():
    assert PIN_VALUES[8] == 8
    assert PIN_VALUES[3] == 3
    assert PIN_VALUES[5] == 5
    assert PIN_VALUES[10] == 10


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS {test.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL {test.__name__}")
            traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed:
        sys.exit(1)
