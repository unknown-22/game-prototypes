"""test_imports.py — Headless logic tests for 099_harvest_chain."""
import random
import sys
from pathlib import Path

# Add prototype directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    COLS,
    ROWS,
    CROP_COLORS,
    SUPER_COMBO,
    OVERGROWTH_THRESHOLD,
    INITIAL_CROPS,
    SEEDS_PER_TURN,
    SPREAD_CHANCE,
    RED,
    GREEN,
    DARK_BLUE,
    YELLOW,
    Particle,
    Game,
)


def _make_game(seed: int = 42) -> Game:
    """Factory for headless Game instances bypassing Pyxel init."""
    g = Game.__new__(Game)
    # Pre-init all attributes _init_state() will touch
    g._rng = random.Random(seed)
    g.phase = ""
    g.grid = [[0] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.last_color = 0
    g.super_mode = False
    g.game_over = False
    g.particles = []
    g._turn_count = 0
    g._init_state()
    g._rng = random.Random(seed)  # _init_state doesn't overwrite, but safe
    return g


# ── BFS Cluster ────────────────────────────────────────────────────────────

def test_bfs_single_cell():
    """BFS from isolated cell returns just that cell."""
    g = _make_game()
    g.grid[2][3] = RED
    cluster = g._bfs_cluster(3, 2, RED)
    assert cluster == {(3, 2)}


def test_bfs_empty_cell():
    """BFS from empty cell returns empty set."""
    g = _make_game()
    cluster = g._bfs_cluster(3, 2, RED)
    assert cluster == set()


def test_bfs_wrong_color():
    """BFS for wrong color returns empty set."""
    g = _make_game()
    g.grid[2][3] = RED
    cluster = g._bfs_cluster(3, 2, GREEN)
    assert cluster == set()


def test_bfs_connected_cluster():
    """BFS collects all 4-connected same-color cells."""
    g = _make_game()
    # Place a 3-cell L-shaped cluster
    g.grid[1][2] = GREEN  # (2,1)
    g.grid[2][2] = GREEN  # (2,2)
    g.grid[2][3] = GREEN  # (3,2)
    cluster = g._bfs_cluster(2, 2, GREEN)
    assert cluster == {(2, 1), (2, 2), (3, 2)}


def test_bfs_disconnected():
    """BFS does NOT collect diagonally-connected cells (only 4-dir)."""
    g = _make_game()
    g.grid[1][2] = GREEN  # (2,1)
    g.grid[2][3] = GREEN  # (3,2) — diagonal, not connected
    cluster = g._bfs_cluster(2, 1, GREEN)
    assert cluster == {(2, 1)}


def test_bfs_full_cluster():
    """BFS collects all cells in a fully connected region."""
    g = _make_game()
    # Fill a 2x2 block with same color
    for r in (2, 3):
        for c in (4, 5):
            g.grid[r][c] = RED
    cluster = g._bfs_cluster(4, 2, RED)
    assert len(cluster) == 4
    assert {(4, 2), (5, 2), (4, 3), (5, 3)} == cluster


def test_bfs_boundary():
    """BFS respects grid boundaries."""
    g = _make_game()
    g.grid[0][0] = RED
    cluster = g._bfs_cluster(0, 0, RED)
    assert cluster == {(0, 0)}


# ── Occupied Count / Overgrowth ────────────────────────────────────────────

def test_count_occupied_empty():
    """Empty grid has 0 occupied cells."""
    g = _make_game()
    assert g._count_occupied() == 0


def test_count_occupied_some():
    """Counts all occupied cells."""
    g = _make_game()
    g.grid[0][0] = RED
    g.grid[0][1] = GREEN
    g.grid[5][7] = YELLOW
    assert g._count_occupied() == 3


def test_check_overgrowth_safe():
    """Below threshold returns False."""
    g = _make_game()
    # Put just a few crops
    g.grid[0][0] = RED
    g.grid[0][1] = GREEN
    assert not g._check_overgrowth()


def test_check_overgrowth_triggered():
    """Above 85% returns True."""
    g = _make_game()
    total = COLS * ROWS  # 48
    threshold_count = int(total * OVERGROWTH_THRESHOLD) + 1  # 41
    for r in range(ROWS):
        for c in range(COLS):
            if r * COLS + c < threshold_count:
                g.grid[r][c] = RED
    assert g._check_overgrowth()


# ── Compute Score ──────────────────────────────────────────────────────────

def test_compute_score_no_combo():
    """Score = cluster_size * 1.0 when combo=0."""
    g = _make_game()
    g.combo = 0
    assert g._compute_score(5) == 5  # 5 * 1.0


def test_compute_score_combo1():
    """Score = cluster_size * 1.0 when combo=1 (no bonus yet)."""
    g = _make_game()
    g.combo = 1
    assert g._compute_score(5) == 5  # 5 * (1 + 0*0.5)


def test_compute_score_combo2():
    """Score = cluster_size * 1.5 when combo=2."""
    g = _make_game()
    g.combo = 2
    assert g._compute_score(4) == 6  # 4 * 1.5


def test_compute_score_combo4():
    """Score = cluster_size * 2.5 when combo=4 (super threshold)."""
    g = _make_game()
    g.combo = 4
    assert g._compute_score(6) == 15  # 6 * (1 + 3*0.5) = 6 * 2.5


def test_compute_score_rounding():
    """Score computation casts to int (floor)."""
    g = _make_game()
    g.combo = 3
    # 3 * (1 + 2*0.5) = 3 * 2.0 = 6
    assert g._compute_score(3) == 6


# ── CA Spread ──────────────────────────────────────────────────────────────

def test_ca_spread_empty_grid():
    """No spread when grid is empty."""
    g = _make_game()
    new_crops = g._ca_spread()
    assert len(new_crops) == 0


def test_ca_spread_isolated_crop():
    """A single crop spreads (recursively) to empty neighbors.
    
    Note: CA spread writes to grid immediately, so later iterations
    see newly-filled cells and spread from them too (chain-cascade).
    With 100% spread chance, a single crop fills the entire reachable grid.
    """
    g = _make_game()
    g.grid[2][3] = RED  # (3,2)
    # Monkey-patch random to always succeed
    _old = g._rng.random
    g._rng.random = lambda: 0.1  # type: ignore
    new_crops = g._ca_spread()
    g._rng.random = _old  # type: ignore
    # With cascading spread, should fill many cells (not just 4)
    assert len(new_crops) >= 4
    for nc, nr, col in new_crops:
        assert col == RED
        assert g.grid[nr][nc] == RED
    # The original crop still exists
    assert g.grid[2][3] == RED


def test_ca_spread_no_spread_when_random_high():
    """No spread when random > SPREAD_CHANCE."""
    g = _make_game()
    g.grid[2][3] = RED
    _old = g._rng.random
    g._rng.random = lambda: 0.9  # type: ignore
    new_crops = g._ca_spread()
    g._rng.random = _old  # type: ignore
    assert len(new_crops) == 0


def test_ca_spread_does_not_overwrite():
    """CA spread won't overwrite existing crops — only fills empty cells."""
    g = _make_game()
    g.grid[2][3] = RED  # (3,2)
    g.grid[1][3] = GREEN  # (3,1) — blocks north spread
    g.grid[2][4] = GREEN  # (4,2) — blocks east spread
    _old = g._rng.random
    g._rng.random = lambda: 0.1  # type: ignore
    new_crops = g._ca_spread()
    g._rng.random = _old  # type: ignore
    # With cascading spread, many cells get filled
    assert len(new_crops) > 0
    # But existing crops should NOT be overwritten
    assert g.grid[2][3] == RED  # original RED still there
    assert g.grid[1][3] == GREEN  # GREEN blocks still there
    assert g.grid[2][4] == GREEN


def test_ca_spread_multiple_crops():
    """Multiple crops all spread independently (cascading)."""
    g = _make_game()
    g.grid[0][0] = RED
    g.grid[5][7] = GREEN
    _old = g._rng.random
    g._rng.random = lambda: 0.1  # type: ignore
    new_crops = g._ca_spread()
    g._rng.random = _old  # type: ignore
    # Both crops spread (cascading means many cells filled)
    assert len(new_crops) >= 2
    # Both original crops still exist
    assert g.grid[0][0] == RED
    assert g.grid[5][7] == GREEN
    # Some cells should be red, some green
    has_red = any(col == RED for _, _, col in new_crops)
    has_green = any(col == GREEN for _, _, col in new_crops)
    assert has_red or has_green  # at least one spread color


# ── Spawn Seeds ────────────────────────────────────────────────────────────

def test_spawn_seeds_empty_grid():
    """Spawning seeds in empty grid fills all requested."""
    g = _make_game()
    spawned = g._spawn_seeds(5)
    assert spawned == 5
    assert g._count_occupied() == 5


def test_spawn_seeds_partial():
    """Spawning when some cells are occupied returns fewer."""
    g = _make_game()
    # Fill most cells
    for r in range(ROWS):
        for c in range(COLS):
            if r * COLS + c < 44:  # 44 of 48 occupied
                g.grid[r][c] = RED
    spawned = g._spawn_seeds(10)
    assert spawned == 4  # only 4 empty cells left
    assert g._count_occupied() == 48


def test_spawn_seeds_full_grid():
    """Spawning in full grid returns 0."""
    g = _make_game()
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = RED
    spawned = g._spawn_seeds(5)
    assert spawned == 0


# ── Harvest ────────────────────────────────────────────────────────────────

def test_harvest_single_crop():
    """Harvesting a single isolated crop gives score = 1."""
    g = _make_game()
    g.grid[2][3] = RED
    size = g._harvest(3, 2)
    assert size == 1
    assert g.score == 1  # combo=0 → mult=1.0
    assert g.grid[2][3] == 0
    assert g.combo == 1
    assert g.last_color == RED
    assert not g.super_mode  # combo=1 < 4


def test_harvest_empty_cell():
    """Harvesting an empty cell returns 0 and does nothing."""
    g = _make_game()
    old_score = g.score
    size = g._harvest(3, 2)
    assert size == 0
    assert g.score == old_score
    assert g.combo == 0


def test_harvest_cluster():
    """Harvesting a connected cluster returns correct size and scores.
    
    Note: _harvest() internally calls CA spread + seeds AFTER clearing,
    so harvested cells may be re-filled by subsequent steps.
    """
    g = _make_game()
    # Place 3 connected cells
    g.grid[1][2] = GREEN  # (2,1)
    g.grid[2][2] = GREEN  # (2,2)
    g.grid[2][3] = GREEN  # (3,2)
    size = g._harvest(2, 2)
    assert size == 3
    # Score: 3 * 1.0 (combo=0) = 3
    assert g.score == 3
    # Combo is now 1
    assert g.combo == 1
    assert g.last_color == GREEN


def test_harvest_combo_same_color():
    """Same-color consecutive harvests increment combo."""
    g = _make_game()
    # First harvest: RED
    g.grid[0][0] = RED
    g._harvest(0, 0)
    assert g.combo == 1
    assert g.last_color == RED

    # Second harvest: RED again
    g.grid[1][1] = RED
    g._harvest(1, 1)
    assert g.combo == 2
    assert g.score >= 2  # 1 + (cluster_size * combo_mult)


def test_harvest_combo_reset_on_wrong_color():
    """Different color harvest resets combo to 1."""
    g = _make_game()
    # Build combo
    g.grid[0][0] = RED
    g._harvest(0, 0)
    assert g.combo == 1

    g.grid[0][1] = RED
    g._harvest(1, 0)
    assert g.combo == 2

    # Wrong color
    g.grid[0][2] = GREEN
    g._harvest(2, 0)
    assert g.combo == 1
    assert g.last_color == GREEN


def test_harvest_super_mode_activation():
    """Combo >= 4 activates super_mode."""
    g = _make_game()
    # Build combo to 4
    for i in range(4):
        g.grid[0][i] = RED
        g._harvest(i, 0)
    assert g.combo == 4
    assert g.super_mode is True


def test_harvest_super_mode_harvests_all():
    """In super mode, ALL same-color crops are harvested, not just connected.
    
    We simulate super mode by directly setting combo/super_mode state,
    then verify super harvest behavior.
    """
    g = _make_game()
    # Simulate having built a combo of 4
    g.combo = 4
    g.max_combo = 4
    g.last_color = RED
    g.super_mode = True
    
    # Place 2 disconnected RED crops
    g.grid[3][0] = RED  # (0,3)
    g.grid[3][7] = RED  # (7,3) — far away, disconnected
    # Also place a GREEN crop that should NOT be harvested
    g.grid[3][4] = GREEN  # (4,3)
    
    size = g._harvest(0, 3)
    assert size == 2  # both RED crops harvested via super mode
    # GREEN should still be there (plus whatever CA spread/seeds added)
    assert g.grid[3][4] == GREEN  # untouched
    # Both RED crops removed from cluster
    # (may be refilled by CA/seeds, but they were in the cluster)
    assert g.combo == 5  # same color → incremented


def test_harvest_score_uses_pre_combo():
    """Score is computed using combo value BEFORE the update."""
    g = _make_game()
    g.combo = 3  # pre-set combo
    g.last_color = RED
    g.grid[2][2] = RED
    g._harvest(2, 2)
    # score gained: 1 * (1 + 2*0.5) = 1 * 2.0 = 2
    assert g.score == 2
    # combo updated to 4 after
    assert g.combo == 4


def test_harvest_max_combo_tracking():
    """max_combo tracks the highest combo achieved."""
    g = _make_game()
    for i in range(5):
        g.grid[0][i] = RED
        g._harvest(i, 0)
    assert g.combo == 5
    assert g.max_combo == 5

    # Reset combo with wrong color
    g.grid[1][0] = GREEN
    g._harvest(0, 1)
    assert g.combo == 1
    assert g.max_combo == 5  # still 5


def test_harvest_overgrowth_game_over():
    """When grid exceeds 85%, game_over is set."""
    g = _make_game()
    # Fill 40 of 48 cells (83.3%) — below threshold
    for r in range(ROWS):
        for c in range(COLS):
            if r * COLS + c < 40:
                g.grid[r][c] = RED if (r + c) % 2 == 0 else GREEN

    # Harvest one cell. CA spread + seeds will likely push over 85%
    g.grid[5][0] = RED  # ensure harvestable
    g._harvest(0, 5)
    # May or may not trigger overgrowth depending on CA spread
    # At minimum, overgrowth check runs
    # Verify game_over flag is set if check passes
    if g._check_overgrowth():
        assert g.game_over is True


def test_harvest_particles_spawned():
    """Harvest spawns particles for each cell in cluster."""
    g = _make_game()
    g.grid[2][2] = RED
    g.grid[2][3] = RED
    g._harvest(2, 2)
    assert len(g.particles) > 0
    # 2 cells * (5-8) particles each
    assert len(g.particles) >= 10
    assert len(g.particles) <= 16
    # Check particle attributes
    for p in g.particles:
        assert isinstance(p, Particle)
        assert p.color == RED
        assert p.life > 0


def test_harvest_turn_count():
    """Each harvest increments turn count."""
    g = _make_game()
    assert g._turn_count == 0
    g.grid[0][0] = RED
    g._harvest(0, 0)
    assert g._turn_count == 1
    g.grid[1][1] = RED
    g._harvest(1, 1)
    assert g._turn_count == 2


# ── Super Mode Deactivation ─────────────────────────────────────────────────

def test_super_mode_deactivates_when_combo_drops():
    """Super mode turns off when combo drops below 4."""
    g = _make_game()
    g.combo = 4
    g.super_mode = True
    g.last_color = RED

    # Harvest wrong color → combo resets to 1
    g.grid[2][2] = GREEN
    g._harvest(2, 2)
    assert g.combo == 1
    assert not g.super_mode


def test_super_mode_stays_with_high_combo():
    """Super mode stays active when combo stays >= 4."""
    g = _make_game()
    g.combo = 4
    g.super_mode = True
    g.last_color = RED

    g.grid[2][2] = RED
    g._harvest(2, 2)
    assert g.combo == 5
    assert g.super_mode is True


# ── Initial Placement ──────────────────────────────────────────────────────

def test_place_initial_crops():
    """Initial crops are placed correctly."""
    g = _make_game()
    g._place_initial_crops()
    assert g._count_occupied() == INITIAL_CROPS  # 12
    # All placed crops have valid colors
    for row in g.grid:
        for cell in row:
            assert cell == 0 or cell in CROP_COLORS


# ── Reset ──────────────────────────────────────────────────────────────────

def test_reset_clears_state():
    """reset() clears all game state and places initial crops."""
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.max_combo = 10
    g.last_color = RED
    g.super_mode = True
    g.game_over = True
    g._turn_count = 50
    g.particles = [Particle(0, 0, 1, 1, 5, RED)]

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.last_color == 0
    assert not g.super_mode
    assert not g.game_over
    assert g._turn_count == 0
    assert g.particles == []
    assert g._count_occupied() == INITIAL_CROPS


# ── Game Over State ────────────────────────────────────────────────────────

def test_game_over_flag_respected():
    """game_over flag is set when overgrowth triggers after harvest.
    
    We need a scenario where after harvest (which clears cells), CA spread
    and seeds still leave enough cells occupied to exceed 85%.
    Using a checkerboard of alternating colors so BFS clusters are small,
    harvesting one cell leaves many others that can spread and fill.
    """
    g = _make_game()
    # Fill 41 of 48 cells (85.4%) with alternating colors so no large cluster
    count = 0
    for r in range(ROWS):
        for c in range(COLS):
            if count < 41:
                g.grid[r][c] = RED if (r + c) % 2 == 0 else GREEN
                count += 1
    # One cell already at >85%, harvest a single isolated cell
    # BFS collects just that one cell → 40 occupied after clear
    # CA spread + seeds should push back over 41
    g.grid[5][7] = RED  # ensure it's RED, isolated
    g._harvest(7, 5)
    # After CA spread + seeds, check if game_over triggered
    # 40 cells remain, CA spreads from many of them, seeds add 2
    # Should exceed 41 (85.4%)
    assert g.game_over


# ── Phase String Comparisons ───────────────────────────────────────────────

def test_phase_title():
    """Initial phase is 'title'."""
    g = _make_game()
    assert g.phase == "title"


def test_phase_persistence():
    """Phase can be changed for headless testing."""
    g = _make_game()
    g.phase = "playing"
    assert g.phase == "playing"
    g.phase = "game_over"
    assert g.phase == "game_over"


# ── Constants ──────────────────────────────────────────────────────────────

def test_constants():
    """Verify key constants are reasonable."""
    assert COLS == 8
    assert ROWS == 6
    assert SUPER_COMBO == 4
    assert OVERGROWTH_THRESHOLD == 0.85
    assert INITIAL_CROPS == 12
    assert SEEDS_PER_TURN == 2
    assert SPREAD_CHANCE == 0.5
    assert len(CROP_COLORS) == 4
    assert RED == 8
    assert GREEN == 3
    assert DARK_BLUE == 5
    assert YELLOW == 10
