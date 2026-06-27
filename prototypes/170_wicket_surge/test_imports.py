"""test_imports.py — Headless logic tests for WICKET SURGE."""
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/170_wicket_surge")
from main import (
    BAT_COLORS,
    BASE_BALL_SPEED,
    BASE_SPAWN_INTERVAL,
    BALL_RADIUS,
    COLOR_CYCLE_FRAMES,
    HEAT_DECAY,
    HEAT_WRONG_HIT,
    MAX_BALL_SPEED,
    MAX_HEAT,
    MAX_WICKETS,
    MIN_SPAWN_INTERVAL,
    STRIKE_ZONE_H,
    STRIKE_ZONE_W,
    STRIKE_ZONE_X,
    STRIKE_ZONE_Y,
    SUPER_DURATION,
    Ball,
    Game,
    Particle,
    Phase,
)


def _make_game() -> Game:
    """Create a Game instance without Pyxel init for headless testing."""
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.wickets = 0
    g.bat_color = 0
    g.color_timer = COLOR_CYCLE_FRAMES
    g.super_mode = False
    g.super_timer = 0
    g.balls = []
    g.particles = []
    g.spawn_timer = BASE_SPAWN_INTERVAL
    g.shake_frames = 0
    g.game_timer = 0
    g.high_score = 0
    g.reset()
    return g


# --- Constants ---


def test_constants() -> None:
    """Verify module-level constants."""
    assert len(BAT_COLORS) == 4
    assert all(isinstance(c, int) for c in BAT_COLORS)
    assert BASE_BALL_SPEED == 1.5
    assert MAX_BALL_SPEED == 4.0
    assert HEAT_WRONG_HIT == 20.0
    assert MAX_HEAT == 100.0
    assert MAX_WICKETS == 3
    assert SUPER_DURATION == 300


# --- Enum ---


def test_phase_enum() -> None:
    """Phase enum has expected members."""
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# --- Dataclasses ---


def test_ball_dataclass() -> None:
    """Ball dataclass creates correctly."""
    b = Ball(x=100.0, y=50.0, color=0, active=True)
    assert b.x == 100.0
    assert b.y == 50.0
    assert b.color == 0
    assert b.active is True

    b2 = Ball(x=200.0, y=10.0, color=2)
    assert b2.active is True  # default
    assert b2.color == 2


def test_particle_dataclass() -> None:
    """Particle dataclass creates correctly."""
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=10, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 10
    assert p.color == 8
    assert p.gravity == 0.0  # default


# --- Game Initialization ---


def test_reset_initializes_state() -> None:
    """reset() sets game to PLAYING with zeroed state."""
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.wickets == 0
    assert g.bat_color == 0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert len(g.balls) == 0
    assert len(g.particles) == 0
    assert g.spawn_timer == BASE_SPAWN_INTERVAL


# --- Ball Spawning ---


def test_spawn_ball_creates_valid_ball() -> None:
    """_spawn_ball creates a Ball with valid position and color."""
    g = _make_game()
    ball = g._spawn_ball()
    assert isinstance(ball, Ball)
    assert ball.active is True
    assert 0 <= ball.color <= 3
    assert 0 <= ball.x <= 320
    assert 0 <= ball.y <= 30


def test_spawn_ball_is_deterministic() -> None:
    """Same seed produces same ball."""
    g1 = _make_game()
    g1.rng = random.Random(42)
    b1 = g1._spawn_ball()

    g2 = _make_game()
    g2.rng = random.Random(42)
    b2 = g2._spawn_ball()

    assert b1.x == b2.x
    assert b1.y == b2.y
    assert b1.color == b2.color


# --- Speed and Interval Calculations ---


def test_ball_speed_default() -> None:
    """_ball_speed returns base speed at score=0."""
    g = _make_game()
    assert g._ball_speed() == 1.5


def test_ball_speed_scales_with_score() -> None:
    """_ball_speed increases with score."""
    g = _make_game()
    g.score = 500
    assert abs(g._ball_speed() - 2.5) < 0.01


def test_ball_speed_capped() -> None:
    """_ball_speed does not exceed MAX_BALL_SPEED."""
    g = _make_game()
    g.score = 100000
    assert g._ball_speed() == MAX_BALL_SPEED


def test_spawn_interval_default() -> None:
    """_spawn_interval returns base at score=0."""
    g = _make_game()
    assert g._spawn_interval() == BASE_SPAWN_INTERVAL


def test_spawn_interval_decreases() -> None:
    """_spawn_interval decreases as score increases."""
    g = _make_game()
    g.score = 100
    assert g._spawn_interval() < BASE_SPAWN_INTERVAL


def test_spawn_interval_minimum() -> None:
    """_spawn_interval has a minimum."""
    g = _make_game()
    g.score = 100000
    assert g._spawn_interval() == MIN_SPAWN_INTERVAL


# --- Strike Zone ---


def test_strike_zone_contains_ball_inside() -> None:
    """Ball centered in strike zone returns True."""
    g = _make_game()
    ball = Ball(
        x=STRIKE_ZONE_X + STRIKE_ZONE_W // 2,
        y=STRIKE_ZONE_Y + STRIKE_ZONE_H // 2,
        color=0,
        active=True,
    )
    assert g._strike_zone_contains(ball) is True


def test_strike_zone_contains_ball_outside_left() -> None:
    """Ball left of strike zone returns False."""
    g = _make_game()
    ball = Ball(x=STRIKE_ZONE_X - BALL_RADIUS - 1, y=STRIKE_ZONE_Y + 10, color=0, active=True)
    assert g._strike_zone_contains(ball) is False


def test_strike_zone_contains_ball_outside_above() -> None:
    """Ball above strike zone returns False."""
    g = _make_game()
    ball = Ball(x=STRIKE_ZONE_X + 10, y=STRIKE_ZONE_Y - BALL_RADIUS - 1, color=0, active=True)
    assert g._strike_zone_contains(ball) is False


def test_strike_zone_contains_ball_partially_overlapping() -> None:
    """Ball edge touching strike zone boundary returns True."""
    g = _make_game()
    ball = Ball(x=STRIKE_ZONE_X + BALL_RADIUS, y=STRIKE_ZONE_Y + BALL_RADIUS, color=0, active=True)
    assert g._strike_zone_contains(ball) is True


# --- Hit Handling ---


def test_handle_hit_increases_score_and_combo() -> None:
    """Hitting a ball increments score and combo."""
    g = _make_game()
    ball = Ball(x=160.0, y=195.0, color=0, active=True)
    g.balls = [ball]
    g.bat_color = 0
    g._handle_hit(ball)

    assert ball.active is False
    assert g.score > 0
    assert g.combo == 1
    assert g.max_combo == 1


def test_handle_hit_combo_multiplier() -> None:
    """Score increases with combo multiplier."""
    g = _make_game()
    g.combo = 3  # multiplier = 1 + 3*0.5 = 2.5

    ball = Ball(x=160.0, y=195.0, color=0, active=True)
    g.balls = [ball]
    g.bat_color = 0
    g._handle_hit(ball)

    # base_score=10, multiplier=2.5 => 25
    assert g.score == 25
    assert g.combo == 4


def test_handle_hit_super_mode_triple_score() -> None:
    """SUPER mode triples base score."""
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.combo = 0  # multiplier = 1.0

    ball = Ball(x=160.0, y=195.0, color=2, active=True)
    g.balls = [ball]
    g._handle_hit(ball)  # super_mode makes all colors match

    # base_score=10*3=30, multiplier=1.0 => 30
    assert g.score == 30


def test_handle_hit_spawns_particles() -> None:
    """Hit spawns particles."""
    g = _make_game()
    ball = Ball(x=160.0, y=195.0, color=0, active=True)
    g.balls = [ball]
    g.bat_color = 0
    g._handle_hit(ball)

    assert len(g.particles) >= 5


def test_handle_hit_activates_super_at_combo_4() -> None:
    """COMBO >= 4 activates SUPER mode."""
    g = _make_game()
    g.combo = 3

    ball = Ball(x=160.0, y=195.0, color=0, active=True)
    g.balls = [ball]
    g.bat_color = 0
    g._handle_hit(ball)

    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_handle_hit_does_not_reactivate_super() -> None:
    """Already in SUPER mode, hitting doesn't reset timer."""
    g = _make_game()
    g.super_mode = True
    g.super_timer = 50
    g.combo = 4

    ball = Ball(x=160.0, y=195.0, color=0, active=True)
    g.balls = [ball]
    g.bat_color = 0
    g._handle_hit(ball)

    assert g.super_timer == 50  # unchanged


# --- Wrong Hit Handling ---


def test_handle_wrong_hit_resets_combo() -> None:
    """Wrong-color hit resets combo to 0."""
    g = _make_game()
    g.combo = 5
    g.max_combo = 5
    g._handle_wrong_hit()

    assert g.combo == 0
    assert g.max_combo == 5  # max_combo preserved


def test_handle_wrong_hit_adds_heat_and_wicket() -> None:
    """Wrong hit adds heat and loses a wicket."""
    g = _make_game()
    initial_heat = g.heat
    initial_wickets = g.wickets

    g._handle_wrong_hit()

    assert g.heat > initial_heat
    assert g.wickets == initial_wickets + 1


def test_handle_wrong_hit_triggers_shake() -> None:
    """Wrong hit sets shake_frames."""
    g = _make_game()
    g._handle_wrong_hit()
    assert g.shake_frames > 0


def test_handle_wrong_hit_spawns_wicket_particles() -> None:
    """Wrong hit spawns wicket particles."""
    g = _make_game()
    g._handle_wrong_hit()
    assert len(g.particles) >= 20


# --- Miss Handling ---


def test_handle_miss_deactivates_ball() -> None:
    """Miss deactivates the ball."""
    g = _make_game()
    ball = Ball(x=160.0, y=220.0, color=0, active=True)
    g.balls = [ball]
    g._handle_miss(ball)

    assert ball.active is False


def test_handle_miss_resets_combo() -> None:
    """Miss resets combo."""
    g = _make_game()
    g.combo = 3
    ball = Ball(x=160.0, y=220.0, color=0, active=True)
    g.balls = [ball]
    g._handle_miss(ball)

    assert g.combo == 0


def test_handle_miss_adds_wicket() -> None:
    """Miss adds a wicket."""
    g = _make_game()
    ball = Ball(x=160.0, y=220.0, color=0, active=True)
    g.balls = [ball]
    g._handle_miss(ball)

    assert g.wickets == 1


def test_handle_miss_deactivates_super() -> None:
    """Miss during SUPER mode deactivates it."""
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    ball = Ball(x=160.0, y=220.0, color=0, active=True)
    g.balls = [ball]
    g._handle_miss(ball)

    assert g.super_mode is False
    assert g.super_timer == 0


# --- Check Swing ---


def test_check_swing_returns_negative_for_no_balls() -> None:
    """_check_swing returns -1 when no balls in zone."""
    g = _make_game()
    result = g._check_swing(160, 200)
    assert result == -1


def test_check_swing_hit_matching_color() -> None:
    """_check_swing returns 0 for matching color hit."""
    g = _make_game()
    g.bat_color = 1  # GREEN
    ball = Ball(x=160.0, y=195.0, color=1, active=True)  # GREEN
    g.balls = [ball]
    result = g._check_swing(160, 200)

    assert result == 0
    assert ball.active is False
    assert g.combo == 1


def test_check_swing_wrong_color() -> None:
    """_check_swing returns 1 for wrong color."""
    g = _make_game()
    g.bat_color = 0  # RED
    ball = Ball(x=160.0, y=195.0, color=1, active=True)  # GREEN
    g.balls = [ball]
    result = g._check_swing(160, 200)

    assert result == 1
    assert g.wickets == 1


def test_check_swing_super_mode_always_hits() -> None:
    """SUPER mode hits any color."""
    g = _make_game()
    g.super_mode = True
    g.bat_color = 0  # RED
    ball = Ball(x=160.0, y=195.0, color=3, active=True)  # YELLOW
    g.balls = [ball]
    result = g._check_swing(160, 200)

    assert result == 0
    assert ball.active is False


def test_check_swing_outside_bat_x() -> None:
    """Click outside bat x-range returns -1."""
    g = _make_game()
    ball = Ball(x=160.0, y=195.0, color=0, active=True)
    g.balls = [ball]
    g.bat_color = 0
    result = g._check_swing(0, 200)  # far left of bat
    assert result == -1


# --- Heat System ---


def test_update_heat_decays() -> None:
    """_update_heat decays heat over time."""
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0
    assert g.heat >= 50.0 - HEAT_DECAY


def test_update_heat_floor_zero() -> None:
    """_update_heat floors at 0."""
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_check_game_over_wickets() -> None:
    """3 wickets triggers game over."""
    g = _make_game()
    g.wickets = 3
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_check_game_over_heat() -> None:
    """Heat >= MAX_HEAT triggers game over."""
    g = _make_game()
    g.heat = 100.0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_check_game_over_updates_high_score() -> None:
    """Game over updates high_score."""
    g = _make_game()
    g.score = 500
    g.high_score = 300
    g.wickets = 3
    g._check_game_over()
    assert g.high_score == 500


def test_check_game_over_does_not_lower_high_score() -> None:
    """Game over keeps higher high_score."""
    g = _make_game()
    g.score = 200
    g.high_score = 500
    g.wickets = 3
    g._check_game_over()
    assert g.high_score == 500


# --- Bat Color Cycling ---


def test_cycle_bat_color_decrements_timer() -> None:
    """_cycle_bat_color decrements the timer."""
    g = _make_game()
    initial = g.color_timer
    g._cycle_bat_color()
    assert g.color_timer == initial - 1


def test_cycle_bat_color_switches_at_zero() -> None:
    """_cycle_bat_color switches color when timer hits 0."""
    g = _make_game()
    g.bat_color = 0
    g.color_timer = 1  # will hit 0 on next call
    g._cycle_bat_color()
    assert g.bat_color == 1
    assert g.color_timer == COLOR_CYCLE_FRAMES


def test_cycle_bat_color_wraps_around() -> None:
    """_cycle_bat_color wraps from 3 back to 0."""
    g = _make_game()
    g.bat_color = 3
    g.color_timer = 1
    g._cycle_bat_color()
    assert g.bat_color == 0


def test_cycle_bat_color_blocked_in_super() -> None:
    """_cycle_bat_color does nothing during SUPER mode."""
    g = _make_game()
    g.super_mode = True
    g.bat_color = 0
    g.color_timer = 1
    g._cycle_bat_color()
    assert g.bat_color == 0  # unchanged
    assert g.color_timer == 1  # unchanged


# --- Super Mode ---


def test_activate_super_sets_flags() -> None:
    """_activate_super sets super_mode and super_timer."""
    g = _make_game()
    g._activate_super()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_deactivate_super_clears_flags() -> None:
    """_deactivate_super clears super state."""
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g._deactivate_super()
    assert g.super_mode is False
    assert g.super_timer == 0


def test_update_super_decrements_timer() -> None:
    """_update_super decrements timer."""
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g._update_super()
    assert g.super_timer == 99


def test_update_super_deactivates_at_zero() -> None:
    """_update_super deactivates when timer reaches 0."""
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_mode is False
    assert g.super_timer == 0


def test_update_super_noop_when_not_active() -> None:
    """_update_super does nothing when not in super mode."""
    g = _make_game()
    g.super_mode = False
    g.super_timer = 0
    g._update_super()
    assert g.super_mode is False
    assert g.super_timer == 0


# --- Ball Update ---


def test_update_balls_moves_balls_down() -> None:
    """_update_balls moves active balls downward."""
    g = _make_game()
    ball = Ball(x=160.0, y=0.0, color=0, active=True)
    g.balls = [ball]
    g._update_balls()
    assert ball.y > 0


def test_update_balls_removes_off_screen_balls() -> None:
    """_update_balls removes balls that go off screen."""
    g = _make_game()
    ball = Ball(x=160.0, y=300.0, color=0, active=True)
    g.balls = [ball]
    g._update_balls()
    assert len(g.balls) == 0


def test_update_balls_super_auto_hit() -> None:
    """SUPER mode auto-hits balls in strike zone."""
    g = _make_game()
    g.super_mode = True
    g.combo = 4
    ball = Ball(x=160.0, y=195.0, color=2, active=True)
    g.balls = [ball]
    initial_score = g.score
    g._update_balls()
    assert ball.active is False
    assert g.score > initial_score


def test_update_balls_handles_miss() -> None:
    """Ball passing through strike zone without being hit counts as miss."""
    g = _make_game()
    ball = Ball(x=160.0, y=STRIKE_ZONE_Y + STRIKE_ZONE_H + 20, color=0, active=True)
    g.balls = [ball]
    g._update_balls()
    assert ball.active is False
    assert g.wickets == 1


# --- Particle System ---


def test_spawn_hit_particles_adds_particles() -> None:
    """_spawn_hit_particles adds particles to the list."""
    g = _make_game()
    g._spawn_hit_particles(160.0, 195.0, BAT_COLORS[0])
    assert len(g.particles) >= 5
    # Check particles have correct properties
    for p in g.particles:
        assert p.life > 0
        assert isinstance(p.color, int)


def test_spawn_hit_particles_super_mode_more_particles() -> None:
    """SUPER mode spawns more hit particles."""
    g = _make_game()
    g.super_mode = True
    g._spawn_hit_particles(160.0, 195.0, BAT_COLORS[0])
    assert len(g.particles) >= 15  # 15-25 in super mode


def test_spawn_wicket_particles() -> None:
    """_spawn_wicket_particles adds red particles."""
    g = _make_game()
    g._spawn_wicket_particles(160.0, 195.0)
    assert len(g.particles) >= 20
    # Wicket particles have gravity
    for p in g.particles:
        assert p.gravity > 0


def test_update_particles_moves_and_removes() -> None:
    """_update_particles moves particles and removes dead ones."""
    g = _make_game()
    p = Particle(x=100.0, y=100.0, vx=1.0, vy=-2.0, life=1, color=8, gravity=0.0)
    g.particles = [p]
    g._update_particles()
    # life was 1, now 0, should be removed (life > 0 check)
    assert len(g.particles) == 0


def test_update_particles_gravity() -> None:
    """Particles with gravity have vy increased."""
    g = _make_game()
    p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=5, color=8, gravity=0.1)
    g.particles = [p]
    g._update_particles()
    assert len(g.particles) == 1
    assert p.vy == 0.1


# --- Full Game Flow ---


def test_multiple_hits_build_combo() -> None:
    """Multiple consecutive same-color hits build combo."""
    g = _make_game()
    g.bat_color = 0  # RED

    for _ in range(5):
        ball = Ball(x=160.0, y=195.0, color=0, active=True)
        g.balls = [ball]
        g._handle_hit(ball)

    assert g.combo == 5
    assert g.max_combo == 5
    assert g.super_mode is True  # combo >= 4
    assert g.score > 0


def test_wrong_hit_breaks_combo_chain() -> None:
    """Wrong-color hit resets the combo chain."""
    g = _make_game()
    g.bat_color = 0

    # Hits 1-3: matching
    for _ in range(3):
        ball = Ball(x=160.0, y=195.0, color=0, active=True)
        g.balls = [ball]
        g._handle_hit(ball)
    assert g.combo == 3

    # Hit 4: wrong color
    ball = Ball(x=160.0, y=195.0, color=1, active=True)  # GREEN
    g.balls = [ball]
    g._check_swing(160, 200)  # This calls _handle_wrong_hit
    assert g.combo == 0
    assert g.wickets == 1


def test_game_over_at_3_wickets() -> None:
    """Game enters GAME_OVER after 3 wickets from misses."""
    g = _make_game()

    for _ in range(3):
        ball = Ball(x=160.0, y=STRIKE_ZONE_Y + STRIKE_ZONE_H + 20, color=0, active=True)
        g.balls = [ball]
        g._update_balls()

    assert g.wickets == 3
    assert g.phase == Phase.GAME_OVER


def test_reset_after_game_over() -> None:
    """reset() restores playable state after game over."""
    g = _make_game()
    g.score = 500
    g.combo = 10
    g.wickets = 3
    g.heat = 99.0
    g.phase = Phase.GAME_OVER

    g.reset()

    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.wickets == 0
    assert g.heat == 0.0


# --- Score Formula ---


def test_score_formula() -> None:
    """Score = int(10 * (1 + combo * 0.5)) * (3 if super else 1)."""
    g = _make_game()

    # combo=0: score = int(10 * 1.0) = 10
    ball = Ball(x=160.0, y=195.0, color=0, active=True)
    g.balls = [ball]
    g.bat_color = 0
    g._handle_hit(ball)
    assert g.score == 10

    # combo=1: score = 10 + int(10 * 1.5) = 25
    ball2 = Ball(x=160.0, y=195.0, color=0, active=True)
    g.balls = [ball2]
    g._handle_hit(ball2)
    assert g.score == 25


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
