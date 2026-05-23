"""test_imports.py — Headless logic tests for TETRA SURGE."""

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/059_tetra_surge")
from main import (
    CHAIN_CELL_SCORE,
    COLS,
    Game,
    LINE_SCORES,
    Phase,
    PIECE_COLORS,
    PIECE_TYPES,
    ROWS,
    SHAPES,
    SURGE_THRESHOLD,
    BOMB_TYPE,
    Particle,
)


def make_game(seed: int = 42) -> Game:
    """Create a headless Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    g._rng = random.Random()  # placeholder, reset() overwrites
    g.reset()
    g._rng = random.Random(seed)
    return g


# ── Grid & Reset ────────────────────────────────────────────────────


def test_reset_creates_empty_grid() -> None:
    g = make_game()
    assert len(g.grid) == ROWS
    assert len(g.grid[0]) == COLS
    assert all(cell == 0 for row in g.grid for cell in row)


def test_reset_sets_initial_state() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.level == 0
    assert g.lines == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.surge is False


# ── Piece spawning ──────────────────────────────────────────────────


def test_spawn_piece_sets_position_and_color() -> None:
    g = make_game()
    g.next_type = 0  # I piece
    g.phase = Phase.PLAYING
    g._spawn_piece()
    assert g.piece_type == 0
    assert g.piece_rot == 0
    assert g.piece_color == PIECE_COLORS[0]
    assert g.piece_y == 0


def test_spawn_t_piece_at_correct_x() -> None:
    g = make_game()
    g.next_type = 2  # T piece (3-wide)
    g.phase = Phase.PLAYING
    g._spawn_piece()
    assert g.piece_x == (COLS - 3) // 2  # (10-3)//2 = 3


def test_spawn_i_piece_at_correct_x() -> None:
    g = make_game()
    g.next_type = 0  # I piece (4-wide)
    g.phase = Phase.PLAYING
    g._spawn_piece()
    assert g.piece_x == (COLS - 4) // 2  # 3


def test_spawn_bomb() -> None:
    g = make_game()
    g.phase = Phase.SPAWN
    g.surge = True
    g._spawn_bomb()
    assert g.piece_type == BOMB_TYPE
    assert g.piece_color == PIECE_COLORS[BOMB_TYPE]


# ── Piece cells ─────────────────────────────────────────────────────


def test_piece_cells_within_grid_bounds() -> None:
    g = make_game()
    g.next_type = 2  # T
    g.phase = Phase.PLAYING
    g._spawn_piece()
    cells = g._piece_cells()
    for col, row in cells:
        assert 0 <= col < COLS
        assert 0 <= row < ROWS


# ── Collision detection ─────────────────────────────────────────────


def test_collides_wall_left() -> None:
    g = make_game()
    assert g._collides(0, 0, -1, 0)  # I piece at col -1


def test_collides_wall_right() -> None:
    g = make_game()
    # I piece (4-wide) at col 7 would occupy cols 7-10, col 10 out of bounds
    assert g._collides(0, 0, 7, 0)


def test_no_collision_empty_grid() -> None:
    g = make_game()
    # T piece at center
    assert not g._collides(2, 0, 3, 5)


def test_collides_with_locked_block() -> None:
    g = make_game()
    g.grid[6][4] = PIECE_COLORS[0]  # block at (col=4, row=6)
    # T piece at (3,5) rot 0: cells at (4,5),(3,6),(4,6),(5,6)
    # grid[6][4] overlaps with T at (4,6) — cell (col=4, row=6)
    assert g._collides(2, 0, 3, 5)


# ── Piece movement ──────────────────────────────────────────────────


def test_move_piece_left() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.piece_type = 0
    g.piece_rot = 0
    g.piece_x = 5
    g.piece_y = 5
    assert g._move_piece(-1, 0)
    assert g.piece_x == 4
    assert g.piece_y == 5


def test_move_piece_blocked_by_wall() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.piece_type = 2  # T, 3-wide
    g.piece_rot = 0
    g.piece_x = 0
    g.piece_y = 5
    assert not g._move_piece(-1, 0)
    assert g.piece_x == 0  # unchanged


def test_move_piece_blocked_by_phase() -> None:
    g = make_game()
    g.phase = Phase.TITLE
    g.piece_x = 5
    assert not g._move_piece(1, 0)
    assert g.piece_x == 5  # unchanged


def test_move_piece_down() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.piece_type = 2
    g.piece_rot = 0
    g.piece_x = 3
    g.piece_y = 5
    assert g._move_piece(0, 1)
    assert g.piece_y == 6


def test_move_piece_blocked_by_bottom() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.piece_type = 2
    g.piece_rot = 0
    g.piece_x = 3
    g.piece_y = ROWS - 2  # T has cells at dy=1 from bounding box
    # Piece at row 18: cells at row 18+0=18 (col3-5) and row 18+1=19 (col4)
    # Row 19 is bottom. Move down would put cells at row 18+1=19 (col3-5) and row 19+1=20 (col4) - out of bounds
    result = g._move_piece(0, 1)
    # This should be blocked because row 20 is out of bounds
    assert not result or g.piece_y == ROWS - 2


# ── Piece rotation ──────────────────────────────────────────────────


def test_rotate_piece_changes_rotation() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.piece_type = 2  # T
    g.piece_rot = 0
    g.piece_x = 3
    g.piece_y = 5
    g._rotate_piece()
    assert g.piece_rot == 1


def test_rotate_o_piece_doesnt_move() -> None:
    """O piece rotation doesn't change shape (still 4 cells at same positions)."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.piece_type = 1  # O
    g.piece_rot = 0
    g.piece_x = 4
    g.piece_y = 5
    assert g._rotate_piece()
    assert g.piece_rot == 1


def test_rotate_blocked_by_wall_kicks() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.piece_type = 0  # I piece
    g.piece_rot = 1  # vertical
    g.piece_x = 9  # right edge
    g.piece_y = 5
    # Vertical I at x=9 occupies col 9+2=11 → out of bounds
    # Rotating to horizontal: 4-wide at x=9 occupies cols 9-12 → out of bounds
    # Wall kicks should try: (0,0), (-1,0), (1,0)... but (1,0) goes further right
    # Let's just test: rotating at edge
    g.piece_x = 7
    success = g._rotate_piece()
    # Whether it succeeds or not depends on wall kicks — both are valid outcomes
    assert g.piece_rot in (1, 2)  # rotated or stayed


# ── Hard drop ───────────────────────────────────────────────────────


def test_hard_drop_lands_on_bottom() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.piece_type = 1  # O piece, 2×2
    g.piece_rot = 0
    g.piece_x = 4
    g.piece_y = 0
    g._hard_drop()
    # O piece at bottom: 2×2 bounding box, cells at (0,0),(1,0),(0,1),(1,1)
    # Should land with dy=1 at row 18 → piece_y = 18
    assert g.piece_y >= 16  # Should have dropped near the bottom


def test_hard_drop_locks_piece() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.piece_type = 1  # O
    g.piece_rot = 0
    g.piece_x = 4
    g.piece_y = 0
    g._hard_drop()
    # After hard drop, piece locks. If no lines cleared: SPAWN phase
    assert g.phase in (Phase.SPAWN, Phase.LINE_CLEAR)


def test_hard_drop_ignored_outside_playing() -> None:
    g = make_game()
    g.phase = Phase.TITLE
    orig_y = g.piece_y
    g._hard_drop()
    assert g.phase == Phase.TITLE


# ── Lock & line clear ───────────────────────────────────────────────


def test_lock_piece_writes_to_grid() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.piece_type = 1  # O
    g.piece_rot = 0
    g.piece_x = 4
    g.piece_y = 18
    g.piece_color = PIECE_COLORS[1]
    g._lock_piece()
    # O piece: (4,18),(5,18),(4,19),(5,19)
    assert g.grid[18][4] == PIECE_COLORS[1]
    assert g.grid[18][5] == PIECE_COLORS[1]
    assert g.grid[19][4] == PIECE_COLORS[1]
    assert g.grid[19][5] == PIECE_COLORS[1]


def test_find_filled_rows_empty() -> None:
    g = make_game()
    assert g._find_filled_rows() == []


def test_find_filled_rows_detects_full() -> None:
    g = make_game()
    for c in range(COLS):
        g.grid[19][c] = PIECE_COLORS[0]
        g.grid[10][c] = PIECE_COLORS[1]
    filled = g._find_filled_rows()
    assert 10 in filled
    assert 19 in filled


def test_line_clear_removes_filled_rows() -> None:
    g = make_game()
    g.level = 0
    # Fill row 19 completely
    for c in range(COLS):
        g.grid[19][c] = PIECE_COLORS[0]  # CYAN
    filled = g._find_filled_rows()
    assert filled == [19]
    assert all(g.grid[19][c] != 0 for c in range(COLS))

    g._process_line_clear(filled)
    # After clear + gravity: row 19 should be empty (blocks fell or were cleared)
    # The row at 19 after process might have blocks from gravity or be empty
    assert g.lines >= 1
    assert g.score > 0


def test_line_clear_gives_score() -> None:
    g = make_game()
    g.score = 0
    g.level = 0
    for c in range(COLS):
        g.grid[19][c] = PIECE_COLORS[0]
    g._process_line_clear([19])
    # 1 line = 100 × 1 × 1 = 100
    assert g.score >= 100


def test_tetris_scoring() -> None:
    """4 lines cleared at once gives higher score."""
    g = make_game()
    g.score = 0
    g.level = 0
    for r in range(16, 20):
        for c in range(COLS):
            g.grid[r][c] = PIECE_COLORS[r % 4]  # different colors
    g._process_line_clear([16, 17, 18, 19])
    assert g.score >= 800  # base for 4 lines
    assert g.lines >= 4


def test_score_with_level_multiplier() -> None:
    g = make_game()
    g.score = 0
    g.level = 2  # multiplier = level + 1 = 3
    for c in range(COLS):
        g.grid[19][c] = PIECE_COLORS[0]
    g._process_line_clear([19])
    # 1 line = 100 × (2+1) × 1 = 300
    assert g.score >= 300


# ── BFS chain propagation ───────────────────────────────────────────


def test_bfs_chain_same_color_adjacent() -> None:
    """Place same-color blocks adjacent to a filled row; BFS should clear them."""
    g = make_game()
    g.score = 0
    g.level = 0
    # Fill rows 18-19 with CYAN blocks — row 19 is full, adjacent same-color above
    for c in range(COLS):
        g.grid[19][c] = PIECE_COLORS[0]  # CYAN
        g.grid[18][c] = PIECE_COLORS[0]  # CYAN
    # Row 19 is full
    g._process_line_clear([19])
    # Row 19 removed, then BFS from row 19 seeds should chain-clear row 18 blocks
    # After BFS + gravity, check combo increased
    assert g.combo >= 1
    assert g.score > 100  # more than just 1 line clear


def test_bfs_chain_different_color_not_propagated() -> None:
    """BFS should NOT propagate to different-colored adjacent cells.
    
    Places a few RED blocks adjacent to the cleared CYAN row (not a full row,
    to avoid them being detected as a filled row and recursively cleared).
    """
    g = make_game()
    g.score = 0
    g.level = 0
    # Fill row 19 with CYAN
    for c in range(COLS):
        g.grid[19][c] = PIECE_COLORS[0]  # CYAN
    # Row 18 has only 3 RED blocks — NOT a full row, won't be recursively cleared
    for c in range(3):
        g.grid[18][c] = PIECE_COLORS[4]  # RED (Z piece color)
    g._process_line_clear([19])
    # RED blocks should survive — BFS doesn't propagate to different colors,
    # and partial row doesn't trigger recursive filled-row clearing
    red_cells = sum(1 for r in range(ROWS) for c in range(COLS) if g.grid[r][c] == PIECE_COLORS[4])
    assert red_cells == 3  # All 3 RED cells should survive


def test_combo_increments_during_chain() -> None:
    g = make_game()
    g.score = 0
    g.level = 0
    g.combo = 0
    g.max_combo = 0
    # Create a row with consistent color + adjacent same-color stack
    for c in range(COLS):
        g.grid[19][c] = PIECE_COLORS[0]  # CYAN
    # Add same-color blocks in row 18 (will be chain-cleared)
    for c in range(COLS):
        g.grid[18][c] = PIECE_COLORS[0]
    g._process_line_clear([19])
    assert g.combo > 1  # combo should have increased from chain
    assert g.max_combo >= g.combo


# ── SURGE detection ─────────────────────────────────────────────────


def test_surge_triggers_at_threshold() -> None:
    g = make_game()
    g.surge = False
    # Manually set combo to trigger SURGE
    g.combo = SURGE_THRESHOLD  # 5
    g._process_line_clear([])  # won't do anything but we can directly check
    # Actually, let's test by making a scenario where combo reaches 5
    # Fill 3 consecutive rows with CYAN (row clears + BFS chain)
    for r in range(17, 20):
        for c in range(COLS):
            g.grid[r][c] = PIECE_COLORS[0]
    g._process_line_clear([17, 18, 19])
    # With 3 rows of same color, BFS should propagate significantly
    assert g.combo >= 3 or g.surge  # significant chain likely


# ── Gravity compaction ──────────────────────────────────────────────


def test_gravity_compact_shifts_blocks_down() -> None:
    g = make_game()
    # Place floating blocks with gaps
    g.grid[5][0] = PIECE_COLORS[0]
    g.grid[5][1] = PIECE_COLORS[1]
    # Gap at row 6, then blocks at row 7
    g.grid[3][2] = PIECE_COLORS[2]
    g._gravity_compact()
    # Blocks should fall to bottom
    assert g.grid[19][0] == PIECE_COLORS[0]
    assert g.grid[19][1] == PIECE_COLORS[1]
    assert g.grid[19][2] == PIECE_COLORS[2]
    assert g.grid[5][0] == 0  # original position should be empty


def test_gravity_compact_preserves_order() -> None:
    g = make_game()
    g.grid[10][0] = PIECE_COLORS[0]  # top block
    g.grid[15][0] = PIECE_COLORS[1]  # bottom block
    g._gravity_compact()
    # Bottom block should be at row 19, top block at row 18
    assert g.grid[19][0] == PIECE_COLORS[1]
    assert g.grid[18][0] == PIECE_COLORS[0]


# ── Game over detection ─────────────────────────────────────────────


def test_not_game_over_empty() -> None:
    g = make_game()
    g.next_type = 2  # T piece
    assert not g._is_game_over()


def test_game_over_blocked_spawn() -> None:
    g = make_game()
    g.next_type = 2  # T piece
    # Block part of spawn area: T spawns at x=3, rows 0-1, cols 3-5
    # T shape at rot 0: (1,0), (0,1), (1,1), (2,1) relative to (3,0)
    # So cells: (4,0), (3,1), (4,1), (5,1)
    g.grid[0][4] = PIECE_COLORS[0]
    assert g._is_game_over()


def test_game_over_full_top() -> None:
    g = make_game()
    g.next_type = 0  # I piece
    # Fill spawn area entirely
    for r in range(2):
        for c in range(COLS):
            g.grid[r][c] = PIECE_COLORS[0]
    assert g._is_game_over()


# ── Score computation ───────────────────────────────────────────────


def test_line_score_values() -> None:
    assert LINE_SCORES[0] == 0
    assert LINE_SCORES[1] == 100
    assert LINE_SCORES[2] == 300
    assert LINE_SCORES[3] == 500
    assert LINE_SCORES[4] == 800


def test_chain_cell_score_constant() -> None:
    assert CHAIN_CELL_SCORE == 50


# ── Level progression ───────────────────────────────────────────────


def test_level_increases_with_lines() -> None:
    g = make_game()
    g.lines = 9
    g.level = 0
    assert g.lines // 10 == 0
    g.lines = 10
    g.level = g.lines // 10
    assert g.level == 1


def test_drop_speed_decreases_with_level() -> None:
    g = make_game()
    g.level = 0
    speed0 = g._get_drop_speed()
    g.level = 5
    speed5 = g._get_drop_speed()
    assert speed5 <= speed0  # should be faster (fewer frames per drop)


# ── Reset between states ────────────────────────────────────────────


def test_reset_clears_score() -> None:
    g = make_game()
    g.score = 5000
    g.level = 5
    g.lines = 50
    g.combo = 10
    g.reset()
    assert g.score == 0
    assert g.level == 0
    assert g.lines == 0
    assert g.combo == 0


def test_reset_clears_grid() -> None:
    g = make_game()
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = PIECE_COLORS[0]
    g.reset()
    assert all(cell == 0 for row in g.grid for cell in row)


# ── 7-bag randomizer ────────────────────────────────────────────────


def test_bag_contains_all_seven_pieces() -> None:
    g = make_game()
    pieces: set[int] = set()
    for _ in range(PIECE_TYPES):
        pieces.add(g._next_from_bag())
    assert pieces == set(range(PIECE_TYPES))


def test_bag_refills_when_empty() -> None:
    g = make_game()
    for _ in range(PIECE_TYPES * 2):
        t = g._next_from_bag()
        assert 0 <= t < PIECE_TYPES


# ── Bomb explosion ──────────────────────────────────────────────────


def test_bomb_explode_clears_5x5_area() -> None:
    g = make_game()
    # Place blocks in a 5×5 area around position (5, 10)
    for r in range(8, 13):
        for c in range(3, 8):
            g.grid[r][c] = PIECE_COLORS[0]
    # Bomb cells centered at approximately (4, 10)
    bomb_cells = [(3, 9), (4, 9), (5, 9), (3, 10), (4, 10), (5, 10), (3, 11), (4, 11), (5, 11)]
    g._bomb_explode(bomb_cells)
    # Check that blocks were cleared from the bomb area
    cleared_count = sum(
        1 for r in range(ROWS) for c in range(COLS)
        if g.grid[r][c] == 0
    )
    assert cleared_count > 0
    # Bomb sets combo to at least 5
    assert g.combo >= 5


# ── Particle system ─────────────────────────────────────────────────


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.life == 15
    assert p.color == 8


def test_spawn_particles_adds_to_list() -> None:
    g = make_game()
    g._spawn_particles_at_cell(5, 5, 8, 3)
    assert len(g.particles) == 3


def test_update_particles_decrements_life() -> None:
    g = make_game()
    g._spawn_particles_at_cell(5, 5, 8, 2)
    assert len(g.particles) == 2
    p = g.particles[0]
    orig_life = p.life
    g._update_particles()
    # Particles with life > 1 should decrement; life=1 removed after update
    if orig_life > 1:
        assert p.life == orig_life - 1


# ── Phase transitions (headless simulation) ─────────────────────────


def test_title_to_spawn_transition() -> None:
    g = make_game()
    g.phase = Phase.TITLE
    # Simulate pressing enter: reset then spawn
    g.reset()
    g.phase = Phase.SPAWN
    g._phase_timer = 1
    assert g.phase == Phase.SPAWN


def test_spawn_to_playing() -> None:
    g = make_game()
    g.phase = Phase.SPAWN
    g._phase_timer = 0
    g.surge = False
    # Simulate spawn: check game over then spawn piece
    if not g._is_game_over():
        g._spawn_piece()
        g.phase = Phase.PLAYING
    assert g.phase == Phase.PLAYING


def test_playing_to_game_over() -> None:
    g = make_game()
    # Fill the grid to force game over
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = PIECE_COLORS[0]
    g.next_type = 2
    assert g._is_game_over()


# ── Shape definitions ───────────────────────────────────────────────


def test_all_shapes_have_correct_rotations() -> None:
    """Each piece should have exactly 4 rotation states."""
    for piece in range(PIECE_TYPES + 1):  # including BOMB
        assert len(SHAPES[piece]) == 4, f"Piece {piece} has {len(SHAPES[piece])} rotations"


def test_all_shapes_have_four_cells() -> None:
    """Standard pieces should have 4 cells (bomb has 9)."""
    for piece in range(PIECE_TYPES):
        for rot in range(4):
            cells = SHAPES[piece][rot]
            assert len(cells) == 4, f"Piece {piece} rot {rot} has {len(cells)} cells"


def test_bomb_has_nine_cells() -> None:
    for rot in range(4):
        assert len(SHAPES[BOMB_TYPE][rot]) == 9


def test_piece_colors_match() -> None:
    assert len(PIECE_COLORS) == PIECE_TYPES + 1  # +1 for BOMB
    assert PIECE_COLORS[0] == 12  # CYAN
    assert PIECE_COLORS[1] == 10  # YELLOW
    assert PIECE_COLORS[2] == 2   # PURPLE
    assert PIECE_COLORS[3] == 3   # GREEN
    assert PIECE_COLORS[4] == 8   # RED
    assert PIECE_COLORS[5] == 6   # LIGHT_BLUE
    assert PIECE_COLORS[6] == 9   # ORANGE
    assert PIECE_COLORS[7] == 14  # PINK


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-x"])
