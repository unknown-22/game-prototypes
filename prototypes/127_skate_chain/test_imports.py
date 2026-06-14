"""test_imports.py — Headless logic tests for SKATE CHAIN.

Tests core game logic without initializing Pyxel (no display needed).
Uses Game.__new__ pattern to bypass pyxel.init().
"""
from __future__ import annotations

import math
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/127_skate_chain")
from main import (
    APEX_THRESHOLD,
    COMBO_THRESHOLD,
    DARK_BLUE,
    FloatingText,
    GAME_DURATION,
    GREEN,
    HEAT_DECAY,
    MAX_HEAT,
    OSC_SPEED_BASE,
    Particle,
    Phase,
    RAMP_BOTTOM_Y,
    RAMP_CENTER_X,
    RAMP_FLAT_LEFT,
    RAMP_FLAT_RIGHT,
    RAMP_HALF_WIDTH,
    RAMP_LEFT_EDGE_X,
    RAMP_RIGHT_EDGE_X,
    RAMP_TOP_Y,
    RED,
    SCREEN_H,
    SCREEN_W,
    Skater,
    SUPER_DURATION,
    TRICK_COLORS,
    TRICK_NAMES,
    YELLOW,
    Game,
    clamp_x,
    oscillation_angle,
    oscillation_x,
    ramp_y,
)


def _make_game() -> Game:
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.particles = []
    g.floating_texts = []
    g._shake_frames = 0
    g._frame_count = 0
    g._osc_frame = 0
    g.reset()
    return g


# ── Ramp Curve Tests ────────────────────────────────────────────────────


def test_ramp_y_flat_section() -> None:
    assert ramp_y(160.0) == RAMP_BOTTOM_Y
    assert ramp_y(RAMP_FLAT_LEFT) == RAMP_BOTTOM_Y
    assert ramp_y(RAMP_FLAT_RIGHT) == RAMP_BOTTOM_Y


def test_ramp_y_left_top() -> None:
    y = ramp_y(RAMP_LEFT_EDGE_X)
    assert y == RAMP_TOP_Y


def test_ramp_y_right_top() -> None:
    y = ramp_y(RAMP_RIGHT_EDGE_X)
    assert y == RAMP_TOP_Y


def test_ramp_y_monotonic_left() -> None:
    prev = RAMP_BOTTOM_Y
    for x in (50.0, 40.0, 35.0, RAMP_LEFT_EDGE_X):
        cy = ramp_y(x)
        assert cy <= prev, f"ramp_y should decrease as x moves left: {cy} > {prev} at x={x}"
        prev = cy


def test_ramp_y_monotonic_right() -> None:
    prev = RAMP_BOTTOM_Y
    for x in (270.0, 280.0, 285.0, RAMP_RIGHT_EDGE_X):
        cy = ramp_y(x)
        assert cy <= prev, f"ramp_y should decrease as x moves right: {cy} > {prev} at x={x}"
        prev = cy


def test_ramp_y_range() -> None:
    for x in range(0, SCREEN_W, 10):
        y = ramp_y(float(x))
        assert RAMP_TOP_Y <= y <= RAMP_BOTTOM_Y, f"y={y} out of range at x={x}"


# ── Oscillation Tests ───────────────────────────────────────────────────


def test_oscillation_angle_zero() -> None:
    assert oscillation_angle(0, 0) == 0.0


def test_oscillation_angle_increases() -> None:
    a1 = oscillation_angle(10, 0)
    a2 = oscillation_angle(20, 0)
    assert a2 > a1


def test_oscillation_angle_combo_speed() -> None:
    a0 = oscillation_angle(100, 0)
    a5 = oscillation_angle(100, 5)
    assert a5 > a0


def test_oscillation_x_center() -> None:
    assert oscillation_x(0.0) == RAMP_CENTER_X


def test_oscillation_x_extremes() -> None:
    x_right = oscillation_x(math.pi / 2)
    assert x_right == RAMP_CENTER_X + RAMP_HALF_WIDTH
    x_left = oscillation_x(-math.pi / 2)
    assert x_left == RAMP_CENTER_X - RAMP_HALF_WIDTH


def test_clamp_x() -> None:
    assert clamp_x(0) == RAMP_LEFT_EDGE_X
    assert clamp_x(400) == RAMP_RIGHT_EDGE_X
    assert clamp_x(160) == 160


# ── Dataclass Tests ─────────────────────────────────────────────────────


def test_skater_default() -> None:
    s = Skater()
    assert s.x == RAMP_CENTER_X
    assert s.y == RAMP_BOTTOM_Y
    assert s.at_apex is False


def test_skater_apex() -> None:
    s = Skater()
    s.angle = math.pi / 2
    assert s.at_apex is True


def test_skater_which_side() -> None:
    s_left = Skater(x=RAMP_CENTER_X - 10)
    assert s_left.which_side == 0
    s_right = Skater(x=RAMP_CENTER_X + 10)
    assert s_right.which_side == 1


def test_particle_fields() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == RED


def test_floating_text_fields() -> None:
    ft = FloatingText(x=50.0, y=60.0, text="+100", life=25, color=YELLOW)
    assert ft.x == 50.0
    assert ft.y == 60.0
    assert ft.text == "+100"
    assert ft.life == 25
    assert ft.color == YELLOW


# ── Game State Tests ────────────────────────────────────────────────────


def test_game_reset() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.game_timer == GAME_DURATION
    assert g.trick_resolved_this_apex is False
    assert g.pre_commit_color == -1
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_game_reset_clears_particles() -> None:
    g = _make_game()
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=RED)]
    g.reset()
    assert len(g.particles) == 0


# ── Trick Color Tests ───────────────────────────────────────────────────


def test_advance_trick_color() -> None:
    g = _make_game()
    g.trick_color_idx = 0
    g.next_trick_idx = 1
    g._advance_trick_color()
    assert g.trick_color_idx == 1
    assert g.next_trick_idx == 2


def test_advance_trick_color_wraps() -> None:
    g = _make_game()
    g.trick_color_idx = 3
    g.next_trick_idx = 0
    g._advance_trick_color()
    assert g.trick_color_idx == 0
    assert g.next_trick_idx == 1


# ── Trick Commit Tests ──────────────────────────────────────────────────


def test_commit_trick_correct() -> None:
    g = _make_game()
    g.trick_color_idx = 0
    result = g._commit_trick(RED)
    assert result == 1


def test_commit_trick_wrong() -> None:
    g = _make_game()
    g.trick_color_idx = 0  # RED
    result = g._commit_trick(GREEN)
    assert result == 0


def test_commit_trick_pre_commit_success() -> None:
    g = _make_game()
    g.trick_color_idx = 0  # RED
    g.pre_commit_color = RED
    g.pre_commit_bonus = False
    result = g._commit_trick(RED)
    assert result == 2


def test_commit_trick_pre_commit_fail() -> None:
    g = _make_game()
    g.trick_color_idx = 0  # RED
    g.pre_commit_color = GREEN
    g.pre_commit_bonus = False
    result = g._commit_trick(GREEN)
    assert result == 0


def test_commit_trick_super_mode() -> None:
    g = _make_game()
    g.super_mode = True
    g.trick_color_idx = 0
    result = g._commit_trick(GREEN)  # wrong color, but super mode
    assert result == 1


# ── Resolve Trick Tests ─────────────────────────────────────────────────


def test_resolve_trick_hit() -> None:
    g = _make_game()
    g.combo = 0
    g.score = 0
    g.heat = 10.0
    g.trick_color_idx = 0
    g._resolve_trick(1)
    assert g.combo == 1
    assert g.score == 100
    assert g.heat == 5.0


def test_resolve_trick_hit_heat_floor() -> None:
    g = _make_game()
    g.combo = 0
    g.heat = 2.0
    g.trick_color_idx = 0
    g._resolve_trick(1)
    assert g.heat == 0.0


def test_resolve_trick_miss() -> None:
    g = _make_game()
    g.combo = 3
    g.score = 500
    g.heat = 10.0
    g._resolve_trick(0)
    assert g.combo == 0
    assert g.heat >= 30.0


def test_resolve_trick_super_score_multiplier() -> None:
    g = _make_game()
    g.super_mode = True
    g.combo = 0
    g.score = 0
    g.trick_color_idx = 0
    g._resolve_trick(1)
    assert g.score == 300  # 100 * 1 * 3


def test_resolve_trick_triggers_super() -> None:
    g = _make_game()
    g.combo = COMBO_THRESHOLD - 1
    g.super_mode = False
    g.trick_color_idx = 0
    g._resolve_trick(1)
    assert g.combo == COMBO_THRESHOLD
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


# ── Super Mode Tests ────────────────────────────────────────────────────


def test_activate_super() -> None:
    g = _make_game()
    assert not g.super_mode
    g._activate_super()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION
    assert g._shake_frames == 8


def test_update_super_decrements() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 10
    g._update_super()
    assert g.super_timer == 9


def test_update_super_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_mode is False
    assert g.super_timer == 0


def test_update_super_noop_when_inactive() -> None:
    g = _make_game()
    g._update_super()
    assert g.super_mode is False


# ── Heat System Tests ───────────────────────────────────────────────────


def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat == max(0.0, 10.0 - HEAT_DECAY)


def test_heat_floor() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_max_causes_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_immunity_during_super() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.heat = MAX_HEAT
    g._update_heat()
    assert g.phase == Phase.PLAYING


def test_heat_below_max_stays_playing() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT - 1.0
    g._update_heat()
    assert g.phase == Phase.PLAYING


# ── Timer Tests ─────────────────────────────────────────────────────────


def test_timer_decreases() -> None:
    g = _make_game()
    initial = g.game_timer
    g._update_timer()
    assert g.game_timer == initial - 1


def test_timer_zero_causes_game_over() -> None:
    g = _make_game()
    g.game_timer = 1
    g._update_timer()
    assert g.game_timer == 0
    assert g.phase == Phase.GAME_OVER


# ── Particle Tests ──────────────────────────────────────────────────────


def test_spawn_particles() -> None:
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100, 100, 5, RED)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == RED
        assert p.life > 0


def test_update_particles_decay() -> None:
    g = _make_game()
    g.particles = [Particle(x=50, y=50, vx=0, vy=0, life=3, color=RED)]
    for _ in range(4):
        g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_gravity() -> None:
    g = _make_game()
    g.particles = [Particle(x=50, y=50, vx=0, vy=0, life=30, color=RED)]
    g._update_particles()
    assert g.particles[0].vy > 0  # gravity applied


# ── Floating Text Tests ─────────────────────────────────────────────────


def test_spawn_floating_text() -> None:
    g = _make_game()
    assert len(g.floating_texts) == 0
    g._spawn_floating_text(100, 100, "+100", YELLOW)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+100"
    assert g.floating_texts[0].color == YELLOW


def test_update_floating_texts_decay() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=50, y=50, text="test", life=2, color=RED)]
    for _ in range(3):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_floating_texts_float_up() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=50, y=50, text="test", life=10, color=RED)]
    g._update_floating_texts()
    assert g.floating_texts[0].y < 50


# ── Physics Tests ───────────────────────────────────────────────────────


def test_update_physics_oscillates() -> None:
    g = _make_game()
    g.combo = 0
    g._osc_frame = 0
    g._update_physics()
    assert g.skater.x == RAMP_CENTER_X  # sin(0) = 0
    assert g.skater.y == RAMP_BOTTOM_Y


def test_update_physics_changes_position() -> None:
    g = _make_game()
    g.combo = 0
    g._osc_frame = 30
    g._update_physics()
    prev_x = g.skater.x
    g._osc_frame += 1
    g._update_physics()
    assert g.skater.x != prev_x


# ── Constants Tests ─────────────────────────────────────────────────────


def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert len(TRICK_COLORS) == 4
    assert len(TRICK_NAMES) == 4
    assert GAME_DURATION == 3600
    assert SUPER_DURATION == 300
    assert MAX_HEAT == 100
    assert COMBO_THRESHOLD == 5
    assert OSC_SPEED_BASE == 0.03
    assert RAMP_CENTER_X == 160
    assert RAMP_BOTTOM_Y == 180
    assert RAMP_TOP_Y == 60


# ── Run ─────────────────────────────────────────────────────────────────


def main() -> None:
    tests = [
        test_ramp_y_flat_section,
        test_ramp_y_left_top,
        test_ramp_y_right_top,
        test_ramp_y_monotonic_left,
        test_ramp_y_monotonic_right,
        test_ramp_y_range,
        test_oscillation_angle_zero,
        test_oscillation_angle_increases,
        test_oscillation_angle_combo_speed,
        test_oscillation_x_center,
        test_oscillation_x_extremes,
        test_clamp_x,
        test_skater_default,
        test_skater_apex,
        test_skater_which_side,
        test_particle_fields,
        test_floating_text_fields,
        test_game_reset,
        test_game_reset_clears_particles,
        test_advance_trick_color,
        test_advance_trick_color_wraps,
        test_commit_trick_correct,
        test_commit_trick_wrong,
        test_commit_trick_pre_commit_success,
        test_commit_trick_pre_commit_fail,
        test_commit_trick_super_mode,
        test_resolve_trick_hit,
        test_resolve_trick_hit_heat_floor,
        test_resolve_trick_miss,
        test_resolve_trick_super_score_multiplier,
        test_resolve_trick_triggers_super,
        test_activate_super,
        test_update_super_decrements,
        test_update_super_expires,
        test_update_super_noop_when_inactive,
        test_heat_decay,
        test_heat_floor,
        test_heat_max_causes_game_over,
        test_heat_immunity_during_super,
        test_heat_below_max_stays_playing,
        test_timer_decreases,
        test_timer_zero_causes_game_over,
        test_spawn_particles,
        test_update_particles_decay,
        test_update_particles_gravity,
        test_spawn_floating_text,
        test_update_floating_texts_decay,
        test_floating_texts_float_up,
        test_update_physics_oscillates,
        test_update_physics_changes_position,
        test_constants,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS  {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {test.__name__}: {e}")

    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
