"""Tests for PING PONG SURGE game logic."""
from __future__ import annotations

import random
from unittest.mock import patch

import pytest

# Import game classes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import Ball, BallColor, BALL_COLORS, Game, Particle, Phase


def _make_game() -> Game:
    """Factory for a fresh Game instance in PLAYING state."""
    g = Game()
    g.reset()
    return g


def _make_ball(
    x: float = 160.0,
    y: float = 200.0,
    vx: float = 0.0,
    vy: float = 3.0,
    color: int = 0,
    speed: float = 3.0,
) -> Ball:
    return Ball(x=x, y=y, vx=vx, vy=vy, color=color, speed=speed)


# ============================================================
# 1. Paddle movement and clamping
# ============================================================


class TestPaddleMovement:
    def test_move_paddle_centers(self) -> None:
        g = _make_game()
        g._move_paddle(160.0)
        assert g.paddle_x == 140.0  # center - paddle_w/2

    def test_move_paddle_left_clamp(self) -> None:
        g = _make_game()
        g._move_paddle(0.0)
        assert g.paddle_x == 0.0

    def test_move_paddle_right_clamp(self) -> None:
        g = _make_game()
        g._move_paddle(400.0)
        assert g.paddle_x == Game.SCREEN_W - Game.PADDLE_W

    def test_cycle_paddle_color(self) -> None:
        g = _make_game()
        assert g.paddle_color == 0
        g._cycle_paddle_color(1)
        assert g.paddle_color == 1
        g._cycle_paddle_color(1)
        assert g.paddle_color == 2
        g._cycle_paddle_color(-1)
        assert g.paddle_color == 1
        # Wrap around
        g._cycle_paddle_color(-1)
        assert g.paddle_color == 0
        g._cycle_paddle_color(-1)
        assert g.paddle_color == 3

    def test_ai_paddle_moves_toward_ball(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=200.0)
        g.ai_paddle_x = 100.0
        g._move_ai_paddle()
        assert g.ai_paddle_x > 100.0  # moves right

    def test_ai_paddle_tracks_ball_exactly_when_close(self) -> None:
        g = _make_game()
        target = 150.0 - Game.PADDLE_W / 2  # ball at 150, paddle center should be there
        g.ball = _make_ball(x=150.0)
        g.ai_paddle_x = target - 1.0
        g._move_ai_paddle()
        assert g.ai_paddle_x == target

    def test_ai_paddle_clamped_left(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=-50.0)
        g.ai_paddle_x = 0.0
        g._move_ai_paddle()
        assert g.ai_paddle_x == 0.0


# ============================================================
# 2. Ball physics: bounce off walls, speed
# ============================================================


class TestBallPhysics:
    def test_ball_moves(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=160.0, y=100.0, vx=2.0, vy=3.0)
        g._update_ball()
        assert g.ball.x == 162.0
        assert g.ball.y == 103.0

    def test_ball_bounces_left_wall(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=3.0, y=100.0, vx=-4.0, vy=1.0)
        g._update_ball()
        assert g.ball.vx > 0  # reflected right

    def test_ball_bounces_right_wall(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=317.0, y=100.0, vx=4.0, vy=1.0)
        g._update_ball()
        assert g.ball.vx < 0  # reflected left

    def test_ball_bounces_top_wall(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=160.0, y=3.0, vx=1.0, vy=-4.0)
        g._update_ball()
        assert g.ball.vy > 0  # reflected down

    def test_ball_speed_ramp_on_rally(self) -> None:
        g = _make_game()
        g.rally_count = 10
        g._serve_ball()
        assert g.ball is not None
        expected = 3.0 + 10 * 0.08
        assert g.ball.speed == pytest.approx(expected)


# ============================================================
# 3. Color match/mismatch: combo increment/reset
# ============================================================


class TestColorMatching:
    def test_color_match_increments_combo(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0)
        g.paddle_color = 0  # match
        g.paddle_x = 140.0
        g._process_hit(is_player=True)
        assert g.combo == 1

    def test_color_mismatch_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 3
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0)
        g.paddle_color = 1  # mismatch
        g.paddle_x = 140.0
        g._process_hit(is_player=True)
        assert g.combo == 0

    def test_match_adds_score(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0)
        g.paddle_color = 0
        g.paddle_x = 140.0
        g._process_hit(is_player=True)
        assert g.score > 0

    def test_combo_multiplies_score(self) -> None:
        g = _make_game()
        g.combo = 3  # next hit -> combo 4, multiplier = 1 + 3*0.5 = 2.5
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0, speed=3.0)
        g.paddle_color = 0
        g.paddle_x = 140.0
        old_score = g.score
        g._process_hit(is_player=True)
        gained = g.score - old_score
        # base 10 * multiplier 2.5 = 25
        assert gained == 25

    def test_max_combo_tracks_highest(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0)
        g.paddle_color = 0
        g.paddle_x = 140.0
        g._process_hit(is_player=True)
        assert g.max_combo == 1

        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0)
        g.combo = 2
        g._process_hit(is_player=True)
        assert g.max_combo == 3

        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=1)
        g.paddle_color = 2  # mismatch (paddle 2 vs ball 1)
        g._process_hit(is_player=True)
        assert g.combo == 0
        assert g.max_combo == 3  # unchanged


# ============================================================
# 4. Heat accumulation and decay
# ============================================================


class TestHeat:
    def test_heat_decays_over_time(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert g.heat == pytest.approx(49.8)

    def test_heat_does_not_go_negative(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_gained_on_match(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0, speed=4.0)
        g.paddle_color = 0
        g.paddle_x = 140.0
        old_heat = g.heat
        g._process_hit(is_player=True)
        assert g.heat > old_heat

    def test_smash_adds_more_heat(self) -> None:
        g = _make_game()
        # Ball far from paddle center -> not smash
        # paddle_x=130, center=150, ball at 170 -> dist=20, paddle_w/4=10 -> not smash
        g.ball = _make_ball(x=170.0, y=205.0, vy=2.0, color=0, speed=4.0)
        g.paddle_color = 0
        g.paddle_x = 130.0
        g._process_hit(is_player=True)
        heat_normal = g.heat

        g.reset()
        # Ball near paddle center -> smash
        # paddle_x=140, center=160, ball at 162 -> dist=2, paddle_w/4=10 -> smash
        g.ball = _make_ball(x=162.0, y=205.0, vy=2.0, color=0, speed=4.0)
        g.paddle_color = 0
        g.paddle_x = 140.0
        g._process_hit(is_player=True)
        heat_smash = g.heat

        assert heat_smash > heat_normal


# ============================================================
# 5. Super rally activation at COMBO >= 5
# ============================================================


class TestSuperRally:
    def test_super_rally_activates_at_combo_5(self) -> None:
        g = _make_game()
        g.combo = 4
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0)
        g.paddle_color = 0
        g.paddle_x = 140.0
        g._process_hit(is_player=True)
        assert g.super_timer == Game.SUPER_DURATION

    def test_super_rally_does_not_activate_below_combo_5(self) -> None:
        g = _make_game()
        g.combo = 3
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0)
        g.paddle_color = 0
        g.paddle_x = 140.0
        g._process_hit(is_player=True)
        assert g.super_timer == 0

    def test_super_timer_counts_down(self) -> None:
        g = _make_game()
        g.super_timer = 60
        g.serve_ready = False
        g._update_super_timer()
        assert g.super_timer == 59

    def test_super_rally_auto_matches_color(self) -> None:
        g = _make_game()
        g.super_timer = 60
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0)
        g.paddle_color = 1  # mismatch normally, but super overrides
        g.paddle_x = 140.0
        g._process_hit(is_player=True)
        assert g.combo == 1  # counts as match

    def test_super_rally_3x_score(self) -> None:
        g = _make_game()
        g.super_timer = 60
        g.combo = 0
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0, speed=3.0)
        g.paddle_color = 0
        g.paddle_x = 140.0
        old_score = g.score
        g._process_hit(is_player=True)
        # base 10 * combo multiplier 1.0 * super 3x = 30
        assert g.score - old_score == 30


# ============================================================
# 6. Overheat activation at HEAT >= 100
# ============================================================


class TestOverheat:
    def test_overheat_activates_at_heat_100(self) -> None:
        g = _make_game()
        g.heat = 100.0
        g._update_heat()
        assert g.overheat_timer == Game.OVERHEAT_DURATION

    def test_overheat_timer_counts_down(self) -> None:
        g = _make_game()
        g.overheat_timer = 10
        g._update_heat()
        assert g.overheat_timer == 9

    def test_heat_resets_after_overheat(self) -> None:
        g = _make_game()
        g.overheat_timer = 1
        g.heat = 100.0
        g._update_heat()
        assert g.overheat_timer == 0
        assert g.heat == 0.0

    def test_shake_during_overheat(self) -> None:
        g = _make_game()
        g.overheat_timer = 50
        g._update_shake()
        # Should produce some shake offset
        assert g.shake_offset_x != 0 or g.shake_offset_y != 0

    def test_no_shake_without_overheat(self) -> None:
        g = _make_game()
        g.overheat_timer = 0
        g._update_shake()
        assert g.shake_offset_x == 0
        assert g.shake_offset_y == 0


# ============================================================
# 7. Game over on miss
# ============================================================


class TestGameOver:
    def test_miss_triggers_game_over(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=160.0, y=250.0, vy=5.0)  # below screen
        g.phase = Phase.PLAYING
        g._update_ball()
        assert g.phase == Phase.GAME_OVER

    def test_game_over_updates_high_score(self) -> None:
        g = _make_game()
        g.score = 500
        g.high_score = 100
        g.ball = _make_ball(x=160.0, y=250.0, vy=5.0)
        g.phase = Phase.PLAYING
        g._update_ball()
        assert g.high_score == 500

    def test_game_timer_expiry_triggers_miss(self) -> None:
        g = _make_game()
        g.game_timer = 1
        g.serve_ready = False
        g.ball = _make_ball(x=160.0, y=100.0, vy=1.0)
        g.phase = Phase.PLAYING
        g.update()
        assert g.phase == Phase.GAME_OVER

    def test_ball_not_missed_when_above_screen(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=160.0, y=200.0, vy=3.0)
        g.phase = Phase.PLAYING
        g._update_ball()
        assert g.phase == Phase.PLAYING  # not yet missed


# ============================================================
# 8. Score computation
# ============================================================


class TestScoreComputation:
    def test_base_score_on_first_hit(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0)
        g.paddle_color = 0
        g.paddle_x = 140.0
        g._process_hit(is_player=True)
        assert g.score == 10

    def test_smash_gives_more_score(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0, speed=4.0)
        g.paddle_color = 0
        g.paddle_x = 140.0  # center at 160, ball at 160 -> smash
        g._process_hit(is_player=True)
        assert g.score == 15  # smash base score

    def test_combo_multiplier_increases_with_combo(self) -> None:
        g = _make_game()
        g.combo = 4
        g.ball = _make_ball(x=160.0, y=205.0, vy=2.0, color=0, speed=3.0)
        g.paddle_color = 0
        g.paddle_x = 140.0
        g._process_hit(is_player=True)
        # combo becomes 5, multiplier = 1 + 4*0.5 = 3.0, base = 10, total = 30
        assert g.score == 30


# ============================================================
# 9. Particle lifecycle
# ============================================================


class TestParticles:
    def test_spawn_particles_creates_correct_count(self) -> None:
        g = _make_game()
        g._spawn_particles(160.0, 120.0, 8, 10)
        assert len(g.particles) == 10

    def test_particles_decay_and_remove(self) -> None:
        g = _make_game()
        g._spawn_particles(160.0, 120.0, 8, 3)
        assert len(g.particles) == 3
        # Force particles to die
        for p in g.particles:
            p.life = 0
        g._update_particles()
        assert len(g.particles) == 0

    def test_particles_move(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 1)
        p = g.particles[0]
        old_x, old_y = p.x, p.y
        g._update_particles()
        assert p.x != old_x or p.y != old_y


# ============================================================
# 10. reset() restores clean state
# ============================================================


class TestReset:
    def test_reset_clears_all_state(self) -> None:
        g = Game()
        g.score = 999
        g.combo = 10
        g.max_combo = 20
        g.heat = 80.0
        g.rally_count = 50
        g.particles = [Particle(0, 0, 0, 0, 10, 8)]
        g.shake_offset_x = 5
        g.shake_offset_y = 5
        g.super_timer = 100
        g.overheat_timer = 100
        g.game_timer = 100

        g.reset()

        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.ball is None
        assert g.heat == 0.0
        assert g.rally_count == 0
        assert len(g.particles) == 0
        assert g.shake_offset_x == 0
        assert g.shake_offset_y == 0
        assert g.super_timer == 0
        assert g.overheat_timer == 0
        assert g.game_timer == Game.GAME_TIME
        assert g.serve_ready is True

    def test_reset_centers_paddle(self) -> None:
        g = Game()
        g.paddle_x = 0.0
        g.ai_paddle_x = 300.0
        g.reset()
        assert g.paddle_x == Game.SCREEN_W / 2 - Game.PADDLE_W / 2
        assert g.ai_paddle_x == Game.SCREEN_W / 2 - Game.PADDLE_W / 2


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    def test_ball_at_corner_bounces_both_axes(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=2.0, y=2.0, vx=-3.0, vy=-3.0)
        g._update_ball()
        assert g.ball is not None
        assert g.ball.vx > 0  # bounced right
        assert g.ball.vy > 0  # bounced down

    def test_paddle_at_edge_clamps(self) -> None:
        g = _make_game()
        g._move_paddle(-50.0)
        assert g.paddle_x == 0.0
        g._move_paddle(500.0)
        assert g.paddle_x == Game.SCREEN_W - Game.PADDLE_W

    def test_serve_ready_no_ball_update(self) -> None:
        g = _make_game()
        g.serve_ready = True
        g.ball = _make_ball(x=160.0, y=200.0, vy=3.0)
        g.update()
        # Ball should not have moved (serve_ready prevents ball update)
        assert g.ball.x == 160.0
        assert g.ball.y == 200.0

    def test_ai_hit_bounces_ball_both_directions(self) -> None:
        g = _make_game()
        g.ball = _make_ball(x=160.0, y=35.0, vy=-3.0, color=2)
        g.ai_paddle_color = 2  # color match
        g.ai_paddle_x = 140.0
        g._check_ai_hit()
        assert g.ball is not None
        assert g.ball.vy > 0  # reflected down

    def test_game_timer_at_zero_stops(self) -> None:
        g = _make_game()
        g.game_timer = 0
        g.phase = Phase.PLAYING
        g.ball = _make_ball()
        g.serve_ready = False
        g.update()
        assert g.phase == Phase.GAME_OVER

    def test_high_score_persists_across_resets(self) -> None:
        g = _make_game()
        g.score = 500
        g.high_score = 100
        g.ball = _make_ball(x=160.0, y=250.0, vy=5.0)
        g.phase = Phase.PLAYING
        g._update_ball()
        assert g.high_score == 500
        g.reset()
        assert g.high_score == 500  # preserved
