"""test_imports.py — Headless logic tests for Alchemy Drop prototype."""
from __future__ import annotations

import inspect
import sys

PROTO_DIR = "/home/unknown22/repos/game-prototypes/prototypes/011_alchemy_drop"
sys.path.insert(0, PROTO_DIR)

from main import (  # noqa: E402
    ALL_ELEMENTS,
    CLEAR_ANIM_FRAMES,
    DROP_BASE_SPEED,
    DROP_MIN_SPEED,
    ELEMENT_CHARS,
    ELEMENT_COLORS,
    ELEMENT_LABELS,
    GRID_COLS,
    GRID_ROWS,
    MATCH_MIN,
    SCREEN_W,
    SCREEN_H,
    SOFT_DROP_BONUS,
    SPEED_UP_SCORE,
    VISIBLE_OFFSET,
    Element,
    Game,
    Particle,
)


# ── Constants ────────────────────────────────────────────────────
def test_screen_dimensions() -> None:
    assert SCREEN_W == 256
    assert SCREEN_H == 256


def test_grid_dimensions() -> None:
    assert GRID_COLS == 8
    assert GRID_ROWS == 16
    assert VISIBLE_OFFSET == 2
    assert 0 <= VISIBLE_OFFSET < GRID_ROWS


def test_match_min() -> None:
    assert MATCH_MIN == 3


def test_drop_speeds() -> None:
    assert DROP_BASE_SPEED > 0
    assert 0 < DROP_MIN_SPEED <= DROP_BASE_SPEED


def test_score_incentives() -> None:
    assert SOFT_DROP_BONUS > 0
    assert SPEED_UP_SCORE > 0


def test_element_enum() -> None:
    assert len(ALL_ELEMENTS) == 5
    for elem in ALL_ELEMENTS:
        assert isinstance(elem, Element)


def test_element_mappings() -> None:
    for elem in ALL_ELEMENTS:
        assert elem in ELEMENT_COLORS
        assert elem in ELEMENT_LABELS
        assert elem in ELEMENT_CHARS
        assert 0 <= ELEMENT_COLORS[elem] <= 15
        assert len(ELEMENT_LABELS[elem]) == 3
        assert len(ELEMENT_CHARS[elem]) == 1


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=0.5, vy=-1.0, life=25, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.life == 25
    assert p.color == 8


# ── Game Class ───────────────────────────────────────────────────
def test_game_init_reset() -> None:
    g = Game.__new__(Game)
    g.reset()

    assert g.score == 0
    assert g.level == 1
    assert g.drop_speed == DROP_BASE_SPEED
    assert not g.game_over
    assert not g.resolving
    assert g.chain_mult == 1
    assert len(g.clearing) == 0
    assert g.clear_timer == 0
    assert len(g.particles) == 0
    assert g.falling_type is not None
    assert isinstance(g.falling_type, int)
    assert 0 <= g.falling_col < GRID_COLS
    assert g.falling_row == 0

    # Grid is properly sized
    assert len(g.grid) == GRID_ROWS
    for row in g.grid:
        assert len(row) == GRID_COLS


def test_can_place() -> None:
    g = Game.__new__(Game)
    g.reset()

    # Empty grid: can place in any valid position
    assert g._can_place(0, GRID_ROWS - 1)
    assert g._can_place(GRID_COLS - 1, 0)

    # Out of bounds
    assert not g._can_place(-1, 0)
    assert not g._can_place(GRID_COLS, 0)
    assert not g._can_place(0, GRID_ROWS)

    # Above grid is fine
    assert g._can_place(0, -1)

    # Occupied cell
    g.grid[5][3] = Element.FIRE.value
    assert not g._can_place(3, 5)
    assert g._can_place(3, 4)


def test_lock_block() -> None:
    g = Game.__new__(Game)
    g.reset()

    orig_type = g.falling_type
    orig_col = g.falling_col
    g.falling_row = 10  # force specific row

    g._lock_block()

    # Block is placed in grid
    assert g.grid[10][orig_col] == orig_type
    # _lock_block calls _scan_matches, which finds no matches
    # (single block), so resolving ends and a new block spawns.
    # The critical assertion: the block was placed and the game
    # continues (not game_over).
    assert not g.game_over
    assert g.falling_type is not None  # new block spawned


def test_spawn_block() -> None:
    g = Game.__new__(Game)
    g.reset()

    # Clear grid and spawn
    g.grid[0][GRID_COLS // 2] = None
    g._spawn_block()

    assert g.falling_type is not None
    assert isinstance(g.falling_type, int)
    assert g.falling_col == GRID_COLS // 2
    assert g.falling_row == 0
    assert not g.game_over


def test_spawn_block_game_over() -> None:
    g = Game.__new__(Game)
    g.reset()

    # Block the spawn position
    g.grid[0][GRID_COLS // 2] = Element.FIRE.value
    g._spawn_block()

    assert g.game_over
    assert g.falling_type is None


def test_scan_matches_horizontal() -> None:
    g = Game.__new__(Game)
    g.reset()

    # Place 3 FIRE horizontally
    for c in range(3):
        g.grid[10][c] = Element.FIRE.value
    g.resolving = True
    g.chain_mult = 1

    g._scan_matches()

    assert len(g.clearing) == 3
    assert g.clear_timer == CLEAR_ANIM_FRAMES
    # All 3 cells should be in clearing set
    clearing_set = set(g.clearing)
    assert (10, 0) in clearing_set
    assert (10, 1) in clearing_set
    assert (10, 2) in clearing_set


def test_scan_matches_vertical() -> None:
    g = Game.__new__(Game)
    g.reset()

    # Place 4 WATER vertically
    for r in range(5, 9):
        g.grid[r][2] = Element.WATER.value
    g.resolving = True
    g.chain_mult = 1

    g._scan_matches()

    assert len(g.clearing) == 4
    clearing_set = set(g.clearing)
    for r in range(5, 9):
        assert (r, 2) in clearing_set


def test_scan_matches_no_match() -> None:
    g = Game.__new__(Game)
    g.reset()

    # Only 2 blocks of same type — not enough
    g.grid[10][0] = Element.FIRE.value
    g.grid[10][1] = Element.FIRE.value
    g.resolving = True
    g.chain_mult = 1

    g._scan_matches()

    assert len(g.clearing) == 0
    assert g.resolving is False
    assert g.falling_type is not None  # new block spawned


def test_scan_matches_cross() -> None:
    """A cross pattern should find both horizontal and vertical matches."""
    g = Game.__new__(Game)
    g.reset()

    # T-shape: FIRE at (10,3), horizontal row of 3 FIREs at row 10 cols 1-3
    # and also FIRE at (9,3) to make the vertical match 2-long (not enough)
    # Better: an L-shape where both arms are 3+
    # Actually, let's just do a cross where horizontal and vertical both have 3+
    # Row 10: FIRE at cols 0,1,2,3,4,5  (horizontal run of 6)
    # Col 0: FIRE at rows 8,9,10 (vertical run of 3)
    for c in range(6):
        g.grid[10][c] = Element.FIRE.value
    for r in range(8, 11):
        g.grid[r][0] = Element.FIRE.value
    g.resolving = True
    g.chain_mult = 1

    g._scan_matches()

    # Horizontal: 6 cells at row 10
    # Vertical: 3 cells at col 0
    # Overlap: (10,0) counted once
    # Total: 6 + 3 - 1 = 8
    assert len(g.clearing) == 8
    assert g.clear_timer == CLEAR_ANIM_FRAMES


def test_resolve_clear() -> None:
    g = Game.__new__(Game)
    g.reset()

    initial_score = g.score
    # Place 3 matching blocks
    for c in range(3):
        g.grid[10][c] = Element.FIRE.value
    g.clearing = [(10, 0), (10, 1), (10, 2)]
    g.clear_timer = 1
    g.chain_mult = 2  # simulate second chain step

    g._resolve_clear()

    # Score increased: 3 blocks * 10 * 2 = 60
    assert g.score == initial_score + 60
    # Cells are cleared
    assert g.grid[10][0] is None
    assert g.grid[10][1] is None
    assert g.grid[10][2] is None
    # Chain mult increased
    assert g.chain_mult == 3
    # Particles spawned
    assert len(g.particles) > 0
    # Combo text shown
    assert g.combo_text == "x2 CHAIN!"
    assert g.combo_timer > 0


def test_resolve_clear_no_combo_text() -> None:
    g = Game.__new__(Game)
    g.reset()

    g.clearing = [(5, 0), (5, 1), (5, 2)]
    g.chain_mult = 1  # first step, no combo text

    g._resolve_clear()

    # No combo text for first chain step
    assert g.combo_text == ""


def test_apply_gravity() -> None:
    g = Game.__new__(Game)
    g.reset()

    # Place blocks with gaps
    g.grid[GRID_ROWS - 1][0] = Element.FIRE.value
    g.grid[GRID_ROWS - 3][0] = Element.WATER.value  # gap at row-2
    g.grid[GRID_ROWS - 4][0] = Element.EARTH.value

    moved = g._apply_gravity()

    assert moved is True
    # WATER should have fallen to GRID_ROWS-2
    assert g.grid[GRID_ROWS - 1][0] == Element.FIRE.value
    assert g.grid[GRID_ROWS - 2][0] == Element.WATER.value
    assert g.grid[GRID_ROWS - 3][0] == Element.EARTH.value
    assert g.grid[GRID_ROWS - 4][0] is None


def test_apply_gravity_no_gaps() -> None:
    g = Game.__new__(Game)
    g.reset()

    # Place blocks with no gaps
    for r in range(GRID_ROWS - 3, GRID_ROWS):
        g.grid[r][0] = Element.FIRE.value

    moved = g._apply_gravity()

    assert moved is False


def test_update_drop_speed() -> None:
    g = Game.__new__(Game)
    g.reset()

    g.score = SPEED_UP_SCORE * 2  # should be level 3
    g._update_drop_speed()

    assert g.level == 3
    assert g.drop_speed == max(DROP_MIN_SPEED, DROP_BASE_SPEED - 2 * 3)
    assert g.speed_text != ""
    assert g.speed_timer > 0


def test_reset_method_attributes() -> None:
    """Verify key state attributes are set in reset()."""
    g = Game.__new__(Game)
    g.reset()

    src = inspect.getsource(Game.reset)
    needed = [
        "self.grid",
        "self.score",
        "self.level",
        "self.drop_speed",
        "self.game_over",
        "self.particles",
        "self.chain_mult",
        "self.falling_type",
        "self.falling_col",
        "self.falling_row",
    ]
    for attr in needed:
        assert attr in src, f"reset() missing {attr}"


def test_methods_are_distinct() -> None:
    """Ensure no method name collisions (pitfall from previous prototypes)."""
    methods = [
        name for name, _ in inspect.getmembers(Game, inspect.isfunction)
    ]
    assert len(methods) == len(set(methods)), f"Duplicate methods: {methods}"
    # Verify key methods exist
    for name in ("reset", "update", "draw", "_scan_matches",
                 "_apply_gravity", "_resolve_clear", "_lock_block",
                 "_spawn_block", "_can_place", "_draw_grid",
                 "_draw_panel", "_draw_overlays", "_handle_input",
                 "_update_drop_speed", "_update_particles"):
        assert name in methods, f"Missing method: {name}"


def test_clear_anim_frame_count() -> None:
    """The solver check in update counts down clear_timer, then resolves."""
    g = Game.__new__(Game)
    g.reset()

    # Simulate a locked block that found matches
    g.resolving = True
    g.chain_mult = 1
    g.clearing = [(10, 0), (10, 1), (10, 2)]
    g.clear_timer = 1
    g.falling_type = None

    # Simulate update (which decrements clear_timer)
    g.clear_timer -= 1  # now 0
    assert g.clear_timer == 0
    initial_score = g.score
    g._resolve_clear()
    g._apply_gravity()
    g._scan_matches()

    # Score increased
    assert g.score > initial_score


def test_game_over_restart() -> None:
    g = Game.__new__(Game)
    g.reset()

    g.game_over = True
    g.score = 500

    g.reset()

    assert not g.game_over
    assert g.score == 0
    assert g.level == 1


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
