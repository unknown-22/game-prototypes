"""test_imports.py — Headless logic tests for 104_tug_chain."""

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/104_tug_chain")
from main import (
    Game,
    GhostTrail,
    Particle,
    Phase,
    RopeSegment,
    SEGMENT_COLORS,
    RAINBOW_COLORS,
    BLACK, WHITE, RED, GREEN, LIGHT_BLUE, YELLOW, GRAY, CYAN, DARK_BLUE,
)


def _make_game() -> Game:
    """Factory for headless Game instances."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.segments = []
    g.ghosts = []
    g.particles = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0
    g.timer = Game.GAME_DURATION
    g.rope_x = 100.0
    g.rope_y = Game.ROPE_Y
    g.pull_color = SEGMENT_COLORS[0]
    g.pull_timer = Game.PULL_WINDOW
    g.super_mode = False
    g.super_timer = 0
    g.ai_pull_timer = 150
    g.ai_pull_color = SEGMENT_COLORS[0]
    g.game_over_reason = ""
    g.shake_frames = 0
    g.grip_zone_index = 3
    g.ghost_bonus = 0
    g.color_index = 0
    g._color_cycle_timer = 0
    g.phase = Phase.PLAYING
    g.reset()
    return g


# ── Data Class Tests ──────────────────────────────────────────────────────────


def test_rope_segment_creation() -> None:
    seg = RopeSegment(x=100.0, y=120.0, color=RED)
    assert seg.x == 100.0
    assert seg.y == 120.0
    assert seg.color == RED
    assert seg.width == 32
    assert seg.height == 12


def test_ghost_trail_creation() -> None:
    ghost = GhostTrail(x=50.0, y=100.0, color=GREEN, life=60, width=32)
    assert ghost.x == 50.0
    assert ghost.life == 60
    assert ghost.color == GREEN


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-3.0, life=25, color=YELLOW)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -3.0
    assert p.life == 25
    assert p.color == YELLOW


# ── Phase Enum Tests ──────────────────────────────────────────────────────────


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Game Initialization Tests ─────────────────────────────────────────────────


def test_game_reset() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0
    assert g.timer == Game.GAME_DURATION
    assert g.pull_timer == Game.PULL_WINDOW
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.game_over_reason == ""
    assert g.shake_frames == 0
    assert g.ghost_bonus == 0


def test_create_segments() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    segs = g._create_segments()
    assert len(segs) == Game.SEGMENT_COUNT
    # _create_segments sets raw x (left edge), _update_segments converts to centers
    assert segs[0].x == 100.0  # raw x, not centered yet
    for seg in segs:
        assert seg.color in SEGMENT_COLORS
        assert seg.width == Game.SEGMENT_WIDTH
        assert seg.height == Game.SEGMENT_HEIGHT


def test_update_segments() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g._update_segments()
    assert len(g.segments) == Game.SEGMENT_COUNT
    # Check first segment x
    assert abs(g.segments[0].x - (100.0 + Game.SEGMENT_WIDTH / 2)) < 0.01
    # Check last segment x
    expected_last_x = 100.0 + (Game.SEGMENT_COUNT - 1) * Game.SEGMENT_WIDTH + Game.SEGMENT_WIDTH / 2
    assert abs(g.segments[-1].x - expected_last_x) < 0.01


def test_get_grip_segment() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g._update_segments()
    grip = g.get_grip_segment()
    assert grip is not None
    assert grip.x > 0
    assert grip.color in SEGMENT_COLORS


def test_get_grip_segment_out_of_bounds() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g.grip_zone_index = 999
    assert g.get_grip_segment() is None


# ── Pull Mechanics Tests ──────────────────────────────────────────────────────


def test_compute_pull_force_normal() -> None:
    g = _make_game()
    g.ghost_bonus = 0
    g.super_mode = False
    force = g.compute_pull_force()
    assert abs(force - 6.0) < 0.01


def test_compute_pull_force_with_ghosts() -> None:
    g = _make_game()
    g.ghost_bonus = 3  # 3 ghosts
    g.super_mode = False
    force = g.compute_pull_force()
    assert abs(force - (6.0 + 3 * 2.0)) < 0.01


def test_compute_pull_force_super() -> None:
    g = _make_game()
    g.ghost_bonus = 0
    g.super_mode = True
    force = g.compute_pull_force()
    assert abs(force - 18.0) < 0.01  # 6.0 * 3


def test_compute_pull_force_super_with_ghosts() -> None:
    g = _make_game()
    g.ghost_bonus = 4
    g.super_mode = True
    force = g.compute_pull_force()
    assert abs(force - (6.0 + 8.0) * 3.0) < 0.01


def test_advance_rope_toward_player() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g._advance_rope(toward_player=6.0)
    assert g.rope_x < 100.0  # moved left
    assert abs(g.rope_x - 94.0) < 0.01


def test_advance_rope_toward_ai() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g._advance_rope(toward_player=-4.0)
    assert g.rope_x > 100.0  # moved right
    assert abs(g.rope_x - 104.0) < 0.01


def test_advance_rope_clamped_left() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 30.0
    g._create_segments()
    g._advance_rope(toward_player=20.0)
    assert g.rope_x == 20.0  # clamped


def test_advance_rope_clamped_right() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 235.0
    g._create_segments()
    g._advance_rope(toward_player=-20.0)
    assert g.rope_x == 240.0  # clamped


def test_pull_success_normal() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g.score = 0
    g.combo = 0
    old_rope_x = g.rope_x
    g._pull_success()
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 10  # combo * 10 = 1 * 10
    assert g.rope_x < old_rope_x  # pulled toward player
    assert g.pull_timer == Game.PULL_WINDOW  # reset
    assert len(g.ghosts) == 1
    assert len(g.particles) == 8


def test_pull_success_combo_builds() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g.combo = 3
    g.max_combo = 3
    g.score = 60
    g._pull_success()
    assert g.combo == 4
    assert g.score == 60 + 40  # 60 + 4*10
    assert g.super_mode is True  # combo >= 4 triggers super
    assert g.super_timer == Game.SUPER_DURATION


def test_pull_success_max_combo_tracks() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g.combo = 5
    g.max_combo = 5
    g._pull_success()
    assert g.max_combo == 6


def test_pull_fail_wrong() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g.combo = 4
    g.max_combo = 4
    g.heat = 0
    old_rope_x = g.rope_x
    g._pull_fail("wrong")
    assert g.combo == 0
    assert g.heat == 2 + 3  # base + wrong penalty
    assert g.pull_timer == Game.PULL_WINDOW
    assert g.rope_x > old_rope_x  # AI pulled


def test_pull_fail_timeout() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g.combo = 3
    g.heat = 0
    old_rope_x = g.rope_x
    g._pull_fail("timeout")
    assert g.combo == 0
    assert g.heat == 2  # no +3 for timeout
    assert g.pull_timer == Game.PULL_WINDOW
    assert g.rope_x > old_rope_x


def test_try_pull_matched() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    old_combo = g.combo
    g._try_pull(matched=True)
    assert g.combo == old_combo + 1


def test_try_pull_not_matched() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g.combo = 2
    g.heat = 0
    g._try_pull(matched=False)
    assert g.combo == 0
    assert g.heat > 0


# ── Ghost Trail Tests ─────────────────────────────────────────────────────────


def test_ghost_creation_from_pull() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    assert len(g.ghosts) == 0
    g._pull_success()
    assert len(g.ghosts) == 1
    assert g.ghosts[0].life == Game.GHOST_LIFE


def test_update_ghosts_decrements_life() -> None:
    g = _make_game()
    g.ghosts = [GhostTrail(x=100.0, y=120.0, color=RED, life=5, width=32)]
    g._update_ghosts()
    assert g.ghosts[0].life == 4


def test_update_ghosts_removes_dead() -> None:
    g = _make_game()
    g.ghosts = [
        GhostTrail(x=100.0, y=120.0, color=RED, life=1, width=32),
        GhostTrail(x=120.0, y=120.0, color=GREEN, life=10, width=32),
    ]
    g._update_ghosts()
    assert len(g.ghosts) == 1  # life=0 removed
    assert g.ghosts[0].color == GREEN


def test_ghost_bonus_updates() -> None:
    g = _make_game()
    g.ghosts = [
        GhostTrail(x=100.0, y=120.0, color=RED, life=10, width=32),
        GhostTrail(x=120.0, y=120.0, color=GREEN, life=20, width=32),
        GhostTrail(x=140.0, y=120.0, color=LIGHT_BLUE, life=30, width=32),
    ]
    g._update_ghosts()
    assert g.ghost_bonus == 3


def test_ghost_bonus_zero_when_empty() -> None:
    g = _make_game()
    g.ghosts = []
    g._update_ghosts()
    assert g.ghost_bonus == 0


# ── Particle Tests ────────────────────────────────────────────────────────────


def test_spawn_particles_normal() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.super_mode = False
    g._spawn_particles(100.0, 120.0, RED, 8)
    assert len(g.particles) == 8
    for p in g.particles:
        assert abs(p.x - 100.0) < 3.1
        assert p.color == RED  # not super, so single color
        assert 15 <= p.life <= 30
        assert -3 <= p.vx <= 3
        assert -5 <= p.vy <= -1


def test_spawn_particles_super_mode() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.super_mode = True
    g._spawn_particles(100.0, 120.0, RED, 20)
    assert len(g.particles) == 20
    # In super mode, colors can be rainbow
    for p in g.particles:
        assert p.color in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)


def test_update_particles_move_and_die() -> None:
    g = _make_game()
    g.particles = [
        Particle(x=100.0, y=120.0, vx=2.0, vy=-3.0, life=5, color=RED),
        Particle(x=200.0, y=130.0, vx=0.0, vy=0.0, life=1, color=GREEN),
    ]
    g._update_particles()
    # First particle moved
    p1 = g.particles[0]
    assert abs(p1.x - 102.0) < 0.01
    # y: 120 + (-3) = 117, then vy becomes -3+0.2=-2.8
    assert abs(p1.y - 117.0) < 0.01
    assert p1.life == 4
    # Second particle with life=1 decremented to 0 and removed
    assert len(g.particles) == 1


# ── Timer Tests ───────────────────────────────────────────────────────────────


def test_update_timers() -> None:
    g = _make_game()
    g.timer = 100
    g.pull_timer = 50
    g.super_timer = 30
    g.super_mode = True
    g._update_timers()
    assert g.timer == 99
    assert g.pull_timer == 49
    assert g.super_timer == 29
    assert g.super_mode is True  # still active


def test_update_timers_super_expires() -> None:
    g = _make_game()
    g.timer = 100
    g.pull_timer = 50
    g.super_timer = 1
    g.super_mode = True
    g._update_timers()
    assert g.super_timer == 0
    assert g.super_mode is False


def test_update_timers_zero_doesnt_go_negative() -> None:
    g = _make_game()
    g.timer = 0
    g.pull_timer = 0
    g.super_timer = 0
    g._update_timers()
    assert g.timer == 0
    assert g.pull_timer == 0
    assert g.super_timer == 0


# ── Color Cycle Tests ─────────────────────────────────────────────────────────


def test_cycle_pull_color_changes() -> None:
    g = _make_game()
    g.color_index = 0
    g._cycle_pull_color()
    # First call just increments timer
    assert g.pull_color == SEGMENT_COLORS[0]  # unchanged until cycle fires

    # Simulate reaching cycle interval
    g._color_cycle_timer = Game.PULL_COLOR_CYCLE_INTERVAL - 1
    g._cycle_pull_color()
    assert g._color_cycle_timer == 0
    assert g.color_index == 1


# ── Win/Lose Tests ────────────────────────────────────────────────────────────


def test_check_win() -> None:
    g = _make_game()
    g.rope_x = 30.0  # past WIN_THRESHOLD of 40
    g.heat = 0
    g.timer = 100
    result = g._check_win_lose()
    assert result == Phase.GAME_OVER
    assert g.game_over_reason == "WIN!"


def test_check_lose_pulled_away() -> None:
    g = _make_game()
    g.rope_x = 210.0  # past LOSE_THRESHOLD of 200
    g.heat = 0
    g.timer = 100
    result = g._check_win_lose()
    assert result == Phase.GAME_OVER
    assert g.game_over_reason == "PULLED AWAY!"


def test_check_lose_overheat() -> None:
    g = _make_game()
    g.rope_x = 100.0
    g.heat = 10
    g.timer = 100
    result = g._check_win_lose()
    assert result == Phase.GAME_OVER
    assert g.game_over_reason == "OVERHEAT!"


def test_check_lose_time_up() -> None:
    g = _make_game()
    g.rope_x = 100.0
    g.heat = 0
    g.timer = 0
    result = g._check_win_lose()
    assert result == Phase.GAME_OVER
    assert g.game_over_reason == "TIME UP!"


def test_check_no_win_lose() -> None:
    g = _make_game()
    g.rope_x = 100.0
    g.heat = 5
    g.timer = 100
    result = g._check_win_lose()
    assert result is None


# ── AI Pull Tests ─────────────────────────────────────────────────────────────


def test_ai_pull_moves_rope() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    # Force AI pull timer to fire
    g.ai_pull_timer = 1
    old_rope_x = g.rope_x
    g._ai_pull()
    assert g.rope_x > old_rope_x  # AI pulls rope right
    assert g.ai_pull_timer > 0  # Reset


def test_ai_pull_no_trigger() -> None:
    g = _make_game()
    g.rope_x = 100.0
    g.ai_pull_timer = 50
    old_rope_x = g.rope_x
    g._ai_pull()
    assert g.rope_x == old_rope_x  # No movement
    assert g.ai_pull_timer == 49


# ── Rope Color Tests ──────────────────────────────────────────────────────────


def test_update_rope_colors() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    original_colors = [seg.color for seg in g.segments]
    # Force cycle
    g._color_cycle_timer = Game.COLOR_CYCLE_INTERVAL - 1
    g._update_rope_colors()
    # Colors should have changed (random seed ensures this)
    new_colors = [seg.color for seg in g.segments]
    for c in new_colors:
        assert c in SEGMENT_COLORS


# ── Combo/Max Combo Tests ─────────────────────────────────────────────────────


def test_max_combo_persists_after_fail() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g.combo = 4
    g.max_combo = 4
    g._pull_fail("timeout")
    assert g.combo == 0
    assert g.max_combo == 4  # max_combo persists


def test_heat_at_9_plus_fail_means_overheat() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g.heat = 9
    g._pull_fail("wrong")
    assert g.heat >= 10  # 9 + 2 + 3 = 14


# ── Multiple Pull Sequence Test ───────────────────────────────────────────────


def test_multiple_successful_pulls_build_combo() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    for i in range(6):
        g._pull_success()
    assert g.combo == 6
    assert g.max_combo == 6
    assert g.super_mode is True  # activated at combo 4
    expected_score = sum((c + 1) * 10 for c in range(6))  # combo 0→1→...→6, scores: 10,20,30,40,50,60
    assert g.score == expected_score


# ── Super Mode Tests ──────────────────────────────────────────────────────────


def test_super_mode_activates_at_combo_4() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g.combo = 3
    g._pull_success()
    assert g.combo == 4
    assert g.super_mode is True


def test_super_mode_increases_force() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g.rope_x = 100.0
    g._create_segments()
    g.super_mode = True
    # Force should be 3x
    force = g.compute_pull_force()
    assert abs(force - 18.0) < 0.01


if __name__ == "__main__":
    import inspect

    tests = [
        obj
        for name, obj in inspect.getmembers(sys.modules[__name__])
        if callable(obj) and name.startswith("test_")
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {test.__name__}: {e}")

    print(f"\n{passed} passed, {failed} failed")
    assert failed == 0, f"{failed} tests failed"
