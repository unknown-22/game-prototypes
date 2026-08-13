"""test_imports.py -- Headless logic tests for CLAY CHAIN (prototype 301).

Run standalone:  uv run python prototypes/301_clay_chain/test_imports.py
Run via pytest:  uv run pytest prototypes/301_clay_chain/test_imports.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (  # noqa: E402
    Game,
    Particle,
    FloatingText,
    Phase,
)

GAME_TIME = 3600


def make_game() -> Game:
    """Bypass __init__ (avoids pyxel.init/run); reset() assigns all state."""
    g = Game.__new__(Game)
    g.reset()
    return g


def set_active_color(g: Game, color: int) -> int:
    """Force the blob at the active (top) position to a given color."""
    idx = g._active_index()
    g.clay[idx] = color
    return idx


# -- Enum / dataclasses -------------------------------------------------------

def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert len({Phase.TITLE, Phase.PLAYING, Phase.GAME_OVER}) == 3


def test_particle_dataclass() -> None:
    p = Particle(1.5, 2.5, -0.5, 0.5, 8, 10)
    assert p.x == 1.5
    assert p.color == 8
    assert p.life == 10


def test_floating_text_dataclass() -> None:
    t = FloatingText("+10", 3.0, 4.0, 10, 30)
    assert t.text == "+10"
    assert t.color == 10
    assert t.life == 30


# -- reset / initial state ----------------------------------------------------

def test_reset_initial_state() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE
    assert len(g.clay) == Game.CLAY_COUNT == 8
    assert all(0 <= c <= 3 for c in g.clay)
    assert g.wheel_angle == 0.0
    assert g.hand_color == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.best_score == 0
    assert g.heat == 0.0
    assert g.timer == GAME_TIME
    assert g.super_timer == 0
    assert g.elapsed == 0
    assert g.shelf == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g.shake == 0
    assert g.last_color is None


def test_reset_is_deterministic() -> None:
    g1 = make_game()
    g2 = make_game()
    assert g1.clay == g2.clay


def test_clay_colors_are_valid_palette() -> None:
    assert Game.CLAY_COLORS == [8, 11, 5, 10]  # RED, LIME, DARK_BLUE, YELLOW


# -- geometry / angle math ----------------------------------------------------

def test_slot_angle_basic() -> None:
    g = make_game()
    g.wheel_angle = 0.0
    assert g._slot_angle(0) == 0.0
    assert g._slot_angle(6) == 270.0
    assert g._slot_angle(8) == 0.0  # wraps


def test_angular_distance() -> None:
    g = make_game()
    assert g._angular_distance(270.0, 270.0) == 0.0
    assert g._angular_distance(0.0, 350.0) == 10.0
    assert g._angular_distance(350.0, 0.0) == 10.0
    assert g._angular_distance(0.0, 180.0) == 180.0


def test_active_index_at_zero_rotation() -> None:
    g = make_game()
    g.wheel_angle = 0.0
    # slot 6 sits at 270 == top marker
    assert g._active_index() == 6


def test_active_index_tracks_marker() -> None:
    g = make_game()
    g.wheel_angle = 270.0  # slot 0 now at top
    assert g._active_index() == 0


# -- matching -----------------------------------------------------------------

def test_is_match_by_hand_color() -> None:
    g = make_game()
    g.hand_color = 0
    g.super_timer = 0
    assert g._is_match(0) is True
    assert g._is_match(1) is False


def test_is_match_during_super() -> None:
    g = make_game()
    g.hand_color = 0
    g.super_timer = 5
    assert g._is_match(3) is True  # any color matches in SUPER


# -- throw --------------------------------------------------------------------

def test_throw_match_increments_combo_and_score() -> None:
    g = make_game()
    g.hand_color = 0
    set_active_color(g, 0)
    result = g._throw()
    assert result is True
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 10  # 10 * 1 * 1
    assert len(g.shelf) == 1
    assert g.last_color == 0


def test_throw_combo_chain_accumulates() -> None:
    g = make_game()
    g.hand_color = 0
    total = 0
    for expected in (1, 2, 3):
        set_active_color(g, 0)
        assert g._throw() is True
        assert g.combo == expected
        total += 10 * expected
    assert g.score == total  # 10 + 20 + 30 = 60
    assert g.max_combo == 3


def test_throw_mismatch_raises_heat_and_resets_combo() -> None:
    g = make_game()
    g.hand_color = 0
    g.combo = 3
    set_active_color(g, 1)
    result = g._throw()
    assert result is False
    assert g.heat == 15.0
    assert g.combo == 0
    assert g.last_color is None


def test_super_triggers_at_combo_four() -> None:
    g = make_game()
    g.hand_color = 0
    g.combo = 3
    set_active_color(g, 0)
    assert g._throw() is True
    assert g.combo == 4
    assert g.super_timer == Game.SUPER_DURATION == 300


def test_super_throw_multiplies_score_by_three() -> None:
    g = make_game()
    g.super_timer = 10
    g.hand_color = 0
    set_active_color(g, 1)  # non-matching color, but SUPER matches anything
    assert g._throw() is True
    assert g.combo == 1
    assert g.score == 30  # 10 * 1 * 3


# -- kiln fire (future hand as cost) -----------------------------------------

def test_kiln_fire_empty_shelf_returns_false() -> None:
    g = make_game()
    g.shelf = []
    before = g.timer
    assert g._kiln_fire() is False
    assert g.timer == before


def test_kiln_fire_blocked_in_super() -> None:
    g = make_game()
    g.shelf = [0]
    g.super_timer = 5
    assert g._kiln_fire() is False
    assert g.shelf == [0]


def test_kiln_fire_banks_shelf_and_costs_time() -> None:
    g = make_game()
    g.shelf = [0, 1, 2]
    g.timer = GAME_TIME
    g.score = 0
    assert g._kiln_fire() is True
    assert g.timer == GAME_TIME - Game.KILN_COST == 3360
    assert g.score == 3 * Game.KILN_BONUS_PER_POT == 75
    assert g.shelf == []


# -- heat / timer -------------------------------------------------------------

def test_heat_decay() -> None:
    g = make_game()
    g.heat = 10.0
    g._update_heat()
    assert abs(g.heat - (10.0 - Game.HEAT_DECAY)) < 0.001


def test_heat_cap_triggers_game_over() -> None:
    g = make_game()
    g.heat = 100.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_threshold_checked_before_decay() -> None:
    g = make_game()
    g.heat = 100.0
    g._update_heat()
    assert g.heat == 100.0  # no decay happened; game over fired first
    assert g.phase == Phase.GAME_OVER


def test_super_freezes_heat() -> None:
    g = make_game()
    g.heat = 50.0
    g.super_timer = 10
    g._update_heat()
    assert g.heat == 50.0


def test_timer_reaches_zero_game_over() -> None:
    g = make_game()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


# -- advancement / interpolation ---------------------------------------------

def test_advance_wheel_rotates() -> None:
    g = make_game()
    g.wheel_angle = 0.0
    g.elapsed = 0
    g._advance_wheel()
    assert abs(g.wheel_angle - Game.WHEEL_SPEED_START) < 0.001


def test_advance_hand_color_cycles() -> None:
    g = make_game()
    g.hand_color = 0
    g.cycle_timer = 0
    g._advance_hand_color()
    assert g.hand_color == 1
    assert g.cycle_timer > 0


def test_cycle_interval_interpolates() -> None:
    g = make_game()
    g.elapsed = 0
    assert g._cycle_interval() == Game.CYCLE_INTERVAL_START
    g.elapsed = GAME_TIME
    assert g._cycle_interval() == Game.CYCLE_INTERVAL_END


def test_wheel_speed_interpolates() -> None:
    g = make_game()
    g.elapsed = 0
    assert g._wheel_speed() == Game.WHEEL_SPEED_START
    g.elapsed = GAME_TIME
    assert g._wheel_speed() == Game.WHEEL_SPEED_END


# -- particles / floating texts ----------------------------------------------

def test_update_particles_moves_and_decays() -> None:
    g = make_game()
    g.particles = [Particle(0.0, 0.0, 1.0, 0.0, 8, 2)]
    g._update_particles()
    p = g.particles[0]
    assert p.x == 1.0
    assert p.life == 1


def test_update_particles_removes_dead() -> None:
    g = make_game()
    g.particles = [Particle(0.0, 0.0, 0.0, 0.0, 8, 1)]
    g._update_particles()
    assert g.particles == []


def test_floating_text_decays_and_removes() -> None:
    g = make_game()
    g.floating_texts = [FloatingText("hi", 0.0, 0.0, 7, 1)]
    g._update_floating_texts()
    assert g.floating_texts == []


def test_spawn_burst_adds_particles() -> None:
    g = make_game()
    g._spawn_burst(100.0, 100.0, 8, 6)
    assert len(g.particles) == 6
    assert all(p.color == 8 for p in g.particles)


def test_spawn_text_adds_floating_text() -> None:
    g = make_game()
    g._spawn_text(100.0, 100.0, "SUPER!", 10)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "SUPER!"


if __name__ == "__main__":
    fns = [
        (name, obj)
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {exc!r}")
    print(f"\n{len(fns) - failed}/{len(fns)} tests passed")
    sys.exit(1 if failed else 0)
