"""Headless logic tests for FORGE CHAIN (309_forge_chain).

Run with:  uv run python prototypes/309_forge_chain/test_imports.py
or:        uv run pytest prototypes/309_forge_chain/test_imports.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (  # noqa: E402
    FloatingText,
    Game,
    Particle,
    Phase,
)


def _make_game() -> Game:
    """Factory: bypass pyxel init via Game.__new__, reset(), then start()."""
    g = Game.__new__(Game)
    g.reset()  # sets all attrs including frame=0 and rng (unseeded)
    g.rng = random.Random(42)  # re-seed AFTER reset (reset overwrites rng)
    g.start()  # phase=PLAYING + spawn billet using seeded rng
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
    assert g.temper == 0
    assert g.heat == 0.0
    assert g.timer == Game.TIMER_START
    assert g.super_timer == 0
    assert 0 <= g.billet_color < len(Game.METAL_COLORS)
    assert g.particles == []
    assert g.texts == []


def test_start_resets_gameplay_state() -> None:
    g = _make_game()
    # dirty the state
    g.score = 999
    g.combo = 7
    g.temper = 5
    g.heat = 80.0
    g.timer = 10
    g.super_timer = 50
    g.start()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.temper == 0
    assert g.heat == 0.0
    assert g.timer == Game.TIMER_START
    assert g.super_timer == 0


# --------------------------------------------------------------------------- #
# strike — match                                                              #
# --------------------------------------------------------------------------- #


def test_match_strike_increments_combo_temper_score() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 0
    g.combo = 0
    g.temper = 0
    g.score = 0
    g.super_timer = 0
    g._strike()
    assert g.combo == 1
    assert g.temper == 1
    assert g.score == 10 * 1 * (1 + 1 // 3)  # = 10
    assert g.heat == 0.0


def test_match_strike_score_formula_uses_temper_tier() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 0
    g.combo = 2
    g.temper = 5  # 5 // 3 == 1 -> multiplier tier 2
    g.score = 100
    g.super_timer = 0
    g._strike()
    # combo 2 -> 3, temper 5 -> 6; gained = 10*3*(1 + 6//3) = 10*3*3 = 90
    assert g.combo == 3
    assert g.temper == 6
    assert g.score == 100 + 10 * 3 * (1 + 6 // 3)


def test_match_strike_tracks_max_combo() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 0
    g.combo = 2
    g.max_combo = 2
    g.super_timer = 0
    g._strike()
    assert g.max_combo == 3


# --------------------------------------------------------------------------- #
# strike — mismatch                                                           #
# --------------------------------------------------------------------------- #


def test_mismatch_strike_heat_and_reset() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 1  # mismatch
    g.combo = 3
    g.temper = 2
    g.heat = 10.0
    g.super_timer = 0
    g._strike()
    assert g.heat == 25.0
    assert g.combo == 0
    assert g.temper == 1


def test_mismatch_temper_clamped_at_zero() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 1
    g.temper = 0
    g._strike()
    assert g.temper == 0


def test_mismatch_does_not_change_score() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 1
    g.score = 55
    g._strike()
    assert g.score == 55


# --------------------------------------------------------------------------- #
# super forge                                                                 #
# --------------------------------------------------------------------------- #


def test_super_forge_triggers_at_combo_4() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 0
    g.combo = 3
    g.super_timer = 0
    g._strike()
    assert g.combo == 4
    assert g.super_timer == Game.SUPER_DURATION


def test_super_mode_matches_any_color_and_3x() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 3  # normally a mismatch
    g.combo = 2
    g.temper = 2
    g.score = 0
    g.super_timer = 10  # active super mode
    g._strike()
    # matches despite color difference; combo 2->3, temper 2->3
    # gained = 10*3*(1 + 3//3)*3 = 10*3*2*3 = 180
    assert g.combo == 3
    assert g.temper == 3
    assert g.score == 180


def test_super_mode_does_not_retrigger() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 0
    g.combo = 5
    g.super_timer = 10
    g._strike()
    # combo >= 4 but super already active -> super_timer unchanged by strike
    assert g.super_timer == 10


def test_super_update_decrements_timer() -> None:
    g = _make_game()
    g.super_timer = 5
    g._update_super()
    assert g.super_timer == 4


# --------------------------------------------------------------------------- #
# quench                                                                      #
# --------------------------------------------------------------------------- #


def test_quench_banks_score_and_resets() -> None:
    g = _make_game()
    g.temper = 3
    g.combo = 2
    g.heat = 40.0
    g.score = 100
    g.super_timer = 0
    g._quench()
    assert g.score == 100 + 3 * 100 + 2 * 20  # = 440
    assert g.heat == 10.0
    assert g.combo == 0
    assert g.temper == 0


def test_quench_heat_clamped_at_zero() -> None:
    g = _make_game()
    g.temper = 1
    g.combo = 0
    g.heat = 10.0
    g.score = 0
    g._quench()
    assert g.heat == 0.0


def test_quench_noop_when_temper_zero() -> None:
    g = _make_game()
    g.temper = 0
    g.combo = 2
    g.heat = 50.0
    g.score = 100
    original_billet = g.billet_color
    g._quench()
    assert g.score == 100
    assert g.heat == 50.0
    assert g.combo == 2
    assert g.billet_color == original_billet


def test_quench_resets_super_timer() -> None:
    g = _make_game()
    g.temper = 2
    g.combo = 1
    g.super_timer = 50
    g._quench()
    assert g.super_timer == 0


def test_quench_spawns_new_billet() -> None:
    g = _make_game()
    g.temper = 2
    g.combo = 1
    g.rng = random.Random(7)
    g._quench()
    assert 0 <= g.billet_color < len(Game.METAL_COLORS)


# --------------------------------------------------------------------------- #
# heat / meltdown                                                             #
# --------------------------------------------------------------------------- #


def test_meltdown_at_heat_100() -> None:
    g = _make_game()
    g.heat = 100.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_decays_below_threshold() -> None:
    g = _make_game()
    g.heat = 50.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.PLAYING
    assert abs(g.heat - 49.97) < 0.01


def test_no_meltdown_just_below_100() -> None:
    g = _make_game()
    g.heat = 99.97
    g.phase = Phase.PLAYING
    g._update_heat()
    # threshold checked BEFORE decay: 99.97 < 100 -> no meltdown, heat decays
    assert g.phase == Phase.PLAYING
    assert abs(g.heat - 99.94) < 0.01


def test_meltdown_updates_best_score() -> None:
    g = _make_game()
    g.score = 400
    g.best_score = 100
    g.heat = 100.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 400


# --------------------------------------------------------------------------- #
# hammer cycling / escalation                                                 #
# --------------------------------------------------------------------------- #


def test_advance_hammer_cycles_color() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.hammer_timer = 1
    g.frame = 0
    g._advance_hammer()
    assert g.hammer_color == 1
    assert g.hammer_timer == 20  # interval at frame 0


def test_advance_hammer_no_change_before_timer() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.hammer_timer = 2
    g.frame = 0
    g._advance_hammer()
    assert g.hammer_color == 0
    assert g.hammer_timer == 1


def test_advance_hammer_wraps_around() -> None:
    g = _make_game()
    g.hammer_color = len(Game.METAL_COLORS) - 1
    g.hammer_timer = 1
    g.frame = 0
    g._advance_hammer()
    assert g.hammer_color == 0


def test_cycle_interval_escalation() -> None:
    g = _make_game()
    g.frame = 0
    assert g._cycle_interval() == 20
    g.frame = 4500
    assert g._cycle_interval() == 12


# --------------------------------------------------------------------------- #
# billet spawn / best score / game over                                       #
# --------------------------------------------------------------------------- #


def test_spawn_billet_in_range() -> None:
    g = _make_game()
    g.rng = random.Random(42)
    for _ in range(20):
        g._spawn_billet()
        assert 0 <= g.billet_color < len(Game.METAL_COLORS)


def test_best_score_update() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 100
    g._best_score_update()
    assert g.best_score == 500


def test_best_score_does_not_decrease() -> None:
    g = _make_game()
    g.score = 50
    g.best_score = 100
    g._best_score_update()
    assert g.best_score == 100


def test_timeup_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = 0
    g._game_over_timeup()
    assert g.phase == Phase.GAME_OVER


# --------------------------------------------------------------------------- #
# particles / floating text                                                   #
# --------------------------------------------------------------------------- #


def test_match_strike_spawns_particles_and_text() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 0
    g.combo = 0
    g.super_timer = 0
    g.particles = []
    g.texts = []
    g._strike()
    assert len(g.particles) == 8
    assert len(g.texts) == 1


def test_super_strike_spawns_more_particles() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 3
    g.super_timer = 10
    g.particles = []
    g._strike()
    assert len(g.particles) == 20


def test_mismatch_spawns_4_particles() -> None:
    g = _make_game()
    g.hammer_color = 0
    g.billet_color = 1
    g.particles = []
    g._strike()
    assert len(g.particles) == 4


def test_quench_spawns_16_particles() -> None:
    g = _make_game()
    g.temper = 2
    g.combo = 1
    g.particles = []
    g._quench()
    assert len(g.particles) == 16


def test_particle_update_removes_dead() -> None:
    g = _make_game()
    g.particles = [Particle(0.0, 0.0, 0.0, 0.0, 1, 8)]
    g._update_particles()
    assert g.particles == []


def test_text_update_removes_dead() -> None:
    g = _make_game()
    g.texts = [FloatingText(0.0, 0.0, "X", 8, 1)]
    g._update_texts()
    assert g.texts == []


# --------------------------------------------------------------------------- #
# dataclasses                                                                 #
# --------------------------------------------------------------------------- #


def test_particle_dataclass() -> None:
    p = Particle(1.0, 2.0, 3.0, 4.0, 5, 8)
    assert (p.x, p.y, p.vx, p.vy, p.life, p.color) == (1.0, 2.0, 3.0, 4.0, 5, 8)


def test_floating_text_dataclass() -> None:
    t = FloatingText(1.0, 2.0, "hi", 8, 5)
    assert (t.x, t.y, t.text, t.color, t.life) == (1.0, 2.0, "hi", 8, 5)


def test_metal_colors_and_names_aligned() -> None:
    assert len(Game.METAL_COLORS) == 4
    assert len(Game.METAL_NAMES) == 4
    assert Game.METAL_COLORS == (8, 11, 5, 10)


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
