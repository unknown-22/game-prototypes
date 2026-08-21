"""test_imports.py — Headless logic tests for SPACE DOCK (331_orbit_dock).

Uses the Game.__new__ bypass pattern: never calls pyxel.init/pyxel.run.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    Bay,
    FloatingText,
    Game,
    Particle,
    Phase,
    Ship,
    dock_score,
    ship_velocity,
    spawn_interval,
    spawn_speed,
)

# Raw color ints (from main.py)
WHITE = 7
RED = 8
YELLOW = 10
LIME = 11


def make_game(seed: int = 42) -> Game:
    """Create a Game bypassing pyxel.init, with deterministic RNG."""
    g = Game.__new__(Game)
    g.reset()
    g.rng = random.Random(seed)
    g.phase = Phase.PLAYING
    return g


def ship_at(g: Game, x: float, y: float, heading: float = 0.0, speed: float = 1.0) -> Ship:
    """Append a ship to g.ships at the given position and return it."""
    ship = Ship(
        x=x,
        y=y,
        heading=heading,
        speed=speed,
        fuel=float(Game.FUEL_START),
        color=WHITE,
        id=g.next_ship_id,
    )
    g.next_ship_id += 1
    g.ships.append(ship)
    return ship


# ---------------------------------------------------------------------------
# Module-level pure functions
# ---------------------------------------------------------------------------
def test_ship_velocity_right():
    vx, vy = ship_velocity(0.0, 1.0)
    assert abs(vx - 1.0) < 1e-9
    assert abs(vy - 0.0) < 1e-9


def test_ship_velocity_down():
    vx, vy = ship_velocity(90.0, 2.0)
    assert abs(vx - 0.0) < 1e-9
    assert abs(vy - 2.0) < 1e-9


def test_spawn_interval_ramps_down():
    assert spawn_interval(0) == 200
    assert spawn_interval(3600) == 50
    assert spawn_interval(100000) == 50  # floor is 50


def test_spawn_speed_ramps_up():
    assert abs(spawn_speed(0) - 0.8) < 1e-9
    assert abs(spawn_speed(1800) - 1.8) < 1e-9
    assert spawn_speed(100000) == 2.2  # cap


def test_dock_score_higher_fuel_is_more():
    assert dock_score(1800.0, 0.5) > dock_score(600.0, 0.5)
    assert dock_score(1800.0, 0.5) == 100 + 1800 // 60


# ---------------------------------------------------------------------------
# Enums and dataclasses
# ---------------------------------------------------------------------------
def test_phase_members():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_ship_dataclass_defaults():
    s = Ship(x=1.0, y=2.0, heading=0.0, speed=1.0, fuel=100.0, color=WHITE)
    assert s.trail == []
    assert s.id == 0
    assert s.color == WHITE


def test_bay_dataclass():
    b = Bay(40, 60, 16)
    assert (b.x, b.y, b.radius) == (40, 60, 16)


def test_particle_and_floating_text():
    p = Particle(0.0, 0.0, 1.0, -1.0, 10, RED)
    t = FloatingText(5.0, 5.0, "DOCKED", 45, LIME)
    assert p.life == 10 and p.color == RED
    assert t.text == "DOCKED" and t.color == LIME


# ---------------------------------------------------------------------------
# reset() state initialization
# ---------------------------------------------------------------------------
def test_reset_initializes_state():
    g = Game.__new__(Game)
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.ships == []
    assert len(g.bays) == 3
    assert g.score == 0
    assert g.lives == Game.LIVES_START
    assert g.docked == 0
    assert g.lost == 0
    assert g.frame == 0
    assert g.selected_index == -1
    assert g.best_score == 0
    assert g.game_over_reason == ""


def test_reset_preserves_best_score():
    g = Game.__new__(Game)
    g.best_score = 999
    g.reset()
    assert g.best_score == 999  # getattr guard preserves prior best


# ---------------------------------------------------------------------------
# _spawn_ship
# ---------------------------------------------------------------------------
def test_spawn_ship_adds_one_ship():
    g = make_game()
    g._spawn_ship()
    assert len(g.ships) == 1
    s = g.ships[0]
    assert s.fuel == float(Game.FUEL_START)
    assert 0.0 <= s.heading < 360.0
    assert s.id == 0


def test_spawn_ship_at_edge():
    g = make_game()
    g._spawn_ship()
    s = g.ships[0]
    on_edge = (
        s.x == 0.0 or s.x == float(Game.SCREEN_W)
        or s.y == 0.0 or s.y == float(Game.SCREEN_H)
    )
    assert on_edge, f"ship spawned off-edge at ({s.x}, {s.y})"


def test_spawn_ship_respects_max():
    g = make_game()
    for _ in range(Game.MAX_SHIPS):
        g._spawn_ship()
    assert len(g.ships) == Game.MAX_SHIPS
    g._spawn_ship()  # should be a no-op
    assert len(g.ships) == Game.MAX_SHIPS


# ---------------------------------------------------------------------------
# _update_ships
# ---------------------------------------------------------------------------
def test_update_ships_moves_and_drains_fuel():
    g = make_game()
    s = ship_at(g, 10.0, 100.0, heading=0.0, speed=1.0)
    g._update_ships()
    assert abs(s.x - 11.0) < 1e-9
    assert abs(s.y - 100.0) < 1e-9
    assert s.fuel == float(Game.FUEL_START - 1)
    assert len(s.trail) == 1


def test_update_ships_wraps_position():
    g = make_game()
    s = ship_at(g, float(Game.SCREEN_W) - 0.5, 100.0, heading=0.0, speed=1.0)
    g._update_ships()
    assert 0.0 <= s.x < Game.SCREEN_W  # wrapped
    assert abs(s.x - 0.5) < 1e-9


def test_update_ships_trail_capped_at_24():
    g = make_game()
    s = ship_at(g, 10.0, 100.0, heading=0.0, speed=1.0)
    for _ in range(30):
        g._update_ships()
    assert len(s.trail) <= 24


# ---------------------------------------------------------------------------
# _check_collisions
# ---------------------------------------------------------------------------
def test_collision_removes_both_and_loses_life():
    g = make_game()
    ship_at(g, 100.0, 100.0)
    ship_at(g, 104.0, 100.0)  # dist 4 < COLLIDE_DIST 8
    lives_before = g.lives
    g._check_collisions()
    assert len(g.ships) == 0
    assert g.lives == lives_before - 1
    assert g.lost == 2


def test_no_collision_when_far():
    g = make_game()
    ship_at(g, 100.0, 100.0)
    ship_at(g, 150.0, 100.0)  # dist 50 >> 8
    g._check_collisions()
    assert len(g.ships) == 2
    assert g.lives == Game.LIVES_START


# ---------------------------------------------------------------------------
# _check_fuel
# ---------------------------------------------------------------------------
def test_fuel_out_strands_ship():
    g = make_game()
    s = ship_at(g, 100.0, 100.0)
    s.fuel = 0.0
    g._check_fuel()
    assert len(g.ships) == 0
    assert g.lives == Game.LIVES_START - 1
    assert g.lost == 1


def test_fuel_positive_no_strand():
    g = make_game()
    ship_at(g, 100.0, 100.0)  # fuel = FUEL_START
    g._check_fuel()
    assert len(g.ships) == 1
    assert g.lives == Game.LIVES_START


# ---------------------------------------------------------------------------
# _check_docking
# ---------------------------------------------------------------------------
def test_dock_near_bay_slow():
    g = make_game()
    bay = g.bays[0]
    ship_at(g, float(bay.x + 3), float(bay.y + 2), speed=0.5)
    g._check_docking()
    assert len(g.ships) == 0
    assert g.docked == 1
    assert g.score > 0


def test_no_dock_when_fast():
    g = make_game()
    bay = g.bays[0]
    ship_at(g, float(bay.x + 3), float(bay.y + 2), speed=1.5)  # > DOCK_SPEED_MAX
    g._check_docking()
    assert len(g.ships) == 1
    assert g.docked == 0


def test_no_dock_when_far():
    g = make_game()
    ship_at(g, 200.0, 200.0, speed=0.5)  # far from all bays
    g._check_docking()
    assert len(g.ships) == 1
    assert g.docked == 0


# ---------------------------------------------------------------------------
# _steer_selected
# ---------------------------------------------------------------------------
def test_steer_turns_heading():
    g = make_game()
    s = ship_at(g, 100.0, 100.0, heading=0.0)
    g.selected_index = 0
    g._steer_selected(turn_left=False, turn_right=True, accel=False, decel=False)
    assert abs(s.heading - Game.TURN_RATE) < 1e-9


def test_steer_left_wraps_around_zero():
    g = make_game()
    s = ship_at(g, 100.0, 100.0, heading=0.0)
    g.selected_index = 0
    g._steer_selected(turn_left=True, turn_right=False, accel=False, decel=False)
    assert abs(s.heading - (360.0 - Game.TURN_RATE)) < 1e-9


def test_steer_throttle_changes_speed():
    g = make_game()
    s = ship_at(g, 100.0, 100.0, heading=0.0, speed=1.0)
    g.selected_index = 0
    g._steer_selected(turn_left=False, turn_right=False, accel=True, decel=False)
    assert abs(s.speed - (1.0 + Game.THROTTLE_ACCEL)) < 1e-9
    g._steer_selected(turn_left=False, turn_right=False, accel=False, decel=True)
    assert abs(s.speed - 1.0) < 1e-9


def test_steer_speed_clamped():
    g = make_game()
    s = ship_at(g, 100.0, 100.0, heading=0.0, speed=Game.SPEED_MAX)
    g.selected_index = 0
    g._steer_selected(turn_left=False, turn_right=False, accel=True, decel=False)
    assert s.speed == Game.SPEED_MAX


def test_steer_recolors_selected():
    g = make_game()
    s = ship_at(g, 100.0, 100.0)
    g.selected_index = 0
    g._steer_selected(turn_left=False, turn_right=False, accel=False, decel=False)
    assert s.color == YELLOW


def test_steer_invalid_selection_resets():
    g = make_game()
    g.selected_index = 5  # out of range
    g._steer_selected(False, False, False, False)
    assert g.selected_index == -1


# ---------------------------------------------------------------------------
# _select_at
# ---------------------------------------------------------------------------
def test_select_at_picks_nearest():
    g = make_game()
    ship_at(g, 50.0, 50.0)
    ship_at(g, 100.0, 100.0)
    g._select_at(102, 100)  # near second ship
    assert g.selected_index == 1


def test_select_at_miss_deselects():
    g = make_game()
    ship_at(g, 50.0, 50.0)
    g._select_at(200, 200)  # nowhere near
    assert g.selected_index == -1


# ---------------------------------------------------------------------------
# _check_game_over
# ---------------------------------------------------------------------------
def test_game_over_lives():
    g = make_game()
    g.lives = 0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "ALL SHIPS LOST"


def test_game_over_time_up():
    g = make_game()
    g.lives = 3
    g.frame = Game.GAME_DURATION
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "TIME UP"


def test_game_over_persists_best_score():
    g = make_game()
    g.score = 500
    g.lives = 0
    g._check_game_over()
    assert g.best_score == 500


# ---------------------------------------------------------------------------
# _count_near_misses
# ---------------------------------------------------------------------------
def test_near_miss_counts_and_scores():
    g = make_game()
    ship_at(g, 100.0, 100.0)
    ship_at(g, 110.0, 100.0)  # dist 10 < NEAR_MISS 14, > COLLIDE_DIST 8
    g._count_near_misses()
    assert g.near_misses == 1
    assert g.score == 20


def test_no_near_miss_when_far():
    g = make_game()
    ship_at(g, 100.0, 100.0)
    ship_at(g, 200.0, 100.0)
    g._count_near_misses()
    assert g.near_misses == 0
    assert g.score == 0


# ---------------------------------------------------------------------------
# Integration: full frame simulation (no pyxel input touched)
# ---------------------------------------------------------------------------
def test_full_simulation_frame_no_crash():
    g = make_game()
    g._spawn_ship()
    for _ in range(5):
        g._update_ships()
        g._check_collisions()
        g._count_near_misses()
        g._check_fuel()
        g._check_docking()
        g._update_particles()
        g._update_floating_texts()
    assert g.frame == 0  # frame is only advanced in update() via pyxel path


if __name__ == "__main__":
    # Minimal test runner (no pytest dependency in headless env)
    import traceback

    tests = [
        v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
