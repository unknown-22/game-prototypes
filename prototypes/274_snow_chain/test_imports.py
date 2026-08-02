"""test_imports.py — Headless logic tests for SNOW CHAIN."""
import sys
import random
import math

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/274_snow_chain")
from main import (
    Game,
    Phase,
    Gate,
    Rock,
    Particle,
    FloatingText,
    GAME_DURATION,
    SUPER_DURATION,
    HEAT_MAX,
    SUPER_COMBO_THRESHOLD,
    MAX_GATES,
    MAX_ROCKS,
    GATE_COLORS,
    NUM_COLORS,
    RED,
    LIME,
    DARK_BLUE,
    YELLOW,
    ORANGE,
    GRAY,
    WHITE,
    PINK,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.PLAYING
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.super_timer = 0
    g.frame = 0
    g.player_x = 160.0
    g.player_y = 160.0
    g.player_vy = 0.0
    g.player_color_idx = 0
    g.player_on_ground = True
    g.scroll_speed = 0.0
    g.color_cycle_timer = 20
    g.color_cycle_interval = 20
    g.gate_spawn_timer = 90
    g.gate_spawn_interval = 90
    g.rock_spawn_timer = 180
    g.rock_spawn_interval = 180
    g.avalanche_edge = -20.0
    g.avalanche_timer = 60
    g.avalanche_interval = 60
    g.stun_timer = 0
    g.shake_frames = 0
    g.gates = []
    g.rocks = []
    g.particles = []
    g.floating_texts = []
    g.ghost_trail = []
    g.snow_particles = []
    g._rng = random.Random(42)
    return g


# ═══════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════


class TestDataClasses:
    def test_gate_defaults(self):
        gate = Gate(x=100.0, y=150.0, color=RED)
        assert gate.x == 100.0
        assert gate.y == 150.0
        assert gate.color == RED
        assert gate.passed is False

    def test_rock(self):
        rock = Rock(x=200.0, y=188.0, radius=8)
        assert rock.x == 200.0
        assert rock.y == 188.0
        assert rock.radius == 8

    def test_particle(self):
        p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=20, color=RED)
        assert p.life == 20
        assert p.color == RED

    def test_floating_text(self):
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=WHITE, life=30)
        assert ft.text == "+10"
        assert ft.life == 30


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════


class TestConstants:
    def test_gate_colors(self):
        assert GATE_COLORS == (RED, LIME, DARK_BLUE, YELLOW)
        assert NUM_COLORS == 4

    def test_super_threshold(self):
        assert SUPER_COMBO_THRESHOLD == 4

    def test_super_duration(self):
        assert SUPER_DURATION == 300

    def test_game_duration(self):
        assert GAME_DURATION == 1800

    def test_heat_max(self):
        assert HEAT_MAX == 100.0


# ═══════════════════════════════════════════════════════════════
# Gate processing
# ═══════════════════════════════════════════════════════════════


class TestProcessGate:
    def test_match_gate_same_color(self):
        g = _make_game()
        g.player_color_idx = 0  # RED
        gate = Gate(x=100.0, y=150.0, color=RED)
        g.combo = 1
        combo_d, score_g, heat_g, triggered = g._process_gate(gate)
        assert combo_d == 1
        assert score_g > 0
        assert heat_g == 0.0
        assert triggered is False

    def test_mismatch_gate_wrong_color(self):
        g = _make_game()
        g.player_color_idx = 0  # RED
        gate = Gate(x=100.0, y=150.0, color=LIME)
        g.combo = 3
        combo_d, score_g, heat_g, triggered = g._process_gate(gate)
        assert combo_d == 0
        assert score_g == 0
        assert heat_g == 15.0
        assert triggered is False

    def test_gate_already_passed(self):
        g = _make_game()
        gate = Gate(x=100.0, y=150.0, color=RED, passed=True)
        combo_d, score_g, heat_g, triggered = g._process_gate(gate)
        assert combo_d == 0
        assert score_g == 0
        assert heat_g == 0.0

    def test_super_mode_any_color_match(self):
        g = _make_game()
        g.super_timer = SUPER_DURATION
        g.player_color_idx = 0  # RED
        gate = Gate(x=100.0, y=150.0, color=LIME)  # wrong color
        g.combo = 4
        combo_d, score_g, heat_g, triggered = g._process_gate(gate)
        assert combo_d == 1
        assert score_g > 0
        assert heat_g == 0.0
        assert triggered is False  # already in super

    def test_match_trigger_super_at_threshold(self):
        g = _make_game()
        g.player_color_idx = 0  # RED
        gate = Gate(x=100.0, y=150.0, color=RED)
        g.combo = SUPER_COMBO_THRESHOLD - 1  # combo=3, will become 4
        g.super_timer = 0
        combo_d, score_g, heat_g, triggered = g._process_gate(gate)
        assert combo_d == 1
        assert triggered is True

    def test_combo_0_first_match(self):
        g = _make_game()
        g.player_color_idx = 0  # RED
        gate = Gate(x=100.0, y=150.0, color=RED)
        g.combo = 0
        combo_d, score_g, heat_g, triggered = g._process_gate(gate)
        assert combo_d == 1
        assert score_g > 0


# ═══════════════════════════════════════════════════════════════
# Rock collision
# ═══════════════════════════════════════════════════════════════


class TestProcessRockCollision:
    def test_no_collision_when_far(self):
        g = _make_game()
        g.player_x = 160.0
        g.player_y = 160.0
        g.player_on_ground = True
        rock = Rock(x=250.0, y=188.0, radius=8)
        heat_g, reset = g._process_rock_collision(rock)
        assert heat_g == 0.0
        assert reset is False

    def test_collision_when_near(self):
        g = _make_game()
        g.player_x = 160.0
        g.player_y = 188.0  # on ground near rock y
        g.player_on_ground = True
        rock = Rock(x=160.0, y=188.0, radius=8)
        heat_g, reset = g._process_rock_collision(rock)
        assert heat_g == 25.0
        assert reset is True

    def test_no_collision_while_jumping(self):
        g = _make_game()
        g.player_x = 160.0
        g.player_y = 140.0  # in air
        g.player_on_ground = False
        rock = Rock(x=160.0, y=188.0, radius=8)
        heat_g, reset = g._process_rock_collision(rock)
        assert heat_g == 0.0
        assert reset is False


# ═══════════════════════════════════════════════════════════════
# Avalanche
# ═══════════════════════════════════════════════════════════════


class TestAvalanche:
    def test_avalanche_starts_left(self):
        g = _make_game()
        assert g.avalanche_edge == -20.0

    def test_avalanche_not_caught_when_ahead(self):
        g = _make_game()
        g.player_x = 160.0
        g.avalanche_edge = 50.0
        caught = g._update_avalanche()
        assert caught is False

    def test_avalanche_caught_when_behind(self):
        g = _make_game()
        g.player_x = 50.0
        g.avalanche_edge = 60.0  # player_x(50) < edge + margin(20) = 80
        caught = g._update_avalanche()
        assert caught is True


# ═══════════════════════════════════════════════════════════════
# Escalation
# ═══════════════════════════════════════════════════════════════


class TestEscalation:
    def test_start_speeds(self):
        g = _make_game()
        g.timer = GAME_DURATION
        assert g.scroll_speed == 0.0  # _make_game sets to 0 for testing
        assert g.gate_spawn_interval == 90
        assert g.rock_spawn_interval == 180

    def test_escalation_updates_intervals(self):
        g = _make_game()
        g.timer = 900  # half time elapsed
        g.scroll_speed = 2.0
        g._update_escalation()
        assert 2.0 < g.scroll_speed < 5.0
        assert g.gate_spawn_interval < 90
        assert g.rock_spawn_interval < 180

    def test_full_escalation_near_end(self):
        g = _make_game()
        g.timer = 10  # almost done
        g.scroll_speed = 2.0
        g._update_escalation()
        # should be near max values
        assert g.scroll_speed > 3.0
        assert g.gate_spawn_interval < 60


# ═══════════════════════════════════════════════════════════════
# Spawning
# ═══════════════════════════════════════════════════════════════


class TestSpawning:
    def test_spawn_gate(self):
        g = _make_game()
        gate = g._spawn_gate()
        assert gate.x == 330.0
        assert 130 <= gate.y <= 170
        assert gate.color in GATE_COLORS
        assert gate.passed is False

    def test_spawn_rock(self):
        g = _make_game()
        rock = g._spawn_rock()
        assert rock.x == 330.0
        assert rock.y == 188.0
        assert rock.radius == 8


# ═══════════════════════════════════════════════════════════════
# Check gate pass
# ═══════════════════════════════════════════════════════════════


class TestCheckGatePass:
    def test_player_passed_gate(self):
        g = _make_game()
        g.player_color_idx = 0  # RED
        gate = Gate(x=100.0, y=150.0, color=RED)
        g.player_x = 120.0  # past the gate
        passed, matched = g._check_gate_pass(g.player_x, gate)
        assert passed is True
        assert matched is True

    def test_player_not_passed_gate(self):
        g = _make_game()
        gate = Gate(x=200.0, y=150.0, color=RED)
        g.player_x = 120.0  # before the gate
        passed, matched = g._check_gate_pass(g.player_x, gate)
        assert passed is False
        assert matched is False

    def test_gate_already_passed_check(self):
        g = _make_game()
        gate = Gate(x=100.0, y=150.0, color=RED, passed=True)
        g.player_x = 120.0
        passed, matched = g._check_gate_pass(g.player_x, gate)
        assert passed is False


# ═══════════════════════════════════════════════════════════════
# Player color
# ═══════════════════════════════════════════════════════════════


class TestPlayerColor:
    def test_normal_color(self):
        g = _make_game()
        g.player_color_idx = 0
        assert g._player_color() == RED

    def test_normal_color_cycle(self):
        g = _make_game()
        g.player_color_idx = 2
        assert g._player_color() == DARK_BLUE

    def test_super_color_rainbow(self):
        g = _make_game()
        g.super_timer = SUPER_DURATION
        g.player_color_idx = 0
        from main import RAINBOW
        assert g._player_color() == RAINBOW[0]


# ═══════════════════════════════════════════════════════════════
# Particles
# ═══════════════════════════════════════════════════════════════


class TestParticles:
    def test_update_particles_moves(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=1.0, vy=-1.0, life=10, color=RED)
        g.particles = [p]
        g._update_particles()
        assert abs(p.x - 101.0) < 0.001
        assert abs(p.y - 99.0) < 0.001
        assert abs(p.vy - (-0.8)) < 0.001

    def test_update_particles_removes_dead(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=RED)
        g.particles = [p]
        g._update_particles()
        assert len(g.particles) == 0

    def test_spawn_gate_particles(self):
        g = _make_game()
        gate = Gate(x=150.0, y=150.0, color=RED)
        assert len(g.particles) == 0
        g._spawn_gate_particles(gate)
        assert len(g.particles) == 8

    def test_spawn_rock_particles(self):
        g = _make_game()
        rock = Rock(x=150.0, y=188.0, radius=8)
        assert len(g.particles) == 0
        g._spawn_rock_particles(rock)
        assert len(g.particles) == 6

    def test_trigger_super_spawns_particles(self):
        g = _make_game()
        g.combo = SUPER_COMBO_THRESHOLD
        g.player_x = 160.0
        g.player_y = 160.0
        assert len(g.particles) == 0
        g._trigger_super()
        assert len(g.particles) == 20


# ═══════════════════════════════════════════════════════════════
# Floating texts
# ═══════════════════════════════════════════════════════════════


class TestFloatingTexts:
    def test_spawn_floating_text(self):
        g = _make_game()
        g._spawn_floating_text(100.0, 50.0, "+10", WHITE)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "+10"
        assert g.floating_texts[0].life == 30

    def test_update_floating_texts_rise(self):
        g = _make_game()
        g._spawn_floating_text(100.0, 50.0, "+10", WHITE)
        g._update_floating_texts()
        assert g.floating_texts[0].y == 49.0
        assert g.floating_texts[0].life == 29

    def test_update_floating_texts_removes_dead(self):
        g = _make_game()
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=WHITE, life=1)
        g.floating_texts = [ft]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


# ═══════════════════════════════════════════════════════════════
# SUPER CARVE
# ═══════════════════════════════════════════════════════════════


class TestSuperCarve:
    def test_super_activates(self):
        g = _make_game()
        g.combo = SUPER_COMBO_THRESHOLD
        g._trigger_super()
        assert g.super_timer == SUPER_DURATION

    def test_super_shake(self):
        g = _make_game()
        g.combo = SUPER_COMBO_THRESHOLD
        g._trigger_super()
        assert g.shake_frames == 6

    def test_super_floating_text(self):
        g = _make_game()
        g.combo = SUPER_COMBO_THRESHOLD
        g.player_x = 160.0
        g.player_y = 160.0
        g._trigger_super()
        assert len(g.floating_texts) == 1
        assert "SUPER" in g.floating_texts[0].text


# ═══════════════════════════════════════════════════════════════
# Heat system
# ═══════════════════════════════════════════════════════════════


class TestHeatSystem:
    def test_heat_starts_zero(self):
        g = _make_game()
        assert g.heat == 0.0

    def test_heat_game_over(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = HEAT_MAX
        g.score = 300
        g.best_score = 200
        g._end_game()
        assert g.phase == Phase.GAME_OVER
        assert g.best_score == 300

    def test_heat_clamped_below_zero(self):
        g = _make_game()
        g.heat = 0.0
        g.heat = max(0.0, g.heat - 0.02)
        assert g.heat == 0.0


# ═══════════════════════════════════════════════════════════════
# Phase and reset
# ═══════════════════════════════════════════════════════════════


class TestPhases:
    def test_initial_phase(self):
        g = _make_game()
        assert g.phase == Phase.PLAYING

    def test_reset_sets_title(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.reset()
        assert g.phase == Phase.TITLE

    def test_reset_clears_score(self):
        g = _make_game()
        g.score = 999
        g.reset()
        assert g.score == 0

    def test_reset_clears_combo(self):
        g = _make_game()
        g.combo = 5
        g.reset()
        assert g.combo == 0

    def test_reset_clears_heat(self):
        g = _make_game()
        g.heat = 80.0
        g.reset()
        assert g.heat == 0.0

    def test_reset_clears_gates(self):
        g = _make_game()
        g.gates = [Gate(x=100.0, y=150.0, color=RED)]
        g.reset()
        assert len(g.gates) == 0

    def test_reset_clears_rocks(self):
        g = _make_game()
        g.rocks = [Rock(x=100.0, y=188.0)]
        g.reset()
        assert len(g.rocks) == 0

    def test_reset_clears_particles_and_texts(self):
        g = _make_game()
        g.particles = [Particle(0, 0, 0, 0, 1, RED)]
        g.floating_texts = [FloatingText(0, 0, "test", WHITE, 1)]
        g.reset()
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0

    def test_best_score_preserved_across_reset(self):
        g = _make_game()
        g.best_score = 500
        g.reset()
        assert g.best_score == 500


# ═══════════════════════════════════════════════════════════════
# Score and tracking
# ═══════════════════════════════════════════════════════════════


class TestScoreTracking:
    def test_score_accumulates(self):
        g = _make_game()
        g.player_color_idx = 0
        gate = Gate(x=100.0, y=150.0, color=RED)
        g.combo = 2
        combo_d, score_g, _, _ = g._process_gate(gate)
        g.combo += combo_d
        g.score += score_g
        assert g.score > 0

    def test_max_combo_tracks_peak(self):
        g = _make_game()
        g.player_color_idx = 0
        # Build combo up via gate matching
        for i in range(5):
            gate = Gate(x=float(i * 50), y=150.0, color=RED)
            combo_d, score_g, _, _ = g._process_gate(gate)
            g.combo += combo_d
            g.score += score_g
            g.max_combo = max(g.max_combo, g.combo)
        assert g.max_combo == 5

    def test_mismatch_resets_combo(self):
        g = _make_game()
        g.combo = 3
        g.max_combo = 3
        g.player_color_idx = 0  # RED
        gate = Gate(x=100.0, y=150.0, color=LIME)  # wrong
        combo_d, _, heat_g, _ = g._process_gate(gate)
        assert combo_d == 0
        assert heat_g == 15.0
        g.combo = 0  # simulation of mismatch reset
        assert g.combo == 0
        assert g.max_combo == 3  # preserved

    def test_best_score_updated(self):
        g = _make_game()
        g.score = 700
        g.best_score = 500
        g._end_game()
        assert g.best_score == 700

    def test_best_score_not_lowered(self):
        g = _make_game()
        g.best_score = 500
        g.score = 300
        g._end_game()
        assert g.best_score == 500


# ═══════════════════════════════════════════════════════════════
# Ghost trail
# ═══════════════════════════════════════════════════════════════


class TestGhostTrail:
    def test_ghost_starts_empty(self):
        g = _make_game()
        assert len(g.ghost_trail) == 0

    def test_ghost_records_points(self):
        g = _make_game()
        g.frame = 5
        assert len(g.ghost_trail) == 0
        g.ghost_trail.append((g.player_x, g.player_y))
        assert len(g.ghost_trail) == 1
        assert g.ghost_trail[0] == (160.0, 160.0)

    def test_new_best_clears_ghost(self):
        g = _make_game()
        g.ghost_trail = [(100.0, 150.0)]
        g.score = 500
        g.best_score = 300
        g._end_game()
        assert len(g.ghost_trail) == 0  # cleared for new best
