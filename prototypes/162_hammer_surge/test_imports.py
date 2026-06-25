"""test_imports.py — Headless logic tests for Hammer Surge."""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # type: ignore[import-not-found]
    COMBO_SUPER_THRESHOLD,
    GHOST_TRAIL_COLORS,
    GHOST_TRAIL_COUNT,
    HAMMER_SPEED_MAX,
    HAMMER_SPEED_MIN,
    HEAT_DECAY,
    HEAT_PER_MISS,
    MAX_HEAT,
    MAX_THROWS,
    POWER_BUILD_RATE,
    RESULT_DURATION,
    SCREEN_H,
    SCREEN_W,
    SUPER_DURATION,
    THROWER_X,
    THROWER_Y,
    ZONE_COLORS,
    ZONE_H,
    ZONE_W,
    ZONE_X,
    ZONE_Y,
    FloatingText,
    Game,
    Particle,
    Phase,
    ThrowRecord,
)


def _make_game() -> Game:
    """Create a fresh game for testing."""
    g = Game(rng=random.Random(42))
    g.reset()
    return g


# ── Initialization ──


def test_game_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.throw_count == MAX_THROWS
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.hammer_active is False
    assert g.hammer_color == 0


def test_start_game_transitions_to_powering():
    g = _make_game()
    g.start_game()
    assert g.phase == Phase.POWERING
    assert g.score == 0
    assert g.throw_count == MAX_THROWS


# ── Power Building ──


def test_build_power_increments():
    g = _make_game()
    g.spin_power = 0.0
    p = g._build_power()
    assert p == POWER_BUILD_RATE
    p = g._build_power()
    assert p == POWER_BUILD_RATE * 2


def test_build_power_caps_at_1():
    g = _make_game()
    g.spin_power = 0.99
    p = g._build_power()
    assert p == min(1.0, 0.99 + POWER_BUILD_RATE)


def test_reset_power():
    g = _make_game()
    g.spin_power = 0.8
    g._reset_power()
    assert g.spin_power == 0.0


# ── Throw Mechanics ──


def test_throw_hammer_sets_active():
    g = _make_game()
    g._throw_hammer(0.0, 0.5)
    assert g.hammer_active is True
    assert g.hammer_x == THROWER_X
    assert g.hammer_y == THROWER_Y
    assert g.spin_power == 0.0  # power reset after throw


def test_throw_hammer_speed_range():
    g = _make_game()
    # min power
    g._throw_hammer(0.0, 0.0)
    speed_min = math.hypot(g.hammer_vx, g.hammer_vy)
    assert abs(speed_min - HAMMER_SPEED_MIN) < 0.001

    # max power
    g._throw_hammer(0.0, 1.0)
    speed_max = math.hypot(g.hammer_vx, g.hammer_vy)
    assert abs(speed_max - HAMMER_SPEED_MAX) < 0.001


def test_throw_hammer_direction():
    g = _make_game()
    g._throw_hammer(0.0, 1.0)
    # angle 0 → vx positive, vy near 0
    assert g.hammer_vx > 0
    assert abs(g.hammer_vy) < 0.001

    g._throw_hammer(math.pi / 4, 1.0)
    assert g.hammer_vx > 0
    assert g.hammer_vy > 0

    g._throw_hammer(-math.pi / 4, 1.0)
    assert g.hammer_vx > 0
    assert g.hammer_vy < 0


def test_update_hammer_flying():
    g = _make_game()
    g.hammer_active = True
    g.hammer_x = float(THROWER_X)
    g.hammer_y = float(THROWER_Y)
    g.hammer_vx = 6.0
    g.hammer_vy = 2.0
    result = g._update_hammer()
    assert result is True
    assert g.hammer_x == THROWER_X + 6.0
    assert g.hammer_y == THROWER_Y + 2.0


def test_update_hammer_lands():
    g = _make_game()
    g.hammer_active = True
    g.hammer_x = ZONE_X - 1.0
    g.hammer_y = 100.0
    g.hammer_vx = 6.0
    g.hammer_vy = 2.0
    result = g._update_hammer()
    assert result is False
    assert g.hammer_x >= ZONE_X


def test_update_hammer_inactive():
    g = _make_game()
    assert g._update_hammer() is False


# ── Zone Computation ──


def test_compute_zone_index():
    g = _make_game()
    assert g._compute_zone_index(45) == 0  # zone 0: 20-70
    assert g._compute_zone_index(95) == 1  # zone 1: 70-120
    assert g._compute_zone_index(145) == 2  # zone 2: 120-170
    assert g._compute_zone_index(195) == 3  # zone 3: 170-220


def test_compute_zone_index_boundaries():
    g = _make_game()
    assert g._compute_zone_index(69.9) == 0
    assert g._compute_zone_index(70.0) == 1
    assert g._compute_zone_index(119.9) == 1
    assert g._compute_zone_index(120.0) == 2


def test_compute_zone_index_edge_cases():
    g = _make_game()
    # below zone 0
    assert g._compute_zone_index(5.0) == 0
    # above zone 3
    assert g._compute_zone_index(300.0) == 3


def test_compute_landing_y():
    g = _make_game()
    # angle 0 → landing_y = THROWER_Y
    ly = g._compute_landing_y(0.0)
    assert ly == THROWER_Y

    # positive angle → landing below center
    ly = g._compute_landing_y(0.5)
    assert ly > THROWER_Y

    # negative angle → landing above center
    ly = g._compute_landing_y(-0.5)
    assert ly < THROWER_Y


# ── Landing Check ──


def test_check_landing_matched():
    g = _make_game()
    g.hammer_color = 0  # RED → zone 0
    zi, matched = g._check_landing(ZONE_X, 45)  # zone 0
    assert zi == 0
    assert matched is True


def test_check_landing_missed():
    g = _make_game()
    g.hammer_color = 0  # RED → zone 0
    zi, matched = g._check_landing(ZONE_X, 95)  # zone 1 (GREEN)
    assert zi == 1
    assert matched is False


def test_check_landing_super_mode_auto_match():
    g = _make_game()
    g.super_mode = True
    g.hammer_color = 0  # RED
    # should auto-match regardless of zone
    zi, matched = g._check_landing(ZONE_X, 95)  # zone 1 (GREEN)
    assert zi == 1
    assert matched is True


# ── Apply Result (Match) ──


def test_apply_result_matched():
    g = _make_game()
    g.score = 0
    g.combo = 0
    g.super_mode = False
    g.hammer_color = 0
    g.hammer_x = ZONE_X
    g.hammer_y = 45.0
    g._apply_result(True)
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score > 0
    assert g.hammer_color == 1  # advanced


def test_apply_result_combo_chain():
    g = _make_game()
    g.combo = 2
    g.max_combo = 2
    g.hammer_color = 0
    g.hammer_x = ZONE_X
    g.hammer_y = 45.0
    g._apply_result(True)
    assert g.combo == 3
    assert g.max_combo == 3
    assert g.score > 0


def test_apply_result_score_multiplier():
    g = _make_game()
    g.combo = 2
    g.hammer_color = 0
    g.hammer_x = ZONE_X
    g.hammer_y = 45.0
    g._apply_result(True)
    # combo 2→3, multiplier = 1.0 + 3*0.25 = 1.75, base = 100, score = 175
    assert g.score == 175  # int(100 * 1.75) = 175


# ── Apply Result (Miss) ──


def test_apply_result_missed():
    g = _make_game()
    g.combo = 3
    g.super_mode = False
    g.heat = 10.0
    g.hammer_color = 0
    g.hammer_x = ZONE_X
    g.hammer_y = 95.0
    g._apply_result(False)
    assert g.combo == 0
    assert g.heat == 10.0 + HEAT_PER_MISS
    assert g.hammer_color == 1  # advanced


def test_apply_result_miss_deactivates_super():
    g = _make_game()
    g.combo = 4
    g.super_mode = True
    g.super_timer = 100
    g.hammer_color = 0
    g.hammer_x = ZONE_X
    g.hammer_y = 95.0
    g._apply_result(False)
    assert g.combo == 0
    assert g.super_mode is False
    assert g.super_timer == 0


def test_apply_result_hammer_color_cycles():
    g = _make_game()
    g.hammer_color = 3
    g.hammer_x = ZONE_X
    g.hammer_y = 45.0
    g._apply_result(True)
    assert g.hammer_color == 0  # 3→0


# ── Heat System ──


def test_update_heat_decay():
    g = _make_game()
    g.heat = 50.0
    result = g._update_heat()
    assert result is False
    assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.001


def test_update_heat_floor():
    g = _make_game()
    g.heat = HEAT_DECAY / 2
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_game_over():
    g = _make_game()
    g.phase = Phase.POWERING
    g.heat = MAX_HEAT  # exactly at max
    result = g._update_heat()
    assert result is True
    assert g.phase == Phase.GAME_OVER


def test_heat_capped_at_max():
    g = _make_game()
    g.heat = 90.0
    g.hammer_x = ZONE_X
    g.hammer_y = 95.0
    g.hammer_color = 0
    g._apply_result(False)
    assert g.heat == min(90.0 + HEAT_PER_MISS, MAX_HEAT)


# ── Super Mode ──


def test_check_super_activation_below_threshold():
    g = _make_game()
    g.combo = 3
    g.super_mode = False
    g._check_super_activation()
    assert g.super_mode is False


def test_check_super_activation_at_threshold():
    g = _make_game()
    g.combo = COMBO_SUPER_THRESHOLD
    g.super_mode = False
    g._check_super_activation()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION
    assert g.shake_frames > 0


def test_check_super_activation_already_active():
    g = _make_game()
    g.combo = 5
    g.super_mode = True
    g.super_timer = 100
    g._check_super_activation()
    assert g.super_timer == 100  # unchanged


def test_update_super_decrements():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 5
    g._update_super()
    assert g.super_timer == 4


def test_update_super_ends():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_timer == 0
    assert g.super_mode is False


def test_update_super_not_active():
    g = _make_game()
    g.super_mode = False
    g.super_timer = 0
    g._update_super()
    assert g.super_mode is False


# ── Score Multiplier ──


def test_get_score_multiplier_no_combo():
    g = _make_game()
    g.combo = 0
    assert g._get_score_multiplier() == 1.0


def test_get_score_multiplier_with_combo():
    g = _make_game()
    g.combo = 4
    assert g._get_score_multiplier() == 1.0 + 4 * 0.25  # 2.0


def test_get_score_multiplier_super_mode():
    g = _make_game()
    g.combo = 1
    g.super_mode = True
    assert g._get_score_multiplier() == 3.0


def test_compute_score_matched():
    g = _make_game()
    g.combo = 2
    # multiplier = 1.0 + 2*0.25 = 1.5, base=100 → 150
    assert g._compute_score(100, True) == 150


def test_compute_score_missed():
    g = _make_game()
    assert g._compute_score(100, False) == 0


# ── Phase Flow ──


def test_advance_from_result_normal():
    g = _make_game()
    g.phase = Phase.RESULT
    g.throw_count = 10
    g.heat = 30.0
    g._advance_from_result()
    assert g.phase == Phase.POWERING
    assert g.throw_count == 9


def test_advance_from_result_game_over_heat():
    g = _make_game()
    g.phase = Phase.RESULT
    g.throw_count = 10
    g.heat = MAX_HEAT
    g._advance_from_result()
    assert g.phase == Phase.GAME_OVER


def test_advance_from_result_game_over_throws():
    g = _make_game()
    g.phase = Phase.RESULT
    g.throw_count = 1
    g.heat = 30.0
    g._advance_from_result()
    assert g.phase == Phase.GAME_OVER
    assert g.throw_count == 0


# ── Ghost Trails ──


def test_record_throw():
    g = _make_game()
    g.hammer_color = 1
    g._record_throw(0.3, 0.7, True)
    assert len(g.ghost_trails) == 1
    rec = g.ghost_trails[0]
    assert rec.angle == 0.3
    assert rec.power == 0.7
    assert rec.color == 1
    assert rec.matched is True


def test_record_throw_limits_count():
    g = _make_game()
    for i in range(5):
        g.hammer_color = i % 4
        g._record_throw(float(i) * 0.1, 0.5, True)
    assert len(g.ghost_trails) == GHOST_TRAIL_COUNT  # 3


def test_record_throw_fifo_order():
    g = _make_game()
    g._record_throw(0.1, 0.5, True)
    g.hammer_color = 1
    g._record_throw(0.2, 0.6, True)
    g.hammer_color = 2
    g._record_throw(0.3, 0.7, True)
    g.hammer_color = 3
    g._record_throw(0.4, 0.8, True)
    assert len(g.ghost_trails) == 3
    # oldest (0.1) removed, newest 3: 0.2, 0.3, 0.4
    assert g.ghost_trails[0].angle == 0.2
    assert g.ghost_trails[2].angle == 0.4


# ── Particles ──


def test_spawn_particles():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 8, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == 8


def test_spawn_super_particles():
    g = _make_game()
    g._spawn_super_particles()
    assert len(g.particles) == 30


def test_update_particles():
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=1.0, vy=-1.0, life=2, color=8),
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=0, color=8),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    p = g.particles[0]
    assert p.x == 1.0
    assert p.y == -1.0
    assert p.vy == -0.9  # gravity applied
    assert p.life == 1


# ── Floating Texts ──


def test_spawn_floating_text():
    g = _make_game()
    g._spawn_floating_text(100.0, 100.0, "TEST", 7, 10)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"


def test_update_floating_texts():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=0.0, y=0.0, text="A", life=1, color=7),
        FloatingText(x=0.0, y=0.0, text="B", life=3, color=7),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "B"
    assert abs(ft.y - (-0.8)) < 0.001
    assert ft.life == 2


# ── Reset ──


def test_reset_clears_all():
    g = _make_game()
    g.score = 500
    g.combo = 5
    g.max_combo = 7
    g.heat = 80.0
    g.throw_count = 3
    g.super_mode = True
    g.super_timer = 100
    g.hammer_active = True
    g.hammer_color = 3
    g.ghost_trails = [ThrowRecord(0.1, 0.5, 0, True)]
    g.particles = [Particle(0, 0, 0, 0, 5, 8)]
    g.floating_texts = [FloatingText(0, 0, "T", 5, 7)]
    g.shake_frames = 5

    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.throw_count == MAX_THROWS
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.hammer_active is False
    assert g.hammer_color == 0
    assert g.ghost_trails == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g.shake_frames == 0


# ── Full Throw Flow Simulation ──


def test_full_throw_flow_match():
    """Simulate a complete throw: build power, throw, land, apply result."""
    g = _make_game()
    g.start_game()

    # Build power
    for _ in range(30):
        g._build_power()
    power = g.spin_power
    assert power > 0.5

    # Throw at angle that lands in zone 0 (RED, matching hammer_color=0)
    # zone 0: y 20-70, need angle = atan((y-120)/80) → about -0.9 to -0.6
    angle = -0.7
    g._throw_hammer(angle, power)
    g.phase = Phase.FLYING
    assert g.hammer_active is True

    # Fly until landing
    while g._update_hammer():
        pass
    assert g.hammer_x >= ZONE_X

    # Check landing
    zi, matched = g._check_landing(g.hammer_x, g.hammer_y)
    g._record_throw(angle, power, matched)
    g._apply_result(matched)
    g.hammer_active = False
    g.phase = Phase.RESULT

    assert matched is True, f"Expected matched=True, zone={zi}, color={g.hammer_color}"
    assert g.score > 0
    assert len(g.ghost_trails) == 1


def test_full_throw_flow_miss():
    """Simulate a throw that misses the matching zone."""
    g = _make_game()
    g.start_game()
    g.hammer_color = 0  # RED, zone 0 at y=45

    # Aim for zone 3 (YELLOW, y=195)
    angle = 1.0  # positive angle → downward
    g.spin_angle = angle

    for _ in range(20):
        g._build_power()

    g._throw_hammer(angle, g.spin_power)
    g.phase = Phase.FLYING

    while g._update_hammer():
        pass

    zi, matched = g._check_landing(g.hammer_x, g.hammer_y)
    # With large positive angle, hammer lands in lower zone, not zone 0
    g._apply_result(matched)

    if zi != 0:
        assert matched is False
        assert g.combo == 0
        assert g.heat == HEAT_PER_MISS


# ── Super Mode Full Flow ──


def test_super_mode_activation_via_apply_result():
    """Build combo to threshold and verify super mode activates."""
    g = _make_game()
    g.start_game()
    g.combo = 3
    g.max_combo = 3
    g.hammer_x = ZONE_X
    g.hammer_y = 45.0  # zone 0
    g.hammer_color = 0  # matches zone 0

    g._apply_result(True)
    assert g.combo == COMBO_SUPER_THRESHOLD
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_mode_score_multiplier():
    g = _make_game()
    g.super_mode = True
    g.combo = 4
    g.hammer_x = ZONE_X
    g.hammer_y = 95.0  # zone 1
    g.hammer_color = 0  # mismatched, but super auto-matches

    g._apply_result(True)  # super auto-match
    # multiplier = 3.0, base = 100, score = 300
    assert g.score >= 300


# ── Constants ──


def test_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert THROWER_X == 160
    assert THROWER_Y == 120
    assert ZONE_X == 240
    assert ZONE_W == 60
    assert ZONE_H == 50
    assert len(ZONE_Y) == 4
    assert len(ZONE_COLORS) == 4
    assert len(GHOST_TRAIL_COLORS) == 4
    assert MAX_THROWS == 15
    assert MAX_HEAT == 100.0
    assert HEAT_PER_MISS == 15.0
    assert COMBO_SUPER_THRESHOLD == 4
    assert SUPER_DURATION == 300
    assert RESULT_DURATION == 60
    assert GHOST_TRAIL_COUNT == 3


# ── Data Class Fields ──


def test_throw_record_fields():
    rec = ThrowRecord(angle=0.5, power=0.8, color=2, matched=True, landing_y=150.0)
    assert rec.angle == 0.5
    assert rec.power == 0.8
    assert rec.color == 2
    assert rec.matched is True
    assert rec.landing_y == 150.0


def test_particle_fields():
    p = Particle(x=1.5, y=2.5, vx=0.5, vy=-0.5, life=10, color=8)
    assert p.x == 1.5
    assert p.life == 10


def test_floating_text_fields():
    ft = FloatingText(x=100.0, y=50.0, text="COMBO", life=30, color=10)
    assert ft.text == "COMBO"
    assert ft.life == 30


# ── Edge Cases ──


def test_throw_at_full_power_caps():
    g = _make_game()
    g._throw_hammer(0.0, 2.0)  # overloaded power value
    speed = math.hypot(g.hammer_vx, g.hammer_vy)
    assert speed <= HAMMER_SPEED_MAX


def test_throw_at_zero_power_still_moves():
    g = _make_game()
    g._throw_hammer(0.0, -0.5)  # negative power
    speed = math.hypot(g.hammer_vx, g.hammer_vy)
    assert speed >= HAMMER_SPEED_MIN


def test_heat_decay_at_game_over_boundary():
    """Heat decay should still happen but game over checked separately."""
    g = _make_game()
    g.phase = Phase.POWERING
    g.heat = MAX_HEAT  # already at max
    result = g._update_heat()
    assert result is True  # game over triggered


def test_throw_count_game_over():
    g = _make_game()
    g.phase = Phase.RESULT
    g.throw_count = 1
    g.heat = 0.0
    g._advance_from_result()
    assert g.phase == Phase.GAME_OVER
    assert g.throw_count == 0


def test_ghost_trails_empty_initially():
    g = _make_game()
    assert len(g.ghost_trails) == 0


def test_combo_max_tracking():
    g = _make_game()
    g.combo = 3
    g.max_combo = 3
    g.hammer_x = ZONE_X
    g.hammer_y = 45.0
    g.hammer_color = 0

    g._apply_result(True)
    assert g.combo == 4
    assert g.max_combo == 4

    g._apply_result(False)
    assert g.combo == 0
    assert g.max_combo == 4  # max persists


# ── Run ──

if __name__ == "__main__":
    import inspect as _inspect

    _tests = [
        obj
        for _name, obj in _inspect.getmembers(sys.modules[__name__])
        if callable(obj) and _name.startswith("test_")
    ]
    passed = 0
    failed = 0
    for _test in _tests:
        try:
            _test()
            print(f"  ✅ {_test.__name__}")
            passed += 1
        except Exception as _e:
            print(f"  ❌ {_test.__name__}: {_e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(_tests)} total")
    if failed > 0:
        sys.exit(1)
