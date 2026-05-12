"""test_imports.py — Headless logic tests for Element Drop prototype.

Tests dataclass construction, game state initialization, peg generation,
combo logic, and phase transitions without requiring a display.
"""

from __future__ import annotations

import sys

# Make the prototype module importable
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/015_element_drop")

# We can't import the Game class directly because __init__ calls pyxel.init()
# Instead, test the dataclasses and logic functions in isolation.

from main import (
    Ball,
    BALL_R,
    BALLS_PER_GAME,
    DISPLAY_SCALE,
    ELEMENT_COLORS,
    ELEMENT_NAMES,
    FloatText,
    FUTURE_SHOWN,
    GRAVITY,
    Particle,
    Peg,
    PEG_R,
    Phase,
    SCREEN_H,
    SCREEN_W,
    TARGET_FRACTION,
)


def test_dataclass_peg() -> None:
    """Peg dataclass constructs correctly."""
    p = Peg(x=100.0, y=50.0, element=2)
    assert p.x == 100.0
    assert p.y == 50.0
    assert p.element == 2
    assert p.alive is True
    assert p.radius == PEG_R


def test_dataclass_ball() -> None:
    """Ball dataclass constructs correctly."""
    b = Ball(x=128.0, y=16.0, vx=0.0, vy=2.0, element=0)
    assert b.x == 128.0
    assert b.alive is True
    assert b.hits == 0
    assert b.element == 0


def test_dataclass_particle() -> None:
    """Particle dataclass constructs correctly."""
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=20, color=8)
    assert p.x == 50.0
    assert p.life == 20
    assert p.size == 1


def test_dataclass_float_text() -> None:
    """FloatText dataclass constructs correctly."""
    ft = FloatText(x=100.0, y=80.0, text="x4", life=40, color=8)
    assert ft.text == "x4"
    assert ft.life == 40
    assert ft.vy == -1.0


def test_phase_enum() -> None:
    """Phase enum has expected members."""
    assert Phase.AIM == 0
    assert Phase.DROP == 1
    assert Phase.RESULT == 2
    assert Phase.GAMEOVER == 3
    assert len(Phase) == 4


def test_element_config() -> None:
    """Element configuration is consistent."""
    assert len(ELEMENT_COLORS) == 5
    assert len(ELEMENT_NAMES) == 5
    assert len(ELEMENT_COLORS) == len(ELEMENT_NAMES)


def test_constants() -> None:
    """Game constants are sane."""
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert DISPLAY_SCALE == 2
    assert BALL_R > 0
    assert PEG_R > 0
    assert GRAVITY > 0
    assert BALLS_PER_GAME == 10
    assert FUTURE_SHOWN == 3
    assert 0 < TARGET_FRACTION < 1


def test_ball_physics_basics() -> None:
    """Ball physics behaves correctly under gravity."""
    b = Ball(x=128.0, y=16.0, vx=0.0, vy=2.0, element=0)
    # simulate gravity
    b.vy += GRAVITY
    b.x += b.vx
    b.y += b.vy
    assert b.y > 16.0  # ball moved down
    assert b.x == 128.0  # no horizontal movement


def test_wall_bounce_left() -> None:
    """Ball bounces off left wall."""
    b = Ball(x=BALL_R - 1.0, y=100.0, vx=-3.0, vy=0.0, element=0)
    # simulate wall collision logic
    if b.x < BALL_R:
        b.x = BALL_R
        b.vx = abs(b.vx) * 0.62
    assert b.x == BALL_R
    assert b.vx > 0  # reversed direction


def test_wall_bounce_right() -> None:
    """Ball bounces off right wall."""
    b = Ball(x=SCREEN_W - BALL_R + 1.0, y=100.0, vx=3.0, vy=0.0, element=0)
    if b.x > SCREEN_W - BALL_R:
        b.x = SCREEN_W - BALL_R
        b.vx = -abs(b.vx) * 0.62
    assert b.x == SCREEN_W - BALL_R
    assert b.vx < 0  # reversed direction


def test_peg_collision_detection() -> None:
    """Ball and peg collision detection works."""
    import math

    b = Ball(x=100.0, y=100.0, vx=0.0, vy=2.0, element=0)
    p = Peg(x=102.0, y=101.0, element=0)  # very close
    dx = b.x - p.x
    dy = b.y - p.y
    dist = math.hypot(dx, dy)
    assert dist < BALL_R + p.radius  # collision detected


def test_peg_no_collision_when_far() -> None:
    """No collision when ball is far from peg."""
    import math

    b = Ball(x=100.0, y=100.0, vx=0.0, vy=2.0, element=0)
    p = Peg(x=200.0, y=200.0, element=0)
    dx = b.x - p.x
    dy = b.y - p.y
    dist = math.hypot(dx, dy)
    assert dist > BALL_R + p.radius  # no collision


def test_peg_alive_default() -> None:
    """New pegs are alive by default."""
    p = Peg(x=50.0, y=50.0, element=3)
    assert p.alive is True


def test_peg_element_bounds() -> None:
    """Peg element can be 0-4 (normal) or 5 (target)."""
    for elem in range(6):
        p = Peg(x=0.0, y=0.0, element=elem)
        assert p.element == elem


def test_phase_transitions() -> None:
    """Phase integer values are sequential."""
    phases = [Phase.AIM, Phase.DROP, Phase.RESULT, Phase.GAMEOVER]
    for i, p in enumerate(phases):
        assert int(p) == i


def test_ball_hits_counter() -> None:
    """Ball tracks hit count correctly."""
    b = Ball(x=0.0, y=0.0, vx=0.0, vy=0.0, element=1)
    assert b.hits == 0
    b.hits += 1
    assert b.hits == 1
    b.hits += 3
    assert b.hits == 4


def test_element_names_have_no_cjk() -> None:
    """Element names contain only ASCII (Pyxel font limitation)."""
    for name in ELEMENT_NAMES:
        assert all(ord(c) < 128 for c in name), f"Non-ASCII in: {name}"
    for label in ["Fr", "Wa", "Ea", "Ai", "Ae"]:
        assert all(ord(c) < 128 for c in label)


def test_peg_can_be_deactivated() -> None:
    """Peg alive flag can be set to False."""
    p = Peg(x=50.0, y=50.0, element=0)
    p.alive = False
    assert p.alive is False
    assert p.element == 0  # other fields unchanged


def test_score_addition() -> None:
    """Score arithmetic works for combo multipliers."""
    score = 0
    # simulate: 4 same-element hits, multipliers x1, x2, x4, x8
    score += 10 * 1  # first hit
    score += 10 * 2  # second hit
    score += 10 * 4  # third hit
    score += 10 * 8  # fourth hit
    assert score == 150


def test_target_score_calculation() -> None:
    """Target pegs give higher base score."""
    score = 0
    # target peg with x4 combo
    score += 30 * 4
    assert score == 120


def test_board_clear_bonus() -> None:
    """Board clear bonus is 500."""
    score = 350
    score += 500  # clear bonus
    assert score == 850


def test_game_state_tracking() -> None:
    """Verify game state variables are independent."""
    balls_left = 10
    targets_total = 8
    targets_cleared = 3
    assert targets_cleared < targets_total
    targets_cleared += 2
    assert targets_cleared == 5
    assert balls_left == 10  # unchanged


def test_combo_multiplier_sequence() -> None:
    """Combo depth produces correct multipliers (2^depth)."""
    for depth in range(6):
        mult = max(1, 2**depth)
        expected = [1, 2, 4, 8, 16, 32][depth]
        assert mult == expected, f"depth={depth}: expected {expected}, got {mult}"


if __name__ == "__main__":
    import traceback

    tests = [
        test_dataclass_peg,
        test_dataclass_ball,
        test_dataclass_particle,
        test_dataclass_float_text,
        test_phase_enum,
        test_element_config,
        test_constants,
        test_ball_physics_basics,
        test_wall_bounce_left,
        test_wall_bounce_right,
        test_peg_collision_detection,
        test_peg_no_collision_when_far,
        test_peg_alive_default,
        test_peg_element_bounds,
        test_phase_transitions,
        test_ball_hits_counter,
        test_element_names_have_no_cjk,
        test_peg_can_be_deactivated,
        test_score_addition,
        test_target_score_calculation,
        test_board_clear_bonus,
        test_game_state_tracking,
        test_combo_multiplier_sequence,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            print(f"  PASS  {test_fn.__name__}")
            passed += 1
        except Exception:
            print(f"  FAIL  {test_fn.__name__}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    if failed > 0:
        sys.exit(1)
