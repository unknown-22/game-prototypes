"""test_imports.py — Headless logic tests for 248_ping_chain."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (
    AI_COLOR_CYCLE_BASE,
    BALL_SPEED_BASE,
    COMBO_THRESHOLD,
    COLORS,
    GAME_TIME,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    HEAT_MISS,
    NUM_COLORS,
    PADDLE_W,
    SCREEN_H,
    SCREEN_W,
    SUPER_DURATION,
    SUPER_SCORE_MULT,
    TABLE_LEFT,
    TABLE_RIGHT,
    Ball,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def _make_game(phase: Phase = Phase.PLAYING, seed: int = 42) -> Game:
    """Factory: create a Game via __new__ bypass for headless testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = phase
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_TIME
    g.super_timer = 0
    g.player_x = 160.0
    g.player_color_idx = 0  # RED=8
    g.ai_x = 160.0
    g.ai_color_idx = 0
    g._color_cooldown = 0
    g._ai_reaction_timer = 0
    g._ai_color_timer = 0
    g._ghost_trail = []
    g._best_rally = 0
    g._rally_count = 0
    g._screen_shake = 0
    g.particles = []
    g.floats = []
    g.ball = Ball(x=160.0, y=120.0, vx=2.0, vy=-2.0, color=COLORS[0], trail=[])
    return g


# ── Phase Enum ────────────────────────────────────────────────────────


class TestPhase:
    def test_phases(self) -> None:
        assert Phase.TITLE in Phase
        assert Phase.PLAYING in Phase
        assert Phase.GAME_OVER in Phase

    def test_phase_identity(self) -> None:
        g = _make_game(Phase.TITLE)
        assert g.phase == Phase.TITLE
        g.phase = Phase.PLAYING
        assert g.phase == Phase.PLAYING


# ── Dataclasses ────────────────────────────────────────────────────────


class TestBall:
    def test_create(self) -> None:
        b = Ball(x=100.0, y=50.0, vx=2.0, vy=-3.0, color=8)
        assert b.x == 100.0
        assert b.y == 50.0
        assert b.vx == 2.0
        assert b.vy == -3.0
        assert b.color == 8
        assert b.trail == []

    def test_trail(self) -> None:
        b = Ball(x=0.0, y=0.0, vx=1.0, vy=1.0, color=8)
        b.trail.append((10.0, 20.0))
        assert b.trail == [(10.0, 20.0)]


class TestParticle:
    def test_create(self) -> None:
        p = Particle(x=50.0, y=30.0, vx=1.0, vy=-1.0, life=20, color=11)
        assert p.x == 50.0
        assert p.life == 20
        assert p.color == 11


class TestFloatingText:
    def test_create(self) -> None:
        ft = FloatingText(x=100.0, y=50.0, text="+100", life=30, color=10)
        assert ft.text == "+100"
        assert ft.life == 30


# ── Timer ──────────────────────────────────────────────────────────────


class TestTimer:
    def test_decrement(self) -> None:
        g = _make_game()
        initial = g.timer
        g._update_timer()
        assert g.timer == initial - 1

    def test_game_over_on_zero(self) -> None:
        g = _make_game()
        g.timer = 1
        g._update_timer()
        # timer becomes 0, timer <= 0 → GAME_OVER
        assert g.phase == Phase.GAME_OVER


# ── Heat ───────────────────────────────────────────────────────────────


class TestHeat:
    def test_decay(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.001

    def test_decay_floor_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_game_over_at_max(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX
        g._update_heat()
        assert g.phase == Phase.GAME_OVER

    def test_no_game_over_below_max(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX - 0.1
        g._update_heat()
        assert g.phase == Phase.PLAYING


# ── Super Mode ─────────────────────────────────────────────────────────


class TestSuperMode:
    def test_decrement(self) -> None:
        g = _make_game()
        g.super_timer = SUPER_DURATION
        g._update_super_mode()
        assert g.super_timer == SUPER_DURATION - 1

    def test_no_decrement_when_zero(self) -> None:
        g = _make_game()
        g.super_timer = 0
        g._update_super_mode()
        assert g.super_timer == 0

    def test_super_active(self) -> None:
        g = _make_game()
        g.super_timer = 1
        assert g._super_active()
        g.super_timer = 0
        assert not g._super_active()


# ── Combo / Match ──────────────────────────────────────────────────────


class TestPaddleHit:
    def test_color_match_increments_combo(self) -> None:
        g = _make_game()
        g.player_color_idx = 0  # RED=8
        g.ball.color = COLORS[0]  # RED=8, matches
        g._on_paddle_hit(is_player=True)
        assert g.combo == 1

    def test_color_match_adds_score(self) -> None:
        g = _make_game()
        g.player_color_idx = 0
        g.ball.color = COLORS[0]  # match
        g._on_paddle_hit(is_player=True)
        assert g.score == 10  # 10 * 1 * 1

    def test_combo_score_scales(self) -> None:
        g = _make_game()
        g.combo = 4
        g.player_color_idx = 0
        g.ball.color = COLORS[0]  # match
        g._on_paddle_hit(is_player=True)
        assert g.score == 10 * 5  # combo becomes 5, score = 10 * 5

    def test_color_mismatch_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 3
        g.player_color_idx = 0  # RED=8
        g.ball.color = COLORS[1]  # LIME=11, mismatch
        g._on_paddle_hit(is_player=True)
        assert g.combo == 0

    def test_color_mismatch_adds_heat(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g.player_color_idx = 0  # RED=8
        g.ball.color = COLORS[1]  # LIME=11, mismatch
        g._on_paddle_hit(is_player=True)
        assert g.heat == HEAT_MISMATCH

    def test_max_combo_tracks_highest(self) -> None:
        g = _make_game()
        g.combo = 3
        g.max_combo = 3
        g.player_color_idx = 0
        g.ball.color = COLORS[0]  # match
        g._on_paddle_hit(is_player=True)
        assert g.max_combo == 4

    def test_combo_activates_super(self) -> None:
        g = _make_game()
        g.combo = COMBO_THRESHOLD - 1  # 3
        g.player_color_idx = 0
        g.ball.color = COLORS[0]  # match → combo becomes 4
        g._on_paddle_hit(is_player=True)
        assert g.super_timer == SUPER_DURATION

    def test_super_mode_any_color_match(self) -> None:
        g = _make_game()
        g.super_timer = 100  # SUPER active
        g.player_color_idx = 0  # RED=8
        g.ball.color = COLORS[1]  # LIME=11 — would mismatch normally
        g._on_paddle_hit(is_player=True)
        assert g.combo == 1  # matches anyway!

    def test_super_mode_multiplies_score(self) -> None:
        g = _make_game()
        g.super_timer = 100  # SUPER active
        g.player_color_idx = 0
        g.ball.color = COLORS[0]  # match
        g._on_paddle_hit(is_player=True)
        assert g.score == 10 * SUPER_SCORE_MULT  # 10 * 1 * 3

    def test_super_no_reactivate_while_active(self) -> None:
        g = _make_game()
        g.super_timer = 100  # already active
        g.player_color_idx = 0
        g.ball.color = COLORS[0]  # match
        g._on_paddle_hit(is_player=True)
        assert g.super_timer == 100  # unchanged (not reset to SUPER_DURATION)

    def test_player_color_advances_on_match(self) -> None:
        g = _make_game()
        g.player_color_idx = 0
        g.ball.color = COLORS[0]  # match
        g._on_paddle_hit(is_player=True)
        assert g.player_color_idx == 1  # advanced to LIME

    def test_player_color_advances_on_mismatch(self) -> None:
        g = _make_game()
        g.player_color_idx = 0
        g.ball.color = COLORS[1]  # mismatch
        g._on_paddle_hit(is_player=True)
        assert g.player_color_idx == 1  # still advances


# ── Ball Physics ───────────────────────────────────────────────────────


class TestBallPhysics:
    def test_wall_bounce_left(self) -> None:
        g = _make_game()
        g.ball.x = TABLE_LEFT + 1  # near left wall
        g.ball.vx = -2.0  # moving left
        g._update_ball()
        assert g.ball.vx > 0  # bounced right

    def test_wall_bounce_right(self) -> None:
        g = _make_game()
        g.ball.x = TABLE_RIGHT - 1  # near right wall
        g.ball.vx = 2.0  # moving right
        g._update_ball()
        assert g.ball.vx < 0  # bounced left

    def test_ball_speed_escalation(self) -> None:
        g = _make_game()
        g.timer = GAME_TIME  # 0s elapsed
        assert g._ball_speed() == BALL_SPEED_BASE

        g.timer = GAME_TIME - 1800  # 30s elapsed
        speed = g._ball_speed()
        assert speed > BALL_SPEED_BASE
        assert speed <= BALL_SPEED_BASE + 0.02 * 30

    def test_ball_trail_grows(self) -> None:
        g = _make_game()
        g.ball.trail = []
        g._update_ball()
        assert len(g.ball.trail) >= 1

    def test_ball_trail_capped(self) -> None:
        g = _make_game()
        for _ in range(20):
            g._update_ball()
        assert len(g.ball.trail) <= 12


# ── Miss ───────────────────────────────────────────────────────────────


class TestMiss:
    def test_miss_adds_heat(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._on_miss()
        assert g.heat == HEAT_MISS

    def test_miss_resets_rally_count(self) -> None:
        g = _make_game()
        g._rally_count = 10
        g.combo = 3
        g._on_miss()
        assert g._rally_count == 0

    def test_miss_respawns_ball(self) -> None:
        g = _make_game()
        old_ball_id = id(g.ball)
        g._on_miss()
        assert id(g.ball) != old_ball_id  # new ball spawned


# ── AI ──────────────────────────────────────────────────────────────────


class TestAI:
    def test_ai_moves_toward_ball(self) -> None:
        g = _make_game()
        g.ai_x = 100.0
        g.ball.x = 200.0
        g._ai_reaction_timer = 0
        g._update_ai()
        assert g.ai_x > 100.0  # moved right

    def test_ai_moves_left(self) -> None:
        g = _make_game()
        g.ai_x = 200.0
        g.ball.x = 100.0
        g._ai_reaction_timer = 0
        g._update_ai()
        assert g.ai_x < 200.0  # moved left

    def test_ai_clamped_to_table(self) -> None:
        g = _make_game()
        g.ai_x = TABLE_LEFT + PADDLE_W / 2  # at left limit
        g.ball.x = 0
        g._ai_reaction_timer = 0
        g._update_ai()
        assert g.ai_x >= TABLE_LEFT + PADDLE_W / 2

    def test_ai_color_cycles(self) -> None:
        g = _make_game()
        g.ai_color_idx = 0
        g._ai_color_timer = AI_COLOR_CYCLE_BASE  # trigger cycle
        g._update_ai()
        assert g.ai_color_idx == 1


# ── Particles ──────────────────────────────────────────────────────────


class TestParticles:
    def test_spawn_particles(self) -> None:
        g = _make_game()
        g._spawn_particles(100, 100, 8, 5)
        assert len(g.particles) == 5

    def test_particle_update(self) -> None:
        g = _make_game()
        g._spawn_particles(100, 100, 8, 5)
        g._update_particles()
        assert len(g.particles) > 0  # still alive with life 15-25

    def test_particle_dies_after_life_expires(self) -> None:
        g = _make_game()
        g.particles = [Particle(x=0, y=0, life=1)]
        g._update_particles()
        assert len(g.particles) == 0  # dead after life decremented to 0


# ── Floating Text ──────────────────────────────────────────────────────


class TestFloats:
    def test_spawn_float(self) -> None:
        g = _make_game()
        g._spawn_float(100, 100, "+10", 10)
        assert len(g.floats) == 1

    def test_float_update(self) -> None:
        g = _make_game()
        g._spawn_float(100, 100, "+10", 2)
        g._update_floats()
        assert len(g.floats) == 1  # still alive (life=1 after decrement)

    def test_float_dies(self) -> None:
        g = _make_game()
        g.floats = [FloatingText(x=0, y=0, text="x", life=1)]
        g._update_floats()
        assert len(g.floats) == 0


# ── Rally & Ghost ──────────────────────────────────────────────────────


class TestRally:
    def test_rally_count_increments_on_match(self) -> None:
        g = _make_game()
        assert g._rally_count == 0
        g.player_color_idx = 0
        g.ball.color = COLORS[0]  # match
        g._on_paddle_hit(is_player=True)
        assert g._rally_count == 1

    def test_rally_count_resets_on_mismatch(self) -> None:
        g = _make_game()
        g._rally_count = 5
        g.ball.color = COLORS[1]  # mismatch with player_color_idx=0
        g._on_paddle_hit(is_player=True)
        assert g._rally_count == 0

    def test_best_rally_updated(self) -> None:
        g = _make_game()
        g._best_rally = 0
        g._rally_count = 2
        g.player_color_idx = 0  # RED=8
        g.ball.color = COLORS[0]  # match
        g._on_paddle_hit(is_player=True)
        assert g._best_rally == 3
        # _rally_count incremented to 3 from 2 at line 260


# ── Game Over Check ────────────────────────────────────────────────────


class TestGameOver:
    def test_timer_zero(self) -> None:
        g = _make_game()
        g.timer = 0
        g._check_game_over()
        assert g.phase == Phase.GAME_OVER

    def test_timer_negative(self) -> None:
        g = _make_game()
        g.timer = -1
        g._check_game_over()
        assert g.phase == Phase.GAME_OVER

    def test_heat_max(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX
        g._check_game_over()
        assert g.phase == Phase.GAME_OVER

    def test_normal_state(self) -> None:
        g = _make_game()
        g.timer = 1000
        g.heat = 0.0
        g._check_game_over()
        assert g.phase == Phase.PLAYING


# ── Spawn Ball ─────────────────────────────────────────────────────────


class TestSpawnBall:
    def test_ball_created(self) -> None:
        g = _make_game()
        g._spawn_ball()
        assert g.ball is not None
        assert g.ball.vx != 0.0
        assert g.ball.vy != 0.0

    def test_rally_reset_on_spawn(self) -> None:
        g = _make_game()
        g._rally_count = 5
        g._spawn_ball()
        assert g._rally_count == 0


# ── Screen Shake ───────────────────────────────────────────────────────


class TestShake:
    def test_spawn_shake(self) -> None:
        g = _make_game()
        g._screen_shake = 0
        g._spawn_shake()
        assert g._screen_shake > 0


# ── Constants ──────────────────────────────────────────────────────────


class TestConstants:
    def test_colors_count(self) -> None:
        assert len(COLORS) == NUM_COLORS == 4

    def test_table_bounds(self) -> None:
        assert TABLE_LEFT < TABLE_RIGHT
        assert SCREEN_W == 320
        assert SCREEN_H == 240

    def test_paddle_in_table(self) -> None:
        # Paddle fits within table bounds at extremes
        left_clamp = TABLE_LEFT + PADDLE_W / 2
        right_clamp = TABLE_RIGHT - PADDLE_W / 2
        assert left_clamp < right_clamp
        assert left_clamp >= TABLE_LEFT
        assert right_clamp <= TABLE_RIGHT
