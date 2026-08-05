"""test_imports.py — Headless logic tests for DODGE CHAIN."""
import random
import sys

sys.path.insert(0, "prototypes/283_dodge_chain")
from main import (
    Ball,
    GAME_DURATION,
    Game,
    Opponent,
    Particle,
    Phase,
    SCREEN_W,
    SUPER_THRESHOLD,
    SUPER_DURATION,
    COLOR_VALS,
    HEAT_HIT,
    HEAT_MAX,
    HEAT_WRONG_COLOR,
    PLAYER_SPEED,
    OPPONENT_COUNT,
    THROW_COOLDOWN,
    FloatingText,
)


def _make_game():
    """Create a Game instance bypassing pyxel.init for headless testing."""
    g = Game.__new__(Game)
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.game_timer = 0
    g.super_mode = False
    g.super_timer = 0
    g.player_x = 160.0
    g.player_y = 200.0
    g.player_color = 0
    g.balls = []
    g.opponents = []
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g._rng = random.Random(42)
    g._throw_cooldown = 0
    g._difficulty_timer = 0
    g.phase = Phase.PLAYING
    g.reset()
    return g


class TestBasicImports:
    def test_constants(self):
        assert SCREEN_W == 320
        assert len(COLOR_VALS) == 4
        assert SUPER_THRESHOLD == 4
        assert HEAT_MAX == 100.0

    def test_phase_enum(self):
        assert Phase.TITLE in Phase
        assert Phase.PLAYING in Phase
        assert Phase.GAME_OVER in Phase

    def test_dataclasses(self):
        b = Ball(x=100, y=200, vx=2, vy=-1, color=0)
        assert b.x == 100
        assert b.color == 0
        assert b.from_player is True
        assert b.active is True

        o = Opponent(x=160, y=45, color=2)
        assert o.color == 2
        assert o.hit is False

        p = Particle(x=50, y=60, vx=1, vy=1, color=3, life=10)
        assert p.life == 10


class TestGameInit:
    def test_make_game(self):
        g = _make_game()
        # reset() sets phase to TITLE; update() transitions to PLAYING
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert len(g.opponents) == OPPONENT_COUNT

    def test_opponents_spawned(self):
        g = _make_game()
        assert all(0 <= opp.color <= 3 for opp in g.opponents)
        # All opponents should be in AI zone
        for opp in g.opponents:
            assert 20 <= opp.x <= 300
            assert 20 <= opp.y <= 75

    def test_reset_clears_state(self):
        g = _make_game()
        g.score = 500
        g.combo = 3
        g.heat = 40.0
        g.balls = [Ball(0, 0, 0, 0, 0)]
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert len(g.balls) == 0  # reset() doesn't spawn balls (done in update transition)


class TestThrowBall:
    def test_throw_basic(self):
        g = _make_game()
        initial_color = g.player_color
        g._throw_ball(200, 100)
        assert len(g.balls) == 1  # only the thrown ball (reset doesn't spawn)
        new_ball = g.balls[-1]
        assert new_ball.from_player is True
        assert new_ball.color == initial_color
        # Velocity should be toward target
        assert new_ball.vx > 0  # target to the right
        assert new_ball.vy < 0  # target above

    def test_throw_cycles_color(self):
        g = _make_game()
        c0 = g.player_color
        g._throw_ball(200, 100)
        c1 = g.player_color
        assert c1 == (c0 + 1) % 4

    def test_throw_cooldown(self):
        g = _make_game()
        g._throw_ball(200, 100)
        assert g._throw_cooldown == THROW_COOLDOWN


class TestCatchBall:
    def test_catch_ai_ball(self):
        g = _make_game()
        g.heat = 20.0  # pre-heat to see the cooling effect
        ai_ball = Ball(
            x=g.player_x + 5, y=g.player_y + 3,
            vx=0, vy=0, color=1, from_player=False
        )
        g.balls.append(ai_ball)
        g._catch_ball(ai_ball)
        assert ai_ball.active is False
        assert g.score == 50
        assert g.heat < 20.0  # HEAT_COOL_CATCH = -10, but clamped at 0 by max()

    def test_catch_spawns_particles(self):
        g = _make_game()
        ai_ball = Ball(
            x=g.player_x + 5, y=g.player_y,
            vx=0, vy=0, color=1, from_player=False
        )
        g.balls.append(ai_ball)
        g._catch_ball(ai_ball)
        assert len(g.particles) == 6


class TestPlayerHit:
    def test_player_hit_adds_heat(self):
        g = _make_game()
        g._player_hit()
        assert g.heat == HEAT_HIT

    def test_player_hit_resets_combo(self):
        g = _make_game()
        g.combo = 5
        g._player_hit()
        assert g.combo == 0

    def test_player_hit_shakes(self):
        g = _make_game()
        g._player_hit()
        assert g.shake_frames > 0

    def test_player_hit_game_over(self):
        g = _make_game()
        g.heat = HEAT_MAX - 1
        g._player_hit()
        assert g.phase == Phase.GAME_OVER


class TestOpponentHit:
    def test_match_hit(self):
        g = _make_game()
        opp = g.opponents[0]
        ball_color = opp.color  # match
        ball = Ball(x=opp.x, y=opp.y, vx=0, vy=0, color=ball_color, from_player=True)
        g._opponent_hit(opp, ball)
        assert opp.hit is True
        assert g.combo == 1
        assert g.score > 0

    def test_match_hit_cools_heat(self):
        g = _make_game()
        g.heat = 30.0
        opp = g.opponents[0]
        ball = Ball(x=opp.x, y=opp.y, vx=0, vy=0, color=opp.color, from_player=True)
        g._opponent_hit(opp, ball)
        assert g.heat < 30.0  # HEAT_COOL_HIT

    def test_wrong_color_hit_resets_combo(self):
        g = _make_game()
        g.combo = 3
        opp = g.opponents[0]
        wrong_color = (opp.color + 1) % 4
        ball = Ball(x=opp.x, y=opp.y, vx=0, vy=0, color=wrong_color, from_player=True)
        g._opponent_hit(opp, ball)
        assert g.combo == 0
        assert opp.hit is True  # still hits

    def test_wrong_color_adds_heat(self):
        g = _make_game()
        opp = g.opponents[0]
        wrong_color = (opp.color + 1) % 4
        ball = Ball(x=opp.x, y=opp.y, vx=0, vy=0, color=wrong_color, from_player=True)
        g._opponent_hit(opp, ball)
        assert g.heat == HEAT_WRONG_COLOR

    def test_activate_super_mode(self):
        g = _make_game()
        g.combo = SUPER_THRESHOLD - 1  # combo = 3
        opp = g.opponents[0]
        ball = Ball(x=opp.x, y=opp.y, vx=0, vy=0, color=opp.color, from_player=True)
        g._opponent_hit(opp, ball)
        assert g.combo == SUPER_THRESHOLD
        assert g.super_mode is True
        assert g.super_timer == SUPER_DURATION

    def test_super_mode_all_hits_match(self):
        g = _make_game()
        g.super_mode = True
        g.super_timer = 100
        g.combo = 5
        opp = g.opponents[0]
        wrong_color = (opp.color + 1) % 4
        ball = Ball(x=opp.x, y=opp.y, vx=0, vy=0, color=wrong_color, from_player=True)
        g._opponent_hit(opp, ball)
        # In super mode, combo increases even with wrong color
        assert g.combo == 6


class TestHandleClick:
    def test_click_catches_close_ai_ball(self):
        g = _make_game()
        ai_ball = Ball(
            x=g.player_x + 3, y=g.player_y + 2,
            vx=0, vy=0, color=1, from_player=False
        )
        g.balls.append(ai_ball)
        g._handle_click(g.player_x, g.player_y)
        # Ball should be caught (inactive)
        assert ai_ball.active is False

    def test_click_throws_when_no_catch(self):
        g = _make_game()
        initial_ball_count = len(g.balls)
        g._handle_click(200, 100)
        assert len(g.balls) == initial_ball_count + 1


class TestUpdateBalls:
    def test_ball_movement(self):
        g = _make_game()
        g.balls = [Ball(x=160, y=100, vx=3, vy=2, color=0, from_player=True)]
        g._update_balls()
        assert g.balls[0].x == 163
        assert g.balls[0].y == 102

    def test_off_screen_ball_removed(self):
        g = _make_game()
        g.balls = [Ball(x=-20, y=120, vx=-5, vy=0, color=0, from_player=True)]
        g._update_balls()
        assert len(g.balls) == 0

    def test_ai_ball_hits_player(self):
        g = _make_game()
        g.balls = [Ball(
            x=g.player_x, y=g.player_y,
            vx=0, vy=0, color=0, from_player=False
        )]
        initial_heat = g.heat
        g._update_balls()
        assert g.heat > initial_heat
        assert g.combo == 0  # reset on hit

    def test_player_ball_hits_opponent(self):
        g = _make_game()
        opp = g.opponents[0]
        g.balls = [Ball(
            x=opp.x, y=opp.y,
            vx=0, vy=0, color=opp.color, from_player=True
        )]
        g._update_balls()
        assert opp.hit is True


class TestUpdateOpponents:
    def test_opponent_throws(self):
        g = _make_game()
        # Set opponent throw_timer to 1 so they throw
        g.opponents[0].throw_timer = 1
        initial_balls = len(g.balls)
        g._update_opponents()
        # Opponent should have thrown a ball
        assert len(g.balls) > initial_balls

    def test_hit_opponent_respawns(self):
        g = _make_game()
        opp = g.opponents[0]
        opp.hit = True
        opp.respawn_timer = 2
        g._update_opponents()
        assert opp.respawn_timer == 1
        g._update_opponents()
        assert opp.hit is False  # respawned


class TestParticleSystem:
    def test_particles_move_and_decay(self):
        g = _make_game()
        g.particles = [Particle(x=100, y=100, vx=1, vy=1, color=0, life=3)]
        g._update_particles()
        assert g.particles[0].life == 2
        assert g.particles[0].x != 100

    def test_particles_removed_when_dead(self):
        g = _make_game()
        g.particles = [Particle(x=100, y=100, vx=0, vy=0, color=0, life=1)]
        g._update_particles()
        assert len(g.particles) == 0


class TestFloatingText:
    def test_floating_text_moves_and_decays(self):
        g = _make_game()
        g.floating_texts = [FloatingText("TEST", 100, 100, 5, 7)]
        g._update_floating_texts()
        assert g.floating_texts[0].life == 4
        assert g.floating_texts[0].y < 100  # floats up

    def test_floating_text_removed(self):
        g = _make_game()
        g.floating_texts = [FloatingText("TEST", 100, 100, 1, 7)]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


class TestTickTimers:
    def test_tick_increments_timer(self):
        g = _make_game()
        g._tick_timers()
        assert g.game_timer == 1

    def test_tick_decays_heat(self):
        g = _make_game()
        g.heat = 10.0
        g._tick_timers()
        assert 0 <= g.heat < 10.0

    def test_super_timer_decrements(self):
        g = _make_game()
        g.super_mode = True
        g.super_timer = 50
        g.combo = 5
        g._tick_timers()
        assert g.super_timer == 49

    def test_super_expires(self):
        g = _make_game()
        g.super_mode = True
        g.super_timer = 1
        g.combo = 5
        g._tick_timers()
        assert g.super_mode is False
        assert g.combo == 0

    def test_game_duration_end(self):
        g = _make_game()
        g.game_timer = GAME_DURATION - 1
        g._tick_timers()
        assert g.phase == Phase.GAME_OVER


class TestPlayerInput:
    def test_move_right(self):
        g = _make_game()
        g.player_x = 100
        g._update_player_input(False, True, False, False)
        assert g.player_x == 100 + PLAYER_SPEED

    def test_move_left(self):
        g = _make_game()
        g.player_x = 200
        g._update_player_input(True, False, False, False)
        assert g.player_x == 200 - PLAYER_SPEED

    def test_clamp_right(self):
        g = _make_game()
        g.player_x = 300
        g._update_player_input(False, True, False, False)
        assert g.player_x == 300

    def test_clamp_left(self):
        g = _make_game()
        g.player_x = 20
        g._update_player_input(True, False, False, False)
        assert g.player_x == 20

    def test_clamp_top(self):
        g = _make_game()
        g.player_y = 165
        g._update_player_input(False, False, True, False)
        assert g.player_y == 165

    def test_clamp_bottom(self):
        g = _make_game()
        g.player_y = 220
        g._update_player_input(False, False, False, True)
        assert g.player_y == 220


class TestAiThrow:
    def test_ai_throws_toward_player(self):
        g = _make_game()
        g.player_x = 160
        g.player_y = 200
        opp = g.opponents[0]
        opp.x = 160
        opp.y = 45
        initial_count = len(g.balls)
        g._ai_throw(opp)
        assert len(g.balls) == initial_count + 1
        ball = g.balls[-1]
        assert ball.from_player is False
        assert ball.vy > 0  # toward player (below)

    def test_super_mode_scoring(self):
        g = _make_game()
        g.super_mode = True
        g.combo = 4
        g.score = 0
        opp = g.opponents[0]
        ball = Ball(x=opp.x, y=opp.y, vx=0, vy=0, color=opp.color, from_player=True)
        g._opponent_hit(opp, ball)
        # Super mode: 3x base * combo
        assert g.score > 0


class TestFinalizeGame:
    def test_updates_best_score(self):
        g = _make_game()
        g.score = 500
        g._finalize_game()
        assert g.best_score == 500

    def test_best_score_persists(self):
        g = _make_game()
        g.score = 300
        g._finalize_game()
        g.score = 200
        g._finalize_game()
        assert g.best_score == 300


class TestSpawnParticles:
    def test_spawn_count(self):
        g = _make_game()
        g._spawn_particles(100, 100, 0, 5)
        assert len(g.particles) == 5

    def test_spawn_positions(self):
        g = _make_game()
        g._spawn_particles(100, 100, 0, 3)
        for p in g.particles:
            assert p.life > 0
            assert p.color == 0


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True, text=True, cwd="/home/unknown22/repos/game-prototypes"
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    sys.exit(result.returncode)
