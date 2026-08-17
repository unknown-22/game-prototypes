"""test_imports.py — Headless logic tests for WINE CHAIN (316_wine_chain).

Runs without a display: imports Game via `from main import ...` and tests pure
logic methods directly. Never touches pyxel input accessors.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    BASE_SCORE,
    BOTTLE_COOLDOWN,
    COLORS,
    GAME_DURATION,
    GRAPE_XS,
    GRAPE_Y,
    HEAT_DECAY,
    HEAT_MAX,
    MISMATCH_HEAT,
    NUM_GRAPES,
    OVERFLOW_HEAT,
    SUPER_DURATION,
    SUPER_THRESHOLD,
    TANK_MAX,
    FloatText,
    Game,
    Grape,
    Particle,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    """Bypass __init__ (and pyxel.init/run) via Game.__new__, seed the RNG."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.best_score = 0
    g._init_state()
    g.phase = Phase.PLAYING
    return g


def test_constants() -> None:
    assert len(COLORS) == 4
    assert TANK_MAX == 6
    assert SUPER_THRESHOLD == 4
    assert HEAT_MAX == 100
    assert BASE_SCORE == 10
    assert NUM_GRAPES == 8
    assert len(GRAPE_XS) == 8
    assert BOTTLE_COOLDOWN == 45
    assert SUPER_DURATION == 300


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.TITLE.value == 0


def test_dataclasses() -> None:
    g = Grape(color=8, x=10, y=20)
    assert g.color == 8 and g.alive and g.respawn_timer == 0
    p = Particle(0.0, 0.0, 1.0, -1.0, 10, 8)
    assert p.vx == 1.0 and p.vy == -1.0 and p.life == 10
    t = FloatText(1.0, 2.0, "hi", 5, 7)
    assert t.text == "hi" and t.life == 5


def test_init_state_defaults() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING  # factory overrides after init
    assert g.score == 0 and g.combo == 0 and g.juice == 0
    assert g.heat == 0.0
    assert g.crusher_color == COLORS[0] and g.crusher_index == 0
    assert g.super_mode is False and g.super_timer == 0
    assert g.bottle_cooldown == 0
    assert g.frame == 0
    assert len(g.grapes) == NUM_GRAPES
    assert all(gr.alive for gr in g.grapes)


def test_best_score_persists_across_reset() -> None:
    g = _make_game()
    g.best_score = 999
    g._init_state()
    assert g.best_score == 999


def test_handle_crush_match_basic() -> None:
    g = _make_game()
    g.crusher_color = 8
    g.grapes[0].color = 8
    g.grapes[0].alive = True
    result = g._handle_crush(0)
    assert result == "match"
    assert g.combo == 1
    assert g.juice == 1
    assert g.score == BASE_SCORE * 1 * 1  # first crush = 10
    assert not g.grapes[0].alive
    assert g.grapes[0].respawn_timer == g._respawn_delay()


def test_handle_crush_combo_and_score_scale() -> None:
    g = _make_game()
    g.crusher_color = 8
    for i in range(3):
        g.grapes[i].color = 8
        g.grapes[i].alive = True
        assert g._handle_crush(i) == "match"
    assert g.combo == 3
    assert g.max_combo == 3
    assert g.juice == 3
    # score = 10*1 + 10*2 + 10*3 = 60
    assert g.score == 10 * (1 + 2 + 3)


def test_handle_crush_mismatch() -> None:
    g = _make_game()
    g.crusher_color = 8
    g.grapes[0].color = 11  # LIME
    g.grapes[0].alive = True
    result = g._handle_crush(0)
    assert result == "mismatch"
    assert g.heat == MISMATCH_HEAT
    assert g.combo == 0
    assert g.juice == 0  # juice not affected
    assert g.grapes[0].alive  # grape stays


def test_handle_crush_mismatch_resets_combo_keeps_juice() -> None:
    g = _make_game()
    g.crusher_color = 8
    g.grapes[0].color = 8
    g.grapes[0].alive = True
    g._handle_crush(0)  # match -> combo 1, juice 1
    g.grapes[1].color = 11  # mismatch
    g.grapes[1].alive = True
    assert g._handle_crush(1) == "mismatch"
    assert g.combo == 0
    assert g.max_combo == 1
    assert g.juice == 1  # juice preserved


def test_handle_crush_overflow() -> None:
    g = _make_game()
    g.crusher_color = 8
    g.juice = TANK_MAX
    g.combo = 5
    g.grapes[0].color = 8
    g.grapes[0].alive = True
    result = g._handle_crush(0)
    assert result == "overflow"
    assert g.heat == OVERFLOW_HEAT
    assert g.combo == 0
    assert g.juice == TANK_MAX  # juice unchanged (spilled value)
    assert not g.grapes[0].alive  # grape wasted


def test_handle_crush_blocked_when_not_playing() -> None:
    g = _make_game()
    g.phase = Phase.TITLE
    assert g._handle_crush(0) == "blocked"
    assert g.combo == 0 and g.juice == 0


def test_handle_crush_blocked_during_cooldown() -> None:
    g = _make_game()
    g.bottle_cooldown = 10
    assert g._handle_crush(0) == "blocked"


def test_handle_crush_blocked_dead_grape() -> None:
    g = _make_game()
    g.grapes[0].alive = False
    assert g._handle_crush(0) == "blocked"


def test_handle_crush_blocked_bad_index() -> None:
    g = _make_game()
    assert g._handle_crush(-1) == "blocked"
    assert g._handle_crush(NUM_GRAPES) == "blocked"


def test_bottle_basic() -> None:
    g = _make_game()
    g.juice = 3
    g.combo = 4
    gained = g._bottle()
    assert gained == 3 * 4 * BASE_SCORE  # 120
    assert g.score == 120
    assert g.juice == 0
    assert g.combo == 0
    assert g.bottle_cooldown == BOTTLE_COOLDOWN


def test_bottle_empty_tank_gives_zero() -> None:
    g = _make_game()
    g.juice = 0
    g.combo = 5
    gained = g._bottle()
    assert gained == 0
    assert g.score == 0
    assert g.bottle_cooldown == BOTTLE_COOLDOWN


def test_bottle_blocked_during_cooldown() -> None:
    g = _make_game()
    g.juice = 3
    g.combo = 4
    g.bottle_cooldown = 5
    assert g._bottle() == 0
    assert g.juice == 3 and g.combo == 4


def test_bottle_blocked_when_not_playing() -> None:
    g = _make_game()
    g.phase = Phase.TITLE
    g.juice = 3
    g.combo = 4
    assert g._bottle() == 0


def test_super_activation_on_fourth_match() -> None:
    g = _make_game()
    g.crusher_color = 8
    for i in range(3):
        g.grapes[i].color = 8
        g.grapes[i].alive = True
        assert g._handle_crush(i) == "match"
    assert g.combo == 3
    assert g.super_mode is False
    g.grapes[3].color = 8
    g.grapes[3].alive = True
    assert g._handle_crush(3) == "match"
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION
    assert g.combo >= SUPER_THRESHOLD


def test_activate_super_direct() -> None:
    g = _make_game()
    g._activate_super()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_bloom_crushes_two_grapes() -> None:
    g = _make_game()
    g.juice = 0
    g.combo = 1
    before = sum(1 for gr in g.grapes if gr.alive)
    g._super_bloom()
    after = sum(1 for gr in g.grapes if gr.alive)
    assert before - after == 2
    assert g.combo == 3  # 1 + 2
    assert g.juice == 2
    # score = 10*2*3 + 10*3*3 = 60 + 90 = 150
    assert g.score == 150


def test_super_bloom_stops_at_tank_max() -> None:
    g = _make_game()
    g.juice = TANK_MAX - 1
    g.combo = 0
    g._super_bloom()
    assert g.juice == TANK_MAX
    assert g.combo == 1


def test_super_mode_makes_any_color_match() -> None:
    g = _make_game()
    g.super_mode = True
    g.crusher_color = 8
    g.grapes[0].color = 11  # would mismatch normally
    g.grapes[0].alive = True
    result = g._handle_crush(0)
    assert result == "match"
    assert g.combo == 1
    assert g.score == BASE_SCORE * 1 * 3  # 3x in super


def test_update_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert abs(g.heat - (50.0 - HEAT_DECAY)) < 1e-9


def test_update_heat_game_over_at_threshold() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.heat == HEAT_MAX  # not decayed (check first, return)


def test_update_heat_frozen_in_super() -> None:
    g = _make_game()
    g.super_mode = True
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0


def test_check_game_over_sets_best_score() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    g.score = 500
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500


def test_update_timer_increments_frame() -> None:
    g = _make_game()
    g._update_timer()
    assert g.frame == 1
    assert g.phase == Phase.PLAYING


def test_update_timer_game_over_at_duration() -> None:
    g = _make_game()
    g.frame = GAME_DURATION - 1
    g._update_timer()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == max(g.best_score, g.score)


def test_cycle_interval_escalation() -> None:
    g = _make_game()
    g.frame = 0
    assert g._cycle_interval() == 20
    g.frame = GAME_DURATION
    assert g._cycle_interval() == 12


def test_respawn_delay_escalation() -> None:
    g = _make_game()
    g.frame = 0
    assert g._respawn_delay() == 60
    g.frame = GAME_DURATION
    assert g._respawn_delay() == 25


def test_update_cycle_advances_color() -> None:
    g = _make_game()
    g.crusher_index = 0
    g.crusher_color = COLORS[0]
    g.cycle_timer = 1
    g._update_cycle()
    assert g.crusher_index == 1
    assert g.crusher_color == COLORS[1]
    assert g.cycle_timer == g._cycle_interval()


def test_update_cycle_no_advance_when_timer_positive() -> None:
    g = _make_game()
    g.crusher_index = 0
    g.cycle_timer = 5
    g._update_cycle()
    assert g.crusher_index == 0
    assert g.cycle_timer == 4


def test_update_grapes_respawn() -> None:
    g = _make_game()
    g.grapes[0].alive = False
    g.grapes[0].respawn_timer = 1
    g._update_grapes()
    assert g.grapes[0].alive is True
    assert g.grapes[0].respawn_timer == 0


def test_update_grapes_no_respawn_early() -> None:
    g = _make_game()
    g.grapes[0].alive = False
    g.grapes[0].respawn_timer = 2
    g._update_grapes()
    assert g.grapes[0].alive is False
    assert g.grapes[0].respawn_timer == 1


def test_kill_and_spawn_grape() -> None:
    g = _make_game()
    g._kill_grape(0)
    assert not g.grapes[0].alive
    assert g.grapes[0].respawn_timer == g._respawn_delay()
    g._spawn_grape(0)
    assert g.grapes[0].alive
    assert g.grapes[0].respawn_timer == 0
    assert g.grapes[0].color in COLORS


def test_update_super_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_mode is False


def test_update_super_stays_active() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 5
    g._update_super()
    assert g.super_mode is True
    assert g.super_timer == 4


def test_update_bottle_cooldown_decrements() -> None:
    g = _make_game()
    g.bottle_cooldown = 3
    g._update_bottle_cooldown()
    assert g.bottle_cooldown == 2
    g.bottle_cooldown = 0
    g._update_bottle_cooldown()
    assert g.bottle_cooldown == 0


def test_grape_at_hit() -> None:
    g = _make_game()
    assert g._grape_at(GRAPE_XS[0], GRAPE_Y) == 0
    assert g._grape_at(GRAPE_XS[3] + 4, GRAPE_Y + 4) == 3


def test_grape_at_miss() -> None:
    g = _make_game()
    assert g._grape_at(5, 5) is None
    assert g._grape_at(78, GRAPE_Y) is None  # midpoint between x=60 and x=96
    assert g._grape_at(160, 200) is None  # below the row, away from tank


def test_four_matches_then_super_fills_tank() -> None:
    """Realistic greed path: 4 matches triggers SUPER, whose bloom auto-crushes
    2 more grapes, filling the tank to max — then BOTTLE banks 6*6*10."""
    g = _make_game()
    g.crusher_color = 8
    for i in range(4):
        g.grapes[i].color = 8
        g.grapes[i].alive = True
        assert g._handle_crush(i) == "match"
    assert g.super_mode is True
    assert g.juice == TANK_MAX  # 4 matches + 2 bloom = 6
    assert g.combo == 6
    gained = g._bottle()
    assert gained == 6 * 6 * BASE_SCORE  # 360
    assert g.juice == 0 and g.combo == 0


def _run_all() -> None:
    tests = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ok  {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} tests passed")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _run_all()
