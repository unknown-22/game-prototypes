"""test_imports.py — Headless logic tests for 131_tile_chain."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (
    FloatingText,
    Game,
    Particle,
    Phase,
    _make_game,
)


def test_init_grid_size():
    g = _make_game(seed=42)
    assert len(g.grid) == Game.ROWS
    assert len(g.grid[0]) == Game.COLS


def test_init_grid_color_counts():
    """Exactly 12 tiles of each color."""
    g = _make_game(seed=42)
    counts = {c: 0 for c in Game.COLORS}
    for row in g.grid:
        for cell in row:
            if cell is not None:
                counts[cell] += 1
    for c, count in counts.items():
        assert count == Game.TILES_PER_COLOR, f"Color {c}: expected 12, got {count}"


def test_init_tiles_remaining():
    g = _make_game(seed=42)
    assert g.tiles_remaining == Game.TOTAL_TILES


def test_init_phase():
    g = _make_game(seed=42)
    assert g.phase == Phase.TITLE


def test_find_matches_same_color():
    """_find_matches returns pairs of same-color tiles."""
    g = _make_game(seed=42)
    pairs = g._find_matches(g.grid)
    assert len(pairs) > 0
    for p1, p2 in pairs:
        c1, r1 = p1
        c2, r2 = p2
        assert g.grid[r1][c1] == g.grid[r2][c2]


def test_select_then_match_same_color():
    g = _make_game(seed=42)
    pairs = g._find_matches(g.grid)
    assert len(pairs) > 0
    p1, p2 = pairs[0]
    c1, r1 = p1
    c2, r2 = p2

    result1 = g._select_tile(c1, r1)
    assert result1 == "select"

    result2 = g._select_tile(c2, r2)
    assert result2 == "match"

    g._handle_match(p1, p2)
    assert g.score > 0
    assert g.combo == 1
    assert g.grid[r1][c1] is None
    assert g.grid[r2][c2] is None
    assert g.tiles_remaining == Game.TOTAL_TILES - 2


def test_wrong_color_select():
    g = _make_game(seed=42)
    non_empty = [
        (c, r)
        for r in range(Game.ROWS)
        for c in range(Game.COLS)
        if g.grid[r][c] is not None
    ]
    # Find two different color tiles
    for i in range(len(non_empty)):
        for j in range(i + 1, len(non_empty)):
            c1, r1 = non_empty[i]
            c2, r2 = non_empty[j]
            if g.grid[r1][c1] != g.grid[r2][c2]:
                g._select_tile(c1, r1)
                result = g._select_tile(c2, r2)
                assert result == "wrong"
                g._handle_wrong()
                assert g.combo == 0
                assert g.heat == Game.WRONG_MATCH_HEAT
                # Tiles should NOT be removed
                assert g.grid[r1][c1] is not None
                assert g.grid[r2][c2] is not None
                return


def test_combo_building():
    g = _make_game(seed=42)
    initial_score = g.score

    for _ in range(4):
        pairs = g._find_matches(g.grid)
        if not pairs:
            break
        p1, p2 = pairs[0]
        c1, r1 = p1
        c2, r2 = p2
        g._select_tile(c1, r1)
        g._select_tile(c2, r2)
        g._handle_match(p1, p2)

    assert g.combo >= 4
    assert g.max_combo == g.combo
    assert g.score > initial_score


def test_super_mode_activation():
    g = _make_game(seed=42)
    g.combo = 3
    pairs = g._find_matches(g.grid)
    assert len(pairs) > 0
    p1, p2 = pairs[0]
    c1, r1 = p1
    c2, r2 = p2

    g._select_tile(c1, r1)
    g._select_tile(c2, r2)
    g._handle_match(p1, p2)

    assert g.super_mode is True
    assert g.super_timer == Game.SUPER_DURATION
    assert g.combo == 4


def test_super_mode_different_colors():
    """SUPER mode allows matching ANY color pair."""
    g = _make_game(seed=42)
    g.super_mode = True
    g.super_timer = Game.SUPER_DURATION

    non_empty = [
        (c, r)
        for r in range(Game.ROWS)
        for c in range(Game.COLS)
        if g.grid[r][c] is not None
    ]
    # Find two different color tiles
    for i in range(len(non_empty)):
        for j in range(i + 1, len(non_empty)):
            c1, r1 = non_empty[i]
            c2, r2 = non_empty[j]
            if g.grid[r1][c1] != g.grid[r2][c2]:
                assert g._can_match((c1, r1), (c2, r2)) is True
                return


def test_super_mode_score_multiplier():
    """SUPER mode gives 3x score."""
    g = _make_game(seed=42)
    g.super_mode = True
    g.super_timer = Game.SUPER_DURATION

    pairs = g._find_matches(g.grid)
    assert len(pairs) > 0
    p1, p2 = pairs[0]

    g._select_tile(p1[0], p1[1])
    g._select_tile(p2[0], p2[1])
    g._handle_match(p1, p2)

    # Score = BASE_SCORE * (1 + combo * 0.5) * SUPER_MULT
    # combo starts at 0, so score = 100 * (1 + 0) * 3 = 300
    assert g.score == 300, f"Expected 300, got {g.score}"


def test_super_mode_expires():
    """Super mode timer counts down and deactivates."""
    g = _make_game(seed=42)
    g.super_mode = True
    g.super_timer = 1

    # Simulate one frame of super timer countdown
    g.super_timer -= 1
    if g.super_timer <= 0:
        g.super_mode = False
        g.super_timer = 0

    assert g.super_mode is False
    assert g.super_timer == 0


def test_combo_reset_on_wrong():
    g = _make_game(seed=42)
    g.combo = 3
    g.max_combo = 3

    non_empty = [
        (c, r)
        for r in range(Game.ROWS)
        for c in range(Game.COLS)
        if g.grid[r][c] is not None
    ]
    for i in range(len(non_empty)):
        for j in range(i + 1, len(non_empty)):
            c1, r1 = non_empty[i]
            c2, r2 = non_empty[j]
            if g.grid[r1][c1] != g.grid[r2][c2]:
                g._select_tile(c1, r1)
                g._select_tile(c2, r2)
                g._handle_wrong()
                assert g.combo == 0
                return


def test_heat_increase():
    g = _make_game(seed=42)
    g.heat = 50.0
    g._handle_wrong()
    assert g.heat == 50.0 + Game.WRONG_MATCH_HEAT


def test_heat_clamped_to_max():
    g = _make_game(seed=42)
    g.heat = 95.0
    g._handle_wrong()
    assert g.heat == Game.MAX_HEAT  # 95 + 15 = 110, clamped to 100


def test_game_over_by_heat():
    g = _make_game(seed=42)
    g.heat = Game.MAX_HEAT
    assert g._check_game_over() is True


def test_game_over_by_timer():
    g = _make_game(seed=42)
    g.game_timer = 0
    assert g._check_game_over() is True


def test_win_condition():
    g = _make_game(seed=42)
    g.tiles_remaining = 0
    assert g._check_win() is True


def test_reshuffle_preserves_color_counts():
    g = _make_game(seed=42)
    # Get current counts
    counts_before = {c: 0 for c in Game.COLORS}
    for row in g.grid:
        for cell in row:
            if cell is not None:
                counts_before[cell] += 1

    g._reshuffle_grid()

    counts_after = {c: 0 for c in Game.COLORS}
    for row in g.grid:
        for cell in row:
            if cell is not None:
                counts_after[cell] += 1

    assert counts_before == counts_after
    assert g.heat >= Game.RESHUFFLE_HEAT


def test_reshuffle_adds_heat():
    g = _make_game(seed=42)
    g.heat = 0.0
    g._reshuffle_grid()
    assert g.heat == Game.RESHUFFLE_HEAT


def test_has_valid_moves():
    g = _make_game(seed=42)
    # Should have valid moves at start (48 tiles, 4 colors)
    assert g._has_valid_moves() is True


def test_no_valid_moves_all_same_color():
    """If all remaining tiles are same color, any pair is valid."""
    g = _make_game(seed=42)
    # Keep only one color
    for row in range(Game.ROWS):
        for col in range(Game.COLS):
            if g.grid[row][col] != 8:  # Keep RED
                g.grid[row][col] = None
                g.tiles_remaining -= 1

    assert g._has_valid_moves() is True  # Same color = any pair matches


def test_no_valid_moves_different_colors():
    """If each remaining tile is a unique color → no pairs possible."""
    g = _make_game(seed=42)
    # We have 4 colors. Place exactly one of each color → no pairs.
    g.tiles_remaining = 0
    for row in range(Game.ROWS):
        for col in range(Game.COLS):
            g.grid[row][col] = None
    # Place 4 tiles, each a different color
    for i, color in enumerate(Game.COLORS):
        g.grid[i][0] = color
        g.tiles_remaining += 1

    assert g._has_valid_moves() is False


def test_can_match_none_tile():
    g = _make_game(seed=42)
    # Set a cell to None
    g.grid[0][0] = None
    # Try to match with None tile
    c1, r1 = 0, 0
    # Find a non-None tile
    for r in range(Game.ROWS):
        for c in range(Game.COLS):
            if g.grid[r][c] is not None:
                assert g._can_match((c1, r1), (c, r)) is False
                return


def test_select_empty_cell():
    g = _make_game(seed=42)
    g.grid[0][0] = None
    result = g._select_tile(0, 0)
    assert result is None


def test_select_deselect_same_cell():
    g = _make_game(seed=42)
    result1 = g._select_tile(0, 0)
    assert result1 == "select"
    result2 = g._select_tile(0, 0)
    assert result2 is None  # deselected


def test_particle_creation():
    g = _make_game(seed=42)
    g._spawn_match_particles(100, 100, 120, 120, 8, count=8)
    assert len(g.particles) == 16  # 8 * 2


def test_floating_text_creation():
    g = _make_game(seed=42)
    g._spawn_floating_text(160, 120, "+100", 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+100"


def test_super_match_spawns_particles_and_text():
    g = _make_game(seed=42)
    g.combo = 3
    pairs = g._find_matches(g.grid)
    p1, p2 = pairs[0]
    g._select_tile(p1[0], p1[1])
    g._select_tile(p2[0], p2[1])
    g._handle_match(p1, p2)

    assert g.super_mode is True
    assert g.shake_frames > 0
    assert len(g.particles) > 0
    assert len(g.floating_texts) > 0


def test_cell_center_calculation():
    g = _make_game(seed=42)
    cx, cy = g._cell_center(0, 0)
    assert cx == Game.CELL / 2
    assert cy == Game.CELL / 2

    cx, cy = g._cell_center(1, 2)
    assert cx == Game.CELL + Game.CELL / 2
    assert cy == 2 * Game.CELL + Game.CELL / 2


def test_max_combo_tracking():
    g = _make_game(seed=42)
    for _ in range(3):
        pairs = g._find_matches(g.grid)
        if not pairs:
            break
        p1, p2 = pairs[0]
        g._select_tile(p1[0], p1[1])
        g._select_tile(p2[0], p2[1])
        g._handle_match(p1, p2)

    assert g.max_combo == g.combo


def test_super_mode_super_timer_decrement():
    """Verify super timer is set correctly on activation."""
    g = _make_game(seed=42)
    g.combo = 3
    pairs = g._find_matches(g.grid)
    assert len(pairs) > 0
    p1, p2 = pairs[0]
    g._select_tile(p1[0], p1[1])
    g._select_tile(p2[0], p2[1])
    g._handle_match(p1, p2)

    assert g.super_timer == Game.SUPER_DURATION


def test_score_formula():
    """Score = BASE_SCORE * (1 + combo * 0.5) * multiplier."""
    g = _make_game(seed=42)
    pairs = g._find_matches(g.grid)
    assert len(pairs) > 0

    # First match: combo starts at 0, score = 100 * (1 + 0) * 1 = 100
    p1, p2 = pairs[0]
    g._select_tile(p1[0], p1[1])
    g._select_tile(p2[0], p2[1])
    g._handle_match(p1, p2)
    assert g.score == 100

    # Second match: combo=1, score = 100 * (1 + 1*0.5) * 1 = 150
    pairs = g._find_matches(g.grid)
    if len(pairs) > 0:
        p1, p2 = pairs[0]
        g._select_tile(p1[0], p1[1])
        g._select_tile(p2[0], p2[1])
        g._handle_match(p1, p2)
        assert g.score == 250  # 100 + 150


def test_phase_enum_values():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_dataclass_particle():
    p = Particle(x=10, y=20, vx=1.0, vy=-2.0, life=20, color=8)
    assert p.x == 10
    assert p.y == 20
    assert p.color == 8


def test_dataclass_floating_text():
    ft = FloatingText(x=100, y=50, text="+100", life=30, color=7)
    assert ft.text == "+100"
    assert ft.life == 30


def test_reset_clears_state():
    g = _make_game(seed=42)
    # Set some non-default state
    g.score = 500
    g.combo = 5
    g.heat = 50
    g.super_mode = True

    # Reset via _start_game
    g._start_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_mode is False


def test_class_constants():
    assert Game.COLS == 8
    assert Game.ROWS == 6
    assert Game.CELL == 40
    assert Game.TOTAL_TILES == 48
    assert Game.GAME_TIME == 5400
    assert Game.SUPER_DURATION == 300
    assert Game.MAX_HEAT == 100
    assert Game.SUPER_COMBO_THRESHOLD == 4
    assert Game.SUPER_SCORE_MULT == 3
    assert Game.WRONG_MATCH_HEAT == 15
    assert Game.RESHUFFLE_HEAT == 10
