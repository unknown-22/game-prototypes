"""test_imports.py -- Headless logic tests for HONEY CHAIN (prototype 302).

Run standalone:  uv run python prototypes/302_honey_chain/test_imports.py
Run via pytest:  uv run pytest prototypes/302_honey_chain/test_imports.py
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (  # noqa: E402
    DARK_BLUE,
    FLOWER_COLORS,
    GRAY,
    LIME,
    RED,
    WHITE,
    YELLOW,
    FloatingText,
    Flower,
    Game,
    Particle,
    Phase,
)

GAME_TIME = 3600


def make_game() -> Game:
    """Bypass __init__ (avoids pyxel.init/run); reseed rng for determinism."""
    g = Game.__new__(Game)
    g.reset()
    g.rng = random.Random(42)
    return g


# -- Enum / dataclasses -------------------------------------------------------

def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_flower_dataclass() -> None:
    f = Flower(2, 3, RED)
    assert f.col == 2
    assert f.row == 3
    assert f.color == RED


def test_particle_dataclass() -> None:
    p = Particle(1.5, 2.5, -0.5, 0.5, 8, 10)
    assert p.x == 1.5
    assert p.y == 2.5
    assert p.vx == -0.5
    assert p.vy == 0.5
    assert p.life == 8
    assert p.color == 10


def test_floating_text_dataclass() -> None:
    t = FloatingText(3.0, 4.0, "+10", 30, 10)
    assert t.x == 3.0
    assert t.y == 4.0
    assert t.text == "+10"
    assert t.life == 30
    assert t.color == 10


# -- Geometry ---------------------------------------------------------------

def test_make_grid_pos() -> None:
    g = make_game()
    assert g._make_grid_pos(0, 0) == (Game.OX + Game.CELL // 2, Game.OY + Game.CELL // 2)
    x, y = g._make_grid_pos(9, 7)
    assert x == Game.OX + 9 * Game.CELL + Game.CELL // 2
    assert y == Game.OY + 7 * Game.CELL + Game.CELL // 2


def test_grid_fits_on_screen() -> None:
    assert Game.OX + Game.COLS * Game.CELL <= 320
    assert Game.OY + Game.ROWS * Game.CELL <= 240


# -- reset / initial state ----------------------------------------------------

def test_reset_initial_state() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == GAME_TIME
    assert g.elapsed == 0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.pollen_color is None
    assert g.game_over_reason == ""
    assert g.shake == 0
    assert len(g.flowers) == Game.INITIAL_FLOWERS
    assert g.particles == []
    assert g.floating_texts == []
    assert g.chain_log == []


def test_reset_spawns_flowers_in_distinct_cells() -> None:
    g = make_game()
    cells = {(f.col, f.row) for f in g.flowers}
    assert len(cells) == Game.INITIAL_FLOWERS  # no overlap


# -- Spawning ---------------------------------------------------------------

def test_spawn_flower_adds_one() -> None:
    g = make_game()
    before = len(g.flowers)
    g._spawn_flower()
    assert len(g.flowers) == before + 1


def test_spawn_flower_color_is_valid() -> None:
    g = make_game()
    g._spawn_flower()
    assert g.flowers[-1].color in FLOWER_COLORS


def test_spawn_flower_respects_max() -> None:
    g = make_game()
    cap = g._max_flowers()
    g.flowers = [Flower(c % 10, c // 10, RED) for c in range(cap)]
    g._spawn_flower()
    assert len(g.flowers) == cap


def test_empty_cells() -> None:
    g = make_game()
    g.flowers = [Flower(0, 0, RED)]
    empty = g._empty_cells()
    assert (0, 0) not in empty
    assert len(empty) == Game.COLS * Game.ROWS - 1


def test_flower_at() -> None:
    g = make_game()
    g.flowers = [Flower(1, 2, LIME)]
    assert g._flower_at(1, 2) is not None
    assert g._flower_at(2, 1) is None


# -- Collection / matching ----------------------------------------------------

def test_first_touch_always_matches() -> None:
    g = make_game()
    g.pollen_color = None
    f = Flower(0, 0, RED)
    g.flowers = [f]
    assert g._try_collect(f) is True
    assert g.combo == 1
    assert g.score == 10  # 10 * 1 * 1
    assert g.pollen_color == RED
    assert f not in g.flowers


def test_same_color_builds_combo() -> None:
    g = make_game()
    g.pollen_color = RED
    total = 0
    for expected in (1, 2, 3):
        f = Flower(expected, 0, RED)
        g.flowers = [f]
        assert g._try_collect(f) is True
        assert g.combo == expected
        total += 10 * expected
    assert g.score == total  # 10 + 20 + 30 = 60
    assert g.max_combo == 3


def test_wrong_color_adds_heat_and_resets_combo() -> None:
    g = make_game()
    g.pollen_color = RED
    g.combo = 3
    f = Flower(0, 0, LIME)
    g.flowers = [f]
    assert g._try_collect(f) is False
    assert g.heat == Game.HEAT_MISMATCH
    assert g.combo == 0
    assert g.pollen_color == LIME  # re-dyed by last flower
    assert f not in g.flowers


def test_super_triggers_at_combo_four() -> None:
    g = make_game()
    g.pollen_color = RED
    g.combo = 3
    f = Flower(0, 0, RED)
    g.flowers = [f]
    assert g._try_collect(f) is True
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == Game.SUPER_DURATION


def test_super_multiplies_score_by_three() -> None:
    g = make_game()
    g.super_mode = True
    g.super_timer = 10
    g.pollen_color = RED
    g.combo = 0
    f = Flower(0, 0, LIME)
    g.flowers = [f]
    assert g._try_collect(f) is True
    assert g.combo == 1
    assert g.score == 30  # 10 * 1 * 3


def test_super_matches_any_color() -> None:
    g = make_game()
    g.super_mode = True
    g.super_timer = 10
    g.pollen_color = RED
    f = Flower(0, 0, DARK_BLUE)
    g.flowers = [f]
    assert g._try_collect(f) is True


def test_collect_appends_chain_log() -> None:
    g = make_game()
    g.pollen_color = RED
    f = Flower(0, 0, RED)
    g.flowers = [f]
    g._try_collect(f)
    assert g.chain_log == [RED]


def test_mismatch_clears_chain_log() -> None:
    g = make_game()
    g.pollen_color = RED
    g.chain_log = [RED, RED]
    f = Flower(0, 0, LIME)
    g.flowers = [f]
    g._try_collect(f)
    assert g.chain_log == []


# -- Bee movement ------------------------------------------------------------

def test_bee_moves_and_normalizes_diagonal() -> None:
    g = make_game()
    g.bee_x = 160.0
    g.bee_y = 120.0
    g.flowers = []
    g._update_bee(1.0, 1.0)
    step = Game.BEE_SPEED / math_hypot(1.0, 1.0)
    assert abs(g.bee_x - (160.0 + step)) < 0.001
    assert abs(g.bee_y - (120.0 + step)) < 0.001


def math_hypot(dx: float, dy: float) -> float:
    import math

    return math.hypot(dx, dy)


def test_bee_clamped_to_grid_bounds() -> None:
    g = make_game()
    g.bee_x = 1.0
    g.bee_y = 1.0
    g.flowers = []
    g._update_bee(-1.0, -1.0)
    assert g.bee_x >= Game.OX + Game.BEE_R
    assert g.bee_y >= Game.OY + Game.BEE_R


def test_bee_collision_collects_flower() -> None:
    g = make_game()
    f = Flower(0, 0, RED)
    g.flowers = [f]
    g.pollen_color = None
    fx, fy = g._make_grid_pos(0, 0)
    g.bee_x = float(fx)
    g.bee_y = float(fy)
    g._update_bee(0.0, 0.0)
    assert f not in g.flowers
    assert g.combo == 1


def test_empty_grid_no_collision() -> None:
    g = make_game()
    g.flowers = []
    g.bee_x = 160.0
    g.bee_y = 120.0
    g.combo = 0
    g._update_bee(1.0, 0.0)
    assert g.combo == 0


# -- Heat / timer ------------------------------------------------------------

def test_heat_decay() -> None:
    g = make_game()
    g.heat = 10.0
    g._update_heat()
    assert abs(g.heat - (10.0 - Game.HEAT_DECAY)) < 0.001


def test_heat_threshold_checked_before_decay() -> None:
    g = make_game()
    g.heat = 100.0
    g._update_heat()
    assert g.heat == 100.0  # no decay happened; game over fired first
    assert g.phase == Phase.GAME_OVER


def test_super_freezes_heat() -> None:
    g = make_game()
    g.heat = 50.0
    g.super_mode = True
    g.super_timer = 10
    g._update_heat()
    assert g.heat == 50.0


def test_timer_reaches_zero_game_over() -> None:
    g = make_game()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


def test_game_over_reason_heat() -> None:
    g = make_game()
    g.heat = 100.0
    assert g._game_over_reason() == "HEAT"


def test_game_over_reason_time() -> None:
    g = make_game()
    g.heat = 0.0
    g.timer = 0
    assert g._game_over_reason() == "TIME"


# -- Super expiry ------------------------------------------------------------

def test_super_expiry_returns_normal_matching() -> None:
    g = make_game()
    g.super_mode = True
    g.super_timer = 1
    g.super_mode = True
    # simulate update's super_timer decrement logic
    g.super_timer -= 1
    if g.super_timer <= 0:
        g.super_mode = False
    assert g.super_mode is False
    # now a wrong-color touch mismatches
    g.pollen_color = RED
    f = Flower(0, 0, LIME)
    g.flowers = [f]
    g.combo = 2
    assert g._try_collect(f) is False
    assert g.combo == 0


# -- Difficulty interpolation -------------------------------------------------

def test_difficulty_interpolation() -> None:
    g = make_game()
    g.elapsed = 0
    assert g._max_flowers() == Game.MAX_FLOWERS_START
    assert g._spawn_interval() == Game.SPAWN_INTERVAL
    assert g._ca_interval() == Game.CA_INTERVAL
    g.elapsed = GAME_TIME
    assert g._max_flowers() == Game.MAX_FLOWERS
    assert g._spawn_interval() == Game.SPAWN_INTERVAL_END
    assert g._ca_interval() == Game.CA_INTERVAL_END


# -- CA spread ---------------------------------------------------------------

def test_ca_spread_sprouts_same_color() -> None:
    g = make_game()
    g.flowers = [Flower(5, 4, YELLOW)]
    g.CA_CHANCE = 1.0
    g._update_ca_spread()
    assert len(g.flowers) == 2
    child = g.flowers[1]
    assert child.color == YELLOW
    assert abs(child.col - 5) + abs(child.row - 4) == 1  # adjacent


def test_ca_spread_respects_max() -> None:
    g = make_game()
    cap = g._max_flowers()
    g.flowers = [Flower(c % 10, c // 10, RED) for c in range(cap)]
    g.CA_CHANCE = 1.0
    g._update_ca_spread()
    assert len(g.flowers) == cap


# -- Particles / floating texts ----------------------------------------------

def test_match_spawns_particles() -> None:
    g = make_game()
    g.pollen_color = RED
    f = Flower(0, 0, RED)
    g.flowers = [f]
    g._try_collect(f)
    assert len(g.particles) == 8
    assert all(p.color == RED for p in g.particles)


def test_super_spawns_rainbow_particles() -> None:
    g = make_game()
    g.super_mode = True
    g.super_timer = 10
    g.pollen_color = RED
    f = Flower(0, 0, LIME)
    g.flowers = [f]
    g._try_collect(f)
    assert len(g.particles) == 20


def test_mismatch_spawns_gray_particles() -> None:
    g = make_game()
    g.pollen_color = RED
    f = Flower(0, 0, LIME)
    g.flowers = [f]
    g._try_collect(f)
    assert len(g.particles) == 4
    assert all(p.color == GRAY for p in g.particles)


def test_update_particles_moves_and_decays() -> None:
    g = make_game()
    g.particles = [Particle(0.0, 0.0, 1.0, 0.0, 2, RED)]
    g._update_particles()
    p = g.particles[0]
    assert p.x == 1.0
    assert p.vy == Game.GRAVITY  # gravity applied
    assert p.life == 1


def test_update_particles_removes_dead() -> None:
    g = make_game()
    g.particles = [Particle(0.0, 0.0, 0.0, 0.0, 1, RED)]
    g._update_particles()
    assert g.particles == []


def test_match_spawns_floating_text() -> None:
    g = make_game()
    g.pollen_color = RED
    f = Flower(0, 0, RED)
    g.flowers = [f]
    g._try_collect(f)
    assert any(t.text.startswith("+") for t in g.floating_texts)


def test_mismatch_spawns_wrong_text() -> None:
    g = make_game()
    g.pollen_color = RED
    f = Flower(0, 0, LIME)
    g.flowers = [f]
    g._try_collect(f)
    assert any(t.text == "WRONG!" for t in g.floating_texts)


def test_update_floating_texts_decays() -> None:
    g = make_game()
    g.floating_texts = [FloatingText(0.0, 0.0, "hi", 1, WHITE)]
    g._update_floating_texts()
    assert g.floating_texts == []


# -- Restart -----------------------------------------------------------------

def test_reset_clears_state() -> None:
    g = make_game()
    g.phase = Phase.GAME_OVER
    g.score = 500
    g.combo = 7
    g.heat = 80.0
    g.super_mode = True
    g.pollen_color = RED
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.pollen_color is None


if __name__ == "__main__":
    fns = [
        (name, obj)
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {exc!r}")
    print(f"\n{len(fns) - failed}/{len(fns)} tests passed")
    sys.exit(1 if failed else 0)
