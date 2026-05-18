"""test_imports.py — Headless logic tests for CHAIN CROSS.

Tests game logic without initializing Pyxel (no display needed).
Uses Game.__new__ pattern to bypass pyxel.init().
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add prototype dir to path
_proto_dir = str(Path(__file__).resolve().parent)
if _proto_dir not in sys.path:
    sys.path.insert(0, _proto_dir)

import random  # noqa: E402

from main import (  # noqa: E402
    SCREEN_W, SCREEN_H, CENTER_X, CENTER_Y,
    ROAD_LEFT, ROAD_RIGHT, ROAD_TOP, ROAD_BOTTOM,
    CAR_SPEED, CAR_W, CAR_H,
    COLOR_VALS, COLOR_NAMES, NUM_COLORS,
    COMBO_THRESHOLD, SUPER_DURATION, SUPER_SCORE_MULT,
    HEAT_PER_CRASH, HEAT_DECAY_PER_PASS, HEAT_MAX,
    HEAT_SPAWN_FAST, HEAT_SPAWN_FASTER,
    SPAWN_INTERVAL_BASE, SPAWN_INTERVAL_FAST, SPAWN_INTERVAL_FASTER,
    MAX_HP,
    Direction, Car, Particle, FloatingText, Phase, Game,
)


# ── Constants ─────────────────────────────────────────────────────────────

def test_constants() -> None:
    """Verify config constants are sane."""
    assert SCREEN_W == 240
    assert SCREEN_H == 240
    assert CENTER_X == 120
    assert CENTER_Y == 120
    assert ROAD_LEFT < ROAD_RIGHT
    assert ROAD_TOP < ROAD_BOTTOM
    assert CAR_SPEED > 0
    assert NUM_COLORS == 5
    assert len(COLOR_VALS) == 5
    assert len(COLOR_NAMES) == 5
    assert COMBO_THRESHOLD == 3
    assert SUPER_DURATION == 120
    assert SUPER_SCORE_MULT == 3
    assert HEAT_PER_CRASH == 15
    assert HEAT_DECAY_PER_PASS == 2
    assert HEAT_MAX == 100
    assert HEAT_SPAWN_FAST == 70
    assert HEAT_SPAWN_FASTER == 90
    assert SPAWN_INTERVAL_BASE == 50
    assert SPAWN_INTERVAL_FAST == 30
    assert SPAWN_INTERVAL_FASTER == 18
    assert MAX_HP == 5


# ── Direction Enum ────────────────────────────────────────────────────────

def test_direction_values() -> None:
    """Verify Direction enum has all 4 directions."""
    dirs = list(Direction)
    assert len(dirs) == 4
    # Check uniqueness
    assert len({d.value for d in dirs}) == 4
    assert Direction.DOWN in Direction
    assert Direction.UP in Direction
    assert Direction.RIGHT in Direction
    assert Direction.LEFT in Direction


# ── Car Dataclass ─────────────────────────────────────────────────────────

def test_car_creation() -> None:
    """Test Car dataclass instantiation and properties."""
    car = Car(x=60.0, y=0.0, direction=Direction.DOWN, color_idx=0)
    assert car.x == 60.0
    assert car.y == 0.0
    assert car.direction == Direction.DOWN
    assert car.color_idx == 0
    assert car.color_val == COLOR_VALS[0]
    assert car.color_name == COLOR_NAMES[0]

    # is_vertical
    assert car.is_vertical is True
    car_h = Car(x=0.0, y=60.0, direction=Direction.RIGHT, color_idx=1)
    assert car_h.is_vertical is False

    # dimensions: vertical cars use CAR_H width, CAR_W height
    assert car.w == CAR_H
    assert car.h == CAR_W
    assert car_h.w == CAR_W
    assert car_h.h == CAR_H


def test_car_is_in_intersection() -> None:
    """Test intersection zone detection."""
    # Inside intersection
    car_in = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.DOWN, color_idx=0)
    assert car_in.is_in_intersection is True

    # At boundary
    car_edge = Car(x=float(ROAD_LEFT), y=float(ROAD_TOP),
                   direction=Direction.RIGHT, color_idx=1)
    assert car_edge.is_in_intersection is True

    # Outside (above)
    car_out = Car(x=CENTER_X, y=float(ROAD_TOP - 10),
                  direction=Direction.DOWN, color_idx=0)
    assert car_out.is_in_intersection is False

    # Outside (right)
    car_out2 = Car(x=float(ROAD_RIGHT + 10), y=CENTER_Y,
                   direction=Direction.LEFT, color_idx=0)
    assert car_out2.is_in_intersection is False


# ── Game State (headless via __new__) ─────────────────────────────────────

def _make_headless_game() -> Game:
    """Create a Game instance without initializing Pyxel."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g._rng = random.Random()
    g._signal_idx = 0
    g._cars = []
    g._particles = []
    g._floating_texts = []
    g._spawn_timer = 0
    g._super_timer = 0
    g._shake_frames = 0
    g._shake_intensity = 0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.hp = MAX_HP
    g.heat = 0
    g.phase = Phase.PLAYING
    g._frame = 0
    g.reset()
    return g


def test_game_reset() -> None:
    """Test reset() initializes state correctly."""
    g = _make_headless_game()
    assert g._signal_idx == 0
    assert len(g._cars) == 0
    assert len(g._particles) == 0
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.hp == MAX_HP
    assert g.heat == 0
    assert g.phase == Phase.PLAYING
    assert not g.is_super


def test_game_spawn_car() -> None:
    """Test _spawn_car creates a car at the correct edge."""
    g = _make_headless_game()

    # Spawn from top (DOWN)
    g._spawn_car(Direction.DOWN)
    assert len(g._cars) == 1
    car = g._cars[0]
    assert car.direction == Direction.DOWN
    assert car.y < 0  # spawned above screen
    assert ROAD_LEFT <= car.x <= ROAD_RIGHT
    assert 0 <= car.color_idx < NUM_COLORS

    # Spawn from left (RIGHT)
    g._spawn_car(Direction.RIGHT)
    assert len(g._cars) == 2
    car2 = g._cars[1]
    assert car2.direction == Direction.RIGHT
    assert car2.x < 0
    assert ROAD_TOP <= car2.y <= ROAD_BOTTOM


def test_game_spawn_interval() -> None:
    """Test spawn interval changes with heat."""
    g = _make_headless_game()

    assert g._spawn_interval() == SPAWN_INTERVAL_BASE

    g.heat = HEAT_SPAWN_FAST
    assert g._spawn_interval() == SPAWN_INTERVAL_FAST

    g.heat = HEAT_SPAWN_FASTER
    assert g._spawn_interval() == SPAWN_INTERVAL_FASTER


def test_signal_properties() -> None:
    """Test signal color properties."""
    g = _make_headless_game()
    assert g._signal_idx == 0
    assert g.signal_color == COLOR_VALS[0]
    assert g.signal_color_name == COLOR_NAMES[0]

    # Simulate changing signal
    g._signal_idx = 3
    assert g.signal_color == COLOR_VALS[3]
    assert g.signal_color_name == COLOR_NAMES[3]


def test_on_match_builds_combo() -> None:
    """Test that matching car builds combo and score."""
    g = _make_headless_game()
    g._signal_idx = 1  # BLUE

    car = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.DOWN, color_idx=1)
    g._on_match(car)

    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score > 0  # 10 * 1 * 1 = 10
    assert g.heat == 0  # heat decay from 0 stays 0
    assert not g.is_super  # combo < threshold

    # Second match
    car2 = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.RIGHT, color_idx=1)
    g._on_match(car2)
    assert g.combo == 2
    assert g.max_combo == 2
    assert g.score == 10 + 20  # 10*1 + 10*2

    # Third match triggers SUPER
    car3 = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.UP, color_idx=1)
    g._on_match(car3)
    assert g.combo == 3
    assert g.is_super
    assert g._super_timer == SUPER_DURATION


def test_on_match_super_multiplier() -> None:
    """Test SUPER CLEAR gives 3x score."""
    g = _make_headless_game()
    g._signal_idx = 2  # GREEN
    g.combo = 3
    g._super_timer = 60  # SUPER active

    car = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.DOWN, color_idx=2)
    g._on_match(car)
    # Score: 10 * combo(4) * 3(SUPER) = 120
    assert g.score == 120
    assert g.combo == 4


def test_on_crash_resets_combo_and_deals_damage() -> None:
    """Test that non-matching car causes crash."""
    g = _make_headless_game()
    g._signal_idx = 0  # RED
    g.combo = 5
    g.score = 200
    g._super_timer = 50

    car = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.DOWN, color_idx=2)  # GREEN
    g._on_crash(car)

    assert g.hp == MAX_HP - 1
    assert g.combo == 0
    assert g._super_timer == 0
    assert g.heat == HEAT_PER_CRASH
    assert g._shake_frames == 8


def test_game_over_on_zero_hp() -> None:
    """Test that game enters GAME_OVER phase when HP reaches 0."""
    g = _make_headless_game()
    g.hp = 1
    g._signal_idx = 0  # RED

    car = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.DOWN, color_idx=1)  # BLUE
    g._on_crash(car)
    assert g.hp == 0
    assert g.phase == Phase.GAME_OVER


def test_heat_decay_on_match() -> None:
    """Test that matching reduces heat."""
    g = _make_headless_game()
    g.heat = 20
    g._signal_idx = 0  # RED

    car = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.DOWN, color_idx=0)
    g._on_match(car)
    assert g.heat == 20 - HEAT_DECAY_PER_PASS  # 18


def test_heat_cap() -> None:
    """Test that heat doesn't exceed HEAT_MAX."""
    g = _make_headless_game()
    g.heat = HEAT_MAX - 5
    g._signal_idx = 0  # RED

    car = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.DOWN, color_idx=1)  # BLUE
    g._on_crash(car)
    assert g.heat == HEAT_MAX  # capped


def test_car_movement() -> None:
    """Test car position updates."""
    g = _make_headless_game()
    g._spawn_car(Direction.DOWN)
    car = g._cars[0]
    orig_x, orig_y = car.x, car.y

    # Simulate one update tick on the car
    car.y += CAR_SPEED
    assert car.y == orig_y + CAR_SPEED
    assert car.x == orig_x  # vertical, no x movement

    # Horizontal car
    g2 = _make_headless_game()
    g2._spawn_car(Direction.RIGHT)
    car2 = g2._cars[0]
    orig_x2, orig_y2 = car2.x, car2.y
    car2.x += CAR_SPEED
    assert car2.x == orig_x2 + CAR_SPEED
    assert car2.y == orig_y2  # horizontal, no y movement


def test_resolve_car_match() -> None:
    """Test _resolve_car calls _on_match for matching color."""
    g = _make_headless_game()
    g._signal_idx = 3  # YELLOW

    car = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.DOWN, color_idx=3)
    g._resolve_car(car)
    assert g.combo == 1
    assert g.score > 0


def test_resolve_car_crash() -> None:
    """Test _resolve_car calls _on_crash for non-matching color."""
    g = _make_headless_game()
    g._signal_idx = 3  # YELLOW
    g.combo = 3

    car = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.DOWN, color_idx=0)  # RED
    g._resolve_car(car)
    assert g.combo == 0
    assert g.hp == MAX_HP - 1


def test_update_cars_removes_intersection_cars() -> None:
    """Test that _update_cars resolves and removes cars at intersection."""
    g = _make_headless_game()
    g._signal_idx = 0  # RED

    # Place a car inside the intersection zone
    car = Car(x=CENTER_X, y=CENTER_Y, direction=Direction.DOWN, color_idx=0)
    g._cars.append(car)
    assert len(g._cars) == 1

    g._update_cars()
    assert len(g._cars) == 0  # resolved and removed


def test_particle_lifecycle() -> None:
    """Test particles expire after their life reaches 0."""
    g = _make_headless_game()
    p = Particle(x=50.0, y=50.0, vx=1.0, vy=-1.0, life=3, color=8)
    g._particles.append(p)

    # Life decrements: 3→2→1→0. At life=0, particle is removed.
    for _ in range(2):
        g._update_particles()
    assert len(g._particles) == 1  # life=1 still alive

    g._update_particles()
    assert len(g._particles) == 0  # life=0 removed


def test_floating_text_lifecycle() -> None:
    """Test floating texts expire after their life reaches 0."""
    g = _make_headless_game()
    ft = FloatingText(x=60.0, y=60.0, text="TEST", life=2, color=10)
    g._floating_texts.append(ft)

    g._update_floating_texts()
    assert len(g._floating_texts) == 1  # life=1
    g._update_floating_texts()
    assert len(g._floating_texts) == 0  # life=0 removed


def test_phase_enum() -> None:
    """Test Phase enum values."""
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_activate_super() -> None:
    """Test SUPER CLEAR activation."""
    g = _make_headless_game()
    g._signal_idx = 4  # PURPLE

    g._activate_super()
    assert g._super_timer == SUPER_DURATION
    assert g.is_super
    assert len(g._particles) > 0  # burst particles
    assert len(g._floating_texts) > 0  # "SUPER CLEAR!" text


def test_super_timer_decrement() -> None:
    """Test that super timer decrements without pyxel."""
    g = _make_headless_game()
    g._super_timer = 10

    # Simulate what update() does for super timer
    g._super_timer -= 1
    assert g._super_timer == 9
    assert g.is_super


# ── Run all ───────────────────────────────────────────────────────────────

def main() -> None:
    tests = [
        test_constants,
        test_direction_values,
        test_car_creation,
        test_car_is_in_intersection,
        test_game_reset,
        test_game_spawn_car,
        test_game_spawn_interval,
        test_signal_properties,
        test_on_match_builds_combo,
        test_on_match_super_multiplier,
        test_on_crash_resets_combo_and_deals_damage,
        test_game_over_on_zero_hp,
        test_heat_decay_on_match,
        test_heat_cap,
        test_car_movement,
        test_resolve_car_match,
        test_resolve_car_crash,
        test_update_cars_removes_intersection_cars,
        test_particle_lifecycle,
        test_floating_text_lifecycle,
        test_phase_enum,
        test_activate_super,
        test_super_timer_decrement,
    ]
    passed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  PASS: {test_fn.__name__}")
        except AssertionError as e:
            print(f"  FAIL: {test_fn.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR: {test_fn.__name__}: {type(e).__name__}: {e}")

    print(f"\n{passed}/{len(tests)} tests passed")
    if passed != len(tests):
        sys.exit(1)


if __name__ == "__main__":
    main()
