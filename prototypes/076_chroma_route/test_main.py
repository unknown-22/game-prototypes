"""Tests for CHROMA ROUTE game logic."""

from __future__ import annotations

import random
import sys

sys.path.insert(0, "prototypes/076_chroma_route")
import main  # noqa: E402


def _make_game(seed: int = 42):
    g = main.Game.__new__(main.Game)
    g._init_state()
    g.phase = main.Phase.PLAYING
    g.rng = random.Random(seed)
    return g


def _make_ship(
    x: float = 160.0, y: float = 220.0, color: int = 8, target_runway: int = 0
) -> main.Ship:
    return main.Ship(x=x, y=y, color=color, target_runway=target_runway)


# ---- Test: Spawning ----
def test_spawn_interval_initial():
    g = _make_game()
    assert g._spawn_interval() == main.SPAWN_INTERVAL_INITIAL


def test_spawn_interval_decreases():
    g = _make_game()
    g.landings = 20
    assert g._spawn_interval() == main.SPAWN_INTERVAL_INITIAL - 2 * main.SPAWN_INTERVAL_DECREMENT


def test_spawn_interval_min():
    g = _make_game()
    g.landings = 1000
    assert g._spawn_interval() == main.SPAWN_INTERVAL_MIN


def test_max_ships_normal():
    g = _make_game()
    assert g._max_ships() == main.MAX_SHIPS_BASE


def test_max_ships_late():
    g = _make_game()
    g.landings = 50
    assert g._max_ships() == main.MAX_SHIPS_LATE


def test_ship_speed_normal():
    g = _make_game()
    assert g._ship_speed() == main.SHIP_SPEED_BASE


def test_ship_speed_fast():
    g = _make_game()
    g.landings = 30
    assert g._ship_speed() == main.SHIP_SPEED_FAST


def test_spawn_ship_appends_to_list():
    g = _make_game()
    assert len(g.ships) == 0
    ship = g._spawn_ship()
    assert ship is not None
    assert len(g.ships) == 1
    assert ship.alive
    assert ship.color in main.SHIP_COLORS


def test_spawn_ship_respects_max():
    g = _make_game()
    max_s = g._max_ships()
    for _ in range(max_s):
        g._spawn_ship()
    result = g._spawn_ship()
    assert result is None


# ---- Test: Ship Movement ----
def test_update_ship_moves_toward_waypoint():
    ship = _make_ship(x=100, y=100, target_runway=0)
    runway = main.Runway(x=130, y=0, w=60, h=16, color=8, side="top")
    ship.path = [(160, 50)]
    ship.path_index = 0
    ship.speed = 2.0
    main.Game._update_ship(ship, runway)
    assert ship.x > 100
    assert ship.y < 100
    assert ship.path_index == 0


def test_update_ship_advances_waypoint():
    ship = _make_ship(x=160, y=50, target_runway=0)
    runway = main.Runway(x=130, y=0, w=60, h=16, color=8, side="top")
    ship.path = [(160, 50)]
    ship.path_index = 0
    ship.speed = 2.0
    main.Game._update_ship(ship, runway)
    assert ship.path_index == 1


def test_update_ship_flies_to_runway_after_path():
    ship = _make_ship(x=100, y=100, target_runway=0)
    runway = main.Runway(x=130, y=0, w=60, h=16, color=8, side="top")
    ship.path = []
    ship.path_index = 0
    ship.speed = 2.0
    main.Game._update_ship(ship, runway)
    assert ship.y < 100


# ---- Test: Collision ----
def test_check_collisions_no_collision():
    g = _make_game()
    g.ships = [
        _make_ship(x=100, y=100),
        _make_ship(x=200, y=200),
    ]
    pairs = g._check_collisions()
    assert len(pairs) == 0


def test_check_collisions_detects():
    g = _make_game()
    g.ships = [
        _make_ship(x=100, y=100),
        _make_ship(x=105, y=105),
    ]
    pairs = g._check_collisions()
    assert len(pairs) == 1


def test_process_collision_destroys_both():
    g = _make_game()
    a = _make_ship(x=100, y=100)
    b = _make_ship(x=105, y=105)
    g.ships = [a, b]
    g.combo = 5
    g.score = 500
    g._process_collision(a, b)
    assert not a.alive
    assert not b.alive
    assert g.combo == 0
    assert g.score == 400
    assert g.collisions == 1


# ---- Test: Landing ----
def test_check_landings_detects():
    g = _make_game()
    runway = g.runways[0]
    ship = _make_ship(x=runway.cx, y=runway.cy, target_runway=0)
    g.ships = [ship]
    landed = g._check_landings()
    assert len(landed) == 1


def test_check_landings_too_far():
    g = _make_game()
    runway = g.runways[0]
    ship = _make_ship(x=runway.cx + 50, y=runway.cy + 50, target_runway=0)
    g.ships = [ship]
    landed = g._check_landings()
    assert len(landed) == 0


def test_process_landing_correct_color():
    g = _make_game()
    runway = g.runways[0]
    ship = _make_ship(x=runway.cx, y=runway.cy, color=8, target_runway=0)
    g.combo = 0
    g.score = 0
    g._process_landing(ship, runway)
    assert not ship.alive
    assert g.combo == 1
    assert g.score == 100
    assert g.landings == 1


def test_process_landing_wrong_color():
    g = _make_game()
    runway = g.runways[0]
    ship = _make_ship(x=runway.cx, y=runway.cy, color=3, target_runway=0)
    g.combo = 3
    g.score = 200
    g._process_landing(ship, runway)
    assert not ship.alive
    assert g.combo == 0
    assert g.score == 150
    assert g.mislands == 1


def test_process_landing_combo_builds():
    g = _make_game()
    runway = g.runways[0]
    g.score = 0
    for _ in range(4):
        ship = _make_ship(x=runway.cx, y=runway.cy, color=8, target_runway=0)
        g._process_landing(ship, runway)
    assert g.combo == 4
    assert g.max_combo == 4
    assert g.score == 100 + 200 + 300 + 400


# ---- Test: COMBO / SURGE ----
def test_update_combo_correct():
    g = _make_game()
    g.combo = 2
    g._update_combo(correct=True)
    assert g.combo == 3
    assert g.max_combo == 3


def test_update_combo_wrong():
    g = _make_game()
    g.combo = 4
    g.max_combo = 4
    g._update_combo(correct=False)
    assert g.combo == 0
    assert g.max_combo == 4


def test_activate_surge():
    g = _make_game()
    g._activate_surge()
    assert g.surge_timer == main.SURGE_DURATION


def test_surge_triggers_at_combo_5():
    g = _make_game()
    runway = g.runways[0]
    g.score = 0
    for _ in range(4):
        ship = _make_ship(x=runway.cx, y=runway.cy, color=8, target_runway=0)
        g._process_landing(ship, runway)
    assert g.surge_timer == 0
    ship = _make_ship(x=runway.cx, y=runway.cy, color=8, target_runway=0)
    g._process_landing(ship, runway)
    assert g.surge_timer == main.SURGE_DURATION


def test_surge_counts_wrong_as_correct():
    g = _make_game()
    g.surge_timer = 10
    runway = g.runways[0]
    ship = _make_ship(x=runway.cx, y=runway.cy, color=3, target_runway=0)
    g.combo = 2
    g.score = 0
    g._process_landing(ship, runway)
    assert g.combo == 3
    assert g.score == 100 * 3 * 2


def test_update_surge_expires():
    g = _make_game()
    g.surge_timer = 2
    g.combo = 7
    g._update_surge()
    assert g.surge_timer == 1
    assert g.combo == 7
    g._update_surge()
    assert g.surge_timer == 0
    assert g.combo == 0


# ---- Test: Waypoint recording ----
def test_add_waypoint():
    g = _make_game()
    g.drawing = True
    g.drawing_path = [(10, 10)]
    g._add_waypoint(20, 30)
    assert len(g.drawing_path) == 2
    assert g.drawing_path[1] == (20, 30)


def test_add_waypoint_clamped():
    g = _make_game()
    g.drawing = True
    g.drawing_path = []
    g._add_waypoint(-10, 300)
    assert g.drawing_path[0] == (0, 239)


# ---- Test: Initialization ----
def test_init_state():
    g = _make_game()
    assert g.phase == main.Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.surge_timer == 0
    assert g.landings == 0
    assert g.timer == main.GAME_DURATION
    assert g.drawing is False
    assert g.drawing_ship is None
    assert len(g.ships) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.runways) == 4


def test_reset():
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.ships = [_make_ship()]
    g.reset()
    assert g.phase == main.Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert len(g.ships) == 0


def test_find_ship_at():
    g = _make_game()
    ship = _make_ship(x=150, y=150)
    g.ships = [ship]
    found = g._find_ship_at(150, 150)
    assert found is ship


def test_find_ship_at_none():
    g = _make_game()
    ship = _make_ship(x=150, y=150)
    g.ships = [ship]
    found = g._find_ship_at(10, 10)
    assert found is None


def test_remove_dead_ships():
    g = _make_game()
    alive = _make_ship(x=100, y=100)
    dead = _make_ship(x=200, y=200)
    dead.alive = False
    g.ships = [alive, dead]
    g._remove_dead_ships()
    assert len(g.ships) == 1
    assert g.ships[0] is alive


def test_make_runways():
    runways = main.Game._make_runways()
    assert len(runways) == 4
    assert runways[0].side == "top"
    assert runways[1].side == "bottom"
    assert runways[2].side == "left"
    assert runways[3].side == "right"
