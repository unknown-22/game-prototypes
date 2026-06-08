"""test_imports.py — Headless logic tests for Slope Surge.

Tests core mechanics: gate passing, combo chaining, SUPER MODE,
heat system, obstacle collision, particle spawning, ghost trail.
"""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/110_slope_surge")
from main import (
    Game, Gate, Obstacle, Particle, FloatingText, GhostPoint, Phase,
    PLAYER_MIN_X, PLAYER_MAX_X, PLAYER_MOVE_SPEED,
    BASE_SCROLL_SPEED, MAX_SCROLL_SPEED, SCROLL_SPEED_INCREMENT, SCROLL_SPEED_INTERVAL,
    GATE_COLORS, GATE_BASE_SCORE, GATE_SPAWN_Y, GATE_OFFSCREEN_Y,
    HEAT_MAX, HEAT_PER_MISS, HEAT_DECAY, HEAT_PER_OBSTACLE,
    SUPER_DURATION, MAX_GATES, MAX_OBSTACLES, MAX_GHOST_POINTS, PLAYER_Y, PLAYER_W, PLAYER_H,
    RED, GREEN, YELLOW, BROWN, GRAY, WHITE,
    OBSTACLE_W, OBSTACLE_H,
)


def _make_game(seed: int = 42) -> Game:
    """Factory: create a Game instance bypassing Pyxel init."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.scroll_speed = BASE_SCROLL_SPEED
    g.player_x = 160.0
    g.player_y = float(PLAYER_Y)
    g.player_w = PLAYER_W
    g.player_h = PLAYER_H
    g.last_gate_color = None
    g.gates = []
    g.obstacles = []
    g.particles = []
    g.floating_texts = []
    g.ghost_trail = []
    g.best_ghost = []
    g.best_score = 0
    g.game_timer = 0
    g._gate_spawn_timer = 0
    g._obstacle_spawn_timer = 0
    g._ghost_record_timer = 0
    g._rainbow_idx = 0
    g.reset()
    return g


# ── Dataclass Tests ──

def test_gate_defaults():
    g = Gate(x=100, y=200, color=RED, width=50)
    assert g.x == 100
    assert g.y == 200
    assert g.color == RED
    assert g.width == 50
    assert g.passed is False
    assert g.pole_w == 6


def test_obstacle_fields():
    o = Obstacle(x=50, y=100, w=16, h=24, color=BROWN)
    assert o.w == 16
    assert o.h == 24
    assert o.color == BROWN


def test_particle_fields():
    p = Particle(x=10, y=20, vx=1.5, vy=-2.0, life=30, color=RED)
    assert p.life == 30
    assert p.size == 2


def test_floating_text_fields():
    ft = FloatingText(x=100, y=50, text="+10", life=30, color=YELLOW)
    assert ft.text == "+10"
    assert ft.life == 30


def test_ghost_point_fields():
    gp = GhostPoint(x=160, y=160)
    assert gp.x == 160
    assert gp.y == 160


# ── Phase Enum Tests ──

def test_phase_values():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Gate Spawning ──

def test_spawn_gate():
    g = _make_game()
    g._spawn_gate()
    assert len(g.gates) == 1
    gate = g.gates[0]
    assert gate.y == GATE_SPAWN_Y
    assert gate.color in GATE_COLORS
    assert 40 <= gate.width <= 70
    assert gate.passed is False


def test_spawn_gate_max_limit():
    g = _make_game()
    for _ in range(10):
        g._spawn_gate()
    assert len(g.gates) == MAX_GATES


def test_spawn_gate_uses_rng():
    g1 = _make_game(42)
    g2 = _make_game(42)
    for _ in range(5):
        g1._spawn_gate()
        g2._spawn_gate()
    for i in range(5):
        assert g1.gates[i].x == g2.gates[i].x
        assert g1.gates[i].color == g2.gates[i].color
        assert g1.gates[i].width == g2.gates[i].width


# ── Obstacle Spawning ──

def test_spawn_obstacle():
    g = _make_game()
    g._spawn_obstacle()
    assert len(g.obstacles) == 1
    obs = g.obstacles[0]
    assert obs.y == GATE_SPAWN_Y
    assert obs.color in (BROWN, GRAY)
    assert obs.w == OBSTACLE_W
    assert obs.h == OBSTACLE_H


def test_spawn_obstacle_max_limit():
    g = _make_game()
    for _ in range(10):
        g._spawn_obstacle()
    assert len(g.obstacles) == MAX_OBSTACLES


# ── Gate Pass Detection ──

def test_check_gate_pass_centered():
    g = _make_game()
    g.player_x = 160
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g.gates = [gate]
    assert g._check_gate_pass(gate) is True


def test_check_gate_pass_off_center():
    g = _make_game()
    g.player_x = 160
    gate = Gate(x=200, y=PLAYER_Y, color=RED, width=60)
    g.gates = [gate]
    # distance = 40, width/2 = 30 → missed
    assert g._check_gate_pass(gate) is False


def test_check_gate_pass_already_passed():
    g = _make_game()
    g.player_x = 160
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60, passed=True)
    g.gates = [gate]
    assert g._check_gate_pass(gate) is False


def test_check_gate_pass_not_crossed_yet():
    g = _make_game()
    g.player_x = 160
    gate = Gate(x=160, y=200, color=RED, width=60)  # above player
    g.gates = [gate]
    assert g._check_gate_pass(gate) is False


# ── Gate Pass Handling ──

def test_handle_gate_pass_first_gate():
    g = _make_game()
    g.last_gate_color = None
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g._handle_gate_pass(gate)
    assert gate.passed is True
    assert g.combo == 1
    assert g.last_gate_color == RED
    assert g.score == GATE_BASE_SCORE


def test_handle_gate_pass_same_color_combo():
    g = _make_game()
    g.last_gate_color = RED
    g.combo = 2
    g.score = 50
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g._handle_gate_pass(gate)
    assert g.combo == 3
    # score_gain = 10 * (3 + 1) = 40
    assert g.score == 50 + 40


def test_handle_gate_pass_different_color_reset():
    g = _make_game()
    g.last_gate_color = RED
    g.combo = 4
    g.score = 100
    gate = Gate(x=160, y=PLAYER_Y, color=GREEN, width=60)
    g._handle_gate_pass(gate)
    assert g.combo == 1
    assert g.last_gate_color == GREEN
    # score_gain = 10 (base)
    assert g.score == 100 + GATE_BASE_SCORE


def test_handle_gate_pass_triggers_super():
    g = _make_game()
    g.last_gate_color = RED
    g.combo = 4  # next same-color will be combo=5
    g.super_mode = False
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g._handle_gate_pass(gate)
    assert g.combo == 5
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_handle_gate_pass_super_multiplier():
    g = _make_game()
    g.last_gate_color = RED
    g.combo = 1
    g.super_mode = True
    g.super_timer = 100
    g.score = 100
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g._handle_gate_pass(gate)
    # score_gain = 10 * (2 + 1) * 3 = 90
    assert g.score == 190


def test_handle_gate_pass_max_combo_tracks():
    g = _make_game()
    g.last_gate_color = RED
    g.combo = 3
    g.max_combo = 3
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g._handle_gate_pass(gate)
    assert g.combo == 4
    assert g.max_combo == 4


def test_handle_gate_pass_spawns_particles():
    g = _make_game()
    g.last_gate_color = RED
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    initial_particles = len(g.particles)
    g._handle_gate_pass(gate)
    assert len(g.particles) > initial_particles


def test_handle_gate_pass_spawns_floating_text():
    g = _make_game()
    g.last_gate_color = RED
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    initial_texts = len(g.floating_texts)
    g._handle_gate_pass(gate)
    assert len(g.floating_texts) > initial_texts


# ── Gate Miss ──

def test_handle_gate_miss_increases_heat():
    g = _make_game()
    g.heat = 1.0
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g._handle_gate_miss(gate)
    assert g.heat == min(HEAT_MAX, 1.0 + HEAT_PER_MISS)
    assert g.combo == 0
    assert g.last_gate_color is None
    assert gate.passed is True


def test_handle_gate_miss_deactivates_super():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.combo = 5
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g._handle_gate_miss(gate)
    assert g.super_mode is False
    assert g.combo == 0


def test_handle_gate_miss_clamps_heat():
    g = _make_game()
    g.heat = HEAT_MAX
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g._handle_gate_miss(gate)
    assert g.heat == HEAT_MAX  # clamped


# ── Obstacle Collision ──

def test_check_obstacle_collision_hit():
    g = _make_game()
    g.player_x = 100
    obs = Obstacle(x=95, y=PLAYER_Y, w=16, h=24, color=BROWN)
    assert g._check_obstacle_collision(obs) is True


def test_check_obstacle_collision_miss_left():
    g = _make_game()
    g.player_x = 100
    obs = Obstacle(x=140, y=PLAYER_Y, w=16, h=24, color=BROWN)
    assert g._check_obstacle_collision(obs) is False


def test_handle_obstacle_collision_adds_heat():
    g = _make_game()
    g.heat = 0.5
    obs = Obstacle(x=95, y=PLAYER_Y, w=16, h=24, color=BROWN)
    g._handle_obstacle_collision(obs)
    assert g.heat == min(HEAT_MAX, 0.5 + HEAT_PER_OBSTACLE)
    assert g.combo == 0
    assert g.last_gate_color is None


def test_handle_obstacle_collision_super_ignored():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.heat = 0.5
    g.combo = 5
    obs = Obstacle(x=95, y=PLAYER_Y, w=16, h=24, color=BROWN)
    g._handle_obstacle_collision(obs)
    assert g.heat == 0.5  # unchanged
    assert g.combo == 5  # unchanged


# ── Super Mode ──

def test_activate_super():
    g = _make_game()
    g._activate_super()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_deactivate_super():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 50
    g.combo = 5
    g.last_gate_color = RED
    g._deactivate_super()
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.combo == 0
    assert g.last_gate_color is None


# ── Heat System ──

def test_update_heat_decay():
    g = _make_game()
    g.heat = 2.0
    g._update_heat()
    assert g.heat == max(0.0, 2.0 - HEAT_DECAY)


def test_update_heat_no_decay_in_super():
    g = _make_game()
    g.super_mode = True
    g.heat = 2.0
    g._update_heat()
    assert g.heat == 2.0  # unchanged in super


def test_update_heat_game_over():
    g = _make_game()
    g.heat = HEAT_MAX
    g.phase = Phase.PLAYING
    g.score = 500
    g.best_score = 300
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500  # updated


def test_update_heat_game_over_preserves_best():
    g = _make_game()
    g.heat = HEAT_MAX
    g.phase = Phase.PLAYING
    g.score = 200
    g.best_score = 500
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500  # not overwritten


def test_update_heat_threshold_before_decay():
    """Heat threshold check runs BEFORE decay — prevents unreachable condition."""
    g = _make_game()
    g.heat = HEAT_MAX  # exactly at threshold
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER  # should trigger, not decay


# ── Gate Scrolling ──

def test_update_gates_scrolls_down():
    g = _make_game()
    g.scroll_speed = 2.0
    gate = Gate(x=160, y=200, color=RED, width=60)
    g.gates = [gate]
    g._update_gates()
    assert gate.y == 198.0


def test_update_gates_cleanup_offscreen():
    g = _make_game()
    gate = Gate(x=160, y=GATE_OFFSCREEN_Y - 1, color=RED, width=60)
    g.gates = [gate]
    g._update_gates()
    assert len(g.gates) == 0


# ── Obstacle Scrolling ──

def test_update_obstacles_scrolls():
    g = _make_game()
    g.scroll_speed = 2.0
    obs = Obstacle(x=100, y=200, w=16, h=24, color=BROWN)
    g.obstacles = [obs]
    g._update_obstacles()
    assert obs.y == 198.0


def test_update_obstacles_cleanup_offscreen():
    g = _make_game()
    obs = Obstacle(x=100, y=GATE_OFFSCREEN_Y - 1, w=16, h=24, color=BROWN)
    g.obstacles = [obs]
    g._update_obstacles()
    assert len(g.obstacles) == 0


# ── Particle System ──

def test_update_particles_moves():
    g = _make_game()
    p = Particle(x=100, y=100, vx=2.0, vy=-1.0, life=10, color=RED)
    g.particles = [p]
    g._update_particles()
    assert p.x == 102.0
    assert p.y == 99.0
    assert p.life == 9


def test_update_particles_cleanup_dead():
    g = _make_game()
    p1 = Particle(x=100, y=100, vx=0, vy=0, life=1, color=RED)
    p2 = Particle(x=200, y=100, vx=0, vy=0, life=5, color=GREEN)
    g.particles = [p1, p2]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].color == GREEN


# ── Floating Text ──

def test_update_floating_texts_moves():
    g = _make_game()
    ft = FloatingText(x=100, y=100, text="TEST", life=10, color=WHITE)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert ft.y == 99.0  # moves up
    assert ft.life == 9


def test_update_floating_texts_cleanup_dead():
    g = _make_game()
    ft = FloatingText(x=100, y=100, text="DEAD", life=1, color=WHITE)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Ghost Trail ──

def test_record_ghost_point():
    g = _make_game()
    g.player_x = 150
    g._record_ghost_point()
    assert len(g.ghost_trail) == 1
    assert g.ghost_trail[0].x == 150
    assert g.ghost_trail[0].y == PLAYER_Y


def test_record_ghost_max_limit():
    g = _make_game()
    for _ in range(MAX_GHOST_POINTS + 10):
        g._record_ghost_point()
    assert len(g.ghost_trail) == MAX_GHOST_POINTS


# ── Scroll Speed ──

def test_update_scroll_speed_base():
    g = _make_game()
    g.game_timer = 0
    g._update_scroll_speed()
    assert g.scroll_speed == BASE_SCROLL_SPEED


def test_update_scroll_speed_increases():
    g = _make_game()
    g.game_timer = SCROLL_SPEED_INTERVAL * 2  # 1200
    g._update_scroll_speed()
    assert g.scroll_speed == BASE_SCROLL_SPEED + 2 * SCROLL_SPEED_INCREMENT


def test_update_scroll_speed_capped():
    g = _make_game()
    g.game_timer = SCROLL_SPEED_INTERVAL * 20  # way past cap
    g._update_scroll_speed()
    assert g.scroll_speed == MAX_SCROLL_SPEED


# ── Spawning Timer ──

def test_update_spawning_creates_gate():
    g = _make_game()
    g._gate_spawn_timer = 1
    initial_gates = len(g.gates)
    g._update_spawning()
    assert len(g.gates) == initial_gates + 1
    assert g._gate_spawn_timer > 0  # reset


def test_update_spawning_creates_obstacle():
    g = _make_game()
    g._obstacle_spawn_timer = 1
    initial_obs = len(g.obstacles)
    g._update_spawning()
    assert len(g.obstacles) == initial_obs + 1
    assert g._obstacle_spawn_timer > 0  # reset


# ── Reset ──

def test_reset_clears_state():
    g = _make_game()
    g.score = 500
    g.combo = 4
    g.heat = 3.0
    g.super_mode = True
    g.player_x = 200
    g.last_gate_color = RED
    g.gates = [Gate(x=100, y=200, color=RED, width=50)]
    g.obstacles = [Obstacle(x=100, y=200, w=16, h=24, color=BROWN)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=10, color=RED)]
    g.floating_texts = [FloatingText(x=0, y=0, text="X", life=10, color=WHITE)]
    g.ghost_trail = [GhostPoint(x=0, y=0)]
    g.game_timer = 300

    g.reset()

    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.scroll_speed == BASE_SCROLL_SPEED
    assert g.player_x == 160.0
    assert g.last_gate_color is None
    assert len(g.gates) == 0
    assert len(g.obstacles) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.ghost_trail) == 0
    assert g.game_timer == 0
    assert g._gate_spawn_timer == 0
    assert g._obstacle_spawn_timer == 0
    assert g._ghost_record_timer == 0
    assert g._rainbow_idx == 0


# ── Player Movement (simulated) ──

def test_player_move_left():
    g = _make_game()
    g.player_x = 160
    # simulate: pyxel.btn(KEY_LEFT) → movement
    g.player_x -= PLAYER_MOVE_SPEED
    g.player_x = max(PLAYER_MIN_X, min(PLAYER_MAX_X, g.player_x))
    assert g.player_x == 157.0


def test_player_move_right():
    g = _make_game()
    g.player_x = 160
    # simulate: pyxel.btn(KEY_RIGHT) → movement
    g.player_x += PLAYER_MOVE_SPEED
    g.player_x = max(PLAYER_MIN_X, min(PLAYER_MAX_X, g.player_x))
    assert g.player_x == 163.0


def test_player_clamped_min():
    g = _make_game()
    g.player_x = 5
    g.player_x = max(PLAYER_MIN_X, min(PLAYER_MAX_X, g.player_x))
    assert g.player_x == PLAYER_MIN_X


def test_player_clamped_max():
    g = _make_game()
    g.player_x = 350
    g.player_x = max(PLAYER_MIN_X, min(PLAYER_MAX_X, g.player_x))
    assert g.player_x == PLAYER_MAX_X


# ── Super Timer Expiry ──

def test_super_timer_decrements():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 10
    # simulate update loop's super timer decrement
    g.super_timer -= 1
    if g.super_timer <= 0:
        g._deactivate_super()
    assert g.super_timer == 9
    assert g.super_mode is True


def test_super_timer_expiry():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g.super_timer -= 1
    if g.super_timer <= 0:
        g._deactivate_super()
    assert g.super_timer == 0
    assert g.super_mode is False


# ── Gate Pass + Super Auto-Pass ──

def test_super_mode_auto_passes_any_color():
    """In SUPER MODE, any gate that crosses the player zone auto-passes
    (no x-position check). But color matching for combo still applies."""
    g = _make_game()
    g.super_mode = True
    g.last_gate_color = RED
    g.combo = 5
    g.score = 100
    gate = Gate(x=200, y=PLAYER_Y, color=GREEN, width=60)  # different color, off-center
    g.gates = [gate]
    # In super mode, _update_gates auto-passes any crossed gate
    # Simulate: gate crossed threshold, auto-pass
    player_top = PLAYER_Y - PLAYER_H / 2
    player_bottom = PLAYER_Y + PLAYER_H / 2
    crossed = player_bottom >= gate.y and player_top < gate.y
    if crossed:
        g._handle_gate_pass(gate)
    assert gate.passed is True
    # Different color resets combo (even in super mode)
    assert g.combo == 1
    assert g.last_gate_color == GREEN


# ── Edge Cases ──

def test_gate_very_wide_always_pass():
    g = _make_game()
    g.player_x = PLAYER_MIN_X  # far left
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=300)
    g.gates = [gate]
    assert g._check_gate_pass(gate) is True


def test_multiple_gates_same_frame():
    g = _make_game()
    g.player_x = 160
    g.last_gate_color = RED
    g1 = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g2 = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g.gates = [g1, g2]
    g._update_gates()
    assert g1.passed is True
    assert g2.passed is True


def test_obstacle_knockback_direction():
    """Player to the right of obstacle center gets knocked left (through obstacle)."""
    g = _make_game()
    g.player_x = 100
    obs = Obstacle(x=90, y=PLAYER_Y, w=16, h=24, color=BROWN)
    g._handle_obstacle_collision(obs)
    # player at 100, obstacle center at 98, player is RIGHT of center
    # → knock_dir=-1 → pushes LEFT to 90 (past obstacle)
    assert g.player_x == 90


def test_obstacle_knockback_clamped():
    g = _make_game()
    g.player_x = PLAYER_MAX_X - 2
    obs = Obstacle(x=PLAYER_MAX_X - 5, y=PLAYER_Y, w=16, h=24, color=BROWN)
    g._handle_obstacle_collision(obs)
    assert g.player_x <= PLAYER_MAX_X


def test_super_activation_from_combo_4_to_5():
    g = _make_game()
    g.last_gate_color = RED
    g.combo = 4
    g.super_mode = False
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g._handle_gate_pass(gate)
    assert g.combo == 5
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_combo_text_appears():
    g = _make_game()
    g.last_gate_color = RED
    g.combo = 2  # next pass = combo 3 → text should appear
    gate = Gate(x=160, y=PLAYER_Y, color=RED, width=60)
    g._handle_gate_pass(gate)
    # should have at least 2 floating texts: score + combo
    assert len(g.floating_texts) >= 2


if __name__ == "__main__":
    import pytest

    # Run all tests in this module
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)
