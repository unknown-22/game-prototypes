"""Tests for Echo Hop — headless mode."""
from __future__ import annotations

import sys

sys.path.insert(0, "prototypes/266_echo_hop")

from main import (  # noqa: E402
    BFS_BONUS,
    COLORS,
    FALL_PENALTY,
    KILL_BASE_SCORE,
    LIME,
    MAX_FOOTPRINTS,
    MAX_HP,
    ORIGIN_X,
    ORIGIN_Y,
    RED,
    SUPER_DURATION,
    SUPER_THRESHOLD,
    Enemy,
    Footprint,
    Game,
    Particle,
    Phase,
)

import random


# ── Helpers ────────────────────────────────────────────────────────────


def _new_game() -> Game:
    g = Game.__new__(Game)
    g._set_defaults()
    g._headless = True
    g._rng = random.Random(42)
    return g


def _start_game(g: Game) -> None:
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.active_color = RED
    g.combo = 0
    g.max_combo = 0
    g.hp = MAX_HP
    g.score = 0
    g.super_mode = False
    g.super_timer = 0
    g.enemies.clear()
    g.footprints.clear()
    g.particles.clear()
    g.spawn_timer = 120
    g.spawn_interval = 120
    g.game_timer = 0
    g.move_cooldown = 0
    g.enemy_move_timer = 0


# ── Test Grid ──────────────────────────────────────────────────────────


class TestGridProjection:
    def test_origin(self) -> None:
        g = _new_game()
        x, y = g._grid_to_screen(0, 0)
        assert x == ORIGIN_X
        assert y == ORIGIN_Y

    def test_diagonal_moves_right(self) -> None:
        g = _new_game()
        x0, y0 = g._grid_to_screen(0, 0)
        x1, y1 = g._grid_to_screen(1, 0)
        assert x1 > x0
        assert y1 > y0

    def test_diagonal_moves_down(self) -> None:
        g = _new_game()
        x0, y0 = g._grid_to_screen(0, 0)
        x1, y1 = g._grid_to_screen(0, 1)
        assert x1 < x0
        assert y1 > y0

    def test_is_valid_top_left(self) -> None:
        g = _new_game()
        assert g._is_valid_cube(0, 0) is True

    def test_is_valid_edge(self) -> None:
        g = _new_game()
        assert g._is_valid_cube(6, 0) is True

    def test_is_valid_bottom_row(self) -> None:
        g = _new_game()
        assert g._is_valid_cube(3, 3) is True

    def test_is_invalid_beyond_pyramid(self) -> None:
        g = _new_game()
        assert g._is_valid_cube(3, 4) is False

    def test_is_invalid_negative(self) -> None:
        g = _new_game()
        assert g._is_valid_cube(-1, 0) is False
        assert g._is_valid_cube(0, -1) is False

    def test_is_invalid_out_of_bounds(self) -> None:
        g = _new_game()
        assert g._is_valid_cube(7, 0) is False
        assert g._is_valid_cube(0, 7) is False


class TestNeighbors:
    def test_center_neighbors(self) -> None:
        g = _new_game()
        n = g._get_neighbors(1, 1)
        assert len(n) == 4
        assert (0, 0) in n
        assert (2, 0) in n
        assert (2, 2) in n
        assert (0, 2) in n

    def test_corner_neighbors(self) -> None:
        g = _new_game()
        n = g._get_neighbors(0, 0)
        assert len(n) == 1
        assert (1, 1) in n

    def test_edge_neighbors(self) -> None:
        g = _new_game()
        n = g._get_neighbors(6, 0)
        assert len(n) == 1
        assert (5, 1) in n


# ── Test Player Movement ───────────────────────────────────────────────


class TestPlayerMovement:
    def test_move_within_grid(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        result = g._move_player(1, 0)
        assert result is True
        assert g.player_gx == 2
        assert g.player_gy == 1

    def test_move_leaves_footprint(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        old_color = g.active_color
        g._move_player(1, 0)
        assert len(g.footprints) > 0
        fp = g.footprints[-1]
        assert fp.grid_x == 2
        assert fp.grid_y == 1
        assert fp.color != old_color

    def test_move_updates_active_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        old_color = g.active_color
        g._move_player(1, 0)
        assert g.active_color != old_color
        assert g.active_color in COLORS

    def test_fall_off_edge(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 6
        g.player_gy = 0
        g.active_color = RED
        g.hp = 5
        result = g._move_player(1, 0)
        assert result is True
        assert g.player_gx == 0
        assert g.player_gy == 0
        assert g.hp == 4
        assert g.combo == 0

    def test_fall_penalty_score(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 6
        g.player_gy = 0
        g.score = 100
        g._move_player(1, 0)
        assert g.score == 100 + FALL_PENALTY

    def test_score_not_negative(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 6
        g.player_gy = 0
        g.score = 0
        g._move_player(1, 0)
        assert g.score >= 0


# ── Test Enemy Stomp ───────────────────────────────────────────────────


class TestEnemyStomp:
    def test_stomp_same_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        enemy = Enemy(2, 1, RED)
        g.enemies.append(enemy)
        g.combo = 0
        g.score = 0
        g._move_player(1, 0)
        assert enemy.alive is False
        assert g.combo == 1
        assert g.score > 0

    def test_stomp_wrong_color_damages(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        g.hp = 5
        enemy = Enemy(2, 1, LIME)
        g.enemies.append(enemy)
        g._move_player(1, 0)
        assert g.hp == 4
        assert g.combo == 0
        assert enemy.alive is True

    def test_stomp_combo_increases(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        g.combo = 3
        enemy = Enemy(2, 1, RED)
        g.enemies.append(enemy)
        g._move_player(1, 0)
        assert g.combo == 4

    def test_stomp_max_combo_tracked(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        g.combo = 0
        g.max_combo = 0
        enemy = Enemy(2, 1, RED)
        g.enemies.append(enemy)
        g._move_player(1, 0)
        assert g.max_combo == 1

    def test_stomp_spawns_particles(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        enemy = Enemy(2, 1, RED)
        g.enemies.append(enemy)
        g._move_player(1, 0)
        assert len(g.particles) > 0

    def test_no_enemy_on_cube(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        g.hp = 5
        g._move_player(1, 0)
        assert g.hp == 5


# ── Test Super Mode ────────────────────────────────────────────────────


class TestSuperMode:
    def test_super_activates_at_threshold(self) -> None:
        g = _new_game()
        _start_game(g)
        g.combo = SUPER_THRESHOLD - 1
        g.super_mode = False
        g._check_super_mode()
        assert g.super_mode is False
        g.combo = SUPER_THRESHOLD
        g._check_super_mode()
        assert g.super_mode is True
        assert g.super_timer == SUPER_DURATION

    def test_super_does_not_reset_while_active(self) -> None:
        g = _new_game()
        _start_game(g)
        g.combo = SUPER_THRESHOLD
        g.super_mode = True
        g.super_timer = 100
        g._check_super_mode()
        assert g.super_timer == 100

    def test_super_timer_decrements(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_mode = True
        g.super_timer = 5
        g._update_super()
        assert g.super_timer == 4

    def test_super_ends_when_timer_zero(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_mode = True
        g.super_timer = 1
        g._update_super()
        assert g.super_mode is False
        assert g.super_timer == 0

    def test_super_multiplies_score(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        g.super_mode = True
        g.combo = 0
        g.score = 0
        enemy = Enemy(2, 1, RED)
        g.enemies.append(enemy)
        g._move_player(1, 0)
        base_score = int(KILL_BASE_SCORE * 1 * 3)
        assert g.score >= base_score


# ── Test BFS Clear ─────────────────────────────────────────────────────


class TestBfsClear:
    def test_bfs_single_enemy(self) -> None:
        g = _new_game()
        _start_game(g)
        g.enemies.append(Enemy(1, 1, RED))
        result = g._bfs_clear(1, 1, RED)
        assert (1, 1) in result
        assert len(result) == 1

    def test_bfs_connected_same_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g.enemies.append(Enemy(1, 1, RED))
        g.enemies.append(Enemy(2, 0, RED))
        g.enemies.append(Enemy(2, 2, RED))
        result = g._bfs_clear(1, 1, RED)
        assert len(result) == 3

    def test_bfs_ignores_different_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g.enemies.append(Enemy(1, 1, RED))
        g.enemies.append(Enemy(2, 1, LIME))
        result = g._bfs_clear(1, 1, RED)
        assert len(result) == 1

    def test_bfs_no_enemy(self) -> None:
        g = _new_game()
        _start_game(g)
        result = g._bfs_clear(1, 1, RED)
        assert len(result) == 0


# ── Test Footprint System ──────────────────────────────────────────────


class TestFootprintSystem:
    def test_footprint_created_on_move(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g._move_player(1, 0)
        assert len(g.footprints) == 1

    def test_footprint_overwrite(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 0
        g.player_gy = 0
        g.footprints.append(Footprint(1, 0, LIME, 100))
        g._move_player(1, 0)
        assert len(g.footprints) == 1
        assert g.footprints[0].grid_x == 1
        assert g.footprints[0].grid_y == 0

    def test_max_footprints(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        for i in range(MAX_FOOTPRINTS + 3):
            g._leave_footprint(i % 3, i % 3)
        assert len(g.footprints) <= MAX_FOOTPRINTS

    def test_update_footprints_decrements_life(self) -> None:
        g = _new_game()
        _start_game(g)
        g.footprints.append(Footprint(0, 0, RED, 10))
        g._update_footprints()
        assert g.footprints[0].life == 9

    def test_update_footprints_removes_dead(self) -> None:
        g = _new_game()
        _start_game(g)
        g.footprints.append(Footprint(0, 0, RED, 1))
        g._update_footprints()
        g._update_footprints()
        assert len(g.footprints) == 0

    def test_active_color_changes_each_hop(self) -> None:
        g = _new_game()
        _start_game(g)
        g.active_color = RED
        colors_seen = {g.active_color}
        for i in range(10):
            g.player_gx = 1
            g.player_gy = 1
            g.move_cooldown = 0
            g.hp = 5
            g._move_player(0, 0)  # won't move but leaves footprint
            colors_seen.add(g.active_color)
        assert len(colors_seen) >= 2


# ── Test Enemy Spawn ───────────────────────────────────────────────────


class TestEnemySpawn:
    def test_spawn_creates_enemy(self) -> None:
        g = _new_game()
        _start_game(g)
        result = g._spawn_enemy()
        assert result is not None
        assert result.grid_x is not None
        assert result.grid_y is not None
        assert result.color in COLORS
        assert result.alive is True

    def test_spawn_adds_to_list(self) -> None:
        g = _new_game()
        _start_game(g)
        before = len(g.enemies)
        g._spawn_enemy()
        assert len(g.enemies) == before + 1

    def test_spawn_on_edge(self) -> None:
        g = _new_game()
        _start_game(g)
        for _ in range(20):
            enemy = g._spawn_enemy()
            if enemy is None:
                continue
            neighbors = g._get_neighbors(enemy.grid_x, enemy.grid_y)
            assert len(neighbors) < 4

    def test_spawn_timer_triggers(self) -> None:
        g = _new_game()
        _start_game(g)
        g.spawn_timer = 0
        g.enemies.clear()
        g._update_spawn_timer()
        assert len(g.enemies) == 1


# ── Test Enemy Movement ────────────────────────────────────────────────


class TestEnemyMovement:
    def test_enemy_moves_toward_player(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 3
        g.player_gy = 3
        enemy = Enemy(0, 0, RED)
        g.enemies.append(enemy)
        g._update_enemies()
        old_dist = abs(enemy.grid_x - 3) + abs(enemy.grid_y - 3)
        new_dist = abs(0 - 3) + abs(0 - 3)
        assert old_dist <= new_dist or old_dist == new_dist

    def test_enemy_does_not_enter_player_cube(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 2
        g.player_gy = 2
        enemy = Enemy(1, 2, RED)
        g.enemies.append(enemy)
        g._update_enemies()
        assert not (enemy.grid_x == g.player_gx and enemy.grid_y == g.player_gy)


# ── Test Phases ────────────────────────────────────────────────────────


class TestPhases:
    def test_title_to_playing(self) -> None:
        g = _new_game()
        _start_game(g)
        g.phase = Phase.TITLE
        g._update_title({"up": False, "right": False, "down": False, "left": False,
                          "space_p": True, "return_p": False})
        assert g.phase == Phase.PLAYING

    def test_game_over_to_playing(self) -> None:
        g = _new_game()
        _start_game(g)
        g.phase = Phase.GAME_OVER
        g._update_game_over({"up": False, "right": False, "down": False, "left": False,
                              "space_p": True, "return_p": False})
        assert g.phase == Phase.PLAYING

    def test_hp_zero_triggers_game_over(self) -> None:
        g = _new_game()
        _start_game(g)
        g.hp = 0
        g.phase = Phase.PLAYING
        g._update_playing({"up": False, "right": False, "down": False, "left": False,
                           "space_p": False, "return_p": False})
        assert g.phase == Phase.GAME_OVER

    def test_reset_clears_state(self) -> None:
        g = _new_game()
        _start_game(g)
        g.score = 500
        g.combo = 10
        g.enemies.append(Enemy(1, 1, RED))
        g.footprints.append(Footprint(0, 0, RED, 100))
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert len(g.enemies) == 0
        assert len(g.footprints) == 0
        assert g.phase == Phase.TITLE


# ── Test Particles ─────────────────────────────────────────────────────


class TestParticles:
    def test_particle_spawn_count(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_particles(1, 1, RED, 5, 5)
        assert len(g.particles) == 5

    def test_particle_update(self) -> None:
        g = _new_game()
        _start_game(g)
        g.particles.append(Particle(100.0, 100.0, 1.0, -1.0, 10, RED))
        g._update_particles()
        p = g.particles[0]
        assert p.x != 100.0
        assert p.y != 100.0
        assert p.life == 9

    def test_particle_life_death(self) -> None:
        g = _new_game()
        _start_game(g)
        g.particles.append(Particle(100.0, 100.0, 0.0, 0.0, 1, RED))
        g._update_particles()
        assert len(g.particles) == 0


# ── Test Edge Cases ────────────────────────────────────────────────────


class TestEdgeCases:
    def test_multiple_enemies_same_cube_all_stomped(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        g.enemies.append(Enemy(2, 1, RED))
        g.enemies.append(Enemy(2, 1, RED))
        g._move_player(1, 0)
        alive_count = sum(1 for e in g.enemies if e.alive)
        assert alive_count == 0

    def test_multiple_enemies_diff_color_one_stomped(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        g.enemies.append(Enemy(2, 1, RED))
        g.enemies.append(Enemy(2, 1, LIME))
        g.hp = 5
        g._move_player(1, 0)
        alive_red = any(e.color == RED and e.alive for e in g.enemies)
        assert alive_red is False
        assert g.hp == 4

    def test_super_bfs_bonus_score(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        g.super_mode = True
        g.combo = 0
        g.score = 0
        g.enemies.append(Enemy(2, 1, RED))
        g.enemies.append(Enemy(3, 0, RED))
        g._move_player(1, 0)
        assert g.score > KILL_BASE_SCORE + BFS_BONUS

    def test_combo_resets_on_wrong_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        g.combo = 5
        g.enemies.append(Enemy(2, 1, LIME))
        g._move_player(1, 0)
        assert g.combo == 0

    def test_combo_resets_on_fall(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 6
        g.player_gy = 0
        g.combo = 10
        g._move_player(1, 0)
        assert g.combo == 0

    def test_cleanup_dead_enemies(self) -> None:
        g = _new_game()
        _start_game(g)
        g.enemies.append(Enemy(1, 1, RED, alive=False))
        g._cleanup_dead_enemies()
        assert len(g.enemies) == 0


# ── Test Scoring ───────────────────────────────────────────────────────


class TestScoring:
    def test_kill_score_with_combo(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        g.combo = 0
        g.score = 0
        g.enemies.append(Enemy(2, 1, RED))
        g._move_player(1, 0)
        assert g.score == int(KILL_BASE_SCORE * 1)

    def test_kill_score_combo_2(self) -> None:
        g = _new_game()
        _start_game(g)
        g.player_gx = 1
        g.player_gy = 1
        g.active_color = RED
        g.combo = 1
        g.score = 0
        g.enemies.append(Enemy(2, 1, RED))
        g._move_player(1, 0)
        assert g.score == int(KILL_BASE_SCORE * 2)


# ── Test Difficulty ────────────────────────────────────────────────────


class TestDifficulty:
    def test_spawn_interval_decreases(self) -> None:
        g = _new_game()
        _start_game(g)
        g.spawn_interval = 120
        g.game_timer = 1800
        g._update_spawn_timer()
        assert g.spawn_interval < 120

    def test_spawn_interval_has_min(self) -> None:
        g = _new_game()
        _start_game(g)
        g.spawn_interval = 120
        g.game_timer = 999999
        g._update_spawn_timer()
        assert g.spawn_interval >= 40


# ── Test Input ─────────────────────────────────────────────────────────


class TestInput:
    def test_headless_input_all_false(self) -> None:
        g = _new_game()
        inp = g._get_input()
        assert inp["up"] is False
        assert inp["right"] is False
        assert inp["down"] is False
        assert inp["left"] is False
        assert inp["space_p"] is False


# ── Test Enemies List ──────────────────────────────────────────────────


class TestEnemiesList:
    def test_enemy_at_finds_enemy(self) -> None:
        g = _new_game()
        _start_game(g)
        g.enemies.append(Enemy(2, 3, RED))
        result = g._enemy_at(2, 3)
        assert len(result) == 1
        assert result[0].color == RED

    def test_enemy_at_empty(self) -> None:
        g = _new_game()
        _start_game(g)
        result = g._enemy_at(5, 5)
        assert len(result) == 0

    def test_enemy_at_ignores_dead(self) -> None:
        g = _new_game()
        _start_game(g)
        g.enemies.append(Enemy(1, 1, RED, alive=False))
        result = g._enemy_at(1, 1)
        assert len(result) == 0
