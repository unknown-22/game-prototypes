"""test_imports.py — Headless logic tests for CHROMA BOARD."""
import sys
import math
import random

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/196_chroma_board")
from main import (
    SCREEN_W, SCREEN_H, SCROLL_SPEED, GRAVITY, JUMP_VEL,
    PLAYER_X, GROUND_Y, GATE_W, GATE_GAP, GATE_SPAWN_INTERVAL,
    COMBO_THRESHOLD, SUPER_DURATION, HEAT_MAX, HEAT_DECAY,
    HEAT_PER_SECOND, HEAT_PER_OBSTACLE, GAME_TIME,
    OBSTACLE_SPAWN_INTERVAL, MAX_PARTICLES,
    RED, GREEN, BLUE, YELLOW,
    Phase, Gate, Obstacle, Particle, FloatText, Player, Game,
)


def _make_game(seed: int = 42) -> Game:
    """Factory: headless Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    g._pre_init_attrs()
    g.random = random.Random(seed)
    g.reset()
    g.frame = 0
    g.best_score = 0
    g.best_max_combo = 0
    g.ghost_gates = []
    return g


# ── Dataclass tests ──

def test_player_defaults():
    p = Player()
    assert p.x == float(PLAYER_X)
    assert p.y == float(GROUND_Y)
    assert p.vy == 0.0
    assert p.on_ground is True
    assert p.color == -1
    assert p.combo == 0
    assert p.max_combo == 0
    assert p.super_timer == 0
    assert p.heat == 0.0


def test_gate_creation():
    g = Gate(x=320.0, y=150.0, color=RED)
    assert g.x == 320.0
    assert g.y == 150.0
    assert g.color == RED
    assert g.scored is False


def test_obstacle_creation():
    o = Obstacle(x=300.0, y=180.0, w=16, h=12, obs_type="rock")
    assert o.x == 300.0
    assert o.y == 180.0
    assert o.w == 16
    assert o.h == 12
    assert o.obs_type == "rock"


def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, color=8, life=15)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.color == 8
    assert p.life == 15


def test_float_text_creation():
    ft = FloatText(x=100.0, y=50.0, text="+100", color=8, life=40)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+100"
    assert ft.color == 8
    assert ft.life == 40


# ── Phase enum tests ──

def test_phase_values():
    assert Phase.TITLE is not None
    assert Phase.PLAYING is not None
    assert Phase.GAME_OVER is not None


# ── Game.reset() tests ──

def test_reset_initializes_player():
    g = _make_game()
    assert g.player.x == float(PLAYER_X)
    assert g.player.y == float(GROUND_Y)
    assert g.player.combo == 0
    assert g.player.heat == 0.0
    assert g.timer == GAME_TIME
    assert g.score == 0
    assert len(g.gates) == 0
    assert len(g.obstacles) == 0
    assert len(g.particles) == 0
    assert len(g.float_texts) == 0


def test_reset_clears_previous_state():
    g = _make_game()
    g.gates.append(Gate(x=100.0, y=150.0, color=RED))
    g.score = 500
    g.player.heat = 50.0
    g.reset()
    assert len(g.gates) == 0
    assert g.score == 0
    assert g.player.heat == 0.0


# ── Spawning tests ──

def test_spawn_gate():
    g = _make_game()
    before = len(g.gates)
    g._spawn_gate()
    assert len(g.gates) == before + 1
    gate = g.gates[-1]
    assert gate.x == float(SCREEN_W + GATE_W)
    assert gate.color in (RED, GREEN, BLUE, YELLOW)
    assert gate.scored is False


def test_spawn_gate_y_in_bounds():
    g = _make_game()
    for _ in range(20):
        g._spawn_gate()
    for gate in g.gates:
        assert GATE_GAP // 2 + 10 <= gate.y <= SCREEN_H - 40


def test_spawn_obstacle():
    g = _make_game()
    before = len(g.obstacles)
    g._spawn_obstacle()
    assert len(g.obstacles) == before + 1
    obs = g.obstacles[-1]
    assert obs.x == float(SCREEN_W + obs.w)
    assert obs.obs_type in ("rock", "tree")
    assert obs.y == float(GROUND_Y - obs.h)


def test_spawn_obstacle_y_position():
    g = _make_game()
    for _ in range(10):
        g._spawn_obstacle()
    for obs in g.obstacles:
        assert abs(obs.y - (GROUND_Y - obs.h)) < 1.0


# ── Gate collision tests ──

def test_gate_collision_hit():
    g = _make_game()
    p = g.player
    p.x = 80.0
    p.y = 150.0
    gate = Gate(x=float(PLAYER_X), y=150.0, color=RED)
    assert g._check_gate_collision(p, gate) is True


def test_gate_collision_miss_vertical():
    g = _make_game()
    p = g.player
    p.x = 80.0
    p.y = 30.0  # above gap
    gate = Gate(x=float(PLAYER_X), y=150.0, color=RED)
    assert g._check_gate_collision(p, gate) is False


def test_gate_collision_miss_horizontal():
    g = _make_game()
    p = g.player
    p.x = 0.0  # far left
    p.y = 150.0
    gate = Gate(x=float(SCREEN_W), y=150.0, color=RED)
    assert g._check_gate_collision(p, gate) is False


# ── Obstacle collision tests ──

def test_obstacle_collision_hit():
    g = _make_game()
    p = g.player
    p.x = 80.0
    p.y = GROUND_Y - 10
    obs = Obstacle(x=80.0, y=float(GROUND_Y - 15), w=20, h=15, obs_type="rock")
    assert g._check_obstacle_collision(p, obs) is True


def test_obstacle_collision_miss():
    g = _make_game()
    p = g.player
    p.x = 80.0
    p.y = GROUND_Y - 10
    obs = Obstacle(x=200.0, y=float(GROUND_Y - 15), w=20, h=15, obs_type="rock")
    assert g._check_obstacle_collision(p, obs) is False


def test_obstacle_collision_super_mode_immune():
    g = _make_game()
    p = g.player
    p.x = 80.0
    p.y = GROUND_Y - 10
    p.super_timer = 100  # super active
    obs = Obstacle(x=80.0, y=float(GROUND_Y - 15), w=20, h=15, obs_type="rock")
    # _check_obstacle_collision returns False in super mode
    assert g._check_obstacle_collision(p, obs) is False


# ── Gate pass processing tests ──

def test_process_gate_pass_first_gate():
    g = _make_game()
    gate = Gate(x=100.0, y=150.0, color=RED)
    g._process_gate_pass(gate)
    assert g.player.combo == 1
    assert g.player.color == RED
    assert g.player.max_combo == 1
    assert g.score > 0


def test_process_gate_pass_same_color_combo():
    g = _make_game()
    g.player.color = RED
    g.player.combo = 2
    g.player.max_combo = 2
    gate = Gate(x=100.0, y=150.0, color=RED)
    g._process_gate_pass(gate)
    assert g.player.combo == 3
    assert g.player.max_combo == 3


def test_process_gate_pass_different_color_reset():
    g = _make_game()
    g.player.color = RED
    g.player.combo = 3
    g.player.max_combo = 3
    gate = Gate(x=100.0, y=150.0, color=GREEN)
    g._process_gate_pass(gate)
    assert g.player.combo == 0
    assert g.player.color == GREEN
    assert g.player.max_combo == 3  # max_combo preserved


def test_process_gate_pass_triggers_super():
    g = _make_game()
    g.player.color = RED
    g.player.combo = COMBO_THRESHOLD - 1  # 3
    gate = Gate(x=100.0, y=150.0, color=RED)
    g._process_gate_pass(gate)
    assert g.player.combo == COMBO_THRESHOLD  # 4
    assert g.player.super_timer == SUPER_DURATION


def test_process_gate_pass_super_no_reset():
    g = _make_game()
    g.player.super_timer = 100
    g.player.color = RED
    g.player.combo = 5
    gate = Gate(x=100.0, y=150.0, color=GREEN)  # different color
    g._process_gate_pass(gate)
    assert g.player.combo == 6  # still incremented in super mode
    assert g.player.super_timer == 100  # super not re-triggered


def test_process_gate_pass_super_multiplier():
    g = _make_game()
    g.player.super_timer = 100
    g.player.combo = 5
    gate = Gate(x=100.0, y=150.0, color=RED)
    score_before = g.score
    g._process_gate_pass(gate)
    score_added = g.score - score_before
    # 3x multiplier: 100 * combo(6) * 3 = 1800
    assert score_added == 1800


def test_process_gate_pass_spawns_float_text():
    g = _make_game()
    gate = Gate(x=100.0, y=150.0, color=RED)
    before = len(g.float_texts)
    g._process_gate_pass(gate)
    assert len(g.float_texts) > before


def test_process_gate_pass_spawns_particles():
    g = _make_game()
    gate = Gate(x=100.0, y=150.0, color=RED)
    before = len(g.particles)
    g._process_gate_pass(gate)
    assert len(g.particles) > before


# ── Obstacle hit processing tests ──

def test_process_obstacle_hit_normal():
    g = _make_game()
    obs = Obstacle(x=100.0, y=float(GROUND_Y - 15), w=20, h=15, obs_type="rock")
    g._process_obstacle_hit(obs)
    assert g.player.heat == HEAT_PER_OBSTACLE
    assert g.player.on_ground is False  # knocked back


def test_process_obstacle_hit_super_smash():
    g = _make_game()
    g.player.super_timer = 100
    g.obstacles.append(Obstacle(x=100.0, y=float(GROUND_Y - 15), w=20, h=15, obs_type="rock"))
    obs = g.obstacles[0]
    score_before = g.score
    g._process_obstacle_hit(obs)
    assert g.score == score_before + 50
    assert g.player.heat == 0.0  # no heat gain in super


# ── Heat system tests ──

def test_heat_increases_per_frame():
    g = _make_game()
    g._update_heat()
    assert g.player.heat > 0.0


def test_heat_clamped_above_zero():
    g = _make_game()
    g.player.heat = -1.0
    g._update_heat()
    assert g.player.heat >= 0.0


def test_heat_game_over_at_max():
    g = _make_game()
    g.player.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_game_over_at_above_max():
    g = _make_game()
    g.player.heat = HEAT_MAX + 10
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


# ── Super mode tests ──

def test_super_timer_decrements():
    g = _make_game()
    g.player.super_timer = 100
    g._update_super()
    assert g.player.super_timer == 99


def test_super_ends_resets_combo():
    g = _make_game()
    g.player.super_timer = 1
    g.player.combo = 10
    g._update_super()
    assert g.player.super_timer == 0
    assert g.player.combo == 0


def test_super_no_change_when_inactive():
    g = _make_game()
    g.player.super_timer = 0
    g.player.combo = 5
    g._update_super()
    assert g.player.super_timer == 0
    assert g.player.combo == 5


# ── Timer tests ──

def test_timer_decrements():
    g = _make_game()
    initial = g.timer
    g._update_timer()
    assert g.timer == initial - 1


def test_timer_game_over_at_zero():
    g = _make_game()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


# ── Position update tests ──

def test_update_positions_scrolls_gates():
    g = _make_game()
    g.gates.append(Gate(x=300.0, y=150.0, color=RED))
    g.gates.append(Gate(x=400.0, y=150.0, color=GREEN))
    g._update_positions()
    assert g.gates[0].x < 300.0
    assert g.gates[1].x < 400.0


def test_update_positions_removes_offscreen_gates():
    g = _make_game()
    g.gates.append(Gate(x=-100.0, y=150.0, color=RED))  # way offscreen
    g._update_positions()
    assert len(g.gates) == 0


def test_update_positions_removes_offscreen_obstacles():
    g = _make_game()
    g.obstacles.append(Obstacle(x=-100.0, y=180.0, w=20, h=12, obs_type="rock"))
    g._update_positions()
    assert len(g.obstacles) == 0


# ── Spawning update tests ──

def test_update_spawning_creates_gate():
    g = _make_game()
    g.gate_spawn_timer = 0
    g._update_spawning()
    assert len(g.gates) == 1
    assert g.gate_spawn_timer == GATE_SPAWN_INTERVAL  # reset


def test_update_spawning_creates_obstacle():
    g = _make_game()
    g.obstacle_spawn_timer = 0
    g._update_spawning()
    assert len(g.obstacles) == 1
    assert g.obstacle_spawn_timer == OBSTACLE_SPAWN_INTERVAL  # reset


def test_update_spawning_decrements_timers():
    g = _make_game()
    g.gate_spawn_timer = 5
    g.obstacle_spawn_timer = 5
    g._update_spawning()
    assert g.gate_spawn_timer == 4
    assert g.obstacle_spawn_timer == 4


# ── Speed update tests ──

def test_speed_increases_over_time():
    g = _make_game()
    g.timer = GAME_TIME - 1200  # 20 seconds elapsed
    g._update_speed()
    assert g.scroll_speed > SCROLL_SPEED


def test_speed_starts_at_default():
    g = _make_game()
    g.timer = GAME_TIME
    g._update_speed()
    assert g.scroll_speed == SCROLL_SPEED


# ── Particle system tests ──

def test_spawn_particles_adds_particles():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 8, 10)
    assert len(g.particles) == 10


def test_spawn_particles_respects_max():
    g = _make_game()
    # fill particle list to near max
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, color=8, life=10)] * (MAX_PARTICLES - 3)
    g._spawn_particles(100.0, 100.0, 8, 10)
    # should only add up to max
    assert len(g.particles) <= MAX_PARTICLES


def test_update_particles_moves_and_removes():
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=1.0, vy=-1.0, color=8, life=1)]
    g._update_particles()
    assert len(g.particles) == 0  # life=1 → 0 → removed


def test_update_particles_survives_with_life():
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=1.0, vy=0.0, color=8, life=3)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 2


# ── Floating text tests ──

def test_spawn_float_text():
    g = _make_game()
    g._spawn_float_text(100.0, 100.0, "TEST", 7)
    assert len(g.float_texts) == 1
    assert g.float_texts[0].text == "TEST"
    assert g.float_texts[0].life == 40


def test_update_floating_texts_removes_dead():
    g = _make_game()
    g.float_texts = [FloatText(x=0.0, y=0.0, text="T", color=7, life=1)]
    g._update_floating_texts()
    assert len(g.float_texts) == 0


def test_update_floating_texts_survives():
    g = _make_game()
    g.float_texts = [FloatText(x=0.0, y=0.0, text="T", color=7, life=5)]
    g._update_floating_texts()
    assert len(g.float_texts) == 1
    assert g.float_texts[0].life == 4


# ── End game tests ──

def test_end_game_sets_phase():
    g = _make_game()
    g.score = 1000
    g.player.max_combo = 7
    g._end_game()
    assert g.phase == Phase.GAME_OVER


def test_end_game_records_best_score():
    g = _make_game()
    g.score = 1000
    g.best_score = 500
    g._end_game()
    assert g.best_score == 1000


def test_end_game_does_not_overwrite_higher_best():
    g = _make_game()
    g.score = 500
    g.best_score = 1000
    g._end_game()
    assert g.best_score == 1000


# ── Integration tests ──

def test_full_combo_chain():
    """Simulate a sequence of gate passes: RED→RED→RED→RED triggers SUPER."""
    g = _make_game()
    colors = [RED, RED, RED, RED]
    for i, color in enumerate(colors):
        gate = Gate(x=100.0 + i * 40, y=150.0, color=color)
        g._process_gate_pass(gate)
    assert g.player.combo == 4
    assert g.player.super_timer == SUPER_DURATION
    assert g.player.max_combo == 4


def test_combo_reset_on_wrong_color():
    """RED→RED→BLUE resets combo."""
    g = _make_game()
    for color in [RED, RED, BLUE]:
        gate = Gate(x=100.0, y=150.0, color=color)
        g._process_gate_pass(gate)
    assert g.player.combo == 0
    assert g.player.max_combo == 2


def test_heat_builds_and_kills():
    """Heat accumulates over many frames, eventually game over."""
    g = _make_game()
    g.player.heat = 99.0
    # Each frame: heat += 0.3, decays 0.05 → net +0.25 per frame
    # 99.0 → 99.25 → 99.5 → 99.75 → 100.0 (after 4 frames)
    for _ in range(4):
        g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_multiple_gate_spawns_with_timer():
    """Timer-based spawning works across multiple ticks."""
    g = _make_game()
    g.gate_spawn_timer = 0
    g._update_spawning()
    assert len(g.gates) == 1
    # Next tick: timer is GATE_SPAWN_INTERVAL (90), decrements to 89, no spawn
    g._update_spawning()
    assert len(g.gates) == 1
    # Force spawn again
    g.gate_spawn_timer = 0
    g._update_spawning()
    assert len(g.gates) == 2


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
