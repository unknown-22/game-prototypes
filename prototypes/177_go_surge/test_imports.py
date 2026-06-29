"""test_imports.py — Headless logic tests for 177_go_surge (Liberty Chain)."""
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/177_go_surge")

from main import (
    CELL,
    COMBO_THRESHOLD,
    GRID_SIZE,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_PER_MISMATCH,
    INITIAL_STONES,
    MAX_STONES,
    OX,
    OY,
    STONE_COLORS,
    SUPER_DURATION,
    SUPER_THRESHOLD,
    FloatingText,
    Game,
    Particle,
    Phase,
    Stone,
    _make_game,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _blank_game() -> Game:
    """Create a game with an empty grid (no initial stones)."""
    g = Game.__new__(Game)
    g._font = None
    g._rng = random.Random(42)
    # Manually init state without placing initial stones
    g.phase = Phase.PLAYING
    g.grid = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]
    g.active_color = 0
    g.last_color = -1
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.heat = 0.0
    g.stones_placed = 0
    g.super_mode = False
    g.super_timer = 0
    g.capture_pending = False
    g.particles = []
    g.floating_texts = []
    g._spawn_timer = 180
    return g


# ═══════════════════════════════════════════════════════════════════════════════
# Initial State
# ═══════════════════════════════════════════════════════════════════════════════


def test_make_game_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.capture_pending is False
    assert g.active_color == 0
    assert g.last_color == -1
    assert g.stones_placed == INITIAL_STONES
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_initial_stones_placed() -> None:
    g = _make_game()
    count = sum(1 for r in range(GRID_SIZE) for c in range(GRID_SIZE) if g.grid[r][c] is not None)
    assert count == INITIAL_STONES
    assert g.stones_placed == INITIAL_STONES


# ═══════════════════════════════════════════════════════════════════════════════
# Stone Placement
# ═══════════════════════════════════════════════════════════════════════════════


def test_place_stone_success() -> None:
    g = _blank_game()
    assert g._place_stone(3, 3) is True
    assert g.grid[3][3] is not None
    assert g.grid[3][3].color == 0  # type: ignore[union-attr]
    assert g.grid[3][3].col == 3  # type: ignore[union-attr]
    assert g.grid[3][3].row == 3  # type: ignore[union-attr]
    assert g.stones_placed == 1


def test_place_stone_occupied() -> None:
    g = _blank_game()
    g._place_stone(3, 3)
    assert g._place_stone(3, 3) is False
    assert g.stones_placed == 1


def test_place_stone_edge_positions() -> None:
    g = _blank_game()
    assert g._place_stone(0, 0) is True
    assert g._place_stone(6, 0) is True
    assert g._place_stone(0, 6) is True
    assert g._place_stone(6, 6) is True
    assert g.stones_placed == 4


# ═══════════════════════════════════════════════════════════════════════════════
# Combo Tracking
# ═══════════════════════════════════════════════════════════════════════════════


def test_combo_same_color_increments() -> None:
    g = _blank_game()
    g.active_color = 0
    g._place_stone(0, 0)  # combo → 1
    assert g.combo == 1
    g._place_stone(1, 0)  # same color, combo → 2
    assert g.combo == 2
    g._place_stone(2, 0)  # same color, combo → 3
    assert g.combo == 3


def test_combo_different_color_resets() -> None:
    g = _blank_game()
    g.active_color = 0
    g._place_stone(0, 0)  # combo → 1
    g.active_color = 1
    g._place_stone(1, 0)  # different color, combo → 1
    assert g.combo == 1


def test_combo_does_not_go_below_one() -> None:
    g = _blank_game()
    g.active_color = 0
    g._place_stone(0, 0)
    assert g.combo == 1
    g.active_color = 1
    g._place_stone(1, 0)
    assert g.combo == 1  # resets to 1, not 0


def test_max_combo_tracks_highest() -> None:
    g = _blank_game()
    g.active_color = 0
    g._place_stone(0, 0)  # combo=1, max=1
    assert g.max_combo == 1
    g._place_stone(1, 0)  # combo=2, max=2
    g._place_stone(2, 0)  # combo=3, max=3
    g.active_color = 1
    g._place_stone(3, 0)  # combo=1, max still 3
    assert g.combo == 1
    assert g.max_combo == 3


# ═══════════════════════════════════════════════════════════════════════════════
# HEAT System
# ═══════════════════════════════════════════════════════════════════════════════


def test_heat_on_mismatch() -> None:
    g = _blank_game()
    g.active_color = 0
    g._place_stone(0, 0)  # first stone, no mismatch
    assert g.heat == 0.0
    g.active_color = 1
    g._place_stone(1, 0)  # mismatch! heat += 20
    assert abs(g.heat - HEAT_PER_MISMATCH) < 0.01


def test_heat_accumulates() -> None:
    g = _blank_game()
    for i in range(5):
        g.active_color = i % 4
        g._place_stone(i, 0)
    # After 5 alternating colors: 0,1,2,3,0 → mismatches on 1,2,3,0 (4 mismatches)
    assert abs(g.heat - 4 * HEAT_PER_MISMATCH) < 0.01


def test_heat_capped_at_max() -> None:
    g = _blank_game()
    g.heat = HEAT_MAX - 5
    g.active_color = 0
    g._place_stone(0, 0)  # first stone no heat
    g.last_color = 1  # force mismatch next
    g.active_color = 2
    g._place_stone(1, 0)  # mismatch, heat += 20 but capped
    assert abs(g.heat - HEAT_MAX) < 0.01


def test_heat_decay() -> None:
    g = _blank_game()
    g.heat = 50.0
    result = g._update_heat()
    assert result is False
    assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.01


def test_heat_decay_floor_zero() -> None:
    g = _blank_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


def test_heat_game_over_at_max() -> None:
    g = _blank_game()
    g.heat = HEAT_MAX
    result = g._update_heat()
    assert result is True
    assert g.phase == Phase.GAME_OVER


def test_heat_below_max_no_game_over() -> None:
    g = _blank_game()
    g.heat = HEAT_MAX - 0.1
    result = g._update_heat()
    assert result is False
    assert g.phase == Phase.PLAYING


# ═══════════════════════════════════════════════════════════════════════════════
# SUPER Mode
# ═══════════════════════════════════════════════════════════════════════════════


def test_super_mode_activates_at_threshold() -> None:
    g = _blank_game()
    g.active_color = 0
    g.last_color = 0
    g.combo = SUPER_THRESHOLD - 1  # combo=4
    g._place_stone(0, 0)  # combo becomes 5 → SUPER
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_mode_not_activated_below_threshold() -> None:
    g = _blank_game()
    g.active_color = 0
    g.last_color = 0
    g.combo = COMBO_THRESHOLD - 1  # combo=2
    g._place_stone(0, 0)  # combo becomes 3 → capture but not super
    assert g.super_mode is False


def test_super_timer_decrements() -> None:
    g = _blank_game()
    g.super_mode = True
    g.super_timer = 10
    g._update_super()
    assert g.super_timer == 9
    assert g.super_mode is True


def test_super_mode_deactivates_on_timer_expiry() -> None:
    g = _blank_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_timer == 0
    assert g.super_mode is False


def test_super_noop_when_inactive() -> None:
    g = _blank_game()
    g.super_mode = False
    g.super_timer = 0
    g._update_super()
    assert g.super_mode is False
    assert g.super_timer == 0


# ═══════════════════════════════════════════════════════════════════════════════
# BFS Group and Liberty Counting
# ═══════════════════════════════════════════════════════════════════════════════


def test_bfs_single_isolated_stone() -> None:
    g = _blank_game()
    g.grid[3][3] = Stone(color=0, col=3, row=3)
    group = g._bfs_group(3, 3, 0)
    assert group == {(3, 3)}


def test_bfs_connected_group() -> None:
    g = _blank_game()
    # Place stones at grid positions: grid[row][col]
    # (3,3): grid[3][3], (3,4): grid[4][3], (4,4): grid[4][4], (2,3): grid[3][2]
    g.grid[3][3] = Stone(color=0, col=3, row=3)  # (3,3)
    g.grid[4][3] = Stone(color=0, col=3, row=4)  # (3,4) — below (3,3)
    g.grid[4][4] = Stone(color=0, col=4, row=4)  # (4,4) — right of (3,4)
    g.grid[3][2] = Stone(color=0, col=2, row=3)  # (2,3) — left of (3,3)
    group = g._bfs_group(3, 3, 0)
    assert len(group) == 4
    assert (3, 3) in group
    assert (3, 4) in group
    assert (4, 4) in group
    assert (2, 3) in group


def test_bfs_different_color_not_included() -> None:
    g = _blank_game()
    g.grid[3][3] = Stone(color=0, col=3, row=3)
    g.grid[3][4] = Stone(color=1, col=3, row=4)  # different color
    group = g._bfs_group(3, 3, 0)
    assert group == {(3, 3)}


def test_bfs_empty_cell_not_explored() -> None:
    g = _blank_game()
    g.grid[3][3] = Stone(color=0, col=3, row=3)
    # (3,4) is empty, should not be in group
    group = g._bfs_group(3, 3, 0)
    assert group == {(3, 3)}


def test_count_liberties_single_stone() -> None:
    g = _blank_game()
    g.grid[3][3] = Stone(color=0, col=3, row=3)
    liberties = g._count_liberties({(3, 3)})
    assert liberties == 4  # all 4 adjacent are empty


def test_count_liberties_zero_when_surrounded() -> None:
    g = _blank_game()
    g.grid[3][3] = Stone(color=0, col=3, row=3)
    g.grid[3][2] = Stone(color=1, col=3, row=2)  # top
    g.grid[2][3] = Stone(color=1, col=2, row=3)  # left
    g.grid[4][3] = Stone(color=1, col=4, row=3)  # right
    g.grid[3][4] = Stone(color=1, col=3, row=4)  # bottom
    liberties = g._count_liberties({(3, 3)})
    assert liberties == 0


def test_count_liberties_group_shares_liberties() -> None:
    g = _blank_game()
    g.grid[3][3] = Stone(color=0, col=3, row=3)
    g.grid[4][3] = Stone(color=0, col=4, row=3)
    # (3,3) liberties: (3,2),(2,3),(3,4) = 3 (4,3 is occupied by ally)
    # (4,3) liberties: (4,2),(4,4),(5,3) = 3 (3,3 is occupied by ally)
    # Shared liberties: (4,3)-(3,3) connection is internal
    # Union: {(3,2),(2,3),(3,4),(4,2),(4,4),(5,3)} = 6
    liberties = g._count_liberties({(3, 3), (4, 3)})
    assert liberties == 6


def test_count_liberties_edge_stone() -> None:
    g = _blank_game()
    g.grid[0][0] = Stone(color=0, col=0, row=0)
    liberties = g._count_liberties({(0, 0)})
    assert liberties == 2  # only right and down are on board


# ═══════════════════════════════════════════════════════════════════════════════
# Capture (Normal Mode)
# ═══════════════════════════════════════════════════════════════════════════════


def test_normal_capture_surrounded_group() -> None:
    """Place active-color stones around an enemy group → BFS capture."""
    g = _blank_game()
    # Place an enemy group (color=1) at center — two stones at (3,3) and (3,4)
    # grid positions: grid[3][3]=(3,3), grid[4][3]=(3,4)
    g.grid[3][3] = Stone(color=1, col=3, row=3)  # (3,3)
    g.grid[4][3] = Stone(color=1, col=3, row=4)  # (3,4)
    g.stones_placed = 2

    # Surround with active-color stones (color=0)
    # Liberties for group {(3,3),(3,4)}: above (3,2),(3,5), left (2,3),(2,4), right (4,3),(4,4)
    # grid: grid[2][3]=(3,2), grid[5][3]=(3,5), grid[3][2]=(2,3), grid[4][2]=(2,4), grid[3][4]=(4,3), grid[4][4]=(4,4)
    surrounds = [
        (2, 3),  # above (3,2)
        (5, 3),  # below (3,5)
        (3, 2),  # left (2,3)
        (4, 2),  # left (2,4)
        (3, 4),  # right (4,3)
        (4, 4),  # right (4,4)
    ]
    for row, col in surrounds:
        g.grid[row][col] = Stone(color=0, col=col, row=row)
        g.stones_placed += 1

    g.active_color = 0
    g.combo = COMBO_THRESHOLD
    g.capture_pending = True

    captured = g._process_capture()
    assert captured == 2
    assert g.grid[3][3] is None  # (3,3) removed
    assert g.grid[4][3] is None  # (3,4) removed
    assert g.score > 0


def test_normal_capture_group_with_liberties_not_captured() -> None:
    """Enemy group with liberties should not be captured."""
    g = _blank_game()
    g.grid[3][3] = Stone(color=1, col=3, row=3)
    g.grid[3][4] = Stone(color=1, col=3, row=4)
    g.stones_placed = 2

    # Partially surround — leave (4,2) open as liberty
    for col, row in [(3, 2), (2, 3), (2, 4), (4, 3), (4, 4), (3, 5), (4, 5)]:
        g.grid[row][col] = Stone(color=0, col=col, row=row)
        g.stones_placed += 1
    # (4,2) is empty = liberty

    g.active_color = 0
    g.combo = COMBO_THRESHOLD
    g.capture_pending = True

    captured = g._process_capture()
    assert captured == 0
    assert g.grid[3][3] is not None
    assert g.grid[3][4] is not None


def test_capture_only_enemy_stones_not_own() -> None:
    """Capture should not remove active-color stones."""
    g = _blank_game()
    # One enemy stone surrounded by active-color
    g.grid[3][3] = Stone(color=1, col=3, row=3)
    g.active_color = 0
    # Surround with active-color stones
    g.grid[3][2] = Stone(color=0, col=3, row=2)
    g.grid[2][3] = Stone(color=0, col=2, row=3)
    g.grid[4][3] = Stone(color=0, col=4, row=3)
    g.grid[3][4] = Stone(color=0, col=3, row=4)
    g.stones_placed = 5

    g.combo = COMBO_THRESHOLD
    g.capture_pending = True

    captured = g._process_capture()
    assert captured == 1
    assert g.grid[3][3] is None  # enemy removed
    # Own stones remain
    assert g.grid[3][2] is not None
    assert g.grid[2][3] is not None
    assert g.grid[4][3] is not None


def test_capture_updates_stones_placed() -> None:
    g = _blank_game()
    # Enemy group at (3,3) and (3,4)
    g.grid[3][3] = Stone(color=1, col=3, row=3)  # (3,3)
    g.grid[4][3] = Stone(color=1, col=3, row=4)  # (3,4)
    g.stones_placed = 2

    surrounds = [
        (2, 3), (5, 3), (3, 2), (4, 2), (3, 4), (4, 4),
    ]
    for row, col in surrounds:
        g.grid[row][col] = Stone(color=0, col=col, row=row)
        g.stones_placed += 1
    # stones_placed = 2 + 6 = 8

    g.active_color = 0
    g.combo = COMBO_THRESHOLD
    g.capture_pending = True

    g._process_capture()
    assert g.stones_placed == 6  # 8 - 2 captured


def test_capture_resets_pending_flag() -> None:
    g = _blank_game()
    g.capture_pending = True
    g.combo = COMBO_THRESHOLD
    g._process_capture()
    assert g.capture_pending is False


def test_capture_scoring_formula() -> None:
    """Score = captured_count × combo."""
    g = _blank_game()
    g.grid[3][3] = Stone(color=1, col=3, row=3)
    g.grid[3][2] = Stone(color=0, col=3, row=2)
    g.grid[2][3] = Stone(color=0, col=2, row=3)
    g.grid[4][3] = Stone(color=0, col=4, row=3)
    g.grid[3][4] = Stone(color=0, col=3, row=4)
    g.grid[0][0] = Stone(color=0, col=0, row=0)  # not part of surround, for visit tracking
    g.stones_placed = 6

    g.active_color = 0
    g.combo = 4  # combo multiplier
    g.score = 0
    g.capture_pending = True

    g._process_capture()
    # 1 enemy captured × combo=4 = 4
    assert g.score == 4


# ═══════════════════════════════════════════════════════════════════════════════
# Capture (SUPER Mode)
# ═══════════════════════════════════════════════════════════════════════════════


def test_super_capture_all_enemy_groups() -> None:
    """SUPER mode captures all enemy groups regardless of liberties."""
    g = _blank_game()
    # Place two separate enemy groups — neither surrounded
    g.grid[3][3] = Stone(color=1, col=3, row=3)  # has liberties
    g.grid[5][5] = Stone(color=2, col=5, row=5)  # has liberties
    g.stones_placed = 2

    g.active_color = 0
    g.super_mode = True
    g.combo = SUPER_THRESHOLD
    g.capture_pending = True

    captured = g._process_capture()
    assert captured == 2  # both captured
    assert g.grid[3][3] is None
    assert g.grid[5][5] is None


def test_super_capture_triple_score() -> None:
    """SUPER mode: score = captured × combo × 3."""
    g = _blank_game()
    g.grid[3][3] = Stone(color=1, col=3, row=3)
    g.grid[5][5] = Stone(color=1, col=5, row=5)
    g.stones_placed = 2

    g.active_color = 0
    g.super_mode = True
    g.combo = 5
    g.score = 0
    g.capture_pending = True

    g._process_capture()
    # 2 captured × combo=5 × 3 = 30
    assert g.score == 30


# ═══════════════════════════════════════════════════════════════════════════════
# Capture Trigger (capture_pending)
# ═══════════════════════════════════════════════════════════════════════════════


def test_capture_pending_set_at_combo_threshold() -> None:
    g = _blank_game()
    g.active_color = 0
    g.last_color = 0
    g.combo = COMBO_THRESHOLD - 1  # combo=2
    g._place_stone(0, 0)  # combo becomes 3
    assert g.capture_pending is True


def test_capture_pending_not_set_below_threshold() -> None:
    g = _blank_game()
    g.active_color = 0
    g.last_color = 0
    g.combo = 1
    g._place_stone(0, 0)  # combo becomes 2
    assert g.capture_pending is False


# ═══════════════════════════════════════════════════════════════════════════════
# Neutral Stone Spawning
# ═══════════════════════════════════════════════════════════════════════════════


def test_spawn_neutral_stone_on_empty() -> None:
    g = _blank_game()
    g._spawn_neutral_stone()
    assert g.stones_placed == 1
    # One cell should now be occupied
    count = sum(1 for r in range(GRID_SIZE) for c in range(GRID_SIZE) if g.grid[r][c] is not None)
    assert count == 1


def test_spawn_neutral_stone_at_max_capacity() -> None:
    g = _blank_game()
    g.stones_placed = MAX_STONES
    g._spawn_neutral_stone()
    # No new stone — stones_placed unchanged
    assert g.stones_placed == MAX_STONES


def test_spawn_neutral_stone_board_full() -> None:
    g = _blank_game()
    # Fill entire board
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            g.grid[r][c] = Stone(color=0, col=c, row=r)
    g.stones_placed = GRID_SIZE * GRID_SIZE
    g._spawn_neutral_stone()
    assert g.stones_placed == GRID_SIZE * GRID_SIZE  # unchanged


# ═══════════════════════════════════════════════════════════════════════════════
# Board Full Check
# ═══════════════════════════════════════════════════════════════════════════════


def test_board_not_full_initially() -> None:
    g = _blank_game()
    assert g._check_board_full() is False


def test_board_full_all_cells_occupied() -> None:
    g = _blank_game()
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            g.grid[r][c] = Stone(color=0, col=c, row=r)
    assert g._check_board_full() is True


# ═══════════════════════════════════════════════════════════════════════════════
# Grid Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def test_grid_to_screen_origin() -> None:
    x, y = Game._grid_to_screen(0, 0)
    assert x == OX
    assert y == OY


def test_grid_to_screen_offset() -> None:
    x, y = Game._grid_to_screen(3, 4)
    assert x == OX + 3 * CELL
    assert y == OY + 4 * CELL


def test_screen_to_grid_valid() -> None:
    result = Game._screen_to_grid(OX + 3 * CELL, OY + 4 * CELL)
    assert result == (3, 4)


def test_screen_to_grid_out_of_bounds() -> None:
    assert Game._screen_to_grid(-10, -10) is None
    assert Game._screen_to_grid(500, 500) is None


def test_screen_to_grid_near_intersection() -> None:
    """Should round to nearest intersection."""
    result = Game._screen_to_grid(OX + 3 * CELL + 5, OY + 4 * CELL - 3)
    assert result == (3, 4)


def test_coordinate_roundtrip() -> None:
    for col in range(GRID_SIZE):
        for row in range(GRID_SIZE):
            sx, sy = Game._grid_to_screen(col, row)
            result = Game._screen_to_grid(sx, sy)
            assert result == (col, row)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════════


def test_stone_dataclass() -> None:
    s = Stone(color=2, col=3, row=4)
    assert s.color == 2
    assert s.col == 3
    assert s.row == 4


def test_particle_dataclass() -> None:
    p = Particle(x=10.5, y=20.3, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.x == 10.5
    assert p.y == 20.3
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+10", life=30, color=10)
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.vy == -0.6


# ═══════════════════════════════════════════════════════════════════════════════
# Particle System
# ═══════════════════════════════════════════════════════════════════════════════


def test_update_particles_decrements_life() -> None:
    g = _blank_game()
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=5, color=8)]
    g._update_particles()
    assert g.particles[0].life == 4


def test_update_particles_removes_dead() -> None:
    g = _blank_game()
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0  # life=1 → decrement to 0 → removed


def test_update_particles_moves_position() -> None:
    g = _blank_game()
    g.particles = [Particle(x=10.0, y=20.0, vx=1.5, vy=-2.5, life=10, color=8)]
    g._update_particles()
    assert abs(g.particles[0].x - 11.5) < 0.01
    assert abs(g.particles[0].y - 17.5) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# Floating Text System
# ═══════════════════════════════════════════════════════════════════════════════


def test_update_floating_texts_moves_up() -> None:
    g = _blank_game()
    g.floating_texts = [FloatingText(x=100, y=50, text="test", life=10, color=7)]
    g._update_floating_texts()
    assert abs(g.floating_texts[0].y - (50 + (-0.6))) < 0.01


def test_update_floating_texts_removes_dead() -> None:
    g = _blank_game()
    g.floating_texts = [FloatingText(x=100, y=50, text="test", life=1, color=7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_spawn_floating_text() -> None:
    g = _blank_game()
    g._spawn_floating_text(100, 50, "+100", 10, 40)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+100"
    assert g.floating_texts[0].life == 40
    assert g.floating_texts[0].color == 10


# ═══════════════════════════════════════════════════════════════════════════════
# Capture Effects (Particles + Texts)
# ═══════════════════════════════════════════════════════════════════════════════


def test_capture_spawns_particles_and_texts() -> None:
    g = _blank_game()
    g.grid[3][3] = Stone(color=1, col=3, row=3)
    g.grid[3][2] = Stone(color=0, col=3, row=2)
    g.grid[2][3] = Stone(color=0, col=2, row=3)
    g.grid[4][3] = Stone(color=0, col=4, row=3)
    g.grid[3][4] = Stone(color=0, col=3, row=4)
    g.stones_placed = 5
    g.active_color = 0
    g.combo = COMBO_THRESHOLD
    g.capture_pending = True

    g._process_capture()
    assert len(g.particles) > 0
    assert len(g.floating_texts) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Reset
# ═══════════════════════════════════════════════════════════════════════════════


def test_reset_clears_state() -> None:
    g = _make_game()
    # Modify state
    g.combo = 10
    g.heat = 80
    g.score = 999
    g.super_mode = True
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=5, color=8)]
    g.grid[0][0] = Stone(color=2, col=0, row=0)

    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.combo == 0
    assert g.score == 0
    assert g.heat == 0.0
    assert g.super_mode is False


# ═══════════════════════════════════════════════════════════════════════════════
# Phase Enum
# ═══════════════════════════════════════════════════════════════════════════════


def test_phase_enum_values() -> None:
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.GAME_OVER == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════


def test_constants() -> None:
    assert GRID_SIZE == 7
    assert CELL == 28
    assert COMBO_THRESHOLD == 3
    assert SUPER_THRESHOLD == 5
    assert SUPER_DURATION == 150
    assert HEAT_MAX == 100.0
    assert HEAT_PER_MISMATCH == 20.0
    assert HEAT_DECAY == 0.05
    assert MAX_STONES == 30
    assert INITIAL_STONES == 10
    assert len(STONE_COLORS) == 4


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


def test_last_color_defaults_negative_one() -> None:
    g = _blank_game()
    assert g.last_color == -1


def test_place_stone_then_capture_multiple_groups() -> None:
    """Place multiple isolated enemy stones, all surrounded."""
    g = _blank_game()
    # Fill center with active stones, leaving some pockets of enemy
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if (r, c) in [(3, 3), (5, 5)]:
                g.grid[r][c] = Stone(color=1, col=c, row=r)
            else:
                g.grid[r][c] = Stone(color=0, col=c, row=r)
    g.stones_placed = GRID_SIZE * GRID_SIZE

    g.active_color = 0
    g.combo = COMBO_THRESHOLD
    g.capture_pending = True

    captured = g._process_capture()
    assert captured == 2  # both enemy pockets captured


def test_super_mode_captures_own_color_too() -> None:
    """SUPER mode: BFS only skips active_color — all other colors captured regardless."""
    g = _blank_game()
    g.grid[3][3] = Stone(color=1, col=3, row=3)  # enemy
    g.grid[5][5] = Stone(color=0, col=5, row=5)  # own color — should NOT be captured
    g.stones_placed = 2
    g.active_color = 0
    g.super_mode = True
    g.combo = SUPER_THRESHOLD
    g.capture_pending = True

    captured = g._process_capture()
    assert captured == 1  # only color=1 captured
    assert g.grid[3][3] is None  # enemy removed
    assert g.grid[5][5] is not None  # own color remains


def test_no_capture_when_no_enemy_groups() -> None:
    g = _blank_game()
    # Only active-color stones
    g.grid[3][3] = Stone(color=0, col=3, row=3)
    g.stones_placed = 1
    g.active_color = 0
    g.combo = COMBO_THRESHOLD
    g.capture_pending = True

    captured = g._process_capture()
    assert captured == 0
    assert g.score == 0


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
