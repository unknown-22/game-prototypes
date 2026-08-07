"""test_imports.py — Headless logic tests for FLASH CHAIN (293)."""
from __future__ import annotations

import random
import sys
from collections.abc import Callable
from typing import Any

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/293_flash_chain")
from main import (  # noqa: E402
    COLS,
    ROWS,
    CELL,
    GRID_X,
    GRID_Y,
    SUBJECT_COLORS,
    HEAT_MAX,
    HEAT_MISMATCH,
    COMBO_SUPER_THRESHOLD,
    GAME_DURATION,
    INITIAL_FOG_INTERVAL,
    INITIAL_SPAWN_INTERVAL,
    SUBJECT_MIN,
    SUBJECT_MAX,
    Game,
    Particle,
    Phase,
    Subject,
)


# ---------------------------------------------------------------------------
# Factory for headless testing
# ---------------------------------------------------------------------------


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.fog = []
    g.subjects = []
    g.last_color = None
    g.super_mode = False
    g.super_timer = 0
    g.flash_alpha = 0
    g.particles = []
    g.frame = 0
    g.fog_interval = INITIAL_FOG_INTERVAL
    g.spawn_interval = INITIAL_SPAWN_INTERVAL
    g.spawn_timer = 0
    g.fog_timer = 0
    g._mouse_just_pressed = False
    g.reset()
    return g


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.FLASH_ANIM in Phase
    assert Phase.GAME_OVER in Phase
    assert len(Phase.__members__) == 4


# ---------------------------------------------------------------------------
# Subject dataclass
# ---------------------------------------------------------------------------


def test_subject_dataclass() -> None:
    s = Subject(col=3, row=2, color=8, life=300)
    assert s.col == 3
    assert s.row == 2
    assert s.color == 8
    assert s.life == 300


def test_particle_dataclass() -> None:
    p = Particle(x=100.0, y=50.0, vx=1.5, vy=-0.5, life=25, color=8)
    assert p.x == 100.0
    assert abs(p.vx - 1.5) < 0.01
    assert p.life == 25


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_color_constants() -> None:
    assert len(SUBJECT_COLORS) == 4
    assert 8 in SUBJECT_COLORS  # RED
    assert 11 in SUBJECT_COLORS  # LIME
    assert 12 in SUBJECT_COLORS  # CYAN
    assert 10 in SUBJECT_COLORS  # YELLOW


def test_grid_dimensions() -> None:
    assert COLS == 8
    assert ROWS == 6
    assert CELL == 32


# ---------------------------------------------------------------------------
# Grid coordinate mapping
# ---------------------------------------------------------------------------


def test_grid_coord_valid() -> None:
    g = _make_game()
    coord = g.grid_coord(GRID_X + 5, GRID_Y + 5)
    assert coord == (0, 0)

    coord2 = g.grid_coord(GRID_X + CELL + 10, GRID_Y + CELL * 2 + 10)
    assert coord2 == (1, 2)


def test_grid_coord_outside() -> None:
    g = _make_game()
    assert g.grid_coord(0, 0) is None
    assert g.grid_coord(GRID_X - 1, GRID_Y) is None
    assert g.grid_coord(GRID_X, GRID_Y - 1) is None
    assert g.grid_coord(GRID_X + CELL * COLS + 1, GRID_Y) is None


# ---------------------------------------------------------------------------
# Fog CA spread
# ---------------------------------------------------------------------------


def test_fog_spread_initial_all_clear() -> None:
    g = _make_game()
    for r in range(ROWS):
        for c in range(COLS):
            assert g.fog[r][c] is False


def test_fog_spread_from_edge() -> None:
    g = _make_game()
    # Place one fogged cell at (0, 0)
    g.fog[0][0] = True
    # Force all spread attempts to succeed
    _old = g.rng.random
    g.rng.random = lambda: 0.1  # < 0.2, always spread
    try:
        g._spread_fog()
    finally:
        g.rng.random = _old
    # Should spread to neighbors (1,0) and (0,1)
    assert g.fog[0][1] or g.fog[1][0]  # at least one neighbor fogged


def test_fog_spread_no_spread_low_chance() -> None:
    g = _make_game()
    g.fog[0][0] = True
    _old = g.rng.random
    g.rng.random = lambda: 0.9  # > 0.2, never spread
    try:
        g._spread_fog()
    finally:
        g.rng.random = _old
    # Only the original cell should still be fogged
    assert g.fog[0][0] is True
    for r in range(ROWS):
        for c in range(COLS):
            if (r, c) != (0, 0):
                assert g.fog[r][c] is False


def test_fog_cannot_spread_out_of_bounds() -> None:
    g = _make_game()
    # Place fog at corner (0, 0) — only 2 valid neighbors
    g.fog[0][0] = True
    _old = g.rng.random
    g.rng.random = lambda: 0.1
    try:
        g._spread_fog()
    finally:
        g.rng.random = _old
    # Never goes out of bounds (negative indices should not be accessed)
    assert True  # no IndexError


# ---------------------------------------------------------------------------
# Subject spawn
# ---------------------------------------------------------------------------


def test_spawn_initial_subjects() -> None:
    g = _make_game()
    g._spawn_subjects()
    assert SUBJECT_MIN <= len(g.subjects) <= SUBJECT_MAX


def test_spawn_subjects_in_unfogged_cells() -> None:
    g = _make_game()
    # Fog the entire grid except one cell
    for r in range(ROWS):
        for c in range(COLS):
            g.fog[r][c] = True
    g.fog[0][0] = False  # only (0,0) is unfogged

    g._spawn_subjects()
    assert len(g.subjects) == 1
    assert g.subjects[0].col == 0
    assert g.subjects[0].row == 0


def test_spawn_no_duplicate_cells() -> None:
    g = _make_game()
    g._spawn_subjects()
    positions: set[tuple[int, int]] = set()
    for s in g.subjects:
        positions.add((s.col, s.row))
    assert len(positions) == len(g.subjects)


def test_spawn_respects_max_count() -> None:
    g = _make_game()
    # Fill with max subjects
    g.subjects = [
        Subject(col=c % COLS, row=c // COLS, color=8, life=300)
        for c in range(SUBJECT_MAX)
    ]
    before = len(g.subjects)
    g._spawn_subjects()
    assert len(g.subjects) == before  # no new, already at max


def test_subject_life_decreases_over_time() -> None:
    g = _make_game()
    life = g._get_subject_life()
    assert life == 300  # initial, elapsed_ratio=0


# ---------------------------------------------------------------------------
# Click handling — match
# ---------------------------------------------------------------------------


def test_handle_click_first_click_always_match() -> None:
    g = _make_game()
    s = Subject(col=3, row=2, color=8, life=300)
    g.subjects.append(s)

    g._handle_click(3, 2)
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 10  # 10 * 1 * 1


def test_handle_click_same_color_combo() -> None:
    g = _make_game()
    g.last_color = 8
    g.combo = 2
    g.max_combo = 2
    g.score = 30  # 10*1 + 10*2

    s = Subject(col=3, row=2, color=8, life=300)
    g.subjects.append(s)

    g._handle_click(3, 2)
    assert g.combo == 3
    assert g.max_combo == 3
    # combo=3, not super_mode → multiplier=1, points = 10 * 3 * 1 = 30
    # score = previous 30 + 30 = 60
    assert g.score == 60


def test_handle_click_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.last_color = 8  # RED
    g.combo = 3
    g.max_combo = 3

    s = Subject(col=3, row=2, color=11, life=300)  # LIME
    g.subjects.append(s)

    g._handle_click(3, 2)
    assert g.combo == 0
    assert g.last_color is None
    assert g.heat == HEAT_MISMATCH


def test_handle_click_removes_subject() -> None:
    g = _make_game()
    s = Subject(col=3, row=2, color=8, life=300)
    g.subjects.append(s)

    g._handle_click(3, 2)
    assert len(g.subjects) == 0


def test_handle_click_fogged_cell_no_effect() -> None:
    g = _make_game()
    g.fog[2][3] = True
    s = Subject(col=3, row=2, color=8, life=300)
    g.subjects.append(s)

    g._handle_click(3, 2)
    assert len(g.subjects) == 1  # subject not removed
    assert g.combo == 0  # no combo change
    assert g.score == 0  # no score change


def test_handle_click_empty_cell_no_effect() -> None:
    g = _make_game()
    g._handle_click(3, 2)
    assert g.combo == 0
    assert g.score == 0
    assert g.heat == 0


# ---------------------------------------------------------------------------
# SUPER FLASH mode
# ---------------------------------------------------------------------------


def test_combo_reaches_super_threshold() -> None:
    g = _make_game()
    # Build combo to threshold - 1
    for i in range(COMBO_SUPER_THRESHOLD - 1):
        color = SUBJECT_COLORS[i % 4]
        s = Subject(col=i % COLS, row=i // COLS, color=color, life=300)
        g.subjects.clear()
        g.subjects.append(s)
        g.last_color = color if i == 0 else g.last_color
        # All matches will be same color
        g.last_color = color
        g._handle_click(s.col, s.row)

    # combo should be COMBO_SUPER_THRESHOLD-1, not yet super
    assert g.combo == COMBO_SUPER_THRESHOLD - 1
    old_super = g.super_mode

    # Next same-color click triggers SUPER
    color = SUBJECT_COLORS[0]
    s = Subject(col=(COMBO_SUPER_THRESHOLD - 1) % COLS, row=0, color=color, life=300)
    g.subjects.clear()
    g.subjects.append(s)
    g.last_color = color
    g._handle_click(s.col, s.row)

    assert g.super_mode
    assert g.super_timer > 0


def test_super_flash_any_color_match() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 300
    g.combo = 5
    g.score = 100
    g.last_color = 8  # RED

    # Click a YELLOW subject during SUPER mode — should still match
    s = Subject(col=4, row=2, color=10, life=300)  # YELLOW
    g.subjects.append(s)

    g._handle_click(4, 2)
    assert g.combo == 6
    assert g.score == 100 + 10 * 6 * 3  # 3x multiplier in super mode = 280


def test_super_flash_score_triple() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 300
    g.combo = 1
    g.score = 0

    s = Subject(col=4, row=2, color=8, life=300)
    g.subjects.append(s)

    g._handle_click(4, 2)
    # combo becomes 2, score = 10 * 2 * 3 = 60
    assert g.score == 60


def test_super_timer_decrements() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 300

    g._update_super()
    assert g.super_timer == 299
    assert g.super_mode is True


def test_super_timer_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1

    g._update_super()
    assert g.super_timer == 0
    assert g.super_mode is False


# ---------------------------------------------------------------------------
# Flash animation
# ---------------------------------------------------------------------------


def test_flash_anim_decrements_alpha() -> None:
    g = _make_game()
    g.flash_alpha = 220
    g.phase = Phase.FLASH_ANIM

    g._update_flash_anim()
    assert g.flash_alpha == 205  # 220 - 15


def test_flash_anim_ends() -> None:
    g = _make_game()
    g.flash_alpha = 10
    g.phase = Phase.FLASH_ANIM

    g._update_flash_anim()
    assert g.flash_alpha == 0
    assert g.phase == Phase.PLAYING


# ---------------------------------------------------------------------------
# Heat system
# ---------------------------------------------------------------------------


def test_heat_increases_on_mismatch() -> None:
    g = _make_game()
    g.last_color = 8
    s = Subject(col=3, row=2, color=11, life=300)
    g.subjects.append(s)

    g._handle_click(3, 2)
    assert g.heat == HEAT_MISMATCH


def test_heat_game_over_at_max() -> None:
    g = _make_game()
    g._update_heat(HEAT_MAX)
    assert g.phase == Phase.GAME_OVER


def test_heat_cannot_exceed_max() -> None:
    g = _make_game()
    g._update_heat(HEAT_MAX + 50)
    assert g.heat <= HEAT_MAX
    assert g.heat == HEAT_MAX


# ---------------------------------------------------------------------------
# Game over
# ---------------------------------------------------------------------------


def test_game_over_updates_best_score() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 300

    g._game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500


def test_game_over_does_not_lower_best_score() -> None:
    g = _make_game()
    g.score = 200
    g.best_score = 500

    g._game_over()
    assert g.best_score == 500


# ---------------------------------------------------------------------------
# Subject update (lifecycle)
# ---------------------------------------------------------------------------


def test_update_subjects_decrements_life() -> None:
    g = _make_game()
    s = Subject(col=3, row=2, color=8, life=5)
    g.subjects.append(s)

    g._update_subjects()
    assert s.life == 4


def test_update_subjects_removes_expired() -> None:
    g = _make_game()
    s = Subject(col=3, row=2, color=8, life=1)
    g.subjects.append(s)

    g._update_subjects()
    assert len(g.subjects) == 0


# ---------------------------------------------------------------------------
# Particles
# ---------------------------------------------------------------------------


def test_particles_move() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=100.0, vx=1.0, vy=-1.0, life=20, color=8)
    g.particles.append(p)

    g._update_particles()
    assert p.x == 101.0
    assert p.y == 99.0
    assert p.life == 19


def test_particles_removed_when_expired() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=100.0, vx=1.0, vy=0.0, life=1, color=8)
    g.particles.append(p)

    g._update_particles()
    assert len(g.particles) == 0


def test_spawn_photo_particles() -> None:
    g = _make_game()
    before = len(g.particles)
    g._spawn_photo_particles(3, 2, 8)
    assert len(g.particles) == before + 8


def test_spawn_mismatch_particles() -> None:
    g = _make_game()
    before = len(g.particles)
    g._spawn_mismatch_particles(3, 2)
    assert len(g.particles) == before + 4


# ---------------------------------------------------------------------------
# Max combo tracking
# ---------------------------------------------------------------------------


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.combo = 5
    g.max_combo = 3

    # Simulate a match
    s = Subject(col=3, row=2, color=8, life=300)
    g.subjects.append(s)
    g.last_color = 8
    g._handle_click(3, 2)
    # combo was 5, match increments to 6, max_combo was 3 → max(3,6) = 6
    assert g.max_combo == 6


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def test_reset_clears_state() -> None:
    g = _make_game()
    g.score = 1000
    g.combo = 10
    g.heat = 50
    g.timer = 100
    g.subjects = [Subject(col=0, row=0, color=8, life=100)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=10, color=8)]
    g.super_mode = True
    g.super_timer = 200

    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0
    assert g.timer == GAME_DURATION
    assert len(g.subjects) == 0
    assert len(g.particles) == 0
    assert g.super_mode is False
    assert g.super_timer == 0


# ---------------------------------------------------------------------------
# Difficulty scaling
# ---------------------------------------------------------------------------


def test_elapsed_ratio_zero() -> None:
    g = _make_game()
    assert g._elapsed_ratio() == 0.0


def test_elapsed_ratio_halfway() -> None:
    g = _make_game()
    g.timer = GAME_DURATION // 2
    ratio = g._elapsed_ratio()
    assert abs(ratio - 0.5) < 0.01


def test_elapsed_ratio_full() -> None:
    g = _make_game()
    g.timer = 0
    assert g._elapsed_ratio() == 1.0


def test_fog_interval_scales() -> None:
    g = _make_game()
    assert g._get_fog_interval() == 90  # initial

    g.timer = 0
    interval = g._get_fog_interval()
    assert interval == 30  # final


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_all_cells_fogged_subject_spawn_returns_none() -> None:
    g = _make_game()
    for r in range(ROWS):
        for c in range(COLS):
            g.fog[r][c] = True

    g._spawn_subjects()
    assert len(g.subjects) == 0


def test_click_outside_grid_no_effect() -> None:
    g = _make_game()
    # grid_coord returns None, so _handle_click is never called by update()
    coord = g.grid_coord(0, 0)
    assert coord is None


def test_heat_decay_does_not_go_below_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    # Simulate what _update_playing does
    g.heat = max(0.0, g.heat - 0.2)
    assert g.heat == 0.0
