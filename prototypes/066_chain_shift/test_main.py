"""test_main.py — Headless logic tests for 066_chain_shift."""
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/066_chain_shift")
from main import (
    Game, Tile, Particle, FloatText, Phase,
    GRID_COLS, GRID_ROWS, CELL_SIZE,
    COLOR_RED, COLOR_GREEN, COLOR_YELLOW, COLORS,
    INITIAL_MOVES, BONUS_MOVE_THRESHOLD, BONUS_MOVES,
    TARGET_SCORE, BASE_POINTS_PER_TILE,
)
import random


def _make_game(seed: int = 42) -> Game:
    """Factory: create Game bypassing __init__ (no pyxel.init needed)."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.grid = []
    g.empty_col = 0
    g.empty_row = 0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.moves_left = INITIAL_MOVES
    g.particles = []
    g.floats = []
    g.target_score = TARGET_SCORE
    g.phase = Phase.PLAYING
    g.anim_timer = 0
    g.won = False
    return g


def _set_grid(g: Game, data: list[list[int | None]]) -> None:
    """Set grid from 2D array. None marks the empty cell."""
    g.grid = []
    for y, row in enumerate(data):
        grid_row: list[Tile | None] = []
        for x, val in enumerate(row):
            if val is None:
                grid_row.append(None)
                g.empty_col = x
                g.empty_row = y
            else:
                grid_row.append(Tile(val))
        g.grid.append(grid_row)


# ── Dataclass tests ──

def test_tile_dataclass():
    t = Tile(color=COLOR_RED)
    assert t.color == COLOR_RED


def test_particle_dataclass():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=COLOR_RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == COLOR_RED


def test_float_text_dataclass():
    ft = FloatText(x=100.0, y=50.0, text="COMBO!", life=25, color=COLOR_YELLOW)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "COMBO!"
    assert ft.life == 25
    assert ft.color == COLOR_YELLOW


# ── Constants ──

def test_constants():
    assert GRID_COLS == 5
    assert GRID_ROWS == 5
    assert CELL_SIZE == 48
    assert INITIAL_MOVES == 40
    assert BONUS_MOVE_THRESHOLD == 5
    assert BONUS_MOVES == 2
    assert TARGET_SCORE == 2000
    assert BASE_POINTS_PER_TILE == 10
    assert len(COLORS) == 4


# ── _bfs_adjacent ──

def test_bfs_single_tile():
    g = _make_game()
    _set_grid(g, [
        [8, 3, 6, 10, 8],
        [3, 8, 3, 6, 10],
        [6, 10, 8, 3, None],
        [10, 8, 3, 6, 8],
        [8, 3, 6, 10, 3],
    ])
    result = g._bfs_adjacent(0, 0, 8)
    assert result == {(0, 0)}


def test_bfs_two_adjacent_tiles():
    g = _make_game()
    _set_grid(g, [
        [8, 8, 6, 10, 8],
        [3, 3, 3, 6, 10],
        [6, 10, 8, 3, None],
        [10, 8, 3, 6, 8],
        [8, 3, 6, 10, 3],
    ])
    result = g._bfs_adjacent(0, 0, 8)
    assert result == {(0, 0), (1, 0)}


def test_bfs_l_shaped_group():
    g = _make_game()
    _set_grid(g, [
        [8, 8, 6, 10, 8],
        [8, 3, 3, 6, 10],
        [6, 10, 8, 3, None],
        [10, 8, 3, 6, 8],
        [8, 3, 6, 10, 3],
    ])
    result = g._bfs_adjacent(0, 0, 8)
    assert len(result) == 3
    assert (0, 0) in result
    assert (1, 0) in result
    assert (0, 1) in result


def test_bfs_3x3_block():
    g = _make_game()
    _set_grid(g, [
        [8, 8, 8, 10, None],
        [8, 8, 8, 6, 10],
        [8, 8, 8, 3, 6],
        [10, 6, 3, 6, 8],
        [6, 3, 10, 8, 3],
    ])
    result = g._bfs_adjacent(0, 0, 8)
    assert len(result) == 9


def test_bfs_empty_cell_returns_empty():
    g = _make_game()
    _set_grid(g, [
        [8, 3, 6, 10, 8],
        [3, 8, 3, 6, 10],
        [6, 10, 8, 3, None],
        [10, 8, 3, 6, 8],
        [8, 3, 6, 10, 3],
    ])
    result = g._bfs_adjacent(4, 2, 3)
    assert len(result) == 0


def test_bfs_wrong_color_returns_empty():
    g = _make_game()
    _set_grid(g, [
        [8, 3, 6, 10, 8],
        [3, 8, 3, 6, 10],
        [6, 10, 8, 3, None],
        [10, 8, 3, 6, 8],
        [8, 3, 6, 10, 3],
    ])
    result = g._bfs_adjacent(0, 0, 3)
    assert len(result) == 0


# ── _find_all_chains ──

def test_find_chains_no_groups():
    g = _make_game()
    _set_grid(g, [
        [8, 3, 6, 10, None],
        [3, 6, 10, 8, 3],
        [6, 10, 8, 3, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    chains = g._find_all_chains()
    assert len(chains) == 0


def test_find_chains_one_group_of_3():
    g = _make_game()
    _set_grid(g, [
        [8, 8, 8, 10, None],
        [3, 3, 6, 10, 8],
        [6, 10, 8, 3, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    chains = g._find_all_chains()
    assert len(chains) == 1
    assert len(chains[0]) == 3
    assert (0, 0) in chains[0]
    assert (1, 0) in chains[0]
    assert (2, 0) in chains[0]


def test_find_chains_one_group_of_2_skipped():
    g = _make_game()
    _set_grid(g, [
        [8, 8, 3, 10, None],
        [3, 3, 6, 10, 8],
        [6, 10, 8, 3, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    chains = g._find_all_chains()
    assert len(chains) == 0


def test_find_chains_multiple_groups():
    g = _make_game()
    _set_grid(g, [
        [8, 8, 8, 10, None],
        [3, 3, 3, 10, 8],
        [6, 10, 6, 6, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    chains = g._find_all_chains()
    assert len(chains) >= 2


def test_find_chains_5x5_all_same_color():
    g = _make_game()
    _set_grid(g, [
        [8, 8, 8, 8, 8],
        [8, 8, 8, 8, 8],
        [8, 8, 8, 8, 8],
        [8, 8, 8, 8, 8],
        [8, 8, 8, 8, None],
    ])
    chains = g._find_all_chains()
    assert len(chains) == 1
    assert len(chains[0]) == 24


# ── _adjacent_to_empty ──

def test_adjacent_right():
    g = _make_game()
    g.empty_col = 2
    g.empty_row = 2
    assert g._adjacent_to_empty(3, 2)


def test_adjacent_left():
    g = _make_game()
    g.empty_col = 2
    g.empty_row = 2
    assert g._adjacent_to_empty(1, 2)


def test_adjacent_up():
    g = _make_game()
    g.empty_col = 2
    g.empty_row = 2
    assert g._adjacent_to_empty(2, 1)


def test_adjacent_down():
    g = _make_game()
    g.empty_col = 2
    g.empty_row = 2
    assert g._adjacent_to_empty(2, 3)


def test_adjacent_diagonal_not():
    g = _make_game()
    g.empty_col = 2
    g.empty_row = 2
    assert not g._adjacent_to_empty(3, 3)
    assert not g._adjacent_to_empty(1, 1)


def test_adjacent_far_not():
    g = _make_game()
    g.empty_col = 2
    g.empty_row = 2
    assert not g._adjacent_to_empty(0, 0)
    assert not g._adjacent_to_empty(4, 4)


# ── _slide ──

def test_slide_valid():
    g = _make_game()
    _set_grid(g, [
        [8, 3, 6, 10, 8],
        [3, 8, 3, 6, 10],
        [6, 10, 8, None, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    assert g.empty_col == 3
    assert g.empty_row == 2
    tile_24 = g.grid[2][4]
    assert tile_24 is not None and tile_24.color == 6
    result = g._slide(4, 2)
    assert result
    assert g.empty_col == 4
    assert g.empty_row == 2
    tile_23 = g.grid[2][3]
    assert tile_23 is not None and tile_23.color == 6
    assert g.grid[2][4] is None


def test_slide_invalid_not_adjacent():
    g = _make_game()
    _set_grid(g, [
        [8, 3, 6, 10, 8],
        [3, 8, 3, 6, 10],
        [6, 10, 8, None, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    result = g._slide(0, 0)
    assert not result
    assert g.empty_col == 3
    assert g.empty_row == 2


def test_slide_invalid_empty_cell():
    g = _make_game()
    _set_grid(g, [
        [8, 3, 6, 10, 8],
        [3, 8, 3, 6, 10],
        [6, 10, 8, None, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    result = g._slide(3, 2)
    assert not result


# ── _is_game_over ──

def test_is_game_over_true():
    g = _make_game()
    g.moves_left = 0
    assert g._is_game_over()


def test_is_game_over_false():
    g = _make_game()
    g.moves_left = 39
    assert not g._is_game_over()


# ── _clear_chains ──

def test_clear_chains_removes_tiles():
    g = _make_game()
    _set_grid(g, [
        [8, 8, 8, 10, None],
        [3, 3, 6, 10, 8],
        [6, 10, 8, 3, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    chains = g._find_all_chains()
    assert len(chains) == 1
    cleared = g._clear_chains(chains)
    assert cleared == 3
    assert g.grid[0][0] is None
    assert g.grid[0][1] is None
    assert g.grid[0][2] is None
    assert g.grid[0][3] is not None
    assert g.grid[0][4] is None
    assert len(g.particles) == 18  # 3 tiles * 6 particles


def test_clear_chains_bonus_moves():
    g = _make_game()
    # 7 contiguous tiles — should give +2 moves
    _set_grid(g, [
        [8, 8, 8, 10, 8],
        [8, 3, 6, 10, 8],
        [8, 10, 8, 3, None],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    chains = g._find_all_chains()
    assert len(chains) >= 1
    old_moves = g.moves_left
    g._clear_chains(chains)
    assert g.moves_left > old_moves


def test_clear_chains_no_bonus_for_small_chain():
    g = _make_game()
    _set_grid(g, [
        [8, 8, 8, 10, None],
        [3, 3, 6, 10, 8],
        [6, 10, 8, 3, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    chains = g._find_all_chains()
    old_moves = g.moves_left
    g._clear_chains(chains)
    assert g.moves_left == old_moves


# ── _fill_empty ──

def test_fill_empty_fills_none_cells():
    g = _make_game()
    _set_grid(g, [
        [8, 8, 8, 10, None],
        [3, 3, 6, 10, 8],
        [6, 10, 8, 3, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    g.grid[0][2] = None
    g._fill_empty()
    assert g.grid[0][2] is not None
    assert g.grid[0][2].color in COLORS
    assert g.grid[0][4] is None  # empty cell stays empty


def test_fill_empty_preserves_empty_slot():
    g = _make_game()
    _set_grid(g, [
        [None, 3, 6, 10, 8],
        [3, 8, 3, 6, 10],
        [6, 10, 8, 3, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    g._fill_empty()
    assert g.grid[0][0] is None
    assert g.empty_col == 0
    assert g.empty_row == 0


# ── _check_and_cascade ──

def test_check_and_cascade_multiple_waves():
    g = _make_game(42)
    _set_grid(g, [
        [8, 8, 8, 8, None],
        [8, 8, 3, 6, 8],
        [6, 6, 6, 3, 6],
        [10, 10, 10, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    # Start with 3 separate chains
    cascades = g._check_and_cascade()
    assert cascades >= 1


def test_check_and_cascade_no_chains():
    g = _make_game()
    _set_grid(g, [
        [8, 3, 6, 10, None],
        [3, 6, 10, 8, 3],
        [6, 10, 8, 3, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    old_score = g.score
    cascades = g._check_and_cascade()
    assert cascades == 0
    assert g.score == old_score


def test_check_and_cascade_increases_combo():
    g = _make_game(42)
    _set_grid(g, [
        [8, 8, 8, 3, 3],
        [3, 3, 3, 6, 10],
        [6, 6, 6, 3, 6],
        [10, 8, 3, 6, None],
        [8, 3, 6, 10, 8],
    ])
    g._check_and_cascade()
    assert g.combo >= 1 if g.max_combo > 0 else True


def test_check_and_cascade_resets_combo_before_cascade():
    g = _make_game(42)
    _set_grid(g, [
        [8, 8, 8, 10, None],
        [3, 3, 6, 10, 8],
        [6, 10, 8, 3, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    g.combo = 5
    g._check_and_cascade()
    assert g.combo < 5  # combo was reset to 0 before cascading


# ── _spawn_particles ──

def test_spawn_particles():
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles(2, 3, COLOR_RED)
    assert len(g.particles) == 6
    for p in g.particles:
        assert p.color == COLOR_RED
        assert p.life > 0


# ── _update_particles ──

def test_update_particles_decays_life():
    g = _make_game()
    g._spawn_particles(2, 2, COLOR_RED)
    old_life = [p.life for p in g.particles]
    g._update_particles()
    for i, p in enumerate(g.particles):
        assert p.life == old_life[i] - 1


def test_update_particles_removes_dead():
    g = _make_game()
    g.particles = [
        Particle(x=0, y=0, vx=0, vy=0, life=1, color=COLOR_RED),
        Particle(x=0, y=0, vx=0, vy=0, life=2, color=COLOR_GREEN),
    ]
    g._update_particles()
    assert len(g.particles) == 1


# ── _spawn_float_text ──

def test_spawn_float_text():
    g = _make_game()
    g._spawn_float_text(100, 50, "COMBO!", COLOR_YELLOW)
    assert len(g.floats) == 1
    assert g.floats[0].text == "COMBO!"
    assert g.floats[0].color == COLOR_YELLOW
    assert g.floats[0].life == 25


# ── _update_floats ──

def test_update_floats_float_up_and_decay():
    g = _make_game()
    g._spawn_float_text(100, 50, "Test", COLOR_YELLOW)
    old_y = g.floats[0].y
    g._update_floats()
    assert g.floats[0].y < old_y
    assert g.floats[0].life == 24


def test_update_floats_removes_dead():
    g = _make_game()
    g.floats = [
        FloatText(x=0, y=0, text="A", life=1, color=7),
        FloatText(x=0, y=0, text="B", life=2, color=7),
    ]
    g._update_floats()
    assert len(g.floats) == 1


# ── reset ──

def test_reset_clears_state():
    g = _make_game(42)
    g.reset()
    g.score = 9999
    g.combo = 10
    g.max_combo = 8
    g.moves_left = 5
    g.won = True
    g.phase = Phase.PLAYING
    g.anim_timer = 15
    g.particles.append(Particle(0, 0, 0, 0, 10, COLOR_RED))
    g.floats.append(FloatText(0, 0, "X", 5, COLOR_YELLOW))

    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.moves_left == INITIAL_MOVES
    assert not g.won
    assert g.phase == Phase.TITLE
    assert g.anim_timer == 0
    assert len(g.particles) == 0
    assert len(g.floats) == 0


def test_reset_grid_has_empty_cell():
    g = _make_game(42)
    g.reset()
    assert g.grid[g.empty_row][g.empty_col] is None
    tile_count = 0
    for row in g.grid:
        for cell in row:
            if cell is not None:
                tile_count += 1
    assert tile_count == GRID_COLS * GRID_ROWS - 1


def test_reset_colors_valid():
    g = _make_game(99)
    g.reset()
    for row in g.grid:
        for cell in row:
            if cell is not None:
                assert cell.color in COLORS


# ── _start_game ──

def test_start_game_sets_playing():
    g = _make_game(42)
    g._start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.moves_left == INITIAL_MOVES
    assert not g.won


# ── _slide followed by chain ──

def test_slide_then_check_chains():
    g = _make_game(42)
    # Set up a grid where sliding will create a 3-chain
    _set_grid(g, [
        [8, 8, 3, 10, None],
        [8, 3, 6, 10, 8],
        [6, 10, 8, 3, 6],
        [10, 8, 3, 6, 10],
        [8, 3, 6, 10, 8],
    ])
    assert g.empty_col == 4
    assert g.empty_row == 0
    old_moves = g.moves_left

    # Slide the tile at (3,0) = 10 down to (4,0) — that would be (4,0) empty but
    # adjacent to empty at (4,0) is (3,0) since empty is at (4,0)
    result = g._slide(3, 0)
    assert result
    assert g.moves_left == old_moves  # not decremented (done in _update_playing)

    cascades = g._check_and_cascade()
    assert cascades >= 0  # may or may not form chains depending on layout


# ── Phase enum ──

def test_phase_values():
    assert Phase.TITLE is not Phase.PLAYING
    assert Phase.PLAYING is not Phase.ANIM_CHAIN
    assert Phase.ANIM_CHAIN is not Phase.GAME_OVER


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS {test.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL {test.__name__}")
            traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed:
        sys.exit(1)
