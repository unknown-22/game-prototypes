"""test_imports.py — Headless logic tests for DIVE CHAIN (251_dive_chain)."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
_mock_pyxel.KEY_UP = 265
_mock_pyxel.KEY_DOWN = 264
_mock_pyxel.frame_count = 0
sys.modules["pyxel"] = _mock_pyxel

from main import (  # noqa: E402
    Game,
    Phase,
    Ring,
    Particle,
    GhostPoint,
)

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
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = 0
    g.diver_x = 0.0
    g.diver_y = 0.0
    g.diver_vx = 0.0
    g.diver_vy = 0.0
    g.diver_color = RED
    g.diver_color_idx = 0
    g.diver_color_cooldown = 0
    g.diver_airborne = False
    g.power = 0.0
    g.charging = False
    g.stun_timer = 0
    g.landing_cooldown = 0
    g.super_timer = 0
    g.rings = []
    g.particles = []
    g.floating_texts = []
    g.ghost_points = []
    g.best_ghost = []
    g.best_score = 0
    g.ring_spawn_timer = 60
    g._shake_frames = 0
    g._bounce_anim = 0.0
    g.reset()
    g._rng = random.Random(seed)
    return g


class TestDataClasses:
    def test_ring_creation(self) -> None:
        r = Ring(100.0, 80.0, -0.5, 0.2, RED)
        assert r.x == 100.0
        assert r.y == 80.0
        assert r.vx == -0.5
        assert r.vy == 0.2
        assert r.color == RED
        assert r.radius == 12

    def test_particle_creation(self) -> None:
        p = Particle(10.0, 20.0, 1.0, -1.0, 30, RED)
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.vx == 1.0
        assert p.vy == -1.0
        assert p.life == 30
        assert p.color == RED

    def test_ghost_point_creation(self) -> None:
        gp = GhostPoint(100.0, 150.0)
        assert gp.x == 100.0
        assert gp.y == 150.0

    def test_color_constants(self) -> None:
        assert Game.COLORS == (8, 11, 5, 10)


class TestGameState:
    def test_reset_initial_state(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.timer == Game.GAME_DURATION
        assert g.heat == 0.0
        assert g.super_timer == 0
        assert g.diver_airborne is False
        assert g.power == 0.0
        assert g.charging is False
        assert len(g.rings) == 0
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0
        assert g.best_score == 0

    def test_diver_starts_on_springboard(self) -> None:
        g = _make_game()
        assert g.diver_y == Game.SPRINGBOARD_Y - Game.DIVER_H
        assert g.diver_airborne is False


class TestRingSpawning:
    def test_spawn_ring(self) -> None:
        g = _make_game()
        g.timer = Game.GAME_DURATION
        r = g._spawn_ring()
        assert isinstance(r, Ring)
        assert Game.AIR_RIGHT <= r.x <= Game.AIR_RIGHT + 20
        assert Game.AIR_TOP + 20 <= r.y <= Game.AIR_BOTTOM - 20
        assert r.color in Game.COLORS
        assert r.vx < 0  # drifts left
        assert r.radius == Game.RING_RADIUS

    def test_ring_cleanup_off_screen(self) -> None:
        g = _make_game()
        g.rings = [Ring(x=float(Game.AIR_LEFT - 30), y=100.0, vx=-0.5, vy=0.0, color=RED)]
        g.ring_spawn_timer = 999
        g._update_rings()
        assert len(g.rings) == 0

    def test_ring_cleanup_off_top(self) -> None:
        g = _make_game()
        g.rings = [Ring(x=100.0, y=float(Game.AIR_TOP - 30), vx=0.0, vy=-0.5, color=RED)]
        g.ring_spawn_timer = 999
        g._update_rings()
        assert len(g.rings) == 0

    def test_ring_count_limited(self) -> None:
        g = _make_game()
        g.timer = Game.GAME_DURATION
        for _ in range(Game.MAX_RINGS + 5):
            g.rings.append(g._spawn_ring())
        g.ring_spawn_timer = 1
        g._update_rings()
        assert len(g.rings) <= Game.MAX_RINGS


class TestCollision:
    def test_collision_overlapping(self) -> None:
        g = _make_game()
        ring = Ring(100.0, 100.0, 0.0, 0.0, RED)
        assert g._check_ring_collision(100.0, 100.0, ring) is True

    def test_collision_edge(self) -> None:
        g = _make_game()
        ring = Ring(100.0, 100.0, 0.0, 0.0, RED)
        dist = Game.COLLISION_RADIUS + ring.radius
        assert g._check_ring_collision(100.0 + dist, 100.0, ring) is True

    def test_collision_far_away(self) -> None:
        g = _make_game()
        ring = Ring(100.0, 100.0, 0.0, 0.0, RED)
        assert g._check_ring_collision(200.0, 200.0, ring) is False


class TestRingCollection:
    def test_collect_matching_ring(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_color = RED
        g.score = 0
        g.combo = 0
        ring = Ring(100.0, 100.0, 0.0, 0.0, RED)
        g.rings = [ring]
        g._collect_ring(ring)
        assert ring not in g.rings
        assert g.combo == 1
        assert g.max_combo == 1
        assert g.score == 10  # 10 * combo * 1

    def test_collect_mismatching_ring(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_color = RED
        g.heat = 0.0
        g.combo = 3
        ring = Ring(100.0, 100.0, 0.0, 0.0, LIME)
        g.rings = [ring]
        g._collect_ring(ring)
        assert ring not in g.rings
        assert g.combo == 0
        assert g.heat == 15.0
        assert g.stun_timer == 15

    def test_combo_multiplier(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_color = RED
        g.combo = 2
        g.score = 0
        ring = Ring(100.0, 100.0, 0.0, 0.0, RED)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.combo == 3
        assert g.score == 30  # BASE(10) * combo(3)

    def test_super_mode_any_color(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_timer = 100
        g.diver_color = RED
        g.combo = 3
        g.score = 0
        ring = Ring(100.0, 100.0, 0.0, 0.0, LIME)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.combo == 4
        assert g.score == 120  # 10 * 4 * 3

    def test_super_activation_at_combo_4(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_color = RED
        g.combo = 3
        ring = Ring(100.0, 100.0, 0.0, 0.0, RED)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.super_timer == Game.SUPER_DURATION

    def test_super_does_not_reactivate(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_timer = 100
        g.diver_color = RED
        g.combo = 5
        ring = Ring(100.0, 100.0, 0.0, 0.0, RED)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.super_timer == 100  # unchanged

    def test_max_combo_tracking(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_color = RED
        for i in range(1, 6):
            ring = Ring(100.0, 100.0, 0.0, 0.0, RED)
            g.rings = [ring]
            g._collect_ring(ring)
        assert g.combo == 5
        assert g.max_combo == 5

    def test_mismatch_resets_combo(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_color = RED
        g.combo = 4
        ring = Ring(100.0, 100.0, 0.0, 0.0, LIME)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.combo == 0


class TestDiverLaunch:
    def test_launch_no_power(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_vy = 0.0
        g.diver_vx = 0.0
        g.power = 0.0
        g._launch_diver()
        assert g.diver_vy == 0.0
        assert g.diver_airborne is False

    def test_launch_applies_velocity(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.power = 50.0
        g.diver_airborne = False
        g._launch_diver()
        assert g.diver_vy < 0  # upward
        assert g.diver_airborne is True
        assert g.power == 0.0
        assert g.combo == 0

    def test_launch_max_power(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.power = Game.POWER_MAX
        g._launch_diver()
        # vy = -100 * 0.12 = -12.0
        assert abs(g.diver_vy - (-Game.POWER_MAX * Game.LAUNCH_VY_SCALE)) < 0.01
        # vx = 100 * 0.03 = 3.0
        assert abs(g.diver_vx - (Game.POWER_MAX * Game.LAUNCH_VX_SCALE)) < 0.01


class TestDiverPhysics:
    def test_gravity_applied_when_airborne(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_airborne = True
        g.diver_vy = 0.0
        g.diver_y = 100.0
        g._update_diver_physics()
        assert g.diver_vy > 0.0  # gravity pulls down

    def test_no_physics_on_ground(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_airborne = False
        g.diver_vy = 5.0
        g._update_diver_physics()
        assert g.diver_vy == 5.0  # unchanged

    def test_landing_on_springboard(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_airborne = True
        g.diver_vy = 5.0
        g.diver_y = Game.SPRINGBOARD_Y - Game.DIVER_H + 2  # past the board
        g._update_diver_physics()
        assert g.diver_airborne is False
        assert g.diver_y == Game.SPRINGBOARD_Y - Game.DIVER_H
        assert g.diver_vy == 0.0
        assert g.landing_cooldown == 30


class TestColorCycling:
    def test_cycle_color_up(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_color = RED
        g._cycle_diver_color(1)
        assert g.diver_color == LIME

    def test_cycle_color_down(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_color = LIME
        g._cycle_diver_color(-1)
        assert g.diver_color == RED

    def test_cycle_color_wraps(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_color = YELLOW
        g._cycle_diver_color(1)
        assert g.diver_color == RED

    def test_cycle_blocked_in_super(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_timer = 100
        g.diver_color = RED
        g._cycle_diver_color(1)
        assert g.diver_color == RED

    def test_cycle_blocked_by_stun(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.stun_timer = 10
        g.diver_color = RED
        g._cycle_diver_color(1)
        assert g.diver_color == RED

    def test_cycle_cooldown(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_color = RED
        g._cycle_diver_color(1)
        assert g.diver_color == LIME
        assert g.diver_color_cooldown == Game.COLOR_CYCLE_COOLDOWN
        g._cycle_diver_color(1)  # blocked
        assert g.diver_color == LIME
        g.diver_color_cooldown = 0
        g._cycle_diver_color(1)
        assert g.diver_color == DARK_BLUE


class TestHeat:
    def test_heat_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = 100.0
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
        g.super_timer = 100
        g.heat = 50.0
        g._update_heat()
        assert g.heat == 50.0

    def test_heat_threshold_before_decay(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = 100.0
        g._update_heat()
        assert g.phase == Phase.GAME_OVER
        assert g.heat == 100.0

    def test_heat_from_mismatch(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_color = RED
        g.heat = 0.0
        ring = Ring(100.0, 100.0, 0.0, 0.0, LIME)
        g.rings = [ring]
        g._collect_ring(ring)
        assert g.heat == 15.0


class TestTimers:
    def test_timer_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.timer = 1
        g.update()
        assert g.phase == Phase.GAME_OVER
        assert g.timer == 0

    def test_super_timer_expires(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_timer = 2
        g.timer = 1000
        g.update()
        assert g.super_timer == 1
        g.update()
        assert g.super_timer == 0

    def test_on_game_over_best_score(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 500
        g.best_score = 300
        g.ghost_points = [GhostPoint(100.0, 100.0)]
        g._on_game_over()
        assert g.phase == Phase.GAME_OVER
        assert g.best_score == 500
        assert len(g.best_ghost) == 1

    def test_on_game_over_not_best(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 200
        g.best_score = 500
        best_ghost = [GhostPoint(50.0, 50.0)]
        g.best_ghost = best_ghost
        g.ghost_points = [GhostPoint(100.0, 100.0)]
        g._on_game_over()
        assert g.best_score == 500
        assert g.best_ghost is best_ghost


class TestParticles:
    def test_spawn_particles(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 5, 5, color=RED)
        assert len(g.particles) == 5
        for p in g.particles:
            assert p.color == RED

    def test_spawn_particles_rainbow(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 5, 5, color=-1)
        assert len(g.particles) == 5

    def test_update_particles_decay(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 3, 3, color=RED)
        assert len(g.particles) == 3
        for p in g.particles:
            p.life = 1
        g._update_particles()
        assert len(g.particles) == 0


class TestFloatingTexts:
    def test_add_floating_text(self) -> None:
        g = _make_game()
        g._add_floating_text(100.0, 50.0, "+10", WHITE)
        assert len(g.floating_texts) == 1
        x, y, text, color, life = g.floating_texts[0]
        assert x == 100.0
        assert text == "+10"
        assert color == WHITE
        assert life == 30

    def test_update_floating_texts_decay(self) -> None:
        g = _make_game()
        g.floating_texts = [(100.0, 50.0, "test", WHITE, 1)]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0

    def test_update_floating_texts_move_up(self) -> None:
        g = _make_game()
        g.floating_texts = [(100.0, 50.0, "test", WHITE, 30)]
        g._update_floating_texts()
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0][1] < 50.0
        assert g.floating_texts[0][4] == 29


class TestCharge:
    def test_charge_builds_power(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.charging = True
        g.diver_airborne = False
        g.power = 0.0
        g.update()
        assert g.power > 0.0

    def test_charge_auto_launch_at_max(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.charging = True
        g.diver_airborne = False
        g.power = Game.POWER_MAX - 0.1
        g.timer = 1000
        g.update()
        assert g.diver_airborne is True
        assert g.power == 0.0

    def test_landing_cooldown_prevents_recharge(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.landing_cooldown = 30
        g.diver_airborne = False
        g.charging = True
        g.power = 0.0
        g.timer = 1000
        g.update()
        assert g.power == 0.0  # charging prevented by cooldown

    def test_landing_cooldown_decrements(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.landing_cooldown = 10
        g.timer = 1000
        g.update()
        assert g.landing_cooldown == 9


class TestGhostTrail:
    def test_ghost_points_recorded_every_5_frames(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.diver_airborne = True
        g.diver_x = 100.0
        g.diver_y = 80.0
        g.timer = 1000
        _mock_pyxel.frame_count = 5
        g.update()
        assert len(g.ghost_points) == 1
        assert g.ghost_points[0].x > 0.0  # ghost track records current position


class TestGameOver:
    def test_best_ghost_saved(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 1000
        g.best_score = 500
        g.ghost_points = [GhostPoint(80.0, 120.0), GhostPoint(90.0, 100.0)]
        g._on_game_over()
        assert g.best_score == 1000
        assert len(g.best_ghost) == 2


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
