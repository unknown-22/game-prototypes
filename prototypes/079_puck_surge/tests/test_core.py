"""Tests for 079_puck_surge core logic."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (
    COL_RED,
    COL_YELLOW,
    FLOAT_LIFE,
    GAME_DURATION,
    MAX_HP,
    PUCK_RADIUS,
    PUCK_SPEED_MIN,
    SURGE_COOLDOWN,
    SURGE_DURATION,
    Game,
    Particle,
    Phase,
    Puck,
)


def make_game() -> Game:
    """Create a headless Game instance for testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.font = None  # type: ignore[assignment]
    # pre-init attributes that reset() touches
    g.particles = []
    g.floats = []
    g.reset()
    return g


# ── Spawn puck ─────────────────────────────────────────────────────────────
def test_spawn_puck() -> None:
    g = make_game()
    assert len(g.pucks) == 0
    g._spawn_puck()
    assert len(g.pucks) == 1
    puck = g.pucks[0]
    assert puck.radius == PUCK_RADIUS
    assert puck.color in {8, 3, 6, 9}
    speed = (puck.vx**2 + puck.vy**2) ** 0.5
    assert PUCK_SPEED_MIN <= speed <= 2.5


# ── Puck movement ──────────────────────────────────────────────────────────
def test_update_pucks_wall_bounce() -> None:
    g = make_game()
    g.pucks = [Puck(x=15.0, y=120.0, vx=-2.0, vy=0.0, color=COL_RED)]
    g._update_pucks()
    assert g.pucks[0].vx > 0


# ── Paddle collision ───────────────────────────────────────────────────────
def test_check_paddle_collision() -> None:
    g = make_game()
    g.pucks = [Puck(x=160.0, y=196.0, vx=0.0, vy=-3.0, color=8)]
    collisions = g._check_paddle_collision(160.0, 200.0, 40.0, 8.0, is_player=True)
    assert collisions == 1
    assert g.pucks[0].vy > 0  # should bounce back
    assert g.last_hit_color == 8


def test_combo_increment_same_color() -> None:
    g = make_game()
    g.last_hit_color = 8
    g.combo = 2
    g.pucks = [Puck(x=160.0, y=196.0, vx=0.0, vy=-3.0, color=8)]
    g._check_paddle_collision(160.0, 200.0, 40.0, 8.0, is_player=True)
    assert g.combo == 3


def test_combo_reset_different_color() -> None:
    g = make_game()
    g.last_hit_color = 8
    g.combo = 3
    g.pucks = [Puck(x=160.0, y=196.0, vx=0.0, vy=-3.0, color=3)]
    g._check_paddle_collision(160.0, 200.0, 40.0, 8.0, is_player=True)
    assert g.combo == 0


# ── Goal scoring ───────────────────────────────────────────────────────────
def test_player_scores_goal() -> None:
    g = make_game()
    g.combo = 1
    g.surge_timer = 0
    g.pucks = [Puck(x=160.0, y=5.0, vx=0.0, vy=-2.0, color=8)]
    scored, ai_scored = g._check_goals()
    assert scored == 200  # BASE_SCORE * (1 + 1) * 1
    assert ai_scored == 0
    assert len(g.pucks) == 0


def test_ai_scores_goal() -> None:
    g = make_game()
    g.pucks = [Puck(x=160.0, y=240.0, vx=0.0, vy=2.0, color=8)]
    scored, ai_scored = g._check_goals()
    assert scored == 0
    assert ai_scored == 1


def test_surge_goal_multiplier() -> None:
    g = make_game()
    g.surge_timer = 10
    g.combo = 0
    g.pucks = [Puck(x=160.0, y=5.0, vx=0.0, vy=-2.0, color=8)]
    scored, _ = g._check_goals()
    assert scored == 300  # BASE_SCORE * 1 * 3
    assert g._shake_frames == 2


# ── SURGE ──────────────────────────────────────────────────────────────────
def test_enter_surge() -> None:
    g = make_game()
    g._enter_surge()
    assert g.surge_timer == SURGE_DURATION
    assert g.surge_cooldown == SURGE_DURATION + SURGE_COOLDOWN
    assert g.combo == 0


def test_surge_timers_decrement() -> None:
    g = make_game()
    g.surge_timer = 5
    g.surge_cooldown = 10
    g._update_surge_timers()
    assert g.surge_timer == 4
    assert g.surge_cooldown == 9


def test_combo_4_triggers_surge() -> None:
    g = make_game()
    g.last_hit_color = 8
    g.combo = 3
    assert g.can_surge is True
    g.pucks = [Puck(x=160.0, y=196.0, vx=0.0, vy=-3.0, color=8)]
    g._check_paddle_collision(160.0, 200.0, 40.0, 8.0, is_player=True)
    assert g.surge_timer > 0


def test_surge_blocked_during_cooldown() -> None:
    g = make_game()
    g.surge_cooldown = 100
    assert g.can_surge is False
    g.last_hit_color = 8
    g.combo = 3
    g.pucks = [Puck(x=160.0, y=196.0, vx=0.0, vy=-3.0, color=8)]
    g._check_paddle_collision(160.0, 200.0, 40.0, 8.0, is_player=True)
    assert g.surge_timer == 0  # surge not triggered while cooling down


# ── Surge puck color ───────────────────────────────────────────────────────
def test_get_puck_draw_color_normal() -> None:
    g = make_game()
    puck = Puck(0, 0, 0, 0, 8)
    assert g._get_puck_draw_color(puck) == 8


def test_get_puck_draw_color_surge() -> None:
    g = make_game()
    g.surge_timer = 10
    puck = Puck(0, 0, 0, 0, 8)
    col = g._get_puck_draw_color(puck)
    assert col in {2, 3, 8, 9, 10, 12}  # SURGE_RAINBOW colors


# ── Timer ──────────────────────────────────────────────────────────────────
def test_update_timer_game_over() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


def test_update_timer_best_score() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.timer = 1
    g.score = 500
    g.best_score = 300
    g._update_timer()
    assert g.best_score == 500


# ── Difficulty ─────────────────────────────────────────────────────────────
def test_update_difficulty_reduces_spawn_interval() -> None:
    g = make_game()
    g.timer = GAME_DURATION - 15 * 30  # 15 seconds elapsed
    g._update_difficulty()
    assert g.spawn_interval < 60


# ── Reset ──────────────────────────────────────────────────────────────────
def test_reset_initializes_all() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.hp == MAX_HP
    assert g.timer == GAME_DURATION
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.surge_timer == 0
    assert g.surge_cooldown == 0
    assert g.pucks == []
    assert g.particles == []
    assert g.floats == []
    assert g.last_hit_color == -1


# ── Particles ──────────────────────────────────────────────────────────────
def test_spawn_particles() -> None:
    g = make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100, 100, COL_RED, 8)
    assert len(g.particles) == 8
    for p in g.particles:
        assert p.color == COL_RED
        assert 10 <= p.life <= 20


def test_update_particles_removes_dead() -> None:
    g = make_game()
    g.particles = [
        Particle(0, 0, 0, 0, 0, COL_RED),
        Particle(0, 0, 0, 0, 5, COL_RED),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


# ── Floating text ──────────────────────────────────────────────────────────
def test_spawn_and_update_floats() -> None:
    g = make_game()
    g._spawn_float(160, 100, "TEST", COL_YELLOW)
    assert len(g.floats) == 1
    assert g.floats[0].life == FLOAT_LIFE
    g._update_floats()
    assert g.floats[0].life == FLOAT_LIFE - 1
    assert g.floats[0].y < 100


def test_update_floats_removes_dead() -> None:
    g = make_game()
    from main import FloatingText

    g.floats = [
        FloatingText(0, 0, "A", 0, COL_YELLOW),
        FloatingText(0, 0, "B", 5, COL_YELLOW),
    ]
    g._update_floats()
    assert len(g.floats) == 1
    assert g.floats[0].text == "B"


# ── Properties ─────────────────────────────────────────────────────────────
def test_time_left() -> None:
    g = make_game()
    g.timer = 300
    assert g.time_left == 10


def test_is_surge() -> None:
    g = make_game()
    g.surge_timer = 0
    assert not g.is_surge
    g.surge_timer = 5
    assert g.is_surge


def test_can_surge() -> None:
    g = make_game()
    g.surge_timer = 0
    g.surge_cooldown = 0
    assert g.can_surge
    g.surge_cooldown = 1
    assert not g.can_surge
    g.surge_cooldown = 0
    g.surge_timer = 1
    assert not g.can_surge
