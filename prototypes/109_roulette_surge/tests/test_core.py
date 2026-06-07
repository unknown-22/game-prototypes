"""Tests for 109_roulette_surge core logic."""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (
    BASE_SCORE,
    COMBO_MULT_STEP,
    FORESIGHT_MAX,
    GAME_COLORS,
    GAME_DURATION_SEC,
    GREEN,
    HEAT_MAX,
    HEAT_PER_MISS,
    LIGHT_BLUE,
    NUM_SEGMENTS,
    RED,
    SEGMENT_COLORS,
    SUPER_MULTIPLIER,
    SUPER_TURNS,
    WHITE,
    YELLOW,
    FPS,
    Game,
    Particle,
    Phase,
)


def make_game() -> Game:
    """Create a headless Game instance for testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0
    g.wheel_angle = 0.0
    g.spin_speed = 0.0
    g.bet_color = -1
    g.winning_color = -1
    g.result_timer = 0
    g.super_mode = False
    g.super_turns = 0
    g.foresight_tokens = FORESIGHT_MAX
    g.foresight_queue = []
    g.game_timer = GAME_DURATION_SEC * FPS
    g.segments = []
    g.particles = []
    g._spin_frames = 0
    g._was_match = False
    g._last_score_gain = 0
    g.high_score = 0
    g._blink = 0
    g._prev_mouse_pressed = False
    g._target_angle_mod = 0.0
    g.reset()
    return g


# ── Wheel segment building ────────────────────────────────────────────────
def test_build_segments() -> None:
    g = make_game()
    assert len(g.segments) == NUM_SEGMENTS
    for i, seg in enumerate(g.segments):
        assert seg.color == SEGMENT_COLORS[i]
        expected_start = i * (2 * math.pi / NUM_SEGMENTS)
        assert abs(seg.start_angle - expected_start) < 0.001
        assert abs(seg.end_angle - seg.start_angle - 2 * math.pi / NUM_SEGMENTS) < 0.001


# ── Wheel angle → winner detection ────────────────────────────────────────
def test_winner_detection_angle_zero() -> None:
    g = make_game()
    g.wheel_angle = 0.0
    idx = int(((2 * math.pi - g.wheel_angle) % (2 * math.pi)) / (math.pi / 4)) % NUM_SEGMENTS
    assert idx == 0
    assert g.segments[idx].color == RED


def test_winner_detection_angle_pi4() -> None:
    g = make_game()
    g.wheel_angle = math.pi / 4
    idx = int(((2 * math.pi - g.wheel_angle) % (2 * math.pi)) / (math.pi / 4)) % NUM_SEGMENTS
    assert idx == 7
    assert g.segments[idx].color == YELLOW


def test_winner_detection_angle_pi2() -> None:
    g = make_game()
    g.wheel_angle = math.pi / 2
    idx = int(((2 * math.pi - g.wheel_angle) % (2 * math.pi)) / (math.pi / 4)) % NUM_SEGMENTS
    assert idx == 6
    assert g.segments[idx].color == LIGHT_BLUE


# ── Match evaluation ──────────────────────────────────────────────────────
def test_match_combo_increments() -> None:
    g = make_game()
    g.bet_color = RED
    g.combo = 2
    g.wheel_angle = 0.0  # segment 0 = RED
    g.foresight_queue = [RED, GREEN]
    g._evaluate_result()
    assert g.combo == 3
    assert g._was_match is True
    assert g.score > 0


def test_match_score_with_combo() -> None:
    g = make_game()
    g.bet_color = GREEN
    g.combo = 3
    g.wheel_angle = 2 * math.pi - (1 * math.pi / 4)  # segment 1 = GREEN
    g.foresight_queue = [GREEN, RED]
    g._evaluate_result()
    expected_mult = 1.0 + 4 * COMBO_MULT_STEP  # combo becomes 4
    expected_gain = int(BASE_SCORE * expected_mult)
    assert g.score == expected_gain
    assert g._last_score_gain == expected_gain


def test_mismatch_resets_combo() -> None:
    g = make_game()
    g.bet_color = RED
    g.combo = 3
    g.wheel_angle = math.pi / 4  # segment 0 = RED but winner is 7 = YELLOW? no...
    # Set angle so winner is GREEN (segment 1 = GREEN, segment 3 = GREEN)
    # segment index 1: needs (2π - angle) % 2π in [π/4, π/2)
    # (2π - angle) = π/4 + π/8 → angle = 2π - 3π/8 = 13π/8
    g.wheel_angle = 2 * math.pi - (1 * math.pi / 4 + math.pi / 8)
    g.bet_color = RED
    g.combo = 3
    g.foresight_queue = [GREEN, RED]
    g._evaluate_result()
    assert g.combo == 0
    assert g._was_match is False
    assert g.heat == HEAT_PER_MISS


def test_mismatch_adds_heat() -> None:
    g = make_game()
    g.bet_color = RED
    g.heat = 20
    g.wheel_angle = 2 * math.pi - (1 * math.pi / 4 + math.pi / 8)  # segment 1 = GREEN
    g.foresight_queue = [GREEN, RED]
    g._evaluate_result()
    assert g.heat == 20 + HEAT_PER_MISS


# ── SUPER MODE activation ─────────────────────────────────────────────────
def test_combo_5_activates_super_mode() -> None:
    g = make_game()
    g.bet_color = RED
    g.combo = 4
    g.wheel_angle = 0.0  # segment 0 = RED
    g.foresight_queue = [RED, GREEN]
    g._evaluate_result()
    assert g.combo == 5
    assert g.super_mode is True
    assert g.super_turns == SUPER_TURNS


def test_super_mode_auto_win() -> None:
    g = make_game()
    g.bet_color = RED
    g.super_mode = True
    g.super_turns = 3
    g.wheel_angle = 2 * math.pi - (1 * math.pi / 4 + math.pi / 8)  # segment 1 = GREEN
    g.foresight_queue = [GREEN, RED]
    g._evaluate_result()
    assert g._was_match is True
    assert g.combo == 1  # reset because prev combo was 0, now it's a win
    assert g.super_turns == 2


def test_super_mode_3x_score() -> None:
    g = make_game()
    g.bet_color = RED
    g.super_mode = True
    g.super_turns = 2
    g.combo = 5
    g.wheel_angle = 0.0  # RED
    g.foresight_queue = [RED, GREEN]
    g._evaluate_result()
    expected_gain = int(BASE_SCORE * SUPER_MULTIPLIER)
    assert g.score == expected_gain
    assert g._last_score_gain == expected_gain


def test_super_mode_does_not_stack_reactivation() -> None:
    g = make_game()
    g.bet_color = RED
    g.super_mode = True
    g.super_turns = 2
    g.combo = 5
    g.wheel_angle = 0.0  # RED
    g.foresight_queue = [RED, GREEN]
    g._evaluate_result()
    assert g.super_mode is True
    assert g.super_turns == 1  # decremented from 2 to 1, not reset to 5


def test_super_mode_expires() -> None:
    g = make_game()
    g.bet_color = RED
    g.super_mode = True
    g.super_turns = 1
    g.wheel_angle = 0.0  # RED
    g.foresight_queue = [RED, GREEN]
    g._evaluate_result()
    assert g.super_mode is False
    assert g.super_turns == 0


# ── HEAT and Game Over ────────────────────────────────────────────────────
def test_heat_100_game_over() -> None:
    g = make_game()
    g.bet_color = RED
    g.heat = HEAT_MAX - HEAT_PER_MISS
    g.wheel_angle = 2 * math.pi - (1 * math.pi / 4 + math.pi / 8)  # GREEN
    g.foresight_queue = [GREEN, RED]
    g._evaluate_result()
    assert g.heat == HEAT_MAX
    assert g.phase == Phase.GAME_OVER


def test_heat_capped_at_max() -> None:
    g = make_game()
    g.bet_color = RED
    g.heat = HEAT_MAX - 5
    g.wheel_angle = 2 * math.pi - (1 * math.pi / 4 + math.pi / 8)  # GREEN
    g.foresight_queue = [GREEN, RED]
    g._evaluate_result()
    assert g.heat == HEAT_MAX
    assert g.phase == Phase.GAME_OVER


# ── max_combo tracking ────────────────────────────────────────────────────
def test_max_combo_tracking() -> None:
    g = make_game()
    g.max_combo = 5
    g.bet_color = RED
    g.combo = 2
    g.wheel_angle = 0.0  # RED
    g.foresight_queue = [RED, GREEN]
    g._evaluate_result()
    assert g.combo == 3
    assert g.max_combo == 5  # unchanged

    g.combo = 6
    g._start_spin()
    g.wheel_angle = 0.0  # RED
    g._evaluate_result()
    assert g.combo == 7
    assert g.max_combo == 7  # updated


# ── FORESIGHT ─────────────────────────────────────────────────────────────
def test_foresight_queue_populated() -> None:
    g = make_game()
    assert len(g.foresight_queue) == 2
    assert g.foresight_queue[0] in GAME_COLORS
    assert g.foresight_queue[1] in GAME_COLORS


def test_foresight_tokens_used() -> None:
    g = make_game()
    assert g.foresight_tokens == FORESIGHT_MAX
    g.phase = Phase.BET
    g.use_foresight()
    assert g.foresight_tokens == FORESIGHT_MAX - 1


def test_foresight_tokens_cannot_go_negative() -> None:
    g = make_game()
    g.foresight_tokens = 1
    g.phase = Phase.BET
    g.use_foresight()
    assert g.foresight_tokens == 0
    g.use_foresight()
    assert g.foresight_tokens == 0


def test_foresight_queue_updates_after_spin() -> None:
    g = make_game()
    old = g.foresight_queue.copy()
    g.bet_color = RED
    g.wheel_angle = 0.0  # RED
    g._evaluate_result()
    assert len(g.foresight_queue) == 2
    # First item was consumed, second shifted, new one added
    assert g.foresight_queue[0] == old[1]


def test_foresight_not_usable_outside_bet() -> None:
    g = make_game()
    g.foresight_tokens = 3
    g.phase = Phase.SPINNING
    g.use_foresight()
    assert g.foresight_tokens == 3


# ── Timer ─────────────────────────────────────────────────────────────────
def test_timer_game_over() -> None:
    g = make_game()
    g.phase = Phase.BET
    g.game_timer = 1
    g._update_timer()
    assert g.game_timer == 0
    assert g.phase == Phase.GAME_OVER


def test_timer_does_not_count_in_title() -> None:
    g = make_game()
    g.phase = Phase.TITLE
    g.game_timer = 100
    g._update_timer()
    assert g.game_timer == 100


# ── Reset ─────────────────────────────────────────────────────────────────
def test_reset_initial_state() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0
    assert g.super_mode is False
    assert g.super_turns == 0
    assert g.foresight_tokens == FORESIGHT_MAX
    assert g.game_timer == GAME_DURATION_SEC * FPS
    assert len(g.particles) == 0
    assert len(g.segments) == NUM_SEGMENTS
    assert len(g.foresight_queue) == 2


# ── Particles ─────────────────────────────────────────────────────────────
def test_spawn_particles() -> None:
    g = make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100, 100, WHITE, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == WHITE
        assert 15 <= p.life <= 25
        assert p.x == 100.0
        assert p.y == 100.0


def test_update_particles_removes_dead() -> None:
    g = make_game()
    g.particles = [
        Particle(0, 0, 0, 0, 0, WHITE),
        Particle(0, 0, 0, 0, 5, WHITE),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


# ── Place bet ─────────────────────────────────────────────────────────────
def test_place_bet_starts_spin() -> None:
    g = make_game()
    g.phase = Phase.BET
    g.place_bet(0)  # RED
    assert g.bet_color == RED
    assert g.phase == Phase.SPINNING


def test_place_bet_rejected_outside_bet_phase() -> None:
    g = make_game()
    g.phase = Phase.TITLE
    g.place_bet(0)
    assert g.phase == Phase.TITLE  # unchanged
    assert g.bet_color == -1


def test_place_bet_rejected_invalid_index() -> None:
    g = make_game()
    g.phase = Phase.BET
    g.place_bet(-1)
    assert g.bet_color == -1
    g.place_bet(4)
    assert g.bet_color == -1


# ── High score ────────────────────────────────────────────────────────────
def test_high_score_updates_on_game_over() -> None:
    g = make_game()
    g.score = 500
    g.high_score = 300
    g.bet_color = RED
    g.heat = HEAT_MAX - HEAT_PER_MISS
    g.wheel_angle = 2 * math.pi - (1 * math.pi / 4 + math.pi / 8)  # GREEN → miss
    g.foresight_queue = [GREEN, RED]
    g._evaluate_result()
    assert g.phase == Phase.GAME_OVER
    assert g.high_score == 500


# ── _find_segment_for_color ───────────────────────────────────────────────
def test_find_segment_for_color() -> None:
    g = make_game()
    idx = g._find_segment_for_color(RED)
    assert g.segments[idx].color == RED
    assert idx in (0, 4)  # RED is at indices 0 and 4


# ── Foresight queue refill ────────────────────────────────────────────────
def test_refill_foresight_keeps_two() -> None:
    g = make_game()
    g.foresight_queue = []
    g._refill_foresight()
    assert len(g.foresight_queue) == 2
