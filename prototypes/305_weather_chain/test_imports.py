"""test_imports.py — Headless logic tests for 305_weather_chain (WEATHER CHAIN).

Tests the game logic without touching Pyxel input/state. Uses the
Game.__new__ bypass pattern (never calls pyxel.init/run/btn/btnp).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    Game,
    WeatherFront,
    Particle,
    FloatingText,
    Phase,
    WEATHER_NAMES,
    WEATHER_COLORS,
    LINE_X,
)


class _FixedRandom(random.Random):
    """Deterministic rng whose random() always returns a fixed value."""

    def __init__(self, value: float) -> None:
        super().__init__(0)
        self._value = value

    def random(self) -> float:
        return self._value


def _make_game(seed: int = 42) -> Game:
    """Factory: Game.__new__ bypass + reset() + seeded rng + PLAYING phase."""
    g = Game.__new__(Game)
    g.reset()
    g._rng = random.Random(seed)
    g.phase = Phase.PLAYING
    return g


# ── Config / dataclass definition tests ─────────────────────────────


def test_weather_names() -> None:
    assert WEATHER_NAMES == ("SUN", "RAIN", "SNOW", "THUNDER")
    assert len(WEATHER_NAMES) == 4


def test_weather_colors() -> None:
    assert WEATHER_COLORS == (10, 6, 7, 2)
    assert len(WEATHER_COLORS) == 4
    # all colors are valid Pyxel palette indices 0..15
    assert all(0 <= c <= 15 for c in WEATHER_COLORS)


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_weatherfront_dataclass() -> None:
    f = WeatherFront(x=320.0, y=100, color=2, speed=1.5)
    assert f.x == 320.0
    assert f.y == 100
    assert f.color == 2
    assert f.speed == 1.5
    assert f.shift_timer == 120
    assert f.flash_timer == 0


def test_particle_dataclass() -> None:
    p = Particle(x=1.0, y=2.0, vx=0.5, vy=-0.5, life=10, color=10)
    assert p.life == 10
    assert p.color == 10


def test_floatingtext_dataclass() -> None:
    ft = FloatingText(x=50, y=60, text="+10", life=30, color=7)
    assert ft.text == "+10"
    assert ft.life == 30


# ── reset() / initial state tests ───────────────────────────────────


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == 3600
    assert g.super_timer == 0
    assert g.forecast_color == 0
    assert g.fronts == []
    assert g.particles == []
    assert g.floats == []
    assert g.cycle_interval == 20
    assert g.spawn_interval == 90
    assert g.phase == Phase.PLAYING  # set by factory


def test_reset_preserves_seeded_rng() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(7)
    g.reset()
    assert g._rng is not None
    # _rng not overwritten because hasattr check passed
    assert g._rng.randint(1, 1) == 1


# ── forecast color cycling ──────────────────────────────────────────


def test_update_cycle_advances_color() -> None:
    g = _make_game()
    g.forecast_color = 0
    g.cycle_timer = 1
    g._update_cycle()
    assert g.forecast_color == 1
    assert g.cycle_timer == g.cycle_interval


def test_update_cycle_wraps_around() -> None:
    g = _make_game()
    g.forecast_color = 3
    g.cycle_timer = 1
    g._update_cycle()
    assert g.forecast_color == 0


def test_update_cycle_no_change_before_interval() -> None:
    g = _make_game()
    g.forecast_color = 0
    g.cycle_timer = 5
    g._update_cycle()
    assert g.forecast_color == 0
    assert g.cycle_timer == 4


# ── spawning ────────────────────────────────────────────────────────


def test_spawn_front_adds_at_right_edge() -> None:
    g = _make_game()
    g._spawn_front()
    assert len(g.fronts) == 1
    assert g.fronts[0].x == 320.0
    assert 24 <= g.fronts[0].y <= 216
    assert g.fronts[0].color in range(4)


def test_spawn_front_respects_max() -> None:
    g = _make_game()
    for _ in range(20):
        g._spawn_front()
    assert len(g.fronts) == 14


def test_spawn_front_speed_scales_with_elapsed() -> None:
    g = _make_game()
    g.timer = 3600  # elapsed = 0
    g._spawn_front()
    slow = g.fronts[0].speed
    assert abs(slow - 1.0) < 0.001

    g.fronts.clear()
    g.timer = 0  # elapsed = 3600
    g._spawn_front()
    fast = g.fronts[0].speed
    assert abs(fast - 2.5) < 0.001


# ── front movement & miss handling ──────────────────────────────────


def test_update_fronts_moves_left() -> None:
    g = _make_game()
    g.spawn_timer = 9999
    f = WeatherFront(x=200.0, y=100, color=0, speed=1.5)
    g.fronts = [f]
    g._update_fronts()
    assert abs(g.fronts[0].x - 198.5) < 0.001


def test_update_fronts_miss_adds_heat_and_resets_combo() -> None:
    g = _make_game()
    g.spawn_timer = 9999
    g.combo = 5
    g.heat = 10.0
    g.fronts = [WeatherFront(x=-30.0, y=100, color=0, speed=1.0)]
    g._update_fronts()
    assert len(g.fronts) == 0
    assert abs(g.heat - 15.0) < 0.001  # +5
    assert g.combo == 0


def test_update_fronts_spawns_periodically() -> None:
    g = _make_game()
    g.spawn_timer = 1
    g._update_fronts()
    assert len(g.fronts) == 1
    assert g.spawn_timer == g.spawn_interval


# ── weather shift twist ─────────────────────────────────────────────


def test_shift_changes_color_when_rng_low() -> None:
    g = _make_game()
    g.spawn_timer = 9999
    f = WeatherFront(x=100.0, y=100, color=0, speed=1.0, shift_timer=0, flash_timer=1)
    g.fronts = [f]
    old = f.color
    g._rng = _FixedRandom(0.1)  # random() < 0.3 → shift happens
    g._update_fronts()
    assert f.color != old
    assert f.color in range(4)
    assert f.shift_timer == 120


def test_shift_no_change_when_rng_high() -> None:
    g = _make_game()
    g.spawn_timer = 9999
    f = WeatherFront(x=100.0, y=100, color=0, speed=1.0, shift_timer=0, flash_timer=1)
    g.fronts = [f]
    old = f.color
    g._rng = _FixedRandom(0.9)  # random() >= 0.3 → no shift
    g._update_fronts()
    assert f.color == old
    assert f.shift_timer == 120


def test_shift_flash_phase_first() -> None:
    g = _make_game()
    g.spawn_timer = 9999
    f = WeatherFront(x=100.0, y=100, color=0, speed=1.0, shift_timer=0, flash_timer=0)
    g.fronts = [f]
    g._update_fronts()
    # first frame only sets flash_timer, no color change
    assert f.flash_timer == 15
    assert f.color == 0


# ── forecast resolution ─────────────────────────────────────────────


def test_forecast_correct_match() -> None:
    g = _make_game()
    g.forecast_color = 0
    g.fronts = [WeatherFront(x=50.0, y=100, color=0, speed=1.0)]
    g._forecast_armed()
    assert g.combo == 1
    assert g.score == 10  # 10 * 1 * 1
    assert g.max_combo == 1
    assert len(g.fronts) == 0


def test_forecast_wrong_match() -> None:
    g = _make_game()
    g.forecast_color = 0
    g.fronts = [WeatherFront(x=50.0, y=100, color=1, speed=1.0)]
    g._forecast_armed()
    assert g.heat == 15.0
    assert g.combo == 0
    assert g.score == 0
    assert len(g.fronts) == 0


def test_forecast_no_armed_front_is_noop() -> None:
    g = _make_game()
    g.forecast_color = 0
    g.fronts = [WeatherFront(x=200.0, y=100, color=0, speed=1.0)]  # x > LINE_X
    g._forecast_armed()
    assert g.combo == 0
    assert len(g.fronts) == 1


def test_forecast_selects_smallest_x() -> None:
    g = _make_game()
    g.forecast_color = 1
    g.fronts = [
        WeatherFront(x=50.0, y=100, color=0, speed=1.0),
        WeatherFront(x=30.0, y=120, color=1, speed=1.0),
    ]
    g._forecast_armed()
    # armed = x=30 (color 1 == forecast) → correct
    assert g.combo == 1
    assert len(g.fronts) == 1
    assert g.fronts[0].x == 50.0


def test_forecast_combo_scoring_accumulates() -> None:
    g = _make_game()
    g.forecast_color = 0
    for _ in range(3):
        g.fronts = [WeatherFront(x=50.0, y=100, color=0, speed=1.0)]
        g._forecast_armed()
    # scores: 10*1 + 10*2 + 10*3 = 60
    assert g.combo == 3
    assert g.score == 60
    assert g.max_combo == 3


def test_super_forecast_triggers_at_combo_4() -> None:
    g = _make_game()
    g.forecast_color = 0
    g.combo = 3
    g.max_combo = 3
    g.fronts = [WeatherFront(x=50.0, y=100, color=0, speed=1.0)]
    g._forecast_armed()
    assert g.combo == 4
    assert g.super_timer == 300


def test_super_mode_any_color_matches_3x() -> None:
    g = _make_game()
    g.super_timer = 300
    g.forecast_color = 0
    g.combo = 1
    g.fronts = [WeatherFront(x=50.0, y=100, color=2, speed=1.0)]  # mismatch
    g._forecast_armed()
    assert g.combo == 2
    assert g.score == 60  # 10 * 2 * 3
    assert len(g.fronts) == 0


# ── heat / timer / difficulty ───────────────────────────────────────


def test_update_heat_game_over_before_decay() -> None:
    g = _make_game()
    g.heat = 100.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_update_heat_decays_when_not_super() -> None:
    g = _make_game()
    g.heat = 50.0
    g.super_timer = 0
    g._update_heat()
    assert abs(g.heat - 49.98) < 0.001


def test_update_heat_frozen_in_super() -> None:
    g = _make_game()
    g.heat = 50.0
    g.super_timer = 100
    g._update_heat()
    assert g.heat == 50.0


def test_update_heat_floor_zero() -> None:
    g = _make_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


def test_update_timer_decrements() -> None:
    g = _make_game()
    g.timer = 100
    g._update_timer()
    assert g.timer == 99


def test_update_timer_game_over_at_zero() -> None:
    g = _make_game()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


def test_update_difficulty_early() -> None:
    g = _make_game()
    g.timer = 3600  # elapsed 0
    g._update_difficulty()
    assert g.cycle_interval == 20
    assert g.spawn_interval == 90


def test_update_difficulty_late() -> None:
    g = _make_game()
    g.timer = 0  # elapsed 3600
    g._update_difficulty()
    assert g.cycle_interval == 12
    assert g.spawn_interval == 30


def test_check_game_over_timer() -> None:
    g = _make_game()
    g.timer = 0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_check_game_over_heat() -> None:
    g = _make_game()
    g.heat = 100.0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_check_game_over_survives() -> None:
    g = _make_game()
    g.timer = 1000
    g.heat = 10.0
    g._check_game_over()
    assert g.phase == Phase.PLAYING


# ── particles & floating text ───────────────────────────────────────


def test_particles_move_and_expire() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=1.0, vy=1.0, life=2, color=10)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].x == 1.0
    assert g.particles[0].life == 1
    g._update_particles()
    assert len(g.particles) == 0


def test_floating_text_moves_up_and_expires() -> None:
    g = _make_game()
    g.floats = [FloatingText(x=50, y=60, text="+10", life=2, color=7)]
    g._update_floats()
    assert len(g.floats) == 1
    assert g.floats[0].y == 59
    assert g.floats[0].life == 1
    g._update_floats()
    assert len(g.floats) == 0


def test_floating_text_spawned_on_match() -> None:
    g = _make_game()
    g.forecast_color = 0
    g.fronts = [WeatherFront(x=50.0, y=100, color=0, speed=1.0)]
    g._forecast_armed()
    assert len(g.floats) >= 1
    assert any("+" in ft.text for ft in g.floats)


def test_super_forecast_spawns_announcement() -> None:
    g = _make_game()
    g.forecast_color = 0
    g.combo = 3
    g.max_combo = 3
    g.fronts = [WeatherFront(x=50.0, y=100, color=0, speed=1.0)]
    g._forecast_armed()
    assert any(ft.text == "SUPER FORECAST!" for ft in g.floats)


def test_burst_creates_particles() -> None:
    g = _make_game()
    g._burst(100.0, 100.0)
    assert len(g.particles) == 8


# ── integration: full resolve → heat → game over ───────────────────


def test_wrong_forecast_drives_game_over() -> None:
    g = _make_game()
    g.forecast_color = 0
    for _ in range(7):  # 7 * 15 = 105 > 100
        g.fronts = [WeatherFront(x=50.0, y=100, color=1, speed=1.0)]
        g._forecast_armed()
    assert g.heat >= 100.0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_line_x_constant() -> None:
    assert LINE_X == 56


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
