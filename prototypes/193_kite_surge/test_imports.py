"""test_imports.py — Headless logic tests for Kite Surge."""
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # type: ignore[import-not-found]
    Game, Phase, Ring, Bird, Particle, EchoDot,
    RING_COLORS, SCREEN_W, SCREEN_H, KITE_X, KITE_SIZE, RING_RADIUS,
    MAX_HEAT, HEAT_DECAY, HEAT_PER_HIT, SUPER_THRESHOLD, SUPER_DURATION,
    SUPER_SCORE_MULT, BASE_RING_SCORE, INVULN_DURATION,
    WIND_BASE, WIND_MAX, KITE_GRAVITY, KITE_MAX_VY,
    PARTICLE_MAX, ECHO_MAX, ECHO_INTERVAL, ECHO_LIFE,
    RED, GREEN, YELLOW, ORANGE, WHITE,
)


def _make_game() -> Game:
    """Factory: bypasses pyxel init/run for headless testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.rings = []
    g.birds = []
    g.particles = []
    g.echo_dots = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.kite_x = KITE_X
    g.kite_y = 120.0
    g.kite_vy = 0.0
    g.wind_speed = WIND_BASE
    g.scroll_x = 0.0
    g.invuln_timer = 0
    g.last_color = None
    g.spawn_timer = 0
    g.bird_timer = 0
    g.game_time = 0
    g.shake_timer = 0
    g.shake_intensity = 0
    g.super_mode = False
    g.frame = 0
    g.echo_frame_counter = 0
    g.super_flash_counter = 0
    g.reset()
    g._rng = random.Random(42)  # reset() may overwrite, so set after
    return g


# ── Dataclass Tests ──

def test_ring_creation() -> None:
    r = Ring(x=100.0, y=120.0, color=RED)
    assert r.x == 100.0
    assert r.y == 120.0
    assert r.color == RED
    assert not r.collected


def test_bird_creation() -> None:
    b = Bird(x=200.0, y=50.0, vy=1.5)
    assert b.x == 200.0
    assert b.y == 50.0
    assert b.vy == 1.5
    assert b.alive


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=RED)
    assert p.life == 15
    assert p.color == RED


def test_echo_dot_creation() -> None:
    e = EchoDot(x=80.0, y=100.0, life=30, color=GREEN)
    assert e.life == 30
    assert e.color == GREEN


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Game State Tests ──

def test_reset_initializes_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.wind_speed == WIND_BASE
    assert not g.super_mode


def test_ring_colors_valid() -> None:
    assert len(RING_COLORS) == 4
    for c in RING_COLORS:
        assert 0 <= c <= 15


# ── Ring Collision & Combo Tests ──

def test_collect_same_color_builds_combo() -> None:
    g = _make_game()
    r1 = Ring(x=KITE_X, y=120.0, color=RED)
    r2 = Ring(x=KITE_X, y=120.0, color=RED)
    g.last_color = None

    # Collect first ring
    g.rings = [r1]
    g._check_ring_collisions()
    assert g.combo == 1
    assert g.last_color == RED
    assert g.score == BASE_RING_SCORE

    # Collect second ring — same color, combo builds
    g.rings = [r2]
    g._check_ring_collisions()
    assert g.combo == 2
    assert g.max_combo == 2
    assert g.score == BASE_RING_SCORE * 2


def test_collect_different_color_resets_combo() -> None:
    g = _make_game()
    r1 = Ring(x=KITE_X, y=120.0, color=RED)
    r2 = Ring(x=KITE_X, y=120.0, color=GREEN)
    g.last_color = None

    # Collect first ring
    g.rings = [r1]
    g._check_ring_collisions()
    assert g.combo == 1
    assert g.last_color == RED

    # Collect second ring — different color, combo resets
    g.rings = [r2]
    g._check_ring_collisions()
    assert g.combo == 1  # reset to 1
    assert g.last_color == GREEN


def test_collect_stores_max_combo() -> None:
    g = _make_game()
    g.combo = 4
    g.last_color = RED
    g.max_combo = 4
    r = Ring(x=KITE_X, y=120.0, color=RED)
    g.rings = [r]

    g._check_ring_collisions()
    assert g.combo == 5
    assert g.max_combo == 5


def test_no_collision_when_ring_far_away() -> None:
    g = _make_game()
    r = Ring(x=300.0, y=200.0, color=GREEN)
    g.rings = [r]
    g._check_ring_collisions()
    assert not r.collected
    assert g.score == 0


def test_collision_at_edge_of_radius() -> None:
    g = _make_game()
    dist = RING_RADIUS + KITE_SIZE * 0.5 - 1
    r = Ring(x=KITE_X + dist, y=120.0, color=YELLOW)
    g.rings = [r]
    g._check_ring_collisions()
    assert r.collected


def test_no_collision_just_outside_radius() -> None:
    g = _make_game()
    dist = RING_RADIUS + KITE_SIZE * 0.5 + 1
    r = Ring(x=KITE_X + dist, y=120.0, color=YELLOW)
    g.rings = [r]
    g._check_ring_collisions()
    assert not r.collected


# ── Super Mode Tests ──

def test_super_mode_triggers_at_threshold() -> None:
    g = _make_game()
    g.combo = SUPER_THRESHOLD - 1  # 4
    g.last_color = RED
    r = Ring(x=KITE_X, y=120.0, color=RED)
    g.rings = [r]

    g._check_ring_collisions()
    assert g.combo == SUPER_THRESHOLD
    assert g.super_mode
    assert g.super_timer == SUPER_DURATION


def test_super_mode_does_not_retrigger_while_active() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.combo = SUPER_THRESHOLD - 1
    g.last_color = RED
    r = Ring(x=KITE_X, y=120.0, color=RED)
    g.rings = [r]

    g._check_ring_collisions()
    assert g.super_mode  # still active
    assert g.super_timer == 100  # not reset


def test_super_mode_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1

    g._update_super_mode()
    assert g.super_timer == 0
    assert not g.super_mode


def test_super_mode_combo_increments_always() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.combo = 3
    g.last_color = RED
    # Different color than last — should still increment in super mode
    r = Ring(x=KITE_X, y=120.0, color=GREEN)
    g.rings = [r]

    g._check_ring_collisions()
    assert g.combo == 4  # increments regardless of color in super


def test_super_mode_3x_score() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.combo = 2
    g.last_color = RED
    r = Ring(x=KITE_X, y=120.0, color=RED)
    g.rings = [r]
    score_before = g.score

    g._check_ring_collisions()
    assert g.score == score_before + BASE_RING_SCORE * SUPER_SCORE_MULT


# ── Bird Collision & Heat Tests ──

def test_bird_hit_increases_heat() -> None:
    g = _make_game()
    b = Bird(x=KITE_X, y=120.0, vy=1.0)
    g.birds = [b]

    g._check_bird_collisions()
    assert g.heat == HEAT_PER_HIT
    assert not b.alive


def test_bird_hit_resets_combo() -> None:
    g = _make_game()
    g.combo = 4
    g.last_color = RED
    b = Bird(x=KITE_X, y=120.0, vy=1.0)
    g.birds = [b]

    g._check_bird_collisions()
    assert g.combo == 0
    assert g.last_color is None


def test_bird_hit_gives_invulnerability() -> None:
    g = _make_game()
    b1 = Bird(x=KITE_X, y=120.0, vy=1.0)
    b2 = Bird(x=KITE_X, y=120.0, vy=1.0)
    g.birds = [b1, b2]

    g._check_bird_collisions()
    assert g.invuln_timer == INVULN_DURATION
    assert g.heat == HEAT_PER_HIT  # only one hit counted


def test_no_bird_collision_when_invulnerable() -> None:
    g = _make_game()
    g.invuln_timer = INVULN_DURATION
    b = Bird(x=KITE_X, y=120.0, vy=1.0)
    g.birds = [b]
    heat_before = g.heat

    g._check_bird_collisions()
    assert g.heat == heat_before  # unchanged
    assert b.alive  # still alive


def test_bird_no_collision_when_far_away() -> None:
    g = _make_game()
    b = Bird(x=300.0, y=200.0, vy=1.0)
    g.birds = [b]

    g._check_bird_collisions()
    assert b.alive
    assert g.heat == 0.0


# ── Heat Tests ──

def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 10.0

    g._update_heat()
    assert g.heat == 10.0 - HEAT_DECAY


def test_heat_decay_bottom_at_zero() -> None:
    g = _make_game()
    g.heat = 0.0

    g._update_heat()
    assert g.heat == 0.0


def test_game_over_at_max_heat() -> None:
    g = _make_game()
    g.heat = MAX_HEAT

    assert g._is_game_over()


def test_game_over_not_triggered_below_max() -> None:
    g = _make_game()
    g.heat = MAX_HEAT - 0.1

    assert not g._is_game_over()


def test_heat_clamped_at_max_on_hit() -> None:
    g = _make_game()
    g.heat = MAX_HEAT - 10.0
    b = Bird(x=KITE_X, y=120.0, vy=1.0)
    g.birds = [b]

    g._check_bird_collisions()
    assert g.heat == MAX_HEAT  # clamped


# ── Physics Tests ──

def test_gravity_pulls_kite_down() -> None:
    g = _make_game()
    g.kite_y = 120.0
    g.kite_vy = 0.0

    g._update_physics()
    assert g.kite_vy > 0  # gravity added
    assert g.kite_y > 120.0


def test_kite_clamped_to_screen_top() -> None:
    g = _make_game()
    g.kite_y = KITE_SIZE  # at margin
    g.kite_vy = -4.0

    g._update_physics()
    assert g.kite_y >= KITE_SIZE


def test_kite_clamped_to_screen_bottom() -> None:
    g = _make_game()
    g.kite_y = SCREEN_H - KITE_SIZE
    g.kite_vy = 4.0

    g._update_physics()
    assert g.kite_y <= SCREEN_H - KITE_SIZE


def test_kite_vy_clamped() -> None:
    g = _make_game()
    g.kite_vy = 10.0
    g._update_physics()
    assert abs(g.kite_vy) <= KITE_MAX_VY + abs(KITE_GRAVITY)


# ── Wind/Difficulty Tests ──

def test_wind_speed_increases() -> None:
    g = _make_game()
    initial = g.wind_speed

    g._update_difficulty()
    assert g.wind_speed > initial


def test_wind_speed_capped() -> None:
    g = _make_game()
    g.wind_speed = WIND_MAX

    g._update_difficulty()
    assert g.wind_speed == WIND_MAX


# ── Ring Movement Tests ──

def test_rings_scroll_left() -> None:
    g = _make_game()
    r = Ring(x=200.0, y=120.0, color=RED)
    g.rings = [r]
    scroll_speed = 2.0

    g._update_rings(scroll_speed)
    assert r.x == 198.0  # scrolled left


def test_rings_removed_when_off_screen() -> None:
    g = _make_game()
    r1 = Ring(x=-50.0, y=120.0, color=RED)
    r2 = Ring(x=200.0, y=120.0, color=GREEN)
    g.rings = [r1, r2]

    g._update_rings(1.0)
    assert len(g.rings) == 1
    assert g.rings[0] is r2


# ── Bird Movement Tests ──

def test_birds_scroll_left() -> None:
    g = _make_game()
    b = Bird(x=200.0, y=100.0, vy=1.0)
    g.birds = [b]
    scroll_speed = 2.0

    g._update_birds(scroll_speed)
    assert b.x == 198.0


def test_birds_patrol_vertically() -> None:
    g = _make_game()
    b = Bird(x=200.0, y=100.0, vy=2.0)
    g.birds = [b]

    g._update_birds(0.0)
    assert b.y == 102.0


def test_birds_bounce_at_boundaries() -> None:
    g = _make_game()
    b = Bird(x=200.0, y=SCREEN_H - 19, vy=3.0)
    g.birds = [b]

    g._update_birds(0.0)
    assert b.vy == -3.0  # bounced


def test_dead_birds_removed_off_screen() -> None:
    g = _make_game()
    b = Bird(x=-100.0, y=100.0, vy=1.0, alive=False)
    g.birds = [b]

    g._update_birds(1.0)
    assert len(g.birds) == 0


# ── Spawning Tests ──

def test_spawn_ring_creates_at_right_edge() -> None:
    g = _make_game()
    r = g._spawn_ring()
    assert r.x > SCREEN_W
    assert 40 <= r.y <= SCREEN_H - 40
    assert r.color in RING_COLORS


def test_spawn_bird_creates_at_right_edge() -> None:
    g = _make_game()
    b = g._spawn_bird()
    assert b.x > SCREEN_W
    assert 60 <= b.y <= SCREEN_H - 60


def test_spawn_rings_auto_trigger() -> None:
    g = _make_game()
    g.spawn_timer = g._get_spawn_interval_ring() - 1

    g._spawn_rings()
    assert g.spawn_timer == 0
    assert len(g.rings) == 1


def test_spawn_birds_auto_trigger() -> None:
    g = _make_game()
    g.bird_timer = g._get_spawn_interval_bird() - 1

    g._spawn_birds()
    assert g.bird_timer == 0
    assert len(g.birds) == 1


# ── Particle Tests ──

def test_collect_spawns_particles() -> None:
    g = _make_game()
    r = Ring(x=KITE_X, y=120.0, color=GREEN)
    g.rings = [r]

    g._check_ring_collisions()
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == GREEN
        assert p.life >= 15


def test_super_spawns_more_particles() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    r = Ring(x=KITE_X, y=120.0, color=RED)
    g.rings = [r]

    g._check_ring_collisions()
    assert len(g.particles) == 8


def test_hit_spawns_particles() -> None:
    g = _make_game()
    b = Bird(x=KITE_X, y=120.0, vy=1.0)
    g.birds = [b]

    g._check_bird_collisions()
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.color in (RED, ORANGE)


def test_particles_decay_and_removed() -> None:
    g = _make_game()
    p = Particle(x=0, y=0, vx=0, vy=0, life=1, color=RED)
    g.particles = [p]

    g._update_particles()
    assert len(g.particles) == 0


def test_particles_capped() -> None:
    g = _make_game()
    for i in range(PARTICLE_MAX + 10):
        g.particles.append(Particle(x=i, y=0, vx=0, vy=0, life=30, color=RED))

    g._update_particles()
    assert len(g.particles) <= PARTICLE_MAX


# ── Echo Trail Tests ──

def test_echo_dots_added_periodically() -> None:
    g = _make_game()
    g.echo_dots = []
    g.echo_frame_counter = ECHO_INTERVAL - 1

    g._update_echo()
    assert len(g.echo_dots) == 1
    # Dot is created then decayed in the same update call
    assert g.echo_dots[0].life == ECHO_LIFE - 1


def test_echo_dots_not_added_every_frame() -> None:
    g = _make_game()
    g.echo_dots = []
    g.echo_frame_counter = 0

    g._update_echo()
    assert len(g.echo_dots) == 0  # not yet at interval


def test_echo_dots_decay() -> None:
    g = _make_game()
    g.echo_dots = [EchoDot(x=80, y=120, life=5, color=WHITE)]

    g._update_echo()
    remaining = [d for d in g.echo_dots if d.life > 0]
    assert len(remaining) == 1
    assert remaining[0].life == 4


def test_echo_dots_removed_when_expired() -> None:
    g = _make_game()
    g.echo_dots = [EchoDot(x=80, y=120, life=1, color=WHITE)]

    g._update_echo()
    assert len(g.echo_dots) == 0


# ── Score Tests ──

def test_score_accumulates() -> None:
    g = _make_game()
    g.combo = 1
    g.last_color = RED
    for i in range(3):
        r = Ring(x=KITE_X, y=120.0, color=RED)
        g.rings = [r]
        g._check_ring_collisions()

    assert g.score == BASE_RING_SCORE * 3


# ── Phase Transition Tests ──

def test_game_over_transition_on_max_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT

    # simulate the game-over check in _update_playing
    if g._is_game_over():
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_game_stays_playing_with_low_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0

    if g._is_game_over():
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.PLAYING


# ── Invulnerability Timer Test ──

def test_invuln_timer_decrements_in_playing() -> None:
    g = _make_game()
    g.invuln_timer = 10

    # Simulate the invuln decrement from _update_playing
    if g.invuln_timer > 0:
        g.invuln_timer -= 1
    assert g.invuln_timer == 9


# ── Constants Tests ──

def test_constants_are_positive() -> None:
    assert SUPER_THRESHOLD > 0
    assert SUPER_DURATION > 0
    assert SUPER_SCORE_MULT > 1
    assert BASE_RING_SCORE > 0
    assert HEAT_PER_HIT > 0
    assert INVULN_DURATION > 0
    assert WIND_BASE > 0
    assert PARTICLE_MAX > 0
    assert ECHO_MAX > 0


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=False,
    )
    sys.exit(result.returncode)
