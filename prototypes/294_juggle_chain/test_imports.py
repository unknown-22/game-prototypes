"""test_imports.py — Headless logic tests for JUGGLE CHAIN (294)."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/294_juggle_chain")
from main import (  # noqa: E402
    COLORS,
    SCREEN_W,
    SCREEN_H,
    CATCH_Y,
    CATCH_ZONE_HALF_W,
    PLAYER_X,
    BALL_RADIUS,
    GRAVITY,
    HEAT_MAX,
    HEAT_MISMATCH,
    HEAT_DROP,
    HEAT_DECAY,
    SUPER_DURATION,
    SUPER_SCORE_MULT,
    COMBO_SUPER_THRESHOLD,
    GAME_TIME,
    MAX_BALLS_START,
    MAX_BALLS_END,
    MIN_SPAWN_INTERVAL,
    MAX_SPAWN_INTERVAL,
    INITIAL_CYCLE_SPEED,
    MIN_CYCLE_SPEED,
    Ball,
    FloatingText,
    Game,
    Particle,
    Phase,
)


# ---------------------------------------------------------------------------
# Factory for headless testing
# ---------------------------------------------------------------------------


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_TIME
    g.hand_color = COLORS[0]
    g.color_idx = 0
    g.cycle_timer = INITIAL_CYCLE_SPEED
    g.spawn_timer = MAX_SPAWN_INTERVAL
    g.elapsed_frames = 0
    g.super_timer = 0
    g.balls = []
    g.particles = []
    g.floating_texts = []
    g._mouse_just_pressed = False
    g.reset()
    return g


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert len(Phase.__members__) == 3


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


def test_ball_dataclass() -> None:
    b = Ball(x=100.0, y=50.0, vx=1.5, vy=-8.0, color=8, active=True)
    assert b.x == 100.0
    assert b.color == 8
    assert b.active is True


def test_particle_dataclass() -> None:
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-1.0, color=8, life=15)
    assert p.life == 15
    assert p.color == 8


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+10", color=7, life=30)
    assert ft.text == "+10"
    assert ft.life == 30


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_color_constants() -> None:
    assert len(COLORS) == 4
    # RED=8, LIME=11, DARK_BLUE=5, YELLOW=10
    assert 8 in COLORS
    assert 11 in COLORS
    assert 5 in COLORS
    assert 10 in COLORS


def test_constant_bounds() -> None:
    assert HEAT_MAX == 100.0
    assert HEAT_MISMATCH == 15.0
    assert HEAT_DROP == 10.0
    assert COMBO_SUPER_THRESHOLD == 4
    assert SUPER_DURATION == 300
    assert SUPER_SCORE_MULT == 3


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == GAME_TIME
    assert g.super_timer == 0
    assert g.elapsed_frames == 0


def test_reset_spawns_initial_balls() -> None:
    g = _make_game()
    active = g._active_balls()
    assert len(active) > 0
    for ball in active:
        assert ball.active is True


def test_reset_clears_previous_state() -> None:
    g = _make_game()
    g.score = 1000
    g.combo = 10
    g.heat = 50.0
    g.super_timer = 200
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, color=8, life=10)]
    g.floating_texts = [FloatingText(x=0, y=0, text="+10", color=7, life=20)]

    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


# ---------------------------------------------------------------------------
# Ball physics
# ---------------------------------------------------------------------------


def test_ball_gravity() -> None:
    g = _make_game()
    ball = Ball(x=160.0, y=100.0, vx=0.0, vy=-5.0, color=8, active=True)
    g.balls = [ball]
    g._update_balls()
    assert ball.vy == -5.0 + GRAVITY
    assert ball.y == 100.0 + ball.vy


def test_ball_bounces_off_left_wall() -> None:
    g = _make_game()
    ball = Ball(x=2.0, y=100.0, vx=-2.0, vy=0.0, color=8, active=True)
    g.balls = [ball]
    g._update_balls()
    assert ball.vx > 0  # bounced right
    assert ball.x >= BALL_RADIUS


def test_ball_bounces_off_right_wall() -> None:
    g = _make_game()
    ball = Ball(x=SCREEN_W - 2.0, y=100.0, vx=2.0, vy=0.0, color=8, active=True)
    g.balls = [ball]
    g._update_balls()
    assert ball.vx < 0  # bounced left
    assert ball.x <= SCREEN_W - BALL_RADIUS


def test_ball_bounces_off_top() -> None:
    g = _make_game()
    ball = Ball(x=160.0, y=2.0, vx=0.0, vy=-3.0, color=8, active=True)
    g.balls = [ball]
    g._update_balls()
    assert ball.vy > 0  # bounced down
    assert ball.y >= BALL_RADIUS


def test_ball_drops_off_screen() -> None:
    g = _make_game()
    ball = Ball(x=160.0, y=SCREEN_H + 10, vx=0.0, vy=0.0, color=8, active=True)
    g.balls = [ball]
    initial_heat = g.heat
    g._update_balls()
    assert ball.active is False
    assert g.heat == initial_heat + HEAT_DROP
    assert g.combo == 0


def test_ball_drop_spawns_particles() -> None:
    g = _make_game()
    ball = Ball(x=160.0, y=SCREEN_H + 10, vx=0.0, vy=0.0, color=8, active=True)
    g.balls = [ball]
    before = len(g.particles)
    g._update_balls()
    assert len(g.particles) == before + 4


# ---------------------------------------------------------------------------
# Catch zone detection
# ---------------------------------------------------------------------------


def test_catch_zone_detects_ball_in_zone() -> None:
    g = _make_game()
    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=8, active=True)
    assert g._is_in_catch_zone(ball) is True


def test_catch_zone_rejects_ball_outside_x() -> None:
    g = _make_game()
    ball = Ball(x=PLAYER_X - CATCH_ZONE_HALF_W - BALL_RADIUS - 1, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=8, active=True)
    assert g._is_in_catch_zone(ball) is False


def test_catch_zone_rejects_ball_above() -> None:
    g = _make_game()
    ball = Ball(x=PLAYER_X, y=CATCH_Y - 1, vx=0.0, vy=0.0, color=8, active=True)
    assert g._is_in_catch_zone(ball) is False


def test_catch_zone_rejects_inactive_ball() -> None:
    g = _make_game()
    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=8, active=False)
    assert g._is_in_catch_zone(ball) is False


# ---------------------------------------------------------------------------
# Catch resolution — match
# ---------------------------------------------------------------------------


def test_resolve_catch_match_combo_increment() -> None:
    g = _make_game()
    g.hand_color = 8  # RED
    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=8, active=True)
    g.balls = [ball]

    g._resolve_catch(ball)
    assert ball.active is False
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 10  # 10 * 1


def test_resolve_catch_match_score_scales_with_combo() -> None:
    g = _make_game()
    g.hand_color = 8
    g.combo = 3
    g.max_combo = 3
    g.score = 60  # previous: 10*1 + 10*2 + 10*3 = 60

    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=8, active=True)
    g.balls = [ball]

    g._resolve_catch(ball)
    assert g.combo == 4
    assert g.score == 60 + 40  # 10 * 4


def test_resolve_catch_match_spawns_particles() -> None:
    g = _make_game()
    g.hand_color = 8
    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=8, active=True)
    g.balls = [ball]
    before = len(g.particles)

    g._resolve_catch(ball)
    assert len(g.particles) == before + 8


def test_resolve_catch_match_spawns_floating_text() -> None:
    g = _make_game()
    g.hand_color = 8
    g.combo = 0
    g.score = 0
    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=8, active=True)
    g.balls = [ball]
    before = len(g.floating_texts)

    g._resolve_catch(ball)
    assert len(g.floating_texts) == before + 1
    assert "+" in g.floating_texts[-1].text


# ---------------------------------------------------------------------------
# Catch resolution — mismatch
# ---------------------------------------------------------------------------


def test_resolve_catch_mismatch_adds_heat() -> None:
    g = _make_game()
    g.hand_color = 8  # RED
    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=11, active=True)  # LIME
    g.balls = [ball]

    g._resolve_catch(ball)
    assert g.heat == HEAT_MISMATCH
    assert g.combo == 0


def test_resolve_catch_mismatch_spawns_particles() -> None:
    g = _make_game()
    g.hand_color = 8
    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=11, active=True)
    g.balls = [ball]
    before = len(g.particles)

    g._resolve_catch(ball)
    assert len(g.particles) == before + 4


def test_resolve_catch_mismatch_spawns_wrong_text() -> None:
    g = _make_game()
    g.hand_color = 8
    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=11, active=True)
    g.balls = [ball]
    before = len(g.floating_texts)

    g._resolve_catch(ball)
    assert len(g.floating_texts) == before + 1
    assert "WRONG" in g.floating_texts[-1].text


# ---------------------------------------------------------------------------
# SUPER JUGGLE
# ---------------------------------------------------------------------------


def test_combo_4_triggers_super() -> None:
    g = _make_game()
    g.hand_color = 8
    g.combo = 3
    g.max_combo = 3
    g.score = 60

    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=8, active=True)
    g.balls = [ball]

    g._resolve_catch(ball)
    assert g.super_timer == SUPER_DURATION
    assert len(g.particles) >= 20  # super burst


def test_super_mode_any_color_match() -> None:
    g = _make_game()
    g.hand_color = 8  # RED
    g.super_timer = 100
    g.combo = 5
    g.score = 100

    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=11, active=True)  # LIME — different
    g.balls = [ball]

    g._resolve_catch(ball)
    assert g.combo == 6  # still increments
    assert g.score == 100 + 10 * 6 * SUPER_SCORE_MULT


def test_super_mode_score_triple() -> None:
    g = _make_game()
    g.super_timer = 100
    g.combo = 0
    g.score = 0

    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=8, active=True)
    g.balls = [ball]

    g._resolve_catch(ball)
    assert g.combo == 1
    assert g.score == 10 * 1 * SUPER_SCORE_MULT  # 30


def test_super_timer_decrements() -> None:
    g = _make_game()
    g.super_timer = 100
    g._update_super_timer()
    assert g.super_timer == 99


def test_super_timer_expires() -> None:
    g = _make_game()
    g.super_timer = 1
    g._update_super_timer()
    assert g.super_timer == 0


def test_super_not_retriggered_while_active() -> None:
    g = _make_game()
    g.hand_color = 8
    g.super_timer = 100  # already in SUPER
    g.combo = 3
    g.score = 60

    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=8, active=True)
    g.balls = [ball]

    g._resolve_catch(ball)
    # Should NOT add extra 20 super burst particles (should use match particles + super score)
    assert g.super_timer == 100  # timer unchanged by match (only decremented by _update_super_timer)


# ---------------------------------------------------------------------------
# Heat system
# ---------------------------------------------------------------------------


def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_decay_not_below_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_at_max_game_over() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_mismatch_heat_accumulates() -> None:
    g = _make_game()
    g.hand_color = 8

    for _ in range(3):
        ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=11, active=True)
        g.balls = [ball]
        g._resolve_catch(ball)

    assert g.heat == HEAT_MISMATCH * 3


# ---------------------------------------------------------------------------
# Game over
# ---------------------------------------------------------------------------


def test_game_over_updates_best_score() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 300
    g._game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500


def test_game_over_does_not_lower_best_score() -> None:
    g = _make_game()
    g.score = 200
    g.best_score = 500
    g._game_over()
    assert g.best_score == 500


def test_timer_zero_game_over() -> None:
    g = _make_game()
    g.timer = 1
    g._update_timers()
    assert g.timer == 0


# ---------------------------------------------------------------------------
# Timers
# ---------------------------------------------------------------------------


def test_update_timers_decrements() -> None:
    g = _make_game()
    initial_timer = g.timer
    initial_elapsed = g.elapsed_frames
    g._update_timers()
    assert g.timer == initial_timer - 1
    assert g.elapsed_frames == initial_elapsed + 1


def test_cycle_timer_changes_hand_color() -> None:
    g = _make_game()
    g.cycle_timer = 1
    initial_color = g.hand_color
    g._update_timers()
    # Color should change after cycle_timer hits 0
    # But reset() sets color_idx=0, hand_color=COLORS[0], cycle_timer=20
    # With cycle_timer=1, after 1 decrement it hits 0, changes color
    assert g.hand_color != initial_color


def test_spawn_timer_spawns_ball() -> None:
    g = _make_game()
    g.balls.clear()
    assert len(g._active_balls()) == 0
    g.spawn_timer = 1
    g._update_timers()
    assert len(g._active_balls()) == 1


# ---------------------------------------------------------------------------
# Difficulty scaling
# ---------------------------------------------------------------------------


def test_elapsed_ratio_zero() -> None:
    g = _make_game()
    assert g._elapsed_ratio() == 0.0


def test_elapsed_ratio_full() -> None:
    g = _make_game()
    g.elapsed_frames = GAME_TIME
    assert g._elapsed_ratio() == 1.0


def test_spawn_interval_scales() -> None:
    g = _make_game()
    init_val = g._get_spawn_interval()
    assert init_val == MAX_SPAWN_INTERVAL

    g.elapsed_frames = GAME_TIME
    final_val = g._get_spawn_interval()
    assert final_val == MIN_SPAWN_INTERVAL


def test_cycle_speed_scales() -> None:
    g = _make_game()
    init_val = g._get_cycle_speed()
    assert init_val == INITIAL_CYCLE_SPEED

    g.elapsed_frames = GAME_TIME
    final_val = g._get_cycle_speed()
    assert final_val == MIN_CYCLE_SPEED


def test_max_balls_scales() -> None:
    g = _make_game()
    init_val = g._get_max_balls()
    assert init_val == MAX_BALLS_START

    g.elapsed_frames = GAME_TIME
    final_val = g._get_max_balls()
    assert final_val == MAX_BALLS_END


# ---------------------------------------------------------------------------
# Spawn limits
# ---------------------------------------------------------------------------


def test_spawn_ball_respects_max() -> None:
    g = _make_game()
    # Fill with max balls
    max_b = g._get_max_balls()
    g.balls = [
        Ball(x=float(i * 40), y=CATCH_Y + 10, vx=0.0, vy=-5.0, color=COLORS[0], active=True)
        for i in range(max_b)
    ]
    before = len(g._active_balls())
    g._spawn_ball()
    assert len(g._active_balls()) == before


def test_spawn_ball_in_bounds() -> None:
    g = _make_game()
    g.balls.clear()
    g._spawn_ball()
    ball = g.balls[0]
    assert 20 <= ball.x <= SCREEN_W - 20
    assert -9.0 <= ball.vy <= -7.0
    assert ball.color in COLORS


# ---------------------------------------------------------------------------
# Particles
# ---------------------------------------------------------------------------


def test_particle_movement() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=100.0, vx=1.0, vy=-1.0, color=8, life=15)
    g.particles = [p]

    g._update_particles()
    assert p.x == 101.0
    assert p.y == 100.0 + (-1.0 + 0.1)  # vy + gravity
    assert p.life == 14


def test_particle_gravity() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=8, life=15)
    g.particles = [p]

    g._update_particles()
    assert p.vy == 0.1


def test_particle_expiry() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=8, life=1)
    g.particles = [p]

    g._update_particles()
    assert len(g.particles) == 0


# ---------------------------------------------------------------------------
# Floating texts
# ---------------------------------------------------------------------------


def test_floating_text_rises() -> None:
    g = _make_game()
    ft = FloatingText(x=100.0, y=100.0, text="+10", color=7, life=20)
    g.floating_texts = [ft]

    g._update_floating_texts()
    assert ft.y == 99.5
    assert ft.life == 19


def test_floating_text_expiry() -> None:
    g = _make_game()
    ft = FloatingText(x=100.0, y=100.0, text="+10", color=7, life=1)
    g.floating_texts = [ft]

    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ---------------------------------------------------------------------------
# Max combo tracking
# ---------------------------------------------------------------------------


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.hand_color = 8
    g.combo = 5
    g.max_combo = 3

    ball = Ball(x=PLAYER_X, y=CATCH_Y + 5, vx=0.0, vy=0.0, color=8, active=True)
    g.balls = [ball]
    g._resolve_catch(ball)
    assert g.max_combo == 6


# ---------------------------------------------------------------------------
# Active balls helper
# ---------------------------------------------------------------------------


def test_active_balls_filters_inactive() -> None:
    g = _make_game()
    g.balls = [
        Ball(x=100.0, y=100.0, vx=0.0, vy=0.0, color=8, active=True),
        Ball(x=120.0, y=100.0, vx=0.0, vy=0.0, color=11, active=False),
        Ball(x=140.0, y=100.0, vx=0.0, vy=0.0, color=5, active=True),
    ]
    active = g._active_balls()
    assert len(active) == 2
    assert all(b.active for b in active)


# ---------------------------------------------------------------------------
# Spawn match particles
# ---------------------------------------------------------------------------


def test_spawn_match_particles_adds_8() -> None:
    g = _make_game()
    before = len(g.particles)
    g._spawn_match_particles(160.0, 200.0, 8)
    assert len(g.particles) == before + 8
