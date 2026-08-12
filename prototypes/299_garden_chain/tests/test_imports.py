from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (  # noqa: E402
    Game,
    Particle,
    Phase,
)

GAME_DURATION = Game.GAME_DURATION
PLANT_COLORS = Game.PLANT_COLORS
RED = 8
LIME = 11
GRAY = 13


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._init_attrs()
    g._rng = random.Random(seed)
    g.reset()
    return g


class TestImports:
    def test_game_class_imports(self) -> None:
        assert Game is not None
        assert Phase.TITLE is not None
        assert Particle(0.0, 0.0, 0.0, 0.0, 1, 0).life == 1

    def test_class_constants(self) -> None:
        assert Game.GRID_COLS == 10
        assert Game.GRID_ROWS == 8
        assert Game.CELL == 24
        assert Game.EMPTY == -1
        assert Game.HEAT_CAP == 100.0
        assert Game.SUPER_THRESHOLD == 4
        assert Game.SUPER_DURATION == 300
        assert GAME_DURATION == 3600


class TestReset:
    def test_reset_initializes_state(self) -> None:
        g = _make_game()
        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.time_left == GAME_DURATION
        assert g.elapsed == 0
        assert g.super_active is False
        assert g.super_timer == 0
        assert g.last_color is None
        assert g.game_over_reason == ""

    def test_grid_dimensions(self) -> None:
        g = _make_game()
        assert len(g.grid) == Game.GRID_ROWS
        for row in g.grid:
            assert len(row) == Game.GRID_COLS

    def test_reset_seeds_initial_plants(self) -> None:
        g = _make_game()
        assert g._plant_count() == Game.INITIAL_PLANTS

    def test_reset_preserves_best_score(self) -> None:
        g = _make_game()
        g.best_score = 500
        g.reset()
        assert g.best_score == 500
        assert g.score == 0


class TestBfsCluster:
    def test_single_cell_cluster(self) -> None:
        g = _make_game()
        g.grid[0][0] = RED
        assert g._bfs_cluster(0, 0, RED) == {(0, 0)}

    def test_connected_cluster(self) -> None:
        g = _make_game()
        for c in range(3):
            g.grid[0][c] = RED
        g.grid[1][1] = RED
        cluster = g._bfs_cluster(0, 0, RED)
        assert cluster == {(0, 0), (1, 0), (2, 0), (1, 1)}

    def test_cluster_stops_at_different_color(self) -> None:
        g = _make_game()
        g.grid[0][0] = RED
        g.grid[0][1] = LIME
        g.grid[0][2] = RED
        assert g._bfs_cluster(0, 0, RED) == {(0, 0)}
        assert g._bfs_cluster(2, 0, RED) == {(2, 0)}

    def test_empty_cell_returns_empty(self) -> None:
        g = _make_game()
        assert g._bfs_cluster(0, 0, RED) == set()


class TestHarvest:
    def test_first_harvest_matches_no_penalty(self) -> None:
        g = _make_game()
        g.grid[0][0] = RED
        gain = g._harvest(0, 0)
        assert gain == Game.POINTS_PER_PLANT
        assert g.combo == 1
        assert g.heat == 0.0
        assert g.grid[0][0] == Game.EMPTY

    def test_same_color_builds_combo(self) -> None:
        g = _make_game()
        g.grid[0][0] = RED
        g.grid[0][3] = RED
        g._harvest(0, 0)
        g._harvest(3, 0)
        assert g.combo == 2

    def test_mismatch_resets_combo_and_adds_heat(self) -> None:
        g = _make_game()
        g.grid[0][0] = RED
        g.grid[0][1] = LIME
        g._harvest(0, 0)
        assert g.combo == 1
        g._harvest(1, 0)
        assert g.combo == 1
        assert g.heat == Game.MISMATCH_HEAT

    def test_miss_adds_heat(self) -> None:
        g = _make_game()
        gain = g._harvest(0, 0)
        assert gain == 0
        assert g.heat == Game.MISS_HEAT
        assert g.combo == 0

    def test_harvest_clears_whole_cluster(self) -> None:
        g = _make_game()
        for c in range(3):
            g.grid[0][c] = RED
        g._harvest(0, 0)
        for c in range(3):
            assert g.grid[0][c] == Game.EMPTY

    def test_cluster_size_scales_score(self) -> None:
        g = _make_game()
        g.grid[0][0] = RED
        g.grid[0][1] = RED
        gain = g._harvest(0, 0)
        assert gain == 2 * Game.POINTS_PER_PLANT

    def test_combo_multiplies_score(self) -> None:
        g = _make_game()
        g.grid[0][0] = RED
        g._harvest(0, 0)  # combo 1, score +10
        g.grid[0][1] = RED
        g.grid[0][2] = RED
        gain = g._harvest(1, 0)  # combo 2, cluster size 2
        assert gain == 2 * Game.POINTS_PER_PLANT * 2


class TestSuperHarvest:
    def test_combo_4_activates_super(self) -> None:
        g = _make_game()
        for c in range(4):
            g.grid[0][c] = RED
            g._harvest(c, 0)
        assert g.super_active is True
        assert g.super_timer == Game.SUPER_DURATION

    def test_super_gives_3x_score(self) -> None:
        g = _make_game()
        for c in range(4):
            g.grid[0][c] = RED
            g._harvest(c, 0)
        g.grid[0][4] = LIME
        gain = g._harvest(4, 0)
        assert gain == Game.POINTS_PER_PLANT * 5 * 3

    def test_super_prevents_mismatch(self) -> None:
        g = _make_game()
        g.super_active = True
        g.super_timer = 100
        g.grid[0][0] = RED
        g._harvest(0, 0)
        g.grid[0][1] = LIME
        g._harvest(1, 0)
        assert g.combo == 2
        assert g.heat == 0.0

    def test_super_timer_decays(self) -> None:
        g = _make_game()
        g.super_active = True
        g.super_timer = 2
        g._update_timers()
        assert g.super_timer == 1
        g._update_timers()
        assert g.super_active is False
        assert g.super_timer == 0


class TestGrowth:
    def test_sprout_adds_one_plant(self) -> None:
        g = _make_game()
        before = g._plant_count()
        g._sprout()
        assert g._plant_count() == before + 1

    def test_sprout_full_grid_noop(self) -> None:
        g = _make_game()
        for r in range(Game.GRID_ROWS):
            for c in range(Game.GRID_COLS):
                g.grid[r][c] = RED
        g._sprout()
        assert g._plant_count() == Game.GRID_COLS * Game.GRID_ROWS

    def test_grow_spreads_to_adjacent_empty(self) -> None:
        g = _make_game(seed=42)
        g.grid[4][5] = RED
        for _ in range(20):
            g._grow()
        spread = any(
            g.grid[4 + dr][5 + dc] == RED
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= 5 + dc < Game.GRID_COLS and 0 <= 4 + dr < Game.GRID_ROWS
        )
        assert spread

    def test_grow_preserves_other_colors(self) -> None:
        g = _make_game(seed=42)
        g.grid[4][5] = RED
        g.grid[4][6] = LIME
        for _ in range(20):
            g._grow()
        assert g.grid[4][6] == LIME


class TestHeat:
    def test_heat_decays(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert g.heat < 50.0

    def test_heat_not_below_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_cap_game_over_before_decay(self) -> None:
        g = _make_game()
        g.heat = Game.HEAT_CAP
        g._update_heat()
        assert g.phase == Phase.GAME_OVER
        assert g.game_over_reason == "OVERGROWN!"

    def test_overgrow_raises_heat_when_occupied(self) -> None:
        g = _make_game()
        for r in range(Game.GRID_ROWS):
            for c in range(Game.GRID_COLS):
                g.grid[r][c] = RED
        g.heat = 0.0
        g._update_overgrow()
        assert g.heat == Game.OVERGROW_HEAT

    def test_no_overgrow_heat_when_sparse(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_overgrow()
        assert g.heat == 0.0


class TestTimers:
    def test_timers_decrement_time(self) -> None:
        g = _make_game()
        g._update_timers()
        assert g.time_left == GAME_DURATION - 1
        assert g.elapsed == 1

    def test_timer_zero_game_over(self) -> None:
        g = _make_game()
        g.time_left = 1
        g._update_timers()
        assert g.phase == Phase.GAME_OVER
        assert g.game_over_reason == "TIME UP!"

    def test_grow_interval_decreases_over_time(self) -> None:
        g = _make_game()
        start = g._grow_interval()
        g.elapsed = GAME_DURATION
        end = g._grow_interval()
        assert end < start

    def test_overgrow_threshold_decreases(self) -> None:
        g = _make_game()
        start = g._overgrow_threshold()
        g.elapsed = GAME_DURATION
        end = g._overgrow_threshold()
        assert end < start

    def test_best_score_updated_on_game_over(self) -> None:
        g = _make_game()
        g.score = 700
        g.time_left = 1
        g._update_timers()
        assert g.best_score == 700


class TestMouseToCell:
    def test_inside_maps_to_cell(self) -> None:
        g = _make_game()
        x = Game.GRID_X + 3 * Game.CELL + Game.CELL // 2
        y = Game.GRID_Y + 2 * Game.CELL + Game.CELL // 2
        assert g._cell_from_xy(x, y) == (3, 2)

    def test_outside_returns_none(self) -> None:
        g = _make_game()
        assert g._cell_from_xy(0, 0) is None
        assert g._cell_from_xy(319, 239) is None


class TestParticles:
    def test_harvest_spawns_particles(self) -> None:
        g = _make_game()
        g.grid[0][0] = RED
        g._harvest(0, 0)
        assert len(g.particles) == 8
        assert all(p.color == RED for p in g.particles)

    def test_particles_decay_and_remove(self) -> None:
        g = _make_game()
        g._spawn_particles(10.0, 10.0, RED, 2, 15, 25, 1.5)
        for p in g.particles:
            p.life = 1
        g._update_particles()
        assert len(g.particles) == 0

    def test_no_gravity(self) -> None:
        g = _make_game()
        g._spawn_particles(10.0, 10.0, RED, 1, 15, 25, 1.5)
        p = g.particles[0]
        vy0 = p.vy
        g._update_particles()
        assert p.vy == vy0
