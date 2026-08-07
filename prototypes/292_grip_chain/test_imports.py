"""test_imports.py -- Headless logic tests for 292_grip_chain."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.absolute()))

from main import (
    SCREEN_W, SCREEN_H, FPS,
    COLS, ROWS, CELL, GRID_X, GRID_Y,
    GAME_DURATION, SUPER_DURATION,
    COLORS, COLOR_CYCLE_INITIAL, COLOR_CYCLE_MIN,
    MIN_HOLDS, MAX_HOLDS,
    RESPAWN_DELAY_INITIAL, RESPAWN_DELAY_MIN,
    HEAT_MISMATCH, HEAT_DECAY, HEAT_MAX,
    COMBO_SUPER_THRESHOLD,
    PARTICLE_COUNT_MATCH, PARTICLE_COUNT_SUPER, PARTICLE_COUNT_MISMATCH,
    FLOAT_TEXT_LIFE, BLINK_VISIBLE, BLINK_HIDDEN,
    BLACK, NAVY, PURPLE, GREEN, BROWN, DARK_BLUE, LIGHT_BLUE,
    WHITE, RED, ORANGE, YELLOW, LIME, CYAN, GRAY, PINK, PEACH,
    Phase, Hold, Particle, FloatingText, Game,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.best_score = 0
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.holds = []
    g.player_col = 0
    g.player_row = 0
    g.player_color_idx = 0
    g.color_cycle_timer = COLOR_CYCLE_INITIAL
    g.super_timer = 0
    g.super_mode = False
    g.respawn_timer = 0
    g.last_grabbed_color = -1
    g.particles = []
    g.floating_texts = []
    g._shake_frames = 0
    g._elapsed_frames = 0
    g.phase = Phase.PLAYING
    g._generate_holds(MIN_HOLDS)
    g._place_player()
    g.respawn_timer = g._get_respawn_delay()
    return g


# ── Constants Tests ──────────────────────────────────────────────────

def test_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert FPS == 30
    assert COLS == 8
    assert ROWS == 10
    assert CELL == 24
    assert GRID_X == 40
    assert GRID_Y == 12
    assert GAME_DURATION == 1800
    assert SUPER_DURATION == 300
    assert COLOR_CYCLE_INITIAL == 45
    assert COLOR_CYCLE_MIN == 20
    assert MIN_HOLDS == 8
    assert MAX_HOLDS == 12
    assert RESPAWN_DELAY_INITIAL == 60
    assert RESPAWN_DELAY_MIN == 30
    assert HEAT_MISMATCH == 15.0
    assert HEAT_DECAY == 0.02
    assert HEAT_MAX == 100.0
    assert COMBO_SUPER_THRESHOLD == 4
    assert PARTICLE_COUNT_MATCH == 8
    assert PARTICLE_COUNT_SUPER == 16
    assert PARTICLE_COUNT_MISMATCH == 4
    assert FLOAT_TEXT_LIFE == 45
    assert BLINK_VISIBLE == 20
    assert BLINK_HIDDEN == 5


def test_color_constants():
    assert COLORS == (8, 11, 5, 10)
    assert BLACK == 0
    assert NAVY == 1
    assert PURPLE == 2
    assert GREEN == 3
    assert BROWN == 4
    assert DARK_BLUE == 5
    assert LIGHT_BLUE == 6
    assert WHITE == 7
    assert RED == 8
    assert ORANGE == 9
    assert YELLOW == 10
    assert LIME == 11
    assert CYAN == 12
    assert GRAY == 13
    assert PINK == 14
    assert PEACH == 15


# ── Hold Management Tests ────────────────────────────────────────────

def test_generate_holds_creates_correct_count():
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.holds = []
    g._generate_holds(8)
    assert len(g.holds) == 8


def test_generate_holds_valid_colors():
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.holds = []
    g._generate_holds(8)
    for h in g.holds:
        assert h.color in COLORS


def test_generate_holds_unique_positions():
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.holds = []
    g._generate_holds(12)
    positions = {(h.col, h.row) for h in g.holds}
    assert len(positions) == 12


def test_generate_holds_no_duplicate_with_existing():
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.holds = [Hold(col=0, row=0, color=RED), Hold(col=1, row=1, color=LIME)]
    g._generate_holds(6)
    positions = {(h.col, h.row) for h in g.holds}
    assert len(positions) == 8


def test_find_hold_returns_hold():
    g = _make_game()
    h = g.holds[0]
    found = g._find_hold(h.col, h.row)
    assert found is h


def test_find_hold_returns_none_for_empty():
    g = _make_game()
    g.holds = []
    assert g._find_hold(0, 0) is None


def test_find_hold_returns_none_for_missing():
    g = _make_game()
    g.holds = [Hold(col=0, row=0, color=RED)]
    assert g._find_hold(7, 9) is None


def test_place_player_on_hold():
    g = _make_game()
    h = g._find_hold(g.player_col, g.player_row)
    assert h is not None


def test_remove_and_respawn_hold_removes():
    g = _make_game()
    hold = g.holds[0]
    g.holds.remove(hold)
    assert hold not in g.holds


# ── Movement Tests ───────────────────────────────────────────────────

def test_try_move_to_existing_hold_succeeds():
    g = _make_game()
    g.holds = [
        Hold(col=0, row=0, color=RED),
        Hold(col=1, row=0, color=LIME),
    ]
    g.player_col = 0
    g.player_row = 0
    initial_col = g.player_col
    result = g._try_move(1, 0)
    assert result is True
    assert g.player_col == initial_col + 1


def test_try_move_to_empty_cell_fails():
    g = _make_game()
    g.holds = [Hold(col=0, row=0, color=RED)]
    g.player_col = 0
    g.player_row = 0
    result = g._try_move(1, 0)
    assert result is False
    assert g.player_col == 0
    assert g.player_row == 0


def test_try_move_out_of_bounds_fails():
    g = _make_game()
    g.holds = [Hold(col=0, row=0, color=RED)]
    g.player_col = 0
    g.player_row = 0
    result = g._try_move(-1, 0)
    assert result is False
    assert g.player_col == 0


def test_try_move_to_bottom_bounds_fails():
    g = _make_game()
    g.holds = [Hold(col=0, row=9, color=RED)]
    g.player_col = 0
    g.player_row = 9
    result = g._try_move(0, 1)
    assert result is False


def test_try_move_up_succeeds():
    g = _make_game()
    g.holds = [
        Hold(col=0, row=1, color=RED),
        Hold(col=0, row=0, color=LIME),
    ]
    g.player_col = 0
    g.player_row = 1
    result = g._try_move(0, -1)
    assert result is True
    assert g.player_row == 0


def test_try_move_left_succeeds():
    g = _make_game()
    g.holds = [
        Hold(col=0, row=0, color=RED),
        Hold(col=1, row=0, color=LIME),
    ]
    g.player_col = 1
    g.player_row = 0
    result = g._try_move(-1, 0)
    assert result is True
    assert g.player_col == 0


# ── Grab Processing Tests ────────────────────────────────────────────

def test_process_grab_match_increments_combo():
    g = _make_game()
    g.combo = 0
    g.score = 0
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=1, row=1, color=RED)
    g.holds.append(hold)
    g._process_grab(hold)
    assert g.combo == 1
    assert g.score == 10  # 10 * 1
    assert g.last_grabbed_color == RED


def test_process_grab_match_changes_hold_color():
    g = _make_game()
    g.player_color_idx = 1  # LIME=11
    hold = Hold(col=1, row=1, color=LIME)
    g.holds.append(hold)
    g._process_grab(hold)
    assert hold.color == LIME


def test_process_grab_match_combo_chain():
    g = _make_game()
    g.combo = 3
    g.score = 60
    g.player_color_idx = 2  # DARK_BLUE=5
    hold = Hold(col=1, row=1, color=DARK_BLUE)
    g.holds.append(hold)
    g._process_grab(hold)
    assert g.combo == 4
    assert g.score == 60 + 40  # 10 * 4
    assert g.max_combo == 4


def test_process_grab_match_triggers_super():
    g = _make_game()
    g.combo = 3
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=1, row=1, color=RED)
    g.holds.append(hold)
    g._process_grab(hold)
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_process_grab_super_mode_3x_score():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.combo = 4
    g.score = 100
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=1, row=1, color=LIME)  # different color but super mode
    g.holds.append(hold)
    g._process_grab(hold)
    assert g.combo == 5
    assert g.score == 100 + 10 * 5 * 3  # 250


def test_process_grab_super_match_any_color():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.combo = 4
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=1, row=1, color=DARK_BLUE)  # any color matches
    g.holds.append(hold)
    g._process_grab(hold)
    assert g.combo == 5
    assert hold.color == RED  # changes to player color


def test_process_grab_mismatch_resets_combo():
    g = _make_game()
    g.combo = 5
    g.score = 100
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=1, row=1, color=LIME)  # mismatch
    g.holds.append(hold)
    g._process_grab(hold)
    assert g.combo == 0
    assert g.last_grabbed_color == -1


def test_process_grab_mismatch_adds_heat():
    g = _make_game()
    g.heat = 0.0
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=1, row=1, color=LIME)  # mismatch
    g.holds.append(hold)
    g._process_grab(hold)
    assert g.heat == HEAT_MISMATCH


def test_process_grab_mismatch_does_not_change_hold_color():
    g = _make_game()
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=1, row=1, color=LIME)
    g.holds.append(hold)
    original_color = hold.color
    g._process_grab(hold)
    assert hold.color == original_color


# ── SUPER GRIP Tests ─────────────────────────────────────────────────

def test_start_super():
    g = _make_game()
    g.super_mode = False
    g.super_timer = 0
    g._start_super()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_end_super():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 50
    g._end_super()
    assert g.super_mode is False
    assert g.super_timer == 0


def test_super_timer_decrements():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.super_timer = 100
    g._elapsed_frames = 0
    g.timer = GAME_DURATION
    g.update()
    assert g.super_timer == 99


def test_super_timer_ends_after_duration():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.super_timer = 1
    g._elapsed_frames = 0
    g.timer = GAME_DURATION
    g.update()
    assert g.super_mode is False


# ── Heat System Tests ────────────────────────────────────────────────

def test_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_clamped_at_zero():
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_clamped_at_max():
    g = _make_game()
    g.heat = 200.0
    g._update_heat()
    assert g.heat == HEAT_MAX


def test_heat_at_max_triggers_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = GAME_DURATION
    g.heat = HEAT_MAX
    g.update()
    assert g.phase == Phase.GAME_OVER


def test_heat_decay_does_not_affect_game_over_check():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = GAME_DURATION
    g.heat = HEAT_MAX + 1
    g.update()
    assert g.phase == Phase.GAME_OVER


# ── Color Cycle Tests ────────────────────────────────────────────────

def test_color_cycle_advances():
    g = _make_game()
    g.color_cycle_timer = 1
    g.player_color_idx = 0
    g._update_color_cycle()
    assert g.player_color_idx == 1
    assert g.color_cycle_timer == g._get_color_cycle_interval()


def test_color_cycle_frozen_in_super():
    g = _make_game()
    g.super_mode = True
    g.color_cycle_timer = 1
    g.player_color_idx = 0
    g._update_color_cycle()
    assert g.player_color_idx == 0


def test_color_cycle_interval_decreases_over_time():
    g = _make_game()
    g._elapsed_frames = 0
    initial = g._get_color_cycle_interval()
    g._elapsed_frames = GAME_DURATION
    final = g._get_color_cycle_interval()
    assert final < initial
    assert final == COLOR_CYCLE_MIN


def test_get_player_color():
    g = _make_game()
    g.player_color_idx = 0
    from main import COLORS
    assert COLORS[0] == RED


# ── Timer Tests ──────────────────────────────────────────────────────

def test_timer_decrements():
    g = _make_game()
    g.timer = 100
    g._update_timer()
    assert g.timer == 99


def test_timer_zero_triggers_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = 1
    g._elapsed_frames = 0
    g.update()
    assert g.phase == Phase.GAME_OVER


# ── Respawn Tests ────────────────────────────────────────────────────

def test_respawn_adds_holds_when_below_min():
    g = _make_game()
    g.holds = [Hold(col=0, row=0, color=RED)]
    g.respawn_timer = 0
    g._elapsed_frames = 0
    initial_count = len(g.holds)
    g._update_respawns()
    assert len(g.holds) > initial_count


def test_respawn_does_not_exceed_max():
    g = _make_game()
    g.holds = [Hold(col=c, row=0, color=RED) for c in range(COLS)]
    assert len(g.holds) == 8
    g.respawn_timer = 1
    g._update_respawns()
    assert len(g.holds) <= MAX_HOLDS


def test_respawn_delay_decreases_over_time():
    g = _make_game()
    g._elapsed_frames = 0
    initial = g._get_respawn_delay()
    g._elapsed_frames = GAME_DURATION
    final = g._get_respawn_delay()
    assert final < initial
    assert final == RESPAWN_DELAY_MIN


def test_min_holds_increases_over_time():
    g = _make_game()
    g._elapsed_frames = 0
    initial = g._get_min_holds()
    g._elapsed_frames = GAME_DURATION
    final = g._get_min_holds()
    assert final > initial
    assert final == MAX_HOLDS


# ── Difficulty Tests ─────────────────────────────────────────────────

def test_progress_starts_at_zero():
    g = _make_game()
    g._elapsed_frames = 0
    assert g._get_progress() == 0.0


def test_progress_ends_at_one():
    g = _make_game()
    g._elapsed_frames = GAME_DURATION
    assert g._get_progress() == 1.0


def test_progress_midpoint():
    g = _make_game()
    g._elapsed_frames = GAME_DURATION // 2
    assert g._get_progress() == 0.5


# ── Particle Tests ───────────────────────────────────────────────────

def test_spawn_particles():
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100, 100, RED, 8, 0.1)
    assert len(g.particles) == 8
    for p in g.particles:
        assert isinstance(p, Particle)
        assert p.color == RED


def test_update_particles_reduces_life():
    g = _make_game()
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=5, color=WHITE)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


def test_particles_die_and_removed():
    g = _make_game()
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=WHITE)]
    g._update_particles()
    assert len(g.particles) == 0


def test_particles_move():
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=-2.0, life=10, color=WHITE)]
    g._update_particles()
    p = g.particles[0]
    assert p.x == 101.0
    assert p.y == 98.0


# ── Floating Text Tests ──────────────────────────────────────────────

def test_add_floating_text():
    g = _make_game()
    assert len(g.floating_texts) == 0
    g._add_floating_text("TEST", 160, 120, WHITE)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"
    assert g.floating_texts[0].color == WHITE
    assert g.floating_texts[0].life == FLOAT_TEXT_LIFE


def test_update_floating_texts_reduces_life():
    g = _make_game()
    g.floating_texts = [FloatingText(x=100, y=100, text="T", life=5, color=WHITE)]
    g._update_floating_texts()
    assert g.floating_texts[0].life == 4


def test_floating_texts_removed_when_dead():
    g = _make_game()
    g.floating_texts = [FloatingText(x=100, y=100, text="T", life=1, color=WHITE)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_floating_texts_float_upward():
    g = _make_game()
    g.floating_texts = [FloatingText(x=100, y=100, text="T", life=10, color=WHITE)]
    g._update_floating_texts()
    assert g.floating_texts[0].y == 99.3


def test_match_creates_floating_text():
    g = _make_game()
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=0, row=0, color=RED)
    g.holds.append(hold)
    g._process_grab(hold)
    assert len(g.floating_texts) >= 1
    assert any("+" in ft.text for ft in g.floating_texts)


def test_mismatch_creates_floating_text():
    g = _make_game()
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=0, row=0, color=LIME)
    g.holds.append(hold)
    g._process_grab(hold)
    texts = [ft.text for ft in g.floating_texts]
    assert "WRONG!" in texts


def test_combo_creates_floating_text():
    g = _make_game()
    g.combo = 1
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=0, row=0, color=RED)
    g.holds.append(hold)
    g._process_grab(hold)
    texts = [ft.text for ft in g.floating_texts]
    assert any("COMBO" in t for t in texts)


def test_super_activation_creates_floating_text():
    g = _make_game()
    g._start_super()
    texts = [ft.text for ft in g.floating_texts]
    assert any("SUPER GRIP!" in t for t in texts)


# ── Game Over Tests ──────────────────────────────────────────────────

def test_end_game_sets_phase():
    g = _make_game()
    g.phase = Phase.PLAYING
    g._end_game()
    assert g.phase == Phase.GAME_OVER


def test_end_game_updates_best_score():
    g = _make_game()
    g.score = 500
    g.best_score = 300
    g._end_game()
    assert g.best_score == 500


def test_end_game_keeps_best_score():
    g = _make_game()
    g.score = 200
    g.best_score = 500
    g._end_game()
    assert g.best_score == 500


# ── Reset Tests ──────────────────────────────────────────────────────

def test_reset_initializes_state():
    g = _make_game()
    g.score = 9999
    g.combo = 10
    g.heat = 99
    g.super_mode = True
    g.super_timer = 100
    g.timer = 100
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=WHITE)]
    g.floating_texts = [FloatingText(x=0, y=0, text="x", life=1, color=WHITE)]

    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.super_mode is False
    assert g.timer == GAME_DURATION
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.last_grabbed_color == -1
    assert g._shake_frames == 0
    assert g._elapsed_frames == 0
    assert g.phase == Phase.PLAYING


def test_reset_preserves_best_score():
    g = _make_game()
    g.best_score = 500
    g.reset()
    assert g.best_score == 500


def test_reset_creates_holds():
    g = _make_game()
    g.reset()
    assert len(g.holds) >= MIN_HOLDS


# ── Hold Center Tests ────────────────────────────────────────────────

def test_hold_center():
    g = _make_game()
    cx, cy = g._hold_center(0, 0)
    assert cx == GRID_X + CELL // 2
    assert cy == GRID_Y + CELL // 2


def test_hold_center_offset():
    g = _make_game()
    cx, cy = g._hold_center(3, 5)
    assert cx == GRID_X + 3 * CELL + CELL // 2
    assert cy == GRID_Y + 5 * CELL + CELL // 2


# ── Data Class Tests ─────────────────────────────────────────────────

def test_hold_creation():
    h = Hold(col=1, row=2, color=RED)
    assert h.col == 1
    assert h.row == 2
    assert h.color == RED


def test_particle_creation():
    p = Particle(x=1.0, y=2.0, vx=0.5, vy=-0.5, life=10, color=WHITE)
    assert p.x == 1.0
    assert p.y == 2.0
    assert p.life == 10
    assert p.color == WHITE


def test_floating_text_creation():
    ft = FloatingText(x=100, y=200, text="HELLO", life=20, color=LIME)
    assert ft.x == 100
    assert ft.y == 200
    assert ft.text == "HELLO"
    assert ft.life == 20
    assert ft.color == LIME


# ── Phase Enum Tests ─────────────────────────────────────────────────

def test_phase_enum():
    assert Phase.TITLE.value is not None
    assert Phase.PLAYING.value is not None
    assert Phase.GAME_OVER.value is not None
    assert len(Phase) == 3


# ── Shake Tests ─────────────────────────────────────────────────────

def test_shake_frames_set_on_mismatch():
    g = _make_game()
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=0, row=0, color=LIME)
    g.holds.append(hold)
    g._process_grab(hold)
    assert g._shake_frames == 8


def test_shake_frames_decrements():
    g = _make_game()
    g._shake_frames = 5
    g.phase = Phase.PLAYING
    g.timer = GAME_DURATION
    g.update()
    assert g._shake_frames == 4


# ── Match Particle Creation Tests ────────────────────────────────────

def test_match_spawns_particles():
    g = _make_game()
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=0, row=0, color=RED)
    g.holds.append(hold)
    g._process_grab(hold)
    assert len(g.particles) == PARTICLE_COUNT_MATCH


def test_super_grab_spawns_particles():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=0, row=0, color=LIME)
    g.holds.append(hold)
    g._process_grab(hold)
    assert len(g.particles) == PARTICLE_COUNT_SUPER


def test_mismatch_spawns_particles():
    g = _make_game()
    g.player_color_idx = 0  # RED=8
    hold = Hold(col=0, row=0, color=LIME)
    g.holds.append(hold)
    g._process_grab(hold)
    assert len(g.particles) == PARTICLE_COUNT_MISMATCH
