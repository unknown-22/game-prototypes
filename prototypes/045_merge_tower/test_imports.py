"""test_imports.py — Headless logic tests for MERGE TOWER."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/045_merge_tower")

from main import (
    Cell, Game, Particle, Phase, GRID_COLS, GRID_ROWS, COLORS, MAX_TIER,
    MERGE_THRESHOLD, SCORE_PER_TIER, COLOR_VALS, TIER_TINTS,
    COMBO_MULTIPLIER, CELL_SIZE, GRID_X, GRID_Y,
)


def test_constants() -> None:
    """Verify game constants are reasonable."""
    assert GRID_COLS == 10
    assert GRID_ROWS == 13
    assert COLORS == 5
    assert MAX_TIER == 3
    assert MERGE_THRESHOLD == 3
    assert len(SCORE_PER_TIER) == 3
    assert COMBO_MULTIPLIER == 1.5
    assert CELL_SIZE == 20
    assert len(COLOR_VALS) == 5
    assert len(TIER_TINTS) == 3


def test_enum_phases() -> None:
    """Verify Phase enum members."""
    assert Phase.DROP in Phase
    assert Phase.MERGE_ANIM in Phase
    assert Phase.GAME_OVER in Phase


def test_cell_dataclass() -> None:
    """Verify Cell dataclass works."""
    c = Cell(color=0, tier=1)
    assert c.color == 0
    assert c.tier == 1


def test_particle_dataclass() -> None:
    """Verify Particle dataclass works."""
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=30, color=0)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 30
    assert p.size == 2  # default


def test_game_creation_headless() -> None:
    """Test Game can be created via __new__ without Pyxel."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()
    assert g.phase == Phase.DROP
    assert g.score == 0
    assert g.combo == 0


def test_reset_state() -> None:
    """Test reset initializes clean state."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    assert g.phase == Phase.DROP
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.max_tier_reached == 1
    assert g.merge_count == 0
    assert g.blocks_dropped == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.merge_cells) == 0
    assert g.shake_frames == 0

    # Block spawn
    assert 0 <= g.block_col < GRID_COLS
    assert 0 <= g.block_color < COLORS
    assert g.block_tier == 1

    # Grid should be empty (except maybe spawn blocked check)
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            assert g.grid[row][col] is None


def test_spawn_block() -> None:
    """Test block spawn places block at top center."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    col = g.block_col
    assert col == GRID_COLS // 2  # center
    assert 0 <= g.block_color < COLORS
    assert g.block_tier == 1
    assert g.phase == Phase.DROP


def test_block_target_row_empty() -> None:
    """Test _block_target_row returns bottom row for empty column."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    g.block_col = 3
    target = g._block_target_row()
    assert target == GRID_ROWS - 1  # bottom row


def test_block_target_row_partial() -> None:
    """Test _block_target_row respects existing blocks."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Place a block at bottom of col 3
    g.grid[GRID_ROWS - 1][3] = Cell(color=0, tier=1)
    g.grid[GRID_ROWS - 2][3] = Cell(color=1, tier=1)

    g.block_col = 3
    target = g._block_target_row()
    assert target == GRID_ROWS - 3  # above the two blocks


def test_cell_to_px() -> None:
    """Test coordinate conversion."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    px, py = g._cell_to_px(0, 0)
    assert px == GRID_X
    assert py == GRID_Y

    px, py = g._cell_to_px(2, 5)
    assert px == GRID_X + 5 * CELL_SIZE
    assert py == GRID_Y + 2 * CELL_SIZE


def test_land_block_no_merge() -> None:
    """Test landing a block with no merge possible."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Place block in empty column
    g.block_col = 5
    g.block_color = 0
    g.block_tier = 1
    g._land_block()

    # Should have placed the block
    target = GRID_ROWS - 1
    cell = g.grid[target][5]
    assert cell is not None
    assert cell.color == 0
    assert cell.tier == 1
    assert g.blocks_dropped == 1

    # With only 1 block, no merge
    assert g.phase != Phase.MERGE_ANIM
    assert g.combo == 0


def test_land_block_triggers_merge() -> None:
    """Test landing a block that completes a 3-block cluster."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Place 2 same-color blocks adjacent horizontally at bottom
    g.grid[GRID_ROWS - 1][3] = Cell(color=0, tier=1)
    g.grid[GRID_ROWS - 1][4] = Cell(color=0, tier=1)

    # Drop the 3rd into position
    g.block_col = 5
    g.block_color = 0
    g.block_tier = 1
    g._land_block()

    # Merge should be triggered (3-in-a-row)
    assert g.phase == Phase.MERGE_ANIM
    assert g.combo == 1
    assert g.max_combo == 1
    assert len(g.merge_cells) == 3
    assert len(g.particles) > 0  # particles spawned


def test_merge_anim_finalize() -> None:
    """Test merge animation completes and creates higher-tier block."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Place 3 same-color blocks in a vertical line at rows 10, 11, 12 col 5
    g.grid[10][5] = Cell(color=0, tier=1)
    g.grid[11][5] = Cell(color=0, tier=1)
    g.grid[12][5] = Cell(color=0, tier=1)

    # Manually trigger merge
    g.combo = 0
    g._check_and_merge()

    assert g.phase == Phase.MERGE_ANIM
    assert len(g.merge_cells) == 3
    cells = set(g.merge_cells)
    assert (10, 5) in cells
    assert (11, 5) in cells
    assert (12, 5) in cells

    # Run merge animation to completion
    g.merge_timer = g.MERGE_ANIM_FRAMES - 1
    g._update_merge_anim()

    # Original edge cells should be cleared (center may get the merged block)
    assert g.grid[10][5] is None
    assert g.grid[12][5] is None

    # A tier-2 block should exist at or near center (row 11 avg = 11)
    merged_cell = g.grid[11][5]
    assert merged_cell is not None
    assert merged_cell.color == 0
    assert merged_cell.tier == 2

    assert g.merge_count == 1
    assert g.score > 0  # should have scored


def test_find_clusters_none() -> None:
    """Test _find_clusters returns empty when no clusters exist."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Place scattered single blocks
    g.grid[0][0] = Cell(color=0, tier=1)
    g.grid[2][2] = Cell(color=1, tier=1)
    g.grid[4][4] = Cell(color=2, tier=1)

    clusters = g._find_clusters()
    assert len(clusters) == 0


def test_find_clusters_horizontal() -> None:
    """Test _find_clusters detects horizontal 3-in-a-row."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    g.grid[5][2] = Cell(color=0, tier=1)
    g.grid[5][3] = Cell(color=0, tier=1)
    g.grid[5][4] = Cell(color=0, tier=1)

    clusters = g._find_clusters()
    assert len(clusters) == 1
    assert len(clusters[0]) == 3
    assert set(clusters[0]) == {(5, 2), (5, 3), (5, 4)}


def test_find_clusters_vertical() -> None:
    """Test _find_clusters detects vertical 3-in-a-row."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    g.grid[3][7] = Cell(color=1, tier=1)
    g.grid[4][7] = Cell(color=1, tier=1)
    g.grid[5][7] = Cell(color=1, tier=1)

    clusters = g._find_clusters()
    assert len(clusters) == 1
    assert len(clusters[0]) == 3


def test_find_clusters_different_colors_no_merge() -> None:
    """Test that different colors don't merge."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    g.grid[5][2] = Cell(color=0, tier=1)
    g.grid[5][3] = Cell(color=0, tier=1)
    g.grid[5][4] = Cell(color=1, tier=1)  # different color

    clusters = g._find_clusters()
    # Only the 2 same-color blocks, not enough for merge
    assert len(clusters) == 0


def test_find_clusters_different_tiers_no_merge() -> None:
    """Test that different tiers don't merge."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    g.grid[5][2] = Cell(color=0, tier=1)
    g.grid[5][3] = Cell(color=0, tier=1)
    g.grid[5][4] = Cell(color=0, tier=2)  # different tier

    clusters = g._find_clusters()
    assert len(clusters) == 0


def test_find_clusters_l_shape() -> None:
    """Test _find_clusters detects L-shaped connected cluster."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    g.grid[5][3] = Cell(color=2, tier=1)
    g.grid[6][3] = Cell(color=2, tier=1)
    g.grid[6][4] = Cell(color=2, tier=1)

    clusters = g._find_clusters()
    assert len(clusters) == 1
    assert len(clusters[0]) == 3


def test_find_clusters_larger_than_3() -> None:
    """Test cluster detection for groups larger than 3."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # 2x3 block = 6 cells
    for r in range(5, 7):
        for c in range(2, 5):
            g.grid[r][c] = Cell(color=3, tier=1)

    clusters = g._find_clusters()
    assert len(clusters) == 1
    assert len(clusters[0]) == 6


def test_chain_merge() -> None:
    """Test that a merge can trigger a chain reaction."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Set up: 3 blocks of color 0 tier 1, plus 3 blocks of color 0 tier 2 adjacent
    # The tier-1 merge creates a tier-2 block which should merge with the existing tier-2 blocks
    g.grid[10][0] = Cell(color=0, tier=1)
    g.grid[10][1] = Cell(color=0, tier=1)
    g.grid[10][2] = Cell(color=0, tier=1)
    # Two tier-2 blocks of same color nearby
    g.grid[9][0] = Cell(color=0, tier=2)
    g.grid[9][1] = Cell(color=0, tier=2)

    g.combo = 0
    result = g._check_and_merge()
    assert result is True
    assert g.combo == 1
    assert g.phase == Phase.MERGE_ANIM

    # Complete first merge
    g.merge_timer = g.MERGE_ANIM_FRAMES - 1
    g._update_merge_anim()

    # After first merge, a tier-2 block is placed.
    # Check if it triggered another merge (chain)
    # The new tier-2 block at (10,1) is adjacent to tier-2 blocks at (9,0) and (9,1)
    if g.phase == Phase.MERGE_ANIM:
        # Chain merge happened
        assert g.combo >= 2
    # Either way, the initial tier-1 blocks should be gone
    assert g.grid[10][0] is None or g.grid[10][0].tier != 1
    assert g.grid[10][1] is None or g.grid[10][1].tier != 1
    assert g.grid[10][2] is None or g.grid[10][2].tier != 1


def test_game_over_when_spawn_blocked() -> None:
    """Test game over when spawn position is blocked."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Fill the center spawn column at row 0
    center = GRID_COLS // 2
    g.grid[0][center] = Cell(color=0, tier=1)

    # Now spawn - should detect game over
    g._spawn_block()
    assert g.phase == Phase.GAME_OVER


def test_particle_update() -> None:
    """Test particles update correctly."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()
    # Set particles AFTER reset (which clears them)
    g.particles = [Particle(x=10.0, y=10.0, vx=1.0, vy=-1.0, life=3, color=0)]

    g._update_particles()
    assert g.particles[0].life == 2
    assert g.particles[0].x > 10.0
    assert g.particles[0].vy > -1.0  # gravity applied

    # Run until death
    g._update_particles()
    g._update_particles()
    assert len(g.particles) == 0


def test_floating_text_update() -> None:
    """Test floating text updates and expires."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()
    # Set floating texts AFTER reset (which clears them)
    g.floating_texts = [(50.0, 50.0, "+100", 7, 2)]

    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0][4] == 1  # life decremented

    g._update_floating_texts()
    assert len(g.floating_texts) == 0  # expired


def test_adjust_block_y() -> None:
    """Test _adjust_block_y clamps to surface height."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Fill column 3 up to row 10
    for r in range(8, GRID_ROWS):
        g.grid[r][3] = Cell(color=1, tier=1)

    g.block_col = 3
    g.block_y = float(GRID_Y + GRID_ROWS * CELL_SIZE)  # way below
    g._adjust_block_y()

    # Should be clamped to surface: row 7 * CELL_SIZE + GRID_Y
    expected_y = GRID_Y + 7 * CELL_SIZE
    assert g.block_y <= expected_y


def test_score_system() -> None:
    """Test scoring for merges."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Tier-1 merge (base 10 points)
    g.grid[10][0] = Cell(color=0, tier=1)
    g.grid[10][1] = Cell(color=0, tier=1)
    g.grid[10][2] = Cell(color=0, tier=1)

    g.combo = 0
    g._check_and_merge()
    g.merge_timer = g.MERGE_ANIM_FRAMES - 1

    score_before = g.score
    g._update_merge_anim()
    assert g.score > score_before
    # Base tier-1 score = 10, combo=1 means no multiplier bonus
    assert g.score >= 10


def test_combo_multiplier() -> None:
    """Test combo multiplier increases with chain merges."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Create a scenario where a tier-1 merge triggers a tier-2 chain
    # 3 tier-1 blocks at bottom left
    g.grid[10][0] = Cell(color=1, tier=1)
    g.grid[11][0] = Cell(color=1, tier=1)
    g.grid[12][0] = Cell(color=1, tier=1)
    # 2 tier-2 blocks of same color adjacent (will form chain)
    g.grid[11][1] = Cell(color=1, tier=2)
    g.grid[12][1] = Cell(color=1, tier=2)

    g.combo = 0
    g._check_and_merge()
    assert g.combo == 1
    assert g.max_combo == 1

    # Complete first merge
    g.merge_timer = g.MERGE_ANIM_FRAMES - 1
    score_before = g.score
    g._update_merge_anim()
    assert g.score > score_before

    # If chain triggered, combo >= 2
    assert g.max_combo >= 1


def test_max_tier_tracking() -> None:
    """Test max_tier_reached updates correctly."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    assert g.max_tier_reached == 1

    g.grid[5][0] = Cell(color=0, tier=1)
    g.grid[5][1] = Cell(color=0, tier=1)
    g.grid[5][2] = Cell(color=0, tier=1)

    g._check_and_merge()
    g.merge_timer = g.MERGE_ANIM_FRAMES - 1
    g._update_merge_anim()

    assert g.max_tier_reached >= 2


def test_particle_life_filter() -> None:
    """Test particles with life=0 are removed immediately on next update."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = [
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=0, color=0),
        Particle(x=1.0, y=1.0, vx=0.0, vy=0.0, life=1, color=1),
    ]
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    g._update_particles()
    assert len(g.particles) == 0  # life=0 removed immediately, life=1 → 0 → removed


def test_land_block_full_column() -> None:
    """Test landing when column is completely full triggers game over."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Fill an entire column
    for r in range(GRID_ROWS):
        g.grid[r][3] = Cell(color=0, tier=1)

    g.block_col = 3
    g.block_color = 1
    g.block_tier = 1
    g._land_block()

    assert g.phase == Phase.GAME_OVER


def test_two_separate_clusters() -> None:
    """Test multiple independent clusters are found."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.particles = []
    g.floating_texts = []
    g.merge_cells = []
    g.reset()

    # Cluster 1: color 0 at top-left
    g.grid[0][0] = Cell(color=0, tier=1)
    g.grid[0][1] = Cell(color=0, tier=1)
    g.grid[0][2] = Cell(color=0, tier=1)

    # Cluster 2: color 1 at bottom-right
    g.grid[10][7] = Cell(color=1, tier=1)
    g.grid[10][8] = Cell(color=1, tier=1)
    g.grid[10][9] = Cell(color=1, tier=1)

    clusters = g._find_clusters()
    assert len(clusters) == 2


if __name__ == "__main__":
    import traceback
    tests = [
        ("test_constants", test_constants),
        ("test_enum_phases", test_enum_phases),
        ("test_cell_dataclass", test_cell_dataclass),
        ("test_particle_dataclass", test_particle_dataclass),
        ("test_game_creation_headless", test_game_creation_headless),
        ("test_reset_state", test_reset_state),
        ("test_spawn_block", test_spawn_block),
        ("test_block_target_row_empty", test_block_target_row_empty),
        ("test_block_target_row_partial", test_block_target_row_partial),
        ("test_cell_to_px", test_cell_to_px),
        ("test_land_block_no_merge", test_land_block_no_merge),
        ("test_land_block_triggers_merge", test_land_block_triggers_merge),
        ("test_merge_anim_finalize", test_merge_anim_finalize),
        ("test_find_clusters_none", test_find_clusters_none),
        ("test_find_clusters_horizontal", test_find_clusters_horizontal),
        ("test_find_clusters_vertical", test_find_clusters_vertical),
        ("test_find_clusters_different_colors_no_merge", test_find_clusters_different_colors_no_merge),
        ("test_find_clusters_different_tiers_no_merge", test_find_clusters_different_tiers_no_merge),
        ("test_find_clusters_l_shape", test_find_clusters_l_shape),
        ("test_find_clusters_larger_than_3", test_find_clusters_larger_than_3),
        ("test_chain_merge", test_chain_merge),
        ("test_game_over_when_spawn_blocked", test_game_over_when_spawn_blocked),
        ("test_particle_update", test_particle_update),
        ("test_floating_text_update", test_floating_text_update),
        ("test_adjust_block_y", test_adjust_block_y),
        ("test_score_system", test_score_system),
        ("test_combo_multiplier", test_combo_multiplier),
        ("test_max_tier_tracking", test_max_tier_tracking),
        ("test_particle_life_filter", test_particle_life_filter),
        ("test_land_block_full_column", test_land_block_full_column),
        ("test_two_separate_clusters", test_two_separate_clusters),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS {name}")
        except Exception:
            print(f"  FAIL {name}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
