"""test_imports.py — Headless logic tests for 315_glow_chain (GLOW CHAIN).

Runs without a display: imports game classes and exercises pure-logic methods.
Never calls update()/draw() or any method touching pyxel.btn/btnp/mouse_*/frame_count.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    BAND_COLORS,
    DARK_BLUE,
    GREEN,
    YELLOW,
    RED,
    WHITE,
    HEAT_MISMATCH,
    HEAT_OVERHEAT,
    HEAT_FREEZE,
    SUPER_DURATION,
    SUPER_THRESHOLD,
    SCORE_BASE,
    SUPER_MULT,
    Phase,
    Particle,
    FloatingText,
    Game,
)


def make_game() -> Game:
    """Bypass __init__ (which calls pyxel.init/pyxel.run) and return a fresh game."""
    g = Game.__new__(Game)
    g.best_score = 0  # reset() does NOT touch best_score; ensure it exists
    g.reset()
    return g


def test_band_index_boundaries() -> None:
    assert Game.band_index(0.0) == 0
    assert Game.band_index(24.9) == 0
    assert Game.band_index(25.0) == 1
    assert Game.band_index(49.9) == 1
    assert Game.band_index(50.0) == 2
    assert Game.band_index(74.9) == 2
    assert Game.band_index(75.0) == 3
    assert Game.band_index(100.0) == 3


def test_band_color_mapping() -> None:
    assert Game.band_color(0.0) == DARK_BLUE
    assert Game.band_color(30.0) == GREEN
    assert Game.band_color(60.0) == YELLOW
    assert Game.band_color(90.0) == RED


def test_reset_initial_state() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.frame == 0
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.reheating is False
    assert g.vessels_made == 0
    assert g.particles == []
    assert g.floats == []
    assert g.shake_frames == 0
    assert g.game_over_reason == ""
    assert 15.0 <= g.temp <= 35.0
    assert g.order_color in BAND_COLORS


def test_blow_success_increments_combo_and_scores() -> None:
    g = make_game()
    g.temp = 30.0  # GREEN band
    g.order_color = GREEN
    assert g._blow() is True
    assert g.combo == 1
    assert g.score == SCORE_BASE * 1 * 1  # 10 — combo increments FIRST
    assert g.max_combo == 1
    assert g.vessels_made == 1
    assert g.heat == 0.0
    assert 15.0 <= g.temp <= 35.0  # temp reset to a fresh gather


def test_blow_combo_sequence_scores_accumulate() -> None:
    g = make_game()
    for _ in range(3):
        g.temp = 30.0
        g.order_color = GREEN
        g._blow()
    assert g.combo == 3
    # 10*1 + 10*2 + 10*3 = 60
    assert g.score == 60
    assert g.max_combo == 3


def test_blow_mismatch_penalizes_and_resets_combo() -> None:
    g = make_game()
    g.temp = 30.0  # GREEN
    g.order_color = RED  # mismatch
    kept_order = g.order_color
    assert g._blow() is False
    assert g.heat == HEAT_MISMATCH
    assert g.combo == 0
    assert g.order_color == kept_order  # order stays on mismatch
    assert 15.0 <= g.temp <= 35.0


def test_super_activates_at_combo_threshold() -> None:
    g = make_game()
    for _ in range(SUPER_THRESHOLD):
        g.temp = 30.0
        g.order_color = GREEN
        g._blow()
    assert g.combo == SUPER_THRESHOLD
    assert g.super_timer == SUPER_DURATION


def test_super_blow_three_times_score() -> None:
    g = make_game()
    g.super_timer = 100  # activate super manually
    g.combo = 5
    g.temp = 0.0  # COLD (DARK_BLUE)
    g.order_color = RED  # would mismatch, but super matches any color
    before = g.score
    assert g._blow() is True
    assert g.combo == 6
    assert g.score - before == SCORE_BASE * 6 * SUPER_MULT  # 10 * 6 * 3


def test_update_temp_reheat_increases() -> None:
    g = make_game()
    g.temp = 50.0
    g._update_temp(True)
    assert abs(g.temp - 50.8) < 0.001


def test_update_temp_reheat_clamps_at_max() -> None:
    g = make_game()
    g.temp = 99.5
    g._update_temp(True)
    assert g.temp == 100.0  # clamped, not yet overheat (check is >= 100 BEFORE adding)


def test_update_temp_overheat_penalty() -> None:
    g = make_game()
    g.temp = 100.0
    g.combo = 3
    g._update_temp(True)
    assert g.heat == HEAT_OVERHEAT
    assert g.combo == 0
    assert 15.0 <= g.temp <= 35.0
    assert any(f.text == "SAG!" for f in g.floats)


def test_update_temp_cooling_decreases() -> None:
    g = make_game()
    g.temp = 50.0
    g.frame = 0
    rate = g._cool_rate()
    g._update_temp(False)
    assert abs(g.temp - (50.0 - rate)) < 0.001


def test_update_temp_freeze_penalty() -> None:
    g = make_game()
    g.temp = 0.2
    g.frame = 0  # cool rate 0.25
    g.combo = 2
    g._update_temp(False)
    assert g.heat == HEAT_FREEZE
    assert g.combo == 0
    assert 15.0 <= g.temp <= 35.0
    assert any(f.text == "CRACK!" for f in g.floats)


def test_update_heat_decays() -> None:
    g = make_game()
    g.heat = 50.0
    g.super_timer = 0
    g._update_heat()
    assert abs(g.heat - (50.0 - 0.02)) < 0.001


def test_update_heat_frozen_in_super() -> None:
    g = make_game()
    g.heat = 50.0
    g.super_timer = 10
    g._update_heat()
    assert g.heat == 50.0


def test_update_heat_game_over_at_cap() -> None:
    g = make_game()
    g.heat = 100.0
    g.score = 500
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "MELTDOWN"
    assert g.best_score == 500


def test_cool_rate_escalates() -> None:
    g = make_game()
    g.frame = 0
    c0 = g._cool_rate()
    g.frame = 3600
    c1 = g._cool_rate()
    assert abs(c0 - 0.25) < 0.001
    assert abs(c1 - 0.55) < 0.001
    assert c1 > c0


def test_update_super_decrements() -> None:
    g = make_game()
    g.super_timer = 5
    g._update_super()
    assert g.super_timer == 4
    g.super_timer = 0
    g._update_super()
    assert g.super_timer == 0  # never negative


def test_particles_move_and_expire() -> None:
    g = make_game()
    g.particles = [Particle(0.0, 0.0, 1.0, 0.0, 2, RED, 1)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 1
    assert abs(g.particles[0].x - 1.0) < 0.001
    assert abs(g.particles[0].vy - 0.05) < 0.001  # gravity applied
    g._update_particles()
    assert g.particles == []  # life reached 0


def test_floats_rise_and_expire() -> None:
    g = make_game()
    g.floats = [FloatingText(100.0, 100.0, "HI", 2, WHITE)]
    g._update_floats()
    assert len(g.floats) == 1
    assert g.floats[0].life == 1
    assert abs(g.floats[0].y - 99.5) < 0.001
    g._update_floats()
    assert g.floats == []


def test_spawn_burst_adds_particles() -> None:
    g = make_game()
    g._spawn_burst(160.0, 150.0, RED, 12)
    assert len(g.particles) == 12
    for p in g.particles:
        assert p.color == RED
        assert 20 <= p.life <= 45


def test_spawn_rainbow_burst_adds_particles() -> None:
    g = make_game()
    g._spawn_rainbow_burst(160.0, 150.0, 24)
    assert len(g.particles) == 24


def test_advance_order_picks_valid_color() -> None:
    g = make_game()
    g.order_color = RED
    g._advance_order()
    assert g.order_color in BAND_COLORS


def test_game_over_sets_best_score_max() -> None:
    g = make_game()
    g.score = 300
    g.best_score = 100
    g._game_over("TIME UP")
    assert g.best_score == 300
    assert g.phase == Phase.GAME_OVER


def test_reset_preserves_best_score() -> None:
    g = make_game()
    g.best_score = 777
    g.score = 123
    g.reset()
    assert g.best_score == 777  # reset must NOT overwrite best_score
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0


def test_blow_resets_temp_every_success() -> None:
    g = make_game()
    temps = set()
    for _ in range(5):
        g.temp = 30.0
        g.order_color = GREEN
        g._blow()
        temps.add(round(g.temp, 2))
    assert g.vessels_made == 5
    assert all(15.0 <= t <= 35.0 for t in temps)


if __name__ == "__main__":
    # Run all tests; report a compact summary.
    import traceback

    tests = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS {name}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"  FAIL {name}")
            traceback.print_exc()
    total = passed + failed
    print(f"\n{passed}/{total} tests passed")
    if failed:
        sys.exit(1)
