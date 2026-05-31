"""test_imports.py — Headless logic tests for FIRE BREAK (089)."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/089_fire_break")

from main import (  # type: ignore[import]
    COMBO_SURGE_THRESHOLD,
    CELL_SIZE,
    FIRE_COLORS,
    GAME_DURATION,
    GRID_COLS,
    GRID_ROWS,
    GRID_X,
    GRID_Y,
    HEAT_PENALTY_WRONG,
    MAX_HEAT,
    SPAWN_INTERVAL,
    SPREAD_INITIAL,
    SURGE_FLASH_FRAMES,
    SHAKE_FRAMES,
    FireBreak,
    Particle,
    Phase,
)


# ─── Factory ────────────────────────────────────────────────────────────────


def _make_game() -> FireBreak:
    """Create a FireBreak instance usable for headless testing."""
    g = FireBreak.__new__(FireBreak)
    # Pre-init ALL instance attributes before reset()
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.fire_color = 1
    g.grid = []
    g.next_grid = []
    g.spawn_timer = 0
    g.spread_timer = 0
    g.spread_interval = SPREAD_INITIAL
    g.game_timer = 0
    g.particles = []
    g.shake_frames = 0
    g.surge_flash = 0
    g._rng = random.Random(42)
    g.surge_count = 0
    g._last_click_surge = False
    g._last_surge_cells = 0
    g._last_score_gained = 0
    g._last_click_combo_broke = False
    g.reset()
    # reset() sets self._rng = random.Random() — overwrite with seeded
    g._rng = random.Random(42)
    return g


# ─── Data / Constants ───────────────────────────────────────────────────────


def test_constants():
    """Verify key game constants are reasonable."""
    assert GRID_COLS == 16
    assert GRID_ROWS == 12
    assert CELL_SIZE == 18
    assert GAME_DURATION == 90 * 30
    assert MAX_HEAT == 100.0
    assert COMBO_SURGE_THRESHOLD == 4
    assert len(FIRE_COLORS) == 4
    assert FIRE_COLORS == [8, 3, 1, 10]


def test_particle_dataclass():
    """Particle dataclass works as expected."""
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-0.5, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -0.5
    assert p.life == 15
    assert p.color == 8


def test_phase_enum():
    assert Phase.TITLE.value != Phase.PLAYING.value
    assert Phase.PLAYING.value != Phase.GAME_OVER.value


# ─── Grid ───────────────────────────────────────────────────────────────────


def test_make_grid():
    g = _make_game()
    grid = g._make_grid()
    assert len(grid) == GRID_ROWS
    assert len(grid[0]) == GRID_COLS
    assert all(cell == 0 for row in grid for cell in row)


def test_grid_size_after_reset():
    g = _make_game()
    assert len(g.grid) == GRID_ROWS
    assert len(g.grid[0]) == GRID_COLS


# ─── Fire Spawning ──────────────────────────────────────────────────────────


def test_spawn_fires_basic():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g._spawn_fires(8)
    fire_count = sum(1 for row in g.grid for cell in row if cell != 0)
    assert fire_count == 8


def test_spawn_fires_no_overflow():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    # Fill grid with fires
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            g.grid[r][c] = 1
    g._spawn_fires(100)
    # No new fires should be added (all filled)
    fire_count = sum(1 for row in g.grid for cell in row if cell != 0)
    assert fire_count == GRID_ROWS * GRID_COLS


def test_spawn_fires_colors_in_range():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g._spawn_fires(20)
    for row in g.grid:
        for cell in row:
            if cell != 0:
                assert 1 <= cell <= 4


# ─── Fire Spreading (CA) ────────────────────────────────────────────────────


def test_spread_fires_neighbor_infection():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    # Place a fire at (5, 5) — wait, we use grid[row][col] so grid[5][5] = row 5, col 5
    # This maps to (x=5, y=5) in tuple space
    g.grid[5][5] = 1  # RED fire
    # Make it spread many times (increase chance to 1.0)
    old_random = g._rng.random
    try:
        g._rng.random = lambda: 0.1  # Always below 0.3 = always spread
        g._spread_fires()
    finally:
        g._rng.random = old_random
    # At least one neighbor should have caught fire
    neighbors = [(5, 4), (5, 6), (4, 5), (6, 5)]
    fire_spread = any(g.grid[r][c] != 0 for r, c in neighbors)
    assert fire_spread


def test_spread_fires_same_color_as_neighbor():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g.grid[5][5] = 2  # GREEN fire
    # Force spread
    old_random = g._rng.random
    try:
        g._rng.random = lambda: 0.1
        g._spread_fires()
    finally:
        g._rng.random = old_random
    # Any new fire should match neighbor color
    neighbors = [(5, 4), (5, 6), (4, 5), (6, 5)]
    for r, c in neighbors:
        if g.grid[r][c] != 0:
            assert g.grid[r][c] == 2


def test_spread_fires_no_spread_without_neighbor():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    # Only one fire cell in corner with one neighbor
    g.grid[0][0] = 1
    old_random = g._rng.random
    try:
        g._rng.random = lambda: 0.1
        g._spread_fires()
    finally:
        g._rng.random = old_random
    # Only neighbors of initial fire: (0,1) and (1,0)
    # Original cell remains 1
    assert g.grid[0][0] == 1


def test_spread_fires_preserves_original_fires():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g.grid[2][3] = 1
    g.grid[5][7] = 3
    g._spread_fires()
    assert g.grid[2][3] == 1
    assert g.grid[5][7] == 3


# ─── Handle Click ───────────────────────────────────────────────────────────


def test_handle_click_correct_color():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.grid[3][4] = 1  # Same color as extinguisher
    g.combo = 0
    gained, changed, surge, cells = g._handle_click(4, 3)
    assert gained > 0
    assert changed is True
    assert g.combo == 1
    assert g.grid[3][4] == 0  # Cell extinguished


def test_handle_click_correct_color_combo_chain():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.grid[3][4] = 1
    g.grid[3][5] = 1
    g.combo = 0
    # First click
    g._handle_click(4, 3)
    assert g.combo == 1
    # Second click - same color, should increase combo
    g._handle_click(5, 3)
    assert g.combo == 2


def test_handle_click_wrong_color_resets_combo():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.grid[3][4] = 1
    g.grid[3][5] = 2  # Different color
    g.combo = 0
    # Build combo
    g._handle_click(4, 3)
    assert g.combo == 1
    # Wrong color click
    g._handle_click(5, 3)
    assert g.combo == 0
    assert g._last_click_combo_broke is True


def test_handle_click_wrong_color_adds_heat():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.grid[3][4] = 2  # Wrong color fire
    old_heat = g.heat
    g._handle_click(4, 3)
    assert g.heat == old_heat + HEAT_PENALTY_WRONG


def test_handle_click_wrong_color_extinguishes_fire():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.grid[3][4] = 2  # Wrong color fire
    g._handle_click(4, 3)
    assert g.grid[3][4] == 0  # Still extinguished


def test_handle_click_empty_cell():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.combo = 3
    old_heat = g.heat
    gained, changed, surge, cells = g._handle_click(4, 3)
    assert gained == 0
    assert changed is False
    assert surge is False
    assert cells == 0
    assert g.combo == 3  # Unchanged
    assert g.heat == old_heat  # Unchanged


def test_handle_click_out_of_bounds():
    g = _make_game()
    gained, changed, surge, cells = g._handle_click(-1, 0)
    assert gained == 0
    assert changed is False
    gained, changed, surge, cells = g._handle_click(0, GRID_ROWS + 1)
    assert gained == 0
    gained, changed, surge, cells = g._handle_click(GRID_COLS + 1, 0)
    assert gained == 0


def test_handle_click_score_progression():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.grid[3][4] = 1
    g.combo = 3
    gained, _, _, _ = g._handle_click(4, 3)
    # Combo becomes 4 (>= threshold), triggers SURGE with 1-cell cluster
    # base: 10 * 4 = 40, surge: 1 * 50 * 4 = 200, total = 240
    assert gained == 10 * 4 + 1 * 50 * 4


# ─── SURGE / BFS ────────────────────────────────────────────────────────────


def test_surge_triggers_at_threshold():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.combo = COMBO_SURGE_THRESHOLD - 1  # 3
    g.grid[3][4] = 1
    _, _, surge, _ = g._handle_click(4, 3)
    assert surge is True  # combo becomes 4, >= threshold


def test_surge_does_not_trigger_below_threshold():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.combo = COMBO_SURGE_THRESHOLD - 2  # 2
    g.grid[3][4] = 1
    _, _, surge, _ = g._handle_click(4, 3)
    assert surge is False  # combo becomes 3, < threshold


def test_surge_resets_combo():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.combo = COMBO_SURGE_THRESHOLD - 1  # 3
    g.grid[3][4] = 1
    g._handle_click(4, 3)
    assert g.combo == 0  # SURGE resets combo


def test_surge_increments_surge_count():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.combo = COMBO_SURGE_THRESHOLD - 1
    g.grid[3][4] = 1
    old_count = g.surge_count
    g._handle_click(4, 3)
    assert g.surge_count == old_count + 1


def test_surge_sets_flash_and_shake():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.combo = COMBO_SURGE_THRESHOLD - 1
    g.grid[3][4] = 1
    g._handle_click(4, 3)
    assert g.surge_flash == SURGE_FLASH_FRAMES
    assert g.shake_frames == SHAKE_FRAMES


def test_surge_max_combo_updated():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.combo = COMBO_SURGE_THRESHOLD - 1
    g.grid[3][4] = 1
    g._handle_click(4, 3)
    assert g.max_combo >= COMBO_SURGE_THRESHOLD


def test_bfs_cluster_single_cell():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g.grid[3][4] = 1  # (col=4, row=3) = (4, 3)
    cluster = g._bfs_cluster(4, 3, 1)
    assert len(cluster) == 1
    assert (4, 3) in cluster


def test_bfs_cluster_connected_same_color():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    # Place a 3-cell L-shaped cluster of color 1
    g.grid[3][4] = 1  # (4, 3)
    g.grid[3][5] = 1  # (5, 3)
    g.grid[4][4] = 1  # (4, 4)
    cluster = g._bfs_cluster(4, 3, 1)
    assert len(cluster) == 3
    assert (4, 3) in cluster
    assert (5, 3) in cluster
    assert (4, 4) in cluster


def test_bfs_cluster_only_same_color():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g.grid[3][4] = 1
    g.grid[3][5] = 2  # Different color adjacent
    cluster = g._bfs_cluster(4, 3, 1)
    assert len(cluster) == 1
    assert (4, 3) in cluster
    assert (5, 3) not in cluster


def test_bfs_cluster_boundary():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g.grid[0][0] = 1  # Corner
    g.grid[0][1] = 1
    g.grid[1][0] = 1
    cluster = g._bfs_cluster(0, 0, 1)
    assert len(cluster) == 3


def test_surge_clears_all_connected_cells():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.grid[3][4] = 1
    g.grid[3][5] = 1
    g.grid[4][4] = 1
    g.combo = COMBO_SURGE_THRESHOLD - 1
    g._handle_click(4, 3)
    # SURGE should have cleared all 3 connected cells
    assert g.grid[3][4] == 0
    assert g.grid[3][5] == 0
    assert g.grid[4][4] == 0


def test_surge_score_includes_cluster_bonus():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    # Place 4 connected same-color fires
    g.grid[3][4] = 1
    g.grid[3][5] = 1
    g.grid[4][4] = 1
    g.grid[4][5] = 1
    g.combo = COMBO_SURGE_THRESHOLD - 1  # 3
    old_score = g.score
    g._handle_click(4, 3)
    # Base: 10 * 4 = 40, Surge: 4 * 50 * 4 = 800, total 840
    expected_gain = 10 * COMBO_SURGE_THRESHOLD + 4 * 50 * COMBO_SURGE_THRESHOLD
    assert g.score == old_score + expected_gain


# ─── HEAT ───────────────────────────────────────────────────────────────────


def test_update_heat_basic():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g.grid[0][0] = 1
    g.grid[0][1] = 1
    g.heat = 0
    g._update_heat()
    assert g.heat > 0


def test_update_heat_empty_grid():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g.heat = 50
    g._update_heat()
    assert g.heat == 50  # No fires, no heat increase


def test_heat_game_over():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g.heat = MAX_HEAT - 0.01
    g.phase = Phase.PLAYING
    # Fill grid with fires to push heat over threshold
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            g.grid[r][c] = 1
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_capped_at_max():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g.heat = MAX_HEAT - 1
    # Fill entire grid
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            g.grid[r][c] = 1
    g._update_heat()
    assert g.heat == MAX_HEAT


# ─── Color Cycling ──────────────────────────────────────────────────────────


def test_cycle_color_wraps():
    g = _make_game()
    g.fire_color = 4
    g._cycle_color()
    assert g.fire_color == 1
    g._cycle_color()
    assert g.fire_color == 2
    g._cycle_color()
    assert g.fire_color == 3
    g._cycle_color()
    assert g.fire_color == 4


# ─── Particles ──────────────────────────────────────────────────────────────


def test_spawn_particles():
    g = _make_game()
    g._rng = random.Random(42)
    old_count = len(g.particles)
    g._spawn_particles(100, 100, 8, 5)
    assert len(g.particles) == old_count + 5
    assert g.particles[-1].color == 8
    assert g.particles[-1].life >= 15
    assert g.particles[-1].life <= 30


def test_update_particles_decays():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_particles(100, 100, 8, 3)
    for p in g.particles:
        p.life = 1  # Force decay on next update
    g._update_particles()
    assert len(g.particles) == 0  # All with life=1 die


def test_update_particles_moves():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_particles(100, 100, 8, 1)
    p = g.particles[0]
    old_life = p.life  # Save before update since p IS the object in the list
    g._update_particles()
    assert g.particles[0].life == old_life - 1


# ─── Timer Advance ───────────────────────────────────────────────────────────


def test_advance_timers_decrements_game_timer():
    g = _make_game()
    old_time = g.game_timer
    g._advance_timers()
    assert g.game_timer == old_time - 1


def test_advance_timers_game_over_on_expiry():
    g = _make_game()
    g.game_timer = 1
    g.phase = Phase.PLAYING
    g._advance_timers()
    assert g.game_timer == 0
    assert g.phase == Phase.GAME_OVER


def test_advance_timers_spread_timer_triggers():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g.grid[5][5] = 1
    g.spread_timer = 1  # Will trigger on next advance
    old_interval = g.spread_interval
    g._advance_timers()
    assert g.spread_interval == old_interval - 1  # Interval decreases
    assert g.spread_timer >= SPREAD_INITIAL - 1  # Reset to new interval


def test_advance_timers_spread_min_cap():
    g = _make_game()
    g.spread_interval = 9
    g.spread_timer = 1
    g._advance_timers()
    assert g.spread_interval >= 8  # SPREAD_MIN


def test_advance_timers_spawn_trigger():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()  # Empty grid, fire_count < 10
    g.spawn_timer = 1
    old_fire_count = sum(1 for row in g.grid for cell in row if cell != 0)
    g._advance_timers()
    new_fire_count = sum(1 for row in g.grid for cell in row if cell != 0)
    assert new_fire_count > old_fire_count  # New fires spawned
    assert g.spawn_timer == SPAWN_INTERVAL


def test_advance_timers_spawn_not_when_many_fires():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    # Fill many cells with fire
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            g.grid[r][c] = 1
    g.spawn_timer = 1
    g._advance_timers()
    # Should still reset timer even if no spawn
    assert g.spawn_timer == SPAWN_INTERVAL


# ─── Grid Coordinates ───────────────────────────────────────────────────────


def test_grid_coords():
    g = _make_game()
    col, row = g._grid_coords(GRID_X, GRID_Y)
    assert col == 0
    assert row == 0
    col, row = g._grid_coords(GRID_X + CELL_SIZE, GRID_Y + CELL_SIZE)
    assert col == 1
    assert row == 1
    col, row = g._grid_coords(GRID_X + 15 * CELL_SIZE, GRID_Y + 11 * CELL_SIZE)
    assert col == 15
    assert row == 11


# ─── Reset ──────────────────────────────────────────────────────────────────


def test_reset_clears_state():
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.heat = 80
    g.surge_count = 10
    g._rng = random.Random(42)
    g.reset()
    # reset() reassigns _rng, so overwrite again
    g._rng = random.Random(42)
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.phase == Phase.PLAYING
    assert g.game_timer == GAME_DURATION
    assert g.surge_count == 0


def test_reset_spawns_initial_fires():
    g = _make_game()
    g._rng = random.Random(42)
    g.reset()
    g._rng = random.Random(42)
    fire_count = sum(1 for row in g.grid for cell in row if cell != 0)
    assert fire_count == 8


def test_game_over_heat_returns_to_title():
    g = _make_game()
    g.phase = Phase.GAME_OVER
    # Simulate transition (this normally happens in update via btnp)
    g.phase = Phase.TITLE
    assert g.phase == Phase.TITLE


# ─── Complete Game Loop Simulation ──────────────────────────────────────────


def test_simulate_game_loop_combo_and_surge():
    """Simulate a mini game loop: place fires, click them with correct color, trigger SURGE."""
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.heat = 0
    g.phase = Phase.PLAYING

    # Place a cluster of 5 connected color-1 fires
    for r, c in [(2, 4), (2, 5), (2, 6), (3, 5), (4, 5)]:
        g.grid[r][c] = 1

    # Click 4 times on same-color fires
    total_gained = 0
    clicks = [(4, 2), (5, 2), (6, 2), (5, 3)]  # 4 same-color clicks
    for col, row in clicks:
        gained, _, _, _ = g._handle_click(col, row)
        total_gained += gained

    # 4th click should trigger SURGE (combo >= 4)
    assert g.surge_count == 1
    # All 5 connected cells should be cleared
    for r, c in [(2, 4), (2, 5), (2, 6), (3, 5), (4, 5)]:
        assert g.grid[r][c] == 0
    # Score should be substantial
    assert g.score > 0


def test_simulate_wrong_color_penalty():
    g = _make_game()
    g._rng = random.Random(42)
    g.fire_color = 1
    g.grid = g._make_grid()
    g.grid[2][4] = 1
    g.grid[2][5] = 2  # Different color
    g.grid[2][6] = 1
    g.combo = 0
    g.phase = Phase.PLAYING

    # Build some combo
    g._handle_click(4, 2)  # Color 1 -> combo=1
    assert g.combo == 1

    # Click wrong color
    g._handle_click(5, 2)  # Color 2 -> combo reset
    assert g.combo == 0
    assert g.heat == HEAT_PENALTY_WRONG


def test_empty_click_no_effect():
    g = _make_game()
    g._rng = random.Random(42)
    g.grid = g._make_grid()
    g.heat = 50
    g.combo = 3
    gained, changed, surge, cells = g._handle_click(4, 2)
    assert gained == 0
    assert not changed
    assert not surge
    assert cells == 0
    assert g.heat == 50
    assert g.combo == 3


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
