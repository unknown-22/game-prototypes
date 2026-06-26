"""test_imports.py — Headless logic tests for NONOGRAM SURGE."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # type: ignore[import-not-found]
    CELL_COLORS,
    CELL_COLOR_NAMES,
    GAME_OVER,
    GRID_X,
    GRID_Y,
    PLAYING,
    TITLE,
    FloatingText,
    Game,
    HintRun,
    Particle,
    _compute_hints,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.SCREEN_W = 320
    g.SCREEN_H = 240
    g.GRID_X = GRID_X
    g.GRID_Y = GRID_Y
    g.CELL = 20
    g.ROWS = 8
    g.COLS = 8
    g.phase = TITLE
    g.selected_color = 0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = 120.0
    g.super_active = False
    g.super_timer = 0.0
    g.solved_count = 0
    g.total_cells = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.flash_timer = 0.0
    g.frame = 0
    g.puzzle_index = 0
    g._last_filled_color = None
    # Load all puzzles so _puzzles is populated
    g._puzzles = []
    g._load_all_puzzles()
    g.reset()
    return g


# ── Data Structures ──


def test_hint_run_fields() -> None:
    h = HintRun(color_idx=2, count=3)
    assert h.color_idx == 2
    assert h.count == 3


def test_particle_fields() -> None:
    p = Particle(x=1.0, y=2.0, vx=0.5, vy=-0.3, color=7, life=15)
    assert p.x == 1.0
    assert p.y == 2.0
    assert p.color == 7
    assert p.life == 15


def test_floating_text_fields() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+10", color=7, life=30)
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == 7


# ── Initialization ──


def test_game_initial_state() -> None:
    g = _make_game()
    assert g.phase == TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_active is False
    assert g.super_timer == 0.0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.puzzle_index == 0


def test_puzzles_loaded() -> None:
    g = _make_game()
    assert len(g._puzzles) == 3
    assert g._puzzles[0].name == "DIAMOND"
    assert g._puzzles[1].name == "HEART"
    assert g._puzzles[2].name == "CROSS"


def test_puzzle_dimensions() -> None:
    g = _make_game()
    for p in g._puzzles:
        assert len(p.solution) == 8
        assert all(len(row) == 8 for row in p.solution)
        assert len(p.row_hints) == 8
        assert len(p.col_hints) == 8


# ── Compute Hints ──


def test_compute_hints_simple() -> None:
    solution = [
        [-1,  0,  0, -1],
        [ 1,  1, -1, -1],
        [-1, -1,  2, -1],
        [ 3, -1, -1,  3],
    ]
    row_hints, col_hints = _compute_hints(solution)
    # Row 0: one run of color 0 count 2
    assert len(row_hints[0]) == 1
    assert row_hints[0][0].color_idx == 0
    assert row_hints[0][0].count == 2
    # Row 1: one run of color 1 count 2
    assert len(row_hints[1]) == 1
    assert row_hints[1][0].color_idx == 1
    assert row_hints[1][0].count == 2
    # Row 2: one run of color 2 count 1
    assert len(row_hints[2]) == 1
    assert row_hints[2][0].color_idx == 2
    assert row_hints[2][0].count == 1
    # Row 3: two runs: color 3 count 1, then color 3 count 1
    assert len(row_hints[3]) == 2
    assert row_hints[3][0].color_idx == 3 and row_hints[3][0].count == 1
    assert row_hints[3][1].color_idx == 3 and row_hints[3][1].count == 1


def test_compute_hints_columns() -> None:
    solution = [
        [0, -1],
        [0,  1],
    ]
    row_hints, col_hints = _compute_hints(solution)
    # Col 0: one run of color 0 count 2
    assert len(col_hints[0]) == 1
    assert col_hints[0][0].color_idx == 0
    assert col_hints[0][0].count == 2
    # Col 1: one run of color 1 count 1
    assert len(col_hints[1]) == 1
    assert col_hints[1][0].color_idx == 1
    assert col_hints[1][0].count == 1


def test_compute_hints_empty_row() -> None:
    solution = [
        [-1, -1, -1],
        [ 0,  0,  0],
    ]
    row_hints, col_hints = _compute_hints(solution)
    assert len(row_hints[0]) == 0
    assert len(row_hints[1]) == 1


def test_compute_hints_alternating_colors() -> None:
    solution = [
        [0, 1, 0],
    ]
    row_hints, _ = _compute_hints(solution)
    assert len(row_hints[0]) == 3
    assert row_hints[0][0].color_idx == 0 and row_hints[0][0].count == 1
    assert row_hints[0][1].color_idx == 1 and row_hints[0][1].count == 1
    assert row_hints[0][2].color_idx == 0 and row_hints[0][2].count == 1


# ── Handle Click ──


def test_handle_click_correct() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0  # RED
    # Puzzle 0 DIAMOND: row 3, col 0 = 0 (RED)
    assert g.puzzle.solution[3][0] == 0
    g._handle_click(3, 0)
    assert g.grid[3][0] == 0  # filled
    assert g.combo == 1
    assert g.score == 10 + 1 * 2  # 12
    assert g.solved_count == 1


def test_handle_click_combo_increases() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0
    # Puzzle 0 DIAMOND: row 3 col 0=0, row 3 col 1=0
    g._handle_click(3, 0)  # combo=1
    g._handle_click(3, 1)  # same color, combo=2
    assert g.combo == 2
    assert g.score == 12 + 14  # first: 12, second: 10+2*2=14, total=26
    assert g.solved_count == 2


def test_handle_click_different_color_resets_combo() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0
    # DIAMOND: row 3 col 0=0 (RED)
    g._handle_click(3, 0)  # combo=1
    assert g.combo == 1
    # Change color
    g.selected_color = 1  # GREEN
    # DIAMOND: row 5 col 6=1 (GREEN)
    assert g.puzzle.solution[5][6] == 1
    g._handle_click(5, 6)
    assert g.combo == 1  # reset to 1 (new color)
    assert g.solved_count == 2


def test_handle_click_wrong_empty_cell() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0
    # DIAMOND: row 0 col 0 = -1 (empty)
    assert g.puzzle.solution[0][0] == -1
    g._handle_click(0, 0)
    assert g.grid[0][0] == -1  # not filled
    assert g.combo == 0
    assert g.heat == 15.0
    assert g.shake_frames == 10
    assert g.solved_count == 0


def test_handle_click_wrong_color() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 1  # GREEN
    # DIAMOND: row 3 col 0 = 0 (RED)
    assert g.puzzle.solution[3][0] == 0
    g._handle_click(3, 0)
    assert g.grid[3][0] == -1  # not filled
    assert g.combo == 0
    assert g.heat == 10.0
    assert g.shake_frames == 5


def test_handle_click_already_filled_ignored() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0
    g._handle_click(3, 0)  # correct fill
    prev_score = g.score
    prev_combo = g.combo
    prev_solved = g.solved_count
    g._handle_click(3, 0)  # click same cell again
    assert g.score == prev_score
    assert g.combo == prev_combo
    assert g.solved_count == prev_solved


# ── Combo Tracking ──


def test_max_combo_tracked() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0
    # Fill 3 consecutive RED cells in DIAMOND puzzle
    # row 3 col 0,1,2 all RED (0)
    g._handle_click(3, 0)  # combo=1, max=1
    g._handle_click(3, 1)  # combo=2, max=2
    g._handle_click(3, 2)  # combo=3, max=3
    assert g.max_combo == 3
    # Wrong click breaks combo but max persists
    g._handle_click(0, 0)  # combo=0
    assert g.combo == 0
    assert g.max_combo == 3


def test_max_combo_persists_after_color_switch() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0
    g._handle_click(3, 0)  # RED, combo=1
    g._handle_click(3, 1)  # RED, combo=2
    assert g.max_combo == 2
    g.selected_color = 1
    g._handle_click(5, 6)  # GREEN, combo=1 (reset)
    assert g.combo == 1
    assert g.max_combo == 2


# ── SUPER Activation ──


def test_combo_5_activates_super() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0
    # Need 5 consecutive correct RED fills
    # DIAMOND: row 3 col 0,1,2,3,4,5,6 are all RED (0)
    for c in range(5):
        g._handle_click(3, c)
    assert g.combo == 5
    assert g.super_active is True
    assert g.super_timer == 5.0
    assert g.flash_timer == 0.3


def test_super_not_activated_below_5() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0
    for c in range(4):
        g._handle_click(3, c)
    assert g.combo == 4
    assert g.super_active is False


def test_super_reveals_unsolved_row() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0
    solved_before = g.solved_count
    # Activate super
    for c in range(5):
        g._handle_click(3, c)
    assert g.super_active is True
    # SUPER should have revealed cells from an unsolved row
    assert g.solved_count > solved_before + 5


def test_super_timer_counts_down() -> None:
    g = _make_game()
    g._start_game()
    g.super_active = True
    g.super_timer = 2.0
    g._update_super(0.5)
    assert g.super_timer == 1.5
    g._update_super(1.5)
    assert g.super_timer == 0.0
    assert g.super_active is False


def test_super_ends_after_duration() -> None:
    g = _make_game()
    g._start_game()
    g.super_active = True
    g.super_timer = 0.01
    g._update_super(0.02)
    assert g.super_timer == 0.0
    assert g.super_active is False


# ── Right Click ──


def test_handle_right_click_clears_cell() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0
    g._handle_click(3, 0)  # fill
    assert g.grid[3][0] == 0
    assert g.solved_count == 1
    g._handle_right_click(3, 0)  # clear
    assert g.grid[3][0] == -1
    assert g.solved_count == 0


def test_handle_right_click_empty_cell_ignored() -> None:
    g = _make_game()
    g._start_game()
    g._handle_right_click(3, 0)  # empty cell
    assert g.grid[3][0] == -1
    assert g.solved_count == 0


# ── Heat System ──


def test_heat_decays_over_time() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat == 9.98  # 10 - 0.02


def test_heat_does_not_go_negative() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


def test_heat_at_100_game_over() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 100.0
    g._update_heat()
    assert g.phase == GAME_OVER


def test_heat_capped_at_100() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 95.0
    g.selected_color = 0
    g._handle_click(0, 0)  # adds 15, should cap at 100
    assert g.heat == 100.0


# ── Puzzle Completion ──


def test_puzzle_complete_adds_bonus_score() -> None:
    g = _make_game()
    g._start_game()
    initial_score = g.score
    # Manually set total_cells small and trigger completion
    g.solved_count = g.total_cells - 1
    # Find and fill the last cell
    for r in range(8):
        for c in range(8):
            if g.puzzle.solution[r][c] != -1 and g.grid[r][c] == -1:
                g.selected_color = g.puzzle.solution[r][c]
                g._handle_click(r, c)
                break
        else:
            continue
        break
    # Should have completed and scored bonus + loaded next puzzle
    expected_bonus = 100 * 1  # puzzle_index was 0 when completing puzzle 0
    assert g.score >= initial_score + expected_bonus


# ── Grid Cell From Mouse ──


def test_grid_cell_from_mouse_valid() -> None:
    g = _make_game()
    g._start_game()
    # GRID_X=80, GRID_Y=55, CELL=20
    # Cell (0,0) center would be at (90, 65)
    cell = g._grid_cell_from_mouse(90, 65)
    assert cell == (0, 0)


def test_grid_cell_from_mouse_corner() -> None:
    g = _make_game()
    g._start_game()
    # Bottom-right cell (7,7)
    cell = g._grid_cell_from_mouse(GRID_X + 7 * 20 + 10, GRID_Y + 7 * 20 + 10)
    assert cell == (7, 7)


def test_grid_cell_from_mouse_outside_x() -> None:
    g = _make_game()
    g._start_game()
    assert g._grid_cell_from_mouse(10, 60) is None  # left of grid
    assert g._grid_cell_from_mouse(300, 60) is None  # right of grid


def test_grid_cell_from_mouse_outside_y() -> None:
    g = _make_game()
    g._start_game()
    assert g._grid_cell_from_mouse(90, 10) is None  # above grid
    assert g._grid_cell_from_mouse(90, 230) is None  # below grid


# ── Color Palette Selection ──


def test_select_color_from_palette_valid() -> None:
    g = _make_game()
    g._start_game()
    # Button 0: x=20 to 80, y=225 to 240
    assert g._select_color_from_palette(50, 230) == 0
    # Button 1: x=95 to 155
    assert g._select_color_from_palette(125, 230) == 1
    # Button 2: x=170 to 230
    assert g._select_color_from_palette(200, 230) == 2
    # Button 3: x=245 to 305
    assert g._select_color_from_palette(275, 230) == 3


def test_select_color_from_palette_outside() -> None:
    g = _make_game()
    g._start_game()
    assert g._select_color_from_palette(10, 230) is None  # left of palette
    assert g._select_color_from_palette(310, 230) is None  # right of palette
    assert g._select_color_from_palette(50, 200) is None  # above palette


# ── Particles ──


def test_spawn_particles_creates_correct_count() -> None:
    g = _make_game()
    g._start_game()
    g._spawn_particles(100.0, 100.0, 8, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == 8


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g._start_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=1),
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=0),
    ]
    g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_keeps_alive() -> None:
    g = _make_game()
    g._start_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=1.0, vy=-1.0, color=8, life=3),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    p = g.particles[0]
    assert p.x == 1.0
    assert p.y < -0.79  # -1.0 + gravity (0.2) but then rounded?
    assert p.life == 2


# ── Floating Texts ──


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._start_game()
    g._spawn_floating_text(100.0, 50.0, "+12", 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+12"
    assert g.floating_texts[0].color == 7


def test_update_floating_texts() -> None:
    g = _make_game()
    g._start_game()
    g.floating_texts = [
        FloatingText(x=0.0, y=0.0, text="A", color=7, life=1),
        FloatingText(x=0.0, y=0.0, text="B", color=7, life=3),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "B"
    assert ft.life == 2
    assert ft.y == -1.0  # moved up by 1


# ── Reset / Start Game ──


def test_start_game_transitions_to_playing() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.timer == 120.0


def test_reset_clears_all_state() -> None:
    g = _make_game()
    g._start_game()
    g.score = 500
    g.combo = 5
    g.max_combo = 7
    g.heat = 80.0
    g.super_active = True
    g.super_timer = 3.0
    g._last_filled_color = 2
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=5)]
    g.floating_texts = [FloatingText(x=0.0, y=0.0, text="X", color=7, life=5)]
    g.shake_frames = 10

    g.reset()
    assert g.phase == TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_active is False
    assert g.super_timer == 0.0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.shake_frames == 0


def test_reset_preserves_puzzles() -> None:
    g = _make_game()
    g._start_game()
    g.reset()
    assert len(g._puzzles) == 3
    assert g.puzzle.name == "DIAMOND"


# ── Load Puzzle ──


def test_load_puzzle_resets_grid() -> None:
    g = _make_game()
    g._start_game()
    g.selected_color = 0
    g._handle_click(3, 0)  # fill cell
    g._load_puzzle(1)  # load HEART
    assert g.puzzle_index == 1
    assert g.puzzle.name == "HEART"
    assert g.solved_count == 0
    assert g.combo == 0
    assert all(cell == -1 for row in g.grid for cell in row)


# ── Constants ──


def test_cell_colors_length() -> None:
    assert len(CELL_COLORS) == 4
    assert len(CELL_COLOR_NAMES) == 4


def test_phase_constants() -> None:
    assert TITLE == 0
    assert PLAYING == 1
    assert GAME_OVER == 2


# ── Run ──

if __name__ == "__main__":
    import inspect as _inspect

    _tests = [
        obj
        for _name, obj in _inspect.getmembers(sys.modules[__name__])
        if callable(obj) and _name.startswith("test_")
    ]
    passed = 0
    failed = 0
    for _test in _tests:
        try:
            _test()
            print(f"  PASS {_test.__name__}")
            passed += 1
        except Exception as _e:
            print(f"  FAIL {_test.__name__}: {_e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(_tests)} total")
    if failed > 0:
        sys.exit(1)
