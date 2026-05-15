"""test_imports.py — Headless logic tests for PIPE SURGE.

Tests core game logic without initializing Pyxel.
Uses __new__ pattern to create game instance for testing.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/029_pipe_surge")

from main import (
    CELL_SIZE,
    COMBO_THRESHOLD,
    GRID_COLS,
    GRID_ROWS,
    HAND_SIZE,
    NUM_COLORS,
    PATH_SCORE_BASE,
    PIPE_COLORS,
    PIPE_SHAPES,
    PIPE_SHAPE_KEYS,
    PRESSURE_MAX,
    SURGE_BONUS,
    TURN_TIME,
    CellPos,
    Dir,
    DIR_OPPOSITE,
    DIR_VEC,
    Particle,
    FloatingText,
    Phase,
    PipeTile,
    PipeSurge,
)


# ── Data structure tests ──

def test_pipe_tile_creation() -> None:
    """PipeTile creates correctly with color and openings."""
    tile = PipeTile(color=0, opens=(True, False, True, False))
    assert tile.color == 0
    assert tile.opens == (True, False, True, False)
    assert tile.has_open(Dir.UP) is True
    assert tile.has_open(Dir.RIGHT) is False
    assert tile.has_open(Dir.DOWN) is True
    assert tile.has_open(Dir.LEFT) is False


def test_pipe_tile_frozen() -> None:
    """PipeTile is frozen/immutable."""
    tile1 = PipeTile(color=0, opens=PIPE_SHAPES["H"])
    tile2 = PipeTile(color=0, opens=PIPE_SHAPES["H"])
    assert tile1 == tile2
    assert hash(tile1) == hash(tile2)


def test_pipe_shapes_count() -> None:
    """All predefined shapes are valid."""
    assert len(PIPE_SHAPES) >= 4
    for shape_key, opens in PIPE_SHAPES.items():
        assert len(opens) == 4
        assert sum(opens) == 2  # Each pipe connects exactly 2 directions


def test_cell_pos() -> None:
    """CellPos NamedTuple works."""
    cp = CellPos(3, 5)
    assert cp.row == 3
    assert cp.col == 5
    assert cp == CellPos(3, 5)
    assert cp != CellPos(5, 3)


def test_dir_enum() -> None:
    """Dir enum and direction vectors work."""
    assert Dir.UP.value == 0
    assert Dir.RIGHT.value == 1
    assert Dir.DOWN.value == 2
    assert Dir.LEFT.value == 3
    assert DIR_VEC[Dir.UP] == (-1, 0)
    assert DIR_VEC[Dir.RIGHT] == (0, 1)
    assert DIR_VEC[Dir.DOWN] == (1, 0)
    assert DIR_VEC[Dir.LEFT] == (0, -1)
    assert DIR_OPPOSITE[Dir.UP] == Dir.DOWN
    assert DIR_OPPOSITE[Dir.RIGHT] == Dir.LEFT


def test_constants() -> None:
    """Config constants are reasonable."""
    assert GRID_ROWS == 8
    assert GRID_COLS == 8
    assert CELL_SIZE == 28
    assert NUM_COLORS == 4
    assert HAND_SIZE == 3
    assert COMBO_THRESHOLD == 4
    assert SURGE_BONUS == 200
    assert PATH_SCORE_BASE == 100
    assert PRESSURE_MAX == 10
    assert TURN_TIME > 0
    assert len(PIPE_COLORS) == 4
    assert len(PIPE_SHAPE_KEYS) >= 4


# ── Game instance via __new__ ──

def _make_game() -> PipeSurge:
    """Create a PipeSurge instance without initializing Pyxel."""
    g = object.__new__(PipeSurge)
    g._reset()
    return g


# ── Grid placement tests ──

def test_grid_initially_empty() -> None:
    """New grid has no pipes placed."""
    g = _make_game()
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            assert g.grid[row][col] is None


def test_place_tile() -> None:
    """Placing a tile from hand works."""
    g = _make_game()
    initial_hand_len = len(g.hand)
    g.selected_idx = 0
    tile = g.hand[0]
    g._place_tile(0, 0)
    assert g.grid[0][0] is not None
    assert g.grid[0][0] == tile
    assert len(g.hand) == initial_hand_len - 1


def test_place_tile_on_occupied() -> None:
    """Cannot place on an occupied cell."""
    g = _make_game()
    g.selected_idx = 0
    g._place_tile(0, 0)
    first_tile = g.grid[0][0]
    g._place_tile(0, 0)  # Should be no-op
    assert g.grid[0][0] == first_tile


def test_rotate_tile() -> None:
    """Rotate cycles a tile's openings 90 degrees clockwise."""
    g = _make_game()
    # Set a known tile: horizontal
    g.hand[0] = PipeTile(color=0, opens=PIPE_SHAPES["H"])  # RIGHT, LEFT
    assert g.hand[0].opens == (False, True, False, True)

    g.selected_idx = 0
    g._rotate_selected()
    # After rotation: UP←LEFT, RIGHT←UP, DOWN←RIGHT, LEFT←DOWN
    # So LEFT→UP, UP→RIGHT, RIGHT→DOWN, DOWN→LEFT
    # Original: (UP=F, RIGHT=T, DOWN=F, LEFT=T)
    # New:      (UP=T, RIGHT=F, DOWN=T, LEFT=F) = vertical
    assert g.hand[0].opens == (True, False, True, False)


def test_draw_hand_size() -> None:
    """Drawing hand creates HAND_SIZE tiles."""
    g = _make_game()
    assert len(g.hand) == HAND_SIZE
    for tile in g.hand:
        assert isinstance(tile, PipeTile)
        assert 0 <= tile.color < NUM_COLORS


# ── BFS Pathfinding tests ──

def test_find_path_straight_horizontal() -> None:
    """BFS finds a straight horizontal path from left source to right drain."""
    g = _make_game()
    # Source on left edge, drain on right edge (row 3)
    g.source_pos = (3, -1)  # left of col 0
    g.source_dir = Dir.RIGHT
    g.drain_pos = (3, GRID_COLS)  # right of col 7
    g.drain_dir = Dir.LEFT

    # Place horizontal pipes in row 3, cols 0-7
    for col in range(GRID_COLS):
        g.grid[3][col] = PipeTile(color=0, opens=PIPE_SHAPES["H"])

    path = g._find_path()
    assert path is not None
    assert len(path) == GRID_COLS  # 8 cells
    assert path[0] == CellPos(3, 0)
    assert path[-1] == CellPos(3, 7)


def test_find_path_straight_vertical() -> None:
    """BFS finds a straight vertical path from top source to bottom drain."""
    g = _make_game()
    g.source_pos = (-1, 4)  # above col 4
    g.source_dir = Dir.DOWN
    g.drain_pos = (GRID_ROWS, 4)  # below col 4
    g.drain_dir = Dir.UP

    for row in range(GRID_ROWS):
        g.grid[row][4] = PipeTile(color=1, opens=PIPE_SHAPES["V"])

    path = g._find_path()
    assert path is not None
    assert len(path) == GRID_ROWS
    assert path[0] == CellPos(0, 4)
    assert path[-1] == CellPos(7, 4)


def test_find_path_with_bends() -> None:
    """BFS finds a path that includes bend tiles."""
    g = _make_game()
    # Source at top edge col 0, drain at right edge row 0
    g.source_pos = (-1, 0)
    g.source_dir = Dir.DOWN
    g.drain_pos = (0, GRID_COLS)
    g.drain_dir = Dir.LEFT

    # Path: down from (0,0) to (7,0), then right to (7,7), then up to (0,7)
    # Vertical at (0..6, 0) — row 7 uses bend
    for row in range(7):
        g.grid[row][0] = PipeTile(color=0, opens=PIPE_SHAPES["V"])

    # Bend at (7, 0): opens RIGHT and UP
    g.grid[7][0] = PipeTile(color=0, opens=PIPE_SHAPES["UR"])  # UP+RIGHT but facing corner: actually need DOWN from above and RIGHT to right

    # Wait, if flow comes from above (row 6, col 0 with V opening DOWN), then at row 7 we need a pipe that opens UP (to receive) and RIGHT (to continue).
    # PIPE_SHAPES["UR"] opens UP and RIGHT. That works!

    # Horizontal at (7, 1..6)
    for col in range(1, 7):
        g.grid[7][col] = PipeTile(color=0, opens=PIPE_SHAPES["H"])
    # Bend at (7, 7): opens UP and LEFT → this is "LU" (LEFT, UP)
    g.grid[7][7] = PipeTile(color=0, opens=PIPE_SHAPES["LU"])

    # Vertical at (1..6, 7) going UP
    for row in range(1, 7):
        g.grid[row][7] = PipeTile(color=0, opens=PIPE_SHAPES["V"])
    # Bend at (0, 7): opens DOWN (to receive from row 1) and LEFT (to drain)
    g.grid[0][7] = PipeTile(color=0, opens=PIPE_SHAPES["DL"])  # DOWN and LEFT

    path = g._find_path()
    assert path is not None
    # Path: 7 vertical + 7 horizontal + 7 vertical = 21? No...
    # down: (0,0)..(7,0) = 8 cells
    # right: (7,1)..(7,7) = 7 cells
    # up: (6,7)..(0,7) = 7 cells
    # Total: 8 + 7 + 7 = 22
    assert len(path) == 22


def test_find_path_no_path() -> None:
    """BFS returns None when no path exists."""
    g = _make_game()
    g.source_pos = (-1, 0)
    g.source_dir = Dir.DOWN
    g.drain_pos = (GRID_ROWS, 7)
    g.drain_dir = Dir.UP

    # Place just one pipe — not enough to reach drain
    g.grid[0][0] = PipeTile(color=0, opens=PIPE_SHAPES["H"])  # horizontal, doesn't go down

    path = g._find_path()
    assert path is None


def test_find_path_color_independent() -> None:
    """BFS connects pipes regardless of color (color only affects combo)."""
    g = _make_game()
    g.source_pos = (-1, 3)
    g.source_dir = Dir.DOWN
    g.drain_pos = (GRID_ROWS, 3)
    g.drain_dir = Dir.UP

    # Mix of colors
    for row in range(GRID_ROWS):
        g.grid[row][3] = PipeTile(color=row % NUM_COLORS, opens=PIPE_SHAPES["V"])

    path = g._find_path()
    assert path is not None
    assert len(path) == GRID_ROWS


def test_find_path_blocked_by_wrong_orientation() -> None:
    """BFS fails when a pipe has the wrong orientation."""
    g = _make_game()
    g.source_pos = (-1, 3)
    g.source_dir = Dir.DOWN
    g.drain_pos = (GRID_ROWS, 3)
    g.drain_dir = Dir.UP

    # Row 0: vertical (works), row 1: horizontal (breaks the chain)
    g.grid[0][3] = PipeTile(color=0, opens=PIPE_SHAPES["V"])  # UP, DOWN
    g.grid[1][3] = PipeTile(color=0, opens=PIPE_SHAPES["H"])  # LEFT, RIGHT (no UP)
    for row in range(2, GRID_ROWS):
        g.grid[row][3] = PipeTile(color=0, opens=PIPE_SHAPES["V"])

    path = g._find_path()
    assert path is None  # Can't get past row 1


# ── Combo calculation tests ──

def test_calc_combo_single_pipe() -> None:
    """A path with 1 pipe of a single color has combo 1."""
    g = _make_game()
    g.grid[3][3] = PipeTile(color=0, opens=PIPE_SHAPES["V"])
    path = [CellPos(3, 3)]
    combo = g._calc_combo(path)
    assert combo == 1


def test_calc_combo_all_same_color_connected() -> None:
    """A path of 5 same-color pipes in a line has combo 5."""
    g = _make_game()
    path: list[CellPos] = []
    for col in range(5):
        g.grid[3][col] = PipeTile(color=0, opens=PIPE_SHAPES["H"])
        path.append(CellPos(3, col))
    combo = g._calc_combo(path)
    assert combo == 5


def test_calc_combo_mixed_colors() -> None:
    """Mixed-color path: combo is the largest same-color chain."""
    g = _make_game()
    path: list[CellPos] = []
    colors = [0, 0, 0, 1, 1, 2, 2, 2]  # chain of 3 red, 2 cyan, 3 green
    for i, col in enumerate(colors):
        g.grid[3][i] = PipeTile(color=col, opens=PIPE_SHAPES["H"])
        path.append(CellPos(3, i))
    combo = g._calc_combo(path)
    assert combo == 3  # Longest = 3 (green)


def test_calc_combo_interleaved_colors() -> None:
    """Interleaved colors: no chain longer than 1."""
    g = _make_game()
    path: list[CellPos] = []
    for i in range(6):
        g.grid[3][i] = PipeTile(color=i % NUM_COLORS, opens=PIPE_SHAPES["H"])
        path.append(CellPos(3, i))
    combo = g._calc_combo(path)
    assert combo == 1


def test_calc_combo_non_adjacent_same_color() -> None:
    """Same colors separated by other colors: each is separate chain."""
    g = _make_game()
    path: list[CellPos] = []
    colors = [0, 1, 0, 2, 0]  # red at positions 0, 2, 4 — not adjacent
    for i, col in enumerate(colors):
        g.grid[3][i] = PipeTile(color=col, opens=PIPE_SHAPES["H"])
        path.append(CellPos(3, i))
    combo = g._calc_combo(path)
    assert combo == 1  # No adjacent same-color pipes


# ── Pressure system tests ──

def test_pressure_starts_zero() -> None:
    """New game starts with 0 pressure."""
    g = _make_game()
    assert g.pressure == 0


def test_pressure_increases_on_failed_flow() -> None:
    """Triggering flow with no path increases pressure."""
    g = _make_game()
    g.pressure = 0
    g._trigger_flow()  # No path → should gain pressure
    assert g.pressure == 1


def test_pressure_game_over() -> None:
    """Pressure at max triggers game over."""
    g = _make_game()
    g.pressure = PRESSURE_MAX - 1
    g._trigger_flow()  # pressure becomes PRESSURE_MAX → game over
    assert g.phase == Phase.GAME_OVER


def test_finish_round_reduces_pressure() -> None:
    """Completing a round reduces pressure."""
    g = _make_game()
    g.pressure = 5
    g._finish_round()
    assert g.pressure == 4


def test_finish_round_min_pressure() -> None:
    """Pressure doesn't go below 0."""
    g = _make_game()
    g.pressure = 0
    g._finish_round()
    assert g.pressure == 0


# ── Particle system tests ──

def test_particle_life_decreases() -> None:
    """Particle life decreases each frame in update loop."""
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=10, color=0)]
    g.particles[0].life = 10
    # Simulate what the update loop does
    g.particles = [p for p in g.particles if p.life > 0]
    for p in g.particles:
        p.life -= 1
    assert g.particles[0].life == 9


def test_particle_removal() -> None:
    """Particles with life <= 0 are removed."""
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=0, color=0),
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=2, color=1),
    ]
    g.particles = [p for p in g.particles if p.life > 0]
    assert len(g.particles) == 1
    assert g.particles[0].color == 1


# ── Phase transitions ──

def test_phase_starts_placing() -> None:
    """New game starts in PLACING phase."""
    g = _make_game()
    assert g.phase == Phase.PLACING


def test_trigger_flow_transitions_to_flowing() -> None:
    """With a valid path, trigger_flow transitions to FLOWING."""
    g = _make_game()
    # Set up a simple vertical path
    g.source_pos = (-1, 3)
    g.source_dir = Dir.DOWN
    g.drain_pos = (GRID_ROWS, 3)
    g.drain_dir = Dir.UP
    for row in range(GRID_ROWS):
        g.grid[row][3] = PipeTile(color=0, opens=PIPE_SHAPES["V"])
    g._trigger_flow()
    assert g.phase == Phase.FLOWING


# ── Score calculation tests ──

def test_score_starts_zero() -> None:
    """New game starts with 0 score."""
    g = _make_game()
    assert g.score == 0


def test_score_increases_on_complete_path() -> None:
    """Completing the flow animation increases score."""
    g = _make_game()
    g.source_pos = (-1, 0)
    g.source_dir = Dir.DOWN
    g.drain_pos = (GRID_ROWS, 0)
    g.drain_dir = Dir.UP
    for row in range(GRID_ROWS):
        g.grid[row][0] = PipeTile(color=0, opens=PIPE_SHAPES["V"])
    g.phase = Phase.PLACING
    g._trigger_flow()
    assert g.phase == Phase.FLOWING
    # Complete the flow animation
    while g.phase == Phase.FLOWING:
        g._update_flowing()
    assert g.score > 0


# ── Source/Drain placement tests ──

def test_source_drain_on_different_edges() -> None:
    """Source and drain are on different edges."""
    g = _make_game()
    # Check they're on different edges
    sr, sc = g.source_pos
    dr, dc = g.drain_pos

    def _edge_of(r: int, c: int) -> str:
        if r == -1:
            return "top"
        if r == GRID_ROWS:
            return "bottom"
        if c == -1:
            return "left"
        if c == GRID_COLS:
            return "right"
        return "none"

    src_edge = _edge_of(sr, sc)
    drn_edge = _edge_of(dr, dc)
    assert src_edge != "none"
    assert drn_edge != "none"
    assert src_edge != drn_edge


# ── Cell helpers tests ──

def test_cell_at_pixel_valid() -> None:
    """_cell_at_pixel returns correct cell for pixel position."""
    g = _make_game()
    result = g._cell_at_pixel(16 + 14, 8 + 14)  # center of cell (0,0)
    assert result == (0, 0)


def test_cell_at_pixel_invalid() -> None:
    """_cell_at_pixel returns None outside grid."""
    g = _make_game()
    assert g._cell_at_pixel(0, 0) is None  # above/left of grid
    assert g._cell_at_pixel(0, 300) is None  # below grid


def test_cell_center() -> None:
    """_cell_center returns correct pixel center."""
    g = _make_game()
    cx, cy = g._cell_center(0, 0)
    assert cx == 16 + 14  # GRID_X + HALF_CELL
    assert cy == 8 + 14    # GRID_Y + HALF_CELL


def test_grid_entry_cell() -> None:
    """_grid_entry_cell correctly computes first grid cell from edge."""
    g = _make_game()
    # Source at top edge col 3, flow enters DOWN
    entry = g._grid_entry_cell((-1, 3), Dir.DOWN)
    assert entry == (0, 3)

    # Source at bottom edge col 5, flow enters UP
    entry = g._grid_entry_cell((GRID_ROWS, 5), Dir.UP)
    assert entry == (7, 5)

    # Source at left edge row 2, flow enters RIGHT
    entry = g._grid_entry_cell((2, -1), Dir.RIGHT)
    assert entry == (2, 0)


def test_is_valid_cell() -> None:
    """_is_valid_cell boundaries are correct."""
    g = _make_game()
    assert g._is_valid_cell(0, 0) is True
    assert g._is_valid_cell(7, 7) is True
    assert g._is_valid_cell(-1, 0) is False
    assert g._is_valid_cell(0, -1) is False
    assert g._is_valid_cell(8, 0) is False
    assert g._is_valid_cell(0, 8) is False


# ── Run all tests ──
if __name__ == "__main__":
    import traceback

    tests = [
        # Data structures
        test_pipe_tile_creation,
        test_pipe_tile_frozen,
        test_pipe_shapes_count,
        test_cell_pos,
        test_dir_enum,
        test_constants,
        # Grid placement
        test_grid_initially_empty,
        test_place_tile,
        test_place_tile_on_occupied,
        test_rotate_tile,
        test_draw_hand_size,
        # BFS Pathfinding
        test_find_path_straight_horizontal,
        test_find_path_straight_vertical,
        test_find_path_with_bends,
        test_find_path_no_path,
        test_find_path_color_independent,
        test_find_path_blocked_by_wrong_orientation,
        # Combo calculation
        test_calc_combo_single_pipe,
        test_calc_combo_all_same_color_connected,
        test_calc_combo_mixed_colors,
        test_calc_combo_interleaved_colors,
        test_calc_combo_non_adjacent_same_color,
        # Pressure system
        test_pressure_starts_zero,
        test_pressure_increases_on_failed_flow,
        test_pressure_game_over,
        test_finish_round_reduces_pressure,
        test_finish_round_min_pressure,
        # Particles
        test_particle_life_decreases,
        test_particle_removal,
        # Phase transitions
        test_phase_starts_placing,
        test_trigger_flow_transitions_to_flowing,
        # Score
        test_score_starts_zero,
        test_score_increases_on_complete_path,
        # Source/Drain
        test_source_drain_on_different_edges,
        # Cell helpers
        test_cell_at_pixel_valid,
        test_cell_at_pixel_invalid,
        test_cell_center,
        test_grid_entry_cell,
        test_is_valid_cell,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  PASS  {test_fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {test_fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {test_fn.__name__}: {e}")
            traceback.print_exc()

    print(f"\nResults: {passed} passed, {failed} failed out of {len(tests)}")
    if failed > 0:
        sys.exit(1)
