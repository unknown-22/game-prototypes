"""test_imports.py — Headless logic tests for GRID CHAIN."""
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/267_grid_chain")
from main import (  # noqa: E402
    Cell,
    FloatingText,
    Game,
    Particle,
    Phase,
    COLORS,
    COLOR_NAMES,
    GAME_DURATION,
    GIVENS_COUNT,
    GRID_COLS,
    GRID_ROWS,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    HEAT_TIME_PRESSURE,
    ROUND_CLEAR_FRAMES,
    SUPER_DURATION,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.grid = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.round_num = 0
    g.super_timer = 0
    g.round_clear_timer = 0
    g.timer = GAME_DURATION
    g.particles = []
    g.floating_texts = []
    g._selected_color = 0
    g._prev_color = 0
    g.best_score = 0
    g._reset_game()
    return g


class TestCell:
    def test_defaults(self) -> None:
        c = Cell()
        assert c.color == 0
        assert c.locked is False

    def test_locked(self) -> None:
        c = Cell(color=8, locked=True)
        assert c.locked is True
        assert c.color == 8


class TestParticle:
    def test_creation(self) -> None:
        p = Particle(10.0, 20.0, 1.0, -1.0, 15, 8)
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.vx == 1.0
        assert p.vy == -1.0
        assert p.life == 15
        assert p.color == 8


class TestFloatingText:
    def test_creation(self) -> None:
        ft = FloatingText(100.0, 80.0, "+50", 30, 7)
        assert ft.x == 100.0
        assert ft.y == 80.0
        assert ft.text == "+50"
        assert ft.life == 30
        assert ft.color == 7


class TestGridGeneration:
    def test_new_round_creates_empty_grid(self) -> None:
        g = _make_game()
        assert len(g.grid) == GRID_ROWS
        assert len(g.grid[0]) == GRID_COLS
        for row in g.grid:
            for cell in row:
                assert isinstance(cell, Cell)

    def test_givens_count(self) -> None:
        g = _make_game()
        locked_count = 0
        for row in g.grid:
            for cell in row:
                if cell.locked:
                    locked_count += 1
        assert locked_count == GIVENS_COUNT

    def test_givens_no_conflicts(self) -> None:
        g = _make_game()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                cell = g.grid[row][col]
                if cell.color != 0:
                    assert g._is_valid_placement(col, row, cell.color)

    def test_new_round_increments_round(self) -> None:
        g = _make_game()
        assert g.round_num == 1
        g._new_round()
        assert g.round_num == 2

    def test_new_round_resets_grid(self) -> None:
        g = _make_game()
        g._new_round()
        filled = sum(1 for row in g.grid for c in row if c.color != 0)
        assert filled > 0


class TestValidation:
    def test_valid_placement_empty_grid(self) -> None:
        g = _make_game()
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        assert g._is_valid_placement(0, 0, 8) is True

    def test_row_conflict(self) -> None:
        g = _make_game()
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g.grid[0][0].color = 8
        assert g._is_valid_placement(1, 0, 8) is False

    def test_column_conflict(self) -> None:
        g = _make_game()
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g.grid[0][0].color = 8
        assert g._is_valid_placement(0, 1, 8) is False

    def test_valid_different_color(self) -> None:
        g = _make_game()
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g.grid[0][0].color = 8
        assert g._is_valid_placement(1, 0, 11) is True

    def test_color_zero_invalid(self) -> None:
        g = _make_game()
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        assert g._is_valid_placement(0, 0, 0) is False


class TestPlaceColor:
    def test_valid_placement_updates_score_and_combo(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g._selected_color = 0
        g._place_color(0, 0)
        assert g.grid[0][0].color == 8
        assert g.score == 10
        assert g.combo == 1

    def test_consecutive_same_color_increases_combo(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g._selected_color = 0
        g._place_color(0, 0)
        assert g.score == 10
        assert g.combo == 1
        g._selected_color = 0
        g._place_color(1, 1)
        assert g.combo == 2
        assert g.score == 30  # 10 + 10*2

    def test_different_color_resets_combo(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g._selected_color = 0
        g._place_color(0, 0)
        assert g.combo == 1
        g._selected_color = 1
        g._place_color(1, 0)
        assert g.combo == 1

    def test_invalid_placement_resets_combo(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g._selected_color = 0
        g._place_color(0, 0)
        assert g.combo == 1
        g._selected_color = 0
        g._place_color(1, 0)
        assert g.combo == 0

    def test_invalid_placement_increases_heat(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g.grid[0][0].color = 8
        g._selected_color = 0
        g._place_color(1, 0)
        assert g.heat == HEAT_MISMATCH

    def test_invalid_placement_cell_stays_empty(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g.grid[0][0].color = 8
        g._selected_color = 0
        g._place_color(1, 0)
        assert g.grid[0][1].color == 0

    def test_locked_cell_ignored(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g.grid[0][0].color = 8
        g.grid[0][0].locked = True
        g._selected_color = 0
        g._place_color(0, 0)
        assert g.grid[0][0].color == 8
        assert g.score == 0

    def test_max_combo_tracked(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g._selected_color = 0
        g._place_color(0, 0)
        g._place_color(1, 1)
        g._place_color(2, 2)
        assert g.max_combo == 3


class TestComboAndSuper:
    def test_combo_4_triggers_super(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g._selected_color = 0
        g._place_color(0, 0)  # combo 1
        g._place_color(1, 1)  # combo 2
        g._place_color(2, 2)  # combo 3
        g._place_color(3, 3)  # combo 4 -> SUPER!
        assert g.super_timer == SUPER_DURATION
        assert g.combo == 4

    def test_super_mode_auto_validates(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g._selected_color = 0
        g._place_color(0, 0)
        g._place_color(1, 1)
        g._place_color(2, 2)
        g._place_color(3, 3)
        assert g.super_timer > 0
        g.grid[0][1].color = 8  # pre-fill to create conflict
        g._selected_color = 0
        g._place_color(0, 1)  # should succeed even though conflict
        assert g.grid[0][1].color == 8
        assert g.combo == 5

    def test_super_mode_3x_score(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g._selected_color = 0
        g._place_color(0, 0)
        g._place_color(1, 1)
        g._place_color(2, 2)
        g._place_color(3, 3)
        assert g.super_timer == SUPER_DURATION
        score_before = g.score
        g._place_color(0, 2)
        assert g.score == score_before + 10 * 4 * 3  # combo=4 at time of placement

    def test_super_timer_decrements(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g._selected_color = 0
        g._place_color(0, 0)
        g._place_color(1, 1)
        g._place_color(2, 2)
        g._place_color(3, 3)
        assert g.super_timer == SUPER_DURATION
        g.super_timer -= 1
        assert g.super_timer == SUPER_DURATION - 1


class TestGridComplete:
    def test_empty_grid_not_complete(self) -> None:
        g = _make_game()
        g.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        assert g._is_grid_complete() is False

    def test_full_grid_complete(self) -> None:
        g = _make_game()
        g.grid = [[Cell(color=8) for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        assert g._is_grid_complete() is True

    def test_partial_grid_not_complete(self) -> None:
        g = _make_game()
        g.grid = [[Cell(color=8) for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        g.grid[0][0].color = 0
        assert g._is_grid_complete() is False


class TestHeat:
    def test_heat_decay(self) -> None:
        g = _make_game()
        g.heat = 10.0
        g.super_timer = 0
        g._update_heat()
        expected = 10.0 - HEAT_DECAY + HEAT_TIME_PRESSURE
        assert g.heat == expected

    def test_heat_capped_at_max(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX - 1.0
        g.super_timer = 0
        g._update_heat()
        assert g.heat <= HEAT_MAX

    def test_heat_floor_at_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g.super_timer = 0
        for _ in range(10):
            g._update_heat()
        assert g.heat >= 0.0

    def test_super_mode_freezes_heat(self) -> None:
        g = _make_game()
        g.heat = 30.0
        g.super_timer = 10
        g._update_heat()
        assert g.heat == 30.0


class TestResetGame:
    def test_reset_clears_state(self) -> None:
        g = _make_game()
        g.score = 500
        g.combo = 3
        g.heat = 50.0
        g.round_num = 5
        g.timer = 100
        g.super_timer = 50
        g._reset_game()
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.round_num == 1
        assert g.timer == GAME_DURATION
        assert g.super_timer == 0
        assert g.phase == Phase.TITLE

    def test_best_score_preserved(self) -> None:
        g = _make_game()
        g.best_score = 999
        g._reset_game()
        assert g.best_score == 999


class TestParticlesAndTexts:
    def test_particles_spawned(self) -> None:
        g = _make_game()
        initial_count = len(g.particles)
        g._spawn_particles(100.0, 80.0, 8, 5)
        assert len(g.particles) == initial_count + 5

    def test_floating_texts_spawned(self) -> None:
        g = _make_game()
        initial_count = len(g.floating_texts)
        g._spawn_floating_text(100.0, 80.0, "+50", 7)
        assert len(g.floating_texts) == initial_count + 1
        assert g.floating_texts[-1].text == "+50"

    def test_particles_decay_and_removed(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 80.0, 8, 1)
        assert len(g.particles) == 1
        g.particles[0].life = 0
        g._update_particles()
        assert len(g.particles) == 0

    def test_floating_texts_decay_and_removed(self) -> None:
        g = _make_game()
        g._spawn_floating_text(100.0, 80.0, "+50", 7)
        assert len(g.floating_texts) == 1
        g.floating_texts[0].life = 0
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


class TestTimer:
    def test_timer_decrements(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.timer = 100
        g._step_game_logic()
        assert g.timer == 99

    def test_timer_zero_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.timer = 1
        g.heat = 0.0
        g._step_game_logic()
        assert g.phase == Phase.GAME_OVER


class TestPhaseTransitions:
    def test_title_to_playing(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE

    def test_heat_max_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = HEAT_MAX
        g._step_game_logic()
        assert g.phase == Phase.GAME_OVER

    def test_game_over_restart(self) -> None:
        g = _make_game()
        g.phase = Phase.GAME_OVER
        g.score = 500
        g.best_score = 0
        g._reset_game()
        g.phase = Phase.PLAYING
        assert g.score == 0
        assert g.phase == Phase.PLAYING
        assert g.round_num == 1


class TestConstants:
    def test_colors_length(self) -> None:
        assert len(COLORS) == 4
        assert len(COLOR_NAMES) == 4

    def test_colors_valid(self) -> None:
        for c in COLORS:
            assert 0 <= c <= 15

    def test_grid_dimensions(self) -> None:
        assert GRID_COLS == 4
        assert GRID_ROWS == 4

    def test_super_duration_positive(self) -> None:
        assert SUPER_DURATION > 0

    def test_heat_max_positive(self) -> None:
        assert HEAT_MAX > 0
        assert HEAT_MISMATCH > 0

    def test_round_clear_frames(self) -> None:
        assert ROUND_CLEAR_FRAMES > 0
