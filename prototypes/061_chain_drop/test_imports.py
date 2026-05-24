"""test_imports.py — Headless logic tests for CHAIN DROP (061_chain_drop)."""
import sys
import math
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import (
    Game, Particle, FloatingText,
    COLS, ROWS, CELL_SIZE, GRID_X, GRID_Y,
    DISC_RADIUS, SUPER_DISC_RADIUS, SUPER_DISC_VALUE, NUM_COLORS,
    DISC_COLORS,
    PHASE_TITLE, PHASE_PLAYING, PHASE_ANIM_DROP, PHASE_ANIM_CLEAR,
    PHASE_ANIM_GRAVITY, PHASE_GRID_PRESSURE, PHASE_GAME_OVER,
)


def _make_game() -> Game:
    """Create Game instance bypassing Pyxel init."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.turn_count = 0
    g.pressure_timer = 5
    g.last_color = None
    g.super_disc_ready = False
    g.particles = []
    g.floating_texts = []
    g._shake_frames = 0
    g._shake_offset_x = 0
    g._shake_offset_y = 0
    g.selected_col = 3
    g.phase = PHASE_TITLE
    g._anim_timer = 0
    g._drop_col = -1
    g._drop_color = -1
    g._drop_target_row = -1
    g._drop_y = 0.0
    g._match_flash_timer = 0
    g._matches_to_clear = []
    g._discs_cleared = 0
    g._chain_count = 0
    g._was_super_disc = False
    g._super_disc_anim_timer = 0
    g._decrement_pressure_on_settle = False
    g._init_state()
    return g


# ── Grid & Data Classes ──


def test_grid_initialization():
    g = _make_game()
    assert g.phase == PHASE_TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.turn_count == 0
    assert g.pressure_timer == 5
    assert len(g.grid) == ROWS
    assert len(g.grid[0]) == COLS
    for row in g.grid:
        for cell in row:
            assert cell is None


def test_dataclass_instantiation():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, color=8, life=20)
    assert p.x == 10.0
    assert p.life == 20

    ft = FloatingText(x=100.0, y=50.0, text="+100", color=7, life=30)
    assert ft.text == "+100"
    assert ft.color == 7


# ── Drop Target Row ──


def test_find_drop_target_row_empty_column():
    g = _make_game()
    # Column 3 is empty
    assert g._find_drop_target_row(3) == ROWS - 1  # bottom row


def test_find_drop_target_row_partially_filled():
    g = _make_game()
    g.grid[5][3] = 0  # bottom row filled
    g.grid[4][3] = 1  # row 4 filled
    assert g._find_drop_target_row(3) == 3  # row 3 is empty


def test_find_drop_target_row_full_column():
    g = _make_game()
    for row in range(ROWS):
        g.grid[row][3] = 0
    assert g._find_drop_target_row(3) == -1


# ── Match Detection: _is_match ──


def test_is_match_all_same_color():
    g = _make_game()
    for c in range(4):
        g.grid[5][c] = 0  # RED
    assert g._is_match([(5, 0), (5, 1), (5, 2), (5, 3)])


def test_is_match_different_colors():
    g = _make_game()
    g.grid[5][0] = 0
    g.grid[5][1] = 0
    g.grid[5][2] = 1  # different
    g.grid[5][3] = 0
    assert not g._is_match([(5, 0), (5, 1), (5, 2), (5, 3)])


def test_is_match_with_none():
    g = _make_game()
    g.grid[5][0] = 0
    g.grid[5][1] = 0
    g.grid[5][2] = 0
    # grid[5][3] is None
    assert not g._is_match([(5, 0), (5, 1), (5, 2), (5, 3)])


def test_is_match_with_super_disc():
    g = _make_game()
    g.grid[5][0] = SUPER_DISC_VALUE
    g.grid[5][1] = 0  # RED
    g.grid[5][2] = 0  # RED
    g.grid[5][3] = 0  # RED
    assert g._is_match([(5, 0), (5, 1), (5, 2), (5, 3)])


def test_is_match_super_disc_no_common_color():
    g = _make_game()
    g.grid[5][0] = SUPER_DISC_VALUE
    g.grid[5][1] = 0  # RED
    g.grid[5][2] = 1  # GREEN — different!
    g.grid[5][3] = 0  # RED
    # Two distinct non-SUPER colors → not a match
    assert not g._is_match([(5, 0), (5, 1), (5, 2), (5, 3)])


def test_is_match_all_super_discs():
    g = _make_game()
    for c in range(4):
        g.grid[5][c] = SUPER_DISC_VALUE
    # All SUPER — no non-SUPER colors → 0 distinct colors ≤ 1 → match
    assert g._is_match([(5, 0), (5, 1), (5, 2), (5, 3)])


# ── Match Detection: _find_all_matches ──


def test_find_all_matches_horizontal():
    g = _make_game()
    for c in range(5):
        g.grid[5][c] = 0  # RED, RED, RED, RED, RED
    matches = g._find_all_matches()
    assert len(matches) >= 1
    all_matched = set().union(*matches)
    # All 5 should be matched
    assert (5, 0) in all_matched
    assert (5, 4) in all_matched


def test_find_all_matches_vertical():
    g = _make_game()
    for r in range(2, 6):
        g.grid[r][3] = 1  # GREEN
    matches = g._find_all_matches()
    assert len(matches) >= 1
    all_matched = set().union(*matches)
    assert (2, 3) in all_matched
    assert (5, 3) in all_matched


def test_find_all_matches_diagonal_down_right():
    g = _make_game()
    for i in range(4):
        g.grid[2 + i][1 + i] = 2  # DARK_BLUE
    matches = g._find_all_matches()
    assert len(matches) >= 1
    all_matched = set().union(*matches)
    assert (2, 1) in all_matched
    assert (5, 4) in all_matched


def test_find_all_matches_diagonal_down_left():
    g = _make_game()
    for i in range(4):
        g.grid[2 + i][5 - i] = 3  # YELLOW
    matches = g._find_all_matches()
    assert len(matches) >= 1
    all_matched = set().union(*matches)
    assert (2, 5) in all_matched
    assert (5, 2) in all_matched


def test_find_all_matches_no_match():
    g = _make_game()
    # Scattered colors — no 4-in-a-row
    g.grid[5][0] = 0
    g.grid[5][2] = 0
    g.grid[5][4] = 0
    g.grid[4][0] = 1
    assert g._find_all_matches() == []


def test_find_all_matches_multiple_groups():
    g = _make_game()
    # Horizontal match in row 5
    for c in range(4):
        g.grid[5][c] = 0
    # Vertical match in col 6 (4 cells for a valid match)
    for r in range(4):
        g.grid[2 + r][6] = 1
    matches = g._find_all_matches()
    assert len(matches) >= 2


def test_find_all_matches_super_disc_bridges():
    g = _make_game()
    g.grid[5][0] = 0  # RED
    g.grid[5][1] = SUPER_DISC_VALUE  # wildcard
    g.grid[5][2] = 0  # RED
    g.grid[5][3] = 0  # RED
    matches = g._find_all_matches()
    assert len(matches) >= 1


def test_find_all_matches_super_disc_does_not_bridge_different():
    g = _make_game()
    g.grid[5][0] = 0  # RED
    g.grid[5][1] = SUPER_DISC_VALUE
    g.grid[5][2] = 1  # GREEN (different!)
    g.grid[5][3] = 0  # RED
    matches = g._find_all_matches()
    # RED-SUPER-GREEN-RED: non-SUPER colors = {RED, GREEN} = 2, no match
    assert matches == []


# ── Group Connected ──


def test_group_connected_single_group():
    g = _make_game()
    matched = {(5, 0), (5, 1), (5, 2), (5, 3)}
    groups = g._group_connected(matched)
    assert len(groups) == 1
    assert groups[0] == matched


def test_group_connected_separate_groups():
    g = _make_game()
    matched = {(5, 0), (5, 1), (5, 2), (5, 3), (0, 6), (1, 6), (2, 6), (3, 6)}
    groups = g._group_connected(matched)
    assert len(groups) == 2
    total = sum(len(grp) for grp in groups)
    assert total == 8


# ── Gravity ──


def test_apply_gravity_no_movement():
    g = _make_game()
    # Empty grid
    assert not g._apply_gravity()


def test_apply_gravity_compacts_down():
    g = _make_game()
    g.grid[0][3] = 0  # top row (most recently dropped)
    g.grid[2][3] = 1  # middle (older disc)
    # row 1,3,4,5 are empty in col 3
    assert g._apply_gravity()
    # After gravity: non_empty from top→bottom = [0, 1]
    # padded: [None, None, None, None, 0, 1]
    # disc 0 (top/newer) → row 4, disc 1 (older) → row 5 (bottom)
    assert g.grid[0][3] is None
    assert g.grid[1][3] is None
    assert g.grid[4][3] == 0  # newer disc ends up on top
    assert g.grid[5][3] == 1  # older disc ends up at bottom


def test_apply_gravity_already_compact():
    g = _make_game()
    g.grid[5][3] = 0
    g.grid[4][3] = 1
    assert not g._apply_gravity()


# ── Combo System ──


def test_combo_increments_on_same_color():
    g = _make_game()
    g.phase = PHASE_PLAYING
    g._drop_col = 3
    g._drop_target_row = 5
    g._drop_color = 0  # RED
    g._decrement_pressure_on_settle = True
    # Simulate disc placement manually
    g.grid[5][3] = 0
    g._on_disc_placed()
    assert g.combo == 0  # first drop, no combo yet
    assert g.last_color == 0

    # Second same-color drop
    g._drop_col = 4
    g._drop_target_row = 5
    g._drop_color = 0  # RED again
    g._decrement_pressure_on_settle = True
    g.grid[5][4] = 0
    g._on_disc_placed()
    assert g.combo == 1
    assert g.max_combo == 1


def test_combo_resets_on_color_change():
    g = _make_game()
    g.phase = PHASE_PLAYING

    # Build combo to 2
    for i in range(3):
        g._drop_col = i
        g._drop_target_row = 5
        g._drop_color = 0  # RED
        g._decrement_pressure_on_settle = True
        g.grid[5][i] = 0
        g._on_disc_placed()
    assert g.combo == 2

    # Different color
    g._drop_col = 3
    g._drop_target_row = 5
    g._drop_color = 1  # GREEN
    g._decrement_pressure_on_settle = True
    g.grid[5][3] = 1
    g._on_disc_placed()
    assert g.combo == 0
    assert g.last_color == 1


def test_super_disc_ready_at_combo_4():
    g = _make_game()
    g.phase = PHASE_PLAYING

    # 5 same-color drops (combo reaches 4 on the 5th drop)
    for i in range(5):
        g._drop_col = i % COLS
        g._drop_target_row = 5
        g._drop_color = 0  # RED
        g._decrement_pressure_on_settle = True
        g.grid[5][i % COLS] = 0
        g._on_disc_placed()

    assert g.super_disc_ready


def test_super_disc_resets_combo():
    g = _make_game()
    g.phase = PHASE_PLAYING

    # Build combo to 4
    for i in range(5):
        g._drop_col = i % COLS
        g._drop_target_row = 5
        g._drop_color = 0
        g._decrement_pressure_on_settle = True
        g.grid[5][i % COLS] = 0
        g._on_disc_placed()

    assert g.super_disc_ready

    # Next disc would be SUPER (test via _next_disc_color)
    color = g._next_disc_color()
    assert color == SUPER_DISC_VALUE
    assert g.combo == 0
    assert g.last_color is None
    assert not g.super_disc_ready


# ── Execute Clear ──


def test_execute_clear_removes_discs():
    g = _make_game()
    for c in range(4):
        g.grid[5][c] = 0
    g._matches_to_clear = g._find_all_matches()
    g.phase = PHASE_ANIM_CLEAR
    initial_score = g.score
    g._execute_clear()

    # Discs should be removed
    for c in range(4):
        assert g.grid[5][c] is None
    # Score should increase
    assert g.score > initial_score


def test_execute_clear_scoring():
    g = _make_game()
    for c in range(4):
        g.grid[5][c] = 0  # 4 discs, 1 group
    g._matches_to_clear = g._find_all_matches()
    g.combo = 3
    initial_score = g.score
    g._execute_clear()

    # base = 4 * 10 = 40, multiplier = 1 (1 group), combo_bonus = 3 * 50 = 150
    # score_gain = 40 * 1 + 150 = 190
    expected = initial_score + 190
    assert g.score == expected


def test_execute_clear_particles_spawned():
    g = _make_game()
    for c in range(4):
        g.grid[5][c] = 0
    g._matches_to_clear = g._find_all_matches()
    assert len(g.particles) == 0
    g._execute_clear()
    assert len(g.particles) > 0


def test_execute_clear_floating_text():
    g = _make_game()
    for c in range(4):
        g.grid[5][c] = 0
    g._matches_to_clear = g._find_all_matches()
    g._execute_clear()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text.startswith("+")


def test_execute_clear_super_disc_multiplier():
    g = _make_game()
    for c in range(4):
        g.grid[5][c] = 0
    g._matches_to_clear = g._find_all_matches()
    g._was_super_disc = True
    initial_score = g.score
    g._execute_clear()

    # base=40, mul=1, combo=0 → 40, ×3 for SUPER → 120
    assert g.score == initial_score + 120


def test_execute_clear_chain_reaction_multiplier():
    g = _make_game()
    for c in range(4):
        g.grid[5][c] = 0
    g._matches_to_clear = g._find_all_matches()
    g._chain_count = 2  # second chain
    initial_score = g.score
    g._execute_clear()

    # base=40, mul=1, combo=0 → 40, chain_bonus = 1.0 + 0.5 * 2 = 2.0 → 80
    assert g.score == initial_score + 80


def test_execute_clear_screen_shake():
    g = _make_game()
    # Create 3 separate groups
    for c in range(4):
        g.grid[5][c] = 0
    for c in range(4):
        g.grid[0][c] = 1
    for r in range(4):
        g.grid[r][6] = 2
    g._matches_to_clear = g._find_all_matches()
    g._execute_clear()
    # Should have shake since >= 3 groups
    assert g._shake_frames == 8


# ── Grid Pressure ──


def test_spawn_pressure_disc_empty_grid():
    g = _make_game()
    spawned, has_matches = g._spawn_pressure_disc()
    assert spawned
    # With random placement, might not match
    # Check that at least one disc was placed
    non_none = sum(
        1 for r in range(ROWS) for c in range(COLS) if g.grid[r][c] is not None
    )
    assert non_none == 1


def test_spawn_pressure_disc_full_grid():
    g = _make_game()
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = 0
    spawned, has_matches = g._spawn_pressure_disc()
    assert not spawned


def test_finish_turn_pressure_triggers():
    g = _make_game()
    g.phase = PHASE_PLAYING
    g._decrement_pressure_on_settle = True
    g.pressure_timer = 1  # Will become 0 after decrement

    g._finish_turn()
    # Should have triggered pressure, and if grid isn't full:
    assert g.phase in (PHASE_GRID_PRESSURE, PHASE_ANIM_CLEAR, PHASE_GAME_OVER)


def test_finish_turn_normal():
    g = _make_game()
    g.phase = PHASE_PLAYING
    g._decrement_pressure_on_settle = True
    g.pressure_timer = 5

    g._finish_turn()
    # pressure_timer becomes 4, > 0, go to PLAYING
    assert g.phase == PHASE_PLAYING
    assert g.pressure_timer == 4


# ── Constants ──


def test_constants():
    assert len(DISC_COLORS) == 4
    assert SUPER_DISC_VALUE == NUM_COLORS == 4
    assert DISC_RADIUS == 14
    assert SUPER_DISC_RADIUS == 16
    assert COLS == 7
    assert ROWS == 6
    assert CELL_SIZE == 32
    assert GRID_X == 48
    assert GRID_Y == 24


# ── Phase Values ──


def test_phase_values():
    assert PHASE_TITLE == 0
    assert PHASE_PLAYING == 1
    assert PHASE_ANIM_DROP == 2
    assert PHASE_ANIM_CLEAR == 3
    assert PHASE_ANIM_GRAVITY == 4
    assert PHASE_GRID_PRESSURE == 5
    assert PHASE_GAME_OVER == 6


# ── Game Over ──


def test_game_over_when_grid_full():
    g = _make_game()
    # Fill entire grid
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c] = 0
    spawned, _ = g._spawn_pressure_disc()
    assert not spawned


# ── Gravity chain reaction ──


def test_gravity_then_new_match_forms():
    """After gravity compacts, new matches can form in the same column."""
    g = _make_game()
    # Set up: row 5 col 3=RED, row 3 col 3=RED, row 2 col 3=RED
    # After clearing some middle rows, those 3 + 1 more from above = 4
    g.grid[5][3] = 0  # RED
    g.grid[4][3] = 1  # GREEN (will be cleared)
    g.grid[3][3] = 0  # RED
    g.grid[2][3] = 0  # RED
    g.grid[1][3] = 0  # RED

    # Clear the GREEN at row 4
    for c2 in range(4):
        g.grid[4][c2] = 1
    g._matches_to_clear = g._find_all_matches()
    g._execute_clear()
    g._apply_gravity()

    # After gravity, REDs at rows 5,3,2,1 should compact to rows 5,4,3,2
    # Then check new matches
    new_matches = g._find_all_matches()
    # Should find 4 REDs in col 3
    assert len(new_matches) >= 1


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
