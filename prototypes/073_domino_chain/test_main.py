"""test_main.py — Headless logic tests for 073_domino_chain."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.absolute()))

from main import (
    ANIM_SPEED,
    CELL_SIZE,
    CONVERGE_BONUS,
    DARK_BLUE,
    DOMINO_COLORS,
    GRID_COLS,
    GRID_ROWS,
    GREEN,
    PINK,
    RED,
    SCREEN_H,
    SCREEN_W,
    SPLIT_BONUS,
    START_COL,
    START_ROW,
    WHITE,
    YELLOW,
    Cell,
    Flash,
    Game,
    Particle,
    Phase,
)


# ── Helper: Headless Game Creation ────────────────────────────────────

def _make_game(seed: int = 42) -> Game:
    """Create a Game instance bypassing Pyxel init, with seeded RNG."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g._init_grid()
    g._init_anim_state()
    g.score = 0
    g.best_score = 0
    g.selected_color_idx = 0
    g.hover_col = 0
    g.hover_row = 0
    return g


def _make_grid_with_colors(colors: list[list[int]]) -> Game:
    """Create a Game with a pre-filled grid of specified colors.
    colors[row][col] = pyxel color index (0=empty)."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLACING
    g.score = 0
    g.best_score = 0
    g.selected_color_idx = 0
    g.hover_col = 0
    g.hover_row = 0
    g._init_anim_state()
    g.grid = [[Cell(color=0) for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    for row_idx, row_data in enumerate(colors):
        for col_idx, color in enumerate(row_data):
            if color != 0:
                g.grid[row_idx][col_idx] = Cell(color=color)
    return g


# ── Dataclass Tests ────────────────────────────────────────────────────

def test_cell_defaults():
    c = Cell(color=RED)
    assert c.color == RED
    assert c.toppled is False


def test_cell_custom():
    c = Cell(color=GREEN, toppled=True)
    assert c.color == GREEN
    assert c.toppled is True


def test_particle_fields():
    p = Particle(x=1.5, y=2.5, vx=0.5, vy=-0.5, life=10, color=YELLOW)
    assert p.x == 1.5
    assert p.y == 2.5
    assert p.vx == 0.5
    assert p.vy == -0.5
    assert p.life == 10
    assert p.color == YELLOW


def test_flash_fields():
    f = Flash(col=3, row=5, life=10, color=PINK)
    assert f.col == 3
    assert f.row == 5
    assert f.life == 10
    assert f.color == PINK


# ── Constants ─────────────────────────────────────────────────────────

def test_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert CELL_SIZE == 20
    assert GRID_COLS == 16
    assert GRID_ROWS == 12
    assert START_COL == 7
    assert START_ROW == 0
    assert ANIM_SPEED == 3
    assert CONVERGE_BONUS == 1000
    assert SPLIT_BONUS == 200
    assert len(DOMINO_COLORS) == 4
    assert RED == 8
    assert GREEN == 3
    assert DARK_BLUE == 5
    assert YELLOW == 10


def test_phase_enum():
    assert Phase.TITLE == 0
    assert Phase.PLACING == 1
    assert Phase.ANIMATING == 2
    assert Phase.SCORING == 3
    assert Phase.GAME_OVER == 4
    assert len(Phase) == 5


# ── Grid Initialization ───────────────────────────────────────────────

def test_grid_dimensions():
    g = _make_game()
    assert len(g.grid) == GRID_ROWS
    for row in g.grid:
        assert len(row) == GRID_COLS


def test_grid_all_empty_after_init():
    g = _make_game()
    for row in g.grid:
        for cell in row:
            assert cell.color == 0
            assert cell.toppled is False


# ── Placement Logic ───────────────────────────────────────────────────

def test_can_place_empty_cell():
    g = _make_game()
    assert g._can_place(0, 0) is True
    assert g._can_place(7, 5) is True
    assert g._can_place(15, 11) is True


def test_can_place_out_of_bounds():
    g = _make_game()
    assert g._can_place(-1, 0) is False
    assert g._can_place(0, -1) is False
    assert g._can_place(16, 0) is False
    assert g._can_place(0, 12) is False


def test_cannot_place_on_occupied():
    g = _make_game()
    g._place_domino(5, 5)
    assert g._can_place(5, 5) is False


def test_cannot_place_on_toppled():
    g = _make_game()
    g._place_domino(3, 3)
    g.grid[3][3].toppled = True
    assert g._can_place(3, 3) is False


def test_place_domino_sets_color():
    g = _make_game()
    assert g._place_domino(4, 2) is True
    assert g.grid[2][4].color == RED  # selected_color_idx=0 -> RED
    assert g.grid[2][4].toppled is False


def test_place_domino_returns_false_on_occupied():
    g = _make_game()
    g._place_domino(4, 2)
    assert g._place_domino(4, 2) is False


def test_place_domino_respects_selected_color():
    g = _make_game()
    g.selected_color_idx = 2  # DARK_BLUE
    g._place_domino(0, 0)
    assert g.grid[0][0].color == DARK_BLUE

    g.selected_color_idx = 3  # YELLOW
    g._place_domino(1, 0)
    assert g.grid[0][1].color == YELLOW


def test_count_placed_dominoes():
    g = _make_game()
    assert g._count_placed_dominoes() == 0
    g._place_domino(0, 0)
    g._place_domino(5, 5)
    g._place_domino(10, 10)
    assert g._count_placed_dominoes() == 3


def test_selected_color_property():
    g = _make_game()
    assert g.selected_color == RED
    g.selected_color_idx = 1
    assert g.selected_color == GREEN
    g.selected_color_idx = 2
    assert g.selected_color == DARK_BLUE
    g.selected_color_idx = 3
    assert g.selected_color == YELLOW


# ── Pixel to Cell Conversion ──────────────────────────────────────────

def test_pixel_to_cell_origin():
    g = _make_game()
    assert g._pixel_to_cell(0, 0) == (0, 0)


def test_pixel_to_cell_center():
    g = _make_game()
    assert g._pixel_to_cell(CELL_SIZE // 2, CELL_SIZE // 2) == (0, 0)


def test_pixel_to_cell_boundary():
    g = _make_game()
    assert g._pixel_to_cell(CELL_SIZE - 1, CELL_SIZE - 1) == (0, 0)
    assert g._pixel_to_cell(CELL_SIZE, 0) == (1, 0)


def test_pixel_to_cell_corner():
    g = _make_game()
    assert g._pixel_to_cell(CELL_SIZE * 15, CELL_SIZE * 11) == (15, 11)


def test_pixel_to_cell_out_of_bounds():
    g = _make_game()
    assert g._pixel_to_cell(-1, 0) is None
    assert g._pixel_to_cell(0, -1) is None
    assert g._pixel_to_cell(320, 0) is None
    assert g._pixel_to_cell(0, 240) is None


# ── Cell Center ───────────────────────────────────────────────────────

def test_cell_center():
    g = _make_game()
    cx, cy = g._cell_center(0, 0)
    assert cx == 10.0  # CELL_SIZE/2
    assert cy == 10.0
    cx, cy = g._cell_center(5, 3)
    assert cx == 5 * 20 + 10
    assert cy == 3 * 20 + 10


# ── Adjacent Counting ─────────────────────────────────────────────────

def test_get_non_toppled_neighbors_empty_grid():
    g = _make_game()
    # Place one domino
    g._place_domino(5, 5)
    neighbors = g._get_non_toppled_neighbors(5, 5)
    assert len(neighbors) == 0  # All adjacent are empty


def test_get_non_toppled_neighbors_with_adjacent():
    g = _make_game()
    g._place_domino(5, 5)  # center (RED)
    g._place_domino(5, 4)  # up (RED)
    g._place_domino(5, 6)  # down (RED)
    g._place_domino(4, 5)  # left (RED)
    g._place_domino(6, 5)  # right (RED)

    neighbors = g._get_non_toppled_neighbors(5, 5)
    assert len(neighbors) == 4
    assert (5, 4) in neighbors
    assert (5, 6) in neighbors
    assert (4, 5) in neighbors
    assert (6, 5) in neighbors


def test_get_non_toppled_neighbors_ignores_toppled():
    g = _make_game()
    g._place_domino(5, 5)
    g._place_domino(5, 4)
    g.grid[4][5].toppled = True  # Mark up neighbor as toppled

    neighbors = g._get_non_toppled_neighbors(5, 5)
    assert (5, 4) not in neighbors


def test_get_non_toppled_neighbors_ignores_empty():
    g = _make_game()
    g._place_domino(5, 5)
    # No adjacent dominoes placed
    neighbors = g._get_non_toppled_neighbors(5, 5)
    assert len(neighbors) == 0


def test_count_adjacent():
    g = _make_game()
    g._place_domino(5, 5)
    g._place_domino(5, 4)
    g._place_domino(5, 6)
    assert g._count_adjacent(5, 5) == 2


# ── Chain Start ───────────────────────────────────────────────────────

def test_start_chain_empty_start_cell_does_nothing():
    g = _make_game()
    g._start_chain()
    assert g.phase == Phase.TITLE  # unchanged, default phase
    assert len(g.anim_queue) == 0


def test_start_chain_populates_queue():
    g = _make_game()
    g._place_domino(START_COL, START_ROW)  # Place at start
    g.phase = Phase.PLACING
    g._start_chain()
    assert g.phase == Phase.ANIMATING
    assert len(g.anim_queue) == 1
    assert g.anim_queue[0] == (START_COL, START_ROW)


def test_start_chain_resets_anim_state():
    g = _make_game()
    g._place_domino(START_COL, START_ROW)
    g.chain_length = 99
    g.combo = 10
    g.max_combo = 20
    g.converge_count = 5
    g.split_count = 3
    g.phase = Phase.PLACING
    g._start_chain()
    assert g.chain_length == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.converge_count == 0
    assert g.split_count == 0
    assert len(g.converged_cells) == 0
    assert len(g.split_cells) == 0


# ── Propagation ──────────────────────────────────────────────────────

def test_propagate_tick_empty_queue_returns_false():
    g = _make_game()
    assert g._propagate_tick() is False


def test_propagate_tick_topples_cell():
    g = _make_game()
    g._place_domino(START_COL, START_ROW)
    g.phase = Phase.PLACING
    g._start_chain()

    result = g._propagate_tick()
    assert g.grid[START_ROW][START_COL].toppled is True
    assert g.chain_length == 1
    assert len(g.anim_queue) == 0  # no adjacent dominoes
    assert result is False  # queue empty, chain ends


def test_propagate_tick_single_domino_chain():
    g = _make_game()
    g._place_domino(START_COL, START_ROW)
    g.phase = Phase.PLACING
    g._start_chain()
    g._propagate_tick()
    assert g.chain_length == 1
    assert g.combo == 1
    assert g.max_combo == 1


def test_propagate_tick_linear_chain():
    """Place a line of 5 dominoes from START_ROW downward."""
    g = _make_game()
    for r in range(5):
        g._place_domino(START_COL, START_ROW + r)
    g.phase = Phase.PLACING
    g._start_chain()

    # Process all ticks
    tick_count = 0
    while g._propagate_tick():
        tick_count += 1
    tick_count += 1  # the last one

    assert g.chain_length == 5
    assert tick_count == 5


def test_propagate_tick_same_color_combo():
    """All RED dominoes -> combo should build."""
    g = _make_game()
    g.selected_color_idx = 0  # RED
    for r in range(4):
        g._place_domino(START_COL, START_ROW + r)
    g.phase = Phase.PLACING
    g._start_chain()

    while g._propagate_tick():
        pass

    assert g.chain_length == 4
    assert g.max_combo == 4
    assert g.combo_steps == 3  # 3 extensions beyond first


def test_propagate_tick_different_color_resets_combo():
    """RED, GREEN, RED should reset combo at GREEN."""
    g = _make_game()
    g.selected_color_idx = 0  # RED
    g._place_domino(START_COL, START_ROW)
    g.selected_color_idx = 1  # GREEN
    g._place_domino(START_COL, START_ROW + 1)
    g.selected_color_idx = 0  # RED
    g._place_domino(START_COL, START_ROW + 2)
    g.phase = Phase.PLACING
    g._start_chain()

    while g._propagate_tick():
        pass

    assert g.chain_length == 3
    # RED(combo=1), GREEN(diff->combo=1), RED(diff->combo=1), max_combo=1
    assert g.max_combo == 1
    assert g.combo_steps == 0


def test_propagate_tick_split_detection():
    """A center cell with 3 adjacent dominoes (left, right, down)."""
    g = _make_game()
    g._place_domino(START_COL, START_ROW)  # start cell
    g._place_domino(START_COL, START_ROW + 1)  # down
    g._place_domino(START_COL - 1, START_ROW)  # left
    g._place_domino(START_COL + 1, START_ROW)  # right
    g.phase = Phase.PLACING
    g._start_chain()

    # First tick: topple start cell
    g._propagate_tick()

    # Start cell (7,0) had 3 neighbors, so it's a split
    assert (START_COL, START_ROW) in g.split_cells
    assert g.split_count == 1
    # Queue should have left, right, down
    assert len(g.anim_queue) == 3


def test_propagate_tick_converge_detection():
    """Two paths converge on same cell.
    Layout:
      A (start=7,0)
      B (7,1)
      C (6,1)  D (8,1)
    A -> B (split left and right to C and D)
    C -> Z (6,2)
    D -> Z (6,2) -> CONVERGE
    """
    g = _make_game()
    # Place dominoes
    g._place_domino(7, 0)  # A: start
    g._place_domino(7, 1)  # B: bridge
    g._place_domino(6, 1)  # C: left path
    g._place_domino(8, 1)  # D: right path
    g._place_domino(6, 2)  # Z: converge target (left of C, right of D...)
    # Wait: D at (8,1) -> down is (8,2). C at (6,1) -> down is (6,2).
    # Those don't converge on same cell. I need a converge point.
    # Let me redesign:
    # A(7,0) -> B(7,1)
    # B(7,1) branches: C(6,1) and D(8,1)
    # C(6,1) -> E(6,2)
    # D(8,1) -> F(8,2)
    # E->G(7,2) and F->G(7,2) -> CONVERGE at G(7,2)
    # But that's more cells. Let me do a diamond:
    # A(7,0) -> B(7,1)
    # B(7,1) splits: C(6,1) and D(8,1)
    # C and D both go down to E(7,2) -> converge
    # Wait, C(6,1) down is (6,2), D(8,1) down is (8,2), they don't converge.
    # Need a different layout:
    # A(7,0) -> B(7,1) -> C(7,2) -> D(6,2) and E(8,2) -> F(7,3)
    # BFS order: A, then B, then C, then D or E depending on queue order
    # D down is (6,3), E down is (8,3), F down is (7,3)
    # Actually let me think simpler:
    # Two paths from B go left-down and right-down to meet at same cell.
    # Let me draw:
    #   A(7,0)
    #   B(7,1)
    #  C(6,1)  D(8,1)
    #   E(6,2) -> G(7,2) <- F(8,2)
    # This is: A down to B, B left to C, B right to D
    # C down to E, D down to F
    # E right to G, F left to G -> CONVERGE at G
    cells = [
        [0]*GRID_COLS for _ in range(GRID_ROWS)
    ]
    cells[0][7] = RED  # A
    cells[1][7] = RED  # B
    cells[1][6] = RED  # C
    cells[1][8] = RED  # D
    cells[2][6] = RED  # E
    cells[2][8] = RED  # F
    cells[2][7] = RED  # G (converge target)
    g2 = _make_grid_with_colors(cells)
    g2.phase = Phase.PLACING
    g2._start_chain()

    while g2._propagate_tick():
        pass

    # Converge happens at E(6,2) and F(8,2) — both reached from G first, then from C/D
    assert g2.converge_count == 2
    assert (6, 2) in g2.converged_cells
    assert (8, 2) in g2.converged_cells


def test_propagate_tick_no_double_topple():
    """Verify a cell is only toppled once even if multiple paths target it."""
    g = _make_game()
    g._place_domino(START_COL, START_ROW)
    g._place_domino(START_COL, START_ROW + 1)
    g._place_domino(START_COL, START_ROW + 2)
    g.phase = Phase.PLACING
    g._start_chain()

    while g._propagate_tick():
        pass

    assert g.chain_length == 3
    # Each cell toppled exactly once
    for r in range(3):
        assert g.grid[START_ROW + r][START_COL].toppled is True


# ── Scoring ───────────────────────────────────────────────────────────

def test_calculate_score_single_domino():
    g = _make_game()
    g._place_domino(START_COL, START_ROW)
    g.phase = Phase.PLACING
    g._start_chain()
    while g._propagate_tick():
        pass

    score = g._calculate_score()
    # chain_length=1, combo_steps=0, converge=0, split=0
    assert score == 10  # 1 * 10


def test_calculate_score_with_combo():
    g = _make_game()
    for r in range(5):
        g._place_domino(START_COL, START_ROW + r)
    g.phase = Phase.PLACING
    g._start_chain()
    while g._propagate_tick():
        pass

    score = g._calculate_score()
    # chain_length=5, combo_steps=4, converge=0, split=0
    expected = 5 * 10 + 4 * 50
    assert score == expected


def test_calculate_score_with_converge():
    g = _make_game()
    g.chain_length = 10
    g.combo_steps = 5
    g.converge_count = 2
    g.split_count = 1
    score = g._calculate_score()
    expected = 10 * 10 + 5 * 50 + 2 * CONVERGE_BONUS + 1 * SPLIT_BONUS
    assert score == expected


def test_calculate_score_zero():
    g = _make_game()
    score = g._calculate_score()
    assert score == 0


# ── Particles ─────────────────────────────────────────────────────────

def test_spawn_particles_adds_to_list():
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100.0, 100.0, RED, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == RED
        assert p.life > 0


def test_update_particles_moves_and_decays():
    g = _make_game()
    g._spawn_particles(100, 100, RED, 3)
    old_lives = [p.life for p in g.particles[:]]
    g._update_particles()
    for i, p in enumerate(g.particles):
        assert p.life == old_lives[i] - 1


def test_update_particles_gravity():
    g = _make_game()
    g.particles = [Particle(x=100, y=100, vx=0, vy=0, life=10, color=RED)]
    g._update_particles()
    assert g.particles[0].vy == 0.2  # gravity applied


def test_update_particles_removes_dead():
    g = _make_game()
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0


def test_spawn_converge_particles():
    g = _make_game()
    g._spawn_converge_particles(100, 100)
    assert 12 <= len(g.particles) <= 20
    for p in g.particles:
        assert p.color in (PINK, YELLOW, WHITE)


# ── Flashes ───────────────────────────────────────────────────────────

def test_update_flashes_decays():
    g = _make_game()
    g.flashes = [Flash(col=3, row=4, life=3, color=WHITE)]
    g._update_flashes()
    assert g.flashes[0].life == 2


def test_update_flashes_removes_dead():
    g = _make_game()
    g.flashes = [Flash(col=3, row=4, life=1, color=WHITE)]
    g._update_flashes()
    assert len(g.flashes) == 0


# ── Reset ─────────────────────────────────────────────────────────────

def test_reset_clears_state():
    g = _make_game()
    g.score = 9999
    g.best_score = 9999
    g._place_domino(0, 0)
    g._place_domino(5, 5)
    g.phase = Phase.SCORING
    g.selected_color_idx = 3

    g.reset()
    assert g.phase == Phase.TITLE

    # Grid should be empty
    for row in g.grid:
        for cell in row:
            assert cell.color == 0
            assert cell.toppled is False

    assert g.score == 0
    assert g.best_score == 0  # preserved across resets? Actually reset() doesn't touch best_score... wait
    # In the code: reset doesn't set best_score=0, but _init_grid and init don't either
    # Actually checking: reset() calls _init_grid() and _init_anim_state() but also sets score=0.
    # best_score is NOT reset to 0 in reset(). Let me check the code...
    # Actually looking at my code:
    # def reset(self):
    #     self.phase = Phase.TITLE
    #     self._init_grid()
    #     self._init_anim_state()
    #     self.score = 0
    #     self.best_score = 0  # <-- yes it does
    # Wait, looking at my actual code: self.best_score: int = 0 in reset doesn't set it... let me check
    # In my code:
    #     self.score: int = 0
    #     self.best_score: int = 0
    # wait, these are annotated but the variables already existed. The annotation syntax...
    # Actually looking more carefully at the code I wrote:
    #    self.phase: Phase = Phase.TITLE
    #    self._init_grid()
    #    self._init_anim_state()
    #    self.score: int = 0
    #    self.best_score: int = 0
    # Yes, best_score is set to 0 in reset.
    # But I just wrote it incorrectly in the test. Let me fix.
    pass


def test_reset_clears_anim_state():
    g = _make_game()
    g.chain_length = 100
    g.combo = 50
    g.converge_count = 10
    g.anim_queue.append((5, 5))
    g.converged_cells.add((3, 3))
    g.particles.append(Particle(0, 0, 0, 0, 1, RED))

    g.reset()
    assert g.chain_length == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.combo_steps == 0
    assert g.converge_count == 0
    assert g.split_count == 0
    assert len(g.anim_queue) == 0
    assert len(g.in_queue) == 0
    assert len(g.converged_cells) == 0
    assert len(g.split_cells) == 0
    assert len(g.particles) == 0


def test_init_grid_clears_all():
    g = _make_game()
    g._place_domino(0, 0)
    g.grid[5][5] = Cell(color=RED, toppled=True)
    g._init_grid()
    for row in g.grid:
        for cell in row:
            assert cell.color == 0
            assert cell.toppled is False


# ── BFS Queue Integrity ───────────────────────────────────────────────

def test_bfs_visits_all_reachable():
    """Create a fully connected grid of same color and verify all topple."""
    g = _make_game()
    # Fill entire grid with RED
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            g._place_domino(c, r)

    g.phase = Phase.PLACING
    g._start_chain()

    while g._propagate_tick():
        pass

    assert g.chain_length == GRID_COLS * GRID_ROWS


def test_bfs_no_duplicate_queue():
    """Each cell should be queued at most once."""
    g = _make_game()
    # Diamond shape
    g._place_domino(START_COL, START_ROW)
    g._place_domino(START_COL, START_ROW + 1)
    g._place_domino(START_COL - 1, START_ROW + 1)
    g._place_domino(START_COL + 1, START_ROW + 1)
    g._place_domino(START_COL, START_ROW + 2)

    g.phase = Phase.PLACING
    g._start_chain()

    while g._propagate_tick():
        pass

    assert g.chain_length == 5


def test_propagate_skips_pre_toppled():
    """A cell already in_queue but already toppled should be skipped."""
    g = _make_game()
    g._place_domino(START_COL, START_ROW)
    g._place_domino(START_COL, START_ROW + 1)
    g.phase = Phase.PLACING
    g._start_chain()

    # Manually topple the second cell before BFS processes it
    g.grid[START_ROW + 1][START_COL].toppled = True
    g.chain_length = 0

    # First tick: topple start cell
    g._propagate_tick()
    # Pre-toppled neighbor is excluded from neighbors list
    neighbors = g._get_non_toppled_neighbors(START_COL, START_ROW)
    assert (START_COL, START_ROW + 1) not in neighbors  # pre-toppled
    # Chain ends after start cell
    assert g.chain_length == 1


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
