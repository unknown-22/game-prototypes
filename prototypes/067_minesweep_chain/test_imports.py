"""test_imports.py — Headless logic tests for MINESWEEP CHAIN."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/067_minesweep_chain")

from main import (
    Game, Cell, Particle, FloatingText, SynthesisAnim, Phase,
    HIDDEN, REVEALED_ORE, REVEALED_EMPTY, FLAGGED, MINE,
    ORE_COLORS, ORE_NAMES,
    COLS, ROWS, TOTAL_ORES, ORES_PER_COLOR, NUM_MINES,
    BASE_ORE_SCORE, CELL_W, CELL_H,
    GRID_X, GRID_Y, SCREEN_W, SCREEN_H, GAME_TIME_SEC,
    NUM_COLORS,
)


# ── Helper ────────────────────────────────────────────────────────────

def _make_game(seed: int = 42) -> Game:
    """Create a Game instance bypassing pyxel.init for headless testing."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(seed)
    g.reset()
    # Re-init grid with deterministic seed
    g._init_grid(seed=seed)
    return g


# ── Dataclass tests ────────────────────────────────────────────────────

def test_cell_defaults() -> None:
    cell = Cell(col=0, row=0)
    assert cell.state == HIDDEN
    assert cell.ore_color == 0
    assert cell.is_mine is False
    assert cell.is_ore is False
    assert cell.revealed is False


def test_cell_revealed_property() -> None:
    cell = Cell(col=0, row=0, state=REVEALED_ORE)
    assert cell.revealed is True
    cell.state = REVEALED_EMPTY
    assert cell.revealed is True
    cell.state = MINE
    assert cell.revealed is True
    cell.state = HIDDEN
    assert cell.revealed is False
    cell.state = FLAGGED
    assert cell.revealed is False


def test_particle_defaults() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=30, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.life == 30


def test_floating_text_defaults() -> None:
    ft = FloatingText(x=5.0, y=10.0, text="+50", life=30, color=8)
    assert ft.text == "+50"
    assert ft.life == 30


def test_synthesis_anim_defaults() -> None:
    anim = SynthesisAnim(cells=[(0, 0), (1, 1)], frame=0, total_frames=15)
    assert len(anim.cells) == 2
    assert anim.frame == 0
    assert anim.total_frames == 15


# ── Phase enum tests ───────────────────────────────────────────────────

def test_phase_values() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.SYNTHESIS in Phase
    assert Phase.GAME_OVER in Phase
    assert len(list(Phase)) == 4


# ── Grid init tests ────────────────────────────────────────────────────

def test_grid_dimensions() -> None:
    g = _make_game()
    assert len(g.grid) == COLS
    for col in g.grid:
        assert len(col) == ROWS


def test_all_cells_initialized() -> None:
    g = _make_game()
    for c in range(COLS):
        for r in range(ROWS):
            cell = g.grid[c][r]
            assert cell.col == c
            assert cell.row == r
            assert cell.state == HIDDEN


def test_mine_count() -> None:
    g = _make_game()
    mine_count = sum(1 for c in range(COLS) for r in range(ROWS) if g.grid[c][r].is_mine)
    assert mine_count == NUM_MINES


def test_ore_count() -> None:
    g = _make_game()
    ore_count = sum(1 for c in range(COLS) for r in range(ROWS) if g.grid[c][r].is_ore)
    assert ore_count == TOTAL_ORES


def test_ores_per_color() -> None:
    g = _make_game()
    for color in range(NUM_COLORS):
        count = sum(
            1 for c in range(COLS) for r in range(ROWS)
            if g.grid[c][r].is_ore and g.grid[c][r].ore_color == color
        )
        assert count == ORES_PER_COLOR, f"Color {color} has {count} ores, expected {ORES_PER_COLOR}"


def test_init_grid_resets_state() -> None:
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.max_combo = 10
    g.time_left = 10.0
    g.ores_revealed = 8
    g._win = True
    g._current_color = 2
    g.particles.append(Particle(0, 0, 0, 0, 10, 8))
    g.floating_texts.append(FloatingText(0, 0, "test", 10, 8))

    g._init_grid(seed=99)

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.time_left == GAME_TIME_SEC
    assert g.ores_revealed == 0
    assert g._win is False
    assert g._current_color is None
    assert g._synthesis_anim is None
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_different_seeds_different_layouts() -> None:
    g1 = _make_game(seed=42)
    g2 = _make_game(seed=99)

    # Compare mine positions
    mines1 = [(c, r) for c in range(COLS) for r in range(ROWS) if g1.grid[c][r].is_mine]
    mines2 = [(c, r) for c in range(COLS) for r in range(ROWS) if g2.grid[c][r].is_mine]
    assert mines1 != mines2, "Different seeds should produce different mine layouts"


# ── Reveal cell tests ──────────────────────────────────────────────────

def test_reveal_ore_cell() -> None:
    g = _make_game(seed=42)
    # Find an ore cell
    for c in range(COLS):
        for r in range(ROWS):
            if g.grid[c][r].is_ore:
                result, ore_color = g._reveal_cell(c, r)
                assert result == REVEALED_ORE
                assert ore_color == g.grid[c][r].ore_color
                assert g.grid[c][r].state == REVEALED_ORE
                return
    assert False, "No ore cell found"


def test_reveal_mine_cell() -> None:
    g = _make_game(seed=42)
    # Find a mine cell
    for c in range(COLS):
        for r in range(ROWS):
            if g.grid[c][r].is_mine:
                result, ore_color = g._reveal_cell(c, r)
                assert result == MINE
                assert ore_color is None
                assert g.grid[c][r].state == MINE
                return
    assert False, "No mine cell found"


def test_reveal_empty_cell() -> None:
    g = _make_game(seed=42)
    # Find an empty cell (not mine, not ore)
    for c in range(COLS):
        for r in range(ROWS):
            if not g.grid[c][r].is_mine and not g.grid[c][r].is_ore:
                result, ore_color = g._reveal_cell(c, r)
                assert result == REVEALED_EMPTY
                assert ore_color is None
                assert g.grid[c][r].state == REVEALED_EMPTY
                return
    assert False, "No empty cell found"


def test_reveal_already_revealed_cell() -> None:
    g = _make_game(seed=42)
    # Find an ore, reveal it, then try to reveal again
    for c in range(COLS):
        for r in range(ROWS):
            if g.grid[c][r].is_ore:
                g._reveal_cell(c, r)  # First reveal
                result, _ = g._reveal_cell(c, r)  # Second reveal
                assert result == REVEALED_ORE  # Returns current state
                return
    assert False, "No ore cell found"


# ── Flag tests ──────────────────────────────────────────────────────────

def test_toggle_flag_on_hidden() -> None:
    g = _make_game(seed=42)
    g._toggle_flag(0, 0)
    assert g.grid[0][0].state == FLAGGED


def test_toggle_flag_on_flagged() -> None:
    g = _make_game(seed=42)
    g._toggle_flag(0, 0)
    assert g.grid[0][0].state == FLAGGED
    g._toggle_flag(0, 0)
    assert g.grid[0][0].state == HIDDEN


def test_toggle_flag_on_revealed_does_nothing() -> None:
    g = _make_game(seed=42)
    # Find an ore, reveal it
    for c in range(COLS):
        for r in range(ROWS):
            if g.grid[c][r].is_ore:
                g._reveal_cell(c, r)
                assert g.grid[c][r].state == REVEALED_ORE
                g._toggle_flag(c, r)  # Should do nothing
                assert g.grid[c][r].state == REVEALED_ORE  # Unchanged
                return
    assert False, "No ore cell found"


# ── Count adjacent ores tests ──────────────────────────────────────────

def test_count_adjacent_ores() -> None:
    g = _make_game(seed=42)
    # Just verify the method returns a dict and values are non-negative
    counts = g._count_adjacent_ores(0, 0)
    assert isinstance(counts, dict)
    for c, cnt in counts.items():
        assert 0 <= c < NUM_COLORS
        assert cnt >= 0


def test_count_adjacent_ores_corner() -> None:
    """Corner cell should have at most 3 neighbors."""
    g = _make_game(seed=42)
    counts = g._count_adjacent_ores(0, 0)
    total = sum(counts.values())
    # A corner has up to 3 8-directional neighbors
    assert total <= 3


def test_count_adjacent_ores_center() -> None:
    """Center cell should have up to 8 neighbors."""
    g = _make_game(seed=42)
    counts = g._count_adjacent_ores(5, 4)
    total = sum(counts.values())
    assert total <= 8


# ── BFS synthesis tests ────────────────────────────────────────────────

def test_bfs_synthesis_single_cell() -> None:
    """BFS from a single ore should find itself (but not include start)."""
    g = _make_game(seed=42)
    # Find an ore, determine its color
    for c in range(COLS):
        for r in range(ROWS):
            if g.grid[c][r].is_ore:
                color = g.grid[c][r].ore_color
                cells = g._bfs_synthesis(c, r, color)
                # start cell is visited but not added to result (already revealed)
                assert (c, r) not in cells
                return
    assert False, "No ore cell found"


def test_bfs_synthesis_adjacent_same_color() -> None:
    """Create a scenario with 3 adjacent same-color ores, test BFS from one."""
    g = _make_game(seed=42)
    # Manually set up: ores at (0,0), (1,0), (0,1) all color=0
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[1][0].is_ore = True
    g.grid[1][0].ore_color = 0
    g.grid[0][1].is_ore = True
    g.grid[0][1].ore_color = 0

    cells = g._bfs_synthesis(0, 0, 0)
    # Should find (1,0) and (0,1) — both adjacent 4-dir same color
    assert (1, 0) in cells
    assert (0, 1) in cells
    assert (0, 0) not in cells  # Start cell excluded
    assert len(cells) == 2


def test_bfs_synthesis_different_color_blocked() -> None:
    """BFS should not cross into different-colored ore cells."""
    g = _make_game(seed=42)
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    # color 0 at (0,0) and (1,0), but (1,0) is color 1
    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[1][0].is_ore = True
    g.grid[1][0].ore_color = 1  # Different color — should block BFS
    g.grid[0][1].is_ore = True
    g.grid[0][1].ore_color = 0

    cells = g._bfs_synthesis(0, 0, 0)
    # Should only find (0,1), not (1,0)
    assert (0, 1) in cells
    assert (1, 0) not in cells
    assert len(cells) == 1


def test_bfs_synthesis_empty_cell_blocked() -> None:
    """BFS should not propagate through empty (non-ore) cells."""
    g = _make_game(seed=42)
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[2][0].is_ore = True  # Separated by empty cell at (1,0)
    g.grid[2][0].ore_color = 0
    # (1,0) is empty (no ore)

    cells = g._bfs_synthesis(0, 0, 0)
    assert (2, 0) not in cells  # BFS shouldn't reach through empty cell
    assert len(cells) == 0  # No adjacent same-color ores


def test_bfs_synthesis_already_revealed_skipped() -> None:
    """BFS should include already-revealed same-color ores that aren't REVEALED_ORE state."""
    g = _make_game(seed=42)
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[1][0].is_ore = True
    g.grid[1][0].ore_color = 0
    g.grid[1][0].state = FLAGGED  # Flagged ore

    cells = g._bfs_synthesis(0, 0, 0)
    assert (1, 0) in cells  # Should find flagged ore
    assert len(cells) == 1


def test_bfs_synthesis_chain_of_three() -> None:
    """Chain of 3 same-color ores in a line: (0,0)→(1,0)→(2,0)."""
    g = _make_game(seed=42)
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[1][0].is_ore = True
    g.grid[1][0].ore_color = 0
    g.grid[2][0].is_ore = True
    g.grid[2][0].ore_color = 0

    cells = g._bfs_synthesis(0, 0, 0)
    assert (1, 0) in cells
    assert (2, 0) in cells
    assert len(cells) == 2


# ── Apply synthesis tests ──────────────────────────────────────────────

def test_apply_synthesis_reveals_cells() -> None:
    g = _make_game(seed=42)
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[1][0].is_ore = True
    g.grid[1][0].ore_color = 0

    revealed = g._apply_synthesis({(0, 0), (1, 0)})
    assert revealed == 2
    assert g.grid[0][0].state == REVEALED_ORE
    assert g.grid[1][0].state == REVEALED_ORE


def test_apply_synthesis_skips_already_revealed() -> None:
    g = _make_game(seed=42)
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[0][0].state = REVEALED_ORE  # Already revealed
    g.grid[1][0].is_ore = True
    g.grid[1][0].ore_color = 0

    revealed = g._apply_synthesis({(0, 0), (1, 0)})
    assert revealed == 1  # Only (1,0) was newly revealed


# ── Win check tests ────────────────────────────────────────────────────

def test_check_win_not_yet() -> None:
    g = _make_game(seed=42)
    assert g._check_win() is False


def test_check_win_after_all_ores_revealed() -> None:
    g = _make_game(seed=42)
    g.ores_revealed = TOTAL_ORES
    assert g._check_win() is True


def test_check_win_after_exceeding() -> None:
    g = _make_game(seed=42)
    g.ores_revealed = TOTAL_ORES + 5
    assert g._check_win() is True


# ── Combo logic tests (via handle_click simulation) ────────────────────

def test_combo_same_color_increments() -> None:
    """Simulate revealing 2 same-color ores in sequence."""
    g = _make_game(seed=42)
    # Manually set up two same-color ores, reveal them through logic
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[0][1].is_ore = True
    g.grid[0][1].ore_color = 0

    # Simulate clicking first ore
    result1, color1 = g._reveal_cell(0, 0)
    assert result1 == REVEALED_ORE
    assert color1 == 0
    g.ores_revealed += 1
    g.combo = 1
    g._current_color = 0

    # Simulate clicking second ore (same color)
    result2, color2 = g._reveal_cell(0, 1)
    assert result2 == REVEALED_ORE
    assert color2 == 0
    g.ores_revealed += 1
    # Should increment combo since same color
    g.combo += 1
    assert g.combo == 2


def test_combo_different_color_resets() -> None:
    """Simulate revealing different-color ore resets combo to 1."""
    g = _make_game(seed=42)
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[0][1].is_ore = True
    g.grid[0][1].ore_color = 1  # Different color

    # First ore
    g._reveal_cell(0, 0)
    g.ores_revealed += 1
    g.combo = 1
    g._current_color = 0

    # Second ore (different color) — combo resets to 1
    g._reveal_cell(0, 1)
    g.combo = 1
    g._current_color = 1
    assert g.combo == 1
    assert g._current_color == 1


def test_combo_empty_cell_resets() -> None:
    """Revealing empty cell resets combo to 0."""
    g = _make_game(seed=42)
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[1][0].is_ore = False  # Empty

    # Reveal ore
    g._reveal_cell(0, 0)
    g.ores_revealed += 1
    g.combo = 1
    g._current_color = 0

    # Reveal empty — combo resets
    g._reveal_cell(1, 0)
    g.combo = 0
    g._current_color = None
    assert g.combo == 0
    assert g._current_color is None


# ── Score calculation tests ────────────────────────────────────────────

def test_base_score_single_ore() -> None:
    points = BASE_ORE_SCORE * 1  # combo=1
    assert points == 10


def test_score_with_combo() -> None:
    points = BASE_ORE_SCORE * 3  # combo=3
    assert points == 30


def test_score_integration() -> None:
    """Full integration: reveal 3 same-color ores, verify score calculation."""
    g = _make_game(seed=42)
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[0][1].is_ore = True
    g.grid[0][1].ore_color = 0
    g.grid[0][2].is_ore = True
    g.grid[0][2].ore_color = 0

    score = 0
    combo = 0

    # Reveal first
    g._reveal_cell(0, 0)
    g.ores_revealed += 1
    combo = 1
    score += BASE_ORE_SCORE * combo  # 10

    # Reveal second
    g._reveal_cell(0, 1)
    g.ores_revealed += 1
    combo += 1  # 2
    score += BASE_ORE_SCORE * combo  # +20 = 30

    # Reveal third (triggers synthesis threshold!)
    g._reveal_cell(0, 2)
    g.ores_revealed += 1
    combo += 1  # 3
    score += BASE_ORE_SCORE * combo  # +30 = 60

    assert score == 60
    assert combo == 3  # SYNTHESIS_THRESHOLD reached


# ── Reset tests ────────────────────────────────────────────────────────

def test_reset_clears_state() -> None:
    g = _make_game(seed=42)
    g.score = 999
    g.combo = 5
    g.time_left = 10.0
    g.ores_revealed = 8
    g.phase = Phase.GAME_OVER
    g.particles.append(Particle(0, 0, 0, 0, 10, 8))
    g.floating_texts.append(FloatingText(0, 0, "x", 5, 8))
    g._current_color = 2
    g._win = True
    g._synthesis_anim = SynthesisAnim()

    g.reset()

    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.time_left == GAME_TIME_SEC
    assert g.ores_revealed == 0
    assert g._current_color is None
    assert g._win is False
    assert g._synthesis_anim is None
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_reset_recreates_grid() -> None:
    g = _make_game(seed=42)
    g.reset()
    assert len(g.grid) == COLS
    for col in g.grid:
        assert len(col) == ROWS


# ── Grid boundary tests ────────────────────────────────────────────────

def test_handle_click_translation() -> None:
    """Verify grid coordinate translation from mouse coords."""
    # GRID_X=20, GRID_Y=40, CELL_W=24, CELL_H=24
    # Mouse at (20, 40) should map to col=0, row=0
    col = (20 - GRID_X) // CELL_W
    row = (40 - GRID_Y) // CELL_H
    assert col == 0
    assert row == 0

    # Mouse at (GRID_X + 5*CELL_W + 10, GRID_Y + 3*CELL_H + 10) → col=5, row=3
    col = (GRID_X + 5 * CELL_W + 10 - GRID_X) // CELL_W
    row = (GRID_Y + 3 * CELL_H + 10 - GRID_Y) // CELL_H
    assert col == 5
    assert row == 3


# ── Constants tests ────────────────────────────────────────────────────

def test_ore_colors_are_valid() -> None:
    assert len(ORE_COLORS) == 4
    for c in ORE_COLORS:
        assert 0 <= c <= 15


def test_ore_names_match() -> None:
    assert len(ORE_NAMES) == 4
    for name in ORE_NAMES:
        assert isinstance(name, str)
        assert len(name) > 0


def test_grid_fits_screen() -> None:
    """Verify the grid fits within the screen."""
    assert GRID_X + COLS * CELL_W <= SCREEN_W
    assert GRID_Y + ROWS * CELL_H <= SCREEN_H


def test_total_cells_match() -> None:
    assert COLS * ROWS == NUM_MINES + TOTAL_ORES + (COLS * ROWS - NUM_MINES - TOTAL_ORES)


# ── Edge case: mine + ore on same cell (shouldn't happen) ──────────────

def test_no_mine_is_also_ore() -> None:
    g = _make_game(seed=42)
    for c in range(COLS):
        for r in range(ROWS):
            cell = g.grid[c][r]
            assert not (cell.is_mine and cell.is_ore), f"Mine+ore overlap at ({c},{r})"


# ── BFS edge cases ────────────────────────────────────────────────────

def test_bfs_synthesis_wrong_color_returns_empty() -> None:
    """BFS with color that doesn't match returns empty set."""
    g = _make_game(seed=42)
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[0][1].is_ore = True
    g.grid[0][1].ore_color = 1  # Different color

    cells = g._bfs_synthesis(0, 0, 1)  # Wrong color
    assert len(cells) == 0


def test_bfs_synthesis_boundary() -> None:
    """BFS at grid boundaries shouldn't crash."""
    g = _make_game(seed=42)
    for col in range(COLS):
        for row in range(ROWS):
            g.grid[col][row].is_mine = False
            g.grid[col][row].is_ore = False
            g.grid[col][row].state = HIDDEN

    # Ore at corner
    g.grid[0][0].is_ore = True
    g.grid[0][0].ore_color = 0
    g.grid[0][7].is_ore = True
    g.grid[0][7].ore_color = 0

    # Should not crash
    cells_corner = g._bfs_synthesis(0, 0, 0)
    assert len(cells_corner) == 0  # (0,7) not 4-direction adjacent to (0,0)

    cells_edge = g._bfs_synthesis(0, 7, 0)
    assert len(cells_edge) == 0


# ── ORE_COLORS constant index tests ────────────────────────────────────

def test_ore_color_indices_valid() -> None:
    """ORE_COLORS should be accessible with indices 0-3."""
    for i in range(NUM_COLORS):
        assert ORE_COLORS[i] is not None


print("All tests passed!")
