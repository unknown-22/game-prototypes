"""Tests for Duck Chain game logic."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import Game, Phase, Particle


def _make_game(seed: int = 42) -> Game:
    game = Game.__new__(Game)
    game.phase = Phase.TITLE
    game._rng = random.Random(seed)
    game.reset()
    return game


class TestTagMatching:
    def test_tag_matching_color(self) -> None:
        game = _make_game()
        assert game.combo == 0
        assert game.score == 0

        game.player_color_idx = 0
        target_idx = 0
        game.ducks[0].color = Game.DUCK_COLORS[0]
        matched, score_earned = game._tag_duck(target_idx)
        assert matched is True
        assert game.combo == 1
        assert score_earned == 10
        assert game.score == 10

    def test_tag_mismatch_color(self) -> None:
        game = _make_game()
        game.player_color_idx = 0
        target_idx = 0
        game.ducks[0].color = Game.DUCK_COLORS[1]
        matched, _ = game._tag_duck(target_idx)
        assert matched is False
        assert game.combo == 0
        assert game.heat == Game.HEAT_MISMATCH

    def test_tag_during_cooldown(self) -> None:
        game = _make_game()
        game.tag_cooldown = 5
        matched, _ = game._tag_duck(0)
        assert matched is False
        assert game.tag_cooldown == 5

    def test_tag_inactive_duck(self) -> None:
        game = _make_game()
        game.ducks[0].active = False
        matched, _ = game._tag_duck(0)
        assert matched is False

    def test_tag_invalid_index(self) -> None:
        game = _make_game()
        matched, _ = game._tag_duck(-1)
        assert matched is False
        matched, _ = game._tag_duck(99)
        assert matched is False


class TestComboChain:
    def test_combo_increases(self) -> None:
        game = _make_game()
        game.player_color_idx = 0
        for i in range(3):
            game.ducks[i].color = Game.DUCK_COLORS[0]
            matched, _ = game._tag_duck(i)
            assert matched is True
            game.tag_cooldown = 0
        assert game.combo == 3
        assert game.max_combo == 3

    def test_combo_resets_on_mismatch(self) -> None:
        game = _make_game()
        game.player_color_idx = 0
        game.ducks[0].color = Game.DUCK_COLORS[0]
        game._tag_duck(0)
        assert game.combo == 1
        game.tag_cooldown = 0
        game.ducks[1].color = Game.DUCK_COLORS[1]
        game._tag_duck(1)
        assert game.combo == 0

    def test_score_multiplied_by_combo(self) -> None:
        game = _make_game()
        game.player_color_idx = 0
        for i in range(3):
            game.ducks[i].color = Game.DUCK_COLORS[0]
            game._tag_duck(i)
            game.tag_cooldown = 0
        expected_score = 10 * 1 + 10 * 2 + 10 * 3
        assert game.score == expected_score

    def test_scoring_super_goose_multiplier(self) -> None:
        game = _make_game()
        game.super_timer = 100
        game.player_color_idx = 0
        game.ducks[0].color = Game.DUCK_COLORS[1]
        matched, score = game._tag_duck(0)
        assert matched is True
        assert score == 10 * 1 * Game.SUPER_MULT


class TestChaseTrigger:
    def test_chase_triggers_at_threshold(self) -> None:
        game = _make_game()
        game.combo = Game.COMBO_THRESHOLD
        game.player_color_idx = 0
        game.player_angle = game.ducks[0].angle
        game.ducks[0].color = Game.DUCK_COLORS[0]
        triggered = game._try_trigger_chase()
        assert triggered is True
        assert game.phase == Phase.CHASE
        assert game.ducks[0].active is False
        assert game.chase_duck_idx == 0

    def test_chase_does_not_trigger_below_threshold(self) -> None:
        game = _make_game()
        game.combo = Game.COMBO_THRESHOLD - 1
        triggered = game._try_trigger_chase()
        assert triggered is False
        assert game.phase == Phase.PLAYING

    def test_chase_does_not_trigger_when_not_playing(self) -> None:
        game = _make_game()
        game.combo = Game.COMBO_THRESHOLD
        game.phase = Phase.CHASE
        triggered = game._try_trigger_chase()
        assert triggered is False


class TestChaseMechanics:
    def test_chase_reach_target(self) -> None:
        game = _make_game()
        game.phase = Phase.CHASE
        game.chase_duck_idx = 0
        game.chase_target_x = 160.0
        game.chase_target_y = 120.0
        game.player_x = 164.0
        game.player_y = 120.0
        game.chase_duck_x = 200.0
        game.chase_duck_y = 200.0
        game.ducks[0].active = False

        result = game._update_chase()
        assert result == "chasing" or result == "reached"

        game.player_x = 160.0
        game.player_y = 120.0
        result = game._update_chase()
        assert result == "reached"

    def test_chase_caught_by_duck(self) -> None:
        game = _make_game()
        game.phase = Phase.CHASE
        game.chase_duck_idx = 0
        game.chase_target_x = 200.0
        game.chase_target_y = 200.0
        game.player_x = 160.0
        game.player_y = 120.0
        game.chase_duck_x = 164.0
        game.chase_duck_y = 120.0
        game.ducks[0].active = False

        result = game._update_chase()
        assert result == "caught"

    def test_chase_reached_gives_super(self) -> None:
        game = _make_game()
        game.chase_duck_idx = 0
        game.ducks[0].active = False
        game._resolve_chase("reached")
        assert game.super_timer == Game.SUPER_DURATION
        assert game.ducks[0].active is True
        assert game.chase_duck_idx == -1

    def test_chase_caught_adds_heat(self) -> None:
        game = _make_game()
        game.heat = 10.0
        game.chase_duck_idx = 0
        game.ducks[0].active = False
        game._resolve_chase("caught")
        assert game.heat == 10.0 + Game.HEAT_CAUGHT
        assert game.chase_duck_idx == -1


class TestHeatSystem:
    def test_heat_decay(self) -> None:
        game = _make_game()
        game.heat = 50.0
        game._update_heat()
        assert game.heat == 50.0 - Game.HEAT_DECAY

    def test_heat_not_below_zero(self) -> None:
        game = _make_game()
        game.heat = 0.0
        game._update_heat()
        assert game.heat == 0.0

    def test_heat_max_triggers_game_over(self) -> None:
        game = _make_game()
        game.heat = Game.HEAT_MAX
        game._update_heat()
        assert game.phase == Phase.GAME_OVER


class TestTimer:
    def test_timer_ticks_down(self) -> None:
        game = _make_game()
        game.timer = 100
        game.super_timer = 0
        game._update_timers()
        assert game.timer == 99

    def test_timer_zero_triggers_game_over(self) -> None:
        game = _make_game()
        game.timer = 1
        game._update_timers()
        assert game.timer == 0
        assert game.phase == Phase.GAME_OVER

    def test_super_timer_ticks_down(self) -> None:
        game = _make_game()
        game.super_timer = 50
        game.timer = 60 * 60
        game._update_timers()
        assert game.super_timer == 49


class TestShuffle:
    def test_shuffle_changes_colors(self) -> None:
        game = _make_game(seed=42)
        game._shuffle_ducks()
        new_colors = [d.color for d in game.ducks]
        assert all(c in Game.DUCK_COLORS for c in new_colors)

    def test_shuffle_avoids_all_same(self) -> None:
        game = _make_game(seed=42)
        for _ in range(10):
            game._shuffle_ducks()
            colors = [d.color for d in game.ducks]
            assert not all(c == colors[0] for c in colors) or len(Game.DUCK_COLORS) == 1


class TestParticles:
    def test_spawn_particles(self) -> None:
        game = _make_game()
        game.particles.clear()
        game._spawn_particles(100.0, 100.0, 8, 5, (10, 20), (-1.0, 1.0), (-1.0, 1.0))
        assert len(game.particles) == 5
        for p in game.particles:
            assert 10 <= p.life <= 20
            assert p.color == 8

    def test_update_particles(self) -> None:
        game = _make_game()
        game.particles = [
            Particle(x=0, y=0, vx=1, vy=0, life=2, color=7),
            Particle(x=0, y=0, vx=0, vy=0, life=0, color=7),
        ]
        game._update_particles()
        assert len(game.particles) == 1
        p = game.particles[0]
        assert p.life == 1
        assert p.vy == Game.PARTICLE_GRAVITY
        assert p.x == 1.0

    def test_super_goose_particles_rainbow(self) -> None:
        game = _make_game(seed=42)
        game.particles.clear()
        colors: list[int] = []
        for _ in range(100):
            game._spawn_particles(0, 0, Game.DUCK_COLORS, 1, (10, 10), (0, 0), (0, 0))
            colors.append(game.particles[-1].color)
            game.particles.clear()
        unique = set(colors)
        assert len(unique) > 1


class TestReset:
    def test_reset_initializes_state(self) -> None:
        game = _make_game()
        assert game.phase == Phase.PLAYING
        assert game.score == 0
        assert game.combo == 0
        assert game.max_combo == 0
        assert game.heat == 0.0
        assert game.timer == Game.GAME_DURATION
        assert len(game.ducks) == Game.DUCK_COUNT
        assert game.chase_duck_idx == -1
        assert game.super_timer == 0

    def test_reset_clears_particles(self) -> None:
        game = _make_game()
        game._spawn_particles(0, 0, 7, 10, (10, 10), (0, 0), (0, 0))
        assert len(game.particles) > 0
        game.reset()
        assert len(game.particles) == 0


class TestDifficultyEscalation:
    def test_color_cycle_decreases(self) -> None:
        game = _make_game()
        game._elapsed_frames = 0
        assert game.get_color_cycle_interval() == 90
        game._elapsed_frames = 100 * 60
        assert game.get_color_cycle_interval() == 50

    def test_shuffle_interval_decreases(self) -> None:
        game = _make_game()
        game._elapsed_frames = 0
        assert game.get_shuffle_interval() == 600
        game._elapsed_frames = 60 * 60 * 2
        assert game.get_shuffle_interval() == 300


class TestHelperFunctions:
    def test_get_player_duck_idx(self) -> None:
        game = _make_game()
        game.player_angle = 0.0
        idx = game._get_player_duck_idx()
        assert 0 <= idx < Game.DUCK_COUNT

    def test_positions_computed(self) -> None:
        game = _make_game()
        game._update_positions()
        for duck in game.ducks:
            assert duck.x != 0.0 or duck.y != 0.0
        assert game.player_x != 0.0
        assert game.player_y != 0.0
