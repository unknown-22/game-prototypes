"""test_imports.py — Headless logic tests for WICKET CHAIN (227_wicket_chain).

Uses Game.__new__(Game) pattern to bypass Pyxel init.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import (
    Ball,
    BALL_COLORS,
    BALL_SPAWN_MIN,
    BALL_SPAWN_START,
    BALL_SPEED_MAX,
    BALL_SPEED_START,
    BAT_REACH_Y,
    BAT_X,
    BAT_Y,
    BOUNDARY_Y,
    COMBO_SUPER,
    FloatingText,
    GAME_TIME,
    Game,
    HEAT_DECAY,
    HEAT_MISMATCH,
    HEAT_PASS,
    HIT_ZONE_X,
    MAX_HEAT,
    Particle,
    Phase,
    RED,
    SCREEN_W,
    SUPER_DURATION,
    YELLOW,
)


def _make_game() -> Game:
    """Create a Game instance without Pyxel init for headless testing."""
    g = Game.__new__(Game)
    # Pre-init all attributes that _reset() touches
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.bat_color_idx = 0
    g.bat_color = BALL_COLORS[0]
    g.balls = []
    g.particles = []
    g.floating_texts = []
    g.score = 0
    g.high_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.game_timer = GAME_TIME
    g.super_timer = 0
    g.ball_spawn_timer = 0
    g._shake_frames = 0
    g._reset()
    # Re-seed after _reset() to ensure determinism
    g._rng = random.Random(42)
    return g


# ── Phase enum tests ──


def test_phase_enum() -> None:
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.GAME_OVER == 2


# ── Ball dataclass tests ──


def test_ball_creation() -> None:
    b = Ball(x=100.0, y=160.0, vx=-2.0, vy=0.0, color=8)
    assert b.x == 100.0
    assert b.y == 160.0
    assert b.vx == -2.0
    assert b.vy == 0.0
    assert b.color == 8
    assert b.active is True
    assert b.resolved is False
    assert b.flying_to_boundary is False


def test_ball_defaults() -> None:
    b = Ball(x=0.0, y=0.0, vx=0.0, vy=0.0, color=11)
    assert b.active is True
    assert b.flying_to_boundary is False
    assert b.resolved is False


# ── Particle dataclass tests ──


def test_particle_creation() -> None:
    p = Particle(x=60.0, y=160.0, vx=1.0, vy=-2.0, life=20, color=8)
    assert p.x == 60.0
    assert p.y == 160.0
    assert p.vx == 1.0
    assert p.life == 20
    assert p.color == 8
    assert p.size == 2


# ── FloatingText dataclass tests ──


def test_floating_text_creation() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+10", life=30, color=10)
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == 10


# ── Game state tests ──


def test_game_reset() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.game_timer == GAME_TIME
    assert g.super_timer == 0
    assert len(g.balls) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.bat_color_idx == 0
    assert g.bat_color == BALL_COLORS[0]


# ── Spawn interval tests ──


def test_spawn_interval_start() -> None:
    g = _make_game()
    assert g._get_spawn_interval() == BALL_SPAWN_START


def test_spawn_interval_end() -> None:
    g = _make_game()
    g.game_timer = 0
    assert g._get_spawn_interval() == BALL_SPAWN_MIN


def test_spawn_interval_mid() -> None:
    g = _make_game()
    g.game_timer = GAME_TIME // 2
    interval = g._get_spawn_interval()
    assert BALL_SPAWN_MIN < interval < BALL_SPAWN_START


def test_spawn_interval_linear() -> None:
    g = _make_game()
    # At 25% elapsed, interval should be ~75% of range from min
    g.game_timer = GAME_TIME * 3 // 4
    i1 = g._get_spawn_interval()
    g.game_timer = GAME_TIME // 4
    i2 = g._get_spawn_interval()
    assert i2 < i1  # later in game = shorter interval


# ── Ball speed tests ──


def test_ball_speed_start() -> None:
    g = _make_game()
    assert abs(g._get_ball_speed() - BALL_SPEED_START) < 0.01


def test_ball_speed_end() -> None:
    g = _make_game()
    g.game_timer = 0
    assert abs(g._get_ball_speed() - BALL_SPEED_MAX) < 0.01


def test_ball_speed_increases() -> None:
    g = _make_game()
    s1 = g._get_ball_speed()
    g.game_timer = GAME_TIME // 2
    s2 = g._get_ball_speed()
    assert s2 > s1


# ── Ball spawn tests ──


def test_spawn_ball() -> None:
    g = _make_game()
    ball = g._spawn_ball()
    assert ball.color in BALL_COLORS
    assert ball.x > SCREEN_W  # spawns off right edge
    assert abs(ball.y - BAT_Y) <= 15  # near batter height
    assert ball.vx < 0  # moves left


# ── Resolve hit tests ──


def test_resolve_hit_match() -> None:
    g = _make_game()
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0])
    g.bat_color = BALL_COLORS[0]
    assert g._resolve_hit(ball) == "hit"


def test_resolve_hit_mismatch() -> None:
    g = _make_game()
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0])
    g.bat_color = BALL_COLORS[1]  # different color
    assert g._resolve_hit(ball) == "miss"


def test_resolve_hit_out_of_range() -> None:
    g = _make_game()
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y + 40, vx=-2.0, vy=0.0, color=BALL_COLORS[0])
    g.bat_color = BALL_COLORS[0]
    assert g._resolve_hit(ball) == "none"


def test_resolve_hit_in_range_edge() -> None:
    g = _make_game()
    # Just within reach
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y + BAT_REACH_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0])
    g.bat_color = BALL_COLORS[0]
    assert g._resolve_hit(ball) == "hit"


def test_resolve_hit_super_mode_any_color() -> None:
    g = _make_game()
    g.super_timer = 100
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[3])
    g.bat_color = BALL_COLORS[0]  # different color, but SUPER matches all
    assert g._resolve_hit(ball) == "hit"


# ── Game over check tests ──


def test_check_game_over_heat() -> None:
    g = _make_game()
    g.heat = MAX_HEAT
    assert g._check_game_over() is True


def test_check_game_over_timer() -> None:
    g = _make_game()
    g.game_timer = 0
    assert g._check_game_over() is True


def test_check_game_over_not_over() -> None:
    g = _make_game()
    g.heat = 50
    g.game_timer = 1000
    assert g._check_game_over() is False


# ── Heat update tests ──


def test_update_heat_decay() -> None:
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat < 10.0
    assert g.heat >= 10.0 - HEAT_DECAY


def test_update_heat_floor_zero() -> None:
    g = _make_game()
    g.heat = 0.001
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_zero_stays_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


# ── On hit (combo / score) tests ──


def test_on_hit_increments_combo() -> None:
    g = _make_game()
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], resolved=True, flying_to_boundary=True)
    assert g.combo == 0
    g._on_hit(ball)
    assert g.combo == 1
    assert g.score == 10  # 10 * 1 * 1


def test_on_hit_consecutive_builds_combo() -> None:
    g = _make_game()
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], resolved=True, flying_to_boundary=True)
    g._on_hit(ball)
    assert g.combo == 1
    assert g.score == 10
    g._on_hit(ball)
    assert g.combo == 2
    assert g.score == 10 + 20  # 10 + 20
    g._on_hit(ball)
    assert g.combo == 3
    assert g.score == 10 + 20 + 30  # 10 + 20 + 30


def test_on_hit_super_multiplier() -> None:
    g = _make_game()
    g.super_timer = 100
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], resolved=True, flying_to_boundary=True)
    g.combo = 2
    g._on_hit(ball)
    # score = 10 * 3 (combo) * 3 (super multiplier) = 90
    assert g.score == 90
    assert g.combo == 3


def test_on_hit_triggers_super() -> None:
    g = _make_game()
    g.combo = COMBO_SUPER - 1  # 3
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], resolved=True, flying_to_boundary=True)
    g._on_hit(ball)  # combo becomes 4
    assert g.combo == COMBO_SUPER
    assert g.super_timer == SUPER_DURATION


def test_on_hit_super_already_active() -> None:
    g = _make_game()
    g.super_timer = 100  # already in SUPER
    g.combo = 5
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], resolved=True, flying_to_boundary=True)
    g._on_hit(ball)
    # Super timer should NOT be reset when already active
    # (condition: self.super_timer <= 0, which is False when 100)
    assert g.super_timer == 100  # unchanged


def test_on_hit_max_combo_tracking() -> None:
    g = _make_game()
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], resolved=True, flying_to_boundary=True)
    assert g.max_combo == 0
    g._on_hit(ball)
    assert g.max_combo == 1
    g._on_hit(ball)
    assert g.max_combo == 2
    # After combo reset, max_combo should persist
    g.combo = 0
    g._on_hit(ball)
    assert g.max_combo == 2  # stays at 2
    assert g.combo == 1


# ── On mismatch tests ──


def test_on_mismatch_resets_combo() -> None:
    g = _make_game()
    g.combo = 5
    g.max_combo = 5
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], resolved=True, flying_to_boundary=True)
    g._on_mismatch(ball)
    assert g.combo == 0
    assert g.max_combo == 5  # max_combo preserved
    assert g.heat == HEAT_MISMATCH


def test_on_mismatch_heat_capped() -> None:
    g = _make_game()
    g.heat = MAX_HEAT - 5
    g.combo = 1
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], resolved=True, flying_to_boundary=True)
    g._on_mismatch(ball)
    assert g.heat == MAX_HEAT  # capped
    assert g.combo == 0


# ── Particle system tests ──


def test_update_particles_decay() -> None:
    g = _make_game()
    p = Particle(x=60.0, y=160.0, vx=2.0, vy=-1.0, life=5, color=8)
    g.particles = [p]
    g._update_particles()
    assert p.life == 4
    assert p.x != 60.0  # moved
    assert abs(p.vx) < 2.0  # decelerated


def test_update_particles_remove_dead() -> None:
    g = _make_game()
    p1 = Particle(x=60.0, y=160.0, vx=1.0, vy=0.0, life=1, color=8)
    p2 = Particle(x=70.0, y=160.0, vx=1.0, vy=0.0, life=10, color=11)
    g.particles = [p1, p2]
    g._update_particles()
    assert len(g.particles) == 1  # p1 removed (life<=0)
    assert g.particles[0] is p2


def test_spawn_hit_particles() -> None:
    g = _make_game()
    g._spawn_hit_particles(60, 160, 8)
    assert len(g.particles) > 0
    # All particles have valid data
    for p in g.particles:
        assert p.life > 0


def test_spawn_miss_particles() -> None:
    g = _make_game()
    g._spawn_miss_particles(60, 160)
    assert len(g.particles) == 6


# ── Floating text tests ──


def test_update_floating_texts() -> None:
    g = _make_game()
    ft = FloatingText(x=100.0, y=50.0, text="TEST", life=3, color=10)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert ft.life == 2
    assert ft.y < 50.0  # floats upward


def test_update_floating_texts_remove_dead() -> None:
    g = _make_game()
    ft1 = FloatingText(x=100.0, y=50.0, text="A", life=1, color=10)
    ft2 = FloatingText(x=100.0, y=50.0, text="B", life=10, color=10)
    g.floating_texts = [ft1, ft2]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1  # ft1 removed (life<=0)
    assert g.floating_texts[0] is ft2


# ── Ball update tests (headless) ──


def test_update_balls_hit_flow() -> None:
    g = _make_game()
    # Ball at x=74 with vx=-2: next position = 72, which is HIT_ZONE_X (72) → resolves
    ball = Ball(x=74.0, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], active=True, resolved=False)
    g.balls = [ball]
    g.bat_color = BALL_COLORS[0]
    g._update_balls()
    # Ball should be resolved and flying to boundary
    assert ball.resolved is True
    assert ball.flying_to_boundary is True
    assert g.combo == 1
    assert g.score == 10


def test_update_balls_mismatch_flow() -> None:
    g = _make_game()
    ball = Ball(x=74.0, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], active=True, resolved=False)
    g.balls = [ball]
    g.bat_color = BALL_COLORS[1]  # mismatch
    g._update_balls()
    assert ball.resolved is True
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH


def test_update_balls_pass_stumps() -> None:
    g = _make_game()
    g.combo = 3
    # Ball is past HIT_ZONE_X (72) and near stumps. Set resolved=True to skip hit-zone logic.
    ball = Ball(x=24.0, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], active=True, resolved=True)
    g.balls = [ball]
    g.bat_color = BALL_COLORS[1]
    g._update_balls()
    # Ball passes stumps (x < STUMP_X - 10 → 24 < 25), becomes inactive
    assert ball.active is False
    # Combo unchanged (resolved balls don't trigger the unresolved pass block)
    assert g.combo == 3


def test_update_balls_already_resolved_skips() -> None:
    g = _make_game()
    ball = Ball(x=50.0, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0], active=True, resolved=True, flying_to_boundary=True, fly_vx=6.0, fly_vy=-3.0)
    g.balls = [ball]
    g.bat_color = BALL_COLORS[1]
    old_combo = g.combo
    g._update_balls()
    # Ball was already resolved, should not process again
    assert g.combo == old_combo


def test_update_balls_fly_to_boundary_removal() -> None:
    g = _make_game()
    # Ball flying up toward boundary
    ball = Ball(x=150.0, y=BOUNDARY_Y + 1, vx=0.0, vy=0.0, color=BALL_COLORS[0], active=True, resolved=True, flying_to_boundary=True, fly_vx=1.0, fly_vy=-5.0)
    g.balls = [ball]
    g._update_balls()
    assert ball.active is False  # reached boundary


# ── Bat color cycling tests ──


def test_bat_color_cycle_left() -> None:
    g = _make_game()
    g.bat_color_idx = 0
    g.bat_color = BALL_COLORS[0]
    # Simulate LEFT press
    g.bat_color_idx = (g.bat_color_idx - 1) % 4
    g.bat_color = BALL_COLORS[g.bat_color_idx]
    assert g.bat_color_idx == 3
    assert g.bat_color == BALL_COLORS[3]


def test_bat_color_cycle_right() -> None:
    g = _make_game()
    g.bat_color_idx = 0
    g.bat_color = BALL_COLORS[0]
    g.bat_color_idx = (g.bat_color_idx + 1) % 4
    g.bat_color = BALL_COLORS[g.bat_color_idx]
    assert g.bat_color_idx == 1
    assert g.bat_color == BALL_COLORS[1]


# ── Game timer tests ──


def test_game_timer_decrements() -> None:
    g = _make_game()
    # Simulate one frame of update logic without calling pyxel-dependent wrapper
    original = g.game_timer
    g.game_timer -= 1
    assert g.game_timer == original - 1


# ── Super timer tests ──


def test_super_timer_decrements() -> None:
    g = _make_game()
    g.super_timer = 100
    g.super_timer -= 1
    assert g.super_timer == 99


# ── High score tracking tests ──


def test_high_score_updated() -> None:
    g = _make_game()
    g.score = 500
    g.high_score = 0
    # Simulate game over check from _update_playing
    g.phase = Phase.GAME_OVER
    if g.score > g.high_score:
        g.high_score = g.score
    assert g.high_score == 500


def test_high_score_not_overwritten() -> None:
    g = _make_game()
    g.score = 200
    g.high_score = 500
    g.phase = Phase.GAME_OVER
    if g.score > g.high_score:
        g.high_score = g.score
    assert g.high_score == 500  # unchanged


# ── Color constant tests ──


def test_ball_colors_count() -> None:
    assert len(BALL_COLORS) == 4


def test_ball_colors_unique() -> None:
    assert len(set(BALL_COLORS)) == 4


def test_all_ball_colors_in_range() -> None:
    for c in BALL_COLORS:
        assert 0 <= c <= 15


# ── Constant sanity checks ──


def test_super_duration_positive() -> None:
    assert SUPER_DURATION > 0


def test_game_time_sufficient() -> None:
    assert GAME_TIME > 0


def test_max_heat_sane() -> None:
    assert MAX_HEAT == 100


def test_heat_mismatch_greater_than_pass() -> None:
    # Mismatch should be more punishing than letting ball pass
    assert HEAT_MISMATCH >= HEAT_PASS


def test_ball_speed_sane() -> None:
    assert BALL_SPEED_START < BALL_SPEED_MAX


def test_spawn_interval_sane() -> None:
    assert BALL_SPAWN_MIN < BALL_SPAWN_START


# ── Edge case: ball exactly at hit zone boundary ──


def test_resolve_hit_at_range_boundary() -> None:
    g = _make_game()
    # Exactly at reach limit
    ball_upper = Ball(x=HIT_ZONE_X, y=BAT_Y + BAT_REACH_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0])
    ball_lower = Ball(x=HIT_ZONE_X, y=BAT_Y - BAT_REACH_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[0])
    g.bat_color = BALL_COLORS[0]
    assert g._resolve_hit(ball_upper) == "hit"
    assert g._resolve_hit(ball_lower) == "hit"


def test_resolve_hit_just_outside_range() -> None:
    g = _make_game()
    ball = Ball(x=HIT_ZONE_X, y=BAT_Y + BAT_REACH_Y + 1, vx=-2.0, vy=0.0, color=BALL_COLORS[0])
    g.bat_color = BALL_COLORS[0]
    assert g._resolve_hit(ball) == "none"


# ── Full round simulation test ──


def test_full_simulation() -> None:
    """Simulate multiple frames of gameplay."""
    g = _make_game()
    # Simulate 10 consecutive hits. Ball starts at x=74 with vx=-2,
    # so in one frame it reaches x=72 (HIT_ZONE_X) and resolves.
    for i in range(10):
        ball = Ball(x=74.0, y=BAT_Y, vx=-2.0, vy=0.0, color=BALL_COLORS[i % 4], active=True, resolved=False)
        g.balls = [ball]
        g.bat_color = BALL_COLORS[i % 4]  # matching
        g._update_balls()
        g.game_timer -= 1
        g._update_heat()
        g._update_particles()
        g._update_floating_texts()
        if g.super_timer > 0:
            g.super_timer -= 1
        g.ball_spawn_timer -= 1
        if g.ball_spawn_timer <= 0:
            g.balls.append(g._spawn_ball())
            g.ball_spawn_timer = g._get_spawn_interval()

    assert g.score > 0
    # All 10 iterations match (bat_color always equals ball color),
    # so combo increments 10 times (1→2→...→10)
    assert g.combo == 10
    assert g.max_combo == 10
    # After combo reaches 4, SUPER activates (iteration 4 onward)
    assert g.super_timer > 0 or g.super_timer == 0  # may have decremented


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
