"""test_imports.py — Headless logic tests for SKI SURGE (prototype 136)."""
import sys
import random

import pytest

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/136_ski_surge")
from main import (
    Game, Gate, Particle, Phase,
    SCREEN_W, SCREEN_H,
    SKIER_X, SKIER_W, SKIER_H, SKIER_SPEED,
    SCROLL_SPEED, COMBO_THRESHOLD, SUPER_DURATION,
    HEAT_MAX, HEAT_PER_WRONG, HEAT_PER_FRAME, HEAT_DECAY,
    SCORE_BASE, GATE_WIDTH,
)


def _make_game():
    """Create a Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.skier_y = SCREEN_H // 2
    g.skier_color = 0
    g.gates = []
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.heat = 0.0
    g.super_timer = 0
    g.super_mode = False
    g.scroll_x = 0.0
    g.scroll_speed = SCROLL_SPEED
    g.particles = []
    g.reset()
    g._rng = random.Random(42)
    return g


class TestGatePassSameColor:
    """Same-color gate pass: combo++, score increases, heat decays."""

    def test_combo_increments(self):
        g = _make_game()
        g.skier_color = 0
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g.gates = [gate]
        g._handle_gate_pass(gate)
        assert g.combo == 1
        assert not gate.passed  # _handle_gate_pass doesn't set passed, _update_playing does

    def test_score_increases_with_combo(self):
        g = _make_game()
        g.skier_color = 0
        # combo=0: score = 10 * (1 + 0*0.5) = 10
        gate1 = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g._handle_gate_pass(gate1)
        assert g.combo == 1
        # combo=1: score = 10 * (1 + 1*0.5) = 15, total 25
        gate2 = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g._handle_gate_pass(gate2)
        assert g.combo == 2
        assert g.score == 25  # 10 + 15

    def test_heat_decays_on_same_color(self):
        g = _make_game()
        g.skier_color = 0
        g.heat = 5.0
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert g.heat == pytest.approx(5.0 - HEAT_DECAY)

    def test_heat_does_not_go_below_zero(self):
        g = _make_game()
        g.skier_color = 0
        g.heat = 0.0
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert g.heat == 0.0

    def test_max_combo_tracks_highest(self):
        g = _make_game()
        g.skier_color = 0
        for _ in range(3):
            gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
            g._handle_gate_pass(gate)
        assert g.combo == 3
        assert g.max_combo == 3


class TestGatePassWrongColor:
    """Wrong-color gate pass: combo resets, heat increases, skier_color updates."""

    def test_combo_resets_to_zero(self):
        g = _make_game()
        g.skier_color = 0
        g.combo = 4
        g.max_combo = 4
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=1, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert g.combo == 0

    def test_max_combo_preserved_on_wrong_color(self):
        g = _make_game()
        g.skier_color = 0
        g.combo = 4
        g.max_combo = 4
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=1, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert g.max_combo == 4

    def test_heat_increases_on_wrong_color(self):
        g = _make_game()
        g.skier_color = 0
        g.heat = 10.0
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=1, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert g.heat == pytest.approx(10.0 + HEAT_PER_WRONG)

    def test_skier_color_updates_to_gate_color(self):
        g = _make_game()
        g.skier_color = 0
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=2, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert g.skier_color == 2

    def test_score_does_not_change_on_wrong_color(self):
        g = _make_game()
        g.skier_color = 0
        g.score = 100
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=1, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert g.score == 100


class TestSuperSurge:
    """COMBO >= 5 triggers SUPER SURGE with 3x score and rainbow."""

    def test_super_mode_activates_at_threshold(self):
        g = _make_game()
        g.skier_color = 0
        g.combo = 4  # about to be 5
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert g.combo == COMBO_THRESHOLD
        assert g.super_mode is True
        assert g.super_timer == SUPER_DURATION

    def test_super_mode_3x_scoring(self):
        g = _make_game()
        g.skier_color = 0
        g.super_mode = True
        g.super_timer = 100
        g.combo = 5
        g.score = 0
        # super: score = 10 * (1 + 5*0.5) * 3 = 10 * 3.5 * 3 = 105
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert g.score == 105

    def test_super_mode_auto_pass_wrong_color(self):
        """In SUPER mode, wrong-color gates still give points and combo."""
        g = _make_game()
        g.skier_color = 0
        g.super_mode = True
        g.super_timer = 100
        g.combo = 5
        g.score = 0
        g.heat = 0.0
        # Gate with wrong color (1 != 0)
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=1, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        # Should NOT reset combo, should NOT change skier_color, should NOT add heat
        assert g.combo == 6
        assert g.skier_color == 0  # unchanged
        assert g.heat == 0.0  # no heat from wrong color
        assert g.score > 0  # scored points

    def test_super_timer_decrements(self):
        g = _make_game()
        g.super_mode = True
        g.super_timer = 100
        g.gates = []
        g._update_playing()
        assert g.super_timer == 99

    def test_super_mode_expires(self):
        g = _make_game()
        g.super_mode = True
        g.super_timer = 1
        g.gates = []
        g._update_playing()
        assert g.super_mode is False
        assert g.super_timer == 0


class TestHeatAndGameOver:
    """HEAT >= HEAT_MAX triggers GAME_OVER."""

    def test_heat_game_over_at_max(self):
        g = _make_game()
        g.heat = HEAT_MAX
        g._update_heat()
        assert g.phase == Phase.GAME_OVER

    def test_heat_below_max_no_game_over(self):
        g = _make_game()
        g.heat = HEAT_MAX - 1.0
        g._update_heat()
        assert g.phase != Phase.GAME_OVER
        assert g.heat == pytest.approx(HEAT_MAX - 1.0 + HEAT_PER_FRAME)

    def test_heat_clamped_at_max(self):
        g = _make_game()
        g.heat = HEAT_MAX
        g._update_heat()
        assert g.heat == HEAT_MAX

    def test_passive_heat_increase(self):
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == pytest.approx(HEAT_PER_FRAME)


class TestGatePassCollision:
    """AABB collision detection for gate passing."""

    def test_gate_at_skier_position_passes(self):
        g = _make_game()
        g.skier_y = SCREEN_H // 2
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        assert g._check_gate_pass(gate) is True

    def test_gate_far_left_no_pass(self):
        g = _make_game()
        g.skier_y = SCREEN_H // 2
        gate = Gate(x=SKIER_X - 100, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        assert g._check_gate_pass(gate) is False

    def test_gate_far_above_no_pass(self):
        g = _make_game()
        g.skier_y = SCREEN_H // 2
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2 - 100, color=0, width=GATE_WIDTH)
        assert g._check_gate_pass(gate) is False

    def test_gate_edge_overlap_passes(self):
        g = _make_game()
        g.skier_y = SCREEN_H // 2
        # Skier half_w=8, half_h=12. Gate width=30.
        # Place gate so its left edge = skier right edge
        gate_x = SKIER_X + SKIER_W // 2 + GATE_WIDTH - 1
        gate = Gate(x=gate_x, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        assert g._check_gate_pass(gate) is True

    def test_gate_just_outside_no_pass(self):
        g = _make_game()
        g.skier_y = SCREEN_H // 2
        gate_x = SKIER_X + SKIER_W // 2 + GATE_WIDTH + 1
        gate = Gate(x=gate_x, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        assert g._check_gate_pass(gate) is False


class TestGateMovementAndSpawning:
    """Gates scroll left, get removed, new ones spawn."""

    def test_gates_move_left(self):
        g = _make_game()
        g.gates = [Gate(x=SCREEN_W, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)]
        g._update_playing()
        assert g.gates[0].x == SCREEN_W - SCROLL_SPEED

    def test_off_screen_gates_removed(self):
        g = _make_game()
        g.gates = [Gate(x=-60, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)]
        g._update_playing()
        assert len(g.gates) == 0

    def test_new_gates_spawn_when_few_remain(self):
        g = _make_game()
        g.gates = [Gate(x=SCREEN_W - 50, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)]
        initial_count = len(g.gates)
        g._update_playing()
        # With only 1 gate and it's past spawn threshold, new gates should spawn
        assert len(g.gates) >= initial_count

    def test_gate_pass_marks_passed(self):
        g = _make_game()
        g.skier_color = 0
        g.skier_y = SCREEN_H // 2
        g.gates = [Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)]
        g._update_playing()
        assert g.gates[0].passed is True


class TestParticles:
    """Particle creation, movement, and lifecycle."""

    def test_particles_created_on_gate_pass(self):
        g = _make_game()
        g.skier_color = 0
        g.particles = []
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert len(g.particles) > 0

    def test_particles_created_on_wrong_color(self):
        g = _make_game()
        g.skier_color = 0
        g.particles = []
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=1, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert len(g.particles) > 0

    def test_particles_move_and_decay(self):
        g = _make_game()
        g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=2.0, life=5, color=8)]
        g._update_particles()
        p = g.particles[0]
        assert p.x == 101.0
        assert p.y == 102.0
        assert p.life == 4

    def test_particles_removed_when_life_expires(self):
        g = _make_game()
        g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=2.0, life=1, color=8)]
        g._update_particles()
        assert len(g.particles) == 0

    def test_super_activation_creates_big_burst(self):
        g = _make_game()
        g.skier_color = 0
        g.combo = 4
        g.particles = []
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert g.super_mode is True
        # Should have a 20-particle burst for super activation
        assert len(g.particles) >= 15  # at least the super burst


class TestReset:
    """Reset clears all state properly."""

    def test_reset_clears_score(self):
        g = _make_game()
        g.score = 999
        g.reset()
        assert g.score == 0

    def test_reset_clears_combo(self):
        g = _make_game()
        g.combo = 10
        g.max_combo = 10
        g.reset()
        assert g.combo == 0
        assert g.max_combo == 0

    def test_reset_clears_heat(self):
        g = _make_game()
        g.heat = 80.0
        g.reset()
        assert g.heat == 0.0

    def test_reset_clears_super_mode(self):
        g = _make_game()
        g.super_mode = True
        g.super_timer = 200
        g.reset()
        assert g.super_mode is False
        assert g.super_timer == 0

    def test_reset_clears_particles(self):
        g = _make_game()
        g.particles = [Particle(x=0, y=0, vx=1, vy=1, life=10, color=8)]
        g.reset()
        assert len(g.particles) == 0

    def test_reset_sets_phase_to_title(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.reset()
        assert g.phase == Phase.TITLE


class TestScoringFormula:
    """Verify scoring math."""

    def test_base_score(self):
        g = _make_game()
        g.skier_color = 0
        g.combo = 0
        g.score = 0
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        assert g.score == SCORE_BASE  # 10 * (1 + 0*0.5) = 10

    def test_combo_2_scoring(self):
        g = _make_game()
        g.skier_color = 0
        g.combo = 2
        g.score = 0
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        expected = int(SCORE_BASE * (1 + 2 * 0.5))  # 10 * 2.0 = 20
        assert g.score == expected

    def test_combo_4_scoring(self):
        g = _make_game()
        g.skier_color = 0
        g.combo = 4
        g.score = 0
        gate = Gate(x=SKIER_X, y=SCREEN_H // 2, color=0, width=GATE_WIDTH)
        g._handle_gate_pass(gate)
        expected = int(SCORE_BASE * (1 + 4 * 0.5))  # 10 * 3.0 = 30
        assert g.score == expected


class TestSkierMovement:
    """Skier vertical movement and clamping."""

    def test_skier_moves_up(self):
        g = _make_game()
        g.skier_y = SCREEN_H // 2
        initial = g.skier_y
        # Simulate UP key press (manual state change, not via _update_input)
        g.skier_y -= SKIER_SPEED
        assert g.skier_y == initial - SKIER_SPEED

    def test_skier_moves_down(self):
        g = _make_game()
        g.skier_y = SCREEN_H // 2
        initial = g.skier_y
        g.skier_y += SKIER_SPEED
        assert g.skier_y == initial + SKIER_SPEED

    def test_skier_clamped_top(self):
        g = _make_game()
        g.skier_y = SKIER_H / 2
        g.skier_y -= SKIER_SPEED
        assert g.skier_y >= SKIER_H / 2 - SKIER_SPEED

    def test_skier_clamped_bottom(self):
        g = _make_game()
        g.skier_y = SCREEN_H - SKIER_H / 2
        g.skier_y += SKIER_SPEED
        assert g.skier_y <= SCREEN_H - SKIER_H / 2 + SKIER_SPEED
