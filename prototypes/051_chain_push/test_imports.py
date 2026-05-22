"""test_imports.py — Headless logic tests for Chain Push.

Runs in CI / WSL without display. Tests core data structures and game logic
without touching Pyxel's Rust runtime.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    CELL,
    COLS,
    COLOR_INTS,
    NUM_COLORS,
    LEVEL_DEFS,
    ROWS,
    SCREEN_H,
    SCREEN_W,
    TIER_MAX,
    TIER_VALUES,
    Block,
    Game,
    Particle,
    Phase,
    Target,
)


def test_constants() -> None:
    """Verify constants are sane."""
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert COLS == 8
    assert ROWS == 8
    assert CELL == 32
    assert NUM_COLORS == 4
    assert len(COLOR_INTS) == 4
    assert TIER_MAX == 3
    assert TIER_VALUES[1:] == (10, 30, 90)
    assert len(LEVEL_DEFS) == 5


def test_block_dataclass() -> None:
    """Test Block creation and attributes."""
    b = Block(2, 3, 0, 1)
    assert b.col == 2
    assert b.row == 3
    assert b.color == 0
    assert b.tier == 1

    b2 = Block(5, 5, 3, 2)
    assert b2.tier == 2
    assert b2.color == 3


def test_target_dataclass() -> None:
    """Test Target creation."""
    t1 = Target(3, 4, 0)
    assert t1.col == 3
    assert t1.row == 4
    assert t1.color == 0

    t2 = Target(5, 5, -1)  # any color
    assert t2.color == -1


def test_particle_dataclass() -> None:
    """Test Particle creation and fields."""
    p = Particle(100.0, 50.0, 1.5, -2.0, 15, 8)
    assert p.x == 100.0
    assert p.y == 50.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8


def test_phase_enum() -> None:
    """Test Phase enum values."""
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.RESOLVING in Phase
    assert Phase.LEVEL_CLEAR in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.VICTORY in Phase


def test_grid_bounds() -> None:
    """Test in_bounds helper."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    # Pre-init attributes
    g.phase = Phase.TITLE
    g.level = 0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_depth = 0
    g.moves = 0
    g.player_col = 0
    g.player_row = 0
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.targets = []
    g.particles = []
    g._merged_blocks = []
    g._resolve_queue = []
    g._spread_queue = []
    g._resolve_timer = 0
    g._level_clear_timer = 0
    g._title_frame = 0
    g.reset()

    assert g._in_bounds(0, 0)
    assert g._in_bounds(COLS - 1, ROWS - 1)
    assert g._in_bounds(3, 4)
    assert not g._in_bounds(-1, 0)
    assert not g._in_bounds(0, -1)
    assert not g._in_bounds(COLS, 0)
    assert not g._in_bounds(0, ROWS)


def test_grid_to_pixel() -> None:
    """Test grid-to-pixel coordinate conversion."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.phase = Phase.TITLE
    g.level = 0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_depth = 0
    g.moves = 0
    g.player_col = 0
    g.player_row = 0
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.targets = []
    g.particles = []
    g._merged_blocks = []
    g._resolve_queue = []
    g._spread_queue = []
    g._resolve_timer = 0
    g._level_clear_timer = 0
    g._title_frame = 0
    g.reset()

    px, py = g._grid_to_pixel(0, 0)
    assert px == CELL // 2  # 16
    assert py == CELL // 2  # 16

    px2, py2 = g._grid_to_pixel(3, 4)
    assert px2 == 3 * CELL + CELL // 2  # 112
    assert py2 == 4 * CELL + CELL // 2  # 144


def test_level1_load() -> None:
    """Test level 1 loads correctly."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()

    g._load_level(1)
    assert g.level == 1
    assert g.phase == Phase.TITLE  # reset sets TITLE, _load_level doesn't change phase
    assert g.player_col == 0
    assert g.player_row == 3
    assert len(g.targets) == 1
    assert g.targets[0].col == 3
    assert g.targets[0].row == 3
    assert g.targets[0].color == 0

    # Check blocks
    assert g.grid[3][1] is not None
    assert g.grid[3][1].color == 0
    assert g.grid[3][1].tier == 1
    assert g.grid[3][3] is not None
    assert g.grid[3][3].color == 0
    assert g.grid[3][3].tier == 1

    # Check empty cells
    assert g.grid[3][0] is None
    assert g.grid[3][2] is None


def test_merge_detection() -> None:
    """Test merge group detection via BFS."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    # Place two adjacent RED blocks
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 1)
    g.grid[3][3] = Block(3, 3, 0, 1)

    groups = g._find_merge_groups()
    assert len(groups) == 1
    assert len(groups[0]) == 2
    blocks = {(b.col, b.row) for b in groups[0]}
    assert blocks == {(2, 3), (3, 3)}


def test_no_merge_different_colors() -> None:
    """Test that different colors don't merge."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 1)  # RED
    g.grid[3][3] = Block(3, 3, 1, 1)  # GREEN

    groups = g._find_merge_groups()
    assert len(groups) == 0


def test_no_merge_single_block() -> None:
    """Test that a single block doesn't form a group."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 1)

    groups = g._find_merge_groups()
    assert len(groups) == 0


def test_merge_group_three_blocks() -> None:
    """Test BFS finds connected component of 3 same-color blocks."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 1)  # RED
    g.grid[3][3] = Block(3, 3, 0, 1)  # RED
    g.grid[2][3] = Block(3, 2, 0, 1)  # RED (north of (3,3))

    groups = g._find_merge_groups()
    assert len(groups) == 1
    assert len(groups[0]) == 3


def test_merge_two_t1_to_t2() -> None:
    """Test merging two T1 blocks creates T2."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 1)
    g.grid[3][3] = Block(3, 3, 0, 1)

    g.combo = 1
    score_before = g.score
    group = g._find_merge_groups()[0]
    g._merge_group(group)

    # Survivor should be T2 RED
    survivor = g.grid[3][3]  # higher col
    assert survivor is not None
    assert survivor.tier == 2
    assert survivor.color == 0

    # Other block removed
    assert g.grid[3][2] is None

    # Score increased
    assert g.score > score_before

    # Merged block tracked
    assert len(g._merged_blocks) == 1
    assert g._merged_blocks[0].tier == 2


def test_merge_t2_and_t1_to_t3() -> None:
    """Test merging T2 + T1 creates T3."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 2)  # RED T2
    g.grid[3][3] = Block(3, 3, 0, 1)  # RED T1

    g.combo = 1
    group = g._find_merge_groups()[0]
    g._merge_group(group)

    # T2 should be survivor, upgraded to T3
    survivor = g.grid[3][2]  # T2 at lower col → survivor
    assert survivor is not None
    assert survivor.tier == 3
    assert survivor.color == 0

    # T1 removed
    assert g.grid[3][3] is None


def test_t3_cannot_exceed_max() -> None:
    """Test T3 merging with T1 doesn't exceed TIER_MAX."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 3)  # RED T3
    g.grid[3][3] = Block(3, 3, 0, 1)  # RED T1

    g.combo = 1
    score_before = g.score
    group = g._find_merge_groups()[0]
    g._merge_group(group)

    survivor = g.grid[3][2]  # T3 lower col → survivor
    assert survivor is not None
    assert survivor.tier == 3  # stays T3 (capped)
    assert g.score > score_before  # still gets bonus score


def test_spread_changes_adjacent_color() -> None:
    """Test spread changes adjacent block's color."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 2)  # RED T2
    g.grid[3][3] = Block(3, 3, 2, 1)  # BLUE T1 — adjacent

    g._do_spread([Block(2, 3, 0, 2)])  # spread from RED T2

    # BLUE should now be RED
    assert g.grid[3][3] is not None
    assert g.grid[3][3].color == 0  # changed to RED
    assert g.grid[3][3].tier == 1  # tier unchanged


def test_spread_does_not_change_same_color() -> None:
    """Test spread doesn't affect same-color adjacent blocks."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 2)  # RED T2
    g.grid[3][3] = Block(3, 3, 0, 1)  # RED T1 — same color

    g._do_spread([Block(2, 3, 0, 2)])

    assert g.grid[3][3] is not None
    assert g.grid[3][3].color == 0  # still RED
    assert g.grid[3][3].tier == 1


def test_spread_empty_cell_ignored() -> None:
    """Test spread ignores empty adjacent cells."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 2)  # RED T2 (all neighbors empty)

    g._do_spread([Block(2, 3, 0, 2)])

    # No errors, no changes
    assert g.grid[3][2] is not None
    for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nr, nc = 3 + dr, 2 + dc
        if 0 <= nr < ROWS and 0 <= nc < COLS and not (nr == 3 and nc == 2):
            assert g.grid[nr][nc] is None


def test_t3_spread_affects_diagonals() -> None:
    """Test T3 spread affects 8-direction neighbors including diagonals."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 3)  # RED T3 at (2,3)
    g.grid[2][1] = Block(1, 2, 2, 1)  # BLUE at (1,2) — NW diagonal
    g.grid[2][3] = Block(3, 2, 1, 1)  # GREEN at (3,2) — NE diagonal
    g.grid[4][1] = Block(1, 4, 3, 1)  # YELLOW at (1,4) — SW diagonal
    g.grid[4][3] = Block(3, 4, 2, 1)  # BLUE at (3,4) — SE diagonal

    g._do_spread([Block(2, 3, 0, 3)])

    # All diagonals should change to RED
    assert g.grid[2][1].color == 0  # was BLUE
    assert g.grid[2][3].color == 0  # was GREEN
    assert g.grid[4][1].color == 0  # was YELLOW
    assert g.grid[4][3].color == 0  # was BLUE


def test_t2_spread_does_not_affect_diagonals() -> None:
    """Test T2 spread only affects 4-direction, not diagonals."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.grid[3][2] = Block(2, 3, 0, 2)  # RED T2 at (2,3)
    g.grid[2][1] = Block(1, 2, 2, 1)  # BLUE at (1,2) — NW diagonal

    g._do_spread([Block(2, 3, 0, 2)])

    # Diagonal should NOT change
    assert g.grid[2][1].color == 2  # still BLUE


def test_check_win_all_targets_covered() -> None:
    """Test win detection when all targets covered."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.targets = [Target(3, 3, 0)]
    g.grid[3][3] = Block(3, 3, 0, 2)  # RED T2 at target position

    assert g._check_win()


def test_check_win_wrong_color() -> None:
    """Test win fails when color doesn't match."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.targets = [Target(3, 3, 0)]  # RED target
    g.grid[3][3] = Block(3, 3, 1, 2)  # GREEN block

    assert not g._check_win()


def test_check_win_empty_target() -> None:
    """Test win fails when target cell is empty."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.targets = [Target(3, 3, 0)]
    g.grid[3][3] = None

    assert not g._check_win()


def test_check_win_any_color() -> None:
    """Test 'any color' target (-1) accepts any block."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)

    g.targets = [Target(3, 3, -1)]  # any color
    g.grid[3][3] = Block(3, 3, 2, 1)  # BLUE

    assert g._check_win()


def test_particle_spawn() -> None:
    """Test particle creation."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()

    g._spawn_particles(100, 100, 8, 6)
    assert len(g.particles) > 0
    for p in g.particles:
        assert p.life > 0
        assert p.color == 8


def test_particle_update() -> None:
    """Test particles expire over time."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()

    g._spawn_particles(100, 100, 8, 10)
    count = len(g.particles)
    assert count > 0

    # Run many ticks
    for _ in range(50):
        g._update_particles()

    # All should have expired
    assert len(g.particles) < count


def test_reset_clears_state() -> None:
    """Test reset clears all game state."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()

    g.phase = Phase.PLAYING
    g.score = 999
    g.combo = 5
    g.max_combo = 7
    g.level = 3
    g.moves = 42
    g.targets = [Target(0, 0, 0)]
    g.particles = [Particle(50, 50, 1, 0, 5, 8)]

    g.reset()

    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.level == 0
    assert g.moves == 0
    assert len(g.targets) == 0
    assert len(g.particles) == 0


def test_all_levels_load() -> None:
    """Test all predefined levels load without error."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()

    for i in range(1, len(LEVEL_DEFS) + 1):
        g._load_level(i)
        assert g.level == i
        assert any(b is not None for row in g.grid for b in row)  # has blocks


def test_procedural_level_generation() -> None:
    """Test procedural level generation for level >= 6."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()

    g._load_level(6)
    assert g.level == 6
    # Should have some blocks
    block_count = sum(1 for row in g.grid for b in row if b is not None)
    assert block_count > 0
    # Should have some targets
    assert len(g.targets) > 0
    # Player should be in bounds
    assert 0 <= g.player_col < COLS
    assert 0 <= g.player_row < ROWS


def test_procedural_level_player_not_on_block() -> None:
    """Test player doesn't start on a block in procedural levels."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()

    for level in range(6, 10):
        g._load_level(level)
        assert g.grid[g.player_row][g.player_col] is None


def test_level1_simulation() -> None:
    """Simulate Level 1 solution: push right → merge → win."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(1)
    g.phase = Phase.PLAYING

    # Player at (0,3). Push right into (1,3) → block moves to (2,3).
    # Simulate the push manually:
    g.grid[3][1] = None  # clear original block position
    g.grid[3][2] = Block(2, 3, 0, 1)  # block moved to (2,3)
    g.player_col = 1
    g.player_row = 3

    # Trigger resolve
    g._start_resolve()
    assert g.phase == Phase.RESOLVING

    # Run resolve to completion
    for _ in range(100):
        g._resolve_timer = 1
        g._update_resolving()
        if g.phase != Phase.RESOLVING:
            break

    # Should have detected win
    assert g.phase == Phase.LEVEL_CLEAR
    assert g.score > 0
    assert g.max_combo >= 1


def test_level2_chain_simulation() -> None:
    """Simulate Level 2: push RED → merge→spread→merge chain."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._load_level(2)
    g.phase = Phase.PLAYING

    # Player at (0,3). Move up to (0,2) first, then push (1,2) right.
    g.grid[2][1] = None  # clear (1,2)
    g.grid[2][2] = Block(2, 2, 0, 1)  # RED at (2,2)
    g.player_col = 1
    g.player_row = 2

    # Trigger resolve
    g._start_resolve()

    # Run resolve to completion
    for _ in range(100):
        g._resolve_timer = 1
        g._update_resolving()
        if g.phase != Phase.RESOLVING:
            break

    # After chain: should have T3 RED at (3,2)
    survivor = g.grid[2][3]
    assert survivor is not None
    assert survivor.tier == 3
    assert survivor.color == 0

    # (3,3) should be empty (merged into T3)
    assert g.grid[3][3] is None

    # Should still be PLAYING (GREEN target not yet covered)
    assert g.phase == Phase.PLAYING
    assert g.max_combo >= 2  # 2-step chain
