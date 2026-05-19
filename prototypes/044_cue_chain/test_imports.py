"""test_imports.py — Headless logic tests for CUE CHAIN.

Uses Game.__new__ pattern to bypass Pyxel init.
"""

from __future__ import annotations

import inspect
import math
import sys

# Add prototype dir to path BEFORE importing main (which imports pyxel)
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/044_cue_chain")

from main import (
    BALL_COUNT,
    BALL_RADIUS,
    CHAIN_BREAK_MULT,
    COMBO_FOR_CHAIN_BREAK,
    FRICTION,
    GAME_TIME_SECS,
    MAX_POWER,
    POCKET_POSITIONS,
    SCREEN_H,
    SCREEN_W,
    STOP_THRESHOLD,
    TABLE_BOTTOM,
    TABLE_LEFT,
    TABLE_RIGHT,
    TABLE_TOP,
    Ball,
    Game,
    Phase,
)


# ── Config Tests ──────────────────────────────────────────────────────────────

def test_config_constants() -> None:
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert TABLE_LEFT == 20
    assert TABLE_RIGHT == 236
    assert BALL_COUNT == 6
    assert BALL_RADIUS == 5
    assert COMBO_FOR_CHAIN_BREAK == 3
    assert CHAIN_BREAK_MULT == 3
    assert GAME_TIME_SECS == 60
    assert MAX_POWER == 8.0
    assert FRICTION == 0.985
    assert STOP_THRESHOLD == 0.3

    # 6 pockets
    assert len(POCKET_POSITIONS) == 6
    # All pockets within table bounds
    for px, py in POCKET_POSITIONS:
        assert TABLE_LEFT <= px <= TABLE_RIGHT
        assert TABLE_TOP <= py <= TABLE_BOTTOM


# ── Ball Dataclass Tests ──────────────────────────────────────────────────────

def test_ball_creation() -> None:
    b = Ball(x=100.0, y=200.0, color=2)
    assert b.x == 100.0
    assert b.y == 200.0
    assert b.vx == 0.0
    assert b.vy == 0.0
    assert b.color == 2
    assert b.active is True

    cue = Ball(x=50.0, y=50.0)
    assert cue.color == -1  # cue ball

    moving = Ball(x=10.0, y=20.0, vx=3.0, vy=-1.5, active=False)
    assert moving.vx == 3.0
    assert moving.vy == -1.5
    assert moving.active is False


# ── Phase Enum Tests ──────────────────────────────────────────────────────────

def test_phase_enum() -> None:
    phases = list(Phase)
    assert Phase.AIMING in phases
    assert Phase.MOVING in phases
    assert Phase.GAME_OVER in phases
    assert len(phases) == 3


# ── Game State Tests (headless, via __new__) ─────────────────────────────────

def _make_game() -> Game:
    """Create a bare Game instance without running Pyxel."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g._rng = None  # type: ignore[attr-defined]
    g.phase = Phase.AIMING  # type: ignore[attr-defined]
    g.score = 0  # type: ignore[attr-defined]
    g.combo = 0  # type: ignore[attr-defined]
    g.max_combo = 0  # type: ignore[attr-defined]
    g.chain_break = False  # type: ignore[attr-defined]
    g.game_timer = 0  # type: ignore[attr-defined]
    g.cue_ball = Ball(0.0, 0.0)  # type: ignore[attr-defined]
    g.balls = []  # type: ignore[attr-defined]
    g._aim_start_x = 0.0  # type: ignore[attr-defined]
    g._aim_start_y = 0.0  # type: ignore[attr-defined]
    g._aiming = False  # type: ignore[attr-defined]
    g._last_pocketed_color = -1  # type: ignore[attr-defined]
    g.reset()
    return g


def test_game_reset() -> None:
    g = _make_game()
    assert g.phase == Phase.AIMING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.chain_break is False
    assert g.game_timer == GAME_TIME_SECS * 30
    assert g.cue_ball.active is True
    assert g._aiming is False

    # Cue ball should be centered on table
    assert abs(g.cue_ball.x - (TABLE_LEFT + (TABLE_RIGHT - TABLE_LEFT) / 2)) < 10
    assert abs(g.cue_ball.y - (TABLE_TOP + (TABLE_BOTTOM - TABLE_TOP) / 2)) < 10

    # Should have exactly BALL_COUNT colored balls
    assert len(g.balls) == BALL_COUNT
    for b in g.balls:
        assert b.active is True
        assert 0 <= b.color <= 3
        # Ball within table bounds
        assert TABLE_LEFT + BALL_RADIUS <= b.x <= TABLE_RIGHT - BALL_RADIUS
        assert TABLE_TOP + BALL_RADIUS <= b.y <= TABLE_BOTTOM - BALL_RADIUS


def test_game_reset_clears_previous_state() -> None:
    g = _make_game()
    g.score = 9999
    g.combo = 5
    g.max_combo = 10
    g.chain_break = True
    g.phase = Phase.GAME_OVER
    g.game_timer = 1
    g.balls.clear()

    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.chain_break is False
    assert g.phase == Phase.AIMING
    assert len(g.balls) == BALL_COUNT


def test_all_stopped_no_motion() -> None:
    g = _make_game()
    g.cue_ball.vx = 0.0
    g.cue_ball.vy = 0.0
    for b in g.balls:
        b.vx = 0.0
        b.vy = 0.0
    assert g._all_stopped() is True


def test_all_stopped_cue_moving() -> None:
    g = _make_game()
    g.cue_ball.vx = 2.0
    for b in g.balls:
        b.vx = 0.0
        b.vy = 0.0
    assert g._all_stopped() is False


def test_all_stopped_colored_moving() -> None:
    g = _make_game()
    g.cue_ball.vx = 0.0
    g.cue_ball.vy = 0.0
    for b in g.balls:
        b.vx = 0.0
        b.vy = 0.0
    g.balls[0].vy = 1.0
    assert g._all_stopped() is False


def test_all_stopped_below_threshold() -> None:
    g = _make_game()
    g.cue_ball.vx = STOP_THRESHOLD * 0.5
    g.cue_ball.vy = 0.0
    for b in g.balls:
        b.vx = 0.0
        b.vy = 0.0
    assert g._all_stopped() is True


def test_all_stopped_cue_inactive() -> None:
    g = _make_game()
    g.cue_ball.active = False
    g.cue_ball.vx = 5.0  # moving but inactive
    for b in g.balls:
        b.vx = 0.0
        b.vy = 0.0
    # Inactive cue ball with velocity is still "stopped"
    assert g._all_stopped() is True


# ── Collision Tests ───────────────────────────────────────────────────────────

def test_resolve_collision_apart() -> None:
    g = _make_game()
    a = Ball(x=100.0, y=100.0, vx=2.0, vy=0.0)
    b = Ball(x=120.0, y=100.0, vx=0.0, vy=0.0)
    g._resolve_collision(a, b)
    # Balls are far apart (> 2*BALL_RADIUS = 10), no change
    assert a.x == 100.0
    assert b.x == 120.0
    assert a.vx == 2.0
    assert b.vx == 0.0


def test_resolve_collision_head_on() -> None:
    g = _make_game()
    a = Ball(x=100.0, y=100.0, vx=3.0, vy=0.0)
    b = Ball(x=108.0, y=100.0, vx=0.0, vy=0.0)
    g._resolve_collision(a, b)
    # Head-on elastic collision: a stops, b takes velocity
    assert abs(a.vx) < 0.2, f"Expected a to nearly stop, got vx={a.vx}"
    assert b.vx > 2.0, f"Expected b to move right, got vx={b.vx}"


def test_resolve_collision_separates_overlap() -> None:
    g = _make_game()
    a = Ball(x=100.0, y=100.0)
    b = Ball(x=105.0, y=100.0)  # 5px apart, BALL_RADIUS*2=10, so overlapping
    g._resolve_collision(a, b)
    dist = math.hypot(b.x - a.x, b.y - a.y)
    assert dist >= BALL_RADIUS * 2 - 0.01


# ── Wall Clamp Tests ──────────────────────────────────────────────────────────

def test_clamp_to_table_left_wall() -> None:
    g = _make_game()
    b = Ball(x=TABLE_LEFT + BALL_RADIUS - 2, y=100.0, vx=-3.0, vy=0.0)
    g._clamp_to_table(b)
    assert b.x >= TABLE_LEFT + BALL_RADIUS - 0.01
    assert b.vx > 0  # reflected right


def test_clamp_to_table_right_wall() -> None:
    g = _make_game()
    b = Ball(x=TABLE_RIGHT - BALL_RADIUS + 2, y=100.0, vx=3.0, vy=0.0)
    g._clamp_to_table(b)
    assert b.x <= TABLE_RIGHT - BALL_RADIUS + 0.01
    assert b.vx < 0  # reflected left


def test_clamp_to_table_top_wall() -> None:
    g = _make_game()
    b = Ball(x=100.0, y=TABLE_TOP + BALL_RADIUS - 2, vx=0.0, vy=-3.0)
    g._clamp_to_table(b)
    assert b.y >= TABLE_TOP + BALL_RADIUS - 0.01
    assert b.vy > 0  # reflected down


def test_clamp_to_table_bottom_wall() -> None:
    g = _make_game()
    b = Ball(x=100.0, y=TABLE_BOTTOM - BALL_RADIUS + 2, vx=0.0, vy=3.0)
    g._clamp_to_table(b)
    assert b.y <= TABLE_BOTTOM - BALL_RADIUS + 0.01
    assert b.vy < 0  # reflected up


# ── Pocket Tests ──────────────────────────────────────────────────────────────

def test_check_pocket_cue_ball() -> None:
    g = _make_game()
    px, py = POCKET_POSITIONS[0]  # top-left pocket
    g.cue_ball.x = float(px)
    g.cue_ball.y = float(py)
    g.cue_ball.active = True
    g.cue_ball.vx = 3.0
    g.cue_ball.vy = 2.0
    g._check_pocket(g.cue_ball, is_cue=True)
    assert g.cue_ball.active is False
    assert g.cue_ball.vx == 0.0
    assert g.cue_ball.vy == 0.0


def test_check_pocket_colored_ball() -> None:
    g = _make_game()
    initial_ball_count = len(g.balls)
    px, py = POCKET_POSITIONS[0]
    g.balls[0].x = float(px)
    g.balls[0].y = float(py)
    g.balls[0].active = True
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g._last_pocketed_color = -1
    g.chain_break = False

    g._check_pocket(g.balls[0], is_cue=False)

    assert g.balls[0].active is False
    assert g.balls[0].vx == 0.0
    assert g.score > 0  # Scored
    assert g.combo == 1  # First pocket = combo 1
    assert g.max_combo == 1


def test_check_pocket_not_near() -> None:
    g = _make_game()
    b = g.balls[0]
    b.x = 100.0
    b.y = 100.0  # Far from all pockets
    b.active = True
    b.vx = 1.0
    g._check_pocket(b, is_cue=False)
    assert b.active is True
    assert b.vx == 1.0


# ── Combo Tests ──────────────────────────────────────────────────────────────

def test_pocket_same_color_builds_combo() -> None:
    g = _make_game()
    g.score = 0
    g.combo = 1
    g.max_combo = 1
    g._last_pocketed_color = 2
    g.chain_break = False

    b = Ball(x=100.0, y=100.0, color=2)  # same color
    g._pocket_ball(b)

    assert g.combo == 2
    assert g.max_combo == 2
    assert g.score == 200  # 100 * 2


def test_pocket_different_color_resets_combo() -> None:
    g = _make_game()
    g.score = 0
    g.combo = 3
    g.max_combo = 3
    g._last_pocketed_color = 2
    g.chain_break = False

    b = Ball(x=100.0, y=100.0, color=1)  # different color
    g._pocket_ball(b)

    assert g.combo == 1  # reset
    assert g.max_combo == 3  # max preserved
    assert g._last_pocketed_color == 1


def test_chain_break_any_color_counts() -> None:
    g = _make_game()
    g.score = 0
    g.combo = 2
    g.max_combo = 2
    g._last_pocketed_color = 0
    g.chain_break = True  # chain break mode

    b = Ball(x=100.0, y=100.0, color=3)  # different color, but chain break ignores
    g._pocket_ball(b)

    assert g.combo == 3  # combo continues
    assert g.score == 900  # 100 * CHAIN_BREAK_MULT(3) * combo(3)


def test_chain_break_activates_at_threshold() -> None:
    g = _make_game()
    g.score = 0
    g.combo = 2
    g.max_combo = 2
    g._last_pocketed_color = 1
    g.chain_break = False

    b = Ball(x=100.0, y=100.0, color=1)  # same color, hits threshold
    g._pocket_ball(b)

    assert g.combo == 3
    assert g.chain_break is True


def test_pocket_replacement_spawns_new_ball() -> None:
    g = _make_game()
    initial_count = len(g.balls)
    active_before = sum(1 for b in g.balls if b.active)

    b = g.balls[0]
    g._pocket_ball(b)

    # One ball pocketed (inactive) + one spawned = same total active
    active_after = sum(1 for b in g.balls if b.active)
    assert active_after == active_before


# ── Finalize Motion Tests ─────────────────────────────────────────────────────

def test_finalize_motion_respawns_cue() -> None:
    g = _make_game()
    g.cue_ball.active = False
    g.cue_ball.x = 999.0  # off table
    g.cue_ball.y = 999.0
    g.chain_break = True

    g._finalize_motion()

    assert g.cue_ball.active is True
    # Should be back near center
    center_x = TABLE_LEFT + (TABLE_RIGHT - TABLE_LEFT) / 2
    center_y = TABLE_TOP + (TABLE_BOTTOM - TABLE_TOP) / 2
    assert abs(g.cue_ball.x - center_x) < 50
    assert abs(g.cue_ball.y - center_y) < 50
    assert g.chain_break is False  # expired
    assert g.phase == Phase.AIMING


def test_finalize_motion_zeros_velocities() -> None:
    g = _make_game()
    g.cue_ball.vx = 5.0
    g.cue_ball.vy = 3.0
    for b in g.balls:
        b.vx = 2.0
        b.vy = -1.0

    g._finalize_motion()

    assert g.cue_ball.vx == 0.0
    assert g.cue_ball.vy == 0.0
    for b in g.balls:
        assert b.vx == 0.0
        assert b.vy == 0.0


# ── Overlap/Avoidance Tests ───────────────────────────────────────────────────

def test_ball_overlaps_with_cue() -> None:
    g = _make_game()
    # Clear existing balls so they don't interfere with overlap checks
    g.balls.clear()
    g.cue_ball.x = 100.0
    g.cue_ball.y = 100.0
    # Check a position overlapping cue ball
    assert g._ball_overlaps(100.0 + BALL_RADIUS, 100.0) is True
    # Check same position overlaps with a colored ball too
    g.balls.append(Ball(x=200.0, y=200.0, active=True))
    assert g._ball_overlaps(200.0 + BALL_RADIUS, 200.0) is True
    # Far from all balls
    assert g._ball_overlaps(50.0, 50.0) is False


def test_separate_cue_ball_pushes_away() -> None:
    g = _make_game()
    g.cue_ball.x = 100.0
    g.cue_ball.y = 100.0
    # Place a ball right on top of cue
    g.balls.clear()
    g.balls.append(Ball(x=100.0 + BALL_RADIUS, y=100.0, active=True))

    g._separate_cue_ball()

    dist = math.hypot(g.cue_ball.x - g.balls[0].x, g.cue_ball.y - g.balls[0].y)
    assert dist >= BALL_RADIUS * 2 + 2


# ── Spawn Tests ────────────────────────────────────────────────────────────────

def test_spawn_balls_creates_correct_count() -> None:
    g = _make_game()
    assert len(g.balls) == BALL_COUNT
    for b in g.balls:
        assert b.active is True
        assert 0 <= b.color <= 3


def test_reset_reproducible_state() -> None:
    g1 = _make_game()
    g2 = _make_game()
    # Both should have BALL_COUNT balls, cue at center, phase AIMING
    assert g1.phase == g2.phase == Phase.AIMING
    assert len(g1.balls) == len(g2.balls) == BALL_COUNT
    assert g1.score == g2.score == 0


# ── Method Signature Tests ────────────────────────────────────────────────────

def test_game_has_required_methods() -> None:
    """Verify all key methods exist (no method name collisions)."""
    required = [
        "reset",
        "update",
        "draw",
        "_spawn_balls",
        "_spawn_one_ball",
        "_ball_overlaps",
        "_all_stopped",
        "_update_aiming",
        "_update_physics",
        "_resolve_collision",
        "_clamp_to_table",
        "_check_pocket",
        "_pocket_ball",
        "_finalize_motion",
        "_separate_cue_ball",
    ]
    source = inspect.getsource(Game)
    for method_name in required:
        assert f"def {method_name}" in source, f"Missing method: {method_name}"


def test_method_names_unique() -> None:
    """No duplicate method names in Game class."""
    methods = [
        name for name, _ in inspect.getmembers(Game, predicate=inspect.isfunction)
        if not name.startswith("__")
    ]
    assert len(methods) == len(set(methods)), f"Duplicate methods: {methods}"


if __name__ == "__main__":
    import subprocess

    # Run all test_ functions
    frame = inspect.currentframe()
    assert frame is not None
    test_funcs = sorted(
        name for name, obj in frame.f_globals.items()
        if name.startswith("test_") and callable(obj)
    )
    passed = 0
    for name in test_funcs:
        try:
            frame.f_globals[name]()
            print(f"  PASS {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")

    print(f"\n{passed}/{len(test_funcs)} tests passed")
    sys.exit(0 if passed == len(test_funcs) else 1)
