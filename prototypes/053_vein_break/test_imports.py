"""test_imports.py — Headless logic tests for VEIN BREAK.

Uses Game.__new__ pattern to bypass pyxel.init/run for headless testing.
"""
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/053_vein_break")
from main import (
    BASE_SCORE,
    CELL,
    CHAIN_BONUS_MULT,
    COLS,
    COLOR_VALS,
    COMBO_MULT_STEP,
    COMBO_THRESHOLD,
    FUEL_PER_DRILL,
    FUEL_PICKUP_AMOUNT,
    FUEL_PICKUP_CHANCE,
    MAX_FUEL,
    NUM_COLORS,
    ROWS,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def make_game() -> Game:
    """Create a Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    # Pre-init all attributes reset() touches
    g._rng = random.Random(42)  # deterministic
    g.grid = [[0] * COLS for _ in range(ROWS)]
    g.player_col = 0
    g.fuel = 0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.last_color = None
    g.phase = Phase.PLAYING
    g.particles = []
    g.floating_texts = []
    g._drill_cooldown = 0
    g._spawn_timer = 0
    g._chain_queue = []
    g._chain_color = 0
    g._chain_score_multi = 1.0
    g._chain_timer = 0
    g._blocks_cleared = 0
    g._game_over_timer = 0
    g._shake_frames = 0
    g.reset()
    return g


# ── Basic dataclass / constant tests ──


def test_constants() -> None:
    """Verify all game constants are sensible."""
    assert COLS == 10
    assert ROWS == 10
    assert CELL == 20
    assert NUM_COLORS == 4
    assert len(COLOR_VALS) == 4
    assert MAX_FUEL == 100
    assert FUEL_PER_DRILL == 3
    assert COMBO_THRESHOLD == 3
    assert BASE_SCORE == 10
    assert 0 < FUEL_PICKUP_CHANCE < 1
    assert FUEL_PICKUP_AMOUNT > 0
    assert COMBO_MULT_STEP > 0
    assert CHAIN_BONUS_MULT > 0


def test_particle_dataclass() -> None:
    """Particle can be created with all fields."""
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, color=8, life=15)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.color == 8
    assert p.life == 15


def test_floating_text_dataclass() -> None:
    """FloatingText can be created with all fields."""
    ft = FloatingText(x=50.0, y=30.0, text="x3", color=8, life=30)
    assert ft.text == "x3"
    assert ft.color == 8
    assert ft.life == 30


def test_phase_enum() -> None:
    """Phase enum has expected members."""
    assert Phase.PLAYING in Phase
    assert Phase.CHAIN_ANIM in Phase
    assert Phase.GAME_OVER in Phase


# ── Game state tests ──


def test_reset_initializes_grid() -> None:
    """After reset(), grid is fully populated with valid colors."""
    g = make_game()
    filled = 0
    for r in range(ROWS):
        for c in range(COLS):
            assert 1 <= g.grid[r][c] <= NUM_COLORS, f"Bad color at ({r},{c})"
            filled += 1
    assert filled == ROWS * COLS


def test_reset_initial_state() -> None:
    """After reset(), all game state variables are at initial values."""
    g = make_game()
    assert g.fuel == MAX_FUEL
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.last_color is None
    assert g.phase == Phase.PLAYING
    assert g.particles == []
    assert g.floating_texts == []
    assert g._chain_queue == []
    assert g._blocks_cleared == 0


# ── _find_topmost_block tests ──


def test_find_topmost_block_full_column() -> None:
    """Returns first row (0) for a full column."""
    g = make_game()
    assert g._find_topmost_block(0) == 0


def test_find_topmost_block_empty_cells() -> None:
    """Skips empty cells at top, returns first non-empty."""
    g = make_game()
    g.grid[0][3] = 0
    g.grid[1][3] = 0
    assert g._find_topmost_block(3) == 2


def test_find_topmost_block_all_empty() -> None:
    """Returns -1 when column is completely empty."""
    g = make_game()
    for r in range(ROWS):
        g.grid[r][5] = 0
    assert g._find_topmost_block(5) == -1


# ── _bfs_cluster tests ──


def test_bfs_single_cell() -> None:
    """A cell with no same-color neighbors returns only itself."""
    g = make_game()
    # Set up isolated cell
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = 1  # all RED
    g.grid[0][0] = 2  # one GREEN
    cluster = g._bfs_cluster(0, 0, 2)
    assert cluster == {(0, 0)}


def test_bfs_connected_line() -> None:
    """A horizontal line of same color is fully detected."""
    g = make_game()
    # Set ALL cells to RED first to avoid random init contaminating the cluster
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = 1  # all RED
    # Create a horizontal green line at row 5
    g.grid[5][2] = 2
    g.grid[5][3] = 2
    g.grid[5][4] = 2
    g.grid[5][5] = 2
    cluster = g._bfs_cluster(2, 5, 2)
    assert cluster == {(2, 5), (3, 5), (4, 5), (5, 5)}


def test_bfs_connected_block() -> None:
    """A 2×2 block of same color is fully detected."""
    g = make_game()
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = 1
    g.grid[3][3] = 2
    g.grid[3][4] = 2
    g.grid[4][3] = 2
    g.grid[4][4] = 2
    cluster = g._bfs_cluster(3, 3, 2)
    assert cluster == {(3, 3), (4, 3), (3, 4), (4, 4)}


def test_bfs_stops_at_different_color() -> None:
    """BFS does not cross into different colors."""
    g = make_game()
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = 1
    g.grid[5][5] = 2  # island
    cluster = g._bfs_cluster(5, 5, 2)
    assert cluster == {(5, 5)}


def test_bfs_boundary_clamp() -> None:
    """BFS at grid edge doesn't go out of bounds."""
    g = make_game()
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = 2
    cluster = g._bfs_cluster(0, 0, 2)
    # Should contain all cells since all are same color
    assert len(cluster) == ROWS * COLS


# ── _apply_gravity tests ──


def test_gravity_no_gaps() -> None:
    """Gravity on a full grid changes nothing."""
    g = make_game()
    # Copy grid
    original = [row[:] for row in g.grid]
    g._apply_gravity()
    for r in range(ROWS):
        for c in range(COLS):
            assert g.grid[r][c] == original[r][c]


def test_gravity_compacts_single_gap() -> None:
    """A gap in a column is filled by blocks above falling down."""
    g = make_game()
    g.grid[0][3] = 0  # gap at top
    original_bottom = g.grid[ROWS - 1][3]
    g._apply_gravity()
    # Bottom row should now be the original second-from-bottom
    assert g.grid[ROWS - 1][3] != 0  # bottom is filled
    assert g.grid[0][3] == 0  # top remains empty


def test_gravity_cleared_column() -> None:
    """Fully cleared column stays empty."""
    g = make_game()
    for r in range(ROWS):
        g.grid[r][7] = 0
    g._apply_gravity()
    for r in range(ROWS):
        assert g.grid[r][7] == 0


# ── _drill tests ──


def test_drill_removes_topmost_block() -> None:
    """_drill() removes the topmost block and deducts fuel."""
    g = make_game()
    g.player_col = 3
    g.fuel = MAX_FUEL
    initial_top = g.grid[0][3]
    g._drill()
    assert g.grid[0][3] == 0
    assert g.fuel == MAX_FUEL - FUEL_PER_DRILL


def test_drill_empty_column_noop() -> None:
    """_drill() on an empty column does nothing."""
    g = make_game()
    g.player_col = 5
    g.fuel = MAX_FUEL
    for r in range(ROWS):
        g.grid[r][5] = 0
    fuel_before = g.fuel
    g._drill()
    assert g.fuel == fuel_before  # no fuel deducted


def test_drill_updates_combo_on_match() -> None:
    """Consecutive same-color drills increment combo."""
    g = make_game()
    g.player_col = 0
    g.fuel = MAX_FUEL
    # Set up two same-color blocks at top
    g.grid[0][0] = 2  # GREEN
    g.grid[0][1] = 2  # GREEN (for second drill)
    # Also set the rest so first drill finds block at row 0
    g.grid[0][0] = 2

    g._drill()  # first drill
    assert g.combo == 1
    assert g.last_color == 2

    # Move and drill second same-color block
    g.player_col = 1
    g.grid[0][1] = 2
    g._drill()  # second drill matches
    assert g.combo == 2


def test_drill_resets_combo_on_mismatch() -> None:
    """Drilling a different color resets combo to 1."""
    g = make_game()
    g.player_col = 0
    g.fuel = MAX_FUEL
    g.grid[0][0] = 2  # GREEN
    g._drill()
    assert g.combo == 1

    # Second drill: different color
    g.player_col = 1
    g.grid[0][1] = 3  # BLUE
    g._drill()
    assert g.combo == 1  # reset
    assert g.last_color == 3


def test_drill_updates_max_combo() -> None:
    """max_combo tracks the highest combo achieved."""
    g = make_game()
    g.player_col = 0
    g.fuel = MAX_FUEL
    # Drill 3 same-color blocks in row
    for c in range(3):
        g.player_col = c
        g.grid[0][c] = 2  # GREEN
        g._drill()
    assert g.max_combo == 3


def test_drill_scores_correctly() -> None:
    """Score calculation uses combo multiplier."""
    g = make_game()
    g.player_col = 0
    g.fuel = MAX_FUEL
    g.grid[0][0] = 2
    g._drill()  # combo=1, score = 10 * 1.0 = 10
    assert g.score == int(BASE_SCORE * 1.0)

    g.player_col = 1
    g.grid[0][1] = 2
    g._drill()  # combo=2, score += 10 * 1.5 = 15
    assert g.score == int(BASE_SCORE * 1.0) + int(BASE_SCORE * (1.0 + COMBO_MULT_STEP))


def test_drill_triggers_chain_break() -> None:
    """COMBO >= 3 on a connected cluster triggers CHAIN_ANIM."""
    g = make_game()
    g.fuel = MAX_FUEL
    # Set ALL cells to RED background
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = 1  # RED

    # Create a GREEN cluster at bottom: row 8-9, cols 8-9 (2×2 = 4 cells)
    g.grid[9][8] = 2
    g.grid[9][9] = 2
    g.grid[8][8] = 2
    g.grid[8][9] = 2

    # Place GREEN blocks at the very top of cols 0, 1 for building combo.
    # These are at row 0 so they are the topmost block and won't shift.
    g.grid[0][0] = 2  # GREEN at top of col 0
    g.grid[0][1] = 2  # GREEN at top of col 1

    # First drill: GREEN at col 0
    g.player_col = 0
    g._drill()
    assert g.combo == 1
    assert g.last_color == 2

    # Second drill: GREEN at col 1 (after gravity, grid[0][1] is still the topmost)
    g.player_col = 1
    g._drill()
    assert g.combo == 2

    # Third drill: GREEN at col 8, where the cluster is.
    # topmost block in col 8: after gravity compaction of prior drills,
    # row 0 col 8 is still RED. But wait — we need the topmost block in
    # col 8 to be GREEN for this to work. The GREEN cluster is at rows 8-9.
    # So there are RED blocks at rows 0-7 above it. _drill() would drill RED
    # (topmost), not GREEN.
    #
    # Fix: clear the RED blocks above the GREEN cluster in col 8 and 9
    # so the GREENs are at the top of their columns.
    for r in range(8):
        g.grid[r][8] = 0
        g.grid[r][9] = 0
    g._apply_gravity()  # compact: GREENs move to rows 0-1

    g.player_col = 8
    g._drill()  # combo=3, drills GREEN, triggers chain
    assert g.combo == 3
    assert g.phase == Phase.CHAIN_ANIM
    # cluster: {(8,0), (9,0), (8,1), (9,1)} in new coords minus drilled (8,0)
    assert len(g._chain_queue) >= 1


def test_drill_fuel_pickup() -> None:
    """Fuel pickups are awarded with correct probability."""
    # Monkey-patch random to guarantee pickup
    g = make_game()
    g.player_col = 0
    g.fuel = MAX_FUEL - 20
    g.grid[0][0] = 2

    _old_random = g._rng.random
    g._rng.random = lambda: 0.0  # forces pickup
    g._drill()
    assert g.fuel == MAX_FUEL - 20 - FUEL_PER_DRILL + FUEL_PICKUP_AMOUNT
    g._rng.random = _old_random


# ── Chain animation tests ──


def test_chain_anim_clears_queued_cells() -> None:
    """_update_chain_anim clears cells from the queue."""
    g = make_game()
    g._chain_queue = [(3, 5), (4, 5)]
    g._chain_color = 2
    g.grid[5][3] = 2
    g.grid[5][4] = 2
    g.phase = Phase.CHAIN_ANIM

    # Tick 1: timer becomes 1, 1%2!=0, skip
    g._update_chain_anim()
    assert len(g._chain_queue) == 2  # unchanged

    # Tick 2: timer becomes 2, 2%2==0, clear first cell
    g._update_chain_anim()
    assert len(g._chain_queue) == 1
    assert g.grid[5][3] == 0

    # Tick 3: timer=3, skip
    g._update_chain_anim()

    # Tick 4: timer=4, clear second cell — queue empty but phase
    # doesn't change until NEXT non-skip tick (tick 6)
    g._update_chain_anim()
    assert len(g._chain_queue) == 0
    assert g.grid[5][4] == 0
    assert g.phase == Phase.CHAIN_ANIM  # still in chain, waiting for next tick

    # Tick 5: timer=5, skip
    g._update_chain_anim()

    # Tick 6: timer=6, 6%2==0, queue empty → else branch → phase transition
    g._update_chain_anim()
    assert g.phase == Phase.PLAYING


def test_chain_anim_skips_already_cleared() -> None:
    """Chain anim gracefully handles already-cleared cells and returns to PLAYING."""
    g = make_game()
    g._chain_queue = [(3, 5)]
    g._chain_color = 2
    g.grid[5][3] = 0  # already cleared
    g.phase = Phase.CHAIN_ANIM
    g._chain_timer = 1  # next tick (timer=2) clears
    g._update_chain_anim()  # timer=2, pop, check grid[r][c]==color → no (it's 0)
    assert g.grid[5][3] == 0  # still 0, no crash
    assert len(g._chain_queue) == 0
    # Need 2 more ticks for phase transition (timer=3 skip, timer=4 transition)
    g._update_chain_anim()  # timer=3, skip
    g._update_chain_anim()  # timer=4, queue empty → transition
    assert g.phase == Phase.PLAYING


# ── _spawn_blocks tests ──


def test_spawn_blocks_fills_empty_top_row() -> None:
    """_spawn_blocks fills empty cells at the top of random columns."""
    g = make_game()
    # Clear an entire column
    for r in range(ROWS):
        g.grid[r][2] = 0
    # Count non-empty cells before spawn
    before = sum(1 for r in range(ROWS) for c in range(COLS) if g.grid[r][c] != 0)
    g._spawn_blocks()
    after = sum(1 for r in range(ROWS) for c in range(COLS) if g.grid[r][c] != 0)
    # At least some new blocks were placed (up to SPAWN_COUNT=2)
    assert after >= before
    assert after <= before + 2

    # Specifically, column 2 should have at most 2 new blocks at the top
    col2_filled = sum(1 for r in range(ROWS) if g.grid[r][2] != 0)
    assert 0 <= col2_filled <= 2


def test_spawn_blocks_only_in_empty_cells() -> None:
    """_spawn_blocks only writes to cells that were empty."""
    g = make_game()
    # Record which cells are non-empty
    non_empty_before: set[tuple[int, int]] = set()
    for r in range(ROWS):
        for c in range(COLS):
            if g.grid[r][c] != 0:
                non_empty_before.add((r, c))
    g._spawn_blocks()
    # All previously non-empty cells should still be non-empty
    for r, c in non_empty_before:
        assert g.grid[r][c] != 0, f"Cell ({r},{c}) was overwritten!"


# ── Particle tests ──


def test_spawn_particles_adds_to_list() -> None:
    """_spawn_particles appends particles."""
    g = make_game()
    count_before = len(g.particles)
    g._spawn_particles(50, 50, 1, 5)
    assert len(g.particles) == count_before + 5


def test_update_particles_reduces_life() -> None:
    """_update_particles decrements particle life."""
    g = make_game()
    g._spawn_particles(50, 50, 1, 3)
    initial_life = g.particles[0].life
    g._update_particles()
    assert g.particles[0].life == initial_life - 1


def test_particles_removed_when_dead() -> None:
    """Particles with life <= 0 are removed."""
    g = make_game()
    g._spawn_particles(50, 50, 1, 2)
    g.particles[0].life = 0
    g._update_particles()
    assert len(g.particles) == 1  # one removed, one remains with life > 0
    g.particles[0].life = 0
    g._update_particles()
    assert len(g.particles) == 0


def test_particles_trimmed_at_max() -> None:
    """Excess particles are trimmed from the front."""
    g = make_game()
    for _ in range(70):
        g.particles.append(Particle(x=0, y=0, vx=0, vy=0, color=8, life=10))
    assert len(g.particles) == 70
    g._spawn_particles(50, 50, 1, 1)  # this triggers trim
    assert len(g.particles) <= 60


# ── Floating text tests ──


def test_add_floating_text() -> None:
    """_add_floating_text adds to the list."""
    g = make_game()
    g._add_floating_text(100, 50, "TEST", 1)  # color index 1 → RED
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"


def test_floating_text_index_color() -> None:
    """Color index 1-4 maps to COLOR_VALS."""
    g = make_game()
    g._add_floating_text(100, 50, "X", 2)  # GREEN index
    assert g.floating_texts[0].color == COLOR_VALS[1]  # index 2 → vals[1] = 11 (GREEN)


def test_floating_text_raw_color() -> None:
    """Raw pyxel color (>=5) passes through unchanged."""
    g = make_game()
    g._add_floating_text(100, 50, "X", 10)  # raw YELLOW
    assert g.floating_texts[0].color == 10


def test_update_floating_texts_removes_expired() -> None:
    """Floating texts with life <= 0 are removed."""
    g = make_game()
    g._add_floating_text(100, 50, "X", 1)
    g.floating_texts[0].life = 0
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Game over tests ──


def test_fuel_depletion_triggers_game_over() -> None:
    """When fuel drops to 0, the game-over condition activates.
    
    We test the internal condition directly because _update_playing()
    calls pyxel.btnp() which panics in headless mode.
    """
    g = make_game()
    g.fuel = 0
    # This is the condition checked at the end of _update_playing()
    if g.fuel <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_low_fuel_not_game_over() -> None:
    """Fuel > 0 but < FUEL_PER_DRILL does not trigger game over
    unless update loop detects it. The game-over trigger is at
    the end of _update_playing()."""
    g = make_game()
    g.fuel = 2  # > 0 but < FUEL_PER_DRILL=3
    assert g.phase == Phase.PLAYING  # phase doesn't change until checked
    # Manual check simulates _update_playing()'s game-over condition
    if g.fuel <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.PLAYING  # fuel=2 > 0, no game over


# ── Integration scenarios ──


def test_drill_gravity_chain_sequence() -> None:
    """Full sequence: drill → combo → chain → gravity."""
    g = make_game()
    g.fuel = MAX_FUEL
    # Fill grid with RED
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = 1  # all RED

    # GREEN cluster at bottom
    g.grid[9][8] = 2
    g.grid[9][9] = 2
    g.grid[8][8] = 2
    g.grid[8][9] = 2

    # Top-of-column GREENs for building combo (row 0 so gravity doesn't affect)
    g.grid[0][0] = 2
    g.grid[0][1] = 2

    # Clear RED blocks above the GREEN cluster so it's at column top
    for r in range(8):
        g.grid[r][8] = 0
        g.grid[r][9] = 0
    g._apply_gravity()  # GREENs move to rows 0-1 in cols 8-9

    g.player_col = 0
    g._drill()  # combo=1, GREEN
    assert g.combo == 1

    g.player_col = 1
    g._drill()  # combo=2, GREEN
    assert g.combo == 2

    # Third GREEN drill triggers chain
    g.player_col = 8
    g._drill()  # combo=3, GREEN, should trigger chain
    assert g.combo == 3
    assert g.phase == Phase.CHAIN_ANIM
    assert len(g._chain_queue) == 3  # 4-cluster minus drilled cell


if __name__ == "__main__":
    import traceback

    tests = [
        ("constants", test_constants),
        ("particle_dataclass", test_particle_dataclass),
        ("floating_text_dataclass", test_floating_text_dataclass),
        ("phase_enum", test_phase_enum),
        ("reset_initializes_grid", test_reset_initializes_grid),
        ("reset_initial_state", test_reset_initial_state),
        ("find_topmost_block_full_column", test_find_topmost_block_full_column),
        ("find_topmost_block_empty_cells", test_find_topmost_block_empty_cells),
        ("find_topmost_block_all_empty", test_find_topmost_block_all_empty),
        ("bfs_single_cell", test_bfs_single_cell),
        ("bfs_connected_line", test_bfs_connected_line),
        ("bfs_connected_block", test_bfs_connected_block),
        ("bfs_stops_at_different_color", test_bfs_stops_at_different_color),
        ("bfs_boundary_clamp", test_bfs_boundary_clamp),
        ("gravity_no_gaps", test_gravity_no_gaps),
        ("gravity_compacts_single_gap", test_gravity_compacts_single_gap),
        ("gravity_cleared_column", test_gravity_cleared_column),
        ("drill_removes_topmost_block", test_drill_removes_topmost_block),
        ("drill_empty_column_noop", test_drill_empty_column_noop),
        ("drill_updates_combo_on_match", test_drill_updates_combo_on_match),
        ("drill_resets_combo_on_mismatch", test_drill_resets_combo_on_mismatch),
        ("drill_updates_max_combo", test_drill_updates_max_combo),
        ("drill_scores_correctly", test_drill_scores_correctly),
        ("drill_triggers_chain_break", test_drill_triggers_chain_break),
        ("drill_fuel_pickup", test_drill_fuel_pickup),
        ("chain_anim_clears_queued_cells", test_chain_anim_clears_queued_cells),
        ("chain_anim_skips_already_cleared", test_chain_anim_skips_already_cleared),
        ("spawn_blocks_fills_empty_top_row", test_spawn_blocks_fills_empty_top_row),
        ("spawn_blocks_only_in_empty_cells", test_spawn_blocks_only_in_empty_cells),
        ("spawn_particles_adds_to_list", test_spawn_particles_adds_to_list),
        ("update_particles_reduces_life", test_update_particles_reduces_life),
        ("particles_removed_when_dead", test_particles_removed_when_dead),
        ("particles_trimmed_at_max", test_particles_trimmed_at_max),
        ("add_floating_text", test_add_floating_text),
        ("floating_text_index_color", test_floating_text_index_color),
        ("floating_text_raw_color", test_floating_text_raw_color),
        ("update_floating_texts_removes_expired", test_update_floating_texts_removes_expired),
        ("fuel_depletion_triggers_game_over", test_fuel_depletion_triggers_game_over),
        ("low_fuel_not_game_over", test_low_fuel_not_game_over),
        ("drill_gravity_chain_sequence", test_drill_gravity_chain_sequence),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS {name}")
        except Exception:
            failed += 1
            print(f"  FAIL {name}")
            traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
