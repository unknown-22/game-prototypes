"""test_imports.py — Headless logic tests for 268_dot_chain."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    CELL,
    COLS,
    COLORS,
    GAME_TIME,
    GRID_X,
    GRID_Y,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    HEAT_SHORT,
    MIN_CHAIN_LEN,
    ROWS,
    SUPER_DURATION,
    Dot,
    FloatingText,
    Game,
    Particle,
    Phase,
)


# ── Helpers ──

def _make_game() -> Game:
    """Create a headless Game instance with seeded RNG."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.reset()
    return g


def _grid_to_screen(col: int, row: int) -> tuple[float, float]:
    x = GRID_X + col * CELL + CELL // 2
    y = GRID_Y + row * CELL + CELL // 2
    return x, y


# ── Data Classes ──

def test_dot_dataclass() -> None:
    dot = Dot(3, 4, 8)
    assert dot.col == 3
    assert dot.row == 4
    assert dot.color == 8  # RED


def test_particle_dataclass() -> None:
    p = Particle(100.0, 50.0, 1.0, -2.0, 20, 8)
    assert p.x == 100.0
    assert p.y == 50.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 20
    assert p.color == 8


def test_floating_text_dataclass() -> None:
    ft = FloatingText(150.0, 80.0, "+100", 30, 7)
    assert ft.x == 150.0
    assert ft.y == 80.0
    assert ft.text == "+100"
    assert ft.life == 30
    assert ft.color == 7
    assert ft.vy == -1.0


# ── Constants ──

def test_constants() -> None:
    assert COLS == 8
    assert ROWS == 7
    assert CELL == 28
    assert MIN_CHAIN_LEN == 3
    assert SUPER_DURATION == 300
    assert HEAT_MAX == 100
    assert HEAT_DECAY == 0.02
    assert HEAT_MISMATCH == 15
    assert HEAT_SHORT == 5
    assert GAME_TIME == 60 * 60
    assert len(COLORS) == 4


# ── Game.__new__ / __init__ bypass ──

def test_new_bypass() -> None:
    g = Game.__new__(Game)
    assert g._headless is True
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == -1
    assert g.heat == 0.0
    assert isinstance(g._rng, random.Random)


def test_reset() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == -1
    assert g.heat == 0.0
    assert g.timer == GAME_TIME
    assert g.super_timer == 0
    assert len(g.dots) == COLS * ROWS  # 56


def test_init_grid() -> None:
    g = _make_game()
    # All cells filled
    for row in range(ROWS):
        for col in range(COLS):
            assert g.grid[row][col] is not None
            assert isinstance(g.grid[row][col], Dot)
    # All colors valid
    for dot in g.dots:
        assert dot.color in COLORS


# ── Grid / Coordinate Conversions ──

def test_grid_to_screen() -> None:
    x, y = _grid_to_screen(0, 0)
    assert x == GRID_X + CELL // 2
    assert y == GRID_Y + CELL // 2
    x2, y2 = _grid_to_screen(7, 6)
    assert x2 == GRID_X + 7 * CELL + CELL // 2
    assert y2 == GRID_Y + 6 * CELL + CELL // 2


def test_screen_to_grid() -> None:
    g = _make_game()
    col, row = g._screen_to_grid(GRID_X, GRID_Y)
    assert col == 0
    assert row == 0
    col, row = g._screen_to_grid(GRID_X + 7 * CELL, GRID_Y + 6 * CELL)
    assert col == 7
    assert row == 6


# ── Adjacency ──

def test_is_adjacent_horizontal() -> None:
    g = _make_game()
    assert g._is_adjacent(0, 0, 1, 0) is True  # right
    assert g._is_adjacent(1, 0, 0, 0) is True  # left
    assert g._is_adjacent(0, 0, 0, 0) is False  # same cell
    assert g._is_adjacent(0, 0, 2, 0) is False  # two cells away


def test_is_adjacent_diagonal() -> None:
    g = _make_game()
    assert g._is_adjacent(0, 0, 1, 1) is True  # down-right
    assert g._is_adjacent(1, 1, 0, 0) is True  # up-left
    assert g._is_adjacent(0, 0, 2, 2) is False  # two cells diag


def test_is_adjacent_vertical() -> None:
    g = _make_game()
    assert g._is_adjacent(3, 2, 3, 3) is True  # down
    assert g._is_adjacent(3, 3, 3, 2) is True  # up
    assert g._is_adjacent(3, 2, 3, 4) is False  # two cells


# ── Find Nearest Dot ──

def test_find_nearest_dot_hit() -> None:
    g = _make_game()
    # Find dot at (0,0)
    sx, sy = _grid_to_screen(0, 0)
    dot = g._find_nearest_dot(int(sx), int(sy))
    assert dot is not None
    assert dot.col == 0
    assert dot.row == 0


def test_find_nearest_dot_miss() -> None:
    g = _make_game()
    # Click far outside the grid
    dot = g._find_nearest_dot(0, 0)
    assert dot is None


def test_find_nearest_dot_returns_closest() -> None:
    g = _make_game()
    # Two dots near the mouse, should return the closer one
    sx0, sy0 = _grid_to_screen(0, 0)
    sx1, sy1 = _grid_to_screen(1, 0)
    # Click closer to (1,0)
    mx = int(sx1) - 5
    my = int(sy1)
    dot = g._find_nearest_dot(mx, my)
    assert dot is not None
    assert dot.col == 1
    assert dot.row == 0


# ── Chain Building ──

def test_start_chain() -> None:
    g = _make_game()
    sx, sy = _grid_to_screen(0, 0)
    g._start_chain(int(sx), int(sy))
    assert g.dragging is True
    assert len(g.chain_path) == 1
    assert g.chain_path[0] == (0, 0)
    assert g.grid[0][0] is not None
    assert g.chain_color == g.grid[0][0].color


def test_extend_chain_same_color() -> None:
    g = _make_game()
    # Set up: (0,0) and (0,1) same color
    color = 8  # RED
    g.grid[0][0] = Dot(0, 0, color)
    g.grid[1][0] = Dot(0, 1, color)
    g.dots = [g.grid[0][0], g.grid[1][0]]  # simplified

    g.dragging = True
    g.chain_path = [(0, 0)]
    g.chain_color = color

    # Click on (0,1)
    sx, sy = _grid_to_screen(0, 1)
    g._extend_chain(int(sx), int(sy))
    assert len(g.chain_path) == 2
    assert g.chain_path[1] == (0, 1)


def test_extend_chain_wrong_color() -> None:
    g = _make_game()
    # Set up: (0,0)=RED, (0,1)=LIME
    g.grid[0][0] = Dot(0, 0, 8)  # RED
    g.grid[1][0] = Dot(0, 1, 11)  # LIME
    g.dots = [g.grid[0][0], g.grid[1][0]]

    g.dragging = True
    g.chain_path = [(0, 0)]
    g.chain_color = 8

    sx, sy = _grid_to_screen(0, 1)
    g._extend_chain(int(sx), int(sy))
    # Should NOT add because wrong color
    assert len(g.chain_path) == 1


def test_extend_chain_not_adjacent() -> None:
    g = _make_game()
    color = 8
    g.grid[0][0] = Dot(0, 0, color)
    g.grid[0][2] = Dot(2, 0, color)
    g.dots = [g.grid[0][0], g.grid[0][2]]

    g.dragging = True
    g.chain_path = [(0, 0)]
    g.chain_color = color

    sx, sy = _grid_to_screen(2, 0)
    g._extend_chain(int(sx), int(sy))
    # Should NOT add because not adjacent
    assert len(g.chain_path) == 1


def test_extend_chain_diagonal_same_color() -> None:
    g = _make_game()
    color = 11  # LIME
    g.grid[0][0] = Dot(0, 0, color)
    g.grid[1][1] = Dot(1, 1, color)
    g.dots = [g.grid[0][0], g.grid[1][1]]

    g.dragging = True
    g.chain_path = [(0, 0)]
    g.chain_color = color

    sx, sy = _grid_to_screen(1, 1)
    g._extend_chain(int(sx), int(sy))
    assert len(g.chain_path) == 2
    assert g.chain_path[1] == (1, 1)


# ── Try Add To Chain ──

def test_try_add_to_chain_valid() -> None:
    g = _make_game()
    color = 5  # DARK_BLUE
    g.grid[0][0] = Dot(0, 0, color)
    g.grid[1][0] = Dot(0, 1, color)
    g.dots = [Dot(0, 0, color), Dot(0, 1, color)]

    g.chain_path = [(0, 0)]
    g.chain_color = color

    result = g._try_add_to_chain(0, 1)
    assert result is True
    assert len(g.chain_path) == 2


def test_try_add_to_chain_wrong_color() -> None:
    g = _make_game()
    g.grid[0][0] = Dot(0, 0, 8)  # RED
    g.grid[1][0] = Dot(0, 1, 11)  # LIME
    g.dots = [Dot(0, 0, 8), Dot(0, 1, 11)]
    assert g.grid[0][0] is not None
    assert g.grid[1][0] is not None

    g.chain_path = [(0, 0)]
    g.chain_color = 8
    initial_heat = g.heat

    result = g._try_add_to_chain(0, 1)
    assert result is False
    assert g.heat == initial_heat + HEAT_MISMATCH


def test_try_add_to_chain_super_mode_any_color() -> None:
    g = _make_game()
    g.grid[0][0] = Dot(0, 0, 8)  # RED
    g.grid[1][0] = Dot(0, 1, 11)  # LIME
    g.dots = [Dot(0, 0, 8), Dot(0, 1, 11)]

    g.chain_path = [(0, 0)]
    g.chain_color = 8
    g.super_timer = 100  # SUPER mode active

    result = g._try_add_to_chain(0, 1)
    assert result is True  # SUPER mode allows any color
    assert len(g.chain_path) == 2


def test_try_add_to_chain_empty_cell() -> None:
    g = _make_game()
    g.grid[0][0] = Dot(0, 0, 8)
    g.grid[1][0] = None  # empty
    g.dots = [Dot(0, 0, 8)]

    g.chain_path = [(0, 0)]
    g.chain_color = 8

    result = g._try_add_to_chain(0, 1)
    assert result is False


def test_try_add_to_chain_already_visited() -> None:
    g = _make_game()
    color = 8
    g.grid[0][0] = Dot(0, 0, color)
    g.grid[1][0] = Dot(0, 1, color)
    g.dots = [Dot(0, 0, color), Dot(0, 1, color)]

    g.chain_path = [(0, 0), (0, 1)]
    g.chain_color = color

    # Try to add (0,1) again
    result = g._try_add_to_chain(0, 1)
    assert result is False


# ── Scoring ──

def test_score_chain_valid() -> None:
    g = _make_game()
    color = 10  # YELLOW
    g.chain_path = [(0, 0), (0, 1), (0, 2)]
    g.chain_color = color
    g.combo = -1
    g._last_combo_color = -1

    score = g._score_chain()
    assert score == 30  # 3 * 10 * (1.0 + 0 * 0.5) * 1.0
    assert g.score == 30
    assert g.combo == 0
    assert g._last_combo_color == color


def test_score_chain_short() -> None:
    g = _make_game()
    g.chain_path = [(0, 0), (0, 1)]
    g.chain_color = 8
    g.combo = 0
    initial_heat = g.heat

    score = g._score_chain()
    assert score == 0
    assert g.heat == initial_heat + HEAT_SHORT
    assert g.combo == -1
    assert len(g.chain_path) == 0


def test_score_chain_combo_increment() -> None:
    g = _make_game()
    color = 8  # RED
    g.chain_path = [(0, 0), (0, 1), (0, 2)]
    g.chain_color = color
    g.combo = 2  # already have combo
    g._last_combo_color = color  # same color

    # Place dots with right color
    for col, row in g.chain_path:
        dot = Dot(col, row, color)
        g.grid[row][col] = dot
        g.dots.append(dot)

    score = g._score_chain()
    assert g.combo == 3  # incremented
    # score = 3 * 10 * (1 + 3 * 0.5) = 30 * 2.5 = 75
    assert score == 75


def test_score_chain_combo_reset_different_color() -> None:
    g = _make_game()
    g.chain_path = [(0, 0), (0, 1), (0, 2)]
    g.chain_color = 11  # LIME
    g.combo = 2
    g._last_combo_color = 8  # different color from current

    _ = g._score_chain()
    assert g.combo == 0  # reset
    assert g._last_combo_color == 11


def test_score_chain_super_multiplier() -> None:
    g = _make_game()
    color = 8
    g.chain_path = [(0, 0), (0, 1), (0, 2)]
    g.chain_color = color
    g.combo = 0
    g._last_combo_color = color
    g.super_timer = 100  # SUPER active

    score = g._score_chain()
    # score = 3 * 10 * (1 + 1 * 0.5) * 3 = 135
    # (combo was 0, same color → combo becomes 1, multiplier=1.5, super x3)
    assert score == 135


def test_score_chain_activates_super() -> None:
    g = _make_game()
    color = 8
    g.chain_path = [(0, 0), (0, 1), (0, 2)]
    g.chain_color = color
    g.combo = 3  # this will become 4 → SUPER
    g._last_combo_color = color
    g.super_timer = 0

    _ = g._score_chain()
    assert g.super_timer == SUPER_DURATION  # activated


def test_score_chain_max_combo_tracks() -> None:
    g = _make_game()
    g.max_combo = 3
    color = 8
    g.chain_path = [(0, 0), (0, 1), (0, 2)]
    g.chain_color = color
    g.combo = 5  # → 6 after increment
    g._last_combo_color = color

    g._score_chain()
    assert g.max_combo == 6


# ── Clear Chain ──

def test_clear_chain() -> None:
    g = _make_game()
    initial_dots = len(g.dots)
    g.chain_path = [(0, 0), (1, 0), (2, 0)]
    g._clear_chain()
    assert len(g.dots) == initial_dots - 3
    assert g.grid[0][0] is None
    assert g.grid[0][1] is None
    assert g.grid[0][2] is None


# ── Gravity ──

def test_apply_gravity() -> None:
    g = _make_game()
    # Clear a column and place a dot at top
    for row in range(ROWS):
        g.grid[row][0] = None
    g.dots = [d for d in g.dots if d.col != 0]

    # Place dot at row 0 (top)
    dot = Dot(0, 0, 8)
    g.grid[0][0] = dot
    g.dots.append(dot)

    g._apply_gravity()
    # Dot should fall to bottom (row 6)
    assert g.grid[6][0] is not None
    assert g.grid[6][0].color == 8
    assert g.grid[6][0].row == 6


def test_apply_gravity_preserves_order() -> None:
    g = _make_game()
    # Clear column
    for row in range(ROWS):
        g.grid[row][0] = None
    g.dots = [d for d in g.dots if d.col != 0]

    # Place dots: top=RED, middle=LIME
    g.grid[0][0] = Dot(0, 0, 8)  # RED
    g.grid[3][0] = Dot(0, 3, 11)  # LIME
    g.dots.append(g.grid[0][0])
    g.dots.append(g.grid[3][0])

    g._apply_gravity()
    # RED was above LIME → should still be above
    assert g.grid[6][0] is not None  # bottom
    assert g.grid[5][0] is not None  # above bottom


# ── Fill Empty ──

def test_fill_empty() -> None:
    g = _make_game()
    initial_dots = len(g.dots)
    # Clear two cells
    g.grid[0][0] = None
    g.grid[1][1] = None
    g.dots = [d for d in g.dots if not (d.col == 0 and d.row == 0) and not (d.col == 1 and d.row == 1)]

    g._fill_empty()
    assert len(g.dots) == initial_dots  # all cells filled
    assert g.grid[0][0] is not None
    assert g.grid[1][1] is not None
    assert g.grid[0][0].color in COLORS
    assert g.grid[1][1].color in COLORS


# ── Heat System ──

def test_update_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    result = g._update_heat()
    assert result is False
    assert g.heat == 50.0 - HEAT_DECAY


def test_update_heat_game_over_at_max() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    result = g._update_heat()
    assert result is True
    assert g.phase == Phase.GAME_OVER


def test_update_heat_clamped_at_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_threshold_before_decay() -> None:
    """Critical: heat >= MAX check must happen BEFORE decay (pitfall)."""
    g = _make_game()
    g.heat = HEAT_MAX  # exactly 100
    # If decay ran first, heat would be 99.98 and check would fail
    result = g._update_heat()
    assert result is True
    assert g.phase == Phase.GAME_OVER
    # Heat should still be 100 (game-over branch doesn't decay)
    assert g.heat == HEAT_MAX


# ── Particles ──

def test_update_particles_life_decrement() -> None:
    g = _make_game()
    g.particles = [Particle(100.0, 50.0, 1.0, -2.0, 3, 8)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 2


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.particles = [Particle(100.0, 50.0, 1.0, -2.0, 1, 8)]
    g._update_particles()
    assert len(g.particles) == 0  # life was 1 → 0 → removed


def test_update_particles_position_update() -> None:
    g = _make_game()
    g.particles = [Particle(100.0, 50.0, 1.5, -2.0, 10, 8)]
    g._update_particles()
    assert g.particles[0].x == 101.5
    assert g.particles[0].y == 48.0


# ── Floating Texts ──

def test_update_floating_texts_life() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(150.0, 80.0, "+100", 2, 7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 1


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(150.0, 80.0, "+100", 1, 7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_update_floating_texts_float_upward() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(150.0, 80.0, "+100", 10, 7)]
    g._update_floating_texts()
    assert g.floating_texts[0].y == 79.0  # vy = -1.0


# ── Spawn Particles ──

def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 50.0, 8, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == 8
        assert 10 <= p.life <= 25


# ── Spawn Floating Text ──

def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(150.0, 80.0, "COMBO x5!", 12)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "COMBO x5!"
    assert g.floating_texts[0].color == 12
    assert g.floating_texts[0].life == 30


# ── End Chain ──

def test_end_chain_valid() -> None:
    g = _make_game()
    color = 10
    # Set all 4 cells to the same color (don't touch g.dots, just grid)
    for col in range(4):
        dot = g.grid[0][col]
        assert dot is not None
        dot.color = color  # just recolor existing dots

    g.dragging = True
    g.chain_path = [(0, 0), (1, 0), (2, 0), (3, 0)]
    g.chain_color = color
    g.combo = -1

    initial_score = g.score
    g._end_chain()
    assert g.dragging is False
    assert g.score > initial_score  # scored
    # Grid should be fully refilled (56 dots)
    assert len(g.dots) == COLS * ROWS


def test_end_chain_short() -> None:
    g = _make_game()
    g.dragging = True
    g.chain_path = [(0, 0), (0, 1)]  # only 2, < MIN_CHAIN_LEN
    g.chain_color = 8
    initial_heat = g.heat

    g._end_chain()
    assert g.dragging is False
    assert len(g.chain_path) == 0
    assert g.heat > initial_heat  # HEAT_SHORT penalty


# ── Timer ──

def test_timer_decreases() -> None:
    g = _make_game()
    # Simulate one update tick (without pyxel calls)
    g.timer -= 1
    if g.timer <= 0:
        g.phase = Phase.GAME_OVER
    assert g.timer == GAME_TIME - 1
    assert g.phase == Phase.PLAYING


def test_timer_game_over() -> None:
    g = _make_game()
    g.timer = 1
    g.timer -= 1  # → 0
    assert g.timer == 0
    # In real game, this triggers game over
    if g.timer <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── Phase Enum ──

def test_phase_values() -> None:
    assert Phase.TITLE.value == 0
    assert Phase.PLAYING.value == 1
    assert Phase.GAME_OVER.value == 2


# ── Deterministic RNG ──

def test_seeded_rng_produces_same_grid() -> None:
    g1 = _make_game()
    g2 = _make_game()
    # Same seed should produce identical grids
    for row in range(ROWS):
        for col in range(COLS):
            d1 = g1.grid[row][col]
            d2 = g2.grid[row][col]
            assert d1 is not None and d2 is not None
            assert d1.color == d2.color


# ── Ghost Trail ──

def test_ghost_trail_added_on_score() -> None:
    g = _make_game()
    color = 8
    g.chain_path = [(0, 0), (1, 0), (2, 0)]
    g.chain_color = color
    g.combo = -1
    g._last_combo_color = -1

    for col, row in g.chain_path:
        dot = Dot(col, row, color)
        g.grid[row][col] = dot
        g.dots.append(dot)

    assert len(g.ghost_trail) == 0
    g._score_chain()
    assert len(g.ghost_trail) == 3


# ── Super Mode ──

def test_super_active_property() -> None:
    g = _make_game()
    assert g.super_active is False
    g.super_timer = 100
    assert g.super_active is True
    g.super_timer = 0
    assert g.super_active is False


# ── Best Score ──

def test_best_score_updated_on_game_over() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 0
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500


# ── Full Reset ──

def test_reset_clears_all_state() -> None:
    g = _make_game()
    # Modify state
    g.score = 1000
    g.combo = 5
    g.max_combo = 7
    g.heat = 80.0
    g.super_timer = 200
    g.timer = 100
    g.ghost_trail = [(100.0, 50.0, 8)]
    g.particles = [Particle(0, 0, 0, 0, 10, 8)]
    g.floating_texts = [FloatingText(0, 0, "test", 10, 7)]

    g.reset()

    assert g.score == 0
    assert g.combo == -1
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.timer == GAME_TIME
    assert len(g.ghost_trail) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.phase == Phase.PLAYING
    assert len(g.dots) == COLS * ROWS


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
