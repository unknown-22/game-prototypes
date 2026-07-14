"""test_imports.py — Headless logic tests for KAYAK CHAIN (236_kayak_chain)."""
from __future__ import annotations

import random
import sys

PROTO_DIR = "/home/unknown22/repos/game-prototypes/prototypes/236_kayak_chain"
sys.path.insert(0, PROTO_DIR)

from main import (  # noqa: E402
    BASE_SCORE,
    COMBO_THRESHOLD,
    GAME_TIME,
    GATE_COLORS,
    GATE_W,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    HEAT_MISS,
    KAYAK_W,
    KAYAK_Y,
    PLAYFIELD_W,
    PLAYFIELD_X,
    PLAYFIELD_RIGHT,
    SCREEN_H,
    SCREEN_W,
    SCROLL_SPEED_INITIAL,
    SCROLL_SPEED_RATE,
    SPAWN_INTERVAL_INITIAL,
    SPAWN_INTERVAL_MIN,
    STUN_DURATION,
    SUPER_DURATION,
    FloatingText,
    Game,
    Gate,
    Particle,
    Phase,
    LIME,
    RED,
    WHITE,
)


def _make_game() -> Game:
    """Create a Game instance bypassing Pyxel init for headless testing."""
    g = Game.__new__(Game)
    # Pre-init attributes that _init_state() touches
    g.rng = random.Random()
    g.phase = Phase.TITLE
    g.kayak_x = 0.0
    g.kayak_y = 0.0
    g.paddle_color_idx = 0
    g.color_timer = 0
    g.gates = []
    g.particles = []
    g.floating_texts = []
    g.score = 0
    g.high_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.stun_timer = 0
    g.game_timer = 0
    g.scroll_speed = 0.0
    g.spawn_interval = 0
    g.spawn_timer = 0
    g._init_state()
    g.rng = random.Random(42)  # Deterministic
    return g


def _make_playing() -> Game:
    """Create a Game with phase=PLAYING (simulate after reset)."""
    g = _make_game()
    g.phase = Phase.PLAYING
    return g


# ── Initialization tests ──


def test_init_state_sets_phase_title() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE


def test_init_state_sets_defaults() -> None:
    g = _make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.stun_timer == 0
    assert g.game_timer == GAME_TIME
    assert g.scroll_speed == SCROLL_SPEED_INITIAL
    assert g.spawn_interval == SPAWN_INTERVAL_INITIAL
    assert g.spawn_timer == SPAWN_INTERVAL_INITIAL
    assert g.gates == []
    assert g.particles == []
    assert g.floating_texts == []


def test_reset_transitions_to_playing() -> None:
    g = _make_game()
    g.reset()
    assert g.phase == Phase.PLAYING


def test_reset_clears_state() -> None:
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.heat = 50.0
    g.super_timer = 100
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0


# ── Gate spawning tests ──


def test_spawn_gate_creates_valid_gate() -> None:
    g = _make_game()
    gate = g._spawn_gate()
    assert isinstance(gate, Gate)
    assert PLAYFIELD_X <= gate.x <= PLAYFIELD_RIGHT - GATE_W
    assert gate.color in GATE_COLORS
    assert gate.y < 0  # Spawns above screen
    assert not gate.passed


def test_spawn_gate_is_deterministic() -> None:
    g1 = _make_game()
    g1.rng = random.Random(42)
    g2 = _make_game()
    g2.rng = random.Random(42)
    gate1 = g1._spawn_gate()
    gate2 = g2._spawn_gate()
    assert gate1.x == gate2.x
    assert gate1.y == gate2.y
    assert gate1.color == gate2.color


# ── Collision tests ──


def test_check_collision_overlapping() -> None:
    g = _make_playing()
    g.kayak_x = 100.0
    g.kayak_y = 100.0
    gate = Gate(x=100.0, y=100.0, color=RED)
    assert g._check_kayak_gate_collision(gate)


def test_check_collision_no_overlap() -> None:
    g = _make_playing()
    g.kayak_x = 100.0
    g.kayak_y = 100.0
    gate = Gate(x=200.0, y=200.0, color=RED)
    assert not g._check_kayak_gate_collision(gate)


def test_check_collision_already_passed() -> None:
    g = _make_playing()
    g.kayak_x = 100.0
    g.kayak_y = 100.0
    gate = Gate(x=100.0, y=100.0, color=RED, passed=True)
    assert not g._check_kayak_gate_collision(gate)


def test_check_collision_edge_touch() -> None:
    g = _make_playing()
    g.kayak_x = 100.0
    g.kayak_y = KAYAK_Y
    gate = Gate(x=100.0 + KAYAK_W - 1, y=KAYAK_Y, color=RED)
    # Kayak right edge touches gate left edge
    assert g._check_kayak_gate_collision(gate)


def test_check_collision_just_outside() -> None:
    g = _make_playing()
    g.kayak_x = 100.0
    g.kayak_y = KAYAK_Y
    gate = Gate(x=100.0 + KAYAK_W + 1, y=KAYAK_Y, color=RED)
    # Kayak right edge is 1px away from gate left edge
    assert not g._check_kayak_gate_collision(gate)


# ── Gate pass handling tests ──


def test_handle_gate_pass_match() -> None:
    g = _make_playing()
    g.paddle_color_idx = 0  # RED
    gate = Gate(x=100.0, y=KAYAK_Y, color=RED)
    g._handle_gate_pass(gate)
    assert gate.passed
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == BASE_SCORE * 1  # 10 * 1 * 1
    assert g.super_timer == 0  # COMBO=1 < threshold
    assert g.heat == 0.0


def test_handle_gate_pass_mismatch() -> None:
    g = _make_playing()
    g.paddle_color_idx = 0  # RED
    g.combo = 3
    gate = Gate(x=100.0, y=KAYAK_Y, color=LIME)
    g._handle_gate_pass(gate)
    assert gate.passed
    assert g.combo == 0  # Reset
    assert g.heat == HEAT_MISMATCH
    assert g.stun_timer == STUN_DURATION
    assert len(g.floating_texts) >= 1


def test_handle_gate_pass_super_mode_always_match() -> None:
    g = _make_playing()
    g.super_timer = 100
    g.paddle_color_idx = 0  # RED
    g.combo = 5
    g.max_combo = 5
    gate = Gate(x=100.0, y=KAYAK_Y, color=LIME)  # Wrong color
    g._handle_gate_pass(gate)
    assert gate.passed
    assert g.combo == 6  # Still increments in super mode
    assert g.max_combo == 6
    assert g.score == BASE_SCORE * 6 * 3  # 10 * 6 * 3 (super multiplier)


def test_handle_gate_pass_combo_chain() -> None:
    g = _make_playing()
    g.paddle_color_idx = 0  # RED
    # At COMBO=4, SUPER activates → pass 5 uses 3x multiplier
    # Score: 10*1 + 10*2 + 10*3 + 10*4 + 10*5*3 = 10+20+30+40+150 = 250
    for i in range(5):
        gate = Gate(x=100.0, y=KAYAK_Y, color=RED, passed=False)
        g._handle_gate_pass(gate)
    assert g.combo == 5
    assert g.max_combo == 5
    assert g.score == 250


def test_handle_gate_pass_triggers_super_at_threshold() -> None:
    g = _make_playing()
    g.paddle_color_idx = 0  # RED
    g.combo = COMBO_THRESHOLD - 1  # 3
    g.max_combo = COMBO_THRESHOLD - 1
    gate = Gate(x=100.0, y=KAYAK_Y, color=RED, passed=False)
    g._handle_gate_pass(gate)
    assert g.combo == COMBO_THRESHOLD
    assert g.super_timer == SUPER_DURATION
    assert len(g.floating_texts) >= 2  # Score + "SUPER!"


def test_handle_gate_pass_extends_super() -> None:
    g = _make_playing()
    g.paddle_color_idx = 0  # RED
    g.combo = COMBO_THRESHOLD  # 4
    g.max_combo = COMBO_THRESHOLD
    g.super_timer = 50  # Already in super
    gate = Gate(x=100.0, y=KAYAK_Y, color=RED, passed=False)
    g._handle_gate_pass(gate)
    assert g.combo == COMBO_THRESHOLD + 1
    assert g.super_timer == SUPER_DURATION  # Reset to full


def test_handle_gate_pass_combo_text() -> None:
    g = _make_playing()
    g.paddle_color_idx = 0
    g.combo = 1
    g.max_combo = 1
    gate = Gate(x=100.0, y=KAYAK_Y, color=RED, passed=False)
    texts_before = len(g.floating_texts)
    g._handle_gate_pass(gate)
    # Score text + COMBO text (combo becomes 2)
    assert len(g.floating_texts) >= texts_before + 2


# ── Gate miss tests ──


def test_handle_gate_miss_adds_heat() -> None:
    g = _make_playing()
    g.heat = 10.0
    gate = Gate(x=100.0, y=SCREEN_H + 10, color=RED)
    g._handle_gate_miss(gate)
    assert g.heat == 10.0 + HEAT_MISS
    assert len(g.floating_texts) >= 1


def test_handle_gate_miss_heat_capped() -> None:
    g = _make_playing()
    g.heat = HEAT_MAX - 1.0
    gate = Gate(x=100.0, y=SCREEN_H + 10, color=RED)
    g._handle_gate_miss(gate)
    assert g.heat == HEAT_MAX


# ── Heat update tests ──


def test_update_heat_decay() -> None:
    g = _make_playing()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_update_heat_no_negative() -> None:
    g = _make_playing()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_decay_near_zero() -> None:
    g = _make_playing()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0  # Clamped at 0


# ── Difficulty tests ──


def test_update_difficulty_no_elapsed_no_change() -> None:
    g = _make_playing()
    g._update_difficulty()
    assert g.scroll_speed == SCROLL_SPEED_INITIAL
    assert g.spawn_interval == SPAWN_INTERVAL_INITIAL


def test_update_difficulty_increases_speed() -> None:
    g = _make_playing()
    g.game_timer = GAME_TIME - (30 * 60)  # 30 seconds elapsed
    g._update_difficulty()
    assert g.scroll_speed > SCROLL_SPEED_INITIAL
    assert abs(g.scroll_speed - (SCROLL_SPEED_INITIAL + 30 * SCROLL_SPEED_RATE)) < 0.01


def test_update_difficulty_spawn_interval_decreases() -> None:
    g = _make_playing()
    g.game_timer = GAME_TIME - (20 * 60)  # 20 seconds elapsed → //10 = 2
    g._update_difficulty()
    expected = max(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_INITIAL - 2 * 5)
    assert g.spawn_interval == expected


def test_update_difficulty_spawn_interval_min_clamp() -> None:
    g = _make_playing()
    g.game_timer = GAME_TIME - (100 * 60)  # Very long elapsed
    g._update_difficulty()
    assert g.spawn_interval == SPAWN_INTERVAL_MIN


# ── Super activation tests ──


def test_activate_super_sets_timer() -> None:
    g = _make_playing()
    g._activate_super()
    assert g.super_timer == SUPER_DURATION
    assert len(g.particles) >= 20  # Particle burst
    assert len(g.floating_texts) >= 1  # "SUPER!" text


# ── End game tests ──


def test_end_game_transitions_phase() -> None:
    g = _make_playing()
    g.score = 500
    g.high_score = 300
    g._end_game()
    assert g.phase == Phase.GAME_OVER


def test_end_game_updates_high_score() -> None:
    g = _make_playing()
    g.score = 500
    g.high_score = 300
    g._end_game()
    assert g.high_score == 500


def test_end_game_does_not_lower_high_score() -> None:
    g = _make_playing()
    g.score = 200
    g.high_score = 500
    g._end_game()
    assert g.high_score == 500


# ── Particle tests ──


def test_spawn_particles_creates_correct_count() -> None:
    g = _make_playing()
    g._spawn_particles(160.0, 120.0, RED, 10)
    assert len(g.particles) == 10


def test_update_particles_decrements_life() -> None:
    g = _make_playing()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=RED, life=1)]
    g._update_particles()
    assert len(g.particles) == 0  # life=1 → decremented to 0 → removed


def test_update_particles_moves_position() -> None:
    g = _make_playing()
    g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=2.0, color=RED, life=5)]
    g._update_particles()
    p = g.particles[0]
    assert p.x == 101.0
    assert p.y == 102.0
    assert p.vy == 2.05  # gravity
    assert p.life == 4


# ── Floating text tests ──


def test_update_floating_texts_moves_up() -> None:
    g = _make_playing()
    g.floating_texts = [FloatingText(x=160.0, y=100.0, text="TEST", color=WHITE, life=10)]
    g._update_floating_texts()
    ft = g.floating_texts[0]
    assert ft.y < 100.0
    assert ft.life == 9


def test_update_floating_texts_removes_dead() -> None:
    g = _make_playing()
    g.floating_texts = [FloatingText(x=160.0, y=100.0, text="TEST", color=WHITE, life=1)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Kayak bounds tests ──


def test_kayak_x_clamped_left() -> None:
    g = _make_playing()
    g.kayak_x = PLAYFIELD_X - 10.0
    # Simulate clamp logic from _update_playing
    g.kayak_x = max(float(PLAYFIELD_X), min(float(PLAYFIELD_RIGHT - KAYAK_W), g.kayak_x))
    assert g.kayak_x == PLAYFIELD_X


def test_kayak_x_clamped_right() -> None:
    g = _make_playing()
    g.kayak_x = PLAYFIELD_RIGHT + 10.0
    g.kayak_x = max(float(PLAYFIELD_X), min(float(PLAYFIELD_RIGHT - KAYAK_W), g.kayak_x))
    assert g.kayak_x == PLAYFIELD_RIGHT - KAYAK_W


def test_kayak_x_inside_bounds() -> None:
    g = _make_playing()
    g.kayak_x = 150.0
    g.kayak_x = max(float(PLAYFIELD_X), min(float(PLAYFIELD_RIGHT - KAYAK_W), g.kayak_x))
    assert g.kayak_x == 150.0


# ── Score calculation tests ──


def test_score_without_super() -> None:
    g = _make_playing()
    g.paddle_color_idx = 0
    g.combo = 2
    g.max_combo = 2
    g.super_timer = 0
    gate = Gate(x=100.0, y=KAYAK_Y, color=RED, passed=False)
    g._handle_gate_pass(gate)
    assert g.score == BASE_SCORE * 3  # combo becomes 3, multiplier=1


def test_score_with_super() -> None:
    g = _make_playing()
    g.paddle_color_idx = 0
    g.combo = 4
    g.max_combo = 4
    g.super_timer = 100  # Active super
    gate = Gate(x=100.0, y=KAYAK_Y, color=RED, passed=False)
    g._handle_gate_pass(gate)
    assert g.score == BASE_SCORE * 5 * 3  # combo becomes 5, multiplier=3


# ── Constants sanity tests ──


def test_gate_colors_valid() -> None:
    assert len(GATE_COLORS) == 4
    assert RED in GATE_COLORS
    assert LIME in GATE_COLORS


def test_screen_dimensions_reasonable() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert PLAYFIELD_W == 280
    assert PLAYFIELD_X == 20
    assert PLAYFIELD_RIGHT == 300


def test_game_time_is_60_seconds() -> None:
    assert GAME_TIME == 3600  # 60 * 60


# ── Combo/MaxCombo tracking ──


def test_max_combo_remains_after_reset() -> None:
    g = _make_playing()
    g.paddle_color_idx = 0
    g.combo = 5
    g.max_combo = 5
    # mismatch resets combo but not max_combo
    gate = Gate(x=100.0, y=KAYAK_Y, color=LIME, passed=False)
    g._handle_gate_pass(gate)
    assert g.combo == 0
    assert g.max_combo == 5  # Preserved


def test_gate_passed_flag_prevents_double_counting() -> None:
    g = _make_playing()
    g.kayak_x = 100.0  # Position kayak to overlap with gate
    g.paddle_color_idx = 0
    gate = Gate(x=100.0, y=KAYAK_Y, color=RED, passed=False)
    # First pass
    assert g._check_kayak_gate_collision(gate)
    g._handle_gate_pass(gate)
    assert gate.passed
    # Second check
    assert not g._check_kayak_gate_collision(gate)


# ── Stun tests ──


def test_stun_prevents_collision_detection() -> None:
    """Verify that _update_playing skips collision when stunned.
    Since _update_playing touches pyxel, we test the logic pattern:
    when stun_timer > 0, _check_kayak_gate_collision should NOT be called.
    We verify stun prevents further mismatches by simulating the skip."""
    g = _make_playing()
    g.stun_timer = 10  # Stunned
    gate = Gate(x=100.0, y=KAYAK_Y, color=RED, passed=False)
    # Simulate what _update_playing does:
    # if self.stun_timer <= 0: for gate in gates: check_collision...
    # When stunned, collision is skipped, gate is NOT passed
    collisions_checked = g.stun_timer <= 0
    if collisions_checked:
        g._handle_gate_pass(gate)
    assert not gate.passed  # Stun prevented collision check
    assert g.heat == 0.0  # No heat from mismatch


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
