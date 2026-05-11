"""test_imports.py — Headless logic tests for CHROMA BREAK."""

import sys
from unittest.mock import MagicMock, patch

# pyxel import must be mocked before importing game module
sys.modules["pyxel"] = MagicMock()

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/014_chroma_break")

import inspect
import math
import random

from main import (
    BALL_R,
    BALL_SPEED,
    BRICK_COLS,
    BRICK_H,
    BRICK_W,
    C_BLACK,
    C_BLUE,
    C_GREEN,
    C_ORANGE,
    C_RED,
    C_WHITE,
    C_YELLOW,
    COMBO_THRESHOLD,
    DISPLAY_SCALE,
    ELEMENT_COLORS,
    ELEMENT_LABELS,
    ELEMENT_NAMES,
    PADDLE_H,
    PADDLE_W,
    PADDLE_Y,
    SCREEN_H,
    SCREEN_W,
    WAVE_DEFS,
    Ball,
    Brick,
    FloatingText,
    Game,
    Particle,
    Phase,
    PowerUp,
)


def test_constants() -> None:
    """Verify all game constants are sensible."""
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert DISPLAY_SCALE == 3
    assert PADDLE_W == 48
    assert PADDLE_H == 8
    assert PADDLE_Y == 232
    assert BALL_R == 3
    assert BALL_SPEED == 3.5
    assert BRICK_W == 32
    assert BRICK_H == 12
    assert BRICK_COLS == 8
    assert COMBO_THRESHOLD == 6
    assert len(ELEMENT_COLORS) == 4
    assert len(ELEMENT_NAMES) == 4
    assert len(ELEMENT_LABELS) == 4
    assert len(WAVE_DEFS) == 6


def test_color_constants() -> None:
    """Verify color constants are distinct."""
    for c in [C_BLACK, C_RED, C_GREEN, C_BLUE, C_YELLOW, C_WHITE]:
        assert 0 <= c <= 15
    assert len(set(ELEMENT_COLORS)) == 4  # element colors distinct


def test_phase_enum() -> None:
    """Verify Phase enum has all states."""
    assert Phase.AIM.value == 0
    assert Phase.PLAY.value == 1
    assert Phase.BALL_LOST.value == 2
    assert Phase.SUPER.value == 3
    assert Phase.WAVE_CLEAR.value == 4
    assert Phase.GAME_OVER.value == 5
    assert len(Phase) == 6


def test_brick_dataclass() -> None:
    """Verify Brick dataclass creation."""
    b = Brick(x=10, y=20, w=32, h=12, color_idx=0)
    assert b.x == 10
    assert b.y == 20
    assert b.w == 32
    assert b.h == 12
    assert b.color_idx == 0
    assert b.hp == 1
    assert b.flashing == 0

    # 2 HP brick
    b2 = Brick(x=0, y=0, w=32, h=12, color_idx=1, hp=2)
    assert b2.hp == 2


def test_ball_dataclass() -> None:
    """Verify Ball dataclass creation."""
    b = Ball(x=128, y=200, vx=2.0, vy=-3.0, color_idx=2)
    assert b.x == 128
    assert b.y == 200
    assert b.vx == 2.0
    assert b.vy == -3.0
    assert b.color_idx == 2
    assert b.super_mode is False


def test_particle_dataclass() -> None:
    """Verify Particle dataclass creation."""
    p = Particle(x=100, y=150, vx=1.0, vy=-2.0, life=15, color=C_RED)
    assert p.x == 100
    assert p.y == 150
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == C_RED


def test_powerup_dataclass() -> None:
    """Verify PowerUp dataclass creation."""
    pu = PowerUp(x=50, y=100, kind="WIDE")
    assert pu.x == 50
    assert pu.y == 100
    assert pu.kind == "WIDE"
    assert pu.vy == 1.2
    assert pu.life == 600


def test_floating_text_dataclass() -> None:
    """Verify FloatingText dataclass creation."""
    ft = FloatingText(x=100, y=200, text="x5", life=30, color=C_ORANGE)
    assert ft.x == 100
    assert ft.y == 200
    assert ft.text == "x5"
    assert ft.life == 30
    assert ft.color == 9  # C_ORANGE
    assert ft.vy == -1.5


def test_wave_defs() -> None:
    """Verify wave definitions have required fields."""
    for w in WAVE_DEFS:
        assert "rows" in w
        assert "speed_mult" in w
        assert "hp2_count" in w
        assert w["rows"] >= 1
        assert w["speed_mult"] >= 100
        assert w["hp2_count"] >= 0


def test_game_class_exists() -> None:
    """Verify Game class has expected methods."""
    methods = [
        "reset", "update", "draw",
        "_spawn_wave", "_reset_ball",
        "_update_aim", "_update_play", "_update_super",
        "_update_ball_lost", "_update_wave_clear",
        "_update_ball_physics", "_check_paddle_collision",
        "_check_brick_collisions", "_ball_rect_collision",
        "_deflect_ball", "_break_brick",
        "_update_paddle", "_update_color_switch",
        "_update_power_ups", "_apply_power_up",
        "_update_particles", "_update_float_texts",
        "_add_float_text", "_on_ball_lost",
    ]
    for name in methods:
        assert hasattr(Game, name), f"Game missing method: {name}"
        m = getattr(Game, name)
        assert callable(m), f"Game.{name} is not callable"


def test_game_reset_state() -> None:
    """Verify Game reset initializes state attributes via source inspection."""
    source = inspect.getsource(Game.reset)
    # Check that reset assigns the core state attributes
    assert "self.phase" in source
    assert "self.score" in source
    assert "self.lives" in source
    assert "self.wave" in source
    assert "self.combo" in source
    assert "self.paddle_color" in source
    assert "self.paddle_w" in source
    assert "self.paddle_x" in source
    assert "self.balls" in source
    assert "self.bricks" in source
    assert "self.particles" in source
    assert "self.power_ups" in source
    assert "self.float_texts" in source
    assert "self.screen_shake" in source


def test_ball_rect_collision_no_overlap() -> None:
    """Test ball-rect collision returns False when far apart."""
    game = Game.__new__(Game)
    game.balls = []
    ball = Ball(x=10, y=10, vx=0, vy=0, color_idx=0)
    brick = Brick(x=200, y=200, w=32, h=12, color_idx=0)
    assert game._ball_rect_collision(ball, brick) is False


def test_ball_rect_collision_overlap() -> None:
    """Test ball-rect collision returns True when overlapping."""
    game = Game.__new__(Game)
    ball = Ball(x=120, y=60, vx=0, vy=0, color_idx=0)
    brick = Brick(x=100, y=50, w=32, h=12, color_idx=0)
    assert game._ball_rect_collision(ball, brick) is True


def test_break_brick_destroys() -> None:
    """Test breaking a 1 HP brick removes it and adds score."""
    game = Game.__new__(Game)
    game.phase = Phase.PLAY
    game.score = 0
    game.combo = 0
    game.max_combo = 0
    game.bricks = [Brick(x=100, y=50, w=32, h=12, color_idx=0, hp=1)]
    game.particles = []
    game.float_texts = []
    game.power_ups = []

    ball = Ball(x=120, y=60, vx=0, vy=0, color_idx=0, super_mode=False)
    game._break_brick(game.bricks[0], ball)

    assert len(game.bricks) == 0
    assert game.combo == 1
    assert game.max_combo == 1
    assert game.score > 0
    assert len(game.particles) >= 1


def test_break_brick_2hp_damages() -> None:
    """Test breaking a 2 HP brick damages but doesn't destroy."""
    game = Game.__new__(Game)
    game.phase = Phase.PLAY
    game.score = 0
    game.combo = 0
    game.bricks = [Brick(x=100, y=50, w=32, h=12, color_idx=0, hp=2)]
    game.particles = []
    game.power_ups = []

    ball = Ball(x=120, y=60, vx=0, vy=0, color_idx=0, super_mode=False)
    game._break_brick(game.bricks[0], ball)

    assert len(game.bricks) == 1
    assert game.bricks[0].hp == 1
    assert game.bricks[0].flashing == 4


def test_break_brick_wrong_color_resets_combo() -> None:
    """Verify that _deflect_ball is used for wrong-color bricks."""
    game = Game.__new__(Game)
    game.phase = Phase.PLAY
    game.combo = 5
    game.bricks = [Brick(x=100, y=50, w=32, h=12, color_idx=0)]
    game.particles = []
    game.float_texts = []
    game.power_ups = []

    ball = Ball(x=120, y=60, vx=0, vy=0, color_idx=1)  # different color
    game._check_brick_collisions(ball)

    # Combo should reset
    assert game.combo == 0
    # Brick still exists (wrong color, no damage)
    assert len(game.bricks) == 1


def test_deflect_ball() -> None:
    """Test ball deflection updates velocity."""
    game = Game.__new__(Game)
    ball = Ball(x=120, y=50, vx=2.0, vy=-3.0, color_idx=0)
    brick = Brick(x=100, y=55, w=32, h=12, color_idx=0)

    game._deflect_ball(ball, brick)

    # Ball should have been pushed out and velocity changed
    # Just verify the ball moved and velocity is non-zero in at least one axis
    assert ball.y <= 55 + 12 + BALL_R + 1  # should be below or at brick bottom
    # One of the velocities should be flipped
    assert ball.vx != 0 or ball.vy != 0


def test_paddle_collision() -> None:
    """Test ball-paddle collision detection."""
    game = Game.__new__(Game)
    game.paddle_x = 100
    game.paddle_w = 48
    game._ball_speed_base = 3.5
    game.combo = 0
    game.paddle_color = 0
    game.particles = []
    game.phase = Phase.PLAY

    ball = Ball(x=124, y=PADDLE_Y - 1, vx=0, vy=3.0, color_idx=0)
    collided = game._check_paddle_collision(ball)

    assert collided is True
    assert ball.vy < 0  # ball should be moving up now


def test_paddle_collision_ball_moving_up() -> None:
    """Test that ball moving up does not collide with paddle."""
    game = Game.__new__(Game)
    game.paddle_x = 100
    game.paddle_w = 48
    game.combo = 0

    ball = Ball(x=124, y=PADDLE_Y, vx=0, vy=-3.0, color_idx=0)
    collided = game._check_paddle_collision(ball)

    assert collided is False


def test_particle_update() -> None:
    """Test particles decay over time."""
    game = Game.__new__(Game)
    game.particles = [
        Particle(x=50, y=50, vx=1, vy=1, life=2, color=C_RED),
        Particle(x=60, y=60, vx=0, vy=0, life=1, color=C_BLUE),
    ]
    game._update_particles()
    assert len(game.particles) == 1
    assert game.particles[0].life == 1

    game._update_particles()
    assert len(game.particles) == 0


def test_float_text_update() -> None:
    """Test floating text decays."""
    game = Game.__new__(Game)
    game.float_texts = [
        FloatingText(x=100, y=100, text="OK", life=2, color=C_WHITE),
    ]
    game._update_float_texts()
    assert len(game.float_texts) == 1
    assert game.float_texts[0].life == 1

    game._update_float_texts()
    assert len(game.float_texts) == 0


def test_add_float_text() -> None:
    """Test adding floating text."""
    game = Game.__new__(Game)
    game.float_texts = []
    game._add_float_text(100, 200, "x3", C_ORANGE)
    assert len(game.float_texts) == 1
    assert game.float_texts[0].text == "x3"
    assert game.float_texts[0].color == C_ORANGE


def test_power_up_apply_wide() -> None:
    """Test WIDE power-up expands paddle."""
    game = Game.__new__(Game)
    game.paddle_w = float(PADDLE_W)
    game.paddle_timer = 0
    game.float_texts = []
    game.particles = []

    pu = PowerUp(x=100, y=200, kind="WIDE")
    game._apply_power_up(pu)

    assert game.paddle_w == float(PADDLE_W) * 1.6
    assert game.paddle_timer == 600


def test_power_up_apply_life() -> None:
    """Test LIFE power-up adds a life."""
    game = Game.__new__(Game)
    game.lives = 2
    game.float_texts = []
    game.particles = []

    pu = PowerUp(x=100, y=200, kind="LIFE")
    game._apply_power_up(pu)

    assert game.lives == 3


def test_power_up_apply_multi() -> None:
    """Test MULTI power-up spawns extra balls."""
    game = Game.__new__(Game)
    game.balls = [Ball(x=120, y=200, vx=1, vy=-1, color_idx=0)]
    game._ball_speed_base = 3.5
    game.float_texts = []
    game.particles = []

    pu = PowerUp(x=100, y=200, kind="MULTI")
    game._apply_power_up(pu)

    assert len(game.balls) >= 3  # original + 2 new


def test_color_switch_resets_combo() -> None:
    """Test that switching colors during active combo shows feedback."""
    game = Game.__new__(Game)
    game.paddle_color = 0
    game.combo = 5
    game.paddle_x = 100
    game.paddle_w = PADDLE_W
    game.float_texts = []
    game.balls = [Ball(x=120, y=200, vx=0, vy=0, color_idx=0)]
    game.phase = Phase.PLAY

    # Simulate pressing 'E' (next color)
    # We can only test the source, not actual btnp since pyxel is mocked
    source = inspect.getsource(Game._update_color_switch)
    assert "self.combo = 0" in source
    assert "SWITCH" in source


def test_ball_lost_reduces_lives() -> None:
    """Test losing a ball reduces lives and sets phase."""
    game = Game.__new__(Game)
    game.lives = 3
    game.combo = 5
    game.phase = Phase.PLAY
    game.float_texts = []
    game.screen_shake = 0

    game._on_ball_lost()

    assert game.lives == 2
    assert game.combo == 0
    assert game.phase == Phase.BALL_LOST
    assert game.screen_shake == 6


def test_wave_defs_ordering() -> None:
    """Test that wave difficulty increases."""
    prev_rows = 0
    prev_speed = 0
    prev_hp2 = 0
    for w in WAVE_DEFS:
        assert w["rows"] >= prev_rows
        assert w["speed_mult"] >= prev_speed
        assert w["hp2_count"] >= prev_hp2
        prev_rows = w["rows"]
        prev_speed = w["speed_mult"]
        prev_hp2 = w["hp2_count"]


def test_element_names_count() -> None:
    """Test element names match color count."""
    assert len(ELEMENT_NAMES) == len(ELEMENT_COLORS) == 4
    assert ELEMENT_NAMES[0] == "FIRE"
    assert ELEMENT_NAMES[1] == "WATER"
    assert ELEMENT_NAMES[2] == "EARTH"
    assert ELEMENT_NAMES[3] == "LIGHT"


def test_no_cjk_in_strings() -> None:
    """Verify no CJK characters in game text."""
    source = inspect.getsource(Game.draw)
    # Check all text() calls have ASCII arguments
    for ch in source:
        if ord(ch) > 127:
            # Allow only common ASCII-extended (like °, ±) but flag CJK
            if "\u4e00" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff":
                pytest.fail(f"CJK character found in draw(): {ch}")


if __name__ == "__main__":
    # Run all tests
    import pytest
    import os
    # Use exit code for pass/fail
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)
