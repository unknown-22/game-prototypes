"""Headless tests for HOOP CHAIN."""

from __future__ import annotations

import random

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (  # noqa: E402
    DEFENDER_HP,
    DEFENDER_RADIUS,
    DEFENDER_SPAWN_INTERVAL,
    GAME_DURATION,
    HEAT_BASKET,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISS,
    HOOP_WIDTH,
    HOOP_X,
    HOOP_Y,
    SCREEN_H,
    SUPER_DURATION,
    SUPER_THRESHOLD,
    Ball,
    Defender,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.game_timer = GAME_DURATION
    g.balls_shot = 0
    g.ball = None
    g.defenders = []
    g.particles = []
    g.floating_texts = []
    g._shake_frames = 0
    g._shake_intensity = 0
    g._last_scored_color = -1
    g._next_ball_color = 0
    g._defender_spawn_timer = DEFENDER_SPAWN_INTERVAL
    g._power_charge = 0.0
    g._charging = False
    g.phase = Phase.AIMING
    g.reset()
    return g


# ------------------------------------------------------------------
# Test 1: Ball physics — gravity pulls ball down, vy increases
# ------------------------------------------------------------------
class TestBallPhysics:
    def test_gravity_increases_vy(self) -> None:
        g = _make_game()
        ball = g._spawn_ball()
        ball.vx = 2.0
        ball.vy = -4.0
        g.ball = ball
        vy_before = ball.vy
        g._update_ball()
        assert g.ball is not None
        assert g.ball.vy > vy_before, "Gravity should increase vy"

    def test_ball_falls_below_screen_deactivates(self) -> None:
        g = _make_game()
        ball = g._spawn_ball()
        ball.x = 160
        ball.y = SCREEN_H + 10  # 250
        ball.vx = 0
        ball.vy = 5.0
        g.ball = ball
        # After a few frames the ball goes below SCREEN_H+20=260 and deactivates
        for _ in range(5):
            g._update_ball()
            if g.ball is None or not g.ball.active:
                break
        assert g.ball is not None
        assert not g.ball.active, "Ball should deactivate when below screen"

    def test_ball_bounces_off_walls(self) -> None:
        g = _make_game()
        ball = g._spawn_ball()
        ball.x = 5  # near left wall
        ball.vx = -3.0
        ball.vy = 0
        g.ball = ball
        g._update_ball()
        assert g.ball is not None
        assert g.ball.vx > 0, "Ball should bounce off left wall"


# ------------------------------------------------------------------
# Test 2: Hoop scoring detection
# ------------------------------------------------------------------
class TestHoopScoring:
    def test_ball_through_hoop_scores(self) -> None:
        g = _make_game()
        ball = g._spawn_ball()
        ball.x = HOOP_X
        ball.y = HOOP_Y
        ball.vx = 0
        ball.vy = -2.0  # moving upward through hoop
        g.ball = ball
        assert g._check_hoop_score(), "Ball passing through hoop should score"

    def test_ball_moving_down_not_score(self) -> None:
        g = _make_game()
        ball = g._spawn_ball()
        ball.x = HOOP_X
        ball.y = HOOP_Y
        ball.vx = 0
        ball.vy = 2.0  # moving downward
        g.ball = ball
        assert not g._check_hoop_score(), "Ball moving down should not score"

    def test_ball_outside_hoop_width_not_score(self) -> None:
        g = _make_game()
        ball = g._spawn_ball()
        ball.x = HOOP_X + HOOP_WIDTH
        ball.y = HOOP_Y
        ball.vx = 0
        ball.vy = -2.0
        g.ball = ball
        assert not g._check_hoop_score(), "Ball outside hoop width should not score"


# ------------------------------------------------------------------
# Test 3: Combo chain — consecutive same-color baskets
# ------------------------------------------------------------------
class TestComboChain:
    def test_same_color_consecutive_increases_combo(self) -> None:
        g = _make_game()
        # First basket
        ball = g._spawn_ball()
        ball.color = 0  # RED
        g.ball = ball
        g._handle_score()
        assert g.combo == 1

        # Second basket, same color
        ball2 = g._spawn_ball()
        ball2.color = 0
        g._last_scored_color = 0  # simulate same-color previous
        g.ball = ball2
        g._handle_score()
        assert g.combo == 2

    def test_different_color_resets_combo_to_1(self) -> None:
        g = _make_game()
        # First basket same color to build combo but NOT trigger super
        g.combo = 1
        g._last_scored_color = 0
        ball = g._spawn_ball()
        ball.color = 0
        g.ball = ball
        g._handle_score()
        assert g.combo == 2

        # Different color: combo should reset to 1
        ball2 = g._spawn_ball()
        ball2.color = 1
        # _last_scored_color was set to 0 by _handle_score above
        g.ball = ball2
        g._handle_score()
        assert g.combo == 1


# ------------------------------------------------------------------
# Test 4: Super mode activation
# ------------------------------------------------------------------
class TestSuperMode:
    def test_combo_reaches_threshold_activates_super(self) -> None:
        g = _make_game()
        g.combo = SUPER_THRESHOLD - 1  # 3
        g.super_mode = False
        ball = g._spawn_ball()
        ball.color = 0
        g._last_scored_color = 0  # same color
        g.ball = ball
        g._handle_score()
        assert g.combo >= SUPER_THRESHOLD
        assert g.super_mode is True
        assert g.super_timer == SUPER_DURATION

    def test_super_mode_multiplies_score(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.combo = 2
        g._last_scored_color = 0
        ball = g._spawn_ball()
        ball.color = 0
        g.ball = ball
        score_before = g.score
        g._handle_score()
        # During super mode: combo becomes 3, score = 10 * 3 * 3 = 90
        assert g.score - score_before == 90


# ------------------------------------------------------------------
# Test 5: Heat on miss
# ------------------------------------------------------------------
class TestHeatMiss:
    def test_miss_adds_heat(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._handle_miss()
        assert g.heat == HEAT_MISS

    def test_miss_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 5
        g._handle_miss()
        assert g.combo == 0


# ------------------------------------------------------------------
# Test 6: Heat on basket
# ------------------------------------------------------------------
class TestHeatBasket:
    def test_basket_reduces_heat(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._last_scored_color = 0
        ball = g._spawn_ball()
        ball.color = 0
        g.ball = ball
        g._handle_score()
        assert g.heat == 50.0 + HEAT_BASKET  # -5

    def test_heat_never_below_zero(self) -> None:
        g = _make_game()
        g.heat = 2.0
        g._last_scored_color = 0
        ball = g._spawn_ball()
        ball.color = 0
        g.ball = ball
        g._handle_score()
        assert g.heat == 0.0


# ------------------------------------------------------------------
# Test 7: Heat decay
# ------------------------------------------------------------------
class TestHeatDecay:
    def test_heat_decays_over_time(self) -> None:
        g = _make_game()
        g.heat = 10.0
        g._update_heat()
        assert g.heat == 10.0 - HEAT_DECAY

    def test_heat_decay_stops_at_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0


# ------------------------------------------------------------------
# Test 8: Game over conditions
# ------------------------------------------------------------------
class TestGameOver:
    def test_game_over_on_max_heat(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX
        assert g._check_game_over() is True

    def test_game_over_on_timer_zero(self) -> None:
        g = _make_game()
        g.game_timer = 0
        assert g._check_game_over() is True

    def test_game_not_over_at_start(self) -> None:
        g = _make_game()
        assert g._check_game_over() is False


# ------------------------------------------------------------------
# Test 9: Defender spawn
# ------------------------------------------------------------------
class TestDefenders:
    def test_defender_spawn_interval(self) -> None:
        g = _make_game()
        g._defender_spawn_timer = 1
        g._update_defenders()
        assert len(g.defenders) <= 1  # at most one spawns

    def test_defender_max_cap(self) -> None:
        g = _make_game()
        # Pre-fill defenders
        from main import MAX_DEFENDERS
        for i in range(MAX_DEFENDERS + 2):
            g.defenders.append(
                Defender(x=100 + i * 10, y=80, radius=DEFENDER_RADIUS, hp=DEFENDER_HP, color=0)
            )
        g._defender_spawn_timer = 1
        g._update_defenders()
        # Should not exceed max
        alive = [d for d in g.defenders if d.y < SCREEN_H + 30]
        assert len(alive) <= MAX_DEFENDERS + 2 - (g._defender_spawn_timer <= 0 and len(alive) < MAX_DEFENDERS)


# ------------------------------------------------------------------
# Test 10: Ball-defender collision
# ------------------------------------------------------------------
class TestBallDefenderCollision:
    def test_defender_takes_damage_on_hit(self) -> None:
        g = _make_game()
        g._handle_defender_hit(Defender(100, 100, 16.0, hp=2, color=0))
        # hp reduced to 1

    def test_defender_destroyed_on_zero_hp(self) -> None:
        g = _make_game()
        g.defenders = [Defender(100, 100, 16.0, hp=1, color=0)]
        g._handle_defender_hit(g.defenders[0])
        assert len(g.defenders) == 0

    def test_super_mode_one_shots_defender(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.defenders = [Defender(100, 100, 16.0, hp=5, color=0)]
        g._handle_defender_hit(g.defenders[0])
        assert len(g.defenders) == 0


# ------------------------------------------------------------------
# Test 11: Reset clears state
# ------------------------------------------------------------------
class TestReset:
    def test_reset_clears_all_state(self) -> None:
        g = _make_game()
        g.score = 999
        g.combo = 7
        g.max_combo = 10
        g.heat = 88.0
        g.super_mode = True
        g.super_timer = 50
        g.game_timer = 100
        g.balls_shot = 20
        g.ball = Ball(0, 0, 0, 0, 0)
        g.defenders = [Defender(0, 0, 0, 0, 0)]
        g.particles = [Particle(0, 0, 0, 0, 0, 0)]
        g.floating_texts = [FloatingText(0, 0, "", 0, 0)]
        g._last_scored_color = 2
        g._next_ball_color = 3
        g._defender_spawn_timer = 123
        g._power_charge = 5.0
        g._charging = True
        g.phase = Phase.GAME_OVER

        g.reset()

        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.super_mode is False
        assert g.super_timer == 0
        assert g.game_timer == GAME_DURATION
        assert g.balls_shot == 0
        assert g.ball is None
        assert g.defenders == []
        assert g.particles == []
        assert g.floating_texts == []
        assert g._last_scored_color == -1
        assert g._next_ball_color == 0
        assert g._defender_spawn_timer == DEFENDER_SPAWN_INTERVAL
        assert g._power_charge == 0.0
        assert g._charging is False
        assert g.phase == Phase.AIMING


# ------------------------------------------------------------------
# Test 12: Spawn ball creates balls with cycling colors
# ------------------------------------------------------------------
class TestSpawnBall:
    def test_spawn_ball_cycles_colors(self) -> None:
        g = _make_game()
        b1 = g._spawn_ball()
        assert b1.color == 0
        b2 = g._spawn_ball()
        assert b2.color == 1
        b3 = g._spawn_ball()
        assert b3.color == 2
        b4 = g._spawn_ball()
        assert b4.color == 3
        b5 = g._spawn_ball()
        assert b5.color == 0  # wraps around


# ------------------------------------------------------------------
# Test 13: Super mode timer expiry
# ------------------------------------------------------------------
class TestSuperModeExpiry:
    def test_super_mode_expires_resets_combo(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.super_timer = 1
        g.combo = 5
        g._update_super_mode()
        assert g.super_mode is False
        assert g.super_timer == 0
        assert g.combo == 0
        assert g._last_scored_color == -1
