"""Headless logic tests for SEW CHAIN (312_sew_chain).

Run with:  uv run python prototypes/312_sew_chain/test_imports.py
or:        uv run pytest prototypes/312_sew_chain/test_imports.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (  # noqa: E402
    FABRIC_COLORS,
    NUM_PATCHES,
    PATCH_SIZE,
    PATCH_X0,
    PATCH_STEP,
    PATCH_Y,
    FloatingText,
    Game,
    Particle,
    Patch,
    Phase,
)


def _make_game() -> Game:
    """Factory: bypass pyxel init via Game.__new__, pre-init reset() attrs."""
    g = Game.__new__(Game)
    g.patches = []
    g.particles = []
    g.floats = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.thread = Game.THREAD_MAX
    g.needle_color = 0
    g.needle_timer = 0
    g.timer = Game.GAME_TIME
    g.elapsed = 0
    g.super_timer = 0
    g.rethread_timer = 0
    g.shake = 0
    g.best_score = 0
    g.frame = 0
    g.phase = Phase.TITLE
    g.reset()
    return g


def _alive_color_set(g: Game) -> set[int]:
    return {p.color for p in g.patches if p.respawn_timer == 0}


# --------------------------------------------------------------------------- #
# reset / initial state                                                        #
# --------------------------------------------------------------------------- #


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.thread == Game.THREAD_MAX
    assert g.needle_color == 0
    assert g.needle_timer == 0
    assert g.timer == Game.GAME_TIME
    assert g.elapsed == 0
    assert g.super_timer == 0
    assert g.rethread_timer == 0
    assert g.shake == 0
    assert g.best_score == 0
    assert g.frame == 0
    assert g.particles == []
    assert g.floats == []
    assert len(g.patches) == NUM_PATCHES
    assert all(p.respawn_timer == 0 for p in g.patches)
    assert all(0 <= p.color < 4 for p in g.patches)


def test_reset_is_deterministic_with_seed() -> None:
    a = _make_game()
    b = _make_game()
    assert [p.color for p in a.patches] == [p.color for p in b.patches]


def test_reset_clears_previous_state() -> None:
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.heat = 90.0
    g.thread = 0
    g.particles.append(Particle(1, 1, 0, 0, 5, 7))
    g.floats.append(FloatingText(1, 1, "x", 5, 7))
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.thread == Game.THREAD_MAX
    assert g.particles == []
    assert g.floats == []
    assert len(g.patches) == NUM_PATCHES


# --------------------------------------------------------------------------- #
# difficulty escalation                                                        #
# --------------------------------------------------------------------------- #


def test_cycle_interval_decreases_with_elapsed() -> None:
    g = _make_game()
    g.elapsed = 0
    assert g._cycle_interval() == 20
    g.elapsed = 600
    assert g._cycle_interval() == 15
    g.elapsed = 3600
    assert g._cycle_interval() == 12  # floor


def test_respawn_delay_decreases_with_elapsed() -> None:
    g = _make_game()
    g.elapsed = 0
    assert g._respawn_delay() == 60
    g.elapsed = 3600
    assert g._respawn_delay() == 25  # floor


def test_heat_decay_is_negative() -> None:
    g = _make_game()
    assert g._heat_decay() < 0


# --------------------------------------------------------------------------- #
# _sew: match / mismatch / no thread / dead patch                              #
# --------------------------------------------------------------------------- #


def test_sew_match_increments_combo_and_score() -> None:
    g = _make_game()
    g.patches[0] = Patch(color=0, x=0, y=0, respawn_timer=0)
    g.needle_color = 0
    g.combo = 2
    assert g._sew(0) == (True, "+30")
    assert g.combo == 3
    assert g.max_combo == 3
    assert g.score == 30  # 10 * 3 (new combo)
    assert g.thread == Game.THREAD_MAX - 1
    assert g.patches[0].respawn_timer > 0


def test_sew_score_uses_new_combo() -> None:
    g = _make_game()
    for i in range(NUM_PATCHES):
        g.patches[i] = Patch(color=0, x=0, y=0, respawn_timer=0)
    g.needle_color = 0
    g._sew(0)
    assert g.score == 10  # combo 1 -> 10
    g._sew(1)
    assert g.score == 30  # combo 2 -> +20


def test_sew_mismatch_adds_heat_and_resets_combo() -> None:
    g = _make_game()
    g.patches[0] = Patch(color=0, x=0, y=0, respawn_timer=0)
    g.needle_color = 1  # wrong
    g.combo = 4
    g.thread = Game.THREAD_MAX
    assert g._sew(0) == (False, "WRONG!")
    assert g.heat == 15.0
    assert g.combo == 0
    assert g.thread == Game.THREAD_MAX - 1  # wasted
    assert g.patches[0].respawn_timer == 0  # patch stays alive
    assert g.shake == 8


def test_sew_no_thread_returns_no_thread() -> None:
    g = _make_game()
    g.patches[0] = Patch(color=0, x=0, y=0, respawn_timer=0)
    g.needle_color = 0
    g.thread = 0
    score_before = g.score
    assert g._sew(0) == (False, "NO THREAD")
    assert g.score == score_before
    assert g.combo == 0
    assert g.patches[0].respawn_timer == 0  # no state change


def test_sew_dead_patch_is_noop() -> None:
    g = _make_game()
    g.patches[0] = Patch(color=0, x=0, y=0, respawn_timer=5)
    g.needle_color = 0
    g.thread = Game.THREAD_MAX
    score_before = g.score
    assert g._sew(0) == (False, "")
    assert g.score == score_before
    assert g.thread == Game.THREAD_MAX


# --------------------------------------------------------------------------- #
# SUPER STITCH                                                                 #
# --------------------------------------------------------------------------- #


def test_combo_4_triggers_super() -> None:
    g = _make_game()
    for i in range(NUM_PATCHES):
        g.patches[i] = Patch(color=0, x=0, y=0, respawn_timer=0)
    g.needle_color = 0
    for i in range(4):
        g._sew(i)
    assert g.super_timer == Game.SUPER_DURATION


def test_super_does_not_retrigger() -> None:
    g = _make_game()
    for i in range(NUM_PATCHES):
        g.patches[i] = Patch(color=0, x=0, y=0, respawn_timer=0)
    g.needle_color = 0
    for i in range(4):
        g._sew(i)
    assert g.super_timer == Game.SUPER_DURATION
    g._sew(4)
    assert g.super_timer == Game.SUPER_DURATION  # unchanged (no re-trigger)


def test_super_matches_any_color() -> None:
    g = _make_game()
    g.super_timer = 10
    g.patches[0] = Patch(color=3, x=0, y=0, respawn_timer=0)
    g.needle_color = 0
    assert g._sew(0)[0] is True
    assert g.combo == 1


def test_super_triples_score_and_does_not_consume_thread() -> None:
    g = _make_game()
    g.super_timer = 10
    g.patches[0] = Patch(color=2, x=0, y=0, respawn_timer=0)
    g.needle_color = 0
    g.combo = 0
    g.thread = Game.THREAD_MAX
    g._sew(0)
    assert g.score == 10 * 1 * 3  # combo 1 (new) * 3x super
    assert g.thread == Game.THREAD_MAX  # thread NOT consumed in super


# --------------------------------------------------------------------------- #
# RETHREAD                                                                     #
# --------------------------------------------------------------------------- #


def test_rethread_requires_low_thread() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.thread = Game.THREAD_MAX
    assert g._rethread() is False
    g.thread = Game.THREAD_MAX - 1
    assert g._rethread() is True
    assert g.phase == Phase.RETHREADING
    assert g.rethread_timer == Game.RETHREAD_DURATION


def test_rethread_only_in_playing_phase() -> None:
    g = _make_game()
    g.thread = 0
    assert g._rethread() is False  # phase is TITLE


def test_finish_rethread_restores_thread_and_adds_heat() -> None:
    g = _make_game()
    g.phase = Phase.RETHREADING
    g.thread = 0
    g.combo = 6
    g.heat = 10.0
    g._finish_rethread()
    assert g.thread == Game.THREAD_MAX
    assert g.combo == 0
    assert g.heat == 15.0
    assert g.phase == Phase.PLAYING


def test_rethread_update_finishes() -> None:
    g = _make_game()
    g.phase = Phase.RETHREADING
    g.rethread_timer = 1
    g.thread = 0
    g._update_rethreading()
    assert g.rethread_timer == 0
    assert g.phase == Phase.PLAYING
    assert g.thread == Game.THREAD_MAX


# --------------------------------------------------------------------------- #
# heat / game over                                                             #
# --------------------------------------------------------------------------- #


def test_heat_decays_over_time() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 10.0
    g._update_heat()
    assert abs(g.heat - 9.98) < 0.01


def test_heat_threshold_triggers_game_over_before_decay() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = Game.HEAT_MAX
    g.score = 500
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500
    assert g.heat == Game.HEAT_MAX  # threshold checked FIRST, no decay


def test_heat_frozen_during_rethread() -> None:
    g = _make_game()
    g.phase = Phase.RETHREADING
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0


def test_heat_frozen_during_super() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_timer = 10
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0


def test_heat_clamped_at_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


# --------------------------------------------------------------------------- #
# needle cycling                                                               #
# --------------------------------------------------------------------------- #


def test_needle_cycles_when_timer_expires() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.needle_color = 0
    g.needle_timer = g._cycle_interval() - 1
    g._update_needle()
    assert g.needle_color == 1
    assert g.needle_timer == 0


def test_needle_does_not_cycle_early() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.needle_color = 0
    g.needle_timer = 5
    g._update_needle()
    assert g.needle_color == 0
    assert g.needle_timer == 6


def test_needle_skips_advance_during_rethread() -> None:
    g = _make_game()
    g.phase = Phase.RETHREADING
    g.needle_color = 0
    g.needle_timer = g._cycle_interval() - 1
    g._update_needle()
    assert g.needle_color == 0  # frozen
    assert g.needle_timer == g._cycle_interval() - 1


def test_needle_wraps_around() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.needle_color = 3
    g.needle_timer = g._cycle_interval() - 1
    g._update_needle()
    assert g.needle_color == 0


# --------------------------------------------------------------------------- #
# patch respawn                                                                 #
# --------------------------------------------------------------------------- #


def test_patch_respawns_with_new_color() -> None:
    g = _make_game()
    g.patches = [Patch(color=0, x=0, y=0, respawn_timer=0) for _ in range(NUM_PATCHES)]
    g.patches[0].respawn_timer = 1
    g._update_patches()
    assert g.patches[0].respawn_timer == 0
    assert 0 <= g.patches[0].color < 4


def test_patch_respawn_timer_decrements() -> None:
    g = _make_game()
    g.patches = [Patch(color=0, x=0, y=0, respawn_timer=0) for _ in range(NUM_PATCHES)]
    g.patches[0].respawn_timer = 3
    g._update_patches()
    assert g.patches[0].respawn_timer == 2
    assert g.patches[0].color == 0  # unchanged until timer hits 0


# --------------------------------------------------------------------------- #
# particles / floating text                                                    #
# --------------------------------------------------------------------------- #


def test_particles_advance_and_expire() -> None:
    g = _make_game()
    g.particles.append(Particle(0, 0, 1.0, 0.5, 2, 8))
    g._update_particles()
    assert g.particles[0].x == 1.0
    assert g.particles[0].y == 0.5
    assert g.particles[0].life == 1
    g._update_particles()
    assert g.particles == []


def test_floats_advance_and_expire() -> None:
    g = _make_game()
    g.floats.append(FloatingText(1, 1, "hi", 1, 7))
    g._update_floats()
    assert g.floats == []


# --------------------------------------------------------------------------- #
# layout                                                                        #
# --------------------------------------------------------------------------- #


def test_patch_layout_fits_screen() -> None:
    g = _make_game()
    for i, p in enumerate(g.patches):
        assert p.x == PATCH_X0 + i * PATCH_STEP
        assert p.y == PATCH_Y
        assert p.x + PATCH_SIZE <= 320


def test_fabric_colors_are_distinct() -> None:
    assert len(set(FABRIC_COLORS)) == 4


# --------------------------------------------------------------------------- #
# main guard (standalone run)                                                  #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
