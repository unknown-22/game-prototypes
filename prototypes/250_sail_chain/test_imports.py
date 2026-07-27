"""test_imports.py — Headless logic tests for SAIL CHAIN (250_sail_chain)."""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Mock pyxel before importing game module
import types

_mock_pyxel = types.ModuleType("pyxel")
_mock_pyxel.BLACK = 0
_mock_pyxel.NAVY = 1
_mock_pyxel.PURPLE = 2
_mock_pyxel.GREEN = 3
_mock_pyxel.BROWN = 4
_mock_pyxel.DARK_BLUE = 5
_mock_pyxel.LIGHT_BLUE = 6
_mock_pyxel.WHITE = 7
_mock_pyxel.RED = 8
_mock_pyxel.ORANGE = 9
_mock_pyxel.YELLOW = 10
_mock_pyxel.LIME = 11
_mock_pyxel.CYAN = 12
_mock_pyxel.GRAY = 13
_mock_pyxel.PINK = 14
_mock_pyxel.PEACH = 15
_mock_pyxel.KEY_SPACE = 32
_mock_pyxel.KEY_RETURN = 13
_mock_pyxel.KEY_LEFT = 263
_mock_pyxel.KEY_RIGHT = 262
_mock_pyxel.KEY_UP = 265
_mock_pyxel.KEY_DOWN = 264
_mock_pyxel.KEY_Z = 90
sys.modules["pyxel"] = _mock_pyxel

from main import (  # noqa: E402
    BUOY_COLOR_VALS,
    Game,
    Phase,
    Buoy,
    BuoyColor,
    Particle,
    FloatingText,
)

# Module-level color constants from main
RED = 8
LIME = 11
DARK_BLUE = 5
YELLOW = 10
WHITE = 7
GREEN = 3
CYAN = 12
GRAY = 13
ORANGE = 9


def _make_game(seed: int = 42) -> Game:
    """Factory: pre-init all instance attributes, then reset()."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.timer = 0
    g.heat = 0.0
    g.boat_x = 0.0
    g.boat_y = 0.0
    g.boat_vx = 0.0
    g.boat_vy = 0.0
    g.boat_angle = 0.0
    g.sail_color = BuoyColor.RED
    g.wind_dir = 0.0
    g.wind_strength = 0.0
    g.wind_timer = 0
    g.super_timer = 0
    g.super_mode = False
    g.buoys = []
    g.particles = []
    g.floating_texts = []
    g.ghost_path = []
    g.current_path = []
    g.best_score = 0
    g.spawn_timer = 0
    g.spawn_interval = 90
    g.color_cycle_cooldown = 0
    g.color_cycle_timer = 0
    g.color_cycle_interval = 90
    g._path_record_timer = 0
    g._screen_shake = 0
    g._rainbow_frame = 0
    g.reset()
    # Override RNG after reset (reset() may re-create it)
    g._rng = random.Random(seed)
    return g


# ── Data class tests ──


class TestDataClasses:
    def test_buoy_creation(self) -> None:
        b = Buoy(100.0, 200.0, BuoyColor.RED)
        assert b.x == 100.0
        assert b.y == 200.0
        assert b.color == BuoyColor.RED
        assert b.vx == 0.0
        assert b.vy == 0.0

    def test_particle_creation(self) -> None:
        p = Particle(10.0, 20.0, 1.0, -1.0, 30, RED)
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.vx == 1.0
        assert p.vy == -1.0
        assert p.life == 30
        assert p.color == RED
        assert p.size == 2.0

    def test_floating_text_creation(self) -> None:
        ft = FloatingText(100.0, 50.0, "+10", 30, WHITE)
        assert ft.x == 100.0
        assert ft.y == 50.0
        assert ft.text == "+10"
        assert ft.life == 30
        assert ft.vy == -1.0

    def test_buoy_color_values(self) -> None:
        assert BUOY_COLOR_VALS == (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW
        assert BUOY_COLOR_VALS[BuoyColor.RED.value] == 8
        assert BUOY_COLOR_VALS[BuoyColor.LIME.value] == 11
        assert BUOY_COLOR_VALS[BuoyColor.DARK_BLUE.value] == 5
        assert BUOY_COLOR_VALS[BuoyColor.YELLOW.value] == 10


# ── Game state tests ──


class TestGameState:
    def test_reset_initial_state(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.timer == Game.GAME_TIME
        assert g.heat == 0.0
        assert g.super_mode is False
        assert g.super_timer == 0
        assert len(g.buoys) == 5
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0
        assert g.best_score == 0

    def test_boat_starts_center(self) -> None:
        g = _make_game()
        assert g.boat_x == Game.SCREEN_W / 2
        assert g.boat_y == Game.SCREEN_H / 2

    def test_wind_initialized(self) -> None:
        g = _make_game()
        assert 0 <= g.wind_dir <= math.pi * 2
        assert g.wind_strength == 0.5
        assert 300 <= g.wind_timer <= 600


# ── Movement tests ──


class TestMovement:
    def test_move_boat_thrust(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.boat_vx = 0.0
        g.boat_vy = 0.0
        g._move_boat(1.0, 0.0)
        assert g.boat_vx > 0.0

    def test_move_boat_super_mode_faster(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_mode = True
        g.boat_vx = 0.0
        g.boat_vy = 0.0
        g._move_boat(1.0, 0.0)
        # super mode gives 1.3x thrust
        assert abs(g.boat_vx - Game.BOAT_THRUST * 1.3) < 0.01

    def test_physics_friction(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.wind_strength = 0.0  # disable wind for clean friction test
        g.boat_vx = 2.0
        g.boat_vy = 0.0
        g._update_physics()
        assert abs(g.boat_vx - 2.0 * Game.BOAT_FRICTION) < 0.01

    def test_physics_speed_clamp(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.boat_vx = 10.0
        g.boat_vy = 0.0
        g._update_physics()
        assert math.hypot(g.boat_vx, g.boat_vy) <= Game.MAX_SPEED + 0.01

    def test_physics_screen_clamp(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.boat_x = -10.0
        g.boat_y = -10.0
        g.boat_vx = 0.0
        g.boat_vy = 0.0
        g._update_physics()
        assert g.boat_x >= 0.0
        assert g.boat_y >= 0.0

        g.boat_x = 400.0
        g.boat_y = 300.0
        g._update_physics()
        assert g.boat_x <= Game.SCREEN_W
        assert g.boat_y <= Game.SCREEN_H

    def test_physics_wind_effect(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.wind_dir = math.pi / 2  # blowing down
        g.wind_strength = 2.0
        g.boat_vx = 0.0
        g.boat_vy = 0.0
        g._update_physics()
        # wind pushes down (positive y)
        assert g.boat_vy > 0.0

    def test_physics_wind_ignored_in_super(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_mode = True
        g.wind_dir = math.pi / 2
        g.wind_strength = 10.0
        g.boat_vx = 0.0
        g.boat_vy = 0.0
        g._update_physics()
        # wind should have no effect
        assert g.boat_vx == 0.0
        assert g.boat_vy == 0.0


# ── Color cycling tests ──


class TestColorCycling:
    def test_cycle_color_down(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.RED
        g._cycle_color(1)
        assert g.sail_color == BuoyColor.LIME

    def test_cycle_color_up(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.LIME
        g._cycle_color(-1)
        assert g.sail_color == BuoyColor.RED

    def test_cycle_color_wraps(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.YELLOW
        g._cycle_color(1)
        assert g.sail_color == BuoyColor.RED

    def test_cycle_color_blocked_in_super(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_mode = True
        original = g.sail_color
        g._cycle_color(1)
        assert g.sail_color == original

    def test_cycle_color_cooldown(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.RED
        g._cycle_color(1)  # sets cooldown to 8
        assert g.sail_color == BuoyColor.LIME
        g._cycle_color(1)  # blocked by cooldown
        assert g.sail_color == BuoyColor.LIME
        # manually clear cooldown
        g.color_cycle_cooldown = 0
        g._cycle_color(1)
        assert g.sail_color == BuoyColor.DARK_BLUE


# ── Buoy collection tests ──


class TestBuoyCollection:
    def test_collect_same_color(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 0
        g.combo = 0
        g.sail_color = BuoyColor.RED
        b = Buoy(g.boat_x, g.boat_y, BuoyColor.RED)
        g.buoys = [b]
        g._collect_buoy(b)
        assert b not in g.buoys
        assert g.combo == 1
        assert g.max_combo == 1
        assert g.score == 10  # BASE_SCORE * combo * 1

    def test_collect_wrong_color(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.RED
        g.heat = 0.0
        g.combo = 3
        b = Buoy(g.boat_x, g.boat_y, BuoyColor.LIME)
        g.buoys = [b]
        g._collect_buoy(b)
        assert b not in g.buoys
        assert g.combo == 0  # reset
        assert g.heat == Game.MISMATCH_HEAT

    def test_combo_multiplier(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.RED
        g.combo = 2
        b = Buoy(g.boat_x, g.boat_y, BuoyColor.RED)
        g.buoys = [b]
        g._collect_buoy(b)
        assert g.combo == 3
        assert g.score == 30  # BASE_SCORE * 3

    def test_super_mode_any_color(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_mode = True
        g.super_timer = 100
        g.sail_color = BuoyColor.RED
        g.combo = 3
        b = Buoy(g.boat_x, g.boat_y, BuoyColor.LIME)
        g.buoys = [b]
        g._collect_buoy(b)
        assert g.combo == 4
        assert g.score == 120  # BASE_SCORE * 4 * 3

    def test_check_collections_distance(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.RED
        # Place buoy at collect range boundary
        b = Buoy(g.boat_x + Game.COLLECT_RADIUS, g.boat_y, BuoyColor.RED)
        g.buoys = [b]
        g._check_collections()
        assert len(g.buoys) == 0  # collected

    def test_no_collection_far_away(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.RED
        b = Buoy(g.boat_x + 100, g.boat_y, BuoyColor.RED)
        g.buoys = [b]
        g._check_collections()
        assert len(g.buoys) == 1  # not collected

    def test_super_activation_at_combo_4(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.RED
        g.combo = 3
        b = Buoy(g.boat_x, g.boat_y, BuoyColor.RED)
        g.buoys = [b]
        g._collect_buoy(b)
        assert g.super_mode is True
        assert g.super_timer == Game.SUPER_DURATION


# ── Heat tests ──


class TestHeat:
    def test_heat_threshold_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = 100.0
        g.timer = 100
        g._update_heat()
        assert g.phase == Phase.GAME_OVER

    def test_heat_decay(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = 50.0
        g._update_heat()
        assert g.heat < 50.0
        assert g.heat >= 50.0 - Game.HEAT_DECAY

    def test_heat_no_decay_in_super(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_mode = True
        g.heat = 50.0
        g._update_heat()
        assert g.heat == 50.0  # no decay

    def test_heat_threshold_before_decay(self) -> None:
        """Critical: threshold check must happen BEFORE decay."""
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = 100.0
        # Even though decay would drop it below 100, game over should trigger
        g._update_heat()
        assert g.phase == Phase.GAME_OVER

    def test_heat_from_mismatch(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.RED
        g.heat = 0.0
        b = Buoy(g.boat_x, g.boat_y, BuoyColor.LIME)
        g.buoys = [b]
        g._collect_buoy(b)
        assert g.heat == Game.MISMATCH_HEAT


# ── Timer / phase tests ──


class TestTimers:
    def test_timer_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.timer = 1
        g._update_timers()
        assert g.phase == Phase.GAME_OVER
        assert g.timer == 0

    def test_super_timer_expires(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_mode = True
        g.super_timer = 1
        g._update_timers()
        assert g.super_mode is False
        assert g.super_timer == 0

    def test_on_game_over_best_score(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 500
        g.best_score = 300
        g.current_path = [(100.0, 100.0), (200.0, 200.0)]
        g._on_game_over()
        assert g.phase == Phase.GAME_OVER
        assert g.best_score == 500
        assert g.ghost_path == [(100.0, 100.0), (200.0, 200.0)]

    def test_on_game_over_not_best(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 200
        g.best_score = 500
        g.ghost_path = [(50.0, 50.0)]
        g.current_path = [(100.0, 100.0)]
        g._on_game_over()
        assert g.phase == Phase.GAME_OVER
        assert g.best_score == 500  # unchanged
        assert g.ghost_path == [(50.0, 50.0)]  # unchanged


# ── Spawning tests ──


class TestSpawning:
    def test_spawn_buoy(self) -> None:
        g = _make_game()
        initial = len(g.buoys)
        g._spawn_buoy()
        assert len(g.buoys) == initial + 1
        b = g.buoys[-1]
        assert isinstance(b.color, BuoyColor)
        assert 0 <= b.x <= Game.SCREEN_W + 10 or -10 <= b.x <= 0
        assert 0 <= b.y <= Game.SCREEN_H + 10 or -10 <= b.y <= 0

    def test_update_buoys_refill(self) -> None:
        g = _make_game()
        g.buoys = []  # empty
        g._update_buoys()
        assert len(g.buoys) == Game.MAX_BUOYS

    def test_update_buoys_off_screen_miss_heat(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = 0.0
        b = Buoy(-100.0, 100.0, BuoyColor.RED, vx=-1.0, vy=0.0)
        g.buoys = [b]
        g._update_buoys()  # buoy moves further off, gets removed
        assert b not in g.buoys
        assert g.heat >= Game.MISS_HEAT  # miss penalty


# ── Wind tests ──


class TestWind:
    def test_wind_changes_when_timer_expires(self) -> None:
        g = _make_game()
        g.wind_timer = 1
        g._update_wind()
        assert g.wind_timer >= 300  # reset to new interval
        assert 0.5 <= g.wind_strength <= 2.0  # strength within valid range


# ── Particle tests ──


class TestParticles:
    def test_spawn_particles_fixed_color(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 5, 5, 2.0, color=RED)
        assert len(g.particles) == 5  # deterministic with seed
        for p in g.particles:
            assert p.color == RED

    def test_spawn_particles_random_color(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 5, 5, 2.0, random_color=True)
        assert len(g.particles) == 5

    def test_update_particles_decay(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 3, 3, 2.0, color=RED)
        initial_count = len(g.particles)
        assert initial_count == 3
        # Set all particles to life=1 — they'll be removed on next update
        for p in g.particles:
            p.life = 1
        g._update_particles()
        assert len(g.particles) == 0  # all removed


# ── Floating text tests ──


class TestFloatingText:
    def test_update_floating_texts_decay(self) -> None:
        g = _make_game()
        g.floating_texts = [
            FloatingText(100.0, 50.0, "test", 1, WHITE),
        ]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0  # life=1 removed after update

    def test_update_floating_texts_move(self) -> None:
        g = _make_game()
        g.floating_texts = [
            FloatingText(100.0, 50.0, "test", 30, WHITE),
        ]
        g._update_floating_texts()
        assert g.floating_texts[0].y < 50.0  # moved up
        assert g.floating_texts[0].life == 29


# ── Path recording tests ──


class TestPathRecording:
    def test_record_path(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g._path_record_timer = 1
        g.boat_x = 150.0
        g.boat_y = 120.0
        g._record_path()
        assert g.current_path == [(150.0, 120.0)]
        assert g._path_record_timer == 15  # reset to 15

    def test_record_path_no_record_when_timer_high(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g._path_record_timer = 10
        g._record_path()
        assert g.current_path == []  # not recorded


# ── Collect_buoy edge case tests ──


class TestCollectBuoyEdgeCases:
    def test_collect_removes_from_buoys(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.RED
        b = Buoy(g.boat_x, g.boat_y, BuoyColor.RED)
        g.buoys = [b]
        g._collect_buoy(b)
        assert len(g.buoys) == 0

    def test_combo_tracking_max_combo(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.RED
        # Collect 5 matching buoys
        for i in range(5):
            b = Buoy(g.boat_x, g.boat_y, BuoyColor.RED)
            g.buoys = [b]
            g._collect_buoy(b)
        assert g.combo == 5
        assert g.max_combo == 5

    def test_super_only_activates_once(self) -> None:
        """SUPER should activate at combo=4 but not re-activate while active."""
        g = _make_game()
        g.phase = Phase.PLAYING
        g.sail_color = BuoyColor.RED
        g.combo = 3
        b = Buoy(g.boat_x, g.boat_y, BuoyColor.RED)
        g.buoys = [b]
        g._collect_buoy(b)
        assert g.super_mode is True
        first_super_timer = g.super_timer
        # Another collection while in SUPER should not reset timer
        g.combo = 5
        b2 = Buoy(g.boat_x, g.boat_y, BuoyColor.RED)
        g.buoys = [b2]
        g._collect_buoy(b2)
        # super_timer NOT changed by _collect_buoy — stays same
        assert g.super_timer == first_super_timer
        assert g.super_mode is True


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
