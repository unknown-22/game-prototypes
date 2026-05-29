"""test_imports.py — Headless logic tests for 083_cell_forge."""
import sys
import random

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/083_cell_forge")
from main import (
    Game,
    Cell,
    CellColor,
    Particle,
    SynthesisEvent,
    FloatingText,
    Phase,
    GRID_COLS,
    GRID_ROWS,
    SYNTHESIS_THRESHOLD,
    HEAT_LIMIT,
    OVERPOP_THRESHOLD,
    MAX_TIER,
    INITIAL_ENERGY,
    MAX_ENERGY,
    tier_color,
    cell_to_pixel,
    pixel_to_cell,
    _NEIGHBOUR_OFFSETS,
)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _make_game() -> Game:
    """Create a Game bypassing __init__ for headless tests."""
    g = Game.__new__(Game)
    # Pre-init ALL instance attributes before _init_state()
    g.phase = Phase.TITLE
    g.grid = []
    g.score = 0
    g.generation = 0
    g.energy = INITIAL_ENERGY
    g.heat = 0
    g.max_tier = 1
    g.combo = 0
    g.max_combo = 0
    g.synthesis_events = []
    g.particles = []
    g.floating_texts = []
    g.mouse_cx = -1
    g.mouse_cy = -1
    g._evolve_timer = 0
    g._synth_timer = 0
    g._rng = random.Random(42)
    g._game_over_timer = 0
    g._init_state()
    # Re-seed RNG after _init_state() overwrites it
    g._rng = random.Random(42)
    return g


# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------


def test_constants() -> None:
    assert GRID_COLS == 16
    assert GRID_ROWS == 12
    assert SYNTHESIS_THRESHOLD == 3
    assert HEAT_LIMIT == 5
    assert OVERPOP_THRESHOLD == 7
    assert MAX_TIER == 4
    assert INITIAL_ENERGY == 8
    assert MAX_ENERGY == 20
    assert len(_NEIGHBOUR_OFFSETS) == 8
    assert len(list(CellColor)) == 4


def test_tier_color() -> None:
    assert tier_color(CellColor.RED, 1) == 8  # RED
    assert tier_color(CellColor.RED, 2) == 9  # ORANGE
    assert tier_color(CellColor.RED, 3) == 10  # YELLOW
    assert tier_color(CellColor.RED, 4) == 7  # WHITE
    assert tier_color(CellColor.RED, 5) == 7  # WHITE (clamped)
    assert tier_color(CellColor.GREEN, 1) == 3  # GREEN
    assert tier_color(CellColor.BLUE, 1) == 6  # LIGHT_BLUE
    assert tier_color(CellColor.YELLOW, 1) == 10  # YELLOW


def test_cell_to_pixel() -> None:
    x, y = cell_to_pixel(0, 0)
    assert x >= 0
    assert y >= 0
    # Different cells give different positions
    x2, y2 = cell_to_pixel(1, 0)
    assert x2 > x


def test_pixel_to_cell() -> None:
    x, y = cell_to_pixel(5, 3)
    result = pixel_to_cell(x + 7, y + 7)
    assert result is not None
    assert result == (5, 3)
    # Outside grid
    assert pixel_to_cell(-10, -10) is None


# ---------------------------------------------------------------------------
# Grid & init
# ---------------------------------------------------------------------------


def test_init_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.generation == 0
    assert g.energy == INITIAL_ENERGY
    assert g.heat == 0
    assert g.max_tier == 1
    assert g.combo == 0
    assert g.max_combo == 0
    assert len(g.grid) == GRID_ROWS
    assert len(g.grid[0]) == GRID_COLS
    for row in g.grid:
        for cell in row:
            assert cell.alive is False
            assert cell.color is None
            assert cell.tier == 1


def test_reset() -> None:
    g = _make_game()
    g.score = 100
    g.energy = 0
    g.heat = 4
    g.generation = 5
    g.reset()
    assert g.score == 0
    assert g.energy == INITIAL_ENERGY
    assert g.heat == 0
    assert g.generation == 0


def test_in_bounds() -> None:
    g = _make_game()
    assert g._in_bounds(0, 0) is True
    assert g._in_bounds(GRID_COLS - 1, GRID_ROWS - 1) is True
    assert g._in_bounds(-1, 0) is False
    assert g._in_bounds(0, -1) is False
    assert g._in_bounds(GRID_COLS, 0) is False
    assert g._in_bounds(0, GRID_ROWS) is False


# ---------------------------------------------------------------------------
# Seed placement
# ---------------------------------------------------------------------------


def test_place_seed() -> None:
    g = _make_game()
    assert g._place_seed(5, 5, CellColor.RED) is True
    assert g.energy == INITIAL_ENERGY - 1
    cell = g.grid[5][5]
    assert cell.alive is True
    assert cell.color == CellColor.RED
    assert cell.tier == 1


def test_place_seed_no_energy() -> None:
    g = _make_game()
    g.energy = 0
    assert g._place_seed(5, 5, CellColor.RED) is False
    assert g.energy == 0
    assert g.grid[5][5].alive is False


def test_place_seed_on_existing() -> None:
    g = _make_game()
    g._place_seed(5, 5, CellColor.RED)
    assert g._place_seed(5, 5, CellColor.GREEN) is False
    assert g.grid[5][5].color == CellColor.RED


def test_can_place() -> None:
    g = _make_game()
    assert g._can_place() is True
    g.energy = 0
    assert g._can_place() is False


# ---------------------------------------------------------------------------
# Neighbor counting
# ---------------------------------------------------------------------------


def test_count_neighbors_empty() -> None:
    g = _make_game()
    count, color = g._count_neighbors(5, 5)
    assert count == 0
    assert color is None


def test_count_neighbors_with_cells() -> None:
    g = _make_game()
    g._place_seed(4, 5, CellColor.RED)  # left of (5,5)
    g._place_seed(6, 5, CellColor.GREEN)  # right
    g._place_seed(5, 4, CellColor.GREEN)  # above
    count, color = g._count_neighbors(5, 5)
    assert count == 3
    assert color == CellColor.GREEN  # majority


def test_count_neighbors_majority_tie() -> None:
    g = _make_game()
    g._place_seed(4, 5, CellColor.RED)  # left
    g._place_seed(6, 5, CellColor.GREEN)  # right
    g._place_seed(5, 4, CellColor.BLUE)  # above
    count, color = g._count_neighbors(5, 5)
    assert count == 3
    # max() with key returns first at max in case of tie (dict iteration order)
    assert color is not None


def test_count_neighbors_corners() -> None:
    g = _make_game()
    # Top-left corner
    count, color = g._count_neighbors(0, 0)
    assert count == 0
    assert color is None
    # Bottom-right corner
    count, color = g._count_neighbors(GRID_COLS - 1, GRID_ROWS - 1)
    assert count == 0
    assert color is None


# ---------------------------------------------------------------------------
# BFS cluster
# ---------------------------------------------------------------------------


def test_bfs_cluster_single() -> None:
    g = _make_game()
    g._place_seed(5, 5, CellColor.RED)
    cluster = g._bfs_cluster(5, 5, CellColor.RED)
    assert len(cluster) == 1
    assert (5, 5) in cluster


def test_bfs_cluster_connected() -> None:
    g = _make_game()
    # Connected via 4-dir adjacency
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.RED)
    g._place_seed(3, 4, CellColor.RED)
    cluster = g._bfs_cluster(3, 3, CellColor.RED)
    assert len(cluster) == 3
    assert (3, 3) in cluster
    assert (4, 3) in cluster
    assert (3, 4) in cluster


def test_bfs_cluster_separated() -> None:
    g = _make_game()
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(3, 5, CellColor.RED)  # Not 4-adjacent to (3,3)
    cluster = g._bfs_cluster(3, 3, CellColor.RED)
    assert len(cluster) == 1
    assert (3, 3) in cluster
    assert (3, 5) not in cluster


def test_bfs_cluster_different_colors() -> None:
    g = _make_game()
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.GREEN)  # Different color
    g._place_seed(3, 4, CellColor.RED)
    cluster = g._bfs_cluster(3, 3, CellColor.RED)
    assert len(cluster) == 2
    assert (4, 3) not in cluster


def test_bfs_cluster_boundary() -> None:
    g = _make_game()
    g._place_seed(0, 0, CellColor.RED)
    g._place_seed(1, 0, CellColor.RED)
    g._place_seed(0, 1, CellColor.RED)
    cluster = g._bfs_cluster(0, 0, CellColor.RED)
    assert len(cluster) == 3


# ---------------------------------------------------------------------------
# Find synthesis clusters
# ---------------------------------------------------------------------------


def test_find_synthesis_clusters_none() -> None:
    g = _make_game()
    clusters = g._find_synthesis_clusters()
    assert len(clusters) == 0


def test_find_synthesis_clusters_too_small() -> None:
    g = _make_game()
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.RED)
    clusters = g._find_synthesis_clusters()
    assert len(clusters) == 0


def test_find_synthesis_clusters_one() -> None:
    g = _make_game()
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.RED)
    g._place_seed(3, 4, CellColor.RED)
    clusters = g._find_synthesis_clusters()
    assert len(clusters) == 1
    cluster, color = clusters[0]
    assert color == CellColor.RED
    assert len(cluster) == 3


def test_find_synthesis_clusters_multiple() -> None:
    g = _make_game()
    # Cluster 1: RED at top-left
    g._place_seed(1, 1, CellColor.RED)
    g._place_seed(2, 1, CellColor.RED)
    g._place_seed(1, 2, CellColor.RED)
    # Cluster 2: GREEN at bottom-right
    g._place_seed(10, 8, CellColor.GREEN)
    g._place_seed(11, 8, CellColor.GREEN)
    g._place_seed(10, 9, CellColor.GREEN)
    clusters = g._find_synthesis_clusters()
    assert len(clusters) == 2


def test_find_synthesis_clusters_no_duplicate_visit() -> None:
    g = _make_game()
    # All RED in a line — should be one cluster
    for c in range(5):
        g._place_seed(c, 5, CellColor.RED)
    clusters = g._find_synthesis_clusters()
    assert len(clusters) == 1
    assert len(clusters[0][0]) == 5


# ---------------------------------------------------------------------------
# Evolution (Conway step)
# ---------------------------------------------------------------------------


def test_evolve_generation_empty() -> None:
    g = _make_game()
    g._evolve_generation()
    assert g.generation == 1
    # Empty grid stays empty
    for row in g.grid:
        for cell in row:
            assert cell.alive is False


def test_evolve_generation_still_life_block() -> None:
    """A 2x2 block is a still life — survives unchanged."""
    g = _make_game()
    g._place_seed(5, 5, CellColor.RED)
    g._place_seed(6, 5, CellColor.RED)
    g._place_seed(5, 6, CellColor.RED)
    g._place_seed(6, 6, CellColor.RED)
    g._evolve_generation()
    for dr in range(2):
        for dc in range(2):
            cell = g.grid[5 + dr][5 + dc]
            assert cell.alive is True
            assert cell.color == CellColor.RED


def test_evolve_generation_blinker() -> None:
    """A 3-cell horizontal blinker oscillates to vertical."""
    g = _make_game()
    g._place_seed(5, 5, CellColor.RED)
    g._place_seed(6, 5, CellColor.RED)
    g._place_seed(7, 5, CellColor.RED)
    g._evolve_generation()
    # Horizontal at cols 5,6,7 row 5 → vertical at col 6, rows 4,5,6
    # grid[row][col]: grid[4][6], grid[5][6], grid[6][6]
    assert g.grid[4][6].alive is True
    assert g.grid[5][6].alive is True
    assert g.grid[6][6].alive is True
    # Original cells die
    assert g.grid[5][5].alive is False
    assert g.grid[5][6].alive is True  # middle survives
    assert g.grid[5][7].alive is False


def test_evolve_birth_from_3_neighbors() -> None:
    """Dead cell with exactly 3 live neighbors is born."""
    g = _make_game()
    g._place_seed(4, 5, CellColor.GREEN)
    g._place_seed(6, 5, CellColor.GREEN)
    g._place_seed(5, 6, CellColor.GREEN)
    g._evolve_generation()
    # Cell at (5,5) has 3 neighbors → born
    assert g.grid[5][5].alive is True
    assert g.grid[5][5].color == CellColor.GREEN
    assert g.grid[5][5].tier == 1


def test_evolve_dies_underpopulation() -> None:
    """Cell with <2 neighbors dies."""
    g = _make_game()
    g._place_seed(5, 5, CellColor.RED)  # Alone → 0 neighbors → dies
    g._evolve_generation()
    assert g.grid[5][5].alive is False


def test_evolve_dies_overpopulation() -> None:
    """Cell with >3 neighbors dies."""
    g = _make_game()
    # Surround (5,5) with 4 neighbors
    for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
        g._place_seed(5 + dc, 5 + dr, CellColor.RED)
    g._place_seed(5, 5, CellColor.RED)  # Center (4 neighbors)
    g._evolve_generation()
    assert g.grid[5][5].alive is False


# ---------------------------------------------------------------------------
# Synthesis processing
# ---------------------------------------------------------------------------


def test_cluster_center() -> None:
    g = _make_game()
    cluster = {(1, 1), (2, 1), (1, 2)}
    cx, cy = g._cluster_center(cluster)
    assert cx == 1  # (1+2+1)/3 = 4/3 = 1
    assert cy == 1  # (1+1+2)/3 = 4/3 = 1


def test_cluster_center_empty() -> None:
    g = _make_game()
    cx, cy = g._cluster_center(set())
    assert cx == 0
    assert cy == 0


def test_process_synthesis_basic() -> None:
    g = _make_game()
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.RED)
    g._place_seed(3, 4, CellColor.RED)
    cluster = {(3, 3), (4, 3), (3, 4)}
    g._process_synthesis(cluster, CellColor.RED)
    assert g.combo == 1
    assert g.max_combo == 1
    # Center cell should be alive with tier 2
    assert g.grid[3][3].alive is True
    assert g.grid[3][3].color == CellColor.RED
    assert g.grid[3][3].tier == 2
    assert g.max_tier == 2
    # Cluster cells get cleared, then chain_explode re-converts
    # All 8 neighbors of (3,3) become RED t1
    # So grid[3][4] (col=4,row=3) IS alive from chain explode
    assert g.grid[3][4].alive is True  # (4,3) — neighbor, re-converted
    assert g.grid[4][3].alive is True  # (3,4) — neighbor, re-converted
    # Center is tier 2 (not t1)
    assert g.grid[3][3].tier == 2


def test_process_synthesis_max_tier() -> None:
    """Synthesis at tier 4 should not go above MAX_TIER."""
    g = _make_game()
    # Place tier-4 cells, track max_tier
    for c, r in [(3, 3), (4, 3), (3, 4)]:
        g.grid[r][c] = Cell(alive=True, color=CellColor.RED, tier=4)
    g.max_tier = 4  # must set explicitly since we bypassed normal tier-up
    cluster = {(3, 3), (4, 3), (3, 4)}
    g._process_synthesis(cluster, CellColor.RED)
    # At MAX_TIER+1, cell should be cleared not upgraded
    assert g.grid[3][3].alive is False
    assert g.max_tier == 4  # unchanged


def test_process_synthesis_score() -> None:
    g = _make_game()
    g.generation = 3
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.RED)
    g._place_seed(3, 4, CellColor.RED)
    cluster = {(3, 3), (4, 3), (3, 4)}
    old_score = g.score
    g._process_synthesis(cluster, CellColor.RED)
    expected = 2 * 3 * 3  # new_tier=2 * cluster_size=3 * generation=3 = 18
    assert g.score == old_score + expected


def test_process_synthesis_synthesis_events() -> None:
    g = _make_game()
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.RED)
    g._place_seed(3, 4, CellColor.RED)
    cluster = {(3, 3), (4, 3), (3, 4)}
    g._process_synthesis(cluster, CellColor.RED)
    assert len(g.synthesis_events) == 1
    se = g.synthesis_events[0]
    assert se.color == CellColor.RED
    assert se.new_tier == 2
    assert se.cluster_size == 3
    assert se.timer > 0


def test_process_synthesis_floating_text() -> None:
    g = _make_game()
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.RED)
    g._place_seed(3, 4, CellColor.RED)
    cluster = {(3, 3), (4, 3), (3, 4)}
    g._process_synthesis(cluster, CellColor.RED)
    assert len(g.floating_texts) >= 1
    ft = g.floating_texts[0]
    assert "+" in ft.text
    assert ft.life == 30


def test_process_synthesis_particles() -> None:
    g = _make_game()
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.RED)
    g._place_seed(3, 4, CellColor.RED)
    cluster = {(3, 3), (4, 3), (3, 4)}
    g._process_synthesis(cluster, CellColor.RED)
    # At least one particle from synthesis + chain explode
    assert len(g.particles) > 0


# ---------------------------------------------------------------------------
# Chain explode
# ---------------------------------------------------------------------------


def test_chain_explode_converts_neighbors() -> None:
    g = _make_game()
    g._chain_explode(5, 5, CellColor.RED)
    # All 8 neighbors should become alive with RED/tier1
    live_neighbors = 0
    for dc, dr in _NEIGHBOUR_OFFSETS:
        nc, nr = 5 + dc, 5 + dr
        if g._in_bounds(nc, nr):
            cell = g.grid[nr][nc]
            assert cell.alive is True
            assert cell.color == CellColor.RED
            assert cell.tier == 1
            live_neighbors += 1
    assert live_neighbors == 8  # center of grid has all 8 neighbors


def test_chain_explode_at_edge() -> None:
    g = _make_game()
    g._chain_explode(0, 0, CellColor.GREEN)
    # Only 3 neighbors in bounds: (1,0), (0,1), (1,1)
    assert g.grid[0][1].alive is True  # (1,0) written as row 0, col 1
    assert g.grid[1][0].alive is True  # (0,1)
    assert g.grid[1][1].alive is True  # (1,1)
    # Count total alive
    alive_count = sum(1 for row in g.grid for c in row if c.alive)
    assert alive_count == 3


def test_chain_explode_overwrites_existing() -> None:
    g = _make_game()
    # Place existing cell at a neighbor position
    g._place_seed(4, 5, CellColor.GREEN)  # (4,5) is left of (5,5)
    g._chain_explode(5, 5, CellColor.RED)
    # Should be overwritten to RED
    cell = g.grid[5][4]
    assert cell.alive is True
    assert cell.color == CellColor.RED
    assert cell.tier == 1


# ---------------------------------------------------------------------------
# Overpopulation & heat
# ---------------------------------------------------------------------------


def test_check_overpopulation_empty() -> None:
    g = _make_game()
    heat = g._check_overpopulation()
    assert heat == 0
    assert g.heat == 0


def test_check_overpopulation_partial() -> None:
    """Place cells that don't reach overpopulation threshold."""
    g = _make_game()
    # 2x2 block → 4 cells per 3x3 window → below threshold of 7
    g._place_seed(5, 5, CellColor.RED)
    g._place_seed(6, 5, CellColor.RED)
    g._place_seed(5, 6, CellColor.RED)
    g._place_seed(6, 6, CellColor.RED)
    heat = g._check_overpopulation()
    assert heat == 0


def test_check_overpopulation_full_3x3() -> None:
    """Fill a 3x3 with 9 cells → overpopulation detected."""
    g = _make_game()
    for r in range(5, 8):  # rows 5,6,7
        for c in range(5, 8):  # cols 5,6,7
            g.grid[r][c] = Cell(alive=True, color=CellColor.RED, tier=1)
    heat = g._check_overpopulation()
    assert heat >= 1  # At least the 5-7 window triggers it


def test_check_overpopulation_heat_accumulates() -> None:
    g = _make_game()
    g.heat = 2
    # Fill a 3x3
    for r in range(5, 8):
        for c in range(5, 8):
            g.grid[r][c] = Cell(alive=True, color=CellColor.RED, tier=1)
    g._check_overpopulation()
    assert g.heat >= 3  # 2 + at least 1


def test_heat_reset_triggers_at_limit() -> None:
    """When heat reaches HEAT_LIMIT, _check_overpopulation triggers reset."""
    g = _make_game()
    g.heat = HEAT_LIMIT - 1  # 4
    # Place enough live cells to trigger at least 1 heat
    for r in range(5, 8):
        for c in range(5, 8):
            g.grid[r][c] = Cell(alive=True, color=CellColor.RED, tier=1)
    g._check_overpopulation()
    # After reset: heat = 0, energy += 3
    assert g.heat == 0
    assert g.energy == INITIAL_ENERGY + 3  # 8 + 3 = 11


def test_trigger_heat_reset_clears_grid() -> None:
    g = _make_game()
    for c in range(5):
        g._place_seed(c, 5, CellColor.RED)
    assert g.grid[5][0].alive is True
    g._trigger_heat_reset()
    for row in g.grid:
        for cell in row:
            assert cell.alive is False


def test_trigger_heat_reset_adds_energy() -> None:
    g = _make_game()
    g.energy = 3
    g._trigger_heat_reset()
    assert g.energy == 6  # 3 + 3


def test_trigger_heat_reset_energy_cap() -> None:
    g = _make_game()
    g.energy = MAX_ENERGY - 1  # 19
    g._trigger_heat_reset()
    assert g.energy == MAX_ENERGY  # capped at 20


def test_trigger_heat_reset_floating_text() -> None:
    g = _make_game()
    g._trigger_heat_reset()
    assert len(g.floating_texts) >= 1
    ft = g.floating_texts[0]
    assert "OVERLOAD" in ft.text.upper() or "ENERGY" in ft.text.upper()


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


def test_calculate_score_for_synthesis() -> None:
    g = _make_game()
    g.generation = 2
    score = g._calculate_score_for_synthesis(2, 3)
    assert score == 2 * 3 * 2  # tier * cluster_size * generation = 12


def test_calculate_score_for_synthesis_generation_0() -> None:
    g = _make_game()
    g.generation = 0
    score = g._calculate_score_for_synthesis(2, 3)
    assert score == 2 * 3 * 1  # max(generation, 1) = 1 → 6


def test_calculate_score() -> None:
    g = _make_game()
    g.score = 42
    assert g._calculate_score() == 42


# ---------------------------------------------------------------------------
# Game over detection
# ---------------------------------------------------------------------------


def test_is_game_over_with_energy() -> None:
    g = _make_game()
    assert g._is_game_over() is False


def test_is_game_over_no_energy_no_cells() -> None:
    g = _make_game()
    g.energy = 0
    assert g._is_game_over() is True


def test_is_game_over_no_energy_still_life() -> None:
    """Still life continues to survive, so not game over."""
    g = _make_game()
    # Place seeds FIRST, then zero energy
    g._place_seed(5, 5, CellColor.RED)
    g._place_seed(6, 5, CellColor.RED)
    g._place_seed(5, 6, CellColor.RED)
    g._place_seed(6, 6, CellColor.RED)
    g.energy = 0
    assert g._is_game_over() is False


def test_is_game_over_no_energy_all_dying() -> None:
    """Single cell will die from underpopulation, game over."""
    g = _make_game()
    g.energy = 0
    g._place_seed(5, 5, CellColor.RED)
    assert g._is_game_over() is True


def test_is_game_over_no_energy_synthesis_possible() -> None:
    """If synthesis clusters exist, not game over."""
    g = _make_game()
    # Place seeds FIRST, then zero energy
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.RED)
    g._place_seed(3, 4, CellColor.RED)
    g.energy = 0
    assert g._is_game_over() is False


# ---------------------------------------------------------------------------
# Phase transitions (testable inner logic)
# ---------------------------------------------------------------------------


def test_advance_phase_title_to_seed() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    g._advance_phase()
    assert g.phase == Phase.SEED


def test_advance_phase_seed_to_evolving() -> None:
    g = _make_game()
    g.phase = Phase.SEED
    g._advance_phase()
    assert g.phase == Phase.EVOLVING
    assert g._evolve_timer > 0


def test_advance_phase_evolving_no_synthesis() -> None:
    """After evolution with no synthesis, go back to SEED."""
    g = _make_game()
    g.phase = Phase.EVOLVING
    g._evolve_timer = 1
    # No cells → no synthesis clusters
    g._advance_phase()
    # _advance_phase doesn't call _evolve_generation directly,
    # it just transitions — evolution happens in update_evolving
    assert g.phase == Phase.SEED


def test_advance_phase_evolving_with_synthesis() -> None:
    """After evolution with synthesis clusters, go to SYNTHESIS."""
    g = _make_game()
    g.phase = Phase.EVOLVING
    g._evolve_timer = 1
    # Place a synthesis cluster
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.RED)
    g._place_seed(3, 4, CellColor.RED)
    g.phase = Phase.EVOLVING
    g._advance_phase()
    assert g.phase == Phase.SYNTHESIS
    assert g._synth_timer > 0


def test_advance_phase_evolving_game_over() -> None:
    """Empty grid + no energy + no synthesis = game over."""
    g = _make_game()
    g.energy = 0
    g.phase = Phase.EVOLVING
    g._advance_phase()
    assert g.phase == Phase.GAME_OVER


def test_advance_phase_cascade_synthesis() -> None:
    """SYNTHESIS phase cascades if new clusters form."""
    g = _make_game()
    g.phase = Phase.SYNTHESIS
    g._synth_timer = 1
    g._advance_phase()
    # No cells, no cascade → should go to SEED or GAME_OVER
    assert g.phase in (Phase.SEED, Phase.GAME_OVER)


# ---------------------------------------------------------------------------
# Particle & floating text updates
# ---------------------------------------------------------------------------


def test_spawn_synthesis_particles() -> None:
    g = _make_game()
    g._spawn_synthesis_particles(100.0, 100.0, CellColor.RED, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 100.0
        assert p.life > 0


def test_update_particles() -> None:
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=1.0, vy=0.0, life=5, color=8, size=3.0),
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=8, size=1.0),
    ]
    g._update_particles()
    # Particle 0: moves, life=4, size reduced
    assert abs(g.particles[0].x - 1.0) < 0.01
    assert abs(g.particles[0].y - 0.0) < 0.01
    assert g.particles[0].life == 4
    assert g.particles[0].size < 3.0
    # Particle 1: life was 1 → 0, removed
    assert len(g.particles) == 1


def test_update_floating_texts() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100.0, y=100.0, text="test", life=5, color=7),
        FloatingText(x=0.0, y=0.0, text="dead", life=1, color=7),
    ]
    g._update_floating_texts()
    # First text rises and life decreases
    assert g.floating_texts[0].life == 4
    assert abs(g.floating_texts[0].y - 99.4) < 0.01
    # Second text removed (life was 1 → 0)
    assert len(g.floating_texts) == 1


def test_update_synthesis_events() -> None:
    g = _make_game()
    g.synthesis_events = [
        SynthesisEvent(cx=5, cy=5, color=CellColor.RED, new_tier=2, cluster_size=3, timer=10),
        SynthesisEvent(cx=10, cy=10, color=CellColor.GREEN, new_tier=3, cluster_size=4, timer=1),
    ]
    g._update_synthesis_events()
    assert g.synthesis_events[0].timer == 9
    assert len(g.synthesis_events) == 1  # Second removed (timer was 1 → 0)


# ---------------------------------------------------------------------------
# Full game loop simulation
# ---------------------------------------------------------------------------


def test_full_loop_place_evolve_synthesize() -> None:
    """Simulate placing seeds, evolving, and synthesizing."""
    g = _make_game()
    g.phase = Phase.SEED

    # Place a blinker pattern + synthesis cluster
    g._place_seed(5, 5, CellColor.RED)
    g._place_seed(6, 5, CellColor.RED)
    g._place_seed(7, 5, CellColor.RED)
    g._place_seed(3, 3, CellColor.RED)
    g._place_seed(4, 3, CellColor.RED)
    g._place_seed(3, 4, CellColor.RED)
    assert g.energy == INITIAL_ENERGY - 6

    # Manually trigger phase transitions like the game loop
    g.phase = Phase.EVOLVING
    g._evolve_timer = 1
    # Simulate evolution completion: evolve → advance phase
    g._evolve_generation()
    g._advance_phase()

    # Should be in SYNTHESIS (the 3-cell cluster triggered synthesis)
    assert g.phase == Phase.SYNTHESIS

    # Process synthesis again via advance
    g._synth_timer = 1
    g._advance_phase()

    # Score should have increased
    assert g.score > 0
    assert g.max_tier >= 2


def test_full_loop_heat_reset() -> None:
    """Simulate a full loop where overpopulation triggers heat reset."""
    g = _make_game()
    g.phase = Phase.SEED

    # Fill a 3x3 area with cells (bypass energy for setup)
    for r in range(5, 8):
        for c in range(5, 8):
            g.grid[r][c] = Cell(alive=True, color=CellColor.RED, tier=1)

    g.heat = HEAT_LIMIT - 1  # 4

    # Directly check overpopulation — it triggers heat reset
    heat_gained = g._check_overpopulation()
    assert heat_gained >= 1
    # Heat limit reached → reset triggered
    assert g.heat == 0
    assert g.energy == INITIAL_ENERGY + 3  # gained +3 from overkill


def test_full_loop_game_over() -> None:
    """Simulate game reaching game over."""
    g = _make_game()
    g.energy = 0
    g.phase = Phase.EVOLVING

    # Empty grid + no energy → should go to game over
    g._advance_phase()
    assert g.phase == Phase.GAME_OVER


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_place_seed_all_colors() -> None:
    g = _make_game()
    colors = list(CellColor)
    for i, color in enumerate(colors):
        assert g._place_seed(i, 0, color) is True
        assert g.grid[0][i].color == color


def test_bfs_cluster_large_L_shape() -> None:
    """L-shape connected via 4-dir should be one cluster."""
    g = _make_game()
    positions = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]
    for c, r in positions:
        g._place_seed(c, r, CellColor.RED)
    cluster = g._bfs_cluster(0, 0, CellColor.RED)
    assert len(cluster) == 5


def test_bfs_cluster_8dir_not_connected() -> None:
    """Diagonal cells are NOT connected."""
    g = _make_game()
    g._place_seed(0, 0, CellColor.RED)
    g._place_seed(1, 1, CellColor.RED)  # diagonal, not 4-adjacent
    cluster = g._bfs_cluster(0, 0, CellColor.RED)
    assert len(cluster) == 1


def test_evolve_changes_generation() -> None:
    g = _make_game()
    assert g.generation == 0
    g._evolve_generation()
    assert g.generation == 1
    g._evolve_generation()
    assert g.generation == 2


def test_update_particles_empty() -> None:
    g = _make_game()
    g._update_particles()
    assert len(g.particles) == 0


def test_update_floating_texts_empty() -> None:
    g = _make_game()
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_update_synthesis_events_empty() -> None:
    g = _make_game()
    g._update_synthesis_events()
    assert len(g.synthesis_events) == 0


def test_no_energy_prevents_placement() -> None:
    g = _make_game()
    # Use all energy
    for i in range(INITIAL_ENERGY):
        g._place_seed(i, 0, CellColor.RED)
    assert g.energy == 0
    assert g._place_seed(0, 1, CellColor.RED) is False


def test_cell_dataclass_defaults() -> None:
    c = Cell()
    assert c.alive is False
    assert c.color is None
    assert c.tier == 1


def test_particle_dataclass() -> None:
    p = Particle(x=1.0, y=2.0, vx=0.5, vy=-0.5, life=10, color=8, size=3.0)
    assert p.x == 1.0
    assert p.life == 10


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=50.0, y=60.0, text="+10", life=30, color=7)
    assert ft.text == "+10"
    assert ft.life == 30
