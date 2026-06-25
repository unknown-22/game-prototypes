"""test_imports.py — Headless logic tests for BINGO SURGE."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # type: ignore[import-not-found]
    BALL_LIFETIME,
    CALL_X,
    CALL_Y,
    COMBO_THRESHOLD,
    GAME_DURATION,
    GRID_SIZE,
    HEAT_DECAY,
    HEAT_MAX,
    SUPER_DURATION,
    BingoCell,
    CallBall,
    Game,
    Particle,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    """Create a Game with deterministic RNG."""
    g = Game()
    g.reset()
    g.rng = random.Random(seed)
    return g


def _make_blank_game(seed: int = 42) -> Game:
    """Create a Game with a clean grid (no random numbers colliding with tests)."""
    g = Game()
    g.reset()
    g.rng = random.Random(seed)
    # Overwrite grid with unique numbers (1-25) and all color=0, nothing marked
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            g.grid[r][c] = BingoCell(number=r * GRID_SIZE + c + 1, color=0)
    return g


# ── Grid Generation ──


def test_generate_grid_size():
    g = _make_game()
    grid = g._generate_grid()
    assert len(grid) == GRID_SIZE
    for row in grid:
        assert len(row) == GRID_SIZE


def test_generate_grid_unique_numbers():
    g = _make_game()
    grid = g._generate_grid()
    numbers = [cell.number for row in grid for cell in row]
    assert sorted(numbers) == list(range(1, 26))


def test_generate_grid_cell_types():
    g = _make_game()
    grid = g._generate_grid()
    for row in grid:
        for cell in row:
            assert isinstance(cell, BingoCell)
            assert cell.number in range(1, 26)
            assert cell.color in (0, 1, 2, 3)
            assert cell.marked is False


# ── Ball Spawning ──


def test_spawn_ball():
    g = _make_game()
    g.current_ball = None
    g._spawn_ball()
    assert g.current_ball is not None
    assert isinstance(g.current_ball, CallBall)
    assert 1 <= g.current_ball.number <= 25
    assert g.current_ball.color in (0, 1, 2, 3)
    assert g.current_ball.timer == float(BALL_LIFETIME)
    assert g.current_ball.alive is True


# ── Handle Click: Match ──


def test_handle_click_perfect_match():
    """Both number AND color match = match. _handle_click(col, row)."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.current_ball = CallBall(number=1, color=2, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=1, color=2)  # grid[row][col]

    result = g._handle_click(0, 0)  # col=0, row=0 → grid[0][0]
    assert result == "match"
    assert g.combo == 1
    assert g.score >= 10


def test_handle_click_match_updates_max_combo():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g.max_combo = 3
    g.current_ball = CallBall(number=13, color=1, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[2][2] = BingoCell(number=13, color=1)

    g._handle_click(2, 2)  # col=2, row=2 → grid[2][2]
    assert g.combo == 4
    assert g.max_combo == 4


def test_handle_click_match_clears_ball():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.current_ball = CallBall(number=2, color=0, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][1] = BingoCell(number=2, color=0)

    g._handle_click(1, 0)  # col=1, row=0 → grid[0][1]
    assert g.current_ball is None


# ── Handle Click: Mismatch ──


def test_handle_click_number_mismatch():
    """Number doesn't match → mismatch."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.current_ball = CallBall(number=7, color=0, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=9, color=0)

    result = g._handle_click(0, 0)
    assert result == "mismatch"
    assert g.heat == 15.0
    assert g.combo == 0


def test_handle_click_color_mismatch():
    """Color doesn't match → mismatch."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.current_ball = CallBall(number=7, color=0, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=7, color=1)

    result = g._handle_click(0, 0)
    assert result == "mismatch"


def test_handle_click_mismatch_resets_combo():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.combo = 4
    g.current_ball = CallBall(number=1, color=0, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=2, color=1)

    g._handle_click(0, 0)
    assert g.combo == 0


# ── Handle Click: Edge Cases ──


def test_handle_click_already_marked():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.current_ball = CallBall(number=1, color=0, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=1, color=0, marked=True)

    result = g._handle_click(0, 0)
    assert result == "already_marked"


def test_handle_click_no_ball():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.current_ball = None
    g.grid[0][0] = BingoCell(number=1, color=0)

    result = g._handle_click(0, 0)
    assert result == "no_ball"


def test_handle_click_wrong_phase():
    g = _make_blank_game()
    g.phase = Phase.TITLE
    g.current_ball = CallBall(number=1, color=0, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=1, color=0)

    result = g._handle_click(0, 0)
    assert result == "no_play"


# ── SUPER Activation ──


def test_super_activation():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.combo = COMBO_THRESHOLD - 1  # 4
    g.super_timer = 0
    g.current_ball = CallBall(number=10, color=3, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=10, color=3)

    g._handle_click(0, 0)
    assert g.combo == COMBO_THRESHOLD  # 5
    assert g.super_timer == SUPER_DURATION  # 300


def test_super_multiplier_on_score():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.super_timer = 100
    g.combo = 3
    g.current_ball = CallBall(number=1, color=1, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=1, color=1)

    score_before = g.score
    g._handle_click(0, 0)
    score_gained = g.score - score_before
    # Base: 10 + 4*5 = 30, with 3x SUPER = 90
    assert score_gained == 90


# ── CA Spread ──


def test_ca_spread_marks_adjacent_same_number():
    g = _make_blank_game()
    g.super_timer = 100
    # 3 cells in a line with same number, all unmarked
    g.grid[0][0] = BingoCell(number=12, color=0, marked=False)
    g.grid[0][1] = BingoCell(number=12, color=1, marked=False)
    g.grid[0][2] = BingoCell(number=12, color=2, marked=False)
    g.grid[1][0] = BingoCell(number=99, color=0, marked=False)

    g._ca_spread(0, 0)
    assert g.grid[0][0].marked is True
    assert g.grid[0][1].marked is True
    assert g.grid[0][2].marked is True
    assert g.grid[1][0].marked is False  # different number


def test_ca_spread_no_effect_on_already_marked():
    g = _make_blank_game()
    g.super_timer = 100
    g.grid[0][0] = BingoCell(number=5, color=0, marked=True)
    g._ca_spread(0, 0)
    assert g.grid[0][0].marked is True


# ── Ball Expired ──


def test_ball_expired_adds_heat():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_ball = CallBall(number=1, color=0, x=CALL_X, y=CALL_Y, timer=0.0)
    g.current_ball.timer = -1
    g.heat = 30.0
    g.combo = 3

    g._on_ball_expired()
    assert g.heat == 50.0  # 30 + 20
    assert g.combo == 0
    assert g.current_ball is None


def test_ball_expired_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_ball = CallBall(number=1, color=0, x=CALL_X, y=CALL_Y, timer=0.0)
    g.heat = 85.0

    g._on_ball_expired()
    assert g.phase == Phase.GAME_OVER


# ── HEAT System ──


def test_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.001


def test_heat_decay_floor():
    g = _make_game()
    g.heat = HEAT_DECAY / 2
    g._update_heat()
    assert g.heat == 0.0


def test_heat_game_over_triggers_above_max():
    """HEAT decays first, so set above max to trigger after decay."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX + HEAT_DECAY  # 100.03 → decays to 100.0 → triggers
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_game_over_exact_100_no_trigger():
    """HEAT=100.0 decays to 99.97 before check — does NOT trigger (by design)."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX  # exactly 100.0
    g._update_heat()
    # Decays to 99.97 before check → no game over
    assert g.phase == Phase.PLAYING
    assert abs(g.heat - (HEAT_MAX - HEAT_DECAY)) < 0.001


def test_heat_mismatch_game_over():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.heat = 90.0
    g.current_ball = CallBall(number=1, color=0, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=2, color=1)

    g._handle_click(0, 0)
    assert g.heat >= HEAT_MAX
    assert g.phase == Phase.GAME_OVER


# ── Timer ──


def test_game_timer_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 1
    g.update()
    assert g.game_timer == 0
    assert g.phase == Phase.GAME_OVER


def test_game_timer_not_yet_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 100
    g.current_ball = None
    g._spawn_cooldown = 999  # prevent auto-spawn
    g.update()
    assert g.phase != Phase.GAME_OVER


# ── BINGO Line Detection ──


def test_check_bingo_row():
    g = _make_game()
    for c in range(GRID_SIZE):
        g.grid[2][c].marked = True
    lines = g._check_bingo()
    assert len(lines) == 1
    assert set(lines[0]) == {(2, c) for c in range(GRID_SIZE)}


def test_check_bingo_column():
    g = _make_game()
    for r in range(GRID_SIZE):
        g.grid[r][3].marked = True
    lines = g._check_bingo()
    assert len(lines) == 1
    assert set(lines[0]) == {(r, 3) for r in range(GRID_SIZE)}


def test_check_bingo_diagonal():
    g = _make_game()
    for i in range(GRID_SIZE):
        g.grid[i][i].marked = True
    lines = g._check_bingo()
    assert len(lines) == 1
    assert set(lines[0]) == {(i, i) for i in range(GRID_SIZE)}


def test_check_bingo_anti_diagonal():
    g = _make_game()
    for i in range(GRID_SIZE):
        g.grid[i][GRID_SIZE - 1 - i].marked = True
    lines = g._check_bingo()
    assert len(lines) == 1
    assert set(lines[0]) == {(i, GRID_SIZE - 1 - i) for i in range(GRID_SIZE)}


def test_check_bingo_multiple():
    g = _make_game()
    for c in range(GRID_SIZE):
        g.grid[0][c].marked = True
    for r in range(GRID_SIZE):
        g.grid[r][0].marked = True
    lines = g._check_bingo()
    assert len(lines) == 2


def test_check_bingo_none():
    g = _make_game()
    lines = g._check_bingo()
    assert lines == []


# ── BINGO Line Clear ──


def test_clear_bingo_line():
    g = _make_game()
    g.rng = random.Random(42)
    cells: list[tuple[int, int]] = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]
    for r, c in cells:
        g.grid[r][c].marked = True
        g.grid[r][c].number = c + 1

    g._clear_bingo_line(cells)
    for r, c in cells:
        assert g.grid[r][c].marked is False
    refilled = [g.grid[r][c].number for r, c in cells]
    assert len(refilled) == len(set(refilled))


def test_clear_bingo_line_increments_counter():
    g = _make_game()
    g.rng = random.Random(42)
    g.bingo_lines_cleared = 2
    g.score = 0
    cells: list[tuple[int, int]] = [(0, c) for c in range(GRID_SIZE)]
    for r, c in cells:
        g.grid[r][c].marked = True
    g._check_and_clear_bingo()
    assert g.bingo_lines_cleared == 3


# ── SUPER Auto-Mark ──


def test_auto_mark_finds_matching_cell():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.current_ball = CallBall(number=15, color=0, x=CALL_X, y=CALL_Y, timer=100.0)
    # blank game has grid[row][col] with number=row*5+col+1, all color=0
    # grid[3][3] has number=16. Change it to 15.
    g.grid[3][3] = BingoCell(number=15, color=2, marked=False)
    # Ensure no other cell has number=15
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if r == 3 and c == 3:
                continue
            if g.grid[r][c].number == 15:
                g.grid[r][c] = BingoCell(number=99, color=0, marked=False)

    g._auto_mark_current_ball()
    assert g.grid[3][3].marked is True
    assert g.current_ball is None


def test_auto_mark_skips_marked_cell():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.current_ball = CallBall(number=5, color=0, x=CALL_X, y=CALL_Y, timer=100.0)
    # grid[1][1] has number=7 from blank_game. Set up two cells with number=5
    g.grid[0][4] = BingoCell(number=5, color=0, marked=True)   # already marked
    g.grid[2][0] = BingoCell(number=5, color=1, marked=False)  # should be chosen
    # Ensure no other cell has number=5
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if (r == 0 and c == 4) or (r == 2 and c == 0):
                continue
            if g.grid[r][c].number == 5:
                g.grid[r][c] = BingoCell(number=99, color=0, marked=False)

    g._auto_mark_current_ball()
    assert g.grid[2][0].marked is True   # second one gets marked
    assert g.grid[0][4].marked is True   # stays marked (unchanged)


# ── Particle System ──


def test_spawn_particles():
    g = _make_game()
    g.rng = random.Random(42)
    assert len(g.particles) == 0
    g._spawn_particles(100.0, 100.0, 8, 5, 10)
    assert len(g.particles) == 5
    for p in g.particles:
        assert isinstance(p, Particle)
        assert p.color == 8


def test_update_particles_removes_dead():
    g = _make_game()
    g.particles = [
        Particle(x=0, y=0, vx=0, vy=0, color=0, life=1),
        Particle(x=0, y=0, vx=0, vy=0, color=0, life=5),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


def test_update_particles_moves():
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=1.0, vy=-1.0, color=0, life=5)]
    g._update_particles()
    p = g.particles[0]
    assert p.x == 1.0
    assert p.y == -1.0


# ── Reset ──


def test_reset_clears_all_state():
    g = _make_game(42)
    g.combo = 10
    g.max_combo = 15
    g.score = 999
    g.heat = 80.0
    g.super_timer = 100
    g.bingo_lines_cleared = 5
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, color=0, life=5)]
    g.current_ball = CallBall(number=1, color=0, x=0, y=0, timer=10)
    g.last_marked_color = 2

    g.reset()
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.bingo_lines_cleared == 0
    assert g.particles == []
    assert g.current_ball is None
    assert g.last_marked_color is None
    assert g.phase == Phase.PLAYING
    assert g.game_timer == GAME_DURATION


# ── Score Calculation ──


def test_score_correct_match_no_super():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.combo = 2
    g.super_timer = 0
    g.current_ball = CallBall(number=10, color=1, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[2][1] = BingoCell(number=10, color=1)

    g._handle_click(1, 2)  # col=1, row=2 → grid[2][1]
    # base: 10 + 3*5 = 25, multiplier=1
    assert g.score == 25


def test_score_mismatch():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.super_timer = 0
    g.current_ball = CallBall(number=10, color=0, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[1][1] = BingoCell(number=11, color=0)

    g._handle_click(1, 1)  # col=1, row=1 → grid[1][1]
    # mismatch gives 5 * 1 = 5
    assert g.score == 5


# ── Combo Chain ──


def test_combo_chain_builds():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    colors = [0, 1, 2, 3]
    for i in range(4):
        num = i + 1
        col = colors[i]
        g.current_ball = CallBall(number=num, color=col, x=CALL_X, y=CALL_Y, timer=100.0)
        g.grid[i][0] = BingoCell(number=num, color=col)
        result = g._handle_click(0, i)  # col=0, row=i → grid[i][0]
        assert result == "match"
    assert g.combo == 4


# ── mark_cell marks cell ──


def test_mark_cell_sets_marked():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.current_ball = CallBall(number=1, color=2, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=1, color=2)

    g._handle_click(0, 0)
    assert g.grid[0][0].marked is True


# ── last_marked_color tracking ──


def test_last_marked_color_match():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.current_ball = CallBall(number=1, color=2, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=1, color=2)

    g._handle_click(0, 0)
    assert g.last_marked_color == 2


def test_last_marked_color_mismatch():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.last_marked_color = 1
    g.current_ball = CallBall(number=1, color=0, x=CALL_X, y=CALL_Y, timer=100.0)
    g.grid[0][0] = BingoCell(number=2, color=1)

    g._handle_click(0, 0)
    assert g.last_marked_color is None


# ── SUPER Deactivation ──


def test_super_timer_decrements():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_timer = 10
    g.update()
    assert g.super_timer == 9


def test_super_timer_not_below_zero():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_timer = 0
    g.update()
    assert g.super_timer == 0


# ── Phase Transitions ──


def test_phase_starts_title():
    g = Game()
    assert g.phase == Phase.TITLE


def test_reset_sets_playing():
    g = _make_game()
    assert g.phase == Phase.PLAYING


# ── Data class fields ──


def test_bingo_cell_defaults():
    cell = BingoCell(number=5, color=2)
    assert cell.number == 5
    assert cell.color == 2
    assert cell.marked is False


def test_call_ball_fields():
    ball = CallBall(number=10, color=1, x=100.0, y=80.0, timer=180.0)
    assert ball.alive is True


# ── Run all tests ──
if __name__ == "__main__":
    import inspect

    tests = [
        obj
        for name, obj in inspect.getmembers(sys.modules[__name__])
        if callable(obj) and name.startswith("test_")
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
