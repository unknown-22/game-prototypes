"""test_imports.py — Headless logic tests for POP CHAIN."""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (  # noqa: E402
    BUBBLE_MAX,
    CELL,
    COLORS,
    COLOR_CYCLE_TIME,
    COLS,
    COMBO_SUPER,
    GAME_TIME,
    GRID_OX,
    GRID_OY,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_WRONG,
    INFLATE_INTERVAL,
    INITIAL_BUBBLES,
    ROWS,
    SCREEN_H,
    SCREEN_W,
    SUPER_DURATION,
    Bubble,
    FloatText,
    Game,
    Particle,
    Phase,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.particles = []
    g.floating_texts = []
    g.reset()
    return g


# ── Constants ──


def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert COLS == 10
    assert ROWS == 8
    assert CELL == 24
    assert GRID_OX == 40
    assert GRID_OY == 24
    assert COLORS == (8, 3, 5, 10)
    assert INFLATE_INTERVAL == 120
    assert COLOR_CYCLE_TIME == 90
    assert SUPER_DURATION == 300
    assert GAME_TIME == 3600
    assert BUBBLE_MAX == 32
    assert HEAT_MAX == 100
    assert HEAT_WRONG == 15
    assert HEAT_DECAY == 0.05
    assert COMBO_SUPER == 4
    assert INITIAL_BUBBLES == 8


# ── Phase ──


def test_phase_values() -> None:
    assert Phase.TITLE is not Phase.PLAYING
    assert Phase.PLAYING is not Phase.GAME_OVER


# ── Dataclasses ──


def test_bubble_dataclass() -> None:
    b = Bubble(3, 5, 8, life=0)
    assert b.col == 3
    assert b.row == 5
    assert b.color == 8
    assert b.life == 0


def test_particle_dataclass() -> None:
    p = Particle(10.0, 20.0, 1.5, -0.5, 15, 8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -0.5
    assert p.life == 15
    assert p.color == 8


def test_floating_text_dataclass() -> None:
    ft = FloatText(100.0, 50.0, "+15", 20, 9)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+15"
    assert ft.life == 20
    assert ft.color == 9


# ── reset ──


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == GAME_TIME
    assert g.super_timer == 0
    assert g.color_index == 0
    assert g.color_timer == COLOR_CYCLE_TIME
    assert g.frame == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert all(
        g.grid[r][c] is None for r in range(ROWS) for c in range(COLS)
    )


def test_reset_clears_mutable_state() -> None:
    g = _make_game()
    g.particles.append(Particle(0, 0, 0, 0, 10, 8))
    g.floating_texts.append(FloatText(0, 0, "test", 10, 7))
    g.score = 500
    g.combo = 10
    g.heat = 50.0
    g.reset()
    assert g.particles == []
    assert g.floating_texts == []
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0


# ── _start_game ──


def test_start_game_sets_phase() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.PLAYING
    assert g.timer == GAME_TIME
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0


def test_start_game_spawns_bubbles() -> None:
    g = _make_game()
    g._start_game()
    assert g._count_alive_bubbles() == INITIAL_BUBBLES


# ── _screen_to_grid ──


def test_screen_to_grid_valid() -> None:
    g = _make_game()
    result = g._screen_to_grid(GRID_OX + CELL, GRID_OY + CELL)
    assert result == (1, 1)


def test_screen_to_grid_origin() -> None:
    g = _make_game()
    result = g._screen_to_grid(GRID_OX, GRID_OY)
    assert result == (0, 0)


def test_screen_to_grid_bottom_right() -> None:
    g = _make_game()
    result = g._screen_to_grid(
        GRID_OX + COLS * CELL - 1, GRID_OY + ROWS * CELL - 1
    )
    assert result == (9, 7)


def test_screen_to_grid_outside() -> None:
    g = _make_game()
    assert g._screen_to_grid(0, 0) is None
    assert g._screen_to_grid(319, 239) is None


def test_screen_to_grid_left_of_grid() -> None:
    g = _make_game()
    assert g._screen_to_grid(GRID_OX - 1, GRID_OY) is None


# ── _random_bubble_color ──


def test_random_bubble_color_valid() -> None:
    g = _make_game()
    for _ in range(100):
        c = g._random_bubble_color()
        assert c in COLORS


# ── _count_alive_bubbles ──


def test_count_alive_bubbles_empty() -> None:
    g = _make_game()
    assert g._count_alive_bubbles() == 0


def test_count_alive_bubbles_with_bubbles() -> None:
    g = _make_game()
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g.grid[1][2] = Bubble(2, 1, 3, life=0)
    assert g._count_alive_bubbles() == 2


def test_count_alive_bubbles_ignores_popping() -> None:
    g = _make_game()
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g.grid[1][2] = Bubble(2, 1, 3, life=60)
    assert g._count_alive_bubbles() == 1


# ── _spawn_initial_bubbles ──


def test_spawn_initial_bubbles_count() -> None:
    g = _make_game()
    g._spawn_initial_bubbles()
    assert g._count_alive_bubbles() == INITIAL_BUBBLES


def test_spawn_initial_bubbles_valid() -> None:
    g = _make_game()
    g._spawn_initial_bubbles()
    for row in range(ROWS):
        for col in range(COLS):
            b = g.grid[row][col]
            if b is not None:
                assert b.color in COLORS
                assert b.life == 0


# ── _pop_bubble ──


def test_pop_empty_cell_returns_zero() -> None:
    g = _make_game()
    assert g._pop_bubble(0, 0) == 0


def test_pop_popping_bubble_returns_zero() -> None:
    g = _make_game()
    g.grid[0][0] = Bubble(0, 0, 8, life=60)
    assert g._pop_bubble(0, 0) == 0


def test_pop_matching_color_scoring() -> None:
    g = _make_game()
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g._pop_bubble(0, 0)
    assert g.combo == 1
    assert g.score > 0
    assert g.max_combo == 1
    assert g.grid[0][0].life == 60
    assert len(g.particles) > 0
    assert len(g.floating_texts) > 0


def test_pop_score_formula() -> None:
    g = _make_game()
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g.combo = 2
    g.max_combo = 2
    result = g._pop_bubble(0, 0)
    expected = int(10 * (1 + 3 * 0.5))
    assert result == expected
    assert g.score == expected


def test_pop_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 3, life=0)
    g.combo = 3
    assert g._pop_bubble(0, 0) == 0
    assert g.combo == 0
    assert g.heat == HEAT_WRONG
    assert g.grid[0][0].life == 60


def test_pop_wrong_color_preserves_max_combo() -> None:
    g = _make_game()
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 3, life=0)
    g.max_combo = 10
    g._pop_bubble(0, 0)
    assert g.max_combo == 10
    assert g.combo == 0


def test_pop_wrong_color_heat_game_over() -> None:
    g = _make_game()
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 3, life=0)
    g.heat = 90.0
    g._pop_bubble(0, 0)
    assert g.heat == float(HEAT_MAX)
    assert g.phase == Phase.GAME_OVER


def test_pop_triggers_super() -> None:
    g = _make_game()
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g.combo = 3
    g.max_combo = 3
    g._pop_bubble(0, 0)
    assert g.combo >= 4
    assert g.super_timer == SUPER_DURATION


def test_pop_super_mode_any_color() -> None:
    g = _make_game()
    g.super_timer = 100
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 3, life=0)
    g.combo = 5
    result = g._pop_bubble(0, 0)
    assert result > 0
    assert g.combo == 6


def test_pop_super_mode_3x_score() -> None:
    g = _make_game()
    g.super_timer = 100
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g.combo = 5
    g.max_combo = 5
    result = g._pop_bubble(0, 0)
    expected = int(10 * (1 + 6 * 0.5)) * 3
    assert result == expected


def test_pop_super_refreshes_timer() -> None:
    g = _make_game()
    g.super_timer = 50
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g.combo = 5
    g._pop_bubble(0, 0)
    assert g.super_timer == SUPER_DURATION


def test_pop_super_does_not_re_activate() -> None:
    g = _make_game()
    g.super_timer = 50
    g.grid[1][0] = Bubble(0, 1, 8, life=0)
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g.combo = 3
    g.max_combo = 3
    g._pop_bubble(0, 0)
    assert g.super_timer == SUPER_DURATION
    assert g.combo == 4


# ── _activate_super ──


def test_activate_super_sets_timer() -> None:
    g = _make_game()
    g.combo = 3
    g._activate_super()
    assert g.super_timer == SUPER_DURATION


def test_activate_super_pops_all_alive() -> None:
    g = _make_game()
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g.grid[0][1] = Bubble(1, 0, 3, life=0)
    g.grid[1][0] = Bubble(0, 1, 5, life=0)
    g.combo = 3
    g.score = 100
    g._activate_super()
    assert g.grid[0][0].life == 60
    assert g.grid[0][1].life == 60
    assert g.grid[1][0].life == 60
    assert g.score > 100


def test_activate_super_chain_scoring() -> None:
    g = _make_game()
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g.grid[0][1] = Bubble(1, 0, 3, life=0)
    g.combo = 3
    g.score = 0
    g._activate_super()
    assert g.combo == 5
    assert g.score == 65


def test_activate_super_empty_grid() -> None:
    g = _make_game()
    g.combo = 4
    g._activate_super()
    assert g.super_timer == SUPER_DURATION
    assert g.combo == 4


# ── _update_heat ──


def test_update_heat_decays() -> None:
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat < 10.0


def test_update_heat_floors_at_zero() -> None:
    g = _make_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_no_decay_at_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


# ── _update_bubble_animations ──


def test_update_bubble_animations_decrements_life() -> None:
    g = _make_game()
    g.grid[0][0] = Bubble(0, 0, 8, life=60)
    g._update_bubble_animations()
    assert g.grid[0][0] is not None
    assert g.grid[0][0].life == 59


def test_update_bubble_animations_removes_dead() -> None:
    g = _make_game()
    g.grid[0][0] = Bubble(0, 0, 8, life=1)
    g._update_bubble_animations()
    assert g.grid[0][0] is None


def test_update_bubble_animations_skips_alive() -> None:
    g = _make_game()
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g._update_bubble_animations()
    assert g.grid[0][0].life == 0


# ── _update_particles ──


def test_update_particles_moves() -> None:
    g = _make_game()
    g.particles = [Particle(100.0, 100.0, 2.0, -1.0, 10, 8)]
    g._update_particles()
    assert abs(g.particles[0].x - 102.0) < 0.01
    assert abs(g.particles[0].y - 99.0) < 0.01
    assert g.particles[0].life == 9


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.particles = [
        Particle(0, 0, 1, 1, 1, 8),
        Particle(10, 10, 1, 1, 5, 8),
    ]
    g._update_particles()
    assert len(g.particles) == 1


# ── _update_floating_texts ──


def test_update_floating_texts_moves() -> None:
    g = _make_game()
    g.floating_texts = [FloatText(100.0, 50.0, "+15", 10, 7)]
    g._update_floating_texts()
    assert abs(g.floating_texts[0].y - 49.5) < 0.01
    assert g.floating_texts[0].life == 9


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatText(0, 0, "a", 1, 7),
        FloatText(10, 10, "b", 5, 7),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "b"


# ── _update_timer ──


def test_update_timer_decrements() -> None:
    g = _make_game()
    g.timer = 100
    g._update_timer()
    assert g.timer == 99


def test_update_timer_game_over() -> None:
    g = _make_game()
    g.timer = 0
    g._update_timer()
    assert g.phase == Phase.GAME_OVER


# ── _spawn_particles / _spawn_floating_text ──


def test_spawn_particles_count() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 8, 10)
    assert len(g.particles) == 10


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100.0, 50.0, "+15", 9)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+15"
    assert ft.life == 20
    assert ft.color == 9


# ── _inflate_bubbles ──


def test_inflate_noop_when_at_cap() -> None:
    g = _make_game()
    count = 0
    for row in range(ROWS):
        for col in range(COLS):
            if count < BUBBLE_MAX:
                g.grid[row][col] = Bubble(col, row, 8, life=0)
                count += 1
    assert g._count_alive_bubbles() == BUBBLE_MAX
    g._inflate_bubbles()
    assert g._count_alive_bubbles() == BUBBLE_MAX


def test_inflate_may_add_bubbles() -> None:
    g = _make_game()
    g.grid[2][2] = Bubble(2, 2, 8, life=0)
    random.seed(42)
    for _ in range(50):
        g._inflate_bubbles()
    assert g._count_alive_bubbles() > 0
    random.seed()


def test_inflate_new_bubble_same_color() -> None:
    g = _make_game()
    g.grid[3][3] = Bubble(3, 3, 3, life=0)
    random.seed(123)
    for _ in range(100):
        g._inflate_bubbles()
    found_new = False
    for row in range(ROWS):
        for col in range(COLS):
            b = g.grid[row][col]
            if b is not None and (col != 3 or row != 3):
                assert b.color == 3
                found_new = True
    if found_new:
        assert g._count_alive_bubbles() > 1
    random.seed()


# ── Integration tests ──


def test_full_combo_chain_to_super() -> None:
    g = _make_game()
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 8, life=0)
    g.grid[0][1] = Bubble(1, 0, 8, life=0)
    g.grid[0][2] = Bubble(2, 0, 8, life=0)
    g.grid[1][0] = Bubble(0, 1, 8, life=0)
    g.grid[1][1] = Bubble(1, 1, 8, life=0)

    g._pop_bubble(0, 0)
    assert g.combo == 1
    assert g.score == 15

    g._pop_bubble(1, 0)
    assert g.combo == 2
    assert g.score == 35

    g._pop_bubble(2, 0)
    assert g.combo == 3
    assert g.score == 60

    g._pop_bubble(0, 1)
    assert g.combo == 5
    assert g.super_timer == SUPER_DURATION
    assert g.score == 125


def test_heat_accumulates_to_game_over() -> None:
    g = _make_game()
    g.heat = 85.0
    g.color_index = 0
    for i in range(4):
        g.grid[i][0] = Bubble(i, 0, 3, life=0)
    g._pop_bubble(0, 0)
    assert g.phase == Phase.GAME_OVER
    assert g.heat == float(HEAT_MAX)


def test_super_ends_gracefully() -> None:
    g = _make_game()
    g.super_timer = 0
    g.color_index = 0
    g.grid[0][0] = Bubble(0, 0, 3, life=0)
    g.combo = 5
    result = g._pop_bubble(0, 0)
    assert result == 0
    assert g.combo == 0


if __name__ == "__main__":
    import pytest

    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)
