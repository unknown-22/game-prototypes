"""Headless logic tests for SNIP CHAIN (310_snip_chain).

Run with:  uv run python prototypes/310_snip_chain/test_imports.py
or:        uv run pytest prototypes/310_snip_chain/test_imports.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (  # noqa: E402
    COLS,
    HAIR_COLORS,
    ROWS,
    START_TIME,
    SUPER_DURATION,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def _make_game() -> Game:
    """Factory: bypass pyxel init via Game.__new__, pre-init rng/best_score, reset()."""
    g = Game.__new__(Game)
    g.rng = random.Random(42)  # reset() USES rng to seed initial locks
    g.best_score = 0  # only set in __init__, NOT in reset()
    g.reset()
    g.rng = random.Random(42)  # re-seed after reset for deterministic growth tests
    return g


# --------------------------------------------------------------------------- #
# reset / initial state                                                        #
# --------------------------------------------------------------------------- #


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == START_TIME
    assert g.scissors_color == 1
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.game_over_reason == ""
    assert len(g.grid) == ROWS
    assert all(len(row) == COLS for row in g.grid)


def test_reset_seeds_only_bottom_row() -> None:
    g = _make_game()
    for r in range(ROWS - 1):
        assert all(v == 0 for v in g.grid[r]), "seed locks must be on the bottom row only"
    filled = sum(1 for v in g.grid[ROWS - 1] if v != 0)
    assert 1 <= filled <= 4  # up to 4 seeds, duplicates may collide


# --------------------------------------------------------------------------- #
# snip — match                                                                #
# --------------------------------------------------------------------------- #


def test_snip_match_increments_combo_and_score() -> None:
    g = _make_game()
    g.grid[3][5] = 2  # row 3, col 5 -> color 2 (LIME)
    g.scissors_color = 2
    g.combo = 0
    g.score = 0
    result = g._snip(5, 3)
    assert result == "MATCH"
    assert g.grid[3][5] == 0  # lock removed
    assert g.combo == 1
    assert g.score == 10  # 10 * 1 * 1


def test_snip_match_score_formula_scales_with_combo() -> None:
    g = _make_game()
    g.grid[7][0] = 1
    g.scissors_color = 1
    g.combo = 4
    g.score = 100
    result = g._snip(0, 7)
    assert result == "MATCH"
    assert g.combo == 5
    assert g.score == 100 + 10 * 5  # = 150


def test_snip_match_tracks_max_combo() -> None:
    g = _make_game()
    g.grid[7][0] = 1
    g.scissors_color = 1
    g.combo = 2
    g.max_combo = 2
    g._snip(0, 7)
    assert g.max_combo == 3


def test_snip_match_spawns_particles_and_text() -> None:
    g = _make_game()
    g.grid[7][0] = 1
    g.scissors_color = 1
    g.particles = []
    g.floating_texts = []
    g._snip(0, 7)
    assert len(g.particles) == 8
    assert len(g.floating_texts) == 1


# --------------------------------------------------------------------------- #
# snip — mismatch                                                             #
# --------------------------------------------------------------------------- #


def test_snip_mismatch_heat_and_combo_reset() -> None:
    g = _make_game()
    g.grid[3][5] = 2
    g.scissors_color = 1
    g.combo = 3
    g.heat = 0.0
    result = g._snip(5, 3)
    assert result == "MISMATCH"
    assert g.grid[3][5] == 2  # lock NOT removed
    assert g.combo == 0
    assert g.heat == 15.0


def test_snip_mismatch_does_not_change_score() -> None:
    g = _make_game()
    g.grid[3][5] = 2
    g.scissors_color = 1
    g.score = 55
    g._snip(5, 3)
    assert g.score == 55


def test_snip_mismatch_spawns_4_particles() -> None:
    g = _make_game()
    g.grid[3][5] = 2
    g.scissors_color = 1
    g.particles = []
    g._snip(5, 3)
    assert len(g.particles) == 4


def test_snip_mismatch_sets_shake() -> None:
    g = _make_game()
    g.grid[3][5] = 2
    g.scissors_color = 1
    g.shake_frames = 0
    g._snip(5, 3)
    assert g.shake_frames == 6


# --------------------------------------------------------------------------- #
# snip — empty / out of bounds                                                #
# --------------------------------------------------------------------------- #


def test_snip_empty_cell_noop() -> None:
    g = _make_game()
    g.grid[3][5] = 0
    g.scissors_color = 1
    g.combo = 2
    g.heat = 0.0
    result = g._snip(5, 3)
    assert result == "EMPTY"
    assert g.combo == 2
    assert g.heat == 0.0


def test_snip_out_of_bounds() -> None:
    g = _make_game()
    assert g._snip(-1, 3) == "EMPTY"
    assert g._snip(COLS, 3) == "EMPTY"
    assert g._snip(0, -1) == "EMPTY"
    assert g._snip(0, ROWS) == "EMPTY"


# --------------------------------------------------------------------------- #
# super snip                                                                  #
# --------------------------------------------------------------------------- #


def test_super_triggers_at_combo_4() -> None:
    g = _make_game()
    g.scissors_color = 1
    g.combo = 3
    g.super_mode = False
    g.grid[7][0] = 1
    g._snip(0, 7)
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_activating_snip_scores_1x_not_3x() -> None:
    g = _make_game()
    g.scissors_color = 1
    g.combo = 3
    g.score = 0
    g.super_mode = False
    g.grid[7][0] = 1
    g._snip(0, 7)
    # 4th match: combo 3 -> 4, mult still 1 (super activates AFTER scoring)
    assert g.score == 40  # 10 * 4 * 1


def test_super_mode_matches_any_color_and_3x() -> None:
    g = _make_game()
    g.scissors_color = 1
    g.grid[7][0] = 3  # normally a mismatch
    g.combo = 4
    g.super_mode = True
    g.super_timer = 10
    g.score = 0
    result = g._snip(0, 7)
    assert result == "MATCH"
    assert g.combo == 5
    assert g.score == 150  # 10 * 5 * 3


def test_super_mode_does_not_retrigger() -> None:
    g = _make_game()
    g.scissors_color = 1
    g.grid[7][0] = 1
    g.combo = 5
    g.super_mode = True
    g.super_timer = 10
    g._snip(0, 7)
    assert g.super_timer == 10  # unchanged by the snip


def test_super_update_decrements_and_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_mode is False
    assert g.super_timer == 0


def test_super_update_noop_when_inactive() -> None:
    g = _make_game()
    g.super_mode = False
    g.super_timer = 5
    g._update_super()
    assert g.super_timer == 5


# --------------------------------------------------------------------------- #
# growth CA                                                                   #
# --------------------------------------------------------------------------- #


def test_grow_hair_snapshot_no_cascade() -> None:
    g = _make_game()
    g.grid = [[0] * COLS for _ in range(ROWS)]
    g.grid[ROWS - 1][0] = 1  # single lock on the bottom row
    g._grow_hair()
    # Snapshot semantics: after ONE pass, no lock may appear above row ROWS-2
    # (a lock at ROWS-1 can only grow ROWS-2 this pass; ROWS-2 growth must not
    # cascade to ROWS-3 in the same pass).
    for r in range(0, ROWS - 2):
        for c in range(COLS):
            assert g.grid[r][c] == 0, f"snapshot violated at row {r} col {c}"


def test_grow_hair_fills_bottom_row_from_scalp() -> None:
    g = _make_game()
    g.rng = random.Random(0)
    g.grid = [[0] * COLS for _ in range(ROWS)]
    g._grow_hair()
    # The bottom row (scalp) is always a candidate; with a seeded rng at 0.35
    # chance across 10 columns, at least one lock should sprout.
    assert any(g.grid[ROWS - 1][c] != 0 for c in range(COLS))


def test_grow_hair_fills_upward_over_time() -> None:
    g = _make_game()
    g.rng = random.Random(0)
    g.grid = [[0] * COLS for _ in range(ROWS)]
    for _ in range(30):
        g._grow_hair()
    filled = sum(1 for row in g.grid for v in row if v != 0)
    assert filled > 0


# --------------------------------------------------------------------------- #
# overgrown                                                                   #
# --------------------------------------------------------------------------- #


def test_check_overgrown_false_when_top_row_empty() -> None:
    g = _make_game()
    g.grid = [[0] * COLS for _ in range(ROWS)]
    assert g._check_overgrown() is False


def test_check_overgrown_true_when_top_row_filled() -> None:
    g = _make_game()
    g.grid = [[0] * COLS for _ in range(ROWS)]
    g.grid[0][3] = 2
    assert g._check_overgrown() is True


def test_overgrown_game_over_via_update_playing() -> None:
    g = _make_game()
    g.grid[0][0] = 1  # a lock already at the top row
    g._update_playing()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "OVERGROWN"


# --------------------------------------------------------------------------- #
# heat / timer                                                                #
# --------------------------------------------------------------------------- #


def test_heat_threshold_game_over_before_decay() -> None:
    g = _make_game()
    g.heat = 100.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "NICKED OUT"


def test_heat_decays_below_threshold() -> None:
    g = _make_game()
    g.heat = 50.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.PLAYING
    assert abs(g.heat - 49.98) < 0.01


def test_no_game_over_just_below_100() -> None:
    g = _make_game()
    g.heat = 99.98
    g.phase = Phase.PLAYING
    g._update_heat()
    # threshold checked BEFORE decay: 99.98 < 100 -> stays playing, heat decays
    assert g.phase == Phase.PLAYING
    assert abs(g.heat - 99.96) < 0.01


def test_heat_frozen_in_super_mode() -> None:
    g = _make_game()
    g.heat = 50.0
    g.super_mode = True
    g._update_heat()
    assert g.heat == 50.0


def test_timer_game_over() -> None:
    g = _make_game()
    g.timer = 1
    g.phase = Phase.PLAYING
    g._update_timer()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "TIME UP"


# --------------------------------------------------------------------------- #
# color cycle / escalation                                                    #
# --------------------------------------------------------------------------- #


def test_color_cycle_advances_after_timer() -> None:
    g = _make_game()
    g.scissors_color = 1
    g.color_timer = 1
    g.cycle_interval = 20
    g._update_color_cycle()
    assert g.scissors_color == 2
    assert g.color_timer == 20


def test_color_cycle_wraps_around() -> None:
    g = _make_game()
    g.scissors_color = 4
    g.color_timer = 1
    g.cycle_interval = 20
    g._update_color_cycle()
    assert g.scissors_color == 1


def test_color_cycle_no_change_before_timer() -> None:
    g = _make_game()
    g.scissors_color = 1
    g.color_timer = 3
    g.cycle_interval = 20
    g._update_color_cycle()
    assert g.scissors_color == 1
    assert g.color_timer == 2


def test_cycle_interval_escalation() -> None:
    g = _make_game()
    g.elapsed = 0
    assert g._cycle_interval() == 20
    g.elapsed = 3600
    assert g._cycle_interval() == 12


def test_grow_interval_escalation() -> None:
    g = _make_game()
    g.elapsed = 0
    assert g._grow_interval() == 60
    g.elapsed = 3600
    assert g._grow_interval() == 30


# --------------------------------------------------------------------------- #
# best score                                                                  #
# --------------------------------------------------------------------------- #


def test_best_score_updates_on_game_over() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 100
    g.grid[0][0] = 1  # force overgrown -> game over
    g._update_playing()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500


def test_best_score_does_not_decrease() -> None:
    g = _make_game()
    g.score = 50
    g.best_score = 100
    g.grid[0][0] = 1
    g._update_playing()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 100


# --------------------------------------------------------------------------- #
# particles / floating text                                                   #
# --------------------------------------------------------------------------- #


def test_particle_update_removes_dead() -> None:
    g = _make_game()
    g.particles = [Particle(0.0, 0.0, 0.0, 0.0, 1, 8)]
    g._update_particles()
    assert g.particles == []


def test_particle_update_moves_and_decays() -> None:
    g = _make_game()
    g.particles = [Particle(0.0, 0.0, 1.0, -1.0, 5, 8)]
    g._update_particles()
    assert len(g.particles) == 1
    p = g.particles[0]
    assert p.x == 1.0
    assert p.y == -1.0
    assert p.life == 4


def test_floating_text_update_removes_dead() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(0.0, 0.0, "X", 8, 1)]
    g._update_floating_texts()
    assert g.floating_texts == []


def test_floating_text_rises_and_decays() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(10.0, 20.0, "+10", 8, 5)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    t = g.floating_texts[0]
    assert t.y == 19.5
    assert t.life == 4


# --------------------------------------------------------------------------- #
# dataclasses / constants                                                     #
# --------------------------------------------------------------------------- #


def test_particle_dataclass() -> None:
    p = Particle(1.0, 2.0, 3.0, 4.0, 5, 8)
    assert (p.x, p.y, p.vx, p.vy, p.life, p.color) == (1.0, 2.0, 3.0, 4.0, 5, 8)


def test_floating_text_dataclass() -> None:
    t = FloatingText(1.0, 2.0, "hi", 8, 5)
    assert (t.x, t.y, t.text, t.color, t.life) == (1.0, 2.0, "hi", 8, 5)


def test_hair_colors_mapping() -> None:
    assert HAIR_COLORS == {1: 8, 2: 11, 3: 5, 4: 10}


def test_phase_enum_members() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:  # noqa: PERF203
            failures += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
