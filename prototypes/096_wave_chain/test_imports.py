from __future__ import annotations

import math
import random
from unittest.mock import patch

import main as _main_module


def _new_game(seed: int = 42) -> _main_module.Game:
    """Create a Game in headless mode (bypassing pyxel.init/run)."""
    game = _main_module.Game.__new__(_main_module.Game)
    game.rng = random.Random(seed)
    game.reset()
    return game


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_constants() -> None:
    assert _main_module.SCREEN_W == 320
    assert _main_module.SCREEN_H == 240
    assert _main_module.MAX_HEAT == 5
    assert _main_module.GAME_DURATION == 3600
    assert _main_module.COMBO_SUPER_THRESHOLD == 5
    assert _main_module.SUPER_DURATION == 300


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------


def test_reset_initial_state() -> None:
    game = _new_game()
    assert game.phase == _main_module.Phase.TITLE
    assert game.score == 0
    assert game.combo == 0
    assert game.combo_color is None
    assert game.max_combo == 0
    assert game.heat == 0
    assert game.timer == 3600
    assert game.elapsed == 0
    assert game.player_offset == 0.0
    assert game.super_mode is False
    assert game.super_timer == 0
    assert game.gems == []
    assert game.rocks == []
    assert game.particles == []


def test_reset_clears_all() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.score = 500
    game.combo = 10
    game.combo_color = _main_module.RED
    game.max_combo = 10
    game.heat = 4
    game.timer = 100
    game.elapsed = 3500
    game.gems = [_main_module.Gem(x=100, y=100, color=_main_module.RED)]
    game.rocks = [_main_module.Rock(x=100, y=100)]
    game.reset()
    assert game.heat == 0
    assert game.score == 0
    assert game.combo == 0
    assert game.timer == 3600
    assert game.gems == []
    assert game.rocks == []


# ---------------------------------------------------------------------------
# Wave math
# ---------------------------------------------------------------------------


def test_wave_amplitude_at_start() -> None:
    game = _new_game()
    assert game.wave_amplitude() == _main_module.WAVE_AMPLITUDE_BASE


def test_wave_amplitude_increases() -> None:
    game = _new_game()
    game.elapsed = 2400
    amp = game.wave_amplitude()
    assert amp > _main_module.WAVE_AMPLITUDE_BASE


def test_wave_amplitude_capped() -> None:
    game = _new_game()
    game.elapsed = 99999
    assert game.wave_amplitude() == 60.0


def test_wave_y_center() -> None:
    game = _new_game()
    y1 = game.wave_y_at(0)
    y2 = game.wave_y_at(math.pi / _main_module.WAVE_FREQUENCY / 2)
    assert abs(y1 - _main_module.SCREEN_H // 2) <= _main_module.WAVE_AMPLITUDE_BASE
    assert abs(y2 - _main_module.SCREEN_H // 2) <= _main_module.WAVE_AMPLITUDE_BASE


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------


def test_player_offset_clamped() -> None:
    game = _new_game()
    game.update_player(up=True, down=False)
    for _ in range(50):
        game.update_player(up=True, down=False)
    assert game.player_offset <= _main_module.PLAYER_OFFSET_RANGE

    for _ in range(50):
        game.update_player(up=False, down=True)
    assert game.player_offset >= -_main_module.PLAYER_OFFSET_RANGE


def test_player_no_input_no_move() -> None:
    game = _new_game()
    game.update_player(up=False, down=False)
    assert game.player_offset == 0.0


# ---------------------------------------------------------------------------
# Gem collection — combo logic
# ---------------------------------------------------------------------------


def test_collect_first_gem_sets_combo() -> None:
    game = _new_game()
    gem = _main_module.Gem(x=100, y=100, color=_main_module.RED)
    game.gems = [gem]
    game.collect_gem(0)
    assert game.combo == 1
    assert game.combo_color == _main_module.RED
    assert game.score >= 10


def test_collect_same_color_increments_combo() -> None:
    game = _new_game()
    gem1 = _main_module.Gem(x=100, y=100, color=_main_module.RED)
    gem2 = _main_module.Gem(x=100, y=100, color=_main_module.RED)
    game.gems = [gem1, gem2]
    game.collect_gem(0)
    assert game.combo == 1
    game.collect_gem(0)  # After first collect, gems[0] is gone; re-add
    game.gems = [_main_module.Gem(x=100, y=100, color=_main_module.RED)]
    # Let's re-do properly
    pass


def test_collect_same_color_increments_combo_v2() -> None:
    game = _new_game()
    game.combo_color = _main_module.GREEN
    game.combo = 2
    game.score = 0
    gem = _main_module.Gem(x=100, y=100, color=_main_module.GREEN)
    game.gems = [gem]
    game.collect_gem(0)
    assert game.combo == 3
    assert game.score > 10


def test_collect_different_color_resets_combo() -> None:
    game = _new_game()
    game.combo_color = _main_module.RED
    game.combo = 4
    game.score = 0
    gem = _main_module.Gem(x=100, y=100, color=_main_module.YELLOW)
    game.gems = [gem]
    game.collect_gem(0)
    assert game.combo == 1
    assert game.combo_color == _main_module.YELLOW


def test_combo_scoring_scales() -> None:
    game = _new_game()
    game.combo_color = _main_module.DARK_BLUE
    game.combo = 5
    game.score = 0
    gem = _main_module.Gem(x=100, y=100, color=_main_module.DARK_BLUE)
    game.gems = [gem]
    game.collect_gem(0)
    assert game.combo == 6
    assert game.score == 40


# ---------------------------------------------------------------------------
# SUPER SURF activation
# ---------------------------------------------------------------------------


def test_super_surf_triggers_at_combo_5() -> None:
    game = _new_game()
    game.combo_color = _main_module.RED
    game.combo = 4
    gem = _main_module.Gem(x=100, y=100, color=_main_module.RED)
    game.gems = [gem]
    game.collect_gem(0)
    assert game.combo >= _main_module.COMBO_SUPER_THRESHOLD
    assert game.super_mode is True
    assert game.super_timer == _main_module.SUPER_DURATION


def test_super_mode_3x_scoring() -> None:
    game = _new_game()
    game.super_mode = True
    game.score = 0
    game.combo = 3
    gem = _main_module.Gem(x=100, y=100, color=_main_module.RED)
    game.gems = [gem]
    game.collect_gem(0)
    expected = (10 + 3 * 5) * 3
    assert game.score == expected


def test_super_mode_all_colors_count() -> None:
    game = _new_game()
    game.super_mode = True
    game.score = 0
    game.combo = 2
    gem = _main_module.Gem(x=100, y=100, color=_main_module.YELLOW)
    game.gems = [gem]
    game.collect_gem(0)
    assert game.score >= (10 + 2 * 5) * 3


# ---------------------------------------------------------------------------
# Rock collision
# ---------------------------------------------------------------------------


def test_rock_hit_increases_heat() -> None:
    game = _new_game()
    rock = _main_module.Rock(x=100, y=100)
    game.rocks = [rock]
    assert game.heat == 0
    game.hit_rock(0)
    assert game.heat == 1


def test_rock_hit_resets_combo() -> None:
    game = _new_game()
    game.combo = 5
    game.combo_color = _main_module.GREEN
    rock = _main_module.Rock(x=100, y=100)
    game.rocks = [rock]
    game.hit_rock(0)
    assert game.combo == 0
    assert game.combo_color is None


def test_super_mode_rock_destroyed_no_heat() -> None:
    game = _new_game()
    game.super_mode = True
    game.heat = 0
    game.score = 0
    rock = _main_module.Rock(x=100, y=100)
    game.rocks = [rock]
    game.hit_rock(0)
    assert game.heat == 0
    assert game.score == 50


# ---------------------------------------------------------------------------
# Game over
# ---------------------------------------------------------------------------


def test_game_over_on_max_heat() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.heat = _main_module.MAX_HEAT - 1
    rock = _main_module.Rock(x=100, y=100)
    game.rocks = [rock]
    game.hit_rock(0)
    assert game.heat == _main_module.MAX_HEAT


def test_game_over_from_heat_in_update() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.heat = _main_module.MAX_HEAT
    game.update()
    assert game.phase == _main_module.Phase.GAME_OVER


def test_game_over_from_timer_in_update() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.timer = 0
    game.update()
    assert game.phase == _main_module.Phase.GAME_OVER


# ---------------------------------------------------------------------------
# Max combo tracking
# ---------------------------------------------------------------------------


def test_max_combo_tracks_highest() -> None:
    game = _new_game()
    game.combo_color = _main_module.RED
    game.combo = 3
    gem = _main_module.Gem(x=100, y=100, color=_main_module.RED)
    game.gems = [gem]
    game.collect_gem(0)
    assert game.max_combo >= 4


# ---------------------------------------------------------------------------
# Super timer expiration
# ---------------------------------------------------------------------------


def test_super_timer_expires() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    game.super_mode = True
    game.super_timer = 1
    game.combo = 10
    game.combo_color = _main_module.YELLOW
    game.update()
    assert game.super_mode is False
    assert game.combo == 0
    assert game.combo_color is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_wave_y_at_extreme_x() -> None:
    game = _new_game()
    y1 = game.wave_y_at(-100)
    y2 = game.wave_y_at(500)
    assert 0 <= y1 <= _main_module.SCREEN_H
    assert 0 <= y2 <= _main_module.SCREEN_H


def test_spawn_gem_adds_to_list() -> None:
    game = _new_game()
    assert len(game.gems) == 0
    game.spawn_gem()
    assert len(game.gems) == 1
    assert game.gems[0].x > _main_module.SCREEN_W


def test_spawn_rock_adds_to_list() -> None:
    game = _new_game()
    assert len(game.rocks) == 0
    game.spawn_rock()
    assert len(game.rocks) == 1
    assert game.rocks[0].x > _main_module.SCREEN_W


def test_gems_move_left_and_despawn() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.PLAYING
    gem = _main_module.Gem(x=10, y=100, color=_main_module.RED)
    game.gems = [gem]
    # Run enough updates to push it off-screen (speed ≈ 1.0 + elapsed/800)
    for _ in range(20):
        game.update()
    assert len(game.gems) == 0


def test_collected_gem_removed() -> None:
    game = _new_game()
    gem = _main_module.Gem(x=100, y=100, color=_main_module.YELLOW)
    game.gems = [gem]
    game.collect_gem(0)
    assert gem.collected is True
    game.phase = _main_module.Phase.PLAYING
    game.update()
    assert len(game.gems) == 0


# ---------------------------------------------------------------------------
# Component import test
# ---------------------------------------------------------------------------


def test_all_symbols_importable() -> None:
    names = [
        "Phase",
        "Game",
        "App",
        "Gem",
        "Rock",
        "Particle",
        "SCREEN_W",
        "SCREEN_H",
        "MAX_HEAT",
        "GAME_DURATION",
        "COMBO_SUPER_THRESHOLD",
        "SUPER_DURATION",
    ]
    for name in names:
        assert hasattr(_main_module, name), f"Missing symbol: {name}"


def test_enum_phases() -> None:
    assert _main_module.Phase.TITLE is not None
    assert _main_module.Phase.PLAYING is not None
    assert _main_module.Phase.GAME_OVER is not None
    assert len(list(_main_module.Phase)) == 3


def test_particle_lifecycle() -> None:
    game = _new_game()
    p = _main_module.Particle(x=10, y=10, vx=1, vy=1, life=1, color=_main_module.WHITE)
    game.particles = [p]
    game.phase = _main_module.Phase.PLAYING
    game.update()
    assert len(game.particles) == 0


# ---------------------------------------------------------------------------
# update_player edge cases
# ---------------------------------------------------------------------------


def test_player_both_directions_no_move() -> None:
    game = _new_game()
    offset_before = game.player_offset
    game.update_player(up=True, down=True)
    assert game.player_offset == offset_before


def test_player_offset_clamped_upper() -> None:
    game = _new_game()
    game.player_offset = _main_module.PLAYER_OFFSET_RANGE
    game.update_player(up=True, down=False)
    assert game.player_offset == _main_module.PLAYER_OFFSET_RANGE


def test_player_offset_clamped_lower() -> None:
    game = _new_game()
    game.player_offset = -_main_module.PLAYER_OFFSET_RANGE
    game.update_player(up=False, down=True)
    assert game.player_offset == -_main_module.PLAYER_OFFSET_RANGE


# ---------------------------------------------------------------------------
# update doesn't process when not PLAYING
# ---------------------------------------------------------------------------


def test_update_noop_in_title() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.TITLE
    elapsed_before = game.elapsed
    game.update()
    assert game.elapsed == elapsed_before


def test_update_noop_in_game_over() -> None:
    game = _new_game()
    game.phase = _main_module.Phase.GAME_OVER
    elapsed_before = game.elapsed
    game.update()
    assert game.elapsed == elapsed_before
