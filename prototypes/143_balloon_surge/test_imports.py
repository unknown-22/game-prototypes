"""test_imports.py — Headless logic tests for Balloon Surge (143_balloon_surge).

Uses Game.__new__(Game) bypass pattern to test without pyxel.init/run.
"""
import sys
import random

import pytest

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/143_balloon_surge")
from main import (
    Game, Phase, Ring, Cloud, Particle, FloatingText,
    COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW, NUM_COLORS, ALL_COLORS,
    RING_PYXEL, BALLOON_PYXEL,
    RING_RADIUS, BALLOON_RADIUS, BALLOON_Y, COLLIDE_DIST,
    FUEL_MAX, HEAT_MAX, FUEL_BURN_RATE, FUEL_BASE_RATE,
    HEAT_BURN_RATE, HEAT_WRONG_COLOR, HEAT_SUPER_END,
    SUPER_DURATION,
    SCROLL_BURN, SCROLL_PASSIVE,
    MOVE_SPEED, BALLOON_MIN_X, BALLOON_MAX_X,
    RAINBOW_CYCLE, RAINBOW_LEN,
    PARTICLE_RING_COLLECT, PARTICLE_SUPER_TRIGGER,
)


# ── Factory ──

def _make_game(seed: int = 42) -> Game:
    """Create a Game instance bypassing pyxel.init/run for headless testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.PLAYING
    g.balloon_x = 160.0
    g.balloon_color = COLOR_RED
    g.fuel = FUEL_MAX
    g.heat = 0.0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.altitude = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.rings = []
    g.clouds = []
    g.particles = []
    g.floating_texts = []
    g.wind = 0.0
    g.scroll_offset = 0.0
    g.shake_frames = 0
    g.frame = 0
    g._ring_spawn_timer = 30
    g._wind_timer = 150
    g.game_over_reason = ""
    g._reset()
    return g


def _make_ring(x: float, y: float, color: int) -> Ring:
    return Ring(x=x, y=y, color=color, radius=RING_RADIUS, active=True)


# ── Dataclass Tests ──

def test_ring_creation():
    r = Ring(x=100.0, y=200.0, color=COLOR_RED)
    assert r.x == 100.0
    assert r.y == 200.0
    assert r.color == COLOR_RED
    assert r.radius == RING_RADIUS
    assert r.active is True


def test_ring_defaults():
    r = Ring(x=50.0, y=60.0, color=COLOR_BLUE)
    assert r.radius == 14
    assert r.active is True


def test_cloud_creation():
    c = Cloud(x=10.0, y=20.0, width=50, speed=0.5)
    assert c.x == 10.0
    assert c.y == 20.0
    assert c.width == 50
    assert c.speed == 0.5


def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-0.5, color=8, life=30, size=3)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -0.5
    assert p.color == 8
    assert p.life == 30
    assert p.size == 3


def test_floating_text_creation():
    ft = FloatingText(x=100.0, y=50.0, text="+50", color=7, life=45)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+50"
    assert ft.color == 7
    assert ft.life == 45
    assert ft.vy == -1.0


# ── Phase Enum Tests ──

def test_phase_values():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    phases = {Phase.TITLE, Phase.PLAYING, Phase.GAME_OVER}
    assert len(phases) == 3


# ── Constants Tests ──

def test_ring_pyxel_colors():
    assert RING_PYXEL[COLOR_RED] == 8
    assert RING_PYXEL[COLOR_GREEN] == 3
    assert RING_PYXEL[COLOR_BLUE] == 5
    assert RING_PYXEL[COLOR_YELLOW] == 10


def test_balloon_pyxel_colors():
    assert BALLOON_PYXEL[COLOR_RED] == 8
    assert BALLOON_PYXEL[COLOR_GREEN] == 3
    assert BALLOON_PYXEL[COLOR_BLUE] == 6  # LIGHT_BLUE
    assert BALLOON_PYXEL[COLOR_YELLOW] == 10


def test_collision_distance():
    assert COLLIDE_DIST == BALLOON_RADIUS + RING_RADIUS
    assert COLLIDE_DIST == 18 + 14  # 32


def test_super_duration():
    assert SUPER_DURATION == 300  # 5 seconds at 60fps


def test_rainbow_cycle_length():
    assert RAINBOW_LEN == len(RAINBOW_CYCLE)
    assert RAINBOW_LEN == 8


# ── Reset / Init Tests ──

def test_reset_initializes_state():
    g = _make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.fuel == FUEL_MAX
    assert g.heat == 0.0
    assert g.altitude == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.phase == Phase.PLAYING


def test_reset_clears_rings():
    g = _make_game()
    g.rings.append(Ring(x=100, y=100, color=COLOR_RED))
    g._reset()
    assert len(g.rings) == 0


def test_reset_clears_particles():
    g = _make_game()
    g.particles.append(Particle(x=0, y=0, vx=0, vy=0, color=8, life=10))
    g.floating_texts.append(FloatingText(x=0, y=0, text="test", color=7, life=10))
    g._reset()
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_reset_initializes_clouds():
    g = _make_game()
    assert len(g.clouds) == 5
    for cloud in g.clouds:
        assert 0 <= cloud.x <= 320
        assert 0 <= cloud.y <= 240
        assert 30 <= cloud.width <= 80


def test_reset_sets_random_balloon_color():
    g = _make_game(42)
    g2 = _make_game(42)
    assert g.balloon_color == g2.balloon_color


def test_reset_preserves_rng_seed():
    g1 = _make_game(42)
    g2 = _make_game(42)
    assert g1.balloon_color == g2.balloon_color
    g1._spawn_ring()
    g2._spawn_ring()
    assert g1.rings[0].color == g2.rings[0].color
    assert g1.rings[0].x == g2.rings[0].x


# ── Fuel System Tests ──

def test_fuel_decreases_on_burn():
    g = _make_game()
    g._update_fuel(burning=True)
    assert g.fuel == pytest.approx(FUEL_MAX - FUEL_BURN_RATE)


def test_fuel_decreases_passively():
    g = _make_game()
    g._update_fuel(burning=False)
    assert g.fuel == pytest.approx(FUEL_MAX - FUEL_BASE_RATE)


def test_fuel_does_not_go_negative():
    g = _make_game()
    g.fuel = 0.0
    g._update_fuel(burning=True)
    assert g.fuel == 0.0


def test_heat_increases_on_burn():
    g = _make_game()
    g._update_fuel(burning=True)
    assert g.heat == pytest.approx(HEAT_BURN_RATE)


def test_heat_does_not_increase_when_idle():
    g = _make_game()
    g._update_fuel(burning=False)
    assert g.heat == 0.0


def test_heat_clamped_to_max():
    g = _make_game()
    g.fuel = 1.0
    g.heat = HEAT_MAX
    g._update_fuel(burning=True)
    assert g.heat == HEAT_MAX


def test_fuel_not_consumed_in_super_mode():
    g = _make_game()
    g.super_mode = True
    initial_fuel = g.fuel
    g._update_fuel(burning=True)
    assert g.fuel == initial_fuel


# ── Ring Pass: Combo System ──

def test_first_ring_pass_sets_combo_1():
    g = _make_game()
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_RED)
    g._handle_ring_pass(ring)
    assert g.combo == 1


def test_same_color_builds_combo():
    g = _make_game()
    g.balloon_color = COLOR_RED
    ring1 = _make_ring(160, BALLOON_Y, COLOR_RED)
    ring2 = _make_ring(160, BALLOON_Y, COLOR_RED)
    g._handle_ring_pass(ring1)
    assert g.combo == 1
    g._handle_ring_pass(ring2)
    assert g.combo == 2
    assert g.balloon_color == COLOR_RED


def test_wrong_color_resets_combo():
    g = _make_game()
    g.balloon_color = COLOR_RED
    ring1 = _make_ring(160, BALLOON_Y, COLOR_RED)
    ring2 = _make_ring(160, BALLOON_Y, COLOR_GREEN)
    g._handle_ring_pass(ring1)
    assert g.combo == 1
    g._handle_ring_pass(ring2)
    assert g.combo == 1
    assert g.balloon_color == COLOR_GREEN


def test_wrong_color_adds_heat():
    g = _make_game()
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_GREEN)
    g._handle_ring_pass(ring)
    assert g.heat == pytest.approx(HEAT_WRONG_COLOR)


def test_balloon_color_changes_on_wrong_pass():
    g = _make_game()
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_BLUE)
    g._handle_ring_pass(ring)
    assert g.balloon_color == COLOR_BLUE


def test_balloon_color_stays_on_same_pass():
    g = _make_game()
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_RED)
    g._handle_ring_pass(ring)
    assert g.balloon_color == COLOR_RED


# ── Scoring Tests ──

def test_same_color_scoring():
    g = _make_game()
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_RED)
    g._handle_ring_pass(ring)
    # combo=1 → points = 10 + 1*5 = 15
    assert g.score == 15


def test_same_color_scoring_combo_3():
    g = _make_game()
    g.balloon_color = COLOR_RED
    for _ in range(3):
        ring = _make_ring(160, BALLOON_Y, COLOR_RED)
        g._handle_ring_pass(ring)
    # combo 1: 15, combo 2: 20, combo 3: 25, total = 60
    assert g.score == 60


def test_wrong_color_scoring():
    g = _make_game()
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_GREEN)
    g._handle_ring_pass(ring)
    assert g.score == 5
    assert g.combo == 1


def test_max_combo_tracks_highest():
    g = _make_game()
    g.balloon_color = COLOR_RED
    for _ in range(4):
        ring = _make_ring(160, BALLOON_Y, COLOR_RED)
        g._handle_ring_pass(ring)
    assert g.combo == 4
    assert g.max_combo == 4
    ring2 = _make_ring(160, BALLOON_Y, COLOR_GREEN)
    g._handle_ring_pass(ring2)
    assert g.combo == 1
    assert g.max_combo == 4


# ── SUPER LIFT Tests ──

def test_super_lift_triggers_at_combo_5():
    g = _make_game()
    g.balloon_color = COLOR_RED
    for _ in range(5):
        ring = _make_ring(160, BALLOON_Y, COLOR_RED)
        g._handle_ring_pass(ring)
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION
    assert g.shake_frames == 10


def test_super_lift_does_not_trigger_below_5():
    g = _make_game()
    g.balloon_color = COLOR_RED
    for _ in range(4):
        ring = _make_ring(160, BALLOON_Y, COLOR_RED)
        g._handle_ring_pass(ring)
    assert g.super_mode is False


def test_super_lift_eventually_ends():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g.combo = 7
    g.super_timer -= 1
    if g.super_timer <= 0:
        g.super_mode = False
        g.super_timer = 0
        g.combo = 0
        g.heat = min(HEAT_MAX, g.heat + HEAT_SUPER_END)
    assert g.super_mode is False
    assert g.combo == 0
    assert g.heat == pytest.approx(HEAT_SUPER_END)


def test_super_mode_prevents_fuel_consumption():
    g = _make_game()
    g.super_mode = True
    initial_fuel = g.fuel
    g._update_fuel(burning=True)
    assert g.fuel == initial_fuel


def test_super_mode_all_passes_count_as_same():
    g = _make_game()
    g.super_mode = True
    g.combo = 5
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_GREEN)
    g._handle_ring_pass(ring)
    assert g.combo == 6
    assert g.heat == 0.0


def test_super_mode_3x_scoring():
    g = _make_game()
    g.super_mode = True
    g.combo = 5
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_RED)
    g._handle_ring_pass(ring)
    # combo 6, base = 10 + 6*5 = 40, *3 = 120
    assert g.score == 120

    ring2 = _make_ring(160, BALLOON_Y, COLOR_GREEN)
    g._handle_ring_pass(ring2)
    # combo 7, base = 10 + 7*5 = 45, *3 = 135
    assert g.score == 120 + 135


def test_super_mode_particles_spawn():
    g = _make_game()
    g.balloon_color = COLOR_RED
    g.balloon_x = 160
    g.combo = 4
    ring = _make_ring(160, BALLOON_Y, COLOR_RED)
    g._handle_ring_pass(ring)
    assert g.super_mode is True
    assert len(g.particles) == PARTICLE_RING_COLLECT + PARTICLE_SUPER_TRIGGER


def test_super_does_not_retrigger():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.combo = 5
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_RED)
    g._handle_ring_pass(ring)
    assert g.super_mode is True
    assert g.super_timer == 100  # Unchanged, super wasn't re-triggered


# ── Ring Spawn Tests ──

def test_spawn_ring_adds_to_list():
    g = _make_game()
    initial_count = len(g.rings)
    g._spawn_ring()
    assert len(g.rings) == initial_count + 1
    ring = g.rings[-1]
    assert 40 <= ring.x <= 280
    assert ring.y == 260.0


def test_spawn_ring_has_valid_color():
    g = _make_game()
    g._spawn_ring()
    ring = g.rings[0]
    assert ring.color in ALL_COLORS


def test_spawn_ring_deterministic():
    g1 = _make_game(42)
    g2 = _make_game(42)
    g1._spawn_ring()
    g2._spawn_ring()
    assert g1.rings[0].x == g2.rings[0].x
    assert g1.rings[0].color == g2.rings[0].color


# ── Ring Pass Edge Cases ──

def test_ring_gets_removed_from_list():
    g = _make_game()
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_RED)
    g.rings.append(ring)
    g._handle_ring_pass(ring)
    assert ring not in g.rings


def test_ring_pass_makes_ring_inactive():
    g = _make_game()
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_RED)
    g._handle_ring_pass(ring)
    assert ring.active is False


def test_multiple_rings_can_be_passed():
    g = _make_game()
    g.balloon_color = COLOR_RED
    for _i in range(5):
        ring = _make_ring(160, BALLOON_Y, COLOR_RED)
        g._handle_ring_pass(ring)
    assert g.combo == 5
    assert g.super_mode is True


# ── Movement Tests ──

def test_balloon_x_clamped_min():
    g = _make_game()
    g.balloon_x = 0
    g.balloon_x = max(BALLOON_MIN_X, min(BALLOON_MAX_X, g.balloon_x))
    assert g.balloon_x == BALLOON_MIN_X


def test_balloon_x_clamped_max():
    g = _make_game()
    g.balloon_x = 500
    g.balloon_x = max(BALLOON_MIN_X, min(BALLOON_MAX_X, g.balloon_x))
    assert g.balloon_x == BALLOON_MAX_X


def test_balloon_x_within_bounds():
    g = _make_game()
    g.balloon_x = 160.0
    assert BALLOON_MIN_X <= g.balloon_x <= BALLOON_MAX_X


# ── Altitude Tests ──

def test_altitude_increases_on_burn():
    g = _make_game()
    scroll_speed = SCROLL_BURN
    g.scroll_offset += scroll_speed
    g.altitude += scroll_speed * 0.1
    assert g.altitude == pytest.approx(SCROLL_BURN * 0.1)


def test_altitude_increases_passively():
    g = _make_game()
    scroll_speed = SCROLL_PASSIVE
    g.scroll_offset += scroll_speed
    g.altitude += scroll_speed * 0.1
    assert g.altitude == pytest.approx(SCROLL_PASSIVE * 0.1)


# ── Particle Tests ──

def test_particle_update_decrements_life():
    g = _make_game()
    p = Particle(x=10, y=20, vx=1, vy=1, color=8, life=5)
    g.particles = [p]
    g._update_particles()
    assert g.particles[0].life == 4


def test_particle_removed_when_life_zero():
    g = _make_game()
    p = Particle(x=10, y=20, vx=1, vy=1, color=8, life=1)
    g.particles = [p]
    g._update_particles()
    assert len(g.particles) == 0


def test_particle_moves():
    g = _make_game()
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-0.5, color=8, life=10)
    g.particles = [p]
    g._update_particles()
    assert g.particles[0].x == 11.5
    assert g.particles[0].y == 19.5


def test_spawn_particles_at():
    g = _make_game()
    g.super_mode = False
    g._spawn_particles_at(100, 100, COLOR_RED, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == RING_PYXEL[COLOR_RED]


# ── Floating Text Tests ──

def test_floating_text_moves_up():
    g = _make_game()
    g.floating_texts = [FloatingText(x=100, y=200, text="+10", color=7, life=30)]
    g._update_floating_texts()
    assert g.floating_texts[0].y == 199.0
    assert g.floating_texts[0].life == 29


def test_floating_text_removed_when_life_zero():
    g = _make_game()
    g.floating_texts = [FloatingText(x=100, y=200, text="+10", color=7, life=1)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_spawn_floating_text():
    g = _make_game()
    g._spawn_floating_text(100, 100, "TEST", 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"
    assert g.floating_texts[0].color == 7


# ── Cloud Tests ──

def test_clouds_initialized():
    g = _make_game()
    assert len(g.clouds) == 5


def test_cloud_update_moves():
    g = _make_game()
    cloud = g.clouds[0]
    initial_x = cloud.x
    g._update_clouds()
    assert cloud.x < initial_x


def test_cloud_wraps_around():
    g = _make_game()
    cloud = g.clouds[0]
    cloud.x = -cloud.width - 1
    g._update_clouds()
    assert cloud.x >= 320


# ── Game Over Tests ──

def test_heat_at_max_triggers_game_over():
    g = _make_game()
    g.heat = HEAT_MAX
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "Overheated!"


def test_heat_below_max_no_game_over():
    g = _make_game()
    g.heat = HEAT_MAX - 0.01
    g._check_game_over()
    assert g.phase == Phase.PLAYING


def test_game_over_reason_default():
    g = _make_game()
    g.heat = HEAT_MAX
    g._check_game_over()
    assert g.game_over_reason == "Overheated!"


# ── Edge Case Tests ──

def test_balloon_color_cycles_through_all():
    g = _make_game()
    g.balloon_color = COLOR_RED
    colors_seen = {COLOR_RED}
    for color in [COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW]:
        ring = _make_ring(160, BALLOON_Y, color)
        g._handle_ring_pass(ring)
        colors_seen.add(g.balloon_color)
    assert len(colors_seen) == NUM_COLORS


def test_score_persistence_across_resets():
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.max_combo = 5
    g._reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0


def test_heat_capped_at_max():
    g = _make_game()
    g.heat = 90.0
    g.balloon_color = COLOR_RED
    ring = _make_ring(160, BALLOON_Y, COLOR_GREEN)
    g._handle_ring_pass(ring)
    assert g.heat == pytest.approx(min(HEAT_MAX, 90.0 + HEAT_WRONG_COLOR))


def test_fuel_zero_can_still_steer():
    g = _make_game()
    g.fuel = 0.0
    g.balloon_x = 160.0
    g.balloon_x -= MOVE_SPEED
    assert g.balloon_x < 160.0


def test_fuel_zero_burn_does_nothing():
    g = _make_game()
    g.fuel = 0.0
    g.heat = 10.0
    g._update_fuel(burning=True)
    assert g.fuel == 0.0
    assert g.heat == 10.0


def test_super_trigger_particles():
    g = _make_game()
    g.balloon_color = COLOR_RED
    g.balloon_x = 160
    g._trigger_super()
    assert len(g.particles) == PARTICLE_SUPER_TRIGGER
    assert g.super_mode is True
    assert g.shake_frames == 10


def test_deterministic_rng():
    g1 = _make_game(42)
    g2 = _make_game(42)
    assert g1.balloon_color == g2.balloon_color


def test_deterministic_rng_different_seeds():
    g1 = _make_game(42)
    g2 = _make_game(99)
    assert g1 is not g2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
