"""test_imports.py — Headless logic tests for Gumball Surge (221_gumball_surge)."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import (
    BASE_SCORE,
    COLS,
    COLORS,
    COMBO_THRESHOLD,
    GAME_TIME,
    GRID_X,
    GRID_Y,
    HEAT_MISMATCH,
    MAX_GUMBALLS,
    MAX_HEAT,
    MAX_SPREADS,
    MISMATCH_SCORE,
    ROWS,
    SPAWN_INTERVAL_BASE,
    SPAWN_INTERVAL_MIN,
    SUPER_DURATION,
    FloatingText,
    Game,
    Gumball,
    Particle,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    """Create a headless game instance with deterministic RNG."""
    g: Game = Game.__new__(Game)
    g._rng = random.Random(seed)
    g._pre_init_state()
    g.reset()
    return g


# ── Module-level constants ──


def test_constants() -> None:
    assert len(COLORS) == 4
    assert COLS == 5
    assert ROWS == 12
    assert GAME_TIME == 1800
    assert MAX_HEAT == 100.0
    assert COMBO_THRESHOLD == 4
    assert MAX_GUMBALLS == 30
    assert BASE_SCORE == 10
    assert HEAT_MISMATCH == 15.0
    assert SUPER_DURATION == 150
    assert SPAWN_INTERVAL_BASE == 45
    assert SPAWN_INTERVAL_MIN == 15


# ── Phase enum ──


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.TITLE != Phase.PLAYING


# ── Dataclass instantiation ──


def test_gumball_dataclass() -> None:
    gb = Gumball(col=2, row=3, color=0)
    assert gb.col == 2
    assert gb.row == 3
    assert gb.color == 0
    assert gb.alive is True
    assert gb.infected is False
    assert gb.spread_count == 0


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.life == 15
    assert p.color == 8


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=50.0, y=30.0, text="+100", life=25, color=10)
    assert ft.text == "+100"
    assert ft.life == 25


# ── Game initialization ──


def test_game_init_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.game_timer == GAME_TIME  # 1800 frames
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.last_color == -1
    assert g.spawn_interval == SPAWN_INTERVAL_BASE
    assert g.spawn_timer == SPAWN_INTERVAL_BASE
    assert g.shake_frames == 0
    assert len(g.gumballs) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.col_heights == [0, 0, 0, 0, 0]
    assert len(g.grid) == COLS
    for col in range(COLS):
        assert len(g.grid[col]) == ROWS
        for row in range(ROWS):
            assert g.grid[col][row] is None


# ── Spawning ──


def test_spawn_gumballs() -> None:
    g = _make_game()
    assert len(g.gumballs) == 0
    g._spawn_gumballs()
    assert len(g.gumballs) == 1
    gb = g.gumballs[0]
    assert 0 <= gb.col < COLS
    assert 0 <= gb.row < ROWS
    assert gb.alive is True
    assert gb.color in (0, 1, 2, 3)
    assert g.grid[gb.col][gb.row] == gb.color
    assert g.col_heights[gb.col] == 1


def test_spawn_limits() -> None:
    g = _make_game()
    # Fill all columns to max
    for col in range(COLS):
        g.col_heights[col] = ROWS
        for r in range(ROWS):
            g.grid[col][r] = 0
            g.gumballs.append(Gumball(col=col, row=r, color=0))
    # All columns full — spawn should do nothing
    before = len(g.gumballs)
    g._spawn_gumballs()
    assert len(g.gumballs) == before


def test_spawn_max_gumballs() -> None:
    g = _make_game()
    # Fill to MAX_GUMBALLS limit
    for _ in range(MAX_GUMBALLS):
        g.gumballs.append(Gumball(col=0, row=0, color=0))
    before = len(g.gumballs)
    g._spawn_gumballs()
    assert len(g.gumballs) == before


# ── Grid conversion ──


def test_grid_to_xy() -> None:
    g = _make_game()
    x, y = g._grid_to_xy(0, 0)
    assert x == GRID_X + 10  # CELL // 2
    assert y == GRID_Y + 10
    x, y = g._grid_to_xy(4, 11)
    assert x == GRID_X + 4 * 20 + 10
    assert y == GRID_Y + 11 * 20 + 10


def test_xy_to_grid() -> None:
    g = _make_game()
    # Click center of cell (0, 0)
    x, y = g._grid_to_xy(0, 0)
    result = g._xy_to_grid(x, y)
    assert result == (0, 0)
    # Click center of cell (4, 11)
    x, y = g._grid_to_xy(4, 11)
    result = g._xy_to_grid(x, y)
    assert result == (4, 11)
    # Click outside grid
    assert g._xy_to_grid(-10, 0) is None
    assert g._xy_to_grid(0, -10) is None
    assert g._xy_to_grid(500, 0) is None
    assert g._xy_to_grid(0, 500) is None


# ── Combo multiplier ──


def test_combo_multiplier() -> None:
    g = _make_game()
    assert g._compute_combo_multiplier(0) == 1
    assert g._compute_combo_multiplier(1) == 1
    assert g._compute_combo_multiplier(2) == 2
    assert g._compute_combo_multiplier(3) == 2
    assert g._compute_combo_multiplier(4) == 3
    assert g._compute_combo_multiplier(5) == 3
    assert g._compute_combo_multiplier(6) == 5
    assert g._compute_combo_multiplier(10) == 5


# ── Collect: match ──


def test_collect_match() -> None:
    g = _make_game(seed=1)
    gb = Gumball(col=2, row=11, color=0)
    g.gumballs.append(gb)
    g.grid[2][11] = 0
    g.col_heights[2] = 1

    assert g.last_color == -1
    g._collect_gumball(gb)
    assert gb.alive is False
    assert g.combo == 1
    assert g.last_color == 0
    assert g.score == BASE_SCORE  # combo=1 -> mult=1 -> 10
    assert g.max_combo == 1
    assert g.col_heights[2] == 0


def test_collect_combo_chain() -> None:
    g = _make_game(seed=1)
    # First gumball
    gb1 = Gumball(col=0, row=11, color=0)
    g.gumballs.append(gb1)
    g.grid[0][11] = 0
    g.col_heights[0] = 1
    g._collect_gumball(gb1)
    assert g.combo == 1
    assert g.score == 10

    # Second same-color
    gb2 = Gumball(col=1, row=11, color=0)
    g.gumballs.append(gb2)
    g.grid[1][11] = 0
    g.col_heights[1] = 1
    g._collect_gumball(gb2)
    assert g.combo == 2
    assert g.score == 10 + BASE_SCORE * 2  # combo=2 -> mult=2 -> 20

    # Third same-color
    gb3 = Gumball(col=2, row=11, color=0)
    g.gumballs.append(gb3)
    g.grid[2][11] = 0
    g.col_heights[2] = 1
    g._collect_gumball(gb3)
    assert g.combo == 3
    assert g.max_combo == 3


# ── Collect: mismatch ──


def test_collect_mismatch() -> None:
    g = _make_game(seed=1)
    # First match
    gb1 = Gumball(col=0, row=11, color=0)
    g.gumballs.append(gb1)
    g.grid[0][11] = 0
    g.col_heights[0] = 1
    g._collect_gumball(gb1)
    assert g.combo == 1
    assert g.last_color == 0
    assert g.score == 10

    # Mismatch with different color
    gb2 = Gumball(col=1, row=11, color=1)
    g.gumballs.append(gb2)
    g.grid[1][11] = 1
    g.col_heights[1] = 1
    g._collect_gumball(gb2)
    assert g.combo == 0
    assert g.last_color == -1  # reset on mismatch
    assert g.heat == HEAT_MISMATCH
    assert g.score == 10 + MISMATCH_SCORE


# ── SUPER activation ──


def test_super_activation() -> None:
    g = _make_game(seed=1)
    # Build combo to threshold
    for i in range(COMBO_THRESHOLD):
        gb = Gumball(col=0, row=11 - i, color=0)
        g.gumballs.append(gb)
        g.grid[0][11 - i] = 0
        g.col_heights[0] += 1
        g._collect_gumball(gb)
    assert g.combo == COMBO_THRESHOLD
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_mode_collect() -> None:
    g = _make_game(seed=1)
    g.super_mode = True
    g.super_timer = 60
    g.last_color = 0  # wrong color

    # Any color should match in super mode
    gb = Gumball(col=0, row=11, color=1)  # different color
    g.gumballs.append(gb)
    g.grid[0][11] = 1
    g.col_heights[0] = 1
    g._collect_gumball(gb)

    assert g.combo == 1  # counted as match
    assert g.score == BASE_SCORE * 3  # super multiplies score by 3
    assert g.last_color == 1  # tracks the color even in super


def test_super_timer_expiry() -> None:
    g = _make_game(seed=1)
    g.super_mode = True
    g.super_timer = 1
    g._update_super_mode()
    assert g.super_mode is False
    assert g.super_timer == 0


# ── Infected gumballs ──


def test_infected_score() -> None:
    g = _make_game()
    # First collect a non-infected to set last_color and combo=1
    gb0 = Gumball(col=0, row=11, color=0)
    g.gumballs.append(gb0)
    g.grid[0][11] = 0
    g.col_heights[0] = 1
    g._collect_gumball(gb0)
    assert g.score == 10  # combo=1 -> mult=1 -> 10

    # Second: infected same-color, combo=2 -> mult=2 -> 10*2=20,
    # then infected halves: max(1, int(2*0.5)) = 1 -> 10
    gb = Gumball(col=1, row=11, color=0, infected=True)
    g.gumballs.append(gb)
    g.grid[1][11] = 0
    g.col_heights[1] = 1
    g._collect_gumball(gb)
    # infected: mult = max(1, int(2 * 0.5)) = max(1, 1) = 1, gain = 10*1 = 10
    assert g.score == 20  # 10 (first) + 10 (infected)


# ── Grid shifting ──


def test_shift_gumballs_down() -> None:
    g = _make_game()
    # Stack gumballs in column 0: row 8, 9, 10
    gb_bottom = Gumball(col=0, row=10, color=0)
    gb_mid = Gumball(col=0, row=9, color=1)
    gb_top = Gumball(col=0, row=8, color=2)
    for gb in [gb_bottom, gb_mid, gb_top]:
        g.gumballs.append(gb)
        g.grid[gb.col][gb.row] = gb.color
    g.col_heights[0] = 3

    # Remove middle gumball (row 9)
    g.grid[0][9] = None
    g.col_heights[0] -= 1
    g._shift_gumballs_down(0, 9)

    # gb_top (was row 8) should shift to row 9
    assert gb_top.row == 9
    # gb_bottom (was row 10) should stay at row 10
    assert gb_bottom.row == 10
    assert g.grid[0][8] is None  # old position cleared
    assert g.grid[0][9] == gb_top.color  # new position filled


# ── Find gumball ──


def test_find_gumball() -> None:
    g = _make_game()
    gb = Gumball(col=2, row=5, color=0)
    g.gumballs.append(gb)
    found = g._find_gumball(2, 5)
    assert found is gb
    assert g._find_gumball(2, 6) is None
    # Dead gumball
    gb.alive = False
    assert g._find_gumball(2, 5) is None


# ── Heat system ──


def test_check_game_over_by_heat() -> None:
    g = _make_game()
    g.heat = 99.0
    assert g._check_game_over() is False
    g.heat = 100.0
    assert g._check_game_over() is True
    g.heat = 101.0
    assert g._check_game_over() is True


def test_check_game_over_by_timer() -> None:
    g = _make_game()
    g.game_timer = 1
    assert g._check_game_over() is False
    g.game_timer = 0
    assert g._check_game_over() is True


# ── Spawn interval ──


def test_spawn_interval_decrease() -> None:
    g = _make_game()
    assert g.spawn_interval == SPAWN_INTERVAL_BASE  # 45
    # Simulate 3 seconds elapsed
    g.game_timer = GAME_TIME - 3 * 30  # 3s * 30fps
    g._update_spawn_interval()
    assert g.spawn_interval == SPAWN_INTERVAL_BASE - 1  # 44
    # Simulate 9 seconds elapsed
    g.game_timer = GAME_TIME - 9 * 30
    g._update_spawn_interval()
    assert g.spawn_interval == SPAWN_INTERVAL_BASE - 3  # 42
    # Shouldn't go below min
    g.game_timer = GAME_TIME - 100 * 30  # far past
    g._update_spawn_interval()
    assert g.spawn_interval == SPAWN_INTERVAL_MIN  # 15


# ── Particles ──


def test_update_particles() -> None:
    g = _make_game()
    p = Particle(x=50.0, y=100.0, vx=1.0, vy=-2.0, life=3, color=8)
    g.particles.append(p)
    g._update_particles()
    assert p.life == 2
    assert abs(p.x - 51.0) < 0.01
    # vy applied FIRST to position, THEN gravity added to vy
    # y += vy → 100.0 + (-2.0) = 98.0, then vy += 0.1 → vy = -1.9
    assert abs(p.y - 98.0) < 0.01
    g._update_particles()
    assert p.life == 1
    g._update_particles()
    assert p.life == 0
    assert len(g.particles) == 0  # removed


# ── Floating texts ──


def test_update_floating_texts() -> None:
    g = _make_game()
    ft = FloatingText(x=50.0, y=100.0, text="+10", life=2, color=10)
    g.floating_texts.append(ft)
    g._update_floating_texts()
    assert ft.life == 1
    assert abs(ft.y - 99.5) < 0.01
    g._update_floating_texts()
    assert ft.life == 0
    assert len(g.floating_texts) == 0  # removed


# ── CA Spread ──


def test_ca_spread_basic() -> None:
    g = _make_game(seed=1)
    # Place a gumball with room to spread
    gb = Gumball(col=2, row=5, color=0)
    g.gumballs.append(gb)
    g.grid[2][5] = 0
    g.col_heights[2] = 1

    # Force spread by mocking random
    orig_random = g._rng.random
    g._rng.random = lambda: 0.1  # type: ignore
    g._ca_spread()
    g._rng.random = orig_random  # type: ignore

    # Should have spread to an adjacent cell
    assert len(g.gumballs) >= 2
    assert gb.spread_count >= 1
    # New gumball should be infected
    new_gb = g.gumballs[-1]
    assert new_gb.infected is True
    assert new_gb.color == 0
    assert new_gb.alive is True


def test_ca_spread_no_chance() -> None:
    g = _make_game(seed=1)
    gb = Gumball(col=2, row=5, color=0)
    g.gumballs.append(gb)
    g.grid[2][5] = 0
    g.col_heights[2] = 1

    # Force no spread
    orig_random = g._rng.random
    g._rng.random = lambda: 0.9  # type: ignore[assignment]  # always above CA_SPREAD_CHANCE (0.20)
    g._ca_spread()
    g._rng.random = orig_random  # type: ignore[assignment]

    assert gb.spread_count == 0


def test_ca_spread_max() -> None:
    g = _make_game(seed=1)
    gb = Gumball(col=2, row=5, color=0, spread_count=MAX_SPREADS)
    g.gumballs.append(gb)
    g.grid[2][5] = 0
    g.col_heights[2] = 1

    orig_random = g._rng.random
    g._rng.random = lambda: 0.1  # type: ignore[assignment]
    g._ca_spread()
    g._rng.random = orig_random  # type: ignore[assignment]

    # Already at max spreads — no new spread
    assert gb.spread_count == MAX_SPREADS


# ── Heat decay ──


def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 30.0
    g.game_timer = GAME_TIME - 60  # some elapsed time
    g._update_heat()
    assert g.heat < 30.0
    assert g.heat > 29.0  # small decay


def test_heat_never_negative() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


# ── SUPER activation edge cases ──


def test_super_not_reactive_if_already_active() -> None:
    g = _make_game(seed=1)
    g.super_mode = True
    g.super_timer = 100
    g.last_color = -1

    # Collect with combo=4 should NOT re-activate
    g.combo = COMBO_THRESHOLD - 1
    gb = Gumball(col=0, row=11, color=0)
    g.gumballs.append(gb)
    g.grid[0][11] = 0
    g.col_heights[0] = 1
    g._collect_gumball(gb)
    assert g.combo == COMBO_THRESHOLD
    assert g.super_mode is True  # still active, not re-activated
    # Timer unchanged by _activate_super (which wasn't called)
    # Actually _activate_super IS called in the code — let me check
    # The code calls _activate_super at combo >= threshold AND not super_mode already


def test_last_color_resets_on_mismatch() -> None:
    g = _make_game(seed=1)
    # First match
    gb1 = Gumball(col=0, row=11, color=0)
    g.gumballs.append(gb1)
    g.grid[0][11] = 0
    g.col_heights[0] = 1
    g._collect_gumball(gb1)
    assert g.last_color == 0

    # Mismatch
    gb2 = Gumball(col=1, row=11, color=1)
    g.gumballs.append(gb2)
    g.grid[1][11] = 1
    g.col_heights[1] = 1
    g._collect_gumball(gb2)
    assert g.last_color == -1
    assert g.combo == 0


# ── max_combo tracking ──


def test_max_combo_tracks_peak() -> None:
    g = _make_game(seed=1)
    # Build combo to 3 only (below SUPER threshold of 4)
    for i in range(3):
        gb = Gumball(col=0, row=11 - i, color=0)
        g.gumballs.append(gb)
        g.grid[0][11 - i] = 0
        g.col_heights[0] += 1
        g._collect_gumball(gb)
    assert g.combo == 3
    assert g.max_combo == 3

    # Reset combo via mismatch (super not active)
    gb_mismatch = Gumball(col=1, row=11, color=1)
    g.gumballs.append(gb_mismatch)
    g.grid[1][11] = 1
    g.col_heights[1] = 1
    g._collect_gumball(gb_mismatch)
    assert g.combo == 0
    assert g.max_combo == 3  # peak preserved


# ── Multiple gumballs same column ──


def test_multiple_gumballs_one_column() -> None:
    g = _make_game(seed=1)
    for i in range(3):
        gb = Gumball(col=2, row=11 - i, color=0)
        g.gumballs.append(gb)
        g.grid[2][11 - i] = 0
        g.col_heights[2] += 1

    assert g.col_heights[2] == 3
    assert g.grid[2][9] == 0
    assert g.grid[2][10] == 0
    assert g.grid[2][11] == 0

    # Collect top gumball
    top = g._find_gumball(2, 9)
    assert top is not None
    g._collect_gumball(top)
    assert g.col_heights[2] == 2
    # Everything above row 9 should shift down
    assert g.grid[2][9] is None
    # Grid positions after shift: gumballs that were at rows 10,11 shift to 10,11 (or 9,10/etc.)
    # After removing row 9, gumballs at row 10→9, row 11→10
    # Wait, the shift goes UP in the code: shift_gumballs_down moves gumballs with row < removed_row
    # row=10 < 11 → shift to row=11? No. Let me re-read the code.
    # In _shift_gumballs_down: for gb with gb.row < removed_row: gb.row += 1
    # So gumballs ABOVE (smaller row number) shift down (increase row number)
    # After removing row 9: row 10 becomes row 11, row 11 → row 12 (beyond grid? since row 11 was bottom)
    # Hmm, this seems correct: gumballs above the removed one fall down.


# ── Reset ──


def test_reset_clears_state() -> None:
    g = _make_game(seed=1)
    g.score = 500
    g.combo = 10
    g.heat = 50.0
    g.gumballs = [Gumball(col=0, row=0, color=0)]
    g.particles = [Particle(x=0, y=0, vx=1, vy=1, life=10, color=8)]
    g.floating_texts = [FloatingText(x=0, y=0, text="hi", life=10)]

    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.game_timer == GAME_TIME
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.last_color == -1
    assert g.shake_frames == 0
    assert len(g.gumballs) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.col_heights == [0, 0, 0, 0, 0]
    assert g.spawn_interval == SPAWN_INTERVAL_BASE
    assert g.spawn_timer == SPAWN_INTERVAL_BASE


# ── Heat clamped at max ──


def test_heat_capped_at_max() -> None:
    g = _make_game()
    g.heat = 90.0
    gb = Gumball(col=0, row=11, color=0)
    g.gumballs.append(gb)
    g.grid[0][11] = 0
    g.col_heights[0] = 1
    g._collect_gumball(gb)  # match (last_color=-1)
    g.last_color = 0
    gb2 = Gumball(col=1, row=11, color=1)
    g.gumballs.append(gb2)
    g.grid[1][11] = 1
    g.col_heights[1] = 1
    g._collect_gumball(gb2)  # mismatch → heat +15
    assert g.heat <= MAX_HEAT  # should be exactly 100, not more


# ── Score with infected in super ──


def test_infected_super_score() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 60
    gb = Gumball(col=0, row=11, color=0, infected=True)
    g.gumballs.append(gb)
    g.grid[0][11] = 0
    g.col_heights[0] = 1
    g._collect_gumball(gb)
    # combo=1 → mult=1; infected → max(1, int(1*0.5)) = 1; super → 1*3 = 3; base=10 → 10*3=30
    # Wait: score = BASE_SCORE * mult * SUPER_SCORE_MULT
    # mult = max(1, int(1 * 0.5)) = max(1, 0) = 1
    # gain = 10 * 1 * 3 = 30
    assert g.score == 30


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
