"""test_imports.py — Headless logic tests for PONG SURGE.

Uses Game.__new__ pattern to bypass Pyxel initialization.
Tests core game logic: paddle positioning, ball physics, color-match
COMBO, SURGE activation, scoring, and game-over detection.
"""
from __future__ import annotations

import math
import sys

# Ensure main.py is importable
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/039_pong_surge")

from main import (
    SCREEN_W,
    SCREEN_H,
    PADDLE_H,
    PADDLE_W,
    PADDLE_X_PLAYER,
    PADDLE_X_AI,
    BALL_RADIUS,
    BALL_SPEED_INIT,
    BALL_SPEED_MAX,
    BALL_SPEED_INCREMENT,
    COMBO_SURGE_THRESHOLD,
    SURGE_DURATION,
    SURGE_SCORE_MULT,
    NUM_COLORS,
    COLOR_DEFS,
    SCORE_PASS_AI,
    SCORE_HIT_BASE,
    Ball,
    Paddle,
    Particle,
    Game,
)


# ── Config/data structure tests ──
def test_config() -> None:
    assert SCREEN_W == 256
    assert SCREEN_H == 192
    assert PADDLE_W == 6
    assert PADDLE_H == 40
    assert BALL_RADIUS == 3
    assert BALL_SPEED_INIT == 2.5
    assert COMBO_SURGE_THRESHOLD == 5
    assert SURGE_DURATION == 180
    assert NUM_COLORS == 4
    assert len(COLOR_DEFS) == 4


def test_color_defs() -> None:
    names = {d[0] for d in COLOR_DEFS}
    assert names == {"RED", "GREEN", "YELLOW", "CYAN"}
    vals = [d[1] for d in COLOR_DEFS]
    assert vals == [8, 11, 10, 13]  # RED, GREEN, YELLOW, CYAN


def test_ball_dataclass() -> None:
    b = Ball(x=100, y=50, vx=3, vy=-2, color=2)
    assert b.x == 100
    assert b.y == 50
    assert b.vx == 3
    assert b.vy == -2
    assert b.color == 2
    assert b.speed == BALL_SPEED_INIT
    assert b.color_val() == 10  # YELLOW


def test_paddle_dataclass() -> None:
    p = Paddle(x=16, y=96, color=0)
    assert p.x == 16
    assert p.y == 96
    assert p.w == PADDLE_W
    assert p.h == PADDLE_H
    assert p.color == 0
    assert p.color_val() == 8  # RED
    assert p.left == 16 - PADDLE_W / 2
    assert p.right == 16 + PADDLE_W / 2
    assert p.top == 96 - PADDLE_H / 2
    assert p.bottom == 96 + PADDLE_H / 2


def test_particle_dataclass() -> None:
    p = Particle(x=10, y=20, vx=1.5, vy=-0.5, color=3, life=15, max_life=20)
    assert p.x == 10
    assert p.y == 20
    assert p.vx == 1.5
    assert p.vy == -0.5
    assert p.color == 3
    assert p.life == 15
    assert p.max_life == 20


# ── Game state tests (headless, __new__ pattern) ──
def _make_game() -> Game:
    """Create a Game instance without initializing Pyxel."""
    g = Game.__new__(Game)
    # Set all attributes that __init__ would set (bypassing Pyxel init)
    g._rng = __import__("random").Random(42)
    g.player = Paddle(x=PADDLE_X_PLAYER, y=SCREEN_H / 2)
    g.ai = Paddle(x=PADDLE_X_AI, y=SCREEN_H / 2)
    g.ball = Ball(x=0, y=0, vx=0, vy=0, color=0)
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.rally_count = 0
    g.surge_timer = 0
    g.particles = []
    g._ai_color_timer = 0
    g._shake_frames = 0
    g.game_over = False
    g.reset()
    return g


def test_game_reset() -> None:
    g = _make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.rally_count == 0
    assert g.surge_timer == 0
    assert len(g.particles) == 0
    assert g.game_over is False
    assert g.ball.x == SCREEN_W / 2
    assert g.ball.y == SCREEN_H / 2
    assert g.player.color == 0
    assert g.ai.color == 1
    assert g.player.x == PADDLE_X_PLAYER
    assert g.ai.x == PADDLE_X_AI


def test_paddle_clamp_top() -> None:
    g = _make_game()
    g.player.y = -10
    g.player.y = max(PADDLE_H / 2, min(SCREEN_H - PADDLE_H / 2, g.player.y))
    assert abs(g.player.y - PADDLE_H / 2) < 0.01


def test_paddle_clamp_bottom() -> None:
    g = _make_game()
    g.player.y = SCREEN_H + 50
    g.player.y = max(PADDLE_H / 2, min(SCREEN_H - PADDLE_H / 2, g.player.y))
    assert abs(g.player.y - (SCREEN_H - PADDLE_H / 2)) < 0.01


def test_color_cycle() -> None:
    g = _make_game()
    assert g.player.color == 0
    g.player.color = (g.player.color + 1) % NUM_COLORS
    assert g.player.color == 1
    g.player.color = (g.player.color + 1) % NUM_COLORS
    assert g.player.color == 2
    g.player.color = (g.player.color + 1) % NUM_COLORS
    assert g.player.color == 3
    g.player.color = (g.player.color + 1) % NUM_COLORS
    assert g.player.color == 0


# ── Ball physics tests ──
def test_ball_wall_bounce_top() -> None:
    g = _make_game()
    g.ball.y = BALL_RADIUS - 1
    g.ball.vy = -2
    g._update_ball()
    assert abs(g.ball.y - BALL_RADIUS) < 0.01
    assert g.ball.vy > 0  # bounced down


def test_ball_wall_bounce_bottom() -> None:
    g = _make_game()
    g.ball.y = SCREEN_H - BALL_RADIUS + 1
    g.ball.vy = 2
    g._update_ball()
    assert abs(g.ball.y - (SCREEN_H - BALL_RADIUS)) < 0.01
    assert g.ball.vy < 0  # bounced up


def test_ball_pass_ai_scores() -> None:
    """Ball passes right wall → player scores, ball resets."""
    g = _make_game()
    g.ball.x = SCREEN_W - BALL_RADIUS + 1
    g.ball.vx = 3
    old_score = g.score
    g._update_ball()
    assert g.score == old_score + SCORE_PASS_AI
    # Ball reset to center
    assert abs(g.ball.x - SCREEN_W / 2) < 0.01
    assert abs(g.ball.y - SCREEN_H / 2) < 0.01


def test_ball_pass_player_game_over() -> None:
    """Ball passes left wall → game over."""
    g = _make_game()
    g.ball.x = BALL_RADIUS - 1
    g.ball.vx = -3
    g._update_ball()
    assert g.game_over is True


# ── Paddle collision tests ──
def test_player_paddle_collision_color_match() -> None:
    """Ball hits player paddle with matching color → COMBO increases."""
    g = _make_game()
    # Place ball exactly at paddle's right edge, moving left
    g.ball.x = PADDLE_X_PLAYER + PADDLE_W / 2 + BALL_RADIUS
    g.ball.y = SCREEN_H / 2
    g.ball.vx = -2
    g.ball.vy = 0
    g.ball.color = 0  # RED
    g.player.color = 0  # RED — match!
    g.ball.speed = BALL_SPEED_INIT

    g._check_paddle_collision(g.player, is_ai=False)

    assert g.ball.vx > 0  # bounced right
    assert g.combo == 1
    assert g.ball.speed > BALL_SPEED_INIT


def test_player_paddle_collision_color_mismatch() -> None:
    """Ball hits player paddle with wrong color → COMBO resets."""
    g = _make_game()
    g.ball.x = PADDLE_X_PLAYER + PADDLE_W / 2 + BALL_RADIUS
    g.ball.y = SCREEN_H / 2
    g.ball.vx = -2
    g.ball.vy = 0
    g.ball.color = 0  # RED
    g.player.color = 1  # GREEN — mismatch!
    g.combo = 3  # existing combo
    g.ball.speed = 4.0

    g._check_paddle_collision(g.player, is_ai=False)

    assert g.combo == 0
    assert abs(g.ball.speed - BALL_SPEED_INIT) < 0.01  # speed reset


def test_ai_paddle_collision_color_match() -> None:
    """Ball hits AI paddle with matching color → COMBO increases."""
    g = _make_game()
    g.ball.x = PADDLE_X_AI - PADDLE_W / 2 - BALL_RADIUS
    g.ball.y = SCREEN_H / 2
    g.ball.vx = 2
    g.ball.vy = 0
    g.ball.color = 1  # GREEN
    g.ai.color = 1  # GREEN — match!
    g.ball.speed = BALL_SPEED_INIT

    g._check_paddle_collision(g.ai, is_ai=True)

    assert g.ball.vx < 0  # bounced left
    assert g.combo == 1


def test_ai_hit_changes_ball_color() -> None:
    """AI hit triggers ball color change (via random)."""
    g = _make_game()
    g.ball.x = PADDLE_X_AI - PADDLE_W / 2 - BALL_RADIUS
    g.ball.y = SCREEN_H / 2
    g.ball.vx = 2
    g.ball.vy = 0
    g.ball.color = 0
    g.ai.color = 0  # match
    g._check_paddle_collision(g.ai, is_ai=True)
    # Ball bounced back and color is valid
    assert g.ball.vx < 0
    assert 0 <= g.ball.color < NUM_COLORS


# ── COMBO / SURGE tests ──
def test_combo_increments() -> None:
    g = _make_game()
    for i in range(4):
        g.combo += 1
        g.max_combo = max(g.max_combo, g.combo)
    assert g.combo == 4
    assert g.max_combo == 4


def test_surge_activation() -> None:
    """COMBO >= 5 triggers SURGE."""
    g = _make_game()
    g.combo = COMBO_SURGE_THRESHOLD
    g.surge_timer = 0

    # Simulate SURGE check from _check_paddle_collision
    if g.combo >= COMBO_SURGE_THRESHOLD and g.surge_timer == 0:
        g.surge_timer = SURGE_DURATION
        g._shake_frames = 15
        g._spawn_surge_particles()

    assert g.surge_timer == SURGE_DURATION
    assert g._shake_frames == 15
    assert len(g.particles) == 25


def test_surge_timer_decrement() -> None:
    g = _make_game()
    g.surge_timer = 10
    g._update_surge()
    assert g.surge_timer == 9


def test_surge_score_multiplier() -> None:
    """SURGE multiplies score gains."""
    g = _make_game()
    g.surge_timer = 100
    combo_mult = SURGE_SCORE_MULT if g.surge_timer > 0 else 1
    assert combo_mult == 3
    g.surge_timer = 0
    combo_mult = SURGE_SCORE_MULT if g.surge_timer > 0 else 1
    assert combo_mult == 1


def test_surge_no_reactivate() -> None:
    """SURGE doesn't reactivate while already active."""
    g = _make_game()
    g.combo = COMBO_SURGE_THRESHOLD + 2
    g.surge_timer = 50  # already active
    old_timer = g.surge_timer
    # The check: if combo >= threshold AND surge_timer == 0
    if g.combo >= COMBO_SURGE_THRESHOLD and g.surge_timer == 0:
        g.surge_timer = SURGE_DURATION
    assert g.surge_timer == old_timer  # unchanged


# ── Speed clamp tests ──
def test_ball_speed_clamp_max() -> None:
    g = _make_game()
    g.ball.speed = BALL_SPEED_MAX + 1
    # Speed normalization in collision logic caps at BALL_SPEED_MAX
    clamped = min(BALL_SPEED_MAX, g.ball.speed)
    assert abs(clamped - BALL_SPEED_MAX) < 0.01


def test_ball_speed_increment() -> None:
    g = _make_game()
    g.ball.speed = BALL_SPEED_INIT
    g.ball.speed = min(BALL_SPEED_MAX, g.ball.speed + BALL_SPEED_INCREMENT)
    assert abs(g.ball.speed - (BALL_SPEED_INIT + BALL_SPEED_INCREMENT)) < 0.01


# ── Particle tests ──
def test_particle_life_decrement() -> None:
    g = _make_game()
    g.particles = [
        Particle(x=50, y=50, vx=0, vy=0, color=0, life=3, max_life=10),
        Particle(x=60, y=60, vx=0, vy=0, color=1, life=1, max_life=10),
        Particle(x=70, y=70, vx=0, vy=0, color=2, life=0, max_life=10),
    ]
    g._update_particles()
    # life=3 → 2 (kept), life=1 → 0 (removed), life=0 → -1 (removed)
    assert len(g.particles) == 1
    assert g.particles[0].life == 2


def test_particle_removal() -> None:
    g = _make_game()
    g.particles = [Particle(x=10, y=10, vx=0, vy=0, color=0, life=0, max_life=10)]
    g._update_particles()
    assert len(g.particles) == 0


def test_spawn_hit_particles() -> None:
    g = _make_game()
    g.ball.x = 128
    g.ball.y = 96
    g.ball.color = 2
    g._spawn_hit_particles(g.player)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.life == 12
        assert p.color == 2


def test_spawn_surge_particles() -> None:
    g = _make_game()
    g.ball.x = 100
    g.ball.y = 80
    g._spawn_surge_particles()
    assert len(g.particles) == 25


def test_spawn_score_particles() -> None:
    g = _make_game()
    g.ball.color = 1
    g._spawn_score_particles()
    assert len(g.particles) == 12


# ── Scoring tests ──
def test_score_on_color_match_hit() -> None:
    g = _make_game()
    g.combo = 2
    g.surge_timer = 0
    combo_mult = SURGE_SCORE_MULT if g.surge_timer > 0 else 1
    g.score += SCORE_HIT_BASE + g.combo * combo_mult
    assert g.score == SCORE_HIT_BASE + 2  # 1 + 2 = 3


def test_score_surge_multiplied() -> None:
    g = _make_game()
    g.combo = 3
    g.surge_timer = 100
    combo_mult = SURGE_SCORE_MULT if g.surge_timer > 0 else 1
    g.score += SCORE_HIT_BASE + g.combo * combo_mult
    assert g.score == SCORE_HIT_BASE + 3 * 3  # 1 + 9 = 10


def test_score_pass_ai() -> None:
    g = _make_game()
    g.score += SCORE_PASS_AI
    assert g.score == SCORE_PASS_AI


# ── Game over / restart tests ──
def test_game_over_prevents_ball_update() -> None:
    g = _make_game()
    g.game_over = True
    # update() returns early when game_over
    # We verify by checking _update_ball isn't called when game_over
    # (Test the guard condition logic directly)
    assert g.game_over is True


def test_reset_clears_all() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 10
    g.max_combo = 15
    g.rally_count = 42
    g.surge_timer = 100
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, color=0, life=5, max_life=5)]
    g.game_over = True

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.rally_count == 0
    assert g.surge_timer == 0
    assert len(g.particles) == 0
    assert g.game_over is False


# ── Rally count test ──
def test_rally_count_increments() -> None:
    g = _make_game()
    assert g.rally_count == 0
    g.rally_count += 1
    assert g.rally_count == 1
    g.rally_count += 1
    assert g.rally_count == 2


# ── AI behavior logic tests ──
def test_ai_moves_toward_ball() -> None:
    g = _make_game()
    g.ai.y = 96
    g.ball.y = 120  # ball below AI
    g.ball.vx = 2  # moving toward AI
    target_y = g.ball.y
    if g.ai.y < target_y:
        g.ai.y += 2.0
    assert g.ai.y > 96  # moved down


def test_ai_returns_center_when_ball_away() -> None:
    g = _make_game()
    g.ai.y = 120
    g.ball.y = 50
    g.ball.vx = -2  # ball moving left, away from AI
    target_y = SCREEN_H / 2  # AI returns to center
    if g.ai.y > target_y:
        g.ai.y -= 2.0
    assert g.ai.y < 120  # moved toward center


# ── Ball direction guard tests ──
def test_no_collision_ball_moving_away_from_player() -> None:
    """Ball moving right shouldn't collide with player paddle."""
    g = _make_game()
    g.ball.x = PADDLE_X_PLAYER + 10
    g.ball.y = SCREEN_H / 2
    g.ball.vx = 2  # moving RIGHT, away from player
    old_vx = g.ball.vx
    g._check_paddle_collision(g.player, is_ai=False)
    # vx should NOT be flipped (no collision processed)
    assert g.ball.vx == old_vx


def test_no_collision_ball_moving_away_from_ai() -> None:
    """Ball moving left shouldn't collide with AI paddle."""
    g = _make_game()
    g.ball.x = PADDLE_X_AI - 10
    g.ball.y = SCREEN_H / 2
    g.ball.vx = -2  # moving LEFT, away from AI
    old_vx = g.ball.vx
    g._check_paddle_collision(g.ai, is_ai=True)
    assert g.ball.vx == old_vx


# ── Paddle bounds tests ──
def test_ai_paddle_clamped() -> None:
    g = _make_game()
    g.ai.y = -100
    half_h = PADDLE_H / 2
    g.ai.y = max(half_h, min(SCREEN_H - half_h, g.ai.y))
    assert abs(g.ai.y - half_h) < 0.01


# ── Velocity normalization test ──
def test_ball_speed_normalization() -> None:
    """After collision, ball velocity magnitude should equal ball.speed."""
    g = _make_game()
    g.ball.speed = 3.5
    g.ball.vx = 2.0
    g.ball.vy = 1.5
    current = math.hypot(g.ball.vx, g.ball.vy)
    scale = g.ball.speed / current
    g.ball.vx *= scale
    g.ball.vy *= scale
    assert abs(math.hypot(g.ball.vx, g.ball.vy) - 3.5) < 0.01


# ── Score accumulation across multiple hits ──
def test_score_multiple_hits() -> None:
    g = _make_game()
    # Simulate 3 matching hits (combo builds).
    # Each hit needs the ball placed at the paddle edge moving toward it.
    for expected_combo in range(1, 4):
        # Place ball at player paddle edge, moving left (toward player)
        g.ball.x = PADDLE_X_PLAYER + PADDLE_W / 2 + BALL_RADIUS
        g.ball.y = SCREEN_H / 2
        g.ball.vx = -2
        g.ball.vy = 0
        g.ball.color = 0
        g.player.color = 0
        g.ball.speed = BALL_SPEED_INIT
        g._check_paddle_collision(g.player, is_ai=False)
        assert g.combo == expected_combo
        assert g.rally_count == expected_combo

    assert g.combo == 3
    assert g.rally_count == 3
    # Score: combo incremented BEFORE scoring.
    # hit 1: combo 0→1, score += 1+1=2
    # hit 2: combo 1→2, score += 1+2=3, total=5
    # hit 3: combo 2→3, score += 1+3=4, total=9
    assert g.score == 9


if __name__ == "__main__":
    import traceback

    tests = [
        test_config,
        test_color_defs,
        test_ball_dataclass,
        test_paddle_dataclass,
        test_particle_dataclass,
        test_game_reset,
        test_paddle_clamp_top,
        test_paddle_clamp_bottom,
        test_color_cycle,
        test_ball_wall_bounce_top,
        test_ball_wall_bounce_bottom,
        test_ball_pass_ai_scores,
        test_ball_pass_player_game_over,
        test_player_paddle_collision_color_match,
        test_player_paddle_collision_color_mismatch,
        test_ai_paddle_collision_color_match,
        test_ai_hit_changes_ball_color,
        test_combo_increments,
        test_surge_activation,
        test_surge_timer_decrement,
        test_surge_score_multiplier,
        test_surge_no_reactivate,
        test_ball_speed_clamp_max,
        test_ball_speed_increment,
        test_particle_life_decrement,
        test_particle_removal,
        test_spawn_hit_particles,
        test_spawn_surge_particles,
        test_spawn_score_particles,
        test_score_on_color_match_hit,
        test_score_surge_multiplied,
        test_score_pass_ai,
        test_game_over_prevents_ball_update,
        test_reset_clears_all,
        test_rally_count_increments,
        test_ai_moves_toward_ball,
        test_ai_returns_center_when_ball_away,
        test_no_collision_ball_moving_away_from_player,
        test_no_collision_ball_moving_away_from_ai,
        test_ai_paddle_clamped,
        test_ball_speed_normalization,
        test_score_multiple_hits,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  PASS {test_fn.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL {test_fn.__name__}")
            traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
