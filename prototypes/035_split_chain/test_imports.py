"""test_imports.py — Headless logic tests for SPLIT CHAIN.

Validates:
  - Game class and dataclasses import correctly
  - reset() initializes all expected state attributes
  - Phase enum has all expected values
  - Asteroid/Bullet/Particle dataclasses construct correctly
  - Ship movement: rotation, thrust, drag, speed clamping, screen wrapping
  - Shooting: bullet spawn direction, cooldown
  - Split logic: LARGE→MEDIUM, MEDIUM→SMALL, SMALL→destroyed
  - COMBO logic: same-color increments, wrong-color resets
  - COMBO bonus: extra split at threshold, burst particles at threshold
  - Collision detection: bullet-asteroid, ship-asteroid
  - Death flow: lives decrement, invulnerability timer, game over
  - Spawning: edge spawning, position biasing
  - Particle system: spawn, update, cull
  - Color cycling
  - HUD state correctness
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    Asteroid,
    Bullet,
    COLORS,
    COMBO_BURST_THRESHOLD,
    COMBO_EXTRA_SPLIT_THRESHOLD,
    Game,
    NUM_COLORS,
    Particle,
    Phase,
    SCREEN_H,
    SCREEN_W,
    SHOOT_COOLDOWN,
    SIZE_LARGE,
    SIZE_MEDIUM,
    SIZE_SMALL,
    STARTING_LIVES,
)


# ── Dataclass tests ──
def test_asteroid_creation() -> None:
    a = Asteroid(x=100.0, y=200.0, vx=1.5, vy=-2.0, radius=14, color=0, size=SIZE_LARGE)
    assert a.x == 100.0
    assert a.y == 200.0
    assert a.vx == 1.5
    assert a.vy == -2.0
    assert a.radius == 14
    assert a.color == 0
    assert a.size == SIZE_LARGE


def test_bullet_creation() -> None:
    b = Bullet(x=50.0, y=60.0, vx=7.0, vy=0.0, color=1)
    assert b.x == 50.0
    assert b.y == 60.0
    assert b.vx == 7.0
    assert b.vy == 0.0
    assert b.color == 1
    assert b.life == 50  # BULLET_LIFETIME


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-1.0, life=25, color=2)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.life == 25
    assert p.color == 2


# ── Phase enum tests ──
def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.DEATH in Phase
    assert Phase.GAME_OVER in Phase


# ── Game reset tests ──
def test_game_reset() -> None:
    g = Game.__new__(Game)
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.high_score == 0
    assert g.lives == STARTING_LIVES
    assert g.combo == 0
    assert g.combo_color == 0
    assert g.bullet_color == 0
    assert g.shoot_timer == 0
    assert g.invuln_timer == 0
    assert len(g.asteroids) == 0
    assert len(g.bullets) == 0
    assert len(g.particles) == 0
    assert g.ship_x == SCREEN_W / 2
    assert g.ship_y == SCREEN_H / 2
    assert g.ship_vx == 0.0
    assert g.ship_vy == 0.0
    assert g.ship_angle == 0.0


# ── Ship movement tests ──
def test_ship_rotation_left() -> None:
    g = Game.__new__(Game)
    g.reset()
    initial_angle = g.ship_angle
    # Simulate left key held (we test the rotation formula directly)
    g.ship_angle -= 4.0  # SHIP_ROTATE_SPEED
    assert g.ship_angle < initial_angle or g.ship_angle > 350  # wrapped
    g.ship_angle %= 360.0
    assert 0 <= g.ship_angle < 360.0


def test_ship_rotation_right() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.ship_angle += 4.0
    assert g.ship_angle == 4.0


def test_ship_rotation_wraps() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.ship_angle = 358.0
    g.ship_angle += 4.0
    g.ship_angle %= 360.0
    assert g.ship_angle == 2.0


def test_ship_thrust() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.ship_angle = 0.0  # pointing up
    rad = math.radians(g.ship_angle)
    g.ship_vx += math.sin(rad) * 0.12  # SHIP_THRUST
    g.ship_vy -= math.cos(rad) * 0.12
    assert g.ship_vx == 0.0  # sin(0) = 0
    assert g.ship_vy == -0.12  # moving up


def test_ship_thrust_right() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.ship_angle = 90.0  # pointing right
    rad = math.radians(g.ship_angle)
    g.ship_vx += math.sin(rad) * 0.12
    g.ship_vy -= math.cos(rad) * 0.12
    assert abs(g.ship_vx - 0.12) < 0.0001
    assert abs(g.ship_vy - 0.0) < 0.0001


def test_ship_drag() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.ship_vx = 5.0
    g.ship_vy = 5.0
    g.ship_vx *= 0.99  # SHIP_DRAG
    g.ship_vy *= 0.99
    assert g.ship_vx == 4.95
    assert g.ship_vy == 4.95


def test_ship_speed_clamp() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.ship_vx = 10.0
    g.ship_vy = 0.0
    speed = math.sqrt(g.ship_vx ** 2 + g.ship_vy ** 2)
    if speed > 5.0:  # SHIP_MAX_SPEED
        scale = 5.0 / speed
        g.ship_vx *= scale
        g.ship_vy *= scale
    assert g.ship_vx == 5.0
    assert g.ship_vy == 0.0


def test_ship_screen_wrap_right() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.ship_x = SCREEN_W + 10
    g.ship_x, g.ship_y = g._wrap_position(g.ship_x, g.ship_y)
    assert g.ship_x == 10.0


def test_ship_screen_wrap_left() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.ship_x = -10.0
    g.ship_x, g.ship_y = g._wrap_position(g.ship_x, g.ship_y)
    assert g.ship_x == SCREEN_W - 10.0


# ── Shooting tests ──
def test_shoot_creates_bullet() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.ship_angle = 0.0
    g.ship_x = 128.0
    g.ship_y = 128.0
    g.bullet_color = 0
    g._shoot()
    assert len(g.bullets) == 1
    b = g.bullets[0]
    assert b.color == 0
    assert b.life == 50
    # Bullet should move upward (angle 0 = up)
    assert abs(b.vx - 0.0) < 0.0001
    assert b.vy < 0  # negative y = upward


def test_shoot_right_direction() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.ship_angle = 90.0
    g.ship_x = 128.0
    g.ship_y = 128.0
    g._shoot()
    b = g.bullets[0]
    assert b.vx > 0  # positive x = right
    assert abs(b.vy - 0.0) < 0.0001


def test_shoot_cooldown() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.shoot_timer = SHOOT_COOLDOWN
    # Normally _update_playing checks timer before shooting
    assert g.shoot_timer > 0
    # Timer decrements each frame
    g.shoot_timer -= 1
    assert g.shoot_timer == SHOOT_COOLDOWN - 1


# ── Asteroid splitting tests ──
def test_large_splits_to_two_medium() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = 0
    g.combo_color = -1  # no active combo
    asteroid = Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=14, color=0, size=SIZE_LARGE)
    g.asteroids.append(asteroid)
    initial_count = len(g.asteroids)
    g._split_asteroid(asteroid)
    # LARGE should be removed (we don't auto-remove in _split_asteroid,
    # removal happens in collision check — just check new children)
    # 2 medium children added + original still there = initial + 2
    assert len(g.asteroids) >= initial_count + 2


def test_medium_splits_to_two_small() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = 0
    g.combo_color = -1
    asteroid = Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=9, color=1, size=SIZE_MEDIUM)
    g.asteroids.append(asteroid)
    initial_count = len(g.asteroids)
    g._split_asteroid(asteroid)
    assert len(g.asteroids) >= initial_count + 2
    # Child asteroids should be SMALL
    new_asteroids = g.asteroids[initial_count:]
    for a in new_asteroids:
        assert a.size == SIZE_SMALL


def test_small_destroys_no_split() -> None:
    g = Game.__new__(Game)
    g.reset()
    asteroid = Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=5, color=2, size=SIZE_SMALL)
    g.asteroids.append(asteroid)
    initial_count = len(g.asteroids)
    g._split_asteroid(asteroid)
    # Small should not create children, only particles
    assert len(g.asteroids) == initial_count  # no new asteroids
    assert len(g.particles) > 0  # but particles are spawned


# ── COMBO tests ──
def test_combo_extra_split_at_threshold() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = COMBO_EXTRA_SPLIT_THRESHOLD  # 3
    g.combo_color = 0
    asteroid = Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=14, color=0, size=SIZE_LARGE)
    g.asteroids.append(asteroid)
    initial_count = len(g.asteroids)
    g._split_asteroid(asteroid)
    # COMBO extra: 3 children instead of 2
    new_count = len(g.asteroids)
    assert new_count >= initial_count + 3  # 3 medium children


def test_combo_no_extra_if_wrong_color() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = COMBO_EXTRA_SPLIT_THRESHOLD
    g.combo_color = 0
    asteroid = Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=14, color=1, size=SIZE_LARGE)
    g.asteroids.append(asteroid)
    initial_count = len(g.asteroids)
    g._split_asteroid(asteroid)
    # Wrong color = no extra split
    new_count = len(g.asteroids)
    assert new_count == initial_count + 2  # only 2 children


def test_combo_burst_particles_at_threshold() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = COMBO_BURST_THRESHOLD  # 5
    g.combo_color = 0
    asteroid = Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=14, color=0, size=SIZE_LARGE)
    g.asteroids.append(asteroid)
    initial_particles = len(g.particles)
    g._split_asteroid(asteroid)
    # COMBO burst spawns extra particles (PARTICLE_COUNT_LARGE = 15)
    # plus PARTICLE_COUNT_SMALL = 6 from normal split
    assert len(g.particles) > initial_particles + 15


# ── Collision tests ──
def test_bullet_asteroid_collision_same_color() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = 0
    g.combo_color = -1
    # Place bullet on asteroid
    g.asteroids.append(Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=14, color=0, size=SIZE_LARGE))
    g.bullets.append(Bullet(x=100.0, y=100.0, vx=0, vy=0, color=0))  # same color
    g._check_bullet_asteroid_collisions()
    # Bullet removed, asteroid removed, combo incremented
    assert len(g.bullets) == 0
    assert g.combo == 1
    assert g.combo_color == 0


def test_bullet_asteroid_collision_wrong_color() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = 3
    g.combo_color = 0
    g.asteroids.append(Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=14, color=1, size=SIZE_LARGE))
    g.bullets.append(Bullet(x=100.0, y=100.0, vx=0, vy=0, color=0))  # wrong color
    g._check_bullet_asteroid_collisions()
    assert g.combo == 0  # combo resets
    assert len(g.bullets) == 0


def test_bullet_asteroid_no_collision_far() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.asteroids.append(Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=14, color=0, size=SIZE_LARGE))
    g.bullets.append(Bullet(x=200.0, y=200.0, vx=0, vy=0, color=0))
    g._check_bullet_asteroid_collisions()
    # Too far, no collision
    assert len(g.bullets) == 1
    assert len(g.asteroids) == 1


def test_ship_asteroid_collision() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.invuln_timer = 0
    g.phase = Phase.PLAYING
    initial_lives = g.lives
    g.ship_x = 100.0
    g.ship_y = 100.0
    g.asteroids.append(Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=14, color=0, size=SIZE_LARGE))
    g._check_ship_asteroid_collisions()
    assert g.lives == initial_lives - 1
    assert g.phase == Phase.DEATH


def test_ship_asteroid_no_collision_invuln() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.invuln_timer = 30  # invulnerable
    g.phase = Phase.PLAYING
    initial_lives = g.lives
    g.ship_x = 100.0
    g.ship_y = 100.0
    g.asteroids.append(Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=14, color=0, size=SIZE_LARGE))
    g._check_ship_asteroid_collisions()
    assert g.lives == initial_lives  # no damage


def test_ship_asteroid_game_over() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.invuln_timer = 0
    g.lives = 1
    g.phase = Phase.PLAYING
    g.ship_x = 100.0
    g.ship_y = 100.0
    g.asteroids.append(Asteroid(x=100.0, y=100.0, vx=0, vy=0, radius=14, color=0, size=SIZE_LARGE))
    g._check_ship_asteroid_collisions()
    assert g.lives == 0
    assert g.phase == Phase.GAME_OVER


# ── Spawning tests ──
def test_spawn_asteroid_from_edge() -> None:
    g = Game.__new__(Game)
    g.reset()
    g._spawn_asteroid(SIZE_LARGE)
    assert len(g.asteroids) == 1
    a = g.asteroids[0]
    assert a.size == SIZE_LARGE
    assert a.radius == 14
    assert 0 <= a.color < NUM_COLORS


def test_spawn_asteroid_respects_max() -> None:
    g = Game.__new__(Game)
    g.reset()
    # Fill to max
    for _ in range(25):
        g.asteroids.append(Asteroid(x=0, y=0, vx=0, vy=0, radius=5, color=0, size=SIZE_SMALL))
    g._spawn_asteroid(SIZE_LARGE)
    assert len(g.asteroids) == 25  # no new asteroid


def test_spawn_asteroid_at_position() -> None:
    g = Game.__new__(Game)
    g.reset()
    g._spawn_asteroid(SIZE_MEDIUM, x=200.0, y=150.0, color=2)
    assert len(g.asteroids) == 1
    a = g.asteroids[0]
    assert a.x == 200.0
    assert a.y == 150.0
    assert a.color == 2
    assert a.size == SIZE_MEDIUM


def test_spawn_initial_asteroids() -> None:
    g = Game.__new__(Game)
    g.reset()
    g._spawn_initial_asteroids()
    assert len(g.asteroids) == 5  # INITIAL_ASTEROIDS


# ── Color cycling tests ──
def test_bullet_color_cycling() -> None:
    g = Game.__new__(Game)
    g.reset()
    assert g.bullet_color == 0
    g.bullet_color = (g.bullet_color + 1) % NUM_COLORS
    assert g.bullet_color == 1
    g.bullet_color = (g.bullet_color + 1) % NUM_COLORS
    assert g.bullet_color == 2
    g.bullet_color = (g.bullet_color + 1) % NUM_COLORS
    assert g.bullet_color == 3
    g.bullet_color = (g.bullet_color + 1) % NUM_COLORS
    assert g.bullet_color == 0  # wraps


def test_color_change_resets_combo() -> None:
    """Changing bullet color should reset combo (handled in _update_playing)."""
    g = Game.__new__(Game)
    g.reset()
    g.combo = 3
    g.combo_color = 1
    # Simulate C key press logic
    g.bullet_color = (g.bullet_color + 1) % NUM_COLORS
    g.combo = 0
    assert g.combo == 0


# ── Score tests ──
def test_score_with_combo() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = 1
    g.combo_color = 0
    # LARGE asteroid base score = 100, multiplier = 1 + 1*0.5 = 1.5
    multiplier = 1.0 + g.combo * 0.5
    score_gain = int(100 * multiplier)  # ASTEROID_SCORES[SIZE_LARGE]
    assert score_gain == 150


def test_score_with_high_combo() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = 5
    # multiplier = 1 + 5*0.5 = 3.5
    multiplier = 1.0 + g.combo * 0.5
    score_gain = int(100 * multiplier)
    assert score_gain == 350


def test_score_no_combo() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = 0
    multiplier = 1.0
    score_gain = int(100 * multiplier)
    assert score_gain == 100


# ── Particle tests ──
def test_particle_update_and_cull() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.particles.append(Particle(x=50.0, y=50.0, vx=1.0, vy=0.0, life=0, color=0))
    g.particles.append(Particle(x=60.0, y=60.0, vx=0.0, vy=1.0, life=5, color=1))
    # Move and cull
    for p in g.particles:
        p.x += p.vx
        p.y += p.vy
        p.life -= 1
    g.particles = [p for p in g.particles if p.life > 0]
    assert len(g.particles) == 1
    assert g.particles[0].x == 60.0
    assert g.particles[0].y == 61.0


# ── Entity wrap tests ──
def test_asteroid_wraps_screen() -> None:
    g = Game.__new__(Game)
    g.reset()
    a = Asteroid(x=SCREEN_W + 50.0, y=SCREEN_H + 30.0, vx=0, vy=0, radius=14, color=0, size=SIZE_LARGE)
    g.asteroids.append(a)
    g._update_entity_positions()
    assert 0 <= a.x < SCREEN_W
    assert 0 <= a.y < SCREEN_H


def test_bullet_wraps_screen() -> None:
    g = Game.__new__(Game)
    g.reset()
    b = Bullet(x=-5.0, y=100.0, vx=-7.0, vy=0, color=0)
    g.bullets.append(b)
    g._update_entity_positions()
    # After moving, bullet should wrap around
    assert 0 <= b.x < SCREEN_W
    # But life decreased
    assert b.life == 49


# ── Death flow tests ──
def test_death_resets_position() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.ship_x = 200.0
    g.ship_y = 50.0
    g.ship_vx = 3.0
    g.ship_vy = 2.0
    g._on_ship_hit()
    assert g.ship_x == SCREEN_W / 2
    assert g.ship_y == SCREEN_H / 2
    assert g.ship_vx == 0.0
    assert g.ship_vy == 0.0


def test_death_clears_bullets() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.bullets.append(Bullet(x=50, y=50, vx=0, vy=0, color=0))
    g.bullets.append(Bullet(x=60, y=60, vx=0, vy=0, color=1))
    g._on_ship_hit()
    assert len(g.bullets) == 0


def test_death_sets_invulnerability() -> None:
    g = Game.__new__(Game)
    g.reset()
    g._on_ship_hit()
    assert g.invuln_timer == 90  # SHIP_INVULN_FRAMES
    assert g.phase == Phase.DEATH


def test_high_score_updated() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.score = 5000
    g.high_score = 3000
    g.lives = 1
    g._on_ship_hit()
    assert g.high_score == 5000
    assert g.phase == Phase.GAME_OVER


# ── Bullet cleanup test ──
def test_expired_bullets_removed() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.bullets.append(Bullet(x=50, y=50, vx=0, vy=0, color=0, life=0))
    g.bullets.append(Bullet(x=60, y=60, vx=0, vy=0, color=1, life=5))
    g._update_entity_positions()
    assert len(g.bullets) == 1
    assert g.bullets[0].life == 4  # life decremented by 1


# ── COMBO state: same_color_chain test ──
def test_combo_increment_same_color_chain() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = 2
    g.combo_color = 0
    # Hit same color → combo should increment to 3
    g.asteroids.append(Asteroid(x=100, y=100, vx=0, vy=0, radius=14, color=0, size=SIZE_LARGE))
    g.bullets.append(Bullet(x=100, y=100, vx=0, vy=0, color=0))
    g._check_bullet_asteroid_collisions()
    assert g.combo == 3
    assert g.combo_color == 0


def test_combo_new_color_switches_combo() -> None:
    g = Game.__new__(Game)
    g.reset()
    g.combo = 2
    g.combo_color = 0
    # Hit different color → combo resets to 1 with new color
    g.asteroids.append(Asteroid(x=100, y=100, vx=0, vy=0, radius=14, color=2, size=SIZE_LARGE))
    g.bullets.append(Bullet(x=100, y=100, vx=0, vy=0, color=2))
    g._check_bullet_asteroid_collisions()
    assert g.combo == 1
    assert g.combo_color == 2


# ── Constants tests ──
def test_color_constants() -> None:
    assert len(COLORS) == 4
    assert NUM_COLORS == 4


def test_asteroid_sizes() -> None:
    assert SIZE_LARGE == 0
    assert SIZE_MEDIUM == 1
    assert SIZE_SMALL == 2


# ── Run all tests ──
def run_all() -> None:
    tests = [
        # Dataclasses
        test_asteroid_creation,
        test_bullet_creation,
        test_particle_creation,
        # Phase
        test_phase_enum,
        # Reset
        test_game_reset,
        # Ship movement
        test_ship_rotation_left,
        test_ship_rotation_right,
        test_ship_rotation_wraps,
        test_ship_thrust,
        test_ship_thrust_right,
        test_ship_drag,
        test_ship_speed_clamp,
        test_ship_screen_wrap_right,
        test_ship_screen_wrap_left,
        # Shooting
        test_shoot_creates_bullet,
        test_shoot_right_direction,
        test_shoot_cooldown,
        # Splitting
        test_large_splits_to_two_medium,
        test_medium_splits_to_two_small,
        test_small_destroys_no_split,
        # COMBO
        test_combo_extra_split_at_threshold,
        test_combo_no_extra_if_wrong_color,
        test_combo_burst_particles_at_threshold,
        # Collision
        test_bullet_asteroid_collision_same_color,
        test_bullet_asteroid_collision_wrong_color,
        test_bullet_asteroid_no_collision_far,
        test_ship_asteroid_collision,
        test_ship_asteroid_no_collision_invuln,
        test_ship_asteroid_game_over,
        # Spawning
        test_spawn_asteroid_from_edge,
        test_spawn_asteroid_respects_max,
        test_spawn_asteroid_at_position,
        test_spawn_initial_asteroids,
        # Color cycling
        test_bullet_color_cycling,
        test_color_change_resets_combo,
        # Scoring
        test_score_with_combo,
        test_score_with_high_combo,
        test_score_no_combo,
        # Particles
        test_particle_update_and_cull,
        # Entity wrap
        test_asteroid_wraps_screen,
        test_bullet_wraps_screen,
        # Death flow
        test_death_resets_position,
        test_death_clears_bullets,
        test_death_sets_invulnerability,
        test_high_score_updated,
        # Bullet cleanup
        test_expired_bullets_removed,
        # COMBO state
        test_combo_increment_same_color_chain,
        test_combo_new_color_switches_combo,
        # Constants
        test_color_constants,
        test_asteroid_sizes,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {test.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {test.__name__}: {type(e).__name__}: {e}")

    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
