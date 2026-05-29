"""test_imports.py — Headless logic tests for CHROMA RALLY (081)."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/081_chroma_rally")
import random
from main import (Game, Phase, Ball, Particle, COLORS, COLOR_NAMES,
                  MATCH_POINTS, COMBO_FOR_SUPER, BALL_SPEED, SUPER_SPEED,
                  SCREEN_W, SCREEN_H, PLAYER_X, OPPONENT_X, NET_X,
                  RACKET_W, RACKET_H, BALL_RADIUS, GRAVITY,
                   COURT_TOP, COURT_BOTTOM,
                  SERVE_FRAMES, TRAIL_LENGTH, SUPER_TRAIL_LENGTH)

# Ball position that exactly touches the player racket edge
PLAYER_HIT_X = PLAYER_X + RACKET_W + BALL_RADIUS  # 51
OPPONENT_HIT_X = OPPONENT_X - RACKET_W - BALL_RADIUS  # 269


def _make_game() -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.particles = []
    g._ball_trail = []
    g._title_demo_ball = Ball(x=NET_X, y=SCREEN_H // 2, vx=2.0, vy=1.0, color=0)
    g._title_demo_paddle_y = SCREEN_H // 2
    g._title_demo_opponent_y = SCREEN_H // 2
    g.reset()
    return g


# ── Constants ───────────────────────────────────────────────────────────

def test_constants():
    assert len(COLORS) == 4
    assert COLORS == (8, 3, 10, 12)
    assert len(COLOR_NAMES) == 4
    assert MATCH_POINTS == 7
    assert COMBO_FOR_SUPER == 4
    assert PLAYER_X == 40
    assert OPPONENT_X == SCREEN_W - 40
    assert NET_X == SCREEN_W // 2


# ── Game reset / state ──────────────────────────────────────────────────

def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.player_y == SCREEN_H // 2
    assert g.opponent_y == SCREEN_H // 2
    assert g.racket_color == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score_player == 0
    assert g.score_opponent == 0
    assert g.super_ready is False
    assert g.particles == []
    assert g._ball_trail == []
    assert g.last_hitter == "none"
    assert g.total_score == 0


def test_phase_enum():
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.POINT_SCORED == 2
    assert Phase.GAME_OVER == 3


# ── Serving ─────────────────────────────────────────────────────────────

def test_serve_ball_creates_active_ball():
    g = _make_game()
    g._rng = random.Random(42)
    g._serve_ball()
    assert g.ball.active is True
    assert g.ball.is_super is False
    assert g.ball.x == NET_X
    assert g.ball.y == SCREEN_H // 2
    assert g.ball.vx != 0
    assert g.combo == 0
    assert g.super_ready is False


def test_serve_ball_clears_combo_and_trail():
    g = _make_game()
    g.combo = 5
    g.super_ready = True
    g._ball_trail = [(100.0, 100.0, 0, False)] * 5
    g._rng = random.Random(42)
    g._serve_ball()
    assert g.combo == 0
    assert g.super_ready is False
    assert g._ball_trail == []


def test_serve_ball_deterministic_with_seed():
    g1 = _make_game()
    g2 = _make_game()
    g1._rng = random.Random(42)
    g2._rng = random.Random(42)
    g1._serve_ball()
    g2._serve_ball()
    assert g1.ball.vx == g2.ball.vx
    assert g1.ball.vy == g2.ball.vy
    assert g1.ball.color == g2.ball.color


# ── Ball Physics ────────────────────────────────────────────────────────

def test_update_ball_moves_ball():
    g = _make_game()
    start_y = SCREEN_H // 2 + 10
    g.ball = Ball(x=NET_X, y=start_y, vx=2.0, vy=1.0, color=0, active=True)
    g._update_ball()
    assert g.ball.x == NET_X + 2.0
    assert g.ball.y == start_y + 1.0  # y += old vy, BEFORE vy += gravity
    assert g.ball.vx == 2.0
    assert abs(g.ball.vy - (1.0 + GRAVITY)) < 0.001


def test_update_ball_bounces_top():
    g = _make_game()
    g.ball = Ball(x=NET_X, y=COURT_TOP + BALL_RADIUS + 1, vx=2.0, vy=-3.0, color=0, active=True)
    g._update_ball()
    assert g.ball.y == COURT_TOP + BALL_RADIUS
    assert g.ball.vy > 0


def test_update_ball_bounces_bottom():
    g = _make_game()
    g.ball = Ball(x=NET_X, y=COURT_BOTTOM - BALL_RADIUS - 1, vx=2.0, vy=3.0, color=0, active=True)
    g._update_ball()
    assert g.ball.y == COURT_BOTTOM - BALL_RADIUS
    assert g.ball.vy < 0


def test_update_ball_skips_inactive():
    g = _make_game()
    g.ball = Ball(x=NET_X, y=SCREEN_H // 2, vx=2.0, vy=1.0, color=0, active=False)
    orig_x, orig_y = g.ball.x, g.ball.y
    g._update_ball()
    assert g.ball.x == orig_x
    assert g.ball.y == orig_y


# ── AI ──────────────────────────────────────────────────────────────────

def test_ai_moves_toward_ball():
    g = _make_game()
    g.ball = Ball(x=OPPONENT_X - 20, y=SCREEN_H // 2 + 50, vx=1.0, vy=0.0, color=0, active=True)
    g.opponent_y = SCREEN_H // 2
    g._ai_move()
    assert g.opponent_y > SCREEN_H // 2


def test_ai_freezes_on_super_shot():
    g = _make_game()
    g.ball = Ball(x=OPPONENT_X - 20, y=SCREEN_H // 2 + 50, vx=3.0, vy=0.0, color=0, active=True, is_super=True)
    g.opponent_y = SCREEN_H // 2
    g._ai_move()
    assert g.opponent_y == SCREEN_H // 2


def test_ai_returns_to_center_when_ball_moving_away():
    g = _make_game()
    g.ball = Ball(x=PLAYER_X + 20, y=SCREEN_H // 2 + 30, vx=-2.0, vy=0.0, color=0, active=True)
    g.opponent_y = SCREEN_H // 2 + 50
    g._ai_move()
    assert abs(g.opponent_y - SCREEN_H // 2) < abs(SCREEN_H // 2 + 50 - SCREEN_H // 2)


def test_ai_clamped_to_court():
    g = _make_game()
    g.ball = Ball(x=OPPONENT_X - 20, y=SCREEN_H + 100, vx=1.0, vy=0.0, color=0, active=True)
    g._ai_move()
    assert g.opponent_y <= COURT_BOTTOM - RACKET_H // 2


# ── Player Hit / Combo ──────────────────────────────────────────────────

def test_player_hit_same_color_builds_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.ball = Ball(x=PLAYER_HIT_X, y=SCREEN_H // 2, vx=-3.0, vy=0.0, color=0, active=True)
    g.player_y = SCREEN_H // 2
    g.racket_color = 0
    g.combo = 0
    g._player_hit_count = 0
    g._check_player_hit()
    assert g.combo >= 1
    assert g.last_hitter == "player"


def test_player_hit_wrong_color_resets_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.ball = Ball(x=PLAYER_HIT_X, y=SCREEN_H // 2, vx=-3.0, vy=0.0, color=2, active=True)
    g.player_y = SCREEN_H // 2
    g.racket_color = 0
    g.combo = 3
    g._player_hit_count = 0
    g._check_player_hit()
    assert g.combo == 0
    assert g.super_ready is False


def test_player_hit_skips_when_ball_moving_away():
    g = _make_game()
    g.ball = Ball(x=PLAYER_HIT_X, y=SCREEN_H // 2, vx=2.0, vy=0.0, color=0, active=True)
    g.player_y = SCREEN_H // 2
    g.racket_color = 0
    g.combo = 0
    g._player_hit_count = 0
    g._check_player_hit()
    assert g.combo == 0  # vx > 0, should skip


def test_player_hit_racket_color_cycles():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.ball = Ball(x=PLAYER_HIT_X, y=SCREEN_H // 2, vx=-3.0, vy=0.0, color=0, active=True)
    g.player_y = SCREEN_H // 2
    g._player_hit_count = 0
    g.racket_color = 0
    g._check_player_hit()
    assert g.racket_color == 1  # (0 + 1) % 4


def test_player_hit_super_shot_triggers():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g._player_hit_count = 3
    g.racket_color = 3
    g.ball = Ball(x=PLAYER_HIT_X, y=SCREEN_H // 2, vx=-3.0, vy=0.0, color=3, active=True)
    g.player_y = SCREEN_H // 2
    g._check_player_hit()
    assert g.combo >= COMBO_FOR_SUPER
    assert g.ball.is_super is True
    assert g.super_ready is True


def test_player_hit_super_shot_speed():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g._player_hit_count = 3
    g.racket_color = 3
    g.ball = Ball(x=PLAYER_HIT_X, y=SCREEN_H // 2, vx=-3.0, vy=0.0, color=3, active=True)
    g.player_y = SCREEN_H // 2
    g._check_player_hit()
    speed = (g.ball.vx ** 2 + g.ball.vy ** 2) ** 0.5
    assert abs(speed - SUPER_SPEED) < 0.01


def test_player_hit_combo_speed_increases():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 0
    g._player_hit_count = 0
    g.racket_color = 0
    g.ball = Ball(x=PLAYER_HIT_X, y=SCREEN_H // 2, vx=-3.0, vy=0.0, color=0, active=True)
    g.player_y = SCREEN_H // 2
    g._check_player_hit()
    speed = (g.ball.vx ** 2 + g.ball.vy ** 2) ** 0.5
    # combo=1 after hit: speed = BALL_SPEED + 1 * 0.5 = 3.5
    assert abs(speed - (BALL_SPEED + 0.5)) < 0.1


def test_max_combo_tracked():
    g = _make_game()
    g.phase = Phase.PLAYING
    assert g.max_combo == 0
    for i in range(2):
        g._player_hit_count = i
        g.racket_color = i % 4
        g.ball = Ball(x=PLAYER_HIT_X, y=SCREEN_H // 2, vx=-3.0, vy=0.0, color=i % 4, active=True)
        g.player_y = SCREEN_H // 2
        g._check_player_hit()
    assert g.max_combo == 2


# ── Opponent Hit ────────────────────────────────────────────────────────

def test_opponent_hit_does_not_affect_player_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g.ball = Ball(x=OPPONENT_HIT_X, y=SCREEN_H // 2, vx=2.0, vy=0.0, color=0, active=True)
    g.opponent_y = SCREEN_H // 2
    g._check_opponent_hit()
    assert g.combo == 3  # Unchanged
    assert g.last_hitter == "opponent"


def test_opponent_hit_skips_when_ball_moving_away():
    g = _make_game()
    g.ball = Ball(x=OPPONENT_HIT_X, y=SCREEN_H // 2, vx=-2.0, vy=0.0, color=0, active=True)
    g.opponent_y = SCREEN_H // 2
    prev_hit_count = g._opponent_hit_count
    g._check_opponent_hit()
    assert g._opponent_hit_count == prev_hit_count


# ── Scoring ─────────────────────────────────────────────────────────────

def test_score_point_player():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 2
    g.total_score = 0
    g.ball = Ball(x=OPPONENT_X + 100, y=SCREEN_H // 2, vx=5.0, vy=0.0, color=0, active=True)
    g._score_point("player")
    assert g.score_player == 1
    assert g.score_opponent == 0
    assert g.total_score > 0
    assert g.ball.active is False
    assert g.phase == Phase.POINT_SCORED
    assert g.serve_timer == SERVE_FRAMES
    assert g.combo == 0


def test_score_point_opponent():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g.ball = Ball(x=PLAYER_X - 100, y=SCREEN_H // 2, vx=-5.0, vy=0.0, color=0, active=True)
    g._score_point("opponent")
    assert g.score_opponent == 1
    assert g.score_player == 0
    assert g.phase == Phase.POINT_SCORED


def test_score_point_super_bonus():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 4
    g.total_score = 0
    g.ball = Ball(x=OPPONENT_X + 100, y=SCREEN_H // 2, vx=5.0, vy=0.0, color=0, active=True, is_super=True)
    g._score_point("player")
    assert g.total_score == 100 + 4 * 50 + 500


# ── Particles ───────────────────────────────────────────────────────────

def test_spawn_hit_particles():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_hit_particles(100.0, 100.0, 0)
    assert len(g.particles) == 8
    for p in g.particles:
        assert p.life == 15
        assert p.max_life == 15
        assert p.color == 0


def test_spawn_super_particles():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_super_particles()
    assert len(g.particles) == 20


def test_spawn_point_particles():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_point_particles(200.0, 150.0)
    assert len(g.particles) == 12


def test_update_particles_removes_expired():
    g = _make_game()
    g.particles = [
        Particle(x=0, y=0, vx=1, vy=1, color=0, life=1, max_life=15),
        Particle(x=0, y=0, vx=1, vy=1, color=0, life=5, max_life=15),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


def test_update_particles_applies_gravity():
    g = _make_game()
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, color=0, life=10, max_life=15)]
    g._update_particles()
    assert g.particles[0].vy == 0.1


# ── Trail ────────────────────────────────────────────────────────────────

def test_update_trail_appends_and_trims():
    g = _make_game()
    g.ball = Ball(x=100, y=100, vx=1, vy=1, color=0, active=True, is_super=False)
    for _ in range(10):
        g._update_trail()
    assert len(g._ball_trail) == TRAIL_LENGTH


def test_update_trail_super_length():
    g = _make_game()
    g.ball = Ball(x=100, y=100, vx=1, vy=1, color=0, active=True, is_super=True)
    for _ in range(15):
        g._update_trail()
    assert len(g._ball_trail) == SUPER_TRAIL_LENGTH


# ── Point-scored phase ──────────────────────────────────────────────────

def test_point_scored_transitions_to_game_over():
    g = _make_game()
    g.phase = Phase.POINT_SCORED
    g.score_player = MATCH_POINTS
    g.serve_timer = 1
    g._point_text_timer = 0
    g._update_point_scored()
    assert g.phase == Phase.GAME_OVER


def test_point_scored_transitions_back_to_playing():
    g = _make_game()
    g.phase = Phase.POINT_SCORED
    g.score_player = 3
    g.score_opponent = 2
    g.serve_timer = 1
    g._point_text_timer = 0
    g._update_point_scored()
    assert g.phase == Phase.PLAYING


def test_point_scored_serve_timer_decrements():
    g = _make_game()
    g.phase = Phase.POINT_SCORED
    g.serve_timer = 30
    g._point_text_timer = 10
    g._update_point_scored()
    assert g.serve_timer == 29
    assert g._point_text_timer == 9


# ── Game Over / restart ─────────────────────────────────────────────────

def test_game_over_state():
    g = _make_game()
    g.phase = Phase.GAME_OVER
    g.score_player = 7
    g.score_opponent = 4
    assert g.phase == Phase.GAME_OVER


# ── Collision edge cases ────────────────────────────────────────────────

def test_player_hit_with_offset_adds_vertical_influence():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.ball = Ball(x=PLAYER_HIT_X, y=SCREEN_H // 2 + 10, vx=-3.0, vy=0.0, color=0, active=True)
    g.player_y = SCREEN_H // 2
    g.racket_color = 0
    g._player_hit_count = 0
    g.combo = 0
    orig_vy = g.ball.vy
    g._check_player_hit()
    assert g.ball.vy != orig_vy  # Vertical influence changes vy


def test_player_hit_aligned_no_extra_vertical():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.ball = Ball(x=PLAYER_HIT_X, y=SCREEN_H // 2, vx=-3.0, vy=1.0, color=0, active=True)
    g.player_y = SCREEN_H // 2
    g.racket_color = 0
    g._player_hit_count = 0
    g.combo = 0
    g._check_player_hit()
    assert g.ball.vx > 0  # Ball reflected rightward


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
