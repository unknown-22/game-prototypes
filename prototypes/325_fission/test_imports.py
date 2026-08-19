"""test_imports.py — Headless logic tests for FISSION (325_fission).

Uses the Game.__new__(Game) bypass pattern: pyxel is imported at module top but
never initialized, and every method under test avoids pyxel Rust calls.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    CHARGE_MAX,
    CHARGE_MIN,
    EDGE_MARGIN,
    EDGE_MULT,
    LIVES,
    MAX_ENERGY,
    MAX_T_BASE,
    MIN_T,
    SENSOR_MIN,
    SENSOR_START,
    TIMER_MAX,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g._sfx_enabled = False
    g.best_score = 0
    g.reset()
    return g


def force_roll(g: Game, roll: int) -> None:
    real = g.rng.randint

    def fake(a: int, b: int) -> int:
        if (a, b) == (CHARGE_MIN, CHARGE_MAX):
            return roll
        return real(a, b)

    g.rng.randint = fake  # type: ignore


# ── Imports & constants ──


def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_constants():
    assert MIN_T == 12
    assert MAX_T_BASE == 22
    assert MAX_ENERGY == 36
    assert CHARGE_MIN == 1 and CHARGE_MAX == 6
    assert SENSOR_START == 6 and SENSOR_MIN == 2
    assert EDGE_MARGIN == 2 and EDGE_MULT == 2
    assert LIVES == 3 and TIMER_MAX == 3600


# ── reset / initial state ──


def test_reset_initial_state():
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.frame == 0
    assert g.energy == 0
    assert g.score == 0
    assert g.lives == LIVES
    assert g.sensor_window == SENSOR_START
    assert g.last_roll == 0
    assert g.close_calls == 0
    assert g.total_banks == 0
    assert MIN_T <= g.threshold <= MAX_T_BASE
    assert g.particles == []
    assert g.floats == []


def test_reset_preserves_seeded_rng():
    g = make_game(seed=7)
    g2 = make_game(seed=7)
    assert g.threshold == g2.threshold


# ── threshold escalation ──


def test_max_t_escalates_with_frame():
    g = make_game()
    g.frame = 0
    assert g._max_t() == MAX_T_BASE
    g.frame = 600
    assert g._max_t() == MAX_T_BASE + 1


# ── bank value (pure) ──


def test_bank_value_normal():
    assert Game._bank_value(10, 30) == 10


def test_bank_value_edge_bonus():
    assert Game._bank_value(28, 30) == 28 * EDGE_MULT


def test_bank_value_exact_edge_margin():
    assert Game._bank_value(28, 30) == 28 * EDGE_MULT


# ── sensor band / danger ──


def test_sensor_band():
    g = make_game()
    g.threshold = 20
    g.sensor_window = 6
    assert g.sensor_band() == (14, 26)


def test_in_danger():
    g = make_game()
    g.threshold = 20
    g.sensor_window = 6
    g.energy = 13
    assert not g.in_danger()
    g.energy = 14
    assert g.in_danger()


# ── charge ──


def test_charge_adds_energy():
    g = make_game()
    g.threshold = 50  # safely above any roll
    force_roll(g, 4)
    assert g.charge() == "charged"
    assert g.energy == 4
    assert g.last_roll == 4
    assert g.sensor_window == SENSOR_START - 1


def test_charge_narrows_sensor_to_min():
    g = make_game()
    g.threshold = 50
    g.sensor_window = SENSOR_MIN
    force_roll(g, 2)
    g.charge()
    assert g.sensor_window == SENSOR_MIN


def test_charge_meltdown_loses_energy_and_life():
    g = make_game()
    g.threshold = 3
    force_roll(g, 4)
    assert g.charge() == "meltdown"
    assert g.lives == LIVES - 1
    assert g.energy == 0
    assert g.score == 0


def test_charge_exactly_threshold_is_safe():
    g = make_game()
    g.threshold = 4
    force_roll(g, 4)
    assert g.charge() == "charged"
    assert g.energy == 4


def test_meltdown_game_over_at_zero_lives():
    g = make_game()
    g.lives = 1
    g.threshold = 1
    force_roll(g, 2)
    g.charge()
    assert g.phase == Phase.GAME_OVER
    assert g._game_over_reason == "MELTDOWN"


# ── bank ──


def test_bank_empty_is_noop():
    g = make_game()
    assert g.bank() == "empty"
    assert g.score == 0


def test_bank_scores_energy():
    g = make_game()
    g.energy = 10
    g.threshold = 30
    assert g.bank() == "banked"
    assert g.score == 10
    assert g.last_bank == 10
    assert g.total_banks == 1
    assert g.close_calls == 0
    assert g.energy == 0


def test_bank_close_call_doubles():
    g = make_game()
    g.threshold = 30
    g.energy = 28  # >= 30 - EDGE_MARGIN(2)
    assert g.bank() == "banked"
    assert g.score == 28 * EDGE_MULT
    assert g.close_calls == 1


def test_bank_spawns_new_reactor():
    g = make_game()
    g.energy = 5
    g.threshold = 30
    g.sensor_window = SENSOR_MIN
    g.bank()
    assert g.energy == 0
    assert g.sensor_window == SENSOR_START


# ── game over ──


def test_game_over_time_up():
    g = make_game()
    g.score = 50
    g._game_over("TIME UP")
    assert g.phase == Phase.GAME_OVER
    assert g._game_over_reason == "TIME UP"


def test_game_over_updates_best_score():
    g = make_game()
    g.score = 50
    g.best_score = 40
    g._game_over("MELTDOWN")
    assert g.best_score == 50
    g.best_score = 40
    g.score = 30
    g._game_over("TIME UP")
    assert g.best_score == 40


# ── particles / floating text ──


def test_burst_adds_particles():
    g = make_game()
    g._burst(160, 80, 11, 12, 3.0, 12, 24)
    assert len(g.particles) == 12
    assert all(isinstance(p, Particle) for p in g.particles)


def test_spawn_float():
    g = make_game()
    g._spawn_float(160, 80, "+10", 11)
    assert isinstance(g.floats[-1], FloatingText)
    assert g.floats[-1].text == "+10"


def test_update_particles_removes_dead():
    g = make_game()
    g._spawn_particle(160, 80, 11, 1.0, 1, 1)
    g._update_particles()
    assert g.particles == []


# ── button bounds ──


def test_charge_button_bounds():
    g = make_game()
    assert g._button_charge_contains(30, 210)
    assert not g._button_charge_contains(30, 10)


def test_bank_button_bounds():
    g = make_game()
    assert g._button_bank_contains(200, 210)
    assert not g._button_bank_contains(30, 210)


if __name__ == "__main__":
    tests = [
        (k, v)
        for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS {name}")
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    if passed != len(tests):
        sys.exit(1)
