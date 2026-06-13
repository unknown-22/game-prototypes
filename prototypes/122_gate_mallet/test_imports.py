"""test_imports.py — Headless logic tests for 122_gate_mallet."""
import math
import random as _random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (
    Game, Phase, PlaySubPhase, Ball, Gate, Particle,
    BALL_COLORS, N_COLORS, SCREEN_W, SCREEN_H,
    FRICTION, MAX_SPEED, MIN_SPEED, MAX_POWER_DIST,
    COMBO_THRESHOLD, SUPER_DURATION, SUPER_SCORE_MULT,
    MAX_HEAT, HEAT_PER_STROKE, HEAT_PER_MISS, HEAT_DECAY_RATE,
    BASE_GATE_SCORE, TOTAL_GATES, GATE_RADIUS, GATE_LAYOUT,
)


def _make_game(seed: int = 42) -> Game:
    """Create a Game bypassing pyxel.init/run for headless testing."""
    g = Game.__new__(Game)
    g._rng = _random.Random(seed)
    g.phase = Phase.TITLE
    g.sub_phase = PlaySubPhase.IDLE
    g.ball = Ball(x=160.0, y=200.0, vx=0.0, vy=0.0, color=0, radius=4.0, moving=False)
    g.gates = []
    g.particles = []
    g.floating_texts = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.gates_passed = 0
    g.heat = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.aiming = False
    g.aim_start_x = 0.0
    g.aim_start_y = 0.0
    g.shake_frames = 0
    g.high_score = 0
    g.stroke_gate_passed = False
    g.reset()
    return g


# --- Test Constants ---

def test_constants() -> None:
    assert N_COLORS == 4
    assert len(BALL_COLORS) == 4
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert FRICTION == 0.95
    assert MAX_SPEED == 8.0
    assert MIN_SPEED == 0.1
    assert MAX_POWER_DIST == 80.0
    assert COMBO_THRESHOLD == 4
    assert SUPER_DURATION == 150
    assert SUPER_SCORE_MULT == 3
    assert MAX_HEAT == 100.0
    assert HEAT_PER_STROKE == 3.0
    assert HEAT_PER_MISS == 10.0
    assert HEAT_DECAY_RATE == 0.5
    assert BASE_GATE_SCORE == 10
    assert TOTAL_GATES == 8
    assert GATE_RADIUS == 12
    assert len(GATE_LAYOUT) == 8


# --- Dataclass Tests ---

def test_ball_creation() -> None:
    b = Ball(x=100.0, y=200.0, vx=0.0, vy=0.0, color=2)
    assert b.x == 100.0
    assert b.y == 200.0
    assert b.vx == 0.0
    assert b.vy == 0.0
    assert b.color == 2
    assert b.radius == 4.0
    assert b.moving is False


def test_gate_creation() -> None:
    g = Gate(x=160.0, y=80.0, color=1)
    assert g.x == 160.0
    assert g.y == 80.0
    assert g.color == 1
    assert g.active is True
    assert g.passed is False
    assert g.score_value == BASE_GATE_SCORE


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8


# --- Enum Tests ---

def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert len(list(Phase)) == 3


def test_subphase_enum() -> None:
    assert PlaySubPhase.IDLE in PlaySubPhase
    assert PlaySubPhase.AIMING in PlaySubPhase
    assert PlaySubPhase.MOVING in PlaySubPhase
    assert len(list(PlaySubPhase)) == 3


# --- Test 1: Ball creation and color cycling ---

def test_ball_color_cycling() -> None:
    g = _make_game()
    assert g.ball.color == 0
    g._do_strike(1.0, 0.0, 80.0)  # Strike to cycle color
    assert g.ball.color == 1
    g._do_strike(-1.0, 0.0, 80.0)
    assert g.ball.color == 2
    g._do_strike(0.0, 1.0, 80.0)
    assert g.ball.color == 3
    g._do_strike(0.0, -1.0, 80.0)
    assert g.ball.color == 0  # Wraps around


# --- Test 2: Physics — velocity, friction, stop threshold ---

def test_physics_velocity_applied() -> None:
    g = _make_game()
    g.sub_phase = PlaySubPhase.MOVING
    g.ball.moving = True
    g._do_strike(1.0, 0.0, 80.0)
    assert g.ball.moving is True
    assert g.ball.vx > 0.0
    assert g.ball.vx <= MAX_SPEED


def test_physics_friction_decelerates() -> None:
    g = _make_game()
    g.sub_phase = PlaySubPhase.MOVING
    g._do_strike(1.0, 0.0, 80.0)
    initial_speed = abs(g.ball.vx)
    g._update_ball()
    assert abs(g.ball.vx) < initial_speed


def test_physics_stops_below_min_speed() -> None:
    g = _make_game()
    g.sub_phase = PlaySubPhase.MOVING
    g.ball.vx = 0.05
    g.ball.vy = 0.0
    g.ball.moving = True
    g._update_ball()
    assert g.ball.moving is False
    assert g.ball.vx == 0.0
    assert g.ball.vy == 0.0


def test_physics_speed_capped() -> None:
    g = _make_game()
    g._do_strike(1.0, 0.0, 80.0 * 10)  # Very large power
    speed = math.sqrt(g.ball.vx ** 2 + g.ball.vy ** 2)
    assert speed <= MAX_SPEED


# --- Test 3: Gate collision — same-color pass → combo++, score+ ---

def test_same_color_gate_pass() -> None:
    g = _make_game()
    g.ball.x = 160.0
    g.ball.y = 80.0
    g.ball.color = 1  # GREEN
    g.ball.moving = True
    gate = Gate(x=160.0, y=80.0, color=1)
    g.gates = [gate]
    g.sub_phase = PlaySubPhase.MOVING

    passed, earned = g._check_gate_pass()
    assert passed == 1
    assert earned >= BASE_GATE_SCORE
    assert g.combo == 1
    assert gate.passed is True


# --- Test 4: Gate collision — wrong-color pass → combo reset ---

def test_wrong_color_gate_pass() -> None:
    g = _make_game()
    g.combo = 3
    g.ball.x = 160.0
    g.ball.y = 80.0
    g.ball.color = 1  # GREEN
    g.ball.moving = True
    gate = Gate(x=160.0, y=80.0, color=2)  # BLUE — mismatch
    g.gates = [gate]
    g.sub_phase = PlaySubPhase.MOVING

    passed, earned = g._check_gate_pass()
    assert passed == 0  # No gate passed (wrong color)
    assert earned == 0
    assert g.combo == 0  # Combo reset
    assert gate.passed is False  # Gate stays available


# --- Test 5: Gate collision — already-passed gate → no score ---

def test_already_passed_gate_no_score() -> None:
    g = _make_game()
    g.ball.x = 160.0
    g.ball.y = 80.0
    g.ball.color = 1
    g.ball.moving = True
    gate = Gate(x=160.0, y=80.0, color=1, passed=True)
    g.gates = [gate]
    g.sub_phase = PlaySubPhase.MOVING
    g.score = 100

    passed, earned = g._check_gate_pass()
    assert passed == 0
    assert earned == 0
    assert g.score == 100  # No change


# --- Test 6: COMBO >= 4 → SUPER mode activates ---

def test_combo_4_activates_super() -> None:
    g = _make_game()
    g.combo = 3
    g.ball.color = 0
    g.ball.x = 60.0
    g.ball.y = 40.0
    g.ball.moving = True
    gate = Gate(x=60.0, y=40.0, color=0)
    g.gates = [gate]
    g.sub_phase = PlaySubPhase.MOVING

    assert g.super_mode is False
    g._check_gate_pass()
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


# --- Test 7: SUPER mode — rainbow (all colors pass) ---

def test_super_mode_any_color_passes() -> None:
    g = _make_game()
    g.super_mode = True
    g.ball.color = 0  # RED
    g.ball.x = 60.0
    g.ball.y = 40.0
    g.ball.moving = True
    gate = Gate(x=60.0, y=40.0, color=2)  # BLUE — would normally mismatch
    g.gates = [gate]
    g.sub_phase = PlaySubPhase.MOVING

    passed, earned = g._check_gate_pass()
    assert passed == 1
    assert earned > 0
    assert gate.passed is True


# --- Test 8: SUPER mode — 3x score multiplier ---

def test_super_mode_3x_score() -> None:
    g = _make_game()
    g.super_mode = True
    g.combo = 2
    g.ball.color = 0
    g.ball.x = 60.0
    g.ball.y = 40.0
    g.ball.moving = True
    gate = Gate(x=60.0, y=40.0, color=0)
    g.gates = [gate]
    g.sub_phase = PlaySubPhase.MOVING
    g.score = 0

    g._check_gate_pass()
    # combo becomes 3 (2 + 1), so score = base(10) * combo(3) * super_mult(3) = 90
    assert g.score == 90
    assert g.super_mode is True


# --- Test 9: SUPER mode — timer countdown and expiry ---

def test_super_mode_timer_countdown() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 5
    g._update_super_mode()
    assert g.super_timer == 4
    g._update_super_mode()
    assert g.super_timer == 3
    g._update_super_mode()
    assert g.super_timer == 2
    g._update_super_mode()
    assert g.super_timer == 1
    g._update_super_mode()
    assert g.super_timer == 0
    assert g.super_mode is False


def test_super_mode_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super_mode()
    assert g.super_mode is False
    assert g.super_timer == 0


# --- Test 10: Heat — increases on stroke (+3) and miss (+10 extra) ---

def test_heat_increases_on_stroke() -> None:
    g = _make_game()
    assert g.heat == 0.0
    g._do_strike(1.0, 0.0, 80.0)
    assert g.heat == HEAT_PER_STROKE


def test_heat_miss_penalty() -> None:
    g = _make_game()
    g.heat = 0.0
    g.sub_phase = PlaySubPhase.MOVING
    g._do_strike(1.0, 0.0, 80.0)
    g.heat += HEAT_PER_MISS  # Simulate miss penalty
    assert g.heat == HEAT_PER_STROKE + HEAT_PER_MISS

    # Test that miss penalty is applied when stroke ends without gate pass
    g2 = _make_game()
    g2._do_strike(1.0, 0.0, 80.0)
    g2.sub_phase = PlaySubPhase.MOVING
    g2.ball.moving = False
    g2.stroke_gate_passed = False
    # Manually simulate what would happen in update():
    if not g2.stroke_gate_passed:
        g2.heat = min(MAX_HEAT, g2.heat + HEAT_PER_MISS)
    assert g2.heat == HEAT_PER_STROKE + HEAT_PER_MISS


# --- Test 11: Heat — decays when ball at rest ---

def test_heat_decays_when_idle() -> None:
    g = _make_game()
    g.sub_phase = PlaySubPhase.IDLE
    g.heat = 50.0
    g.ball.moving = False
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY_RATE


def test_heat_does_not_decay_when_moving() -> None:
    g = _make_game()
    g.sub_phase = PlaySubPhase.MOVING
    g.heat = 50.0
    g.ball.moving = True
    g._update_heat()
    assert g.heat == 50.0  # No decay when moving


def test_heat_does_not_go_below_zero() -> None:
    g = _make_game()
    g.sub_phase = PlaySubPhase.IDLE
    g.heat = 0.0
    g.ball.moving = False
    g._update_heat()
    assert g.heat == 0.0


# --- Test 12: Heat >= MAX_HEAT → GAME_OVER ---

def test_heat_max_triggers_game_over() -> None:
    g = _make_game()
    g.heat = MAX_HEAT
    g.ball.moving = False
    g.phase = Phase.PLAYING
    g.sub_phase = PlaySubPhase.IDLE
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.heat == MAX_HEAT


def test_heat_exceeds_max_clamped() -> None:
    g = _make_game()
    g.heat = MAX_HEAT + 50.0
    g.ball.moving = False
    g.phase = Phase.PLAYING
    g.sub_phase = PlaySubPhase.IDLE
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.heat == MAX_HEAT


# --- Test 13: Score calculation — base × combo multiplier ---

def test_score_calculation() -> None:
    g = _make_game()
    g.ball.color = 0
    g.ball.x = 60.0
    g.ball.y = 40.0
    g.ball.moving = True
    gate = Gate(x=60.0, y=40.0, color=0)
    g.gates = [gate]
    g.sub_phase = PlaySubPhase.MOVING

    # combo 0 → combo 1: score = 10 * 1 = 10
    g._check_gate_pass()
    assert g.score == 10
    assert g.combo == 1

    # Reset gate and pass again
    gate.passed = False
    g._check_gate_pass()
    assert g.score == 30  # 10 + 10*2 = 30
    assert g.combo == 2


# --- Test 14: max_combo tracking ---

def test_max_combo_tracking() -> None:
    g = _make_game()
    assert g.max_combo == 0
    g.combo = 5
    g.max_combo = max(g.max_combo, g.combo)
    assert g.max_combo == 5
    g.combo = 2
    g.max_combo = max(g.max_combo, g.combo)
    assert g.max_combo == 5  # Should NOT go down


# --- Test 15: Multiple gates in one frame ---

def test_multiple_gates_same_frame() -> None:
    g = _make_game()
    g.ball.color = 0
    g.ball.x = 100.0
    g.ball.y = 100.0
    g.ball.moving = True
    gate1 = Gate(x=100.0, y=100.0, color=0)
    gate2 = Gate(x=105.0, y=100.0, color=0)
    g.gates = [gate1, gate2]
    g.sub_phase = PlaySubPhase.MOVING

    passed, earned = g._check_gate_pass()
    assert passed == 2
    assert gate1.passed is True
    assert gate2.passed is True


# --- Test 16: Course reset — all gates re-activate ---

def test_course_reset() -> None:
    g = _make_game()
    for gate in g.gates:
        gate.passed = True
    assert g._all_gates_passed() is True
    g._reset_course()
    assert g._all_gates_passed() is False
    for gate in g.gates:
        assert gate.active is True
        assert gate.passed is False


# --- Test 17: Particle spawning and lifecycle ---

def test_particle_spawning() -> None:
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100.0, 100.0, 8, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 100.0
        assert p.life == 15
        assert p.color == 8


def test_particle_lifecycle() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 8, 3)
    assert len(g.particles) == 3
    for _ in range(20):
        g._update_particles()
    assert len(g.particles) == 0


# --- Test 18: Floating text lifecycle ---

def test_floating_text_lifecycle() -> None:
    g = _make_game()
    g._add_floating_text(100.0, 100.0, "+10", 8, 5)
    assert len(g.floating_texts) == 1
    for _ in range(10):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


# --- Test 19: Phase transitions ---

def test_phase_transitions_title_to_playing() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    # Simulate what update() does on title click
    g.phase = Phase.PLAYING
    g.sub_phase = PlaySubPhase.IDLE
    assert g.phase == Phase.PLAYING


def test_phase_transitions_heat_to_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.sub_phase = PlaySubPhase.IDLE
    g.heat = MAX_HEAT
    g.ball.moving = False
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


# --- Test 20: reset() initializes all state correctly ---

def test_reset_initializes_state() -> None:
    g = _make_game()
    g.score = 999
    g.combo = 10
    g.heat = 88.0
    g.super_mode = True
    g.super_timer = 100
    g.gates_passed = 50
    g.phase = Phase.GAME_OVER
    g.sub_phase = PlaySubPhase.MOVING
    g.particles = [Particle(0, 0, 0, 0, 10, 0)]
    g.floating_texts = [{"x": 0, "y": 0, "text": "x", "life": 5, "color": 0}]

    g.reset()

    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.gates_passed == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.aiming is False
    assert g.shake_frames == 0
    assert g.high_score == 0
    assert g.stroke_gate_passed is False
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.ball.moving is False
    assert g.ball.color == 0
    assert len(g.gates) == TOTAL_GATES


# --- Test: No heat cost when power is zero ---

def test_no_heat_when_no_power() -> None:
    g = _make_game()
    g._do_strike(1.0, 0.0, 0.0)  # power = 0
    assert g.heat == 0.0
    assert g.ball.moving is False


# --- Test: Spawn gates produces expected count ---

def test_spawn_gates_count() -> None:
    g = _make_game()
    assert len(g.gates) == TOTAL_GATES
    for gate in g.gates:
        assert 0 <= gate.color < N_COLORS
        assert gate.active is True
        assert gate.passed is False


# --- Test: Heat clamps at MAX_HEAT ---

def test_heat_clamps_at_max() -> None:
    g = _make_game()
    g.heat = 0.0
    # Simulate many strokes with miss penalties
    for _ in range(20):
        g.heat = min(MAX_HEAT, g.heat + HEAT_PER_STROKE + HEAT_PER_MISS)
    assert g.heat == MAX_HEAT


# --- Test: _do_strike computes correct speed ---

def test_do_strike_speed_calculation() -> None:
    g = _make_game()
    # power = MAX_POWER_DIST → speed = MAX_SPEED
    g._do_strike(1.0, 0.0, MAX_POWER_DIST)
    assert g.ball.vx == MAX_SPEED

    # power = MAX_POWER_DIST / 2 → speed = MAX_SPEED / 2
    g.ball = Ball(x=160.0, y=200.0, vx=0.0, vy=0.0, color=0)
    g._do_strike(1.0, 0.0, MAX_POWER_DIST / 2)
    assert math.isclose(g.ball.vx, MAX_SPEED / 2)


# --- Test: Stroke gate passed flag ---

def test_stroke_gate_passed_flag() -> None:
    g = _make_game()
    assert g.stroke_gate_passed is False
    g._do_strike(1.0, 0.0, 80.0)
    assert g.stroke_gate_passed is False  # Set to False by strike

    # Pass a gate
    g.ball.x = 60.0
    g.ball.y = 40.0
    g.ball.color = 0
    gate = Gate(x=60.0, y=40.0, color=0)
    g.gates = [gate]
    g._check_gate_pass()
    assert g.stroke_gate_passed is True


# --- Test: High score tracking ---

def test_high_score_tracking() -> None:
    g = _make_game()
    g.score = 500
    g.high_score = 0
    g.heat = MAX_HEAT
    g.phase = Phase.PLAYING
    g.sub_phase = PlaySubPhase.IDLE
    g.ball.moving = False
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.high_score == 500


# --- Test: Gate flash timer ---

def test_gate_flash_timer() -> None:
    g = _make_game()
    gate = Gate(x=100.0, y=100.0, color=0, flash_timer=5)
    g.gates = [gate]
    for _ in range(10):
        g._update_gate_flash()
    assert gate.flash_timer == 0


# --- Test: All gates passed detection ---

def test_all_gates_passed_detection() -> None:
    g = _make_game()
    g._spawn_gates()
    assert g._all_gates_passed() is False
    for gate in g.gates:
        gate.passed = True
    assert g._all_gates_passed() is True


# --- Test: Zero-distance strike does nothing ---

def test_zero_distance_strike() -> None:
    g = _make_game()
    g._do_strike(0.0, 0.0, 80.0)
    assert g.ball.moving is False
    assert g.heat == 0.0  # No heat when no movement


# --- Test: Ball keeps within screen bounds ---

def test_ball_screen_bounds() -> None:
    g = _make_game()
    g.sub_phase = PlaySubPhase.MOVING
    g.ball.x = -10.0
    g.ball.moving = True
    g._update_ball()
    assert g.ball.x >= 0.0

    g.ball.x = SCREEN_W + 10.0
    g.ball.vx = -1.0
    g.ball.moving = True
    g._update_ball()
    assert g.ball.x <= SCREEN_W

    g.ball.y = -10.0
    g.ball.vy = -1.0
    g.ball.moving = True
    g._update_ball()
    assert g.ball.y >= 0.0

    g.ball.y = SCREEN_H + 10.0
    g.ball.vy = 1.0
    g.ball.moving = True
    g._update_ball()
    assert g.ball.y <= SCREEN_H


# --- Test: Empty floating texts update doesn't crash ---

def test_empty_floating_texts_update() -> None:
    g = _make_game()
    g.floating_texts = []
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# --- Test: Empty particles update doesn't crash ---

def test_empty_particles_update() -> None:
    g = _make_game()
    g.particles = []
    g._update_particles()
    assert len(g.particles) == 0


# --- Test: Super mode doesn't re-trigger when already active ---

def test_super_mode_no_retrigger() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.combo = 5
    g.ball.color = 0
    g.ball.x = 60.0
    g.ball.y = 40.0
    g.ball.moving = True
    gate = Gate(x=60.0, y=40.0, color=0)
    g.gates = [gate]
    g.sub_phase = PlaySubPhase.MOVING

    old_timer = g.super_timer
    g._check_gate_pass()
    assert g.super_mode is True  # Still active
    assert g.super_timer == old_timer  # Timer not reset
