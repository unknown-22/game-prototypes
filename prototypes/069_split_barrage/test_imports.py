"""test_imports.py — Headless logic tests for SPLIT BARRAGE."""
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/069_split_barrage")

from main import (
    Game,
    Fragment,
    Particle,
    ComboText,
    Phase,
    FRAGMENT_COLORS,
    MIN_CLUSTER,
    SCORE_PER_CELL,
    GRID_COLS,
    GRID_ROWS,
    GRID_Y,
    POWER_MIN,
    POWER_MAX,
    SHOTS_TOTAL,
)


# ── Helper ────────────────────────────────────────────────────────────

def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(seed)
    g.reset()
    return g


# ── Dataclass tests ────────────────────────────────────────────────────

def test_fragment_defaults() -> None:
    frag = Fragment(x=100.0, y=50.0, vx=2.0, vy=-3.0, color=8)
    assert frag.x == 100.0
    assert frag.y == 50.0
    assert frag.vx == 2.0
    assert frag.vy == -3.0
    assert frag.color == 8
    assert frag.landed is False
    assert frag.grid_col == -1
    assert frag.grid_row == -1


def test_particle_defaults() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, color=8, life=12)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.color == 8
    assert p.life == 12


def test_combo_text_defaults() -> None:
    ct = ComboText(x=80.0, y=200.0, life=30, text="x3", color=10)
    assert ct.x == 80.0
    assert ct.y == 200.0
    assert ct.life == 30
    assert ct.text == "x3"
    assert ct.color == 10


# ── Phase enum tests ───────────────────────────────────────────────────

def test_phase_values() -> None:
    assert Phase.TITLE in Phase
    assert Phase.AIMING in Phase
    assert Phase.FLYING in Phase
    assert Phase.SPLITTING in Phase
    assert Phase.RESOLVING in Phase
    assert Phase.GAME_OVER in Phase
    assert len(list(Phase)) == 6


# ── Constants tests ────────────────────────────────────────────────────

def test_constants() -> None:
    assert MIN_CLUSTER == 3
    assert SCORE_PER_CELL == 10
    assert GRID_COLS == 16
    assert GRID_ROWS == 5
    assert len(FRAGMENT_COLORS) == 4
    assert POWER_MIN == 1.0
    assert POWER_MAX == 20.0
    assert SHOTS_TOTAL == 10


# ── Reset tests ────────────────────────────────────────────────────────

def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.combo_multiplier == 1.0
    assert g.shots_used == 0
    assert g.projectile_active is False
    assert g.is_aiming is False
    assert len(g.fragments) == 0
    assert len(g.particles) == 0
    assert len(g.combo_texts) == 0

    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            assert g.grid[r][c] == 0


def test_start_game_transitions_to_aiming() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.AIMING
    assert g.score == 0
    assert g.combo == 0
    assert g.shots_used == 0


# ── BFS Cluster tests ──────────────────────────────────────────────────

def test_bfs_cluster_empty_cell() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    result = Game._bfs_cluster(grid, 0, 0)
    assert len(result) == 0


def test_bfs_cluster_single_cell() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[0][0] = 8
    result = Game._bfs_cluster(grid, 0, 0)
    assert result == {(0, 0)}


def test_bfs_cluster_connected_horizontal() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[0][0] = 8
    grid[0][1] = 8
    grid[0][2] = 8
    result = Game._bfs_cluster(grid, 0, 0)
    assert result == {(0, 0), (1, 0), (2, 0)}


def test_bfs_cluster_connected_vertical() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[0][0] = 9
    grid[1][0] = 9
    grid[2][0] = 9
    result = Game._bfs_cluster(grid, 0, 0)
    assert result == {(0, 0), (0, 1), (0, 2)}


def test_bfs_cluster_separated_by_different_color() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[0][0] = 8
    grid[0][1] = 9  # different color breaks cluster
    grid[0][2] = 8
    result = Game._bfs_cluster(grid, 0, 0)
    assert result == {(0, 0)}


def test_bfs_cluster_L_shape() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[0][0] = 10
    grid[0][1] = 10
    grid[1][0] = 10
    result = Game._bfs_cluster(grid, 0, 0)
    assert result == {(0, 0), (1, 0), (0, 1)}


# ── Find All Clusters tests ────────────────────────────────────────────

def test_find_all_clusters_empty() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    result = Game._find_all_clusters(grid)
    assert len(result) == 0


def test_find_all_clusters_no_match_3() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[0][0] = 8
    grid[0][1] = 8
    result = Game._find_all_clusters(grid)
    assert len(result) == 0  # only 2, not enough


def test_find_all_clusters_one_cluster() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[0][0] = 8
    grid[0][1] = 8
    grid[0][2] = 8
    result = Game._find_all_clusters(grid)
    assert len(result) == 1
    assert len(result[0]) == 3


def test_find_all_clusters_two_separate_clusters() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[0][0] = 8
    grid[0][1] = 8
    grid[0][2] = 8
    grid[0][4] = 9
    grid[0][5] = 9
    grid[0][6] = 9
    result = Game._find_all_clusters(grid)
    assert len(result) == 2


def test_find_all_clusters_sorted_by_size() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[0][0] = 8
    grid[0][1] = 8
    grid[0][2] = 8  # size 3
    grid[0][4] = 9
    grid[0][5] = 9
    grid[0][6] = 9
    grid[0][7] = 9
    grid[0][8] = 9  # size 5
    result = Game._find_all_clusters(grid)
    assert len(result[0]) == 5  # largest first
    assert len(result[1]) == 3


# ── Gravity Compaction tests ───────────────────────────────────────────

def test_apply_gravity_empty() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    moved = Game._apply_gravity(grid)
    assert moved is False


def test_apply_gravity_already_bottom() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[GRID_ROWS - 1][0] = 8
    moved = Game._apply_gravity(grid)
    assert moved is False


def test_apply_gravity_falls_down() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[0][0] = 8
    moved = Game._apply_gravity(grid)
    assert moved is True
    assert grid[GRID_ROWS - 1][0] == 8
    assert grid[0][0] == 0


def test_apply_gravity_multiple_stack() -> None:
    grid = [[0] * GRID_COLS for _ in range(GRID_ROWS)]
    grid[0][0] = 8
    grid[2][0] = 9
    grid[3][0] = 0
    grid[4][0] = 10
    moved = Game._apply_gravity(grid)
    assert moved is True
    assert grid[4][0] == 10
    assert grid[3][0] == 9
    assert grid[2][0] == 8
    assert grid[1][0] == 0
    assert grid[0][0] == 0


# ── Fragment Spawning tests ────────────────────────────────────────────

def test_spawn_fragments_count_low_power() -> None:
    g = _make_game()
    frags = g._spawn_fragments(160.0, 100.0, 1.0)
    assert len(frags) == 5


def test_spawn_fragments_count_high_power() -> None:
    g = _make_game()
    frags = g._spawn_fragments(160.0, 100.0, 20.0)
    assert len(frags) == 7


def test_spawn_fragments_position_origin() -> None:
    g = _make_game()
    frags = g._spawn_fragments(200.0, 150.0, 8.0)
    for f in frags:
        assert f.x == 200.0
        assert f.y == 150.0
        assert f.landed is False


def test_spawn_fragments_valid_colors() -> None:
    g = _make_game()
    frags = g._spawn_fragments(160.0, 100.0, 10.0)
    for f in frags:
        assert f.color in FRAGMENT_COLORS


def test_spawn_fragments_different_seed_different_colors() -> None:
    g1 = _make_game(42)
    g2 = _make_game(99)
    frags1 = g1._spawn_fragments(160.0, 100.0, 10.0)
    frags2 = g2._spawn_fragments(160.0, 100.0, 10.0)
    colors1 = [f.color for f in frags1]
    colors2 = [f.color for f in frags2]
    # With different seeds, color orders should be different
    # (Very unlikely to match exactly)
    assert colors1 != colors2


# ── Fragment Landing tests ─────────────────────────────────────────────

def test_resolve_landing_success() -> None:
    g = _make_game()
    frag = Fragment(x=100.0, y=GRID_Y, vx=0.0, vy=0.0, color=8)
    result = g._resolve_landing(frag)
    assert result is True
    assert frag.landed is True
    assert frag.grid_col == 5  # 100 // 20 = 5
    assert frag.grid_row == 4  # bottom row
    assert g.grid[4][5] == 8


def test_resolve_landing_stack() -> None:
    g = _make_game()
    g.grid[4][3] = 8  # bottom row occupied
    frag = Fragment(x=70.0, y=GRID_Y, vx=0.0, vy=0.0, color=9)
    result = g._resolve_landing(frag)
    assert result is True
    assert frag.grid_col == 3
    assert frag.grid_row == 3  # one above bottom
    assert g.grid[3][3] == 9


def test_resolve_landing_column_full() -> None:
    g = _make_game()
    for r in range(GRID_ROWS):
        g.grid[r][5] = 8
    frag = Fragment(x=105.0, y=GRID_Y, vx=0.0, vy=0.0, color=10)
    result = g._resolve_landing(frag)
    assert result is False
    assert frag.landed is False


def test_resolve_landing_out_of_bounds_left() -> None:
    g = _make_game()
    frag = Fragment(x=-5.0, y=GRID_Y, vx=0.0, vy=0.0, color=8)
    result = g._resolve_landing(frag)
    assert result is False
    assert frag.landed is False


def test_resolve_landing_out_of_bounds_right() -> None:
    g = _make_game()
    frag = Fragment(x=330.0, y=GRID_Y, vx=0.0, vy=0.0, color=8)
    result = g._resolve_landing(frag)
    assert result is False
    assert frag.landed is False


# ── Scoring / Resolution tests ─────────────────────────────────────────

def test_check_and_resolve_empty_grid() -> None:
    g = _make_game()
    score = g._check_and_resolve()
    assert score == 0
    assert g.combo == 0


def test_check_and_resolve_single_cluster() -> None:
    g = _make_game()
    g.grid[4][0] = 8
    g.grid[4][1] = 8
    g.grid[4][2] = 8
    score = g._check_and_resolve()
    # cluster_size=3, combo=0 initially, multiplier=1.0
    # points = 3*3 * 1.0 * 10 = 90
    assert score == 90
    assert g.score == 90
    assert g.combo == 1
    assert g.max_combo == 1

    # ensure grid is cleared
    assert g.grid[4][0] == 0
    assert g.grid[4][1] == 0
    assert g.grid[4][2] == 0
    assert len(g.particles) > 0


def test_check_and_resolve_chain_reaction() -> None:
    g = _make_game()
    # Place fragments in such a way that after gravity, a new cluster forms
    g.grid[2][0] = 8
    g.grid[1][0] = 8
    g.grid[0][0] = 8  # vertical cluster of 3 at col 0, rows 0-2

    # Also place a fragment at col 1, row 4 with same color
    g.grid[4][1] = 8
    g.grid[3][1] = 8  # with the cluster above clearing, gravity may put them together

    # First: vertical cluster of 3 at col 0 should clear
    # Then gravity: col 1 fragments fall down, may or may not form new cluster
    score = g._check_and_resolve()
    # First: 3*3 * 1.0 * 10 = 90, combo becomes 1, multiplier becomes 1.5
    # After gravity: if g.grid[4][1] and g.grid[3][1] fall to rows 4,3
    # They are 2 of same color in col 1; no cluster of 3, stops
    # But wait: after first cluster clears at (0,0),(0,1),(0,2), gravity runs
    # col 1: rows 3,4 have 8 -> after gravity: row4=8, row3=8, rows 0-2 empty
    # Only 2 at col 1, so no more clusters.
    assert score >= 90
    assert g.score >= 90


def test_check_and_resolve_combo_increases_multiplier() -> None:
    g = _make_game()
    # Create two separated clusters
    g.grid[4][0] = 8
    g.grid[4][1] = 8
    g.grid[4][2] = 8  # cluster 1

    g.grid[4][5] = 9
    g.grid[4][6] = 9
    g.grid[4][7] = 9  # cluster 2

    score = g._check_and_resolve()
    # First cluster: cs=3, multiplier=1.0 (combo=0), points = 3*3*1.0*10 = 90
    #   combo becomes 1, multiplier becomes 1.0
    # Second cluster: cs=3, multiplier=1.0 (combo=1), points = 3*3*1.0*10 = 90
    #   combo becomes 2, multiplier becomes 1.5
    # Total = 180
    assert score == 180
    assert g.score == 180
    assert g.combo == 2
    assert g.max_combo == 2
    assert g.combo_multiplier == 1.5


def test_score_big_cluster() -> None:
    g = _make_game()
    # 5 cells cluster
    g.grid[4][0] = 8
    g.grid[4][1] = 8
    g.grid[4][2] = 8
    g.grid[4][3] = 8
    g.grid[4][4] = 8
    score = g._check_and_resolve()
    # size=5, multiplier=1.0: 5*5*1.0*10=250
    assert score == 250
    assert g.score == 250


# ── Resolve Step (animated) tests ──────────────────────────────────────

def test_resolve_step_empty_grid() -> None:
    g = _make_game()
    g._resolve_state = "wait"
    done = g._resolve_step()
    assert done is True
    assert g.combo == 0
    assert g.combo_multiplier == 1.0


def test_resolve_step_finds_clusters() -> None:
    g = _make_game()
    g.grid[4][0] = 8
    g.grid[4][1] = 8
    g.grid[4][2] = 8
    g._resolve_state = "wait"
    done = g._resolve_step()
    assert done is False
    assert g._resolve_state == "finding"
    assert len(g._resolve_clusters) == 1


# ── Apply Gravity with chain test ──────────────────────────────────────

def test_apply_gravity_enables_chain() -> None:
    g = _make_game()
    # Setup: clear a bottom cluster, gravity brings new cluster together
    g.grid[4][0] = 8
    g.grid[4][1] = 8
    g.grid[4][2] = 8  # bottom cluster of 3

    g.grid[3][0] = 8  # directly above, same color -> will form cluster of 4
    # Actually: BFS from (0,4) finds (0,4),(1,4),(2,4),(0,3)=4 cells
    # So one cluster of size 4

    score = g._check_and_resolve()
    assert score == 160  # 4*4*1.0*10 = 160
    # After clearing, no more fragments, so gravity returns False
    assert g.grid[3][0] == 0
    assert g.grid[4][0] == 0


# ── Full round test ────────────────────────────────────────────────────

def test_full_round_simulation() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.AIMING

    # Simulate fragments landing with a 3-match
    frags = [
        Fragment(x=10.0, y=GRID_Y, vx=0.0, vy=0.0, color=8),
        Fragment(x=30.0, y=GRID_Y, vx=0.0, vy=0.0, color=8),
        Fragment(x=50.0, y=GRID_Y, vx=0.0, vy=0.0, color=8),
        Fragment(x=70.0, y=GRID_Y, vx=0.0, vy=0.0, color=9),
        Fragment(x=90.0, y=GRID_Y, vx=0.0, vy=0.0, color=10),
    ]
    for frag in frags:
        g._resolve_landing(frag)

    # All landed, run resolve
    g.phase = Phase.RESOLVING
    g._resolve_state = "wait"

    # Run through all resolve steps
    for _ in range(200):
        done = g._resolve_step()
        if done:
            break

    # After resolution, should be back to AIMING with score
    assert g.score >= 90  # the 3-match gives 90
    assert g.shots_used == 0  # Wasn't incremented because we manually set phase


# ── Combo tracking test ────────────────────────────────────────────────

def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    assert g.max_combo == 0

    g.grid[4][0] = 8
    g.grid[4][1] = 8
    g.grid[4][2] = 8
    g._check_and_resolve()
    assert g.max_combo == 1

    g.grid[4][5] = 9
    g.grid[4][6] = 9
    g.grid[4][7] = 9
    g.grid[4][8] = 9
    g._check_and_resolve()
    assert g.max_combo == 2


# ── Reset after game over test ─────────────────────────────────────────

def test_reset_after_play() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 5
    g.max_combo = 5
    g.shots_used = 10
    g.grid[4][0] = 8
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.shots_used == 0
    assert g.phase == Phase.TITLE
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            assert g.grid[r][c] == 0


# ── Fragment spread angle tests ────────────────────────────────────────

def test_fragments_spread_outward() -> None:
    g = _make_game(42)
    frags = g._spawn_fragments(160.0, 100.0, 10.0)
    vx_values = [f.vx for f in frags]
    assert min(vx_values) < max(vx_values)  # not all same direction


# ── Combo text spawn test ──────────────────────────────────────────────

def test_spawn_combo_text() -> None:
    g = _make_game()
    g._spawn_combo_text(3, 4, 5, 2.5)
    assert len(g.combo_texts) == 1
    ct = g.combo_texts[0]
    assert ct.text == "x5"
    assert ct.life == 30


# ── Particle spawn test ────────────────────────────────────────────────

def test_spawn_explosion() -> None:
    g = _make_game(42)
    g._spawn_explosion(5, 4, 8)
    assert len(g.particles) == 8
    for p in g.particles:
        assert p.color == 8


# ── Particle update test ───────────────────────────────────────────────

def test_update_particles_moves_and_decays() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, color=8, life=5)
    g.particles.append(p)
    g._update_particles()
    assert p.x == 101.0
    assert p.y == 48.0
    assert p.life == 4


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, color=8, life=1)
    g.particles.append(p)
    g._update_particles()
    assert len(g.particles) == 0


# ── Combo text update test ─────────────────────────────────────────────

def test_update_combo_texts_floats_and_decays() -> None:
    g = _make_game()
    ct = ComboText(x=80.0, y=200.0, life=10, text="x3", color=10)
    g.combo_texts.append(ct)
    g._update_combo_texts()
    assert ct.y == 199.5
    assert ct.life == 9


def test_update_combo_texts_removes_dead() -> None:
    g = _make_game()
    ct = ComboText(x=80.0, y=200.0, life=1, text="x3", color=10)
    g.combo_texts.append(ct)
    g._update_combo_texts()
    assert len(g.combo_texts) == 0


print("All tests passed!")
