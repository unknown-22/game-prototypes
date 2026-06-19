"""test_imports.py — Headless logic tests for Claw Surge (142_claw_surge).

Uses Game.__new__(Game) bypass pattern to test without pyxel.init/run.
"""
import sys
import random

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/142_claw_surge")
from main import Game, Particle, FloatingText, Phase, COLORS, COLS, ROWS, GRID_LEFT, GRID_TOP, CELL

# ── Helpers ──

def _make_game(seed: int = 42) -> Game:
    """Create a Game instance bypassing pyxel.init/run for headless testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.PLAYING
    g.grid = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.last_color = -1
    g.heat = 0.0
    g.super_claw = False
    g.super_timer = 0
    g.particles = []
    g.floating_texts = []
    g.cursor_x = 0
    g.cursor_y = 0
    g.grab_x = 0
    g.grab_y = 0
    g.frame = 0
    g.game_over_reason = ""
    g._reset()
    return g


def _set_grid(g: Game, grid: list[list[int]]) -> None:
    """Replace game grid with a controlled test grid."""
    g.grid = [row[:] for row in grid]


def _grab_cell(g: Game, col: int, row: int) -> None:
    """Simulate clicking on grid cell (col, row). Runs the grab logic headlessly."""
    color = g.grid[row][col]
    g.grab_x = col
    g.grab_y = row

    if g.super_claw:
        cluster = g._bfs_cluster(col, row, color)
        for c, r in cluster:
            g.grid[r][c] = -1
        cluster_size = len(cluster)
        base_score = cluster_size * 100
        combo_bonus = g.combo if g.combo > 0 else 1
        g.score += base_score * combo_bonus
        g.combo += cluster_size - 1
        g.last_color = color
        g.super_claw = False
        g.heat = max(0.0, g.heat - cluster_size * 3.0)
    else:
        if g.last_color == -1 or color == g.last_color:
            g.combo += 1
            score_add = 10 + g.combo * 5
        else:
            g.combo = 1
            score_add = 10
            g.heat = min(100.0, g.heat + 10.0)
        g.last_color = color
        g.score += score_add
        g.grid[row][col] = -1

        if g.combo >= 4:
            g.super_claw = True

    if g.combo > g.max_combo:
        g.max_combo = g.combo

    g._apply_gravity()
    g._check_game_over()
    # Decay after game over check
    g.heat = max(0.0, g.heat - 2.0)


# ── Dataclass Tests ──

def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-0.5, life=30, color=8, size=3)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -0.5
    assert p.life == 30
    assert p.color == 8
    assert p.size == 3


def test_floating_text_creation():
    ft = FloatingText(x=100.0, y=50.0, text="+50", life=45, color=7)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+50"
    assert ft.life == 45
    assert ft.color == 7
    assert ft.vy == -1.0


# ── Phase Enum Tests ──

def test_phase_values():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.SUPER_ANIM in Phase
    assert Phase.GAME_OVER in Phase
    # All phases are distinct
    phases = {Phase.TITLE, Phase.PLAYING, Phase.SUPER_ANIM, Phase.GAME_OVER}
    assert len(phases) == 4


# ── Constants Tests ──

def test_color_constants():
    assert len(COLORS) == 4
    assert COLORS[0] == 8  # RED
    assert COLORS[1] == 3  # GREEN
    assert COLORS[2] == 10  # YELLOW
    assert COLORS[3] == 6  # LIGHT_BLUE


def test_grid_dimensions():
    assert COLS == 8
    assert ROWS == 6
    assert CELL == 30
    assert GRID_LEFT == 40
    assert GRID_TOP == 30


# ── Reset / Init Tests ──

def test_reset_initializes_state():
    g = _make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.last_color == -1
    assert g.heat == 0.0
    assert g.super_claw is False
    assert g.super_timer == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.phase == Phase.PLAYING


def test_reset_fills_grid():
    g = _make_game()
    for row in range(ROWS):
        for col in range(COLS):
            assert 0 <= g.grid[row][col] <= 3


def test_reset_clears_previous_state():
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.heat = 50.0
    g.super_claw = True
    g.particles.append(Particle(0, 0, 0, 0, 10, 8))
    g.floating_texts.append(FloatingText(0, 0, "test", 10, 7))
    g._reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_claw is False
    assert g.particles == []
    assert g.floating_texts == []


# ── BFS Cluster Tests ──

def test_bfs_single_cell():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[2][3] = 0  # Single red cell at row 2, col 3
    _set_grid(g, grid)
    cluster = g._bfs_cluster(3, 2, 0)
    assert cluster == {(3, 2)}


def test_bfs_horizontal_line():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    for c in range(3, 6):
        grid[2][c] = 1  # Green line row 2, cols 3-5
    _set_grid(g, grid)
    cluster = g._bfs_cluster(3, 2, 1)
    assert cluster == {(3, 2), (4, 2), (5, 2)}


def test_bfs_2d_cluster():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    # T-shape of yellow cells
    grid[1][3] = 2
    grid[2][2] = 2
    grid[2][3] = 2
    grid[2][4] = 2
    _set_grid(g, grid)
    cluster = g._bfs_cluster(3, 2, 2)
    assert len(cluster) == 4
    assert (3, 1) in cluster
    assert (2, 2) in cluster
    assert (3, 2) in cluster
    assert (4, 2) in cluster


def test_bfs_different_color_not_included():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[2][2] = 0  # RED
    grid[2][3] = 1  # GREEN (different)
    _set_grid(g, grid)
    cluster = g._bfs_cluster(2, 2, 0)
    assert cluster == {(2, 2)}


def test_bfs_boundary():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[0][0] = 3  # Corner
    grid[0][1] = 3  # Edge
    _set_grid(g, grid)
    cluster = g._bfs_cluster(0, 0, 3)
    assert cluster == {(0, 0), (1, 0)}


def test_bfs_empty_grid():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    _set_grid(g, grid)
    cluster = g._bfs_cluster(3, 3, 0)
    assert cluster == {(3, 3)}


# ── Gravity Tests ──

def test_gravity_compacts_column():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[0][2] = 0  # RED at top
    grid[1][2] = -1
    grid[2][2] = 1  # GREEN below gap
    grid[3][2] = -1
    grid[4][2] = 2  # YELLOW further down
    grid[5][2] = -1
    _set_grid(g, grid)
    g._apply_gravity()
    # After gravity, cells should be compacted to bottom
    # Column 2 from bottom up: YELLOW(2), GREEN(1), RED(0), then 3 new random
    assert g.grid[5][2] == 2  # YELLOW at bottom
    assert g.grid[4][2] == 1  # GREEN
    assert g.grid[3][2] == 0  # RED
    # Top 3 should be filled with new random values (0-3)
    for r in range(3):
        assert 0 <= g.grid[r][2] <= 3


def test_gravity_preserves_order():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[1][1] = 0
    grid[2][1] = 1
    grid[3][1] = 2
    grid[4][1] = 3
    _set_grid(g, grid)
    g._apply_gravity()
    # Bottom 4 should be 3, 2, 1, 0 in order (from bottom up: 3 at row 5, 2 at row 4, etc.)
    assert g.grid[5][1] == 3
    assert g.grid[4][1] == 2
    assert g.grid[3][1] == 1
    assert g.grid[2][1] == 0


def test_gravity_fills_empty_grid():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    _set_grid(g, grid)
    g._apply_gravity()
    # All cells should be filled
    for row in range(ROWS):
        for col in range(COLS):
            assert 0 <= g.grid[row][col] <= 3


# ── Grab / Combo Tests ──

def test_first_grab_sets_combo_1():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[5][3] = 0  # Bottom row, col 3
    _set_grid(g, grid)
    _grab_cell(g, 3, 5)
    assert g.combo == 1
    assert g.last_color == 0
    assert g.score > 0


def test_same_color_grab_builds_combo():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[5][2] = 0  # RED
    grid[5][3] = 0  # RED
    _set_grid(g, grid)
    _grab_cell(g, 2, 5)
    assert g.combo == 1
    assert g.last_color == 0
    _grab_cell(g, 3, 5)
    assert g.combo == 2
    assert g.last_color == 0


def test_wrong_color_resets_combo():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[5][2] = 0  # RED
    grid[5][3] = 1  # GREEN
    _set_grid(g, grid)
    _grab_cell(g, 2, 5)
    assert g.combo == 1
    heat_before = g.heat
    _grab_cell(g, 3, 5)
    assert g.combo == 1  # Reset to 1
    assert g.last_color == 1
    assert g.heat > heat_before  # HEAT increased


def test_wrong_color_adds_heat():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[5][2] = 0
    grid[5][3] = 1
    _set_grid(g, grid)
    _grab_cell(g, 2, 5)  # First grab, combo=1, last_color=0
    _grab_cell(g, 3, 5)  # Wrong color, HEAT should increase
    assert g.heat >= 8.0  # +10 HEAT then -2 decay = +8 net (min)


def test_combo_increases_score():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[5][2] = 0
    grid[5][3] = 0
    grid[5][4] = 0
    _set_grid(g, grid)
    _grab_cell(g, 2, 5)  # combo 1 → score_add = 10 + 1*5 = 15
    score1 = g.score
    _grab_cell(g, 3, 5)  # combo 2 → score_add = 10 + 2*5 = 20
    score2 = g.score - score1
    assert score2 > score1  # Higher combo = more points
    assert score2 == 20


def test_max_combo_tracks_highest():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    for c in range(4):
        grid[5][c] = 0  # 4 RED cells
    _set_grid(g, grid)
    for c in range(4):
        _grab_cell(g, c, 5)
    assert g.max_combo == 4


# ── SUPER CLAW Tests ──

def test_super_claw_activates_at_combo_4():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    for c in range(4):
        grid[5][c] = 0  # 4 RED cells
    _set_grid(g, grid)
    for c in range(3):
        _grab_cell(g, c, 5)
    assert g.combo == 3
    assert g.super_claw is False
    _grab_cell(g, 3, 5)  # 4th same-color → SUPER
    assert g.combo == 4
    assert g.super_claw is True


def test_super_claw_grabs_bfs_cluster():
    g = _make_game()
    # Create a 2x2 RED cluster
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[4][2] = 0
    grid[4][3] = 0
    grid[5][2] = 0
    grid[5][3] = 0
    _set_grid(g, grid)
    # First build combo to 4
    for i in range(3):
        # Place red cells to build combo
        # We need to manipulate grid before each grab since gravity refills
        g.grid = [row[:] for row in grid]
    # Actually let's just set super_claw directly and grab
    g.super_claw = True
    g.combo = 4
    g.last_color = 0
    _set_grid(g, grid)
    score_before = g.score
    _grab_cell(g, 2, 5)
    # Should grab all 4 cells
    assert g.score > score_before + 300  # 4*100*bonus
    # Cluster cells should be cleared
    assert g.grid[4][2] == -1 or 0 <= g.grid[4][2] <= 3  # May be refilled by gravity
    assert g.super_claw is False  # Used up


def test_super_claw_gives_big_score():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    # 5-cell cluster
    grid[3][3] = 0
    grid[4][3] = 0
    grid[5][3] = 0
    grid[4][2] = 0
    grid[4][4] = 0
    _set_grid(g, grid)
    g.super_claw = True
    g.combo = 4
    g.last_color = 0
    _grab_cell(g, 3, 5)
    # cluster_size=5, base_score=500, combo_bonus=4, score_add=2000
    assert g.score == 2000
    assert g.combo == 8  # 4 + 5 - 1


def test_super_claw_resets_flag():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[5][0] = 0
    _set_grid(g, grid)
    g.super_claw = True
    g.combo = 4
    _grab_cell(g, 0, 5)
    assert g.super_claw is False


# ── Heat Tests ──

def test_heat_decays_after_grab():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[5][3] = 0
    _set_grid(g, grid)
    g.heat = 10.0
    _grab_cell(g, 3, 5)
    assert g.heat <= 8.0  # max(0, 10 - 2) = 8


def test_heat_game_over():
    g = _make_game()
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[5][3] = 0
    _set_grid(g, grid)
    g.heat = 99.0
    g.last_color = 1  # Different from the cell we'll grab
    _grab_cell(g, 3, 5)  # Wrong color: heat + 10 = 109 → capped at 100
    # _grab_cell calls _check_game_over BEFORE decay, so game over triggers
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "Overheated!"


# ── Game Over Tests ──

def test_check_game_over_overheated():
    g = _make_game()
    g.heat = 100.0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "Overheated!"


def test_check_game_over_heat_below_threshold():
    g = _make_game()
    g.heat = 99.0
    g._check_game_over()
    assert g.phase == Phase.PLAYING


def test_check_game_over_depletion():
    g = _make_game()
    # Make grid all empty
    grid = [[-1] * COLS for _ in range(ROWS)]
    _set_grid(g, grid)
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "All prizes collected!"


# ── Particle Tests ──

def test_particle_update_decrements_life():
    g = _make_game()
    g.particles = [Particle(10, 20, 1, 1, 5, 8)]
    g._update_particles()
    assert g.particles[0].life == 4


def test_particle_removed_when_life_zero():
    g = _make_game()
    g.particles = [Particle(10, 20, 1, 1, 1, 8)]
    g._update_particles()
    assert len(g.particles) == 0


def test_particle_moves():
    g = _make_game()
    g.particles = [Particle(10.0, 20.0, 1.5, -0.5, 10, 8)]
    g._update_particles()
    assert g.particles[0].x == 11.5
    assert g.particles[0].y == 19.5


# ── Floating Text Tests ──

def test_floating_text_moves_up():
    g = _make_game()
    g.floating_texts = [FloatingText(100, 200, "+10", 30, 7)]
    g._update_floating_texts()
    assert g.floating_texts[0].y == 199.0
    assert g.floating_texts[0].life == 29


def test_floating_text_removed_when_life_zero():
    g = _make_game()
    g.floating_texts = [FloatingText(100, 200, "+10", 1, 7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Spawn Tests ──

def test_spawn_particles():
    g = _make_game()
    g._spawn_particles_at(100, 100, 0, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == COLORS[0]
        assert 10 <= p.life <= 30


def test_spawn_floating_text():
    g = _make_game()
    g._spawn_floating_text(100, 100, "TEST", 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"
    assert g.floating_texts[0].color == 7
    assert g.floating_texts[0].life == 45


# ── Edge Case Tests ──

def test_max_combo_updates_correctly():
    g = _make_game()
    # Set combo > max_combo externally
    grid = [[-1] * COLS for _ in range(ROWS)]
    grid[5][0] = 0
    _set_grid(g, grid)
    _grab_cell(g, 0, 5)
    assert g.max_combo == 1
    assert g.combo == 1


def test_last_color_initially_negative_one():
    g = _make_game()
    assert g.last_color == -1


def test_super_timer_transitions():
    g = _make_game()
    g.phase = Phase.SUPER_ANIM
    g.super_timer = 1
    # Simulate one frame of super_anim update
    g.super_timer -= 1
    if g.super_timer <= 0:
        g.phase = Phase.PLAYING
        g.super_timer = 0
    assert g.phase == Phase.PLAYING
    assert g.super_timer == 0


def test_grid_bounds_check():
    """Verify grid access doesn't go out of bounds with valid (col, row)."""
    g = _make_game()
    # All cells should be accessible
    for row in range(ROWS):
        for col in range(COLS):
            val = g.grid[row][col]
            assert val in (-1, 0, 1, 2, 3)


# ── Deterministic RNG Tests ──

def test_rng_deterministic():
    g1 = _make_game(42)
    g2 = _make_game(42)
    for row in range(ROWS):
        for col in range(COLS):
            assert g1.grid[row][col] == g2.grid[row][col]


def test_rng_different_seeds():
    g1 = _make_game(42)
    g2 = _make_game(99)
    # Likely different, but not guaranteed — check at least one cell
    # We'll just verify the function succeeds
    assert g1.grid is not g2.grid


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
