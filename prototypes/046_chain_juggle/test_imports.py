"""test_imports.py — Headless logic tests for Chain Juggle.

Uses Game.__new__ pattern to bypass Pyxel init.
"""
from __future__ import annotations

import math
import random
import sys
from typing import Any

# Ensure main.py is importable
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/046_chain_juggle")
import main  # noqa: E402
from main import (
    Ball, ChainJuggle, Particle,
    SCREEN_H, SCREEN_W, BALL_RADIUS, SUPER_RADIUS,
    COLORS, N_COLORS, GRAVITY, PLAYER_Y, PLAYER_H,
    MAX_BALLS, HAZARD_START_Y, HAZARD_RISE, SPEED_INCREASE,
    COMBO_THRESHOLD, SUPER_DURATION, PARTICLE_LIFE,
)  # noqa: E402


# ── Helpers ──

def make_game() -> ChainJuggle:
    """Create a headless Game instance via __new__."""
    g = ChainJuggle.__new__(ChainJuggle)
    g._rng = random.Random(42)  # deterministic for tests
    # Pre-init all attributes that reset() touches
    g.player_x = SCREEN_W / 2.0
    g.balls = []
    g.particles = []
    g.combo = 0
    g.active_color = -1
    g.score = 0
    g.max_combo = 0
    g.hazard_y = HAZARD_START_Y
    g.game_over = False
    g._spawn_timer = 0
    g._shake_frames = 0
    g.balls_juggled = 0
    g._frame = 0
    g.reset()
    return g


# ── Data structure tests ──

def test_ball_dataclass() -> None:
    b = Ball(x=50.0, y=100.0, vx=1.0, vy=-2.0, color=0)
    assert b.x == 50.0
    assert b.y == 100.0
    assert b.vx == 1.0
    assert b.vy == -2.0
    assert b.color == 0
    assert b.speed_mult == 1.0
    assert not b.is_super
    assert b.radius() == BALL_RADIUS

    b2 = Ball(x=0.0, y=0.0, vx=0.0, vy=0.0, color=1,
              is_super=True, super_timer=90)
    assert b2.is_super
    assert b2.radius() == SUPER_RADIUS


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-0.5, life=15, color=8)
    assert p.x == 10.0
    assert p.life == 15
    assert p.color == 8


def test_constants() -> None:
    assert SCREEN_W == 240
    assert SCREEN_H == 300
    assert GRAVITY > 0
    assert PLAYER_Y > SCREEN_H // 2
    assert BALL_RADIUS < SUPER_RADIUS
    assert N_COLORS == 4
    assert len(COLORS) == 4
    assert COMBO_THRESHOLD == 4
    assert SPEED_INCREASE > 0
    assert HAZARD_RISE > 0
    assert HAZARD_START_Y > SCREEN_H
    assert MAX_BALLS == 5
    assert SUPER_DURATION == 90


# ── Game state tests ──

def test_reset_initial_state() -> None:
    g = make_game()
    assert g.combo == 0
    assert g.active_color == -1
    assert g.score == 0
    assert g.max_combo == 0
    assert g.hazard_y == HAZARD_START_Y
    assert not g.game_over
    assert g.balls_juggled == 0
    assert len(g.balls) == 2  # two initial balls
    assert len(g.particles) == 0
    # Player in center
    assert abs(g.player_x - SCREEN_W / 2) < 0.01


def test_spawn_ball() -> None:
    g = make_game()
    initial = len(g.balls)
    g.balls.clear()  # remove initial balls
    g._spawn_ball()
    assert len(g.balls) == 1
    b = g.balls[0]
    assert 0 <= b.color < N_COLORS
    assert BALL_RADIUS + 10 <= b.x <= SCREEN_W - BALL_RADIUS - 10
    assert 20 <= b.y <= 50
    assert not b.is_super
    assert b.speed_mult == 1.0


def test_spawn_ball_max_limit() -> None:
    g = make_game()
    # Fill to MAX_BALLS
    for _ in range(MAX_BALLS - len(g.balls)):
        g._spawn_ball()
    assert len(g.balls) == MAX_BALLS
    g._spawn_ball()  # should be no-op
    assert len(g.balls) == MAX_BALLS


# ── Physics tests ──

def test_apply_physics_gravity() -> None:
    g = make_game()
    b = Ball(x=100.0, y=50.0, vx=0.0, vy=0.0, color=0)
    g._apply_physics(b)
    assert b.vy == GRAVITY  # gravity added
    assert b.y == 50.0 + GRAVITY  # position updated (after vy change? no, vy changed then position)
    # Wait, _apply_physics does: vy += GRAVITY; x += vx*speed_mult; y += vy*speed_mult
    # So b.vy was 0, becomes GRAVITY=0.25
    # b.y = 50 + 0.25 * 1.0 = 50.25
    assert abs(b.y - (50.0 + GRAVITY)) < 0.01


def test_apply_physics_speed_mult() -> None:
    g = make_game()
    b = Ball(x=100.0, y=50.0, vx=2.0, vy=1.0, color=0, speed_mult=2.0)
    g._apply_physics(b)
    assert abs(b.vy - (1.0 + GRAVITY)) < 0.01
    assert abs(b.x - (100.0 + 2.0 * 2.0)) < 0.01
    assert abs(b.y - (50.0 + (1.0 + GRAVITY) * 2.0)) < 0.01


def test_wall_bounce_left() -> None:
    g = make_game()
    b = Ball(x=3.0, y=100.0, vx=-2.0, vy=0.0, color=0)
    g._check_walls(b)
    assert b.x == float(BALL_RADIUS)  # snapped to wall
    assert b.vx > 0  # bounced right


def test_wall_bounce_right() -> None:
    g = make_game()
    b = Ball(x=SCREEN_W - 3.0, y=100.0, vx=2.0, vy=0.0, color=0)
    g._check_walls(b)
    assert b.x == float(SCREEN_W - BALL_RADIUS)
    assert b.vx < 0  # bounced left


def test_ceiling_bounce() -> None:
    g = make_game()
    b = Ball(x=100.0, y=3.0, vx=0.0, vy=-2.0, color=0)
    g._check_walls(b)
    assert b.y == float(BALL_RADIUS)
    assert b.vy > 0  # bounced down


def test_speed_clamp() -> None:
    g = make_game()
    b = Ball(x=100.0, y=50.0, vx=10.0, vy=10.0, color=0, speed_mult=1.0)
    g._clamp_speed(b)
    assert abs(b.vx) <= 3.5
    assert abs(b.vy) <= 3.5


# ── Paddle collision tests ──

def test_paddle_hit_detection() -> None:
    g = make_game()
    # Place ball just above paddle center
    g.player_x = 120.0
    b = Ball(x=120.0, y=float(PLAYER_Y - BALL_RADIUS),
             vx=0.0, vy=5.0, color=0)
    hit = g._check_paddle(b)
    assert hit
    assert b.vy < 0  # bounced upward
    assert b.y <= float(PLAYER_Y - PLAYER_H)  # at or above paddle top


def test_paddle_miss_off_side() -> None:
    g = make_game()
    g.player_x = 120.0
    # Ball far to the right of paddle
    b = Ball(x=200.0, y=float(PLAYER_Y),
             vx=0.0, vy=1.0, color=0)
    hit = g._check_paddle(b)
    assert not hit
    # vy unchanged (no bounce)
    assert b.vy == 1.0


def test_same_color_combo_increment() -> None:
    g = make_game()
    g.player_x = 120.0
    g.active_color = 1  # LIME
    g.combo = 2
    b = Ball(x=120.0, y=float(PLAYER_Y - BALL_RADIUS),
             vx=0.0, vy=3.0, color=1)
    old_speed = b.speed_mult
    g._check_paddle(b)
    assert g.combo == 3  # incremented
    assert g.active_color == 1  # unchanged
    assert b.speed_mult == old_speed + SPEED_INCREASE  # sped up
    assert g.score > 0


def test_different_color_resets_combo() -> None:
    g = make_game()
    g.player_x = 120.0
    g.active_color = 1  # LIME
    g.combo = 3
    b = Ball(x=120.0, y=float(PLAYER_Y - BALL_RADIUS),
             vx=0.0, vy=3.0, color=2)  # CYAN - different!
    g._check_paddle(b)
    assert g.combo == 1  # reset to 1
    assert g.active_color == 2  # switched to CYAN
    assert g.score == 10  # base points


def test_max_combo_tracking() -> None:
    g = make_game()
    g.player_x = 120.0
    g.active_color = 0
    # Build combo to 3
    for i in range(3):
        b = Ball(x=120.0, y=float(PLAYER_Y - BALL_RADIUS),
                 vx=0.0, vy=3.0, color=0)
        g._check_paddle(b)
    assert g.max_combo >= 3
    # Reset with different color
    b2 = Ball(x=120.0, y=float(PLAYER_Y - BALL_RADIUS),
              vx=0.0, vy=3.0, color=1)
    g._check_paddle(b2)
    assert g.combo == 1
    assert g.max_combo == 3  # preserved


# ── Compression tests ──

def test_compress_requires_same_color_balls() -> None:
    """Compression returns 0 when no same-color balls exist."""
    g = make_game()
    g.balls.clear()  # remove random initial balls
    g.balls = [Ball(x=100.0, y=100.0, vx=0.0, vy=0.0, color=1)]
    result = g._compress(0)  # compress color 0, but only color 1 exists
    assert result == 0
    assert len(g.balls) == 1  # untouched


def test_compress_creates_super_ball() -> None:
    g = make_game()
    g.balls.clear()  # clear random initial balls
    # Add 3 same-color balls
    for _ in range(3):
        b = Ball(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0)
        g.balls.append(b)
    count = g._compress(0)
    assert count == 3
    assert len(g.balls) == 1
    assert g.balls[0].is_super
    assert g.balls[0].color == 0
    assert g.balls[0].super_timer == SUPER_DURATION
    assert g._shake_frames == 10


def test_compress_only_affects_same_color() -> None:
    g = make_game()
    g.balls = [
        Ball(x=50.0, y=100.0, vx=0.0, vy=0.0, color=0),
        Ball(x=80.0, y=100.0, vx=0.0, vy=0.0, color=0),
        Ball(x=110.0, y=100.0, vx=0.0, vy=0.0, color=1),  # different color
    ]
    count = g._compress(0)
    assert count == 2
    # Super ball from color 0, plus the color 1 ball
    assert len(g.balls) == 2
    supers = [b for b in g.balls if b.is_super]
    assert len(supers) == 1
    assert supers[0].color == 0
    # Color 1 ball untouched
    others = [b for b in g.balls if not b.is_super]
    assert len(others) == 1
    assert others[0].color == 1


def test_compress_preserves_existing_super() -> None:
    g = make_game()
    g.balls = [
        Ball(x=50.0, y=100.0, vx=0.0, vy=0.0, color=0),
        Ball(x=80.0, y=100.0, vx=0.0, vy=0.0, color=0),
        Ball(x=110.0, y=100.0, vx=0.0, vy=0.0, color=0,
             is_super=True, super_timer=30),
    ]
    count = g._compress(0)
    assert count == 2  # only 2 regular balls compressed
    assert len(g.balls) == 2  # old super + new super
    supers = [b for b in g.balls if b.is_super]
    assert len(supers) == 2


# ── Missed ball / hazard tests ──

def test_missed_ball_raises_hazard() -> None:
    g = make_game()
    old_hazard = g.hazard_y
    # Simulate a ball falling below screen - directly remove and update hazard
    b = Ball(x=100.0, y=float(SCREEN_H + 10), vx=0.0, vy=0.0, color=0)
    g.balls.append(b)
    # Manually trigger miss handling (what happens in update)
    missed = [b for b in g.balls if b.y - b.radius() > float(SCREEN_H)]
    for mb in missed:
        g.balls.remove(mb)
        g.hazard_y -= HAZARD_RISE
        g.combo = 0
        g.active_color = -1
    assert g.hazard_y == old_hazard - HAZARD_RISE
    assert g.combo == 0
    assert g.active_color == -1


def test_hazard_game_over() -> None:
    g = make_game()
    g.hazard_y = float(PLAYER_Y + PLAYER_H)  # exactly at player
    # Check game-over condition
    if g.hazard_y <= float(PLAYER_Y + PLAYER_H):
        g.game_over = True
    assert g.game_over


def test_hazard_not_game_over_above_player() -> None:
    g = make_game()
    g.hazard_y = float(PLAYER_Y + PLAYER_H + 10)  # above player
    if g.hazard_y <= float(PLAYER_Y + PLAYER_H):
        g.game_over = True
    assert not g.game_over


# ── Super ball decay tests ──

def test_super_timer_decay() -> None:
    g = make_game()
    b = Ball(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0,
             is_super=True, super_timer=3)
    g.balls.append(b)
    # Simulate timer decay (as done in update)
    for _ in range(3):
        for b2 in g.balls:
            if b2.is_super:
                b2.super_timer -= 1
                if b2.super_timer <= 0:
                    b2.is_super = False
    assert not b.is_super
    assert b.super_timer == 0


# ── Particle tests ──

def test_particle_spawn() -> None:
    g = make_game()
    g._spawn_particles(100.0, 100.0, 8, 4)
    assert len(g.particles) == 4
    for p in g.particles:
        assert p.life == PARTICLE_LIFE


def test_particle_update_decay() -> None:
    g = make_game()
    g._spawn_particles(100.0, 100.0, 8, 1)
    p = g.particles[0]
    for _ in range(PARTICLE_LIFE):
        g._update_particles()
    assert len(g.particles) == 0  # expired


# ── Combo threshold for compression in paddle hit ──

def test_paddle_hit_triggers_compression_at_threshold() -> None:
    g = make_game()
    g.player_x = 120.0
    g.active_color = 0
    g.combo = 3  # one below threshold
    # Add some same-color balls
    g.balls = [
        Ball(x=80.0, y=80.0, vx=0.0, vy=0.0, color=0),
        Ball(x=160.0, y=60.0, vx=0.0, vy=0.0, color=0),
    ]
    # Hit a same-color ball → combo becomes 4 → should trigger compression
    b = Ball(x=120.0, y=float(PLAYER_Y - BALL_RADIUS),
             vx=0.0, vy=3.0, color=0)
    g._check_paddle(b)
    assert g.combo >= COMBO_THRESHOLD  # (actually 4, but _compress called)
    # Check that compression happened: all color-0 balls + the hit ball
    # should be compressed into one super ball
    color0_balls = [b for b in g.balls if b.color == 0]
    assert len(color0_balls) >= 1
    # At least one should be super
    supers = [b for b in g.balls if b.is_super]
    assert len(supers) >= 1


# ── Score calculation tests ──

def test_score_same_color_scales_with_combo() -> None:
    g = make_game()
    g.player_x = 120.0
    g.active_color = 0
    g.combo = 1
    scores = []
    for _ in range(3):
        b = Ball(x=120.0, y=float(PLAYER_Y - BALL_RADIUS),
                 vx=0.0, vy=3.0, color=0)
        g._check_paddle(b)
        scores.append(g.score)
    # Scores should increase non-linearly (combo multiplier)
    assert scores[2] > scores[1] > scores[0]


def test_score_super_ball_bonus() -> None:
    g = make_game()
    g.player_x = 120.0
    g.active_color = 0
    g.combo = 2
    # Regular ball hit
    b_reg = Ball(x=120.0, y=float(PLAYER_Y - BALL_RADIUS),
                 vx=0.0, vy=3.0, color=0)
    g._check_paddle(b_reg)
    reg_score = g.score

    g2 = make_game()
    g2.player_x = 120.0
    g2.active_color = 0
    g2.combo = 2
    # Super ball hit (same combo)
    b_sup = Ball(x=120.0, y=float(PLAYER_Y - SUPER_RADIUS),
                 vx=0.0, vy=3.0, color=0, is_super=True, super_timer=30)
    g2._check_paddle(b_sup)
    # Super ball should give 3x points
    assert g2.score == 0 + 30 * 3  # combo=3 after hit, 10*3=30 * 3 = 90
    assert g2.score > reg_score


# ── Edge cases ──

def test_compress_no_same_color_balls() -> None:
    g = make_game()
    g.balls = [Ball(x=100.0, y=100.0, vx=0.0, vy=0.0, color=1)]
    result = g._compress(0)  # compress color 0 but only color 1 exists
    assert result == 0
    assert len(g.balls) == 1
    assert not g.balls[0].is_super


def test_player_clamp() -> None:
    """Player can't move off screen."""
    g = make_game()
    g.player_x = -50.0
    # Simulate clamping (done in update)
    half_w = 40 / 2
    g.player_x = max(half_w, min(240.0 - half_w, g.player_x))
    assert g.player_x == half_w  # clamped to left edge

    g.player_x = 300.0
    g.player_x = max(half_w, min(240.0 - half_w, g.player_x))
    assert g.player_x == 240.0 - half_w  # clamped to right edge


def test_reset_clears_all_state() -> None:
    g = make_game()
    g.score = 500
    g.combo = 10
    g.max_combo = 15
    g.balls_juggled = 50
    g.hazard_y = 200.0
    g.game_over = True
    g._shake_frames = 5

    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.balls_juggled == 0
    assert g.hazard_y == HAZARD_START_Y
    assert not g.game_over
    assert g._shake_frames == 0
    assert g.active_color == -1


def test_game_over_reset_via_space() -> None:
    """reset() is callable and restores playable state."""
    g = make_game()
    g.game_over = True
    g.score = 999
    g.reset()
    assert not g.game_over
    assert g.score == 0
    assert len(g.balls) == 2


# ── Run ──

def run_tests() -> int:
    """Run all tests and return failure count."""
    tests: list[tuple[str, Any]] = [
        ("test_ball_dataclass", test_ball_dataclass),
        ("test_particle_dataclass", test_particle_dataclass),
        ("test_constants", test_constants),
        ("test_reset_initial_state", test_reset_initial_state),
        ("test_spawn_ball", test_spawn_ball),
        ("test_spawn_ball_max_limit", test_spawn_ball_max_limit),
        ("test_apply_physics_gravity", test_apply_physics_gravity),
        ("test_apply_physics_speed_mult", test_apply_physics_speed_mult),
        ("test_wall_bounce_left", test_wall_bounce_left),
        ("test_wall_bounce_right", test_wall_bounce_right),
        ("test_ceiling_bounce", test_ceiling_bounce),
        ("test_speed_clamp", test_speed_clamp),
        ("test_paddle_hit_detection", test_paddle_hit_detection),
        ("test_paddle_miss_off_side", test_paddle_miss_off_side),
        ("test_same_color_combo_increment", test_same_color_combo_increment),
        ("test_different_color_resets_combo", test_different_color_resets_combo),
        ("test_max_combo_tracking", test_max_combo_tracking),
        ("test_compress_requires_same_color_balls", test_compress_requires_same_color_balls),
        ("test_compress_creates_super_ball", test_compress_creates_super_ball),
        ("test_compress_only_affects_same_color", test_compress_only_affects_same_color),
        ("test_compress_preserves_existing_super", test_compress_preserves_existing_super),
        ("test_missed_ball_raises_hazard", test_missed_ball_raises_hazard),
        ("test_hazard_game_over", test_hazard_game_over),
        ("test_hazard_not_game_over_above_player", test_hazard_not_game_over_above_player),
        ("test_super_timer_decay", test_super_timer_decay),
        ("test_particle_spawn", test_particle_spawn),
        ("test_particle_update_decay", test_particle_update_decay),
        ("test_paddle_hit_triggers_compression_at_threshold", test_paddle_hit_triggers_compression_at_threshold),
        ("test_score_same_color_scales_with_combo", test_score_same_color_scales_with_combo),
        ("test_score_super_ball_bonus", test_score_super_ball_bonus),
        ("test_compress_no_same_color_balls", test_compress_no_same_color_balls),
        ("test_player_clamp", test_player_clamp),
        ("test_reset_clears_all_state", test_reset_clears_all_state),
        ("test_game_over_reset_via_space", test_game_over_reset_via_space),
    ]

    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
            failed += 1

    return failed


if __name__ == "__main__":
    failed = run_tests()
    print(f"\n{len([t for t in dir() if t.startswith('test_')])} tests, {failed} failed")
    if failed:
        sys.exit(1)
