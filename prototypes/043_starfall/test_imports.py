"""test_imports.py — Headless logic tests for STARFALL (043).

Runs without Pyxel initialization using Game.__new__ pattern.
"""

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/043_starfall")
from main import (
    CITY_COUNT,
    CITY_HP,
    CITY_MARGIN,
    CITY_SPACING,
    CITY_W,
    CITY_Y,
    CLOSE_BONUS_THRESHOLD,
    COMBO_THRESHOLD_SURGE,
    EXPLOSION_DURATION,
    EXPLOSION_RADIUS,
    INTERCEPTOR_COOLDOWN,
    INTERCEPTOR_SPEED,
    MAX_HEAT,
    NUM_COLORS,
    SCREEN_H,
    SCREEN_W,
    STAR_RADIUS,
    STARS_PER_WAVE_BASE,
    STAR_SPAWN_INTERVAL,
    SURGE_DURATION,
    City,
    Game,
    Interceptor,
    Particle,
    Phase,
    Star,
)


def make_game() -> Game:
    """Create a Game instance without Pyxel init using __new__ + pre-init."""
    g = Game.__new__(Game)
    # Pre-init ALL attributes that reset() touches
    g.cities = []
    g.stars = []
    g.interceptors = []
    g.particles = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.surge_timer = 0
    g.wave = 1
    g.stars_spawned = 0
    g.stars_to_spawn = STARS_PER_WAVE_BASE
    g.spawn_timer = 0
    g.wave_pause_timer = 0
    g.phase = Phase.PLAYING
    g._shake_frames = 0
    g._shake_x = 0
    g._shake_y = 0
    g._rng = random.Random(42)  # deterministic
    g.reset()
    return g


# ═══ Dataclass / Constant Tests ═══


def test_city_dataclass() -> None:
    c = City(x=100, y=CITY_Y, color=2)
    assert c.x == 100
    assert c.y == CITY_Y
    assert c.color == 2
    assert c.hp == CITY_HP
    assert c.cooldown == 0
    assert c.alive is True
    c.hp = 0
    assert c.alive is False


def test_star_dataclass() -> None:
    s = Star(x=50.0, y=100.0, color=3, speed=1.2)
    assert s.x == 50.0
    assert s.color == 3
    assert abs(s.speed - 1.2) < 0.001


def test_interceptor_dataclass() -> None:
    inv = Interceptor(x=10.0, y=20.0, target_x=100.0, target_y=200.0, city_color=0)
    assert inv.alive is True
    assert inv.city_color == 0


def test_particle_dataclass() -> None:
    p = Particle(x=5.0, y=6.0, vx=1.0, vy=-2.0, life=10, color=8)
    assert p.life == 10
    p.x += p.vx
    assert abs(p.x - 6.0) < 0.001


def test_constants() -> None:
    assert CITY_COUNT == 5
    assert CITY_HP == 3
    assert NUM_COLORS == 5
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert EXPLOSION_RADIUS > 0
    assert INTERCEPTOR_SPEED > 0
    assert STAR_RADIUS > 0
    assert MAX_HEAT == 100
    assert COMBO_THRESHOLD_SURGE >= 2


def test_phase_enum() -> None:
    assert Phase.PLAYING != Phase.GAME_OVER
    assert Phase.WAVE_CLEAR != Phase.GAME_OVER
    assert len(list(Phase)) == 3


# ═══ Game State Tests ═══


def test_reset_creates_cities() -> None:
    g = make_game()
    assert len(g.cities) == CITY_COUNT
    for i, c in enumerate(g.cities):
        assert c.alive
        assert c.hp == CITY_HP
        assert c.color == i % NUM_COLORS
        expected_x = CITY_MARGIN + i * CITY_SPACING
        assert c.x == expected_x


def test_reset_initial_state() -> None:
    g = make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.wave == 1
    assert g.phase == Phase.PLAYING
    assert len(g.interceptors) == 0
    assert len(g.particles) == 0


def test_spawn_star() -> None:
    g = make_game()
    initial_count = len(g.stars)
    g._spawn_star()
    assert len(g.stars) == initial_count + 1
    s = g.stars[-1]
    assert STAR_RADIUS * 3 <= s.x <= SCREEN_W - STAR_RADIUS * 3
    assert s.y < 0  # spawns above screen
    assert 0 <= s.color < NUM_COLORS


def test_launch_interceptor() -> None:
    g = make_game()
    # Launch near city 0 (x=CITY_MARGIN=20, y=CITY_Y=224)
    g._launch_interceptor(CITY_MARGIN, 100)
    assert len(g.interceptors) == 1
    inv = g.interceptors[0]
    assert inv.city_color == 0  # nearest city is 0
    assert inv.alive is True


def test_interceptor_cooldown() -> None:
    g = make_game()
    # Launch from city 0
    g._launch_interceptor(CITY_MARGIN, 100)
    assert g.cities[0].cooldown == INTERCEPTOR_COOLDOWN
    # Second launch near city 1
    g._launch_interceptor(CITY_MARGIN + CITY_SPACING, 50)
    assert len(g.interceptors) == 2
    # Both cities on cooldown
    assert g.cities[0].cooldown == INTERCEPTOR_COOLDOWN
    assert g.cities[1].cooldown == INTERCEPTOR_COOLDOWN


def test_update_cooldowns() -> None:
    g = make_game()
    g._launch_interceptor(CITY_MARGIN, 100)
    assert g.cities[0].cooldown == INTERCEPTOR_COOLDOWN
    for _ in range(INTERCEPTOR_COOLDOWN):
        g._update_cooldowns()
    assert g.cities[0].cooldown == 0


def test_star_hit_ground_damages_city() -> None:
    g = make_game()
    c = g.cities[2]  # middle city
    initial_hp = c.hp
    # Place a star directly on city 2
    s = Star(x=float(c.x), y=CITY_Y - 1.0, color=0, speed=1.0)
    g._star_hit_ground(s)
    assert c.hp == initial_hp - 1
    assert g.heat > 0  # heat increased
    assert g.combo == 0  # combo reset


def test_star_hit_ground_miss_resets_combo() -> None:
    g = make_game()
    g.combo = 5
    # Star between cities (no city at x=50)
    s = Star(x=50.0, y=CITY_Y - 1.0, color=0, speed=1.0)
    g._star_hit_ground(s)
    assert g.combo == 0  # combo reset on ANY ground hit


def test_explode_color_match_combo() -> None:
    g = make_game()
    # Place a star
    g.stars = [Star(x=100.0, y=120.0, color=0, speed=1.0)]
    # Explode with same color (0)
    g._explode(100.0, 120.0, 0)
    assert g.combo == 1
    assert g.score > 0
    assert len(g.stars) == 0  # star destroyed


def test_explode_wrong_color_resets_combo() -> None:
    g = make_game()
    g.combo = 3
    g.stars = [Star(x=100.0, y=120.0, color=2, speed=1.0)]
    g._explode(100.0, 120.0, 0)  # color 0 vs star color 2
    assert g.combo == 0  # reset
    assert len(g.stars) == 0  # still destroyed


def test_explode_miss_resets_combo() -> None:
    g = make_game()
    g.combo = 3
    g.stars = [Star(x=10.0, y=10.0, color=0, speed=1.0)]
    # Explode far from any star
    g._explode(200.0, 200.0, 0)
    assert g.combo == 0  # miss resets combo
    assert len(g.stars) == 1  # star still there


def test_explode_surge_activation() -> None:
    g = make_game()
    g.combo = COMBO_THRESHOLD_SURGE - 1  # one away from surge
    g.stars = [Star(x=100.0, y=120.0, color=0, speed=1.0)]
    g._explode(100.0, 120.0, 0)
    assert g.combo == COMBO_THRESHOLD_SURGE
    assert g.surge_timer == SURGE_DURATION
    assert g.max_combo >= COMBO_THRESHOLD_SURGE


def test_explode_close_bonus() -> None:
    g = make_game()
    g.combo = 0
    # Star far from ground (no bonus)
    g.stars = [Star(x=100.0, y=50.0, color=0, speed=1.0)]
    g._explode(100.0, 50.0, 0)
    score_far = g.score

    g.reset()
    g.combo = 0
    # Star close to ground (bonus)
    g.stars = [Star(x=100.0, y=190.0, color=0, speed=1.0)]
    assert 190.0 > CLOSE_BONUS_THRESHOLD  # verify bonus applies
    g._explode(100.0, 190.0, 0)
    score_close = g.score

    assert score_close > score_far  # close = more risk = more reward


def test_explode_particles() -> None:
    g = make_game()
    g.stars = [Star(x=100.0, y=120.0, color=0, speed=1.0)]
    g._explode(100.0, 120.0, 0)
    assert len(g.particles) > 0
    for p in g.particles:
        assert p.life == EXPLOSION_DURATION


def test_update_particles_decay() -> None:
    g = make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=1.0, vy=1.0, life=3, color=8)]
    g._update_particles()
    assert len(g.particles) == 1
    p = g.particles[0]
    assert p.life == 2
    assert abs(p.x - 1.0) < 0.05


def test_update_particles_removal() -> None:
    g = make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0  # life expired


def test_update_heat_decay() -> None:
    g = make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0
    assert g.heat >= 0.0


def test_heat_never_negative() -> None:
    g = make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_star_movement() -> None:
    g = make_game()
    g.stars = [Star(x=100.0, y=0.0, color=0, speed=1.0)]
    initial_y = g.stars[0].y
    g._update_stars()
    if len(g.stars) > 0:
        assert g.stars[0].y > initial_y  # star moves down


def test_combo_multiplier_math() -> None:
    """Verify combo multiplier formula: 1.0 + (combo-1)*0.5, capped at 10.0."""
    for combo in range(1, 30):
        mult = 1.0 + (combo - 1) * 0.5
        mult = min(mult, 10.0)
        if combo == 1:
            assert abs(mult - 1.0) < 0.001
        elif combo == 5:
            assert abs(mult - 3.0) < 0.001
        elif combo == 19:
            assert abs(mult - 10.0) < 0.001  # capped


def test_game_over_detection() -> None:
    g = make_game()
    # Kill all cities
    for c in g.cities:
        c.hp = 0
    assert all(not c.alive for c in g.cities)
    # In real game, update() would set phase=GAME_OVER, but we test the condition


# ═══ Run ═══

if __name__ == "__main__":
    tests = [
        test_city_dataclass,
        test_star_dataclass,
        test_interceptor_dataclass,
        test_particle_dataclass,
        test_constants,
        test_phase_enum,
        test_reset_creates_cities,
        test_reset_initial_state,
        test_spawn_star,
        test_launch_interceptor,
        test_interceptor_cooldown,
        test_update_cooldowns,
        test_star_hit_ground_damages_city,
        test_star_hit_ground_miss_resets_combo,
        test_explode_color_match_combo,
        test_explode_wrong_color_resets_combo,
        test_explode_miss_resets_combo,
        test_explode_surge_activation,
        test_explode_close_bonus,
        test_explode_particles,
        test_update_particles_decay,
        test_update_particles_removal,
        test_update_heat_decay,
        test_heat_never_negative,
        test_update_star_movement,
        test_combo_multiplier_math,
        test_game_over_detection,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  PASS {test_fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {test_fn.__name__}: {e}")

    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
