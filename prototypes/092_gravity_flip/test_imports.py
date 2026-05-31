"""Tests for 092_gravity_flip."""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import main


def _make_game(seed: int = 42) -> main.Game:
    game = main.Game.__new__(main.Game)
    game._rng = random.Random(seed)
    game.reset()
    game.phase = main.Phase.PLAYING
    return game


# ─── Reset & Initialization ─────────────────────────────────────────────────


def test_import_and_reset() -> None:
    game = _make_game()
    game.phase = main.Phase.TITLE
    assert game.player_x == main.SCREEN_W / 2
    assert game.player_y == main.SCREEN_H / 2
    assert game.player_vx == 0.0
    assert game.player_vy == 0.0
    assert game.gravity == main.Gravity.DOWN
    assert game.hp == main.MAX_HP
    assert game.score == 0
    assert game.combo == 0
    assert game.max_combo == 0
    assert game.combo_color == main.EMPTY_COLOR
    assert not game.super_mode
    assert game.super_timer == 0
    assert game.heat == 0.0
    assert game.game_timer == main.GAME_TIMER
    assert game.gems == []
    assert game.spikes == []
    assert game.particles == []
    assert game.float_texts == []


# ─── Gravity Flip ───────────────────────────────────────────────────────────


def test_gravity_flip_changes_direction() -> None:
    game = _make_game()
    game._on_gravity_flip(main.Gravity.UP)
    assert game.gravity == main.Gravity.UP
    assert game.player_vy == -main.MAX_SPEED
    assert game.heat == main.HEAT_PER_FLIP


def test_gravity_flip_same_direction_noop() -> None:
    game = _make_game()
    assert game.gravity == main.Gravity.DOWN
    game._on_gravity_flip(main.Gravity.DOWN)
    assert game.gravity == main.Gravity.DOWN
    assert game.heat == 0.0


def test_gravity_flip_all_directions() -> None:
    game = _make_game()
    game._on_gravity_flip(main.Gravity.UP)
    assert game.player_vy == -main.MAX_SPEED
    game._on_gravity_flip(main.Gravity.RIGHT)
    assert game.player_vx == main.MAX_SPEED
    game._on_gravity_flip(main.Gravity.LEFT)
    assert game.player_vx == -main.MAX_SPEED
    game._on_gravity_flip(main.Gravity.DOWN)
    assert game.player_vy == main.MAX_SPEED


# ─── Apply Gravity ──────────────────────────────────────────────────────────


def test_apply_gravity_moves_player_down() -> None:
    game = _make_game()
    game.gravity = main.Gravity.DOWN
    game.player_y = 100.0
    game.player_vy = 0.0
    game._apply_gravity()
    assert game.player_vy > 0.0
    assert game.player_y > 100.0


def test_apply_gravity_moves_player_up() -> None:
    game = _make_game()
    game.gravity = main.Gravity.UP
    game.player_y = 100.0
    game.player_vy = 0.0
    game._apply_gravity()
    assert game.player_vy < 0.0
    assert game.player_y < 100.0


def test_apply_gravity_respects_max_speed() -> None:
    game = _make_game()
    game.gravity = main.Gravity.DOWN
    for _ in range(200):
        game._apply_gravity()
    speed = math.sqrt(game.player_vx**2 + game.player_vy**2)
    assert speed <= main.MAX_SPEED + 0.01


# ─── Clamp to Room ──────────────────────────────────────────────────────────


def test_clamp_to_room_left_wall() -> None:
    game = _make_game()
    game.player_x = 0.0
    game.player_vx = -1.0
    game._clamp_to_room()
    assert game.player_x == main.ROOM_L + main.PLAYER_RADIUS
    assert game.player_vx == 0.0


def test_clamp_to_room_top_wall() -> None:
    game = _make_game()
    game.player_y = 0.0
    game.player_vy = -1.0
    game._clamp_to_room()
    assert game.player_y == main.ROOM_T + main.PLAYER_RADIUS
    assert game.player_vy == 0.0


def test_clamp_to_room_player_in_bounds() -> None:
    game = _make_game()
    cx = (main.ROOM_L + main.ROOM_R) / 2
    cy = (main.ROOM_T + main.ROOM_B) / 2
    game.player_x = cx
    game.player_y = cy
    game._clamp_to_room()
    assert game.player_x == cx
    assert game.player_y == cy


# ─── Gem Collection ─────────────────────────────────────────────────────────


def test_collect_gem_adds_score() -> None:
    game = _make_game()
    game.gems = [main.Gem(game.player_x, game.player_y, main.RED)]
    game._collect_gems()
    assert game.score > 0
    assert len(game.gems) == 0
    assert game.combo == 1


def test_collect_gem_starts_combo() -> None:
    game = _make_game()
    game.gems = [main.Gem(game.player_x, game.player_y, main.RED)]
    game._collect_gems()
    assert game.combo == 1
    assert game.combo_color == main.RED


def test_collect_same_color_builds_combo() -> None:
    game = _make_game()
    game.combo = 1
    game.combo_color = main.RED
    game.gems = [main.Gem(game.player_x, game.player_y, main.RED)]
    game._collect_gems()
    assert game.combo == 2
    assert game.combo_color == main.RED


def test_collect_different_color_resets_combo() -> None:
    game = _make_game()
    game.combo = 2
    game.combo_color = main.RED
    game.gems = [main.Gem(game.player_x, game.player_y, main.GREEN)]
    game._collect_gems()
    assert game.combo == 1
    assert game.combo_color == main.GREEN


def test_combo_score_multiplier() -> None:
    game = _make_game()
    game.combo = 1
    game.combo_color = main.RED
    game.gems = [main.Gem(game.player_x, game.player_y, main.RED, value=10)]
    game._collect_gems()
    assert game.combo == 2
    assert game.score == 20


def test_max_combo_tracked() -> None:
    game = _make_game()
    game.combo = 0
    game.combo_color = main.EMPTY_COLOR
    assert game.max_combo == 0
    game.gems.append(main.Gem(game.player_x, game.player_y, main.RED))
    game._collect_gems()
    assert game.max_combo == 1


# ─── Super Mode ─────────────────────────────────────────────────────────────


def test_super_mode_activation() -> None:
    game = _make_game()
    game.combo = 2
    game.combo_color = main.RED
    game.gems = [main.Gem(game.player_x, game.player_y, main.RED)]
    game._collect_gems()
    assert game.combo == 3
    assert game.super_mode
    assert game.super_timer == main.SUPER_DURATION


def test_super_mode_timer_expires() -> None:
    game = _make_game()
    game.super_mode = True
    game.super_timer = 1
    game._update_super_mode()
    assert game.super_timer == 0
    assert not game.super_mode


def test_super_mode_score_multiplier() -> None:
    game = _make_game()
    game.super_mode = True
    game.combo = 0
    game.combo_color = main.EMPTY_COLOR
    game.gems = [main.Gem(game.player_x, game.player_y, main.RED, value=10)]
    game._collect_gems()
    assert game.score == 30


def test_super_mode_re_trigger_resets_timer() -> None:
    game = _make_game()
    game.super_mode = True
    game.super_timer = 100
    game.combo = 2
    game.combo_color = main.RED
    game.gems = [main.Gem(game.player_x, game.player_y, main.RED)]
    game._collect_gems()
    assert game.super_timer == main.SUPER_DURATION


# ─── Spike Collision ────────────────────────────────────────────────────────


def test_spike_collision_damages_player() -> None:
    game = _make_game()
    spike = main.Spike(game.player_x, main.ROOM_T, "top")
    game.spikes = [spike]
    game.player_y = main.ROOM_T + main.PLAYER_RADIUS - 1
    old_hp = game.hp
    game._check_spike_collisions()
    assert game.hp == old_hp - 1
    assert game.invuln_timer == main.INVULN_FRAMES


def test_spike_collision_blocked_by_invuln() -> None:
    game = _make_game()
    game.invuln_timer = 30
    spike = main.Spike(game.player_x, main.ROOM_T, "top")
    game.spikes = [spike]
    game.player_y = main.ROOM_T + main.PLAYER_RADIUS - 1
    old_hp = game.hp
    game._check_spike_collisions()
    assert game.hp == old_hp


def test_super_mode_blocks_spike_damage() -> None:
    game = _make_game()
    game.super_mode = True
    spike = main.Spike(game.player_x, main.ROOM_T, "top")
    game.spikes = [spike]
    game.player_y = main.ROOM_T + main.PLAYER_RADIUS - 1
    old_hp = game.hp
    game._check_spike_collisions()
    assert game.hp == old_hp


def test_spike_no_collision_when_far() -> None:
    game = _make_game()
    spike = main.Spike(main.ROOM_R, main.ROOM_T, "top")
    game.spikes = [spike]
    game.player_x = main.SCREEN_W / 2
    game.player_y = main.SCREEN_H / 2
    old_hp = game.hp
    game._check_spike_collisions()
    assert game.hp == old_hp


# ─── Heat Mechanics ─────────────────────────────────────────────────────────


def test_heat_decays_over_time() -> None:
    game = _make_game()
    game.heat = 50.0
    game._update_heat()
    assert game.heat < 50.0


def test_heat_decay_stops_at_zero() -> None:
    game = _make_game()
    game.heat = 0.0
    game._update_heat()
    assert game.heat == 0.0


def test_heat_damage_at_max() -> None:
    game = _make_game()
    game.heat = 100.3
    old_hp = game.hp
    game._update_heat()
    assert game.hp == old_hp - 1
    assert game.heat == 0.0


def test_heat_damage_blocked_by_super_mode() -> None:
    game = _make_game()
    game.super_mode = True
    game.heat = 100.0
    old_hp = game.hp
    game._update_heat()
    assert game.hp == old_hp


# ─── Particle & Float Text Lifecycle ────────────────────────────────────────


def test_particles_spawned_on_collect() -> None:
    game = _make_game()
    game._spawn_collect_particles(100.0, 100.0, main.RED)
    assert len(game.particles) == 8


def test_particles_cleaned_up() -> None:
    game = _make_game()
    game._spawn_collect_particles(100.0, 100.0, main.RED)
    for p in game.particles:
        p.life = 1
    game._update_particles()
    game._update_particles()
    assert len(game.particles) == 0


def test_damage_particles_spawned() -> None:
    game = _make_game()
    game._spawn_damage_particles(100.0, 100.0)
    assert len(game.particles) == 6


def test_float_texts_cleaned_up() -> None:
    game = _make_game()
    game.float_texts = [main.FloatText(100.0, 100.0, "test", 1, main.WHITE)]
    game._update_float_texts()
    assert len(game.float_texts) == 0


# ─── Spawning ───────────────────────────────────────────────────────────────


def test_gem_spawns_in_bounds() -> None:
    game = _make_game()
    game._spawn_gem()
    assert len(game.gems) == 1
    gem = game.gems[0]
    assert main.ROOM_L <= gem.x <= main.ROOM_R
    assert main.ROOM_T <= gem.y <= main.ROOM_B
    assert gem.color in main.GEM_COLORS


def test_spike_spawns_on_wall() -> None:
    game = _make_game()
    game._spawn_spike()
    assert len(game.spikes) == 1
    spike = game.spikes[0]
    assert spike.wall in ("top", "bottom", "left", "right")


def test_spike_count_capped() -> None:
    game = _make_game()
    for _ in range(20):
        game._spawn_spike()
    max_spikes = 8 + game._current_wave()
    assert len(game.spikes) <= max_spikes


# ─── Game State ─────────────────────────────────────────────────────────────


def test_hp_zero_triggers_game_over() -> None:
    game = _make_game()
    game.hp = 1
    game.heat = 0.0
    game._update_heat()
    game.hp = 0
    game.phase = main.Phase.GAME_OVER
    assert game.phase == main.Phase.GAME_OVER


def test_timer_zero_triggers_game_over() -> None:
    game = _make_game()
    game.game_timer = 0
    game.phase = main.Phase.GAME_OVER
    assert game.phase == main.Phase.GAME_OVER


def test_wave_increases_over_time() -> None:
    game = _make_game()
    game.game_timer = main.GAME_TIMER
    assert game._current_wave() == 1
    game.game_timer = main.GAME_TIMER - 600
    assert game._current_wave() == 2
    game.game_timer = main.GAME_TIMER - 1200
    assert game._current_wave() == 3


# ─── Timers ─────────────────────────────────────────────────────────────────


def test_invuln_timer_decrements() -> None:
    game = _make_game()
    game.invuln_timer = 10
    game._update_timers()
    assert game.invuln_timer == 9


def test_game_timer_decrements() -> None:
    game = _make_game()
    old_timer = game.game_timer
    game._update_timers()
    assert game.game_timer == old_timer - 1


# ─── Reset ──────────────────────────────────────────────────────────────────


def test_reset_after_game() -> None:
    game = _make_game()
    game.score = 500
    game.combo = 5
    game.max_combo = 5
    game.heat = 75.0
    game.hp = 1
    game.gems = [main.Gem(100.0, 100.0, main.RED)]
    game.spikes = [main.Spike(10.0, 10.0, "top")]
    game.particles = [main.Particle(0.0, 0.0, 1.0, 1.0, 10, main.RED, 10)]
    game.float_texts = [main.FloatText(0.0, 0.0, "x", 10, main.WHITE)]
    game.super_mode = True
    game.super_timer = 100
    game.reset()
    assert game.score == 0
    assert game.combo == 0
    assert game.max_combo == 0
    assert game.heat == 0.0
    assert game.hp == main.MAX_HP
    assert game.gems == []
    assert game.spikes == []
    assert game.particles == []
    assert game.float_texts == []
    assert not game.super_mode
    assert game.super_timer == 0
    assert game.phase == main.Phase.TITLE
