"""Headless logic tests for TEA CHAIN (308_tea_chain).

Run with:  uv run python prototypes/308_tea_chain/test_imports.py
or:        uv run pytest prototypes/308_tea_chain/test_imports.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (  # noqa: E402
    GAME_TIME,
    MAX_HEAT,
    PATIENCE_MAX,
    STEEP_MAX,
    FloatText,
    Game,
    Guest,
    Particle,
    Phase,
)


def _make_game() -> Game:
    """Factory: bypass pyxel init via Game.__new__, pre-init all attrs, reset()."""
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_TIME
    g.steep = 0
    g.brew_color = 0
    g.color_timer = 20
    g.spawn_timer = 90
    g.super_timer = 0
    g.shake_frames = 0
    g.guests = []
    g.particles = []
    g.floating_texts = []
    g.reset()
    g.phase = Phase.PLAYING
    return g


# --------------------------------------------------------------------------- #
# reset / initial state                                                        #
# --------------------------------------------------------------------------- #


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.best_score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == GAME_TIME
    assert g.steep == 0
    assert g.brew_color == 0
    assert g.super_timer == 0
    assert g.guests == []
    assert g.particles == []
    assert g.floating_texts == []


def test_dataclass_fields() -> None:
    guest = Guest(seat=1, color=2, patience=600)
    assert guest.seat == 1
    assert guest.color == 2
    assert guest.patience == 600
    p = Particle(0.0, 0.0, 1.0, -1.0, 10, 8)
    assert p.life == 10
    ft = FloatText(10.0, 20.0, "hi", 30, 7)
    assert ft.text == "hi"


# --------------------------------------------------------------------------- #
# serve()                                                                      #
# --------------------------------------------------------------------------- #


def test_serve_empty_seat() -> None:
    g = _make_game()
    assert g.serve(0) == "empty"
    assert g.combo == 0
    assert g.score == 0


def test_serve_match_builds_combo_and_score() -> None:
    g = _make_game()
    g.guests.append(Guest(0, 0, PATIENCE_MAX))  # color 0 == brew_color 0
    assert g.serve(0) == "match"
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 10  # 10 * 1 * 1
    assert g.steep == 0
    assert g.guests == []


def test_serve_match_steep_multiplier_1x_2x_3x() -> None:
    # steep 14 -> 1x
    g = _make_game()
    g.steep = 14
    g.guests.append(Guest(0, 0, PATIENCE_MAX))
    g.serve(0)
    assert g.score == 10
    # steep 15 -> 2x
    g = _make_game()
    g.steep = 15
    g.guests.append(Guest(0, 0, PATIENCE_MAX))
    g.serve(0)
    assert g.score == 20
    # steep 44 -> 3x
    g = _make_game()
    g.steep = 44
    g.guests.append(Guest(0, 0, PATIENCE_MAX))
    g.serve(0)
    assert g.score == 30


def test_serve_consecutive_matches_compound_combo() -> None:
    g = _make_game()
    g.guests.append(Guest(0, 0, PATIENCE_MAX))
    g.serve(0)
    g.guests.append(Guest(1, 0, PATIENCE_MAX))
    g.serve(1)
    assert g.combo == 2
    assert g.max_combo == 2
    assert g.score == 10 + 20  # 10*1 + 10*2


def test_serve_wrong_color() -> None:
    g = _make_game()
    g.guests.append(Guest(0, 1, PATIENCE_MAX))  # color 1 != brew_color 0
    assert g.serve(0) == "wrong"
    assert g.heat == 15.0
    assert g.combo == 0
    assert len(g.guests) == 1  # guest stays


def test_serve_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.combo = 3
    g.guests.append(Guest(0, 1, PATIENCE_MAX))
    g.serve(0)
    assert g.combo == 0


def test_serve_wrong_color_can_game_over() -> None:
    g = _make_game()
    g.heat = 90.0
    g.guests.append(Guest(0, 1, PATIENCE_MAX))
    g.serve(0)  # heat 90 -> 105
    assert g.phase == Phase.GAME_OVER


def test_serve_super_matches_any_color_with_3x() -> None:
    g = _make_game()
    g.super_timer = 100
    g.combo = 1
    g.steep = 0
    g.guests.append(Guest(0, 1, PATIENCE_MAX))  # mismatched but SUPER matches all
    assert g.serve(0) == "match"
    assert g.combo == 2
    assert g.score == 10 * 2 * 1 * 3  # 60


# --------------------------------------------------------------------------- #
# SUPER BREW activation                                                        #
# --------------------------------------------------------------------------- #


def test_super_brew_activates_at_combo_4() -> None:
    g = _make_game()
    for seat in (0, 1, 2):
        g.guests.append(Guest(seat, 0, PATIENCE_MAX))
        g.serve(seat)
    assert g.combo == 3
    assert g.super_timer == 0
    g.guests.append(Guest(0, 0, PATIENCE_MAX))
    g.serve(0)
    assert g.combo == 4
    assert g.super_timer == 300


def test_super_not_reactivated_while_active() -> None:
    g = _make_game()
    g.super_timer = 100
    g.combo = 4
    g.guests.append(Guest(0, 0, PATIENCE_MAX))
    g.serve(0)
    assert g.combo == 5
    assert g.super_timer == 100  # unchanged, not reset to 300


# --------------------------------------------------------------------------- #
# steep / over-steep                                                           #
# --------------------------------------------------------------------------- #


def test_steep_increments() -> None:
    g = _make_game()
    g._update_steep()
    assert g.steep == 1
    assert g.heat == 0.0


def test_over_steep_resets_steep_and_adds_heat() -> None:
    g = _make_game()
    g.steep = STEEP_MAX - 1  # 44
    g._update_steep()
    assert g.steep == 0
    assert g.heat == 12.0


def test_over_steep_does_not_reset_combo() -> None:
    g = _make_game()
    g.combo = 5
    g.steep = STEEP_MAX - 1
    g._update_steep()
    assert g.combo == 5


# --------------------------------------------------------------------------- #
# brew color cycle                                                             #
# --------------------------------------------------------------------------- #


def test_brew_color_cycles() -> None:
    g = _make_game()
    g.color_timer = 1
    g._update_brew_color()
    assert g.brew_color == 1
    g.color_timer = 1
    g._update_brew_color()
    assert g.brew_color == 2


def test_brew_color_wraps_at_4() -> None:
    g = _make_game()
    g.brew_color = 3
    g.color_timer = 1
    g._update_brew_color()
    assert g.brew_color == 0


def test_brew_color_cycle_speeds_up_over_time() -> None:
    g = _make_game()
    g.timer = 0  # elapsed = GAME_TIME (full 60s)
    g.color_timer = 1
    g._update_brew_color()
    assert g.color_timer == 12  # fastest cycle


# --------------------------------------------------------------------------- #
# spawn / guests                                                               #
# --------------------------------------------------------------------------- #


def test_spawn_guest_fills_empty_seat() -> None:
    g = _make_game()
    g._spawn_guest()
    assert len(g.guests) == 1
    assert g.guests[0].seat in (0, 1, 2)
    assert g.guests[0].patience == PATIENCE_MAX
    assert g.guests[0].color in range(4)


def test_spawn_guest_skips_when_full() -> None:
    g = _make_game()
    for seat in (0, 1, 2):
        g.guests.append(Guest(seat, 0, PATIENCE_MAX))
    g._spawn_guest()
    assert len(g.guests) == 3


def test_spawn_interval_decreases_over_time() -> None:
    g = _make_game()
    g.spawn_timer = 1
    g.timer = GAME_TIME - 3000  # elapsed 3000
    g._update_spawn()
    assert g.spawn_timer == 40  # floor clamp


def test_guest_patience_expiry() -> None:
    g = _make_game()
    g.guests.append(Guest(0, 0, 1))
    g.combo = 3
    g._update_guests()
    assert g.guests == []
    assert g.heat == 5.0
    assert g.combo == 0


# --------------------------------------------------------------------------- #
# heat / game over                                                             #
# --------------------------------------------------------------------------- #


def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert abs(g.heat - 9.98) < 0.001


def test_heat_frozen_during_super() -> None:
    g = _make_game()
    g.heat = 10.0
    g.super_timer = 100
    g._update_heat()
    assert g.heat == 10.0


def test_heat_floor_at_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_threshold_game_over_checked_before_decay() -> None:
    g = _make_game()
    g.heat = MAX_HEAT  # exactly 100.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_timer_game_over() -> None:
    g = _make_game()
    g.timer = 1
    g._check_game_over()  # timer still > 0
    assert g.phase == Phase.PLAYING
    g.timer = 0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_best_score_recorded_on_game_over() -> None:
    g = _make_game()
    g.score = 500
    g.heat = MAX_HEAT
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500


def test_best_score_does_not_regress() -> None:
    g = _make_game()
    g.best_score = 999
    g.score = 10
    g.heat = MAX_HEAT
    g._check_game_over()
    assert g.best_score == 999


# --------------------------------------------------------------------------- #
# particles / floating text lifecycle                                          #
# --------------------------------------------------------------------------- #


def test_particle_lifecycle() -> None:
    g = _make_game()
    g.particles = [Particle(0.0, 0.0, 1.0, 0.0, 1, 8)]
    g._update_particles()
    assert g.particles == []  # life 1 -> 0 -> removed


def test_floating_text_lifecycle() -> None:
    g = _make_game()
    g.floating_texts = [FloatText(0.0, 0.0, "x", 2, 7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1  # life 2 -> 1, still alive
    assert g.floating_texts[0].life == 1
    g._update_floating_texts()
    assert g.floating_texts == []  # life 1 -> 0 -> removed


def test_match_spawns_particles_and_text() -> None:
    g = _make_game()
    g.guests.append(Guest(0, 0, PATIENCE_MAX))
    g.serve(0)
    assert len(g.particles) == 8
    assert any("+" in ft.text for ft in g.floating_texts)


# --------------------------------------------------------------------------- #
# seat hitbox mapping (pure logic, no pyxel)                                   #
# --------------------------------------------------------------------------- #


def test_seat_at_mapping() -> None:
    g = _make_game()
    assert g._seat_at(70, 70) == 0
    assert g._seat_at(160, 70) == 1
    assert g._seat_at(250, 70) == 2
    assert g._seat_at(10, 10) is None
    assert g._seat_at(70, 200) is None


def test_phase_not_playing_blocks_serve() -> None:
    g = _make_game()
    g.phase = Phase.TITLE
    g.guests.append(Guest(0, 0, PATIENCE_MAX))
    assert g.serve(0) == "empty"
    assert len(g.guests) == 1


# --------------------------------------------------------------------------- #
# main runner (works without pytest)                                           #
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
