"""Tests for TUG CHAIN prototype."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (  # type: ignore[import-untyped]
    CENTER_X,
    GAME_DURATION,
    HEAT_MAX,
    HEAT_WRONG,
    LOSE_THRESHOLD,
    PULL_FORCE_BASE,
    PULL_FORCE_COMBO,
    SEGMENT_WIDTH,
    SUPER_COMBO_THRESHOLD,
    WIN_THRESHOLD,
    FloatingText,
    Game,
    Particle,
    Phase,
    Segment,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.best_score = 0
    g._init_state()
    return g


def _setup_playing(g: Game) -> None:
    g.phase = Phase.PLAYING


def _place_active_segment(g: Game, color: int) -> None:
    g.segments.clear()
    g.segments.append(Segment(x=CENTER_X - SEGMENT_WIDTH // 2 - g.rope_position, color=color))


class TestSegments:
    def test_initial_segments_count(self) -> None:
        g = _make_game()
        assert len(g.segments) >= 12

    def test_find_active_segment_near_center(self) -> None:
        g = _make_game()
        _setup_playing(g)
        _place_active_segment(g, 0)
        seg = g._find_active_segment()
        assert seg is not None
        assert seg.color == 0

    def test_find_active_segment_none_when_far(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.segments.clear()
        g.segments.append(Segment(x=CENTER_X - 100, color=0))
        seg = g._find_active_segment()
        assert seg is None

    def test_update_segments_moves_segments(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.rope_speed = 2.0
        g.segments.clear()
        g.segments.append(Segment(x=CENTER_X, color=0))
        old_x = g.segments[0].x
        g._update_segments()
        assert g.segments[0].x < old_x

    def test_update_segments_removes_off_screen(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.segments.clear()
        g.segments.append(Segment(x=0, color=0))
        g._update_segments()
        assert len(g.segments) > 0

    def test_update_segments_spawns_new(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.segments.clear()
        g.segments.append(Segment(x=0, color=0))
        g._update_segments()
        last_x = max(s.x for s in g.segments)
        assert last_x >= 320


class TestPlayerPull:
    def test_pull_success_same_color(self) -> None:
        g = _make_game()
        _setup_playing(g)
        _place_active_segment(g, 0)
        g.player_color = 0
        old_pos = g.rope_position
        result = g._player_pull()
        assert result == "success"
        assert g.rope_position < old_pos
        assert g.combo == 1
        assert g.score > 0

    def test_pull_fail_wrong_color(self) -> None:
        g = _make_game()
        _setup_playing(g)
        _place_active_segment(g, 0)
        g.player_color = 1
        g.combo = 3
        result = g._player_pull()
        assert result == "miss"
        assert g.combo == 0
        assert g.heat == HEAT_WRONG

    def test_pull_none_no_active_segment(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.player_color = 0
        result = g._player_pull()
        assert result == "none"

    def test_pull_success_cycles_player_color(self) -> None:
        g = _make_game()
        _setup_playing(g)
        _place_active_segment(g, 0)
        g.player_color = 0
        g._player_pull()
        assert g.player_color == 1

    def test_pull_success_cools_heat(self) -> None:
        g = _make_game()
        _setup_playing(g)
        _place_active_segment(g, 0)
        g.player_color = 0
        g.heat = 20
        g._player_pull()
        assert g.heat < 20

    def test_pull_tracks_max_combo(self) -> None:
        g = _make_game()
        _setup_playing(g)
        for color in range(3):
            _place_active_segment(g, color)
            g.player_color = color
            g._player_pull()
        assert g.max_combo == 3

    def test_pull_score_with_combo(self) -> None:
        g = _make_game()
        _setup_playing(g)
        _place_active_segment(g, 0)
        g.player_color = 0
        g.combo = 2
        g._player_pull()
        assert g.score == 10 * 3  # 10 * max(1, combo=3)


class TestSuperMode:
    def test_super_mode_activates_at_threshold(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.combo = SUPER_COMBO_THRESHOLD - 1
        _place_active_segment(g, 3)
        g.player_color = 3
        g._player_pull()
        assert g.super_mode
        assert g.super_timer == 300

    def test_super_mode_any_color_matches(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.super_mode = True
        g.super_timer = 100
        g.player_color = 0
        _place_active_segment(g, 2)
        result = g._player_pull()
        assert result == "success"

    def test_super_mode_doubles_pull_force(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.super_mode = True
        g.super_timer = 100
        _place_active_segment(g, 0)
        g.player_color = 0
        g.rope_position = 0
        g.combo = 0
        g._player_pull()
        # pull_force = (PULL_FORCE_BASE + combo*PULL_FORCE_COMBO) * 2
        # combo becomes 1 in _on_pull_success
        expected = -2 * (PULL_FORCE_BASE + 1 * PULL_FORCE_COMBO)
        assert g.rope_position == expected

    def test_super_mode_deactivates_after_timer(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.super_mode = True
        g.super_timer = 1
        g._update_super_mode()
        assert not g.super_mode

    def test_super_mode_resets_combo_on_end(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.super_mode = True
        g.super_timer = 1
        g.combo = 5
        g._update_super_mode()
        assert g.combo == 0

    def test_super_mode_phase_anim(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.combo = SUPER_COMBO_THRESHOLD - 1
        _place_active_segment(g, 3)
        g.player_color = 3
        g._player_pull()
        assert g.phase == Phase.SUPER_ANIM


class TestAIPull:
    def test_ai_pull_moves_rope(self) -> None:
        g = _make_game()
        _setup_playing(g)
        _place_active_segment(g, 0)
        g.ai_pull_target = 0
        old_pos = g.rope_position
        g._ai_pull()
        assert g.rope_position > old_pos

    def test_ai_pull_wrong_no_move(self) -> None:
        g = _make_game()
        _setup_playing(g)
        _place_active_segment(g, 0)
        g.ai_pull_target = 1
        old_pos = g.rope_position
        g._ai_pull()
        assert g.rope_position == old_pos


class TestHeat:
    def test_heat_passive_increase(self) -> None:
        g = _make_game()
        _setup_playing(g)
        old_heat = g.heat
        g._update_heat()
        assert g.heat > old_heat

    def test_heat_capped_at_max(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.heat = HEAT_MAX
        g._update_heat()
        assert g.heat == HEAT_MAX

    def test_heat_wrong_pull_adds_heat(self) -> None:
        g = _make_game()
        _setup_playing(g)
        _place_active_segment(g, 0)
        g.player_color = 1
        g.heat = 0
        g._player_pull()
        assert g.heat == HEAT_WRONG


class TestTimer:
    def test_timer_decrements(self) -> None:
        g = _make_game()
        _setup_playing(g)
        old = g.timer
        g._update_timer()
        assert g.timer == old - 1

    def test_timer_zero_returns_true(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.timer = 1
        assert not g._update_timer()
        assert g.timer == 0
        assert g._update_timer()
        assert g.timer == -1


class TestWinLose:
    def test_win_rope_threshold(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.rope_position = WIN_THRESHOLD
        result = g._check_win_lose()
        assert result
        assert g.phase == Phase.VICTORY

    def test_lose_rope_threshold(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.rope_position = LOSE_THRESHOLD
        result = g._check_win_lose()
        assert result
        assert g.phase == Phase.DEFEAT

    def test_lose_heat_max(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.heat = HEAT_MAX
        result = g._check_win_lose()
        assert result
        assert g.phase == Phase.DEFEAT

    def test_no_win_lose_normal(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.rope_position = 0
        g.heat = 0
        result = g._check_win_lose()
        assert not result
        assert g.phase == Phase.PLAYING


class TestParticles:
    def test_spawn_particles_adds_to_list(self) -> None:
        g = _make_game()
        _setup_playing(g)
        assert len(g.particles) == 0
        g._spawn_particles(160, 120, 8, 10, life=20)
        assert len(g.particles) == 10

    def test_update_particles_expires_them(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g._spawn_particles(160, 120, 8, 3, life=1)
        g._update_particles()
        assert len(g.particles) == 0


class TestFloatingTexts:
    def test_spawn_floating_text_adds_to_list(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g._spawn_floating_text(160, 120, "TEST", 7, life=40)
        assert len(g.floating_texts) == 1

    def test_update_floating_text_expires(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g._spawn_floating_text(160, 120, "TEST", 7, life=1)
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


class TestReset:
    def test_reset_clears_state(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.score = 500
        g.combo = 10
        g.heat = 80
        g.rope_position = -50
        g.super_mode = True
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0
        assert g.rope_position == 0
        assert not g.super_mode
        assert g.phase == Phase.TITLE

    def test_reset_preserves_best_score(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.score = 500
        g.best_score = 200
        g.reset()
        assert g.best_score == 200


class TestDifficulty:
    def test_difficulty_scales_rope_speed(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.timer = GAME_DURATION
        g._update_difficulty()
        assert g.rope_speed >= 0.8

    def test_difficulty_scales_with_elapsed_time(self) -> None:
        g = _make_game()
        _setup_playing(g)
        g.timer = GAME_DURATION // 2
        g._update_difficulty()
        assert g.rope_speed > 0.8


class TestDataClasses:
    def test_segment_defaults(self) -> None:
        s = Segment(x=100.0, color=0)
        assert s.width == 24
        assert s.height == 12

    def test_particle_fields(self) -> None:
        p = Particle(x=0.0, y=0.0, vx=1.0, vy=-2.0, color=8, life=20)
        assert p.vx == 1.0
        assert p.vy == -2.0

    def test_floating_text_default_vy(self) -> None:
        ft = FloatingText(x=0.0, y=0.0, text="Hi", color=7, life=40)
        assert ft.vy == -1.0
