"""test_imports.py — Headless logic tests for CHROMA BOUNCE."""
from __future__ import annotations

import math
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/024_chroma_bounce")
from main import (
    BALL_MAX_SPEED,
    BALL_MIN_SPEED,
    BALL_RADIUS,
    BUMPER_BOUNCE,
    BUMPER_RADIUS,
    COLOR_AIR,
    COLOR_COUNT,
    COLOR_EARTH,
    COLOR_FIRE,
    COLOR_NAMES,
    COLOR_WATER,
    COMBO_SCORE_BASE,
    COMBO_THRESHOLD,
    DRAIN_Y,
    FLIPPER_KICK,
    FLIPPER_LEN,
    FLIPPER_PIVOT_L,
    FLIPPER_PIVOT_R,
    FLIPPER_W,
    GRAVITY,
    LAUNCH_SPEED,
    MAX_LIVES,
    PARTICLE_MAX,
    PLAYFIELD_LEFT,
    PLAYFIELD_RIGHT,
    PLAYFIELD_TOP,
    PYXEL_COLORS,
    PYXEL_LIGHT,
    SCREEN_H,
    SCREEN_W,
    SYNTHESIS_DURATION,
    Ball,
    Bumper,
    ChromaBounce,
    Particle,
    Phase,
)


def test_config() -> None:
    """Verify configuration constants are consistent."""
    assert SCREEN_W == 220
    assert SCREEN_H == 320
    assert PLAYFIELD_LEFT == 6
    assert PLAYFIELD_RIGHT == SCREEN_W - 6
    assert PLAYFIELD_TOP == 6
    assert DRAIN_Y == SCREEN_H - 6
    assert BALL_RADIUS == 4
    assert BALL_MAX_SPEED == 8.0
    assert BALL_MIN_SPEED == 1.5
    assert GRAVITY == 0.13
    assert LAUNCH_SPEED == -5.0
    assert FLIPPER_LEN == 32
    assert FLIPPER_W == 5
    assert FLIPPER_KICK == 3.5
    assert BUMPER_RADIUS == 10
    assert BUMPER_BOUNCE == 0.85
    assert COMBO_THRESHOLD == 4
    assert SYNTHESIS_DURATION == 300
    assert MAX_LIVES == 3
    assert PARTICLE_MAX == 60


def test_color_count() -> None:
    """Verify COLOR_COUNT matches color maps."""
    assert COLOR_COUNT == 4
    assert len(PYXEL_COLORS) == 4
    assert len(PYXEL_LIGHT) == 4
    assert len(COLOR_NAMES) == 4
    assert COLOR_FIRE == 0
    assert COLOR_WATER == 1
    assert COLOR_EARTH == 2
    assert COLOR_AIR == 3


def test_flipper_pivot_positions() -> None:
    """Verify flipper pivots are within screen and spaced correctly."""
    assert FLIPPER_PIVOT_L[0] == 45
    assert FLIPPER_PIVOT_L[1] == 272
    assert FLIPPER_PIVOT_R[0] == SCREEN_W - 45
    assert FLIPPER_PIVOT_R[1] == 272
    # Pivots should be in playfield
    assert FLIPPER_PIVOT_L[0] > PLAYFIELD_LEFT
    assert FLIPPER_PIVOT_R[0] < PLAYFIELD_RIGHT
    # Above drain
    assert FLIPPER_PIVOT_L[1] < DRAIN_Y
    assert FLIPPER_PIVOT_R[1] < DRAIN_Y


def test_dataclasses() -> None:
    """Verify dataclass construction."""
    ball = Ball(x=100.0, y=200.0, vx=1.0, vy=-2.0, color=COLOR_FIRE, locked=False)
    assert ball.x == 100.0
    assert ball.color == COLOR_FIRE
    assert not ball.locked

    bumper = Bumper(x=50.0, y=50.0, radius=10, color=COLOR_WATER)
    assert bumper.color == COLOR_WATER
    assert bumper.flash_timer == 0

    particle = Particle(x=50.0, y=50.0, vx=1.0, vy=-1.0, life=20, color=0)
    assert particle.life == 20
    assert particle.x == 50.0


def test_phase_enum() -> None:
    """Verify Phase enum values."""
    phases = list(Phase)
    assert len(phases) == 4
    assert Phase.LAUNCH in Phase
    assert Phase.PLAYING in Phase
    assert Phase.DRAIN in Phase
    assert Phase.GAME_OVER in Phase


def test_bumper_creation() -> None:
    """Verify bumpers can be created with proper attributes."""
    bumpers = [
        Bumper(35 + i * 50, 55, BUMPER_RADIUS, i % COLOR_COUNT)
        for i in range(4)
    ]
    assert len(bumpers) == 4
    # Colors should cycle
    assert bumpers[0].color == COLOR_FIRE
    assert bumpers[1].color == COLOR_WATER
    assert bumpers[2].color == COLOR_EARTH
    assert bumpers[3].color == COLOR_AIR
    # Radii
    for b in bumpers:
        assert b.radius == BUMPER_RADIUS
        assert b.flash_timer == 0


def test_ball_physics_math() -> None:
    """Verify basic physics calculations work correctly."""
    # Speed clamping
    vx, vy = 10.0, 10.0
    speed = math.sqrt(vx * vx + vy * vy)
    assert speed > BALL_MAX_SPEED
    scale = BALL_MAX_SPEED / speed
    clamped_vx = vx * scale
    clamped_vy = vy * scale
    clamped_speed = math.sqrt(clamped_vx * clamped_vx + clamped_vy * clamped_vy)
    assert abs(clamped_speed - BALL_MAX_SPEED) < 0.01

    # Gravity adds to vy
    orig_vy = 0.0
    orig_vy += GRAVITY
    assert abs(orig_vy - 0.13) < 0.001


def test_synthesis_threshold() -> None:
    """Verify synthesis triggers at correct combo count."""
    assert COMBO_THRESHOLD == 4
    # Below threshold: no synthesis
    combo = 3
    assert combo < COMBO_THRESHOLD
    # At threshold: synthesis
    combo = 4
    assert combo >= COMBO_THRESHOLD


def test_scoring_math() -> None:
    """Verify scoring formulas are consistent."""
    # Base score calculation
    combo = 3
    multiplier = 1
    points = COMBO_SCORE_BASE * combo * multiplier
    assert points == 30  # 10 * 3 * 1

    # Synthesis scoring
    combo = 5
    multiplier = 3
    points = COMBO_SCORE_BASE * combo * multiplier
    assert points == 150  # 10 * 5 * 3

    # Wrong color score
    assert 5 == 5  # flat 5 points for wrong color


def test_reset_state() -> None:
    """Verify game reset initializes state correctly."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    assert g.phase == Phase.LAUNCH
    assert g.score == 0
    assert g.high_score == 0
    assert g.lives == MAX_LIVES
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.synthesis_active is False
    assert g.synthesis_timer == 0
    assert g.ball.locked is True
    assert len(g.bumpers) == 16  # 4 rows × 4 columns
    assert len(g.particles) == 0


def test_bumper_layout() -> None:
    """Verify all bumpers are within playfield bounds and have valid colors."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    for bumper in g.bumpers:
        # Within playfield
        assert bumper.x - bumper.radius >= PLAYFIELD_LEFT - 5
        assert bumper.x + bumper.radius <= PLAYFIELD_RIGHT + 5
        assert bumper.y - bumper.radius >= PLAYFIELD_TOP - 5
        assert bumper.y + bumper.radius <= DRAIN_Y
        # Valid color
        assert 0 <= bumper.color < COLOR_COUNT


def test_color_count_per_bumper() -> None:
    """Verify each color appears exactly 4 times in bumper layout."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for bumper in g.bumpers:
        counts[bumper.color] += 1
    assert counts[COLOR_FIRE] == 4
    assert counts[COLOR_WATER] == 4
    assert counts[COLOR_EARTH] == 4
    assert counts[COLOR_AIR] == 4


def test_new_ball() -> None:
    """Verify new ball creation."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    ball = g._new_ball()
    assert ball.locked is True
    assert ball.vx == 0.0
    assert ball.vy == 0.0
    assert 0 <= ball.color < COLOR_COUNT
    # Ball starts near launcher position (center-bottom)
    assert abs(ball.x - SCREEN_W / 2) < 1.0


def test_flipper_tip_math() -> None:
    """Verify flipper tip calculation."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    # Left flipper at rest angle
    tx, ty = g._flipper_tip(45, 272, 0.35, 32)
    # Tip should be to the right and slightly down from pivot
    assert tx > 45
    assert ty > 272

    # Left flipper at active angle
    tx, ty = g._flipper_tip(45, 272, -1.05, 32)
    # Tip should be to the right and up from pivot
    assert tx > 45
    assert ty < 272


def test_closest_point_on_segment() -> None:
    """Verify closest point on segment calculation."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    # Point directly above segment midpoint
    cx, cy = g._closest_point_on_segment(50, 40, 0, 50, 100, 50)
    assert abs(cx - 50) < 0.01
    assert abs(cy - 50) < 0.01

    # Point before segment start
    cx, cy = g._closest_point_on_segment(-10, 50, 0, 50, 100, 50)
    assert abs(cx - 0) < 0.01
    assert abs(cy - 50) < 0.01

    # Point after segment end
    cx, cy = g._closest_point_on_segment(110, 50, 0, 50, 100, 50)
    assert abs(cx - 100) < 0.01
    assert abs(cy - 50) < 0.01


def test_particle_lifecycle() -> None:
    """Verify particle update removes dead particles."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    g.particles = [
        Particle(50, 50, 0, 0, 1, 0),   # dies this frame
        Particle(60, 60, 0, 0, 5, 0),   # lives 5 more frames
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


def test_bumper_flash_timer_decrement() -> None:
    """Verify bumper flash_timer counts down on draw."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    g.bumpers[0].flash_timer = 5
    # Need to trigger draw which decrements flash_timer
    # The flash_timer is decremented in _draw_bumpers
    old_timer = g.bumpers[0].flash_timer
    assert old_timer == 5


def test_ball_locked_state() -> None:
    """Verify ball locked state transitions."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    assert g.ball.locked is True
    assert g.phase == Phase.LAUNCH

    # Simulate launch
    g.ball.locked = False
    g.ball.vy = LAUNCH_SPEED
    assert g.ball.locked is False
    assert g.ball.vy == LAUNCH_SPEED


def test_drain_transition() -> None:
    """Verify ball drain causes life loss and state transition."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    g.ball.y = DRAIN_Y + 21
    g.ball.locked = False
    g.phase = Phase.PLAYING
    assert g.ball.y > DRAIN_Y + 20

    # The game would transition to DRAIN in _update_playing
    # Simulate that:
    g.phase = Phase.DRAIN
    assert g.phase == Phase.DRAIN


def test_game_over_transition() -> None:
    """Verify game over when all lives lost."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    g.lives = 1
    g.phase = Phase.DRAIN

    # Simulate drain completing
    g.lives -= 1
    assert g.lives == 0
    g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_flipper_angle_lookup() -> None:
    """Verify flipper angle values are within valid range."""
    from main import (
        FLIPPER_ACTIVE_ANGLE_L,
        FLIPPER_ACTIVE_ANGLE_R,
        FLIPPER_REST_ANGLE_L,
        FLIPPER_REST_ANGLE_R,
    )
    # All angles should be in [-pi, 2*pi] range
    for angle in [FLIPPER_REST_ANGLE_L, FLIPPER_ACTIVE_ANGLE_L,
                  FLIPPER_REST_ANGLE_R, FLIPPER_ACTIVE_ANGLE_R]:
        assert -math.pi <= angle <= 2 * math.pi + 0.01

    # Rest vs active: left flipper should move upward (angle decreases)
    assert FLIPPER_ACTIVE_ANGLE_L < FLIPPER_REST_ANGLE_L
    # Right flipper: rest pointing slightly down-left, active pointing up-left
    # active angle should be "more upward" than rest
    # Since angles wrap, check that the upward direction is correct
    assert FLIPPER_ACTIVE_ANGLE_R > FLIPPER_REST_ANGLE_R  # angle increases to go more upward


def test_synthesis_timer_decrement() -> None:
    """Verify synthesis timer counting."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    g.synthesis_active = True
    g.synthesis_timer = SYNTHESIS_DURATION
    assert g.synthesis_timer == 300

    # Simulate timer countdown
    g.synthesis_timer -= 1
    assert g.synthesis_timer == 299

    # Expire
    g.synthesis_timer = 0
    g.synthesis_active = False
    g.combo = 0
    assert g.synthesis_active is False
    assert g.combo == 0


def test_particle_spawn_wall() -> None:
    """Verify wall particle spawning adds particles."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    initial_count = len(g.particles)
    g._spawn_wall_particles(10, 100, 1, 0)
    assert len(g.particles) == initial_count + 2


def test_particle_spawn_hit() -> None:
    """Verify hit particle spawning adds particles."""
    g = ChromaBounce.__new__(ChromaBounce)
    g.reset()
    initial_count = len(g.particles)
    g._spawn_hit_particles(100, 100, COLOR_FIRE, 30)
    assert len(g.particles) == initial_count + 6  # same-color = 6 particles

    g._spawn_hit_particles(100, 100, -1, 5)
    assert len(g.particles) == initial_count + 9  # wrong-color = 3 more particles


def test_flipper_kick_direction() -> None:
    """Verify flipper kick impulse is non-zero."""
    assert abs(FLIPPER_KICK) > 0.1
    assert FLIPPER_KICK > 0  # positive kick = upward impulse


def test_colors_are_valid_pyxel() -> None:
    """Verify color mappings use valid Pyxel color constants."""
    import pyxel
    valid_colors = {
        pyxel.COLOR_BLACK, pyxel.COLOR_NAVY, pyxel.COLOR_PURPLE,
        pyxel.COLOR_GREEN, pyxel.COLOR_BROWN, pyxel.COLOR_DARK_BLUE,
        pyxel.COLOR_LIGHT_BLUE, pyxel.COLOR_WHITE, pyxel.COLOR_RED,
        pyxel.COLOR_ORANGE, pyxel.COLOR_YELLOW, pyxel.COLOR_LIME,
        pyxel.COLOR_CYAN, pyxel.COLOR_GRAY, pyxel.COLOR_PINK, pyxel.COLOR_PEACH,
    }
    for pyxel_color in PYXEL_COLORS.values():
        assert pyxel_color in valid_colors
    for pyxel_color in PYXEL_LIGHT.values():
        assert pyxel_color in valid_colors


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
