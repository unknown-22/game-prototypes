"""test_imports.py -- Headless logic tests for 296_dig_chain."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.absolute()))

from main import (
    SCREEN_W, SCREEN_H, FPS,
    COLS, ROWS, CELL, GRID_X, GRID_Y,
    TIMER_MAX, SUPER_DURATION, COMBO_THRESHOLD, NUM_COLORS,
    DIRT_COLORS,
    HEAT_MISMATCH, HEAT_DECAY, HEAT_MAX,
    FOSSIL_BONUS, FOSSIL_CHANCE, FOSSIL_SPAWN_INTERVAL,
    PARTICLE_COUNT_DIG, PARTICLE_COUNT_SUPER, PARTICLE_COUNT_FOSSIL,
    FLOAT_TEXT_LIFE,
    BLACK, WHITE, RED, YELLOW, LIME, CYAN, GRAY,
    Phase, Particle, FloatingText, Game,
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
    g.last_color = None
    g.timer = TIMER_MAX
    g.super_timer = 0
    g.super_mode = False
    g.cells = []
    g.particles = []
    g.floating_texts = []
    g._shake_frames = 0
    g._fossil_spawn_counter = 0
    g._frame = 0
    g.phase = Phase.PLAYING
    g._init_grid()
    return g


# ── Constants Tests ──────────────────────────────────────────────────

def test_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert FPS == 30
    assert COLS == 8
    assert ROWS == 6
    assert CELL == 28
    assert GRID_X == (320 - 8 * 28) // 2
    assert GRID_Y == (240 - 6 * 28) // 2 - 14
    assert TIMER_MAX == 1800
    assert SUPER_DURATION == 300
    assert COMBO_THRESHOLD == 4
    assert NUM_COLORS == 4
    assert HEAT_MISMATCH == 15.0
    assert HEAT_DECAY == 0.02
    assert HEAT_MAX == 100.0
    assert FOSSIL_BONUS == 50
    assert FOSSIL_CHANCE == 0.15
    assert FOSSIL_SPAWN_INTERVAL == 120
    assert PARTICLE_COUNT_DIG == 8
    assert PARTICLE_COUNT_SUPER == 20
    assert PARTICLE_COUNT_FOSSIL == 4
    assert FLOAT_TEXT_LIFE == 45


def test_color_constants():
    assert DIRT_COLORS == (8, 11, 12, 10)
    assert BLACK == 0
    assert RED == 8
    assert LIME == 11
    assert CYAN == 12
    assert YELLOW == 10
    assert WHITE == 7
    assert GRAY == 13


# ── Grid Tests ───────────────────────────────────────────────────────

def test_grid_initialized_correct_size():
    g = _make_game()
    assert len(g.cells) == COLS
    for col in g.cells:
        assert len(col) == ROWS


def test_grid_cells_have_color_excavated_fossil():
    g = _make_game()
    for col in range(COLS):
        for row in range(ROWS):
            cell = g.cells[col][row]
            assert "color" in cell
            assert "excavated" in cell
            assert "fossil_bonus" in cell
            assert isinstance(cell["color"], int)
            assert 0 <= cell["color"] < NUM_COLORS
            assert cell["excavated"] is False
            assert isinstance(cell["fossil_bonus"], bool)


def test_get_cell_valid():
    g = _make_game()
    cell = g._get_cell(0, 0)
    assert cell is not None
    assert cell["excavated"] is False


def test_get_cell_out_of_bounds():
    g = _make_game()
    assert g._get_cell(-1, 0) is None
    assert g._get_cell(0, -1) is None
    assert g._get_cell(COLS, 0) is None
    assert g._get_cell(0, ROWS) is None


# ── Click Handling Tests ─────────────────────────────────────────────

def test_handle_click_out_of_bounds():
    g = _make_game()
    valid, score = g._handle_click(-1, 0)
    assert valid is False
    assert score == 0
    valid, score = g._handle_click(COLS, 0)
    assert valid is False
    assert score == 0


def test_handle_click_excavates_cell():
    g = _make_game()
    cell = g.cells[0][0]
    assert cell["excavated"] is False
    g._handle_click(0, 0)
    assert cell["excavated"] is True


def test_handle_click_already_dug_rejected():
    g = _make_game()
    g._handle_click(0, 0)
    valid, score = g._handle_click(0, 0)
    assert valid is False
    assert score == 0


def test_handle_click_increments_combo():
    g = _make_game()
    g.last_color = None
    g._handle_click(0, 0)
    assert g.combo == 1


def test_handle_click_same_color_extends_combo():
    g = _make_game()
    g._handle_click(0, 0)
    cell_color = g.cells[0][0]["color"]
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["color"] = cell_color
            g.cells[col][row]["excavated"] = False
            g.cells[col][row]["fossil_bonus"] = False

    g.last_color = cell_color
    g.combo = 1
    g._handle_click(0, 1)
    assert g.combo == 2


def test_handle_click_wrong_color_resets_combo():
    g = _make_game()
    g._handle_click(0, 0)
    cell_color = g.cells[0][0]["color"]
    wrong_color = (cell_color + 1) % NUM_COLORS
    g.cells[0][1]["color"] = wrong_color
    g.cells[0][1]["excavated"] = False
    g._handle_click(0, 1)
    assert g.combo == 0
    assert g.last_color is None


def test_handle_click_wrong_color_adds_heat():
    g = _make_game()
    g.heat = 0.0
    g._handle_click(0, 0)
    cell_color = g.cells[0][0]["color"]
    wrong_color = (cell_color + 1) % NUM_COLORS
    g.cells[0][1]["color"] = wrong_color
    g.cells[0][1]["excavated"] = False
    g._handle_click(0, 1)
    assert g.heat == HEAT_MISMATCH


def test_handle_click_gives_score():
    g = _make_game()
    g.score = 0
    g.cells[0][0]["fossil_bonus"] = False
    g._handle_click(0, 0)
    assert g.score == 10  # 10 * combo(1)


def test_handle_click_combo_chain_score():
    g = _make_game()
    cell_color = g.cells[0][0]["color"]
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["color"] = cell_color
            g.cells[col][row]["excavated"] = False
            g.cells[col][row]["fossil_bonus"] = False

    g._handle_click(0, 0)
    g._handle_click(0, 1)
    g._handle_click(0, 2)
    assert g.combo == 3
    assert g.score == 10 + 20 + 30  # 10*1 + 10*2 + 10*3


def test_handle_click_triggers_super_at_threshold():
    g = _make_game()
    cell_color = g.cells[0][0]["color"]
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["color"] = cell_color
            g.cells[col][row]["excavated"] = False
            g.cells[col][row]["fossil_bonus"] = False

    g._handle_click(0, 0)
    g._handle_click(0, 1)
    g._handle_click(0, 2)
    g._handle_click(0, 3)
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_handle_click_super_any_color_match():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.last_color = 0
    g.combo = 4
    g.cells[0][0]["color"] = 2  # different color
    g.cells[0][0]["excavated"] = False
    g._handle_click(0, 0)
    assert g.combo == 5


def test_handle_click_super_3x_score():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.last_color = 0
    g.combo = 4
    g.score = 100
    g.cells[0][0]["color"] = 0
    g.cells[0][0]["excavated"] = False
    g.cells[0][0]["fossil_bonus"] = False
    g._handle_click(0, 0)
    assert g.score == 100 + 10 * 5 * 3  # 250


def test_handle_click_max_combo_tracks():
    g = _make_game()
    cell_color = g.cells[0][0]["color"]
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["color"] = cell_color
            g.cells[col][row]["excavated"] = False
            g.cells[col][row]["fossil_bonus"] = False

    g._handle_click(0, 0)
    g._handle_click(0, 1)
    g._handle_click(0, 2)
    assert g.max_combo == 3

    wrong_color = (cell_color + 1) % NUM_COLORS
    g.cells[0][3]["color"] = wrong_color
    g._handle_click(0, 3)
    assert g.max_combo == 3  # should not decrease


# ── Fossil Tests ─────────────────────────────────────────────────────

def test_fossil_bonus_gives_score():
    g = _make_game()
    g.score = 0
    g.cells[0][0]["fossil_bonus"] = True
    g.cells[0][0]["excavated"] = False
    g._handle_click(0, 0)
    assert g.score == 10 + FOSSIL_BONUS


def test_fossil_bonus_only_once():
    g = _make_game()
    g.cells[0][0]["fossil_bonus"] = True
    g.cells[0][0]["excavated"] = False
    g._handle_click(0, 0)
    assert g.cells[0][0]["fossil_bonus"] is False


def test_spawn_fossil_adds_to_undug():
    g = _make_game()
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["fossil_bonus"] = False
            g.cells[col][row]["excavated"] = False
    g._spawn_fossil()
    fossil_count = sum(
        1 for col in range(COLS) for row in range(ROWS) if g.cells[col][row]["fossil_bonus"]
    )
    assert fossil_count == 1


def test_spawn_fossil_skips_excavated():
    g = _make_game()
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["fossil_bonus"] = False
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["excavated"] = True
    g.cells[0][0]["excavated"] = False
    g._spawn_fossil()
    assert g.cells[0][0]["fossil_bonus"] is True


def test_spawn_fossil_no_undug_noop():
    g = _make_game()
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["fossil_bonus"] = False
            g.cells[col][row]["excavated"] = True
    prior = g.cells[0][0]["fossil_bonus"]
    g._spawn_fossil()
    assert g.cells[0][0]["fossil_bonus"] == prior


# ── SUPER EXCAVATION Tests ───────────────────────────────────────────

def test_activate_super():
    g = _make_game()
    g.super_mode = False
    g.super_timer = 0
    g._activate_super()
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
    g.timer = TIMER_MAX
    g.update()
    assert g.super_timer == 99


def test_super_timer_ends():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.super_timer = 1
    g.timer = TIMER_MAX
    g.update()
    assert g.super_mode is False


# ── Heat Tests ───────────────────────────────────────────────────────

def test_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._update_heat(False)
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_clamped_at_zero():
    g = _make_game()
    g.heat = 0.0
    g._update_heat(False)
    assert g.heat == 0.0


def test_heat_add_on_mismatch():
    g = _make_game()
    g.heat = 30.0
    g._update_heat(True)
    assert g.heat == 30.0 + HEAT_MISMATCH


def test_heat_cap_on_mismatch():
    g = _make_game()
    g.heat = 90.0
    g._update_heat(True)
    assert g.heat == HEAT_MAX


def test_heat_trigger_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = TIMER_MAX
    g.heat = HEAT_MAX
    g.update()
    assert g.phase == Phase.GAME_OVER


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
    g.update()
    assert g.phase == Phase.GAME_OVER


def test_timer_clamped_at_zero():
    g = _make_game()
    g.timer = 0
    g._update_timer()
    assert g.timer == 0


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


def test_check_game_over_timer():
    g = _make_game()
    g.timer = 0
    assert g._check_game_over() is True


def test_check_game_over_heat():
    g = _make_game()
    g.heat = HEAT_MAX
    assert g._check_game_over() is True


def test_check_game_over_false():
    g = _make_game()
    g.timer = 100
    g.heat = 50
    assert g._check_game_over() is False


# ── Reset Tests ──────────────────────────────────────────────────────

def test_reset_initializes_state():
    g = _make_game()
    g.score = 9999
    g.combo = 10
    g.max_combo = 5
    g.heat = 99
    g.super_mode = True
    g.super_timer = 100
    g.timer = 100
    g.last_color = 2
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=WHITE)]
    g.floating_texts = [FloatingText(x=0, y=0, text="x", life=1, color=WHITE)]
    g._shake_frames = 10

    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.super_mode is False
    assert g.timer == TIMER_MAX
    assert g.last_color is None
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g._shake_frames == 0
    assert g.phase == Phase.PLAYING


def test_reset_preserves_best_score():
    g = _make_game()
    g.best_score = 500
    g.reset()
    assert g.best_score == 500


def test_reset_creates_grid():
    g = _make_game()
    g.reset()
    assert len(g.cells) == COLS
    assert len(g.cells[0]) == ROWS


# ── Cell Center Tests ────────────────────────────────────────────────

def test_cell_center():
    g = _make_game()
    cx, cy = g._cell_center(0, 0)
    assert cx == GRID_X + CELL // 2
    assert cy == GRID_Y + CELL // 2


def test_cell_center_offset():
    g = _make_game()
    cx, cy = g._cell_center(3, 5)
    assert cx == GRID_X + 3 * CELL + CELL // 2
    assert cy == GRID_Y + 5 * CELL + CELL // 2


# ── Nearby Fossil Tests ──────────────────────────────────────────────

def test_has_nearby_fossil_false_when_none():
    g = _make_game()
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["fossil_bonus"] = False
    assert g._has_nearby_fossil(0, 0) is False


def test_has_nearby_fossil_true_when_adjacent():
    g = _make_game()
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["fossil_bonus"] = False
            g.cells[col][row]["excavated"] = False
    g.cells[1][0]["fossil_bonus"] = True
    assert g._has_nearby_fossil(0, 0) is True


def test_has_nearby_fossil_skips_excavated():
    g = _make_game()
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["fossil_bonus"] = False
            g.cells[col][row]["excavated"] = False
    g.cells[1][0]["fossil_bonus"] = True
    g.cells[1][0]["excavated"] = True
    assert g._has_nearby_fossil(0, 0) is False


def test_has_nearby_fossil_far_away():
    g = _make_game()
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["fossil_bonus"] = False
            g.cells[col][row]["excavated"] = False
    g.cells[5][5]["fossil_bonus"] = True
    assert g._has_nearby_fossil(0, 0) is False


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


def test_click_spawns_dig_particles():
    g = _make_game()
    g.cells[0][0]["fossil_bonus"] = False
    g._handle_click(0, 0)
    assert len(g.particles) == PARTICLE_COUNT_DIG


def test_super_click_spawns_super_particles():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.last_color = 0
    g.combo = 4
    g.cells[0][0]["color"] = 0
    g.cells[0][0]["excavated"] = False
    g.cells[0][0]["fossil_bonus"] = False
    g._handle_click(0, 0)
    assert len(g.particles) == PARTICLE_COUNT_SUPER


def test_fossil_spawns_extra_particles():
    g = _make_game()
    g.cells[0][0]["fossil_bonus"] = True
    g.cells[0][0]["excavated"] = False
    g._handle_click(0, 0)
    assert len(g.particles) == PARTICLE_COUNT_DIG + PARTICLE_COUNT_FOSSIL


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
    assert g.floating_texts[0].y == 99.0


def test_match_creates_floating_text():
    g = _make_game()
    g.cells[0][0]["fossil_bonus"] = False
    g._handle_click(0, 0)
    assert len(g.floating_texts) >= 1
    assert any("+10" in ft.text for ft in g.floating_texts)


def test_super_activation_creates_floating_text():
    g = _make_game()
    g._activate_super()
    texts = [ft.text for ft in g.floating_texts]
    assert any("SUPER EXCAVATION!" in t for t in texts)


# ── Data Class Tests ─────────────────────────────────────────────────

def test_particle_creation():
    p = Particle(x=1.0, y=2.0, vx=0.5, vy=-0.5, life=10, color=WHITE)
    assert p.x == 1.0
    assert p.y == 2.0
    assert p.life == 10
    assert p.color == WHITE
    assert p.size == 2


def test_floating_text_creation():
    ft = FloatingText(x=100, y=200, text="HELLO", life=20, color=LIME)
    assert ft.x == 100
    assert ft.y == 200
    assert ft.text == "HELLO"
    assert ft.life == 20
    assert ft.color == LIME
    assert ft.vy == -1.0


# ── Phase Enum Tests ─────────────────────────────────────────────────

def test_phase_enum():
    assert Phase.TITLE.value is not None
    assert Phase.PLAYING.value is not None
    assert Phase.GAME_OVER.value is not None
    assert len(Phase) == 3


# ── Shake Tests ─────────────────────────────────────────────────────

def test_mismatch_sets_shake():
    g = _make_game()
    g._handle_click(0, 0)
    cell_color = g.cells[0][0]["color"]
    wrong_color = (cell_color + 1) % NUM_COLORS
    g.cells[0][1]["color"] = wrong_color
    g.cells[0][1]["excavated"] = False
    g._handle_click(0, 1)
    assert g._shake_frames == 10


def test_shake_decrements():
    g = _make_game()
    g._shake_frames = 5
    g.phase = Phase.PLAYING
    g.timer = TIMER_MAX
    g.update()
    assert g._shake_frames == 4


# ── Fossil Spawn Timer Tests ─────────────────────────────────────────

def test_fossil_spawns_periodically():
    g = _make_game()
    for col in range(COLS):
        for row in range(ROWS):
            g.cells[col][row]["fossil_bonus"] = False
            g.cells[col][row]["excavated"] = False
    # advance past interval
    g.phase = Phase.PLAYING
    g._fossil_spawn_counter = FOSSIL_SPAWN_INTERVAL - 1
    g.timer = TIMER_MAX
    g.update()
    fossil_count = sum(
        1 for col in range(COLS) for row in range(ROWS) if g.cells[col][row]["fossil_bonus"]
    )
    assert fossil_count == 1
    assert g._fossil_spawn_counter == 0
