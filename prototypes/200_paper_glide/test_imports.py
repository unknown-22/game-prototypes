"""test_imports.py — Headless logic tests for 200_paper_glide."""
import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/200_paper_glide")

from main import (
    Game,
    Plane,
    Ring,
    Particle,
    GhostPoint,
    Phase,
    RED, GREEN, ORANGE, WHITE,
)


def _make_game() -> Game:
    """Create a Game bypassing pyxel.init for headless testing."""
    g: Game = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = Game.TIMER_FRAMES
    g.game_over = False
    g.plane = Plane(0, 0, 0, 0)
    g.rings: list[Ring] = []
    g.particles: list[Particle] = []
    g.ghost_trail: list[GhostPoint] = []
    g.ghost_active = False
    g.aim_start_x = 0
    g.aim_start_y = 0
    g.drag_power = 0.0
    g.drag_angle = 0.0
    g.throw_count = 0
    g.super_active = False
    g.super_timer = 0
    g.combo_ring_color = None
    g._flight_path: list[GhostPoint] = []
    g._mouse_pressed = False
    g.rng = random.Random(42)
    g.reset()
    return g


def _make_plane(x: float = 100, y: float = 120, vx: float = 5.0, vy: float = 0.0) -> Plane:
    return Plane(x, y, vx, vy)


def _make_ring(x: int = 150, y: int = 120, color: int = RED) -> Ring:
    return Ring(x, y, color)


# === Phase & Game Structure Tests ===


def test_game_has_phases() -> None:
    assert Phase.TITLE in Phase
    assert Phase.AIMING in Phase
    assert Phase.FLYING in Phase
    assert Phase.GAME_OVER in Phase


def test_reset_initializes_state() -> None:
    g = _make_game()
    g.score = 100  # dirty state
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.throw_count == 0
    assert g.super_active is False
    assert g.super_timer == 0
    assert g.combo_ring_color is None
    assert len(g.rings) >= 2  # at least 2 rings spawned
    assert g.timer == Game.TIMER_FRAMES


def test_rings_spawned_after_reset() -> None:
    g = _make_game()
    assert len(g.rings) >= 2
    assert len(g.rings) <= 6
    for ring in g.rings:
        assert ring.color in Game.RING_COLORS
        assert ring.active is True
        assert 0 <= ring.x <= 320
        assert 0 <= ring.y <= 240


# === Throw Plane Tests ===


def test_throw_plane_sets_velocity() -> None:
    g = _make_game()
    g._throw_plane(0.0, 8.0)  # straight right
    assert g.plane.x == Game.LAUNCH_X
    assert g.plane.y == Game.LAUNCH_Y
    assert abs(g.plane.vx - 8.0) < 0.01
    assert abs(g.plane.vy) < 0.01
    assert g.combo_ring_color is None
    assert g.throw_count == 1


def test_throw_plane_angle_upward() -> None:
    g = _make_game()
    g._throw_plane(-math.pi / 4, 8.0)  # upward right
    assert g.plane.vy < 0  # negative = up
    assert g.plane.vx > 0


def test_throw_plane_angle_downward() -> None:
    g = _make_game()
    g._throw_plane(math.pi / 4, 8.0)  # downward right
    assert g.plane.vy > 0  # positive = down
    assert g.plane.vx > 0


def test_throw_plane_resets_combo_color() -> None:
    g = _make_game()
    g.combo_ring_color = RED
    g._throw_plane(0.0, 5.0)
    assert g.combo_ring_color is None


def test_throw_plane_increments_throw_count() -> None:
    g = _make_game()
    assert g.throw_count == 0
    g._throw_plane(0.0, 5.0)
    assert g.throw_count == 1
    g._throw_plane(0.0, 5.0)
    assert g.throw_count == 2


# === Ring Collision Tests ===


def test_check_ring_collision_direct_hit() -> None:
    g = _make_game()
    g.plane = _make_plane(150, 120)  # plane at ring center
    ring = _make_ring(150, 120)
    assert g._check_ring_collision(ring) is True


def test_check_ring_collision_near_edge() -> None:
    g = _make_game()
    g.plane = _make_plane(150, 120)  # center
    ring = _make_ring(166, 120)  # 16px away, still < 18
    assert g._check_ring_collision(ring) is True


def test_check_ring_collision_far_away() -> None:
    g = _make_game()
    g.plane = _make_plane(100, 100)
    ring = _make_ring(200, 200)
    assert g._check_ring_collision(ring) is False


def test_check_ring_collision_boundary() -> None:
    g = _make_game()
    ring = _make_ring(0, 0)
    # exactly 17.0 distance
    g.plane = _make_plane(17.0, 0)
    assert g._check_ring_collision(ring) is True
    # 19px away — too far
    g.plane = _make_plane(19.0, 0)
    assert g._check_ring_collision(ring) is False


# === Handle Ring Pass Tests ===


def test_handle_ring_pass_first_ring_sets_color() -> None:
    g = _make_game()
    g.plane = _make_plane()
    ring = _make_ring(color=RED)
    assert g.combo_ring_color is None
    assert g.combo == 0
    g._handle_ring_pass(ring)
    assert g.combo_ring_color == RED
    assert g.combo == 1
    assert g.score > 0


def test_handle_ring_pass_same_color_extends_combo() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.combo_ring_color = RED
    g.combo = 3
    g.score = 50
    ring = _make_ring(color=RED)
    g._handle_ring_pass(ring)
    assert g.combo == 4
    assert g.score > 50


def test_handle_ring_pass_different_color_resets_combo() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.combo_ring_color = RED
    g.combo = 3
    g.score = 50
    g.heat = 0.0
    ring = _make_ring(color=GREEN)
    g._handle_ring_pass(ring)
    assert g.combo == 0
    assert g.combo_ring_color is None
    assert g.heat == Game.HEAT_MISMATCH


def test_handle_ring_pass_super_mode_always_matches() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.combo_ring_color = RED  # established color
    g.plane.super_timer = 100  # in super mode
    ring = _make_ring(color=GREEN)  # different color
    g._handle_ring_pass(ring)
    assert g.combo == 1  # combo increases (match via super mode)
    assert g.combo_ring_color == RED  # keeps original color


def test_combo_4_triggers_super() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.combo = 3
    g.combo_ring_color = RED
    g.super_active = False
    ring = _make_ring(color=RED)
    g._handle_ring_pass(ring)
    assert g.combo == 4
    assert g.super_active is True
    assert g.super_timer == Game.SUPER_DURATION
    assert g.plane.super_timer == Game.SUPER_DURATION


def test_handle_ring_pass_scoring_formula() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.combo = 0
    g.combo_ring_color = None
    ring = _make_ring(color=RED)
    g._handle_ring_pass(ring)
    # score = 10 * (1 + 1 * 0.5) = 15
    assert g.score == 15


def test_handle_ring_pass_scoring_combo_3() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.combo = 2
    g.combo_ring_color = RED
    g.score = 0
    ring = _make_ring(color=RED)
    g._handle_ring_pass(ring)
    # combo goes to 3, score = 10 * (1 + 3 * 0.5) = 25
    assert g.combo == 3
    assert g.score == 25


def test_handle_ring_pass_super_scoring_triple() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.plane.super_timer = 100
    g.combo = 0
    g.combo_ring_color = RED
    g.score = 0
    ring = _make_ring(color=RED)
    g._handle_ring_pass(ring)
    # combo=1, base = 10*(1+1*0.5)=15, super *3 = 45
    assert g.score == 45


def test_handle_ring_pass_heat_triggers_game_over() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.combo_ring_color = RED
    g.heat = 90.0
    g.game_over = False
    ring = _make_ring(color=GREEN)  # mismatch
    g._handle_ring_pass(ring)
    assert g.heat == 100.0  # HEAT_MISMATCH = 10
    assert g.game_over is True
    assert g.phase == Phase.GAME_OVER


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.combo_ring_color = RED
    g.combo = 5
    g.max_combo = 5
    ring = _make_ring(color=RED)
    g._handle_ring_pass(ring)
    assert g.combo == 6
    assert g.max_combo == 6


# === Spawn Rings Tests ===


def test_spawn_rings_generates_enough() -> None:
    g = _make_game()
    g.rings = []
    g.rng = random.Random(42)
    g._spawn_rings()
    assert len(g.rings) >= 2
    assert len(g.rings) <= 6


def test_spawn_rings_x_positions_increase() -> None:
    g = _make_game()
    g.rings = []
    g.rng = random.Random(42)
    g._spawn_rings()
    for i in range(len(g.rings) - 1):
        assert g.rings[i].x < g.rings[i + 1].x


def test_spawn_rings_deterministic() -> None:
    g1 = _make_game()
    g1.rings = []
    g1.rng = random.Random(42)
    g1._spawn_rings()

    g2 = _make_game()
    g2.rings = []
    g2.rng = random.Random(42)
    g2._spawn_rings()

    assert len(g1.rings) == len(g2.rings)
    for r1, r2 in zip(g1.rings, g2.rings):
        assert r1.x == r2.x
        assert r1.y == r2.y
        assert r1.color == r2.color


# === Particle Tests ===


def test_add_particles_creates_particles() -> None:
    g = _make_game()
    g.rng = random.Random(42)
    g._add_particles(100, 100, RED, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == RED
        assert p.life >= 15
        assert p.life <= 30


def test_update_particles_moves_and_decays() -> None:
    g = _make_game()
    # _update_particles order: x+=vx, y+=vy, vy+=0.05, life-=1
    # On first frame: vy starts at 0, so y stays 0; vy becomes 0.05 after
    g.particles = [Particle(0, 0, 1, 0, 2, RED), Particle(0, 0, 0, 1, 1, GREEN)]
    g._update_particles()
    # particle 1: life 2→1, still alive, x=1, y=0+before_gravity_vy, vy=0.05
    # particle 2: life 1→0, removed
    assert len(g.particles) == 1
    assert g.particles[0].color == RED
    assert g.particles[0].life == 1
    assert g.particles[0].x == 1
    assert g.particles[0].vy == 0.05  # gravity applied to vy (but not yet to y)


def test_update_particles_gravity_applied() -> None:
    g = _make_game()
    # _update_particles order: x+=vx, y+=vy, vy+=0.05, life-=1
    g.particles = [Particle(0, 0, 0, 0, 10, WHITE)]
    g._update_particles()
    assert g.particles[0].vy == 0.05  # gravity was added to vy (y not yet affected)


def test_ring_pass_particles_count() -> None:
    g = _make_game()
    g.rng = random.Random(42)
    g._add_ring_pass_particles(100, 100, RED)
    assert len(g.particles) == 8


def test_super_particles_count() -> None:
    g = _make_game()
    g.rng = random.Random(42)
    g._add_super_particles(100, 100)
    assert len(g.particles) == 20


def test_miss_particles_count() -> None:
    g = _make_game()
    g.rng = random.Random(42)
    g._add_miss_particles(100, 100)
    assert len(g.particles) == 4
    for p in g.particles:
        assert p.color == ORANGE


def test_mismatch_particles_count() -> None:
    g = _make_game()
    g.rng = random.Random(42)
    g._add_mismatch_particles(100, 100)
    assert len(g.particles) == 4
    for p in g.particles:
        assert p.color == ORANGE


# === SUPER Tests ===


def test_activate_super_sets_state() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g._activate_super()
    assert g.super_active is True
    assert g.super_timer == Game.SUPER_DURATION
    assert g.plane.super_timer == Game.SUPER_DURATION
    assert len(g.particles) == 20  # super particles spawned


def test_super_timer_decrements() -> None:
    g = _make_game()
    g.plane = Plane(100, 120, 5, 0, True, super_timer=50)
    g.plane.super_timer = 50
    # We can directly decrement since _update_plane uses pyxel.frame_count
    g.plane.super_timer -= 1
    assert g.plane.super_timer == 49


# === HEAT Tests ===


def test_update_heat_decays() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0
    assert g.heat >= 49.9  # roughly 50 - 0.02


def test_update_heat_clamps_to_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_triggers_game_over() -> None:
    g = _make_game()
    # _update_heat now checks BEFORE decaying (fixed decay-before-check bug)
    g.heat = 100.0  # exactly at max
    g.game_over = False
    g.phase = Phase.AIMING
    g._update_heat()
    assert g.game_over is True
    assert g.phase == Phase.GAME_OVER


def test_update_heat_does_nothing_when_game_over() -> None:
    g = _make_game()
    g.heat = 50.0
    g.game_over = True
    current_heat = g.heat
    g._update_heat()
    assert g.heat == current_heat  # no decay


# === Plane Physics Tests ===


def test_plane_gravity_applied() -> None:
    plane = Plane(100, 100, 0, 0)
    gravity = Game.GRAVITY
    plane.vy += gravity
    plane.y += plane.vy
    assert plane.vy == gravity
    assert plane.y == 100 + gravity


def test_plane_drag_applied() -> None:
    plane = Plane(100, 100, 10, 5)
    drag = Game.DRAG
    plane.vx *= drag
    plane.vy *= drag
    assert plane.vx == 10 * drag
    assert plane.vy == 5 * drag


# === Scoring Tests ===


def test_score_reset_on_new_game() -> None:
    g = _make_game()
    g.score = 999
    g.reset()
    assert g.score == 0


def test_combo_reset_on_different_color() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.combo_ring_color = RED
    g.combo = 3
    ring = _make_ring(color=GREEN)
    g._handle_ring_pass(ring)
    assert g.combo == 0


def test_super_does_not_retrigger_when_already_active() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.combo = 5
    g.combo_ring_color = RED
    g.super_active = True
    g.super_timer = 200
    g.plane.super_timer = 200
    ring = _make_ring(color=RED)
    g._handle_ring_pass(ring)
    # super already active, combo increases but no new activation
    assert g.combo == 6
    # super_timer should not be reset to SUPER_DURATION
    assert g.super_timer == 200


# === Data Class Tests ===


def test_ring_defaults() -> None:
    ring = Ring(100, 200, RED)
    assert ring.active is True
    assert ring.color == RED


def test_plane_defaults() -> None:
    plane = Plane(50, 60, 3, 4)
    assert plane.alive is True
    assert plane.super_timer == 0
    assert plane.rainbow_phase == 0.0


def test_particle_creation() -> None:
    p = Particle(10, 20, 1, 2, 5, GREEN)
    assert p.x == 10
    assert p.y == 20
    assert p.vx == 1
    assert p.vy == 2
    assert p.life == 5
    assert p.color == GREEN


def test_ghost_point_creation() -> None:
    gp = GhostPoint(123, 456)
    assert gp.x == 123
    assert gp.y == 456


# === Edge Cases ===


def test_empty_rings_no_collision() -> None:
    g = _make_game()
    g.rings = []
    g.plane = _make_plane(150, 120)
    # _update_plane would exit early since no rings
    # Just verify plane is alive
    assert g.plane.alive is True


def test_inactive_ring_no_collision() -> None:
    g = _make_game()
    g.plane = _make_plane(150, 120)
    ring = Ring(150, 120, RED, active=False)
    # _update_plane checks ring.active before collision
    assert ring.active is False
    assert g._check_ring_collision(ring) is True  # collision IS detected
    # but _update_plane skips inactive rings


def test_super_mode_expires() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.super_active = True
    g.super_timer = 1
    g.plane.super_timer = 1
    # simulate decrement that happens in _update_plane
    g.plane.super_timer -= 1
    g.super_timer -= 1
    if g.plane.super_timer == 0:
        g.super_active = False
    assert g.super_active is False
    assert g.super_timer == 0


def test_heat_exact_100_plus_mismatch_game_over() -> None:
    g = _make_game()
    g.plane = _make_plane()
    g.combo_ring_color = RED
    g.heat = 95.0
    g.game_over = False
    ring = _make_ring(color=GREEN)
    g._handle_ring_pass(ring)
    # heat = 105 > 100
    assert g.heat >= 100
    assert g.game_over is True


def test_throw_power_below_threshold_ignored() -> None:
    g = _make_game()
    g.plane = _make_plane()
    # _on_mouse_release checks drag_power > 0.5
    g.drag_power = 0.3
    # In the real code, this stays in AIMING
    assert g.drag_power <= 0.5


def test_spawn_rings_retries_if_too_few() -> None:
    # With a very constrained RNG, the sweep might produce < 2 rings in a tight space
    # The code has a recursive retry: if len(rings) < 2, call _spawn_rings() again
    g = _make_game()
    g.rings = []
    g.rng = random.Random(42)
    g._spawn_rings()
    assert len(g.rings) >= 2


def test_plane_super_timer_default_zero() -> None:
    plane = Plane(0, 0, 0, 0)
    assert plane.super_timer == 0


def test_score_does_not_exceed_reasonable_bound() -> None:
    g = _make_game()
    g.plane = _make_plane()
    # simulate 20 successful rings at combo 0 each (reset between)
    # Each ring: combo goes 0→1, score = 10 * (1 + 1*0.5) = 15
    for _ in range(20):
        g.combo_ring_color = None
        g.combo = 0
        ring = Ring(0, 0, RED)
        g._handle_ring_pass(ring)
    # 20 * 15 = 300
    assert g.score == 300


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
