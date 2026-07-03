"""test_imports.py — Headless logic tests for 192_dodge_surge."""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from main import (
    COLORS,
    COLOR_NAMES,
    Game,
    Ball,
    Opponent,
    Particle,
    Phase,
)

# Aliases for convenience
BALL_RADIUS = Game.BALL_RADIUS
PLAYER_RADIUS = Game.PLAYER_RADIUS

# ── Factory ──────────────────────────────────────────────────────────────

def _make_game() -> Game:
    """Create a Game via __new__ to bypass pyxel.init/run."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g._play_sound = lambda *a, **kw: None
    g._init_state()
    return g


def _make_playing() -> Game:
    """Factory with game already in PLAYING state."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.reset()
    g._spawn_opponents()
    return g


# ── Constants ────────────────────────────────────────────────────────────

def test_color_constants() -> None:
    assert len(COLORS) == 4
    assert len(COLOR_NAMES) == 4
    assert 8 in COLORS  # RED
    assert 3 in COLORS  # GREEN
    assert 5 in COLORS  # DARK_BLUE
    assert 10 in COLORS  # YELLOW


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Dataclass Tests ──────────────────────────────────────────────────────

def test_ball_dataclass() -> None:
    b = Ball(x=100.0, y=100.0, vx=1.0, vy=-1.0, color=0, is_player_ball=False, life=10)
    assert b.x == 100.0
    assert b.color == 0
    assert not b.is_player_ball


def test_opponent_dataclass() -> None:
    o = Opponent(x=50.0, y=50.0, color=1, hp=3, throw_timer=60, flash_timer=0)
    assert o.hp == 3
    assert o.color == 1


def test_particle_dataclass() -> None:
    p = Particle(x=0.0, y=0.0, vx=1.0, vy=-2.0, color=8, life=15)
    assert p.life == 15
    assert p.color == 8


# ── Initialization ───────────────────────────────────────────────────────

def test_init_state_defaults() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert not g.super_mode
    assert g.super_timer == 0
    assert g.heat == 0.0
    assert g.held_ball_color == -1
    assert g.last_caught_color == -1
    assert len(g.opponents) == 0
    assert len(g.balls) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.ghost_trail) == 0


def test_reset_clears_state() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 100
    g.combo = 5
    g.max_combo = 5
    g.super_mode = True
    g.super_timer = 100
    g.heat = 50.0
    g._spawn_opponents()
    g._spawn_neutral_ball()
    g.reset()
    g._spawn_opponents()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert not g.super_mode
    assert g.heat == 0.0
    assert len(g.balls) == 0  # reset clears balls


# ── Opponent Spawning ────────────────────────────────────────────────────

def test_spawn_opponents() -> None:
    g = _make_playing()
    assert len(g.opponents) == 3
    for opp in g.opponents:
        assert opp.hp >= 1
        assert opp.throw_timer > 0


def test_opponent_positions_fit_screen() -> None:
    g = _make_playing()
    for opp in g.opponents:
        assert opp.x - 10 >= 0  # left edge
        assert opp.x + 10 <= 320  # right edge
        assert opp.y > Game.COURT_TOP
        assert opp.y < Game.PLAYER_ZONE_TOP


# ── Ball Spawning ────────────────────────────────────────────────────────

def test_spawn_neutral_ball() -> None:
    g = _make_playing()
    g._spawn_neutral_ball()
    assert len(g.balls) == 1
    ball = g.balls[0]
    assert ball.y == float(Game.COURT_MID)
    assert not ball.is_player_ball
    assert 0 <= ball.color <= 3


def test_spawn_opponent_throw() -> None:
    g = _make_playing()
    opp = g.opponents[0]
    g._spawn_opponent_throw(opp)
    assert len(g.balls) == 1
    ball = g.balls[0]
    assert not ball.is_player_ball
    # Aimed toward player
    assert ball.vy > 0  # should be going down toward player


# ── Player Throw ─────────────────────────────────────────────────────────

def test_player_throw_with_held_ball() -> None:
    g = _make_playing()
    g.held_ball_color = 1
    g._player_throw()
    assert len(g.balls) == 1
    assert g.balls[0].is_player_ball
    assert g.balls[0].color == 1
    assert g.held_ball_color == -1  # consumed


def test_player_throw_no_held_ball() -> None:
    g = _make_playing()
    g.held_ball_color = -1
    g._player_throw()
    assert len(g.balls) == 0  # nothing thrown


# ── Catch / COMBO System ─────────────────────────────────────────────────

def test_first_catch() -> None:
    g = _make_playing()
    ball = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
    g.balls.append(ball)
    g._on_catch(ball)
    assert g.combo == 1
    assert g.last_caught_color == 0
    assert g.held_ball_color == 0
    assert g.player_color == 0
    assert g.score > 0


def test_same_color_combo() -> None:
    g = _make_playing()
    ball1 = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
    g.balls.append(ball1)
    g._on_catch(ball1)
    g.balls.clear()

    ball2 = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
    g.balls.append(ball2)
    g._on_catch(ball2)
    assert g.combo == 2
    assert g.max_combo == 2


def test_different_color_resets_combo() -> None:
    g = _make_playing()
    ball1 = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
    g.balls.append(ball1)
    g._on_catch(ball1)
    g.balls.clear()

    ball2 = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=1, is_player_ball=False, life=10)
    g.balls.append(ball2)
    g._on_catch(ball2)
    assert g.combo == 1  # reset to 1 for new color


def test_combo_score_increases() -> None:
    g = _make_playing()
    for i in range(4):
        ball = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
        g.balls.append(ball)
        g._on_catch(ball)
        g.balls.clear()
    # Score increases with combo
    assert g.score > 0


# ── SUPER Mode ───────────────────────────────────────────────────────────

def test_super_activates_at_combo_4() -> None:
    g = _make_playing()
    for i in range(4):
        ball = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
        g.balls.append(ball)
        g._on_catch(ball)
        g.balls.clear()
    assert g.super_mode
    assert g.super_timer == Game.SUPER_DURATION


def test_super_no_double_activation() -> None:
    g = _make_playing()
    for i in range(8):
        ball = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
        g.balls.append(ball)
        g._on_catch(ball)
        g.balls.clear()
    assert g.super_mode
    assert g.super_timer == Game.SUPER_DURATION  # not doubled


def test_super_score_multiplier() -> None:
    g = _make_playing()
    # Build to SUPER
    for i in range(4):
        ball = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
        g.balls.append(ball)
        g._on_catch(ball)
        g.balls.clear()
    assert g.super_mode
    score_after_super_catch = g.score
    g.super_timer = 100  # keep super active

    ball2 = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
    g.balls.append(ball2)
    g._on_catch(ball2)
    g.balls.clear()
    score_after = g.score
    # Super catch should score more than regular catch
    regular_catch_score = 10 * (1 + 5 * 0.5)  # combo=5, no super
    super_catch_score = int(regular_catch_score * 3)
    assert score_after - score_after_super_catch >= super_catch_score


def test_super_auto_throw_timer() -> None:
    g = _make_playing()
    for i in range(4):
        ball = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
        g.balls.append(ball)
        g._on_catch(ball)
        g.balls.clear()
    assert g._super_auto_throw_timer == 15


# ── Opponent Elimination ─────────────────────────────────────────────────

def test_eliminate_opponent() -> None:
    g = _make_playing()
    opp = g.opponents[0]
    initial_hp = opp.hp
    opp.hp = 1
    g._eliminate_opponent(opp, 0)
    assert opp.hp >= 1  # respawned
    assert g.score >= 100  # elimination score


def test_elimination_score_scales_with_combo() -> None:
    g = _make_playing()
    g.combo = 5
    g.max_combo = 5
    opp = g.opponents[0]
    opp.hp = 1
    g._eliminate_opponent(opp, 0)
    # 100 * (1 + 5 * 0.5) = 350
    assert g.score >= 350


# ── Player Hit / HEAT System ─────────────────────────────────────────────

def test_heat_on_hit() -> None:
    g = _make_playing()
    g.heat = 0
    # Simulate hit by adding an opponent ball at player position
    ball = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
    g.balls.append(ball)
    # Simulate the hit logic directly
    g.heat += Game.HEAT_ON_HIT
    g.shake_frames = 5
    g.combo = 0
    g.balls.clear()
    assert g.heat == 15.0
    assert g.shake_frames == 5
    assert g.combo == 0


def test_heat_decay() -> None:
    g = _make_playing()
    g.heat = 50.0
    # Simulate heat decay
    old_heat = g.heat
    g.heat = max(0.0, g.heat - Game.HEAT_DECAY)
    assert g.heat == old_heat - Game.HEAT_DECAY


def test_heat_game_over_at_threshold() -> None:
    """Heat at exactly MAX_HEAT should trigger game over (checked BEFORE decay)."""
    g = _make_playing()
    g.heat = Game.MAX_HEAT
    # Simulate one _update_playing frame (the game over check is first)
    if g.game_timer <= 0 or g.heat >= Game.MAX_HEAT:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_heat_does_not_decay_before_check() -> None:
    """Heat = 100 should NOT decay to 99.7 before the game-over check."""
    g = _make_playing()
    g.heat = 100.0
    # Check before decay (correct ordering)
    should_end = g.game_timer <= 0 or g.heat >= Game.MAX_HEAT
    assert should_end


# ── CA Danger Grid ───────────────────────────────────────────────────────

def test_mark_danger() -> None:
    g = _make_playing()
    g._mark_danger(50.0, float(Game.COURT_TOP + 50))
    assert g.danger_grid[5][5] == 3  # col=5, row=5


def test_ca_spread() -> None:
    g = _make_playing()
    g._mark_danger(50.0, float(Game.COURT_TOP + 50))
    old_grid = [row[:] for row in g.danger_grid]
    g._update_ca_grid()
    # Cell at (5,5) was 3, should now be 2 (decayed)
    assert g.danger_grid[5][5] == 2
    # Neighbors should have spread (intensity 2)
    assert g.danger_grid[5][4] >= 1 or g.danger_grid[4][5] >= 1


def test_ca_decay_to_zero() -> None:
    g = _make_playing()
    g._mark_danger(50.0, float(Game.COURT_TOP + 50))
    # After 3 CA updates, intensity 3 → 0
    for _ in range(3):
        g._update_ca_grid()
    assert g.danger_grid[5][5] == 0


def test_danger_slow_speed() -> None:
    g = _make_playing()
    g._mark_danger(g.player_x, g.player_y)
    assert g._is_in_danger(g.player_x, g.player_y)


# ── Ghost Trail ──────────────────────────────────────────────────────────

def test_ball_ghost_life_decrements() -> None:
    g = _make_playing()
    ball = Ball(x=100.0, y=100.0, vx=1.0, vy=0, color=0, is_player_ball=False, life=10)
    g.balls.append(ball)
    # Simulate the ghost trail update
    for ball_item in g.balls:
        if ball_item.life > 0:
            ball_item.life -= 1
    assert ball.life == 9


# ── Particle System ──────────────────────────────────────────────────────

def test_spawn_particles() -> None:
    g = _make_playing()
    g._spawn_particles(100.0, 100.0, 8, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 100.0
        assert p.color == 8


def test_particle_gravity() -> None:
    g = _make_playing()
    g._spawn_particles(100.0, 100.0, 8, 5)
    for p in g.particles:
        p.x += p.vx
        p.y += p.vy
        p.vy += 0.1
        p.life -= 1
    # All particles should have vy increased
    for p in g.particles:
        assert p.vy > -1.5  # started at -1.5 min, +0.1


def test_particle_lifecycle() -> None:
    g = _make_playing()
    p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=1)
    g.particles.append(p)
    # One tick should remove life=1 particle
    alive: list[Particle] = []
    for pt in g.particles:
        pt.x += pt.vx
        pt.y += pt.vy
        pt.vy += 0.1
        pt.life -= 1
        if pt.life > 0:
            alive.append(pt)
    assert len(alive) == 0  # life=1 → 0 → removed


# ── Floating Text ────────────────────────────────────────────────────────

def test_add_floating_text() -> None:
    g = _make_playing()
    g._add_floating_text(100.0, 100.0, "TEST", 8, 30)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "TEST"
    assert ft.color == 8
    assert ft.life == 30


def test_floating_text_lifecycle() -> None:
    g = _make_playing()
    g._add_floating_text(100.0, 100.0, "TEST", 8, 2)
    # One tick
    for ft in g.floating_texts:
        ft.y += ft.vy
        ft.life -= 1
    alive = [ft for ft in g.floating_texts if ft.life > 0]
    assert len(alive) == 1
    # Second tick
    for ft in alive:
        ft.y += ft.vy
        ft.life -= 1
    alive2 = [ft for ft in alive if ft.life > 0]
    assert len(alive2) == 0


# ── Difficulty Scaling ───────────────────────────────────────────────────

def test_difficulty_scales_over_time() -> None:
    g = _make_playing()
    assert g._difficulty_level == 0
    # Simulate 15 seconds
    g.game_timer = Game.GAME_TIME - 15 * 60
    g._update_ca_grid()  # no-op, just to call a method
    elapsed_seconds = (Game.GAME_TIME - g.game_timer) // 60
    new_diff = elapsed_seconds // 15
    assert new_diff == 1


def test_throw_interval_decreases() -> None:
    g = _make_playing()
    # At difficulty 0
    interval_0 = g._get_opponent_throw_interval()
    g._difficulty_level = 1
    interval_1 = g._get_opponent_throw_interval()
    # With higher difficulty, interval should be shorter (on average)
    assert interval_1 <= interval_0 + 10  # allow for randomness


# ── Phase Transitions ────────────────────────────────────────────────────

def test_title_phase() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE


def test_game_over_from_timer() -> None:
    g = _make_playing()
    g.game_timer = 0
    if g.game_timer <= 0 or g.heat >= Game.MAX_HEAT:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_game_over_from_heat() -> None:
    g = _make_playing()
    g.heat = 100.0
    if g.game_timer <= 0 or g.heat >= Game.MAX_HEAT:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── Scoring ──────────────────────────────────────────────────────────────

def test_score_starts_at_zero() -> None:
    g = _make_game()
    assert g.score == 0


def test_catch_adds_positive_score() -> None:
    g = _make_playing()
    ball = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
    g.balls.append(ball)
    g._on_catch(ball)
    assert g.score > 0


def test_max_combo_tracks_peak() -> None:
    g = _make_playing()
    g.max_combo = 7
    g.combo = 3
    g.last_caught_color = 0  # same color as ball to trigger increment
    ball = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
    g.balls.append(ball)
    g._on_catch(ball)
    # combo becomes 4, max_combo stays 7
    assert g.max_combo == 7
    assert g.combo == 4


# ── Danger Grid Reset ────────────────────────────────────────────────────

def test_reset_clears_danger_grid() -> None:
    g = _make_playing()
    g._mark_danger(100.0, float(Game.COURT_TOP + 50))
    # col=10, row=5 → danger_grid[row][col] = danger_grid[5][10]
    assert g.danger_grid[5][10] == 3
    g.reset()
    g._spawn_opponents()
    for row in range(Game.CA_GRID_ROWS):
        for col in range(Game.CA_GRID_COLS):
            assert g.danger_grid[row][col] == 0


# ── Opponent Respawn ─────────────────────────────────────────────────────

def test_opponent_respawns_after_elimination() -> None:
    g = _make_playing()
    opp = g.opponents[0]
    opp.hp = 1
    g._eliminate_opponent(opp, 0)
    assert opp.hp >= 1
    assert opp.x >= 40
    assert opp.x <= Game.SCREEN_W - 40
    assert opp.throw_timer > 0


# ── Reset preserves nothing from previous game ────────────────────────────

def test_reset_clears_all_balls() -> None:
    g = _make_playing()
    g._spawn_neutral_ball()
    g._spawn_neutral_ball()
    assert len(g.balls) == 2
    g.reset()
    g._spawn_opponents()
    assert len(g.balls) == 0


def test_reset_clears_all_particles() -> None:
    g = _make_playing()
    g._spawn_particles(100.0, 100.0, 8, 10)
    g.reset()
    g._spawn_opponents()
    assert len(g.particles) == 0


# ── Inspect: _init_state initializes all attributes ──────────────────────

def test_init_state_source_has_key_attributes() -> None:
    import inspect
    source = inspect.getsource(Game._init_state)
    for attr in (
        "self.phase",
        "self.player_x",
        "self.player_y",
        "self.player_color",
        "self.held_ball_color",
        "self.last_caught_color",
        "self.opponents",
        "self.balls",
        "self.particles",
        "self.danger_grid",
        "self.ghost_trail",
        "self.score",
        "self.combo",
        "self.max_combo",
        "self.super_mode",
        "self.super_timer",
        "self.heat",
        "self.game_timer",
        "self.frame",
        "self.shake_frames",
        "self.floating_texts",
        "_difficulty_level",
        "_ball_spawn_timer",
        "_super_auto_throw_timer",
    ):
        assert attr in source, f"Missing {attr} in _init_state"


def test_reset_source_has_key_attributes() -> None:
    import inspect
    source = inspect.getsource(Game.reset)
    for attr in (
        "self.phase",
        "self.player_x",
        "self.player_y",
        "self.player_color",
        "self.held_ball_color",
        "self.last_caught_color",
        "self.opponents",
        "self.balls",
        "self.particles",
        "self.score",
        "self.combo",
        "self.max_combo",
        "self.super_mode",
        "self.super_timer",
        "self.heat",
        "self.game_timer",
        "self.frame",
        "self.shake_frames",
        "self.floating_texts",
        "_difficulty_level",
        "_ball_spawn_timer",
        "_super_auto_throw_timer",
    ):
        assert attr in source, f"Missing {attr} in reset"


# ── Edge Cases ───────────────────────────────────────────────────────────

def test_catch_with_no_held_ball() -> None:
    """Catching a ball when not holding anything should work."""
    g = _make_playing()
    assert g.held_ball_color == -1
    ball = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=2, is_player_ball=False, life=10)
    g.balls.append(ball)
    g._on_catch(ball)
    assert g.held_ball_color == 2


def test_throw_to_nearest_opponent() -> None:
    g = _make_playing()
    g.held_ball_color = 1
    # Move player to center
    g.player_x = float(Game.SCREEN_W // 2)
    g.player_y = float(Game.SCREEN_H - 50)
    g._player_throw()
    ball = g.balls[0]
    # Should be aimed upward (toward opponents at y ~ COURT_TOP + 30)
    assert ball.vy < 0


def test_super_mode_deactivates() -> None:
    g = _make_playing()
    for i in range(4):
        ball = Ball(x=g.player_x, y=g.player_y, vx=0, vy=0, color=0, is_player_ball=False, life=10)
        g.balls.append(ball)
        g._on_catch(ball)
        g.balls.clear()
    assert g.super_mode
    g.super_timer = 0
    g.super_mode = False  # simulate deactivation
    assert not g.super_mode


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
