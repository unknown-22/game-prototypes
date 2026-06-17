"""test_imports.py — Headless logic tests for DODGE CHAIN.

Uses Game.__new__(Game) to bypass __init__ (avoids pyxel.init/run).
Tests core logic methods directly — never calls pyxel input functions.
"""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/134_dodge_chain")

# Import all game classes and constants
from main import (  # noqa: E402
    ARENA_BOTTOM,
    ARENA_LEFT,
    ARENA_RIGHT,
    ARENA_TOP,
    BALL_COLORS,
    BALL_LIFE,
    BALL_RADIUS,
    BALL_SPEED,
    COMBO_THRESHOLD,
    ECHO_DAMAGE_MULTIPLIER,
    ECHO_DURATION,
    ECHO_STAMINA_BONUS,
    GAME_TIME,
    INITIAL_OPPONENTS,
    MAX_HEAT,
    MAX_OPPONENTS,
    MAX_STAMINA,
    NEAR_MISS_RADIUS,
    NUM_COLORS,
    OPPONENT_BALL_SPEED,
    OPPONENT_RADIUS,
    PLAYER_RADIUS,
    PLAYER_SPEED,
    SCREEN_H,
    SCREEN_W,
    SUPER_DURATION,
    THROW_STAMINA_COST,
    Ball,
    EchoTrail,
    FloatingText,
    Game,
    Opponent,
    Particle,
    Phase,
    Player,
)


def _make_game() -> Game:
    """Create a headless Game instance ready for testing."""
    g: Game = Game.__new__(Game)
    # Pre-init ALL instance attributes that reset() touches
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.stamina = float(MAX_STAMINA)
    g.game_timer = GAME_TIME
    g.super_timer = 0
    g.super_active = False
    g.player = Player(x=160.0, y=140.0)
    g.opponents = []
    g.balls = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.next_opponent_spawn = 0
    g.shake_frames = 0
    g.echo_bonus = False
    g.reset()
    return g


# ═══════════════════════════════════════════════════════════════════
# Constant verification
# ═══════════════════════════════════════════════════════════════════


def test_constants() -> None:
    """Verify all game constants are properly defined."""
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert ARENA_LEFT == 16
    assert ARENA_TOP == 40
    assert ARENA_RIGHT == 304
    assert ARENA_BOTTOM == 224
    assert NUM_COLORS == 4
    assert SUPER_DURATION == 5 * 60
    assert MAX_HEAT == 100
    assert MAX_STAMINA == 100
    assert THROW_STAMINA_COST == 15
    assert COMBO_THRESHOLD == 5
    assert INITIAL_OPPONENTS == 3
    assert MAX_OPPONENTS == 8
    assert BALL_SPEED > 0
    assert OPPONENT_BALL_SPEED > 0
    assert PLAYER_RADIUS > 0
    assert OPPONENT_RADIUS > 0
    assert len(BALL_COLORS) == 4


# ═══════════════════════════════════════════════════════════════════
# Phase enum
# ═══════════════════════════════════════════════════════════════════


def test_phase_enum() -> None:
    """Phase enum has all three phases."""
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ═══════════════════════════════════════════════════════════════════
# Data class creation
# ═══════════════════════════════════════════════════════════════════


def test_player_creation() -> None:
    p = Player(x=100.0, y=200.0)
    assert p.x == 100.0
    assert p.y == 200.0
    assert p.radius == PLAYER_RADIUS
    assert p.color == 0
    assert p.color_timer == 120


def test_opponent_creation() -> None:
    o = Opponent(x=50.0, y=60.0, color=2)
    assert o.x == 50.0
    assert o.y == 60.0
    assert o.color == 2
    assert o.alive is True
    assert o.hp == 1


def test_ball_creation() -> None:
    b = Ball(x=10.0, y=20.0, vx=1.5, vy=-0.5, color=0)
    assert b.x == 10.0
    assert b.vx == 1.5
    assert b.owner_is_player is True
    assert b.life == BALL_LIFE


def test_echo_trail_creation() -> None:
    e = EchoTrail(x=30.0, y=40.0, life=ECHO_DURATION, color=1)
    assert e.life == ECHO_DURATION
    assert e.color == 1


def test_particle_creation() -> None:
    p = Particle(x=0.0, y=0.0, vx=1.0, vy=2.0, life=20, color=8)
    assert p.life == 20
    assert p.color == 8


def test_floating_text_creation() -> None:
    ft = FloatingText(x=0.0, y=0.0, text="TEST", life=30, color=7)
    assert ft.text == "TEST"
    assert ft.life == 30
    assert ft.vy == -1.0


# ═══════════════════════════════════════════════════════════════════
# Game._make_game factory
# ═══════════════════════════════════════════════════════════════════


def test_make_game_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.stamina == float(MAX_STAMINA)
    assert g.game_timer == GAME_TIME
    assert g.super_active is False
    assert g.super_timer == 0
    assert len(g.opponents) == 0
    assert len(g.balls) == 0
    assert len(g.echoes) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


# ═══════════════════════════════════════════════════════════════════
# _spawn_opponent
# ═══════════════════════════════════════════════════════════════════


def test_spawn_opponent_in_arena() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    opp = g._spawn_opponent()
    assert opp.alive is True
    assert ARENA_LEFT <= opp.x <= ARENA_RIGHT
    assert ARENA_TOP <= opp.y <= ARENA_BOTTOM
    assert 0 <= opp.color < NUM_COLORS
    assert opp.throw_cooldown > 0


def test_spawn_opponent_away_from_player() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    opp = g._spawn_opponent()
    dist = math.hypot(opp.x - g.player.x, opp.y - g.player.y)
    assert dist > 60


# ═══════════════════════════════════════════════════════════════════
# _throw_ball
# ═══════════════════════════════════════════════════════════════════


def test_throw_ball_normal() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.stamina = float(MAX_STAMINA)
    g.player.color = 2
    ball = g._throw_ball(200.0, 140.0)
    assert ball is not None
    assert ball.owner_is_player is True
    assert ball.color == 2  # player color
    assert ball.damage == 1
    assert g.stamina == float(MAX_STAMINA) - THROW_STAMINA_COST


def test_throw_ball_no_stamina() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.stamina = 5.0  # less than cost
    ball = g._throw_ball(200.0, 140.0)
    assert ball is None
    assert g.stamina == 5.0  # unchanged


def test_throw_ball_super_mode_no_stamina_cost() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_active = True
    g.stamina = float(MAX_STAMINA)
    ball = g._throw_ball(200.0, 140.0)
    assert ball is not None
    assert ball.color == -1  # super ball
    assert g.stamina == float(MAX_STAMINA)  # no cost


def test_throw_ball_echo_bonus_damage() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.stamina = float(MAX_STAMINA)
    g.echo_bonus = True
    ball = g._throw_ball(200.0, 140.0)
    assert ball is not None
    assert ball.damage == ECHO_DAMAGE_MULTIPLIER
    assert g.echo_bonus is False  # consumed


def test_throw_ball_velocity_direction() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.stamina = float(MAX_STAMINA)
    g.player.x = 100.0
    g.player.y = 100.0
    ball = g._throw_ball(200.0, 100.0)  # aim right
    assert ball is not None
    assert ball.vx > 0  # moving right
    assert abs(ball.vy) < 0.01  # nearly horizontal


# ═══════════════════════════════════════════════════════════════════
# _opponent_throw
# ═══════════════════════════════════════════════════════════════════


def test_opponent_throw() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 200.0
    g.player.y = 140.0
    opp = Opponent(x=100.0, y=140.0, color=3)
    ball = g._opponent_throw(opp)
    assert ball.owner_is_player is False
    assert ball.color == opp.color
    assert ball.damage == 1
    # Ball should move toward player (right)
    assert ball.vx > 0


# ═══════════════════════════════════════════════════════════════════
# _move_player
# ═══════════════════════════════════════════════════════════════════


def test_move_player_basic() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 160.0
    g.player.y = 140.0
    g._move_player(1.0, 0.0)
    assert g.player.x == 160.0 + PLAYER_SPEED
    assert g.player.y == 140.0


def test_move_player_diagonal_normalized() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 160.0
    g.player.y = 140.0
    g._move_player(1.0, 1.0)
    # Diagonal should be normalized: speed / sqrt(2)
    expected_step = PLAYER_SPEED / math.sqrt(2)
    assert abs(g.player.x - 160.0 - expected_step) < 0.001
    assert abs(g.player.y - 140.0 - expected_step) < 0.001


def test_move_player_bounds_left() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = float(ARENA_LEFT)
    g.player.y = 140.0
    g._move_player(-1.0, 0.0)
    assert g.player.x == ARENA_LEFT + PLAYER_RADIUS


def test_move_player_bounds_right() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = float(ARENA_RIGHT)
    g.player.y = 140.0
    g._move_player(1.0, 0.0)
    assert g.player.x == ARENA_RIGHT - PLAYER_RADIUS


def test_move_player_bounds_top() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 160.0
    g.player.y = float(ARENA_TOP)
    g._move_player(0.0, -1.0)
    assert g.player.y == ARENA_TOP + PLAYER_RADIUS


def test_move_player_bounds_bottom() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 160.0
    g.player.y = float(ARENA_BOTTOM)
    g._move_player(0.0, 1.0)
    assert g.player.y == ARENA_BOTTOM - PLAYER_RADIUS


# ═══════════════════════════════════════════════════════════════════
# _update_balls
# ═══════════════════════════════════════════════════════════════════


def test_update_balls_movement() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    ball = Ball(x=100.0, y=100.0, vx=3.0, vy=0.0, color=0)
    g.balls = [ball]
    g._update_balls()
    assert len(g.balls) == 1
    assert g.balls[0].x == 103.0
    assert g.balls[0].life == BALL_LIFE - 1


def test_update_balls_wall_bounce_left() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    ball = Ball(x=float(ARENA_LEFT + 2), y=100.0, vx=-5.0, vy=0.0, color=0)
    g.balls = [ball]
    g._update_balls()
    assert len(g.balls) == 1
    assert g.balls[0].vx > 0  # bounced right


def test_update_balls_wall_bounce_right() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    ball = Ball(x=float(ARENA_RIGHT - 2), y=100.0, vx=5.0, vy=0.0, color=0)
    g.balls = [ball]
    g._update_balls()
    assert len(g.balls) == 1
    assert g.balls[0].vx < 0  # bounced left


def test_update_balls_wall_bounce_top() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    ball = Ball(x=160.0, y=float(ARENA_TOP + 2), vx=0.0, vy=-5.0, color=0)
    g.balls = [ball]
    g._update_balls()
    assert len(g.balls) == 1
    assert g.balls[0].vy > 0  # bounced down


def test_update_balls_wall_bounce_bottom() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    ball = Ball(x=160.0, y=float(ARENA_BOTTOM - 2), vx=0.0, vy=5.0, color=0)
    g.balls = [ball]
    g._update_balls()
    assert len(g.balls) == 1
    assert g.balls[0].vy < 0  # bounced up


def test_update_balls_expired_removed() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    ball = Ball(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0, life=0)
    g.balls = [ball]
    g._update_balls()
    assert len(g.balls) == 0


def test_update_balls_missed_player_ball_resets_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 4
    ball = Ball(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0, owner_is_player=True, life=0)
    g.balls = [ball]
    g._update_balls()
    assert len(g.balls) == 0
    assert g.combo == 0  # combo reset on miss


def test_update_balls_super_ball_no_combo_reset() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    ball = Ball(x=100.0, y=100.0, vx=0.0, vy=0.0, color=-1, owner_is_player=True, life=0)
    g.balls = [ball]
    g._update_balls()
    assert len(g.balls) == 0
    assert g.combo == 3  # super ball miss doesn't reset combo


# ═══════════════════════════════════════════════════════════════════
# _check_player_hit
# ═══════════════════════════════════════════════════════════════════


def test_check_player_hit_no_hit() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 160.0
    g.player.y = 140.0
    far_ball = Ball(x=300.0, y=200.0, vx=0.0, vy=0.0, color=0, owner_is_player=False)
    g.balls = [far_ball]
    damage = g._check_player_hit()
    assert damage == 0
    assert len(g.balls) == 1  # ball survives


def test_check_player_hit_direct_hit() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 160.0
    g.player.y = 140.0
    # Ball exactly on player
    hit_ball = Ball(x=160.0, y=140.0, vx=0.0, vy=0.0, color=0, owner_is_player=False, damage=1)
    g.balls = [hit_ball]
    damage = g._check_player_hit()
    assert damage == 1
    assert len(g.balls) == 0  # ball removed


def test_check_player_hit_near_miss() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 160.0
    g.player.y = 140.0
    # Ball at edge of hit radius
    near_ball = Ball(
        x=160.0 + PLAYER_RADIUS + BALL_RADIUS - 0.5,
        y=140.0,
        vx=0.0, vy=0.0, color=0, owner_is_player=False,
    )
    g.balls = [near_ball]
    damage = g._check_player_hit()
    assert damage == 1  # hit


def test_check_player_hit_dodge() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 160.0
    g.player.y = 140.0
    # Ball just outside hit radius
    dodge_ball = Ball(
        x=160.0 + PLAYER_RADIUS + BALL_RADIUS + 0.5,
        y=140.0,
        vx=0.0, vy=0.0, color=0, owner_is_player=False,
    )
    g.balls = [dodge_ball]
    damage = g._check_player_hit()
    assert damage == 0  # dodged


def test_check_player_hit_ignores_player_balls() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 160.0
    g.player.y = 140.0
    # Player ball at same position doesn't count
    own_ball = Ball(x=160.0, y=140.0, vx=0.0, vy=0.0, color=0, owner_is_player=True)
    g.balls = [own_ball]
    damage = g._check_player_hit()
    assert damage == 0
    assert len(g.balls) == 1  # player ball survives


# ═══════════════════════════════════════════════════════════════════
# _check_opponent_hits
# ═══════════════════════════════════════════════════════════════════


def test_check_opponent_hits_no_hit() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.opponents = [Opponent(x=300.0, y=200.0, color=0)]
    ball = Ball(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0, owner_is_player=True)
    g.balls = [ball]
    hits = g._check_opponent_hits()
    assert len(hits) == 0
    assert len(g.balls) == 1  # ball survives


def test_check_opponent_hits_direct_hit() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    opp = Opponent(x=200.0, y=150.0, color=1)
    g.opponents = [opp]
    ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=0, owner_is_player=True)
    g.balls = [ball]
    hits = g._check_opponent_hits()
    assert len(hits) == 1
    assert hits[0][0] is opp
    assert hits[0][1] is ball
    assert len(g.balls) == 0  # ball consumed


def test_check_opponent_hits_dead_opponent_ignored() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    dead_opp = Opponent(x=200.0, y=150.0, color=1, alive=False)
    g.opponents = [dead_opp]
    ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=0, owner_is_player=True)
    g.balls = [ball]
    hits = g._check_opponent_hits()
    assert len(hits) == 0


def test_check_opponent_hits_ignores_opponent_balls() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    opp = Opponent(x=200.0, y=150.0, color=1)
    g.opponents = [opp]
    opp_ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=0, owner_is_player=False)
    g.balls = [opp_ball]
    hits = g._check_opponent_hits()
    assert len(hits) == 0
    assert len(g.balls) == 1  # opponent ball passes through


def test_check_opponent_hits_one_per_ball_frame() -> None:
    """Each ball hits only one opponent per frame."""
    g = _make_game()
    g.phase = Phase.PLAYING
    opp1 = Opponent(x=200.0, y=150.0, color=1)
    opp2 = Opponent(x=200.0, y=150.0, color=2)  # same position
    g.opponents = [opp1, opp2]
    ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=0, owner_is_player=True)
    g.balls = [ball]
    hits = g._check_opponent_hits()
    assert len(hits) == 1  # hits first opponent only


# ═══════════════════════════════════════════════════════════════════
# _resolve_hit
# ═══════════════════════════════════════════════════════════════════


def test_resolve_hit_match_combo_up() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 0
    g.score = 0
    opp = Opponent(x=200.0, y=150.0, color=0)
    ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=0, owner_is_player=True)
    g._resolve_hit(opp, ball)
    assert g.combo == 1
    assert g.score > 0
    assert g.max_combo == 1


def test_resolve_hit_match_max_combo_tracks() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g.max_combo = 3
    g.score = 0
    opp = Opponent(x=200.0, y=150.0, color=0)
    ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=0, owner_is_player=True)
    g._resolve_hit(opp, ball)
    assert g.combo == 4
    assert g.max_combo == 4


def test_resolve_hit_match_super_active_3x_score() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 0
    g.score = 0
    g.super_active = True
    opp = Opponent(x=200.0, y=150.0, color=0)
    ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=-1, owner_is_player=True)
    g._resolve_hit(opp, ball)
    # super: score_mult = 3, combo=1
    expected_score = opp.score_value * 3 * 1
    assert g.score == expected_score


def test_resolve_hit_match_super_always_matches() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 0
    g.super_active = True
    opp = Opponent(x=200.0, y=150.0, color=3)  # different from ball color=0
    ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=0, owner_is_player=True)
    g._resolve_hit(opp, ball)
    assert g.combo == 1  # still match because super_active


def test_resolve_hit_mismatch_resets_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g.max_combo = 3
    opp = Opponent(x=200.0, y=150.0, color=3)
    ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=0, owner_is_player=True)
    g._resolve_hit(opp, ball)
    assert g.combo == 0


def test_resolve_hit_kills_opponent() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    opp = Opponent(x=200.0, y=150.0, color=0, hp=1)
    ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=0, damage=2)
    g._resolve_hit(opp, ball)
    assert opp.alive is False


def test_resolve_hit_activates_super_at_threshold() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = COMBO_THRESHOLD - 1  # at 4, next hit = 5
    opp = Opponent(x=200.0, y=150.0, color=0)
    ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=0, owner_is_player=True)
    g._resolve_hit(opp, ball)
    assert g.combo == COMBO_THRESHOLD
    assert g.super_active is True
    assert g.super_timer == SUPER_DURATION


def test_resolve_hit_no_double_super() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_active = True
    g.super_timer = 100
    g.combo = 6
    opp = Opponent(x=200.0, y=150.0, color=0)
    ball = Ball(x=200.0, y=150.0, vx=0.0, vy=0.0, color=-1, owner_is_player=True)
    g._resolve_hit(opp, ball)
    assert g.combo == 7
    # super timer unchanged (already active)
    assert g.super_timer == 100


# ═══════════════════════════════════════════════════════════════════
# _activate_super
# ═══════════════════════════════════════════════════════════════════


def test_activate_super() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_active = False
    g.super_timer = 0
    g._activate_super()
    assert g.super_active is True
    assert g.super_timer == SUPER_DURATION


# ═══════════════════════════════════════════════════════════════════
# Echo trail system
# ═══════════════════════════════════════════════════════════════════


def test_spawn_echo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._spawn_echo(100.0, 120.0, 2)
    assert len(g.echoes) == 1
    assert g.echoes[0].x == 100.0
    assert g.echoes[0].y == 120.0
    assert g.echoes[0].color == 2
    assert g.echoes[0].life == ECHO_DURATION


def test_update_echoes_life_decrement() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    echo = EchoTrail(x=100.0, y=120.0, life=10, color=2)
    g.echoes = [echo]
    g._update_echoes()
    assert len(g.echoes) == 1
    assert g.echoes[0].life == 9


def test_update_echoes_expired_removed() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    echo = EchoTrail(x=100.0, y=120.0, life=1, color=0)
    g.echoes = [echo]
    g._update_echoes()
    assert len(g.echoes) == 0  # life decremented to 0, removed


def test_check_echo_collect_touching() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 100.0
    g.player.y = 120.0
    g.stamina = 30.0
    g.echo_bonus = False
    echo = EchoTrail(x=100.0, y=120.0, life=100, color=2)
    g.echoes = [echo]
    g._check_echo_collect()
    assert len(g.echoes) == 0  # collected
    assert g.echo_bonus is True
    assert g.stamina == 30.0 + ECHO_STAMINA_BONUS


def test_check_echo_collect_not_touching() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 100.0
    g.player.y = 120.0
    echo = EchoTrail(x=200.0, y=200.0, life=100, color=2)
    g.echoes = [echo]
    g._check_echo_collect()
    assert len(g.echoes) == 1  # not collected
    assert g.echo_bonus is False


def test_check_echo_collect_stamina_capped() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 100.0
    g.player.y = 120.0
    g.stamina = float(MAX_STAMINA)
    echo = EchoTrail(x=100.0, y=120.0, life=100, color=2)
    g.echoes = [echo]
    g._check_echo_collect()
    assert g.stamina == float(MAX_STAMINA)  # capped


# ═══════════════════════════════════════════════════════════════════
# _update_opponents
# ═══════════════════════════════════════════════════════════════════


def test_update_opponents_move_toward_player() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 200.0
    g.player.y = 140.0
    opp = Opponent(x=100.0, y=140.0, color=0, throw_cooldown=999)
    g.opponents = [opp]
    g._update_opponents()
    assert opp.x > 100.0  # moved right toward player


def test_update_opponents_throw_on_cooldown() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 200.0
    g.player.y = 140.0
    opp = Opponent(x=100.0, y=140.0, color=0, throw_cooldown=0)
    g.opponents = [opp]
    g._update_opponents()
    assert len(g.balls) >= 1  # opponent threw
    assert g.balls[0].owner_is_player is False


def test_update_opponents_remove_dead() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    dead_opp = Opponent(x=100.0, y=100.0, color=0, alive=False)
    g.opponents = [dead_opp]
    g._update_opponents()
    assert len(g.opponents) == 0


# ═══════════════════════════════════════════════════════════════════
# _update_timers
# ═══════════════════════════════════════════════════════════════════


def test_update_timers_game_timer_decrements() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 100
    g._update_timers()
    assert g.game_timer == 99


def test_update_timers_super_deactivates() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_active = True
    g.super_timer = 1
    g.combo = 5
    g._update_timers()
    assert g.super_active is False
    assert g.combo == 0  # combo reset on super end


def test_update_timers_color_cycles() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.color = 0
    g.player.color_timer = 1
    g._update_timers()
    # timer hit 0, reset to 120, color cycles
    assert g.player.color_timer == 120
    assert g.player.color == 1


# ═══════════════════════════════════════════════════════════════════
# _cycle_player_color
# ═══════════════════════════════════════════════════════════════════


def test_cycle_player_color_forward() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.color = 0
    g._cycle_player_color(True)
    assert g.player.color == 1
    g._cycle_player_color(True)
    assert g.player.color == 2
    g._cycle_player_color(True)
    assert g.player.color == 3
    g._cycle_player_color(True)
    assert g.player.color == 0  # wrap around


def test_cycle_player_color_backward() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.color = 0
    g._cycle_player_color(False)
    assert g.player.color == 3  # wrap around


# ═══════════════════════════════════════════════════════════════════
# _check_game_over
# ═══════════════════════════════════════════════════════════════════


def test_check_game_over_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = float(MAX_HEAT)
    g.game_timer = 100
    assert g._check_game_over() is True


def test_check_game_over_timer() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g.game_timer = 0
    assert g._check_game_over() is True


def test_check_game_over_not_yet() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g.game_timer = 100
    assert g._check_game_over() is False


# ═══════════════════════════════════════════════════════════════════
# _difficulty_bonus / _difficulty_speed_bonus
# ═══════════════════════════════════════════════════════════════════


def test_difficulty_bonus_early() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = GAME_TIME  # full time, ~90s remaining
    assert g._difficulty_bonus() == 0


def test_difficulty_bonus_mid() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 45 * 60  # 45s remaining
    assert g._difficulty_bonus() == 20


def test_difficulty_bonus_late() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 15 * 60  # 15s remaining
    assert g._difficulty_bonus() == 50


def test_difficulty_speed_bonus_early() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = GAME_TIME
    assert g._difficulty_speed_bonus() == 0.0


def test_difficulty_speed_bonus_mid() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 45 * 60
    assert g._difficulty_speed_bonus() == 0.3


def test_difficulty_speed_bonus_late() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 15 * 60
    assert g._difficulty_speed_bonus() == 0.6


# ═══════════════════════════════════════════════════════════════════
# _nearest_opponent
# ═══════════════════════════════════════════════════════════════════


def test_nearest_opponent_returns_closest() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 100.0
    g.player.y = 100.0
    near = Opponent(x=110.0, y=100.0, color=0)
    far = Opponent(x=200.0, y=200.0, color=1)
    g.opponents = [far, near]
    result = g._nearest_opponent()
    assert result is near


def test_nearest_opponent_ignores_dead() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 100.0
    g.player.y = 100.0
    dead_near = Opponent(x=101.0, y=100.0, color=0, alive=False)
    far = Opponent(x=200.0, y=200.0, color=1)
    g.opponents = [dead_near, far]
    result = g._nearest_opponent()
    assert result is far


def test_nearest_opponent_no_opponents() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.opponents = []
    result = g._nearest_opponent()
    assert result is None


# ═══════════════════════════════════════════════════════════════════
# Particle and floating text
# ═══════════════════════════════════════════════════════════════════


def test_spawn_particles() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._spawn_particles(100.0, 120.0, 8, 5)
    assert len(g.particles) == 5


def test_update_particles() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    p = Particle(x=0.0, y=0.0, vx=1.0, vy=0.0, life=5, color=8)
    g.particles = [p]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].x == 1.0
    assert g.particles[0].life == 4


def test_update_particles_expired_removed() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=8)
    g.particles = [p]
    g._update_particles()
    assert len(g.particles) == 0  # life decremented to 0


def test_spawn_floating_text() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._spawn_floating_text(100.0, 120.0, "TEST", 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"


def test_update_floating_texts() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    ft = FloatingText(x=0.0, y=100.0, text="UP", life=10, color=7)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].y == 99.0  # vy=-1.0
    assert g.floating_texts[0].life == 9


# ═══════════════════════════════════════════════════════════════════
# reset() re-initialization
# ═══════════════════════════════════════════════════════════════════


def test_reset_clears_state() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 500
    g.combo = 3
    g.heat = 80.0
    g.opponents = [Opponent(x=100.0, y=100.0, color=0)]
    g.balls = [Ball(x=0.0, y=0.0, vx=0.0, vy=0.0, color=0)]
    g.echoes = [EchoTrail(x=0.0, y=0.0, life=100, color=0)]
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=0)]
    g.floating_texts = [FloatingText(x=0.0, y=0.0, text="X", life=1, color=0)]
    g.super_active = True
    g.echo_bonus = True
    g.shake_frames = 5
    g.next_opponent_spawn = 100
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert len(g.opponents) == 0
    assert len(g.balls) == 0
    assert len(g.echoes) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.super_active is False
    assert g.echo_bonus is False


# ═══════════════════════════════════════════════════════════════════
# Near-miss echo spawning (via ball proximity check in update)
# ═══════════════════════════════════════════════════════════════════


def test_near_miss_triggers_echo() -> None:
    """Verify that a passing opponent ball within NEAR_MISS_RADIUS spawns echo.
    This tests the logic loop in _update_playing without calling it directly."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 160.0
    g.player.y = 140.0
    # Place an opponent ball just past the player (within near miss radius)
    near_ball = Ball(
        x=160.0 + NEAR_MISS_RADIUS - 1.0,
        y=140.0,
        vx=0.0, vy=0.0, color=1, owner_is_player=False,
    )
    g.balls = [near_ball]
    # Simulate the echo spawning loop from _update_playing
    for ball in g.balls:
        if not ball.owner_is_player and not ball.echo_spawned:
            dist = math.hypot(ball.x - g.player.x, ball.y - g.player.y)
            if dist < NEAR_MISS_RADIUS:
                g._spawn_echo(g.player.x, g.player.y, ball.color)
                ball.echo_spawned = True
    assert len(g.echoes) == 1
    assert g.echoes[0].color == 1


def test_near_miss_far_ball_no_echo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = 160.0
    g.player.y = 140.0
    far_ball = Ball(
        x=160.0 + NEAR_MISS_RADIUS + 1.0,
        y=140.0,
        vx=0.0, vy=0.0, color=1, owner_is_player=False,
    )
    g.balls = [far_ball]
    for ball in g.balls:
        if not ball.owner_is_player and not ball.echo_spawned:
            dist = math.hypot(ball.x - g.player.x, ball.y - g.player.y)
            if dist < NEAR_MISS_RADIUS:
                g._spawn_echo(g.player.x, g.player.y, ball.color)
                ball.echo_spawned = True
    assert len(g.echoes) == 0


# ═══════════════════════════════════════════════════════════════════
# Super deactivation preserves max_combo
# ═══════════════════════════════════════════════════════════════════


def test_super_deactivation_resets_combo_but_preserves_max() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 7
    g.max_combo = 7
    g.super_active = True
    g.super_timer = 1
    g._update_timers()
    assert g.super_active is False
    assert g.combo == 0
    assert g.max_combo == 7  # preserved


# ═══════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
