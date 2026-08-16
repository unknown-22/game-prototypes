"""test_imports.py — Headless logic tests for 313_hydra_chain.

Uses Game.__new__(Game) to bypass __init__ (avoids pyxel.init/run panic).
reset() is self-contained (assigns all instance attributes), so no pre-init
block is required before calling reset().
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import FloatingText, Game, Head, Particle, Phase  # noqa: E402


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.reset()
    return g


# --------------------------------------------------------------------------
# reset / initialization
# --------------------------------------------------------------------------


def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.frame == 0
    assert g.timer == Game.GAME_LENGTH
    assert len(g.heads) == Game.HEADS_START
    assert all(h.tier == 1 for h in g.heads)
    assert all(0 <= h.color < 4 for h in g.heads)
    assert g.blade_color == 0
    assert g.super_timer == 0
    assert g.particles == []
    assert g.floats == []
    assert g.respawn_queue == []


def test_reset_seeds_rng_deterministically():
    g1 = _make_game()
    g2 = _make_game()
    assert [h.color for h in g1.heads] == [h.color for h in g2.heads]


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------


def test_head_at_hit():
    g = _make_game()
    g.heads = [Head(color=0, tier=1)]
    hx, hy = g._head_pos(0)
    assert g._head_at(hx, hy) == 0
    assert g._head_at(hx + g._head_radius(1), hy) == 0


def test_head_at_miss():
    g = _make_game()
    g.heads = [Head(color=0, tier=1)]
    assert g._head_at(5, 5) is None


def test_head_at_empty():
    g = _make_game()
    g.heads = []
    assert g._head_at(36, 118) is None


def test_chain_run_contiguous():
    g = _make_game()
    g.heads = [Head(0, 1), Head(0, 1), Head(0, 1)]
    assert g._chain_run(1, 0) == [0, 1, 2]
    assert g._chain_run(0, 0) == [0, 1, 2]


def test_chain_run_stops_at_color_change():
    g = _make_game()
    g.heads = [Head(1, 1), Head(0, 1), Head(0, 1), Head(1, 1)]
    assert g._chain_run(1, 0) == [1, 2]


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------


def test_do_cut_score():
    g = _make_game()
    g.heads = [Head(color=0, tier=2)]
    g.combo = 3
    g.super_timer = 0
    assert g._do_cut_score(0) == 10 * 3 * 2 * 1
    g.super_timer = 1
    assert g._do_cut_score(0) == 10 * 3 * 2 * 3


# --------------------------------------------------------------------------
# cut (match)
# --------------------------------------------------------------------------


def test_cut_matching_head_scores_and_removes():
    g = _make_game()
    g.heads = [Head(color=0, tier=1)]
    g.blade_color = 0
    g._cut_head(0)
    assert g.score == 10          # first cut scores 10*tier (combo increments first)
    assert g.combo == 1
    assert len(g.heads) == 0
    assert len(g.respawn_queue) == 1


def test_cut_higher_tier_scores_more():
    g = _make_game()
    g.heads = [Head(color=0, tier=3)]
    g.blade_color = 0
    g._cut_head(0)
    assert g.score == 30          # 10 * combo(1) * tier(3)


def test_cut_chain_scores_all_contiguous():
    g = _make_game()
    g.heads = [Head(0, 1), Head(0, 1), Head(0, 1)]
    g.blade_color = 0
    g._cut_head(1)
    # combo 1,2,3 -> gains 10*1 + 10*2 + 10*3 = 60
    assert g.score == 60
    assert g.combo == 3
    assert g.max_combo == 3
    assert len(g.heads) == 0
    assert len(g.respawn_queue) == 3


def test_cut_chain_ignores_non_contiguous_same_color():
    g = _make_game()
    g.heads = [Head(0, 1), Head(0, 1), Head(1, 1), Head(0, 1)]
    g.blade_color = 0
    g._cut_head(0)
    assert g.combo == 2
    assert len(g.heads) == 2      # color-1 and trailing color-0 heads remain
    assert g.heads[0].color == 1
    assert g.heads[1].color == 0


# --------------------------------------------------------------------------
# cut (mismatch)
# --------------------------------------------------------------------------


def test_cut_mismatch_adds_heat_and_resets_combo():
    g = _make_game()
    g.heads = [Head(color=1, tier=1)]
    g.blade_color = 0
    g.combo = 3
    g.max_combo = 3
    g._cut_head(0)
    assert g.heat == 15
    assert g.combo == 0
    assert len(g.heads) == 1      # head stays
    assert g.score == 0


# --------------------------------------------------------------------------
# super blade
# --------------------------------------------------------------------------


def test_super_activates_at_combo_4():
    g = _make_game()
    g.heads = [Head(0, 1)] * 4
    g.blade_color = 0
    g._cut_head(0)                # cuts all 4 contiguous
    assert g.combo == 4
    assert g.super_timer == Game.SUPER_DURATION


def test_super_allows_any_color_match():
    g = _make_game()
    g.heads = [Head(color=1, tier=1)]
    g.blade_color = 0
    g.super_timer = 100
    g.combo = 5
    g._cut_head(0)                # mismatched color, but SUPER active
    assert g.score == 10 * 6 * 1 * 3   # combo 5->6, 3x multiplier
    assert len(g.heads) == 0


def test_super_does_not_freeze_combo_on_regular_cut():
    g = _make_game()
    g.super_timer = 0
    g.heads = [Head(color=0, tier=1)]
    g.blade_color = 0
    g._cut_head(0)
    assert g.score == 10


# --------------------------------------------------------------------------
# strike (inversion: grow / enrage)
# --------------------------------------------------------------------------


def test_strike_grows_tier():
    g = _make_game()
    g.heads = [Head(color=0, tier=1)]
    g._strike_head(0)
    assert g.heads[0].tier == 2
    g._strike_head(0)
    assert g.heads[0].tier == 3


def test_strike_at_max_tier_enrages():
    g = _make_game()
    g.heads = [Head(color=0, tier=3)]
    g.heat = 0.0
    g._strike_head(0)
    assert g.heads[0].tier == 1    # reset
    assert g.heat == 20            # enrage heat
    assert len(g.heads) == 2       # hydra multiplies (+1 head)


def test_strike_enrage_caps_at_max_heads():
    g = _make_game()
    g.heads = [Head(color=0, tier=3)] * Game.MAX_HEADS
    g._strike_head(0)
    assert len(g.heads) == Game.MAX_HEADS
    assert g.heads[0].tier == 1


def test_spawn_head_caps_at_max_heads():
    g = _make_game()
    g.heads = [Head(color=0, tier=1)] * Game.MAX_HEADS
    g._spawn_head()
    assert len(g.heads) == Game.MAX_HEADS


# --------------------------------------------------------------------------
# heat / failure conditions
# --------------------------------------------------------------------------


def test_update_heat_clamps_positive():
    g = _make_game()
    g.heat = 1.0
    g._update_heat(-5.0)
    assert g.heat == 0.0


def test_update_heat_triggers_game_over_at_cap():
    g = _make_game()
    g.heat = 95.0
    g._update_heat(10.0)
    assert g.heat == 100.0
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "HYDRA RAMPAGE"


def test_update_timer_decrements_and_game_overs():
    g = _make_game()
    g.timer = 2
    g._update_timer()
    assert g.frame == 1
    assert g.timer == 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "TIME UP"


# --------------------------------------------------------------------------
# escalation
# --------------------------------------------------------------------------


def test_cycle_interval_escalates():
    g = _make_game()
    g.frame = 0
    assert g._cycle_interval() == 20
    g.frame = 120
    assert g._cycle_interval() == 19
    g.frame = 2000
    assert g._cycle_interval() == 12


def test_respawn_delay_escalates():
    g = _make_game()
    g.frame = 0
    assert g._respawn_delay() == 60
    g.frame = 3600
    assert g._respawn_delay() == 25


# --------------------------------------------------------------------------
# blade cycling
# --------------------------------------------------------------------------


def test_blade_cycles_after_interval():
    g = _make_game()
    g.blade_color = 0
    g.blade_timer = 0
    g.frame = 0                  # interval 20
    for _ in range(19):
        g._update_blade()
    assert g.blade_color == 0
    g._update_blade()            # 20th call triggers cycle
    assert g.blade_color == 1


# --------------------------------------------------------------------------
# respawn queue / super / particles / floats
# --------------------------------------------------------------------------


def test_update_heads_processes_respawn_queue():
    g = _make_game()
    g.heads = [Head(color=0, tier=1)]
    g.respawn_queue = [1, 3]
    g._update_heads()
    assert len(g.heads) == 2
    assert g.respawn_queue == [2]


def test_update_super_decrements():
    g = _make_game()
    g.super_timer = 5
    g._update_super()
    assert g.super_timer == 4
    g.super_timer = 0
    g._update_super()
    assert g.super_timer == 0


def test_update_particles_lifecycle():
    g = _make_game()
    g.particles = [Particle(0, 0, 1, 1, 2, 8)]
    g._update_particles()
    assert len(g.particles) == 1
    g._update_particles()
    assert len(g.particles) == 0


def test_update_floats_lifecycle():
    g = _make_game()
    g.floats = [FloatingText(0, 0, "x", 2, 7)]
    g._update_floats()
    assert len(g.floats) == 1
    g._update_floats()
    assert len(g.floats) == 0


# --------------------------------------------------------------------------
# best score persistence across restart
# --------------------------------------------------------------------------


def test_best_score_persists_across_reset():
    g = _make_game()
    g.score = 500
    g._trigger_game_over("TIME UP")
    assert g.best_score == 500
    g.reset()
    assert g.best_score == 500
    assert g.score == 0


def test_trigger_game_over_sets_reason():
    g = _make_game()
    g._trigger_game_over("TIME UP")
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "TIME UP"


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
