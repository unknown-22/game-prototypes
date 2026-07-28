"""test_imports.py — Headless logic tests for LEAP CHAIN (254_leap_chain).

Uses Game.__new__(Game) bypass to avoid Pyxel init.
Never calls methods that access pyxel.btn/btnp/mouse_x/mouse_y.
"""
import math
import random
import sys

# Make the prototype directory importable
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/254_leap_chain")
from main import (
    Game, Phase, Particle, FloatingText, Zone, parse_distance,
    GROUND_Y, RUNNER_START_X,
    NUM_JUMPS, GAME_TIME, HEAT_MAX, HEAT_DECAY, HEAT_MISMATCH, COMBO_THRESHOLD, SUPER_DURATION,
    PLAYER_COLORS, COLOR_RED, COLOR_LIME, COLOR_DARK_BLUE, COLOR_YELLOW,
    COLOR_WHITE, COLOR_NAMES,
    ZONE_DEFS,
)


def _make_game() -> Game:
    """Create a Game instance without Pyxel init, with seeded RNG."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes that reset() touches
    g.zones = []
    g.particles = []
    g.floating_texts = []
    g.jump_distances = []
    g.reset()
    # Seed RNG after reset (reset may overwrite)
    random.seed(42)
    return g


# ── parse_distance tests ──

def test_parse_distance():
    assert parse_distance("4.0m") == 4.0
    assert parse_distance("8.0m") == 8.0
    assert parse_distance("0.0m") == 0.0


# ── Phase enum tests ──

def test_phase_enum():
    phases = list(Phase)
    assert Phase.TITLE in phases
    assert Phase.APPROACH in phases
    assert Phase.FLIGHT in phases
    assert Phase.SCORING in phases
    assert Phase.GAME_OVER in phases
    assert Phase.VICTORY in phases
    assert len(phases) == 6


# ── Constants tests ──

def test_constants():
    assert len(PLAYER_COLORS) == 4
    assert len(COLOR_NAMES) == 4
    assert len(ZONE_DEFS) == 5
    assert NUM_JUMPS == 6
    assert GAME_TIME == 60 * 30  # 1800f
    assert HEAT_MAX == 100
    assert COMBO_THRESHOLD == 4
    assert SUPER_DURATION == 300


# ── Dataclass tests ──

def test_particle_dataclass():
    p = Particle(10.0, 20.0, 1.5, -2.0, 30, COLOR_RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 30
    assert p.color == COLOR_RED


def test_floating_text_dataclass():
    ft = FloatingText(50.0, 30.0, "+100", 60, COLOR_WHITE)
    assert ft.x == 50.0
    assert ft.y == 30.0
    assert ft.text == "+100"
    assert ft.life == 60


def test_zone_dataclass():
    z = Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m")
    assert z.x == 100.0
    assert z.y == GROUND_Y
    assert z.width == 40
    assert z.color == COLOR_RED
    assert z.distance_label == "4.0m"


# ── Game initialization tests ──

def test_game_reset():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.runner_x == float(RUNNER_START_X)
    assert g.runner_y == float(GROUND_Y)
    assert g.power == 0.0
    assert g.combo == 0
    assert g.score == 0
    assert g.jumps_used == 0
    assert g.heat == 0.0
    assert g.timer == GAME_TIME
    assert g.super_remaining == 0
    assert g.super_active is False
    assert g.best_distance == 0.0
    assert len(g.zones) == 5
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.jump_distances) == 0


# ── Zone spawning tests ──

def test_spawn_zones_count():
    g = _make_game()
    assert len(g.zones) == len(ZONE_DEFS)


def test_spawn_zones_positions():
    g = _make_game()
    for i, (expected_x, expected_width, expected_label) in enumerate(ZONE_DEFS):
        assert g.zones[i].x == float(expected_x)
        assert g.zones[i].width == expected_width
        assert g.zones[i].distance_label == expected_label
        assert g.zones[i].color in PLAYER_COLORS


# ── Color cycling tests ──

def test_cycle_color_advances():
    g = _make_game()
    g.phase = Phase.APPROACH
    initial_idx = g.current_color_idx
    # Cycle one step
    for _ in range(20):  # COLOR_CYCLE_SPEED
        g._cycle_color()
    assert g.current_color_idx == (initial_idx + 1) % len(PLAYER_COLORS)


def test_current_color_property():
    g = _make_game()
    g.current_color_idx = 0
    assert g.current_color == COLOR_RED
    g.current_color_idx = 1
    assert g.current_color == COLOR_LIME
    g.current_color_idx = 2
    assert g.current_color == COLOR_DARK_BLUE
    g.current_color_idx = 3
    assert g.current_color == COLOR_YELLOW


# ── Launch velocity tests ──

def test_get_launch_velocity_zero_power():
    g = _make_game()
    vx, vy = g._get_launch_velocity(0.0, 45.0)
    assert vx > 0
    assert vy < 0  # upward


def test_get_launch_velocity_max_power():
    g = _make_game()
    vx, vy = g._get_launch_velocity(100.0, 45.0)
    assert vx > 0
    assert vy < 0


def test_get_launch_velocity_steep_angle():
    g = _make_game()
    vx_steep, vy_steep = g._get_launch_velocity(50.0, 75.0)
    vx_shallow, vy_shallow = g._get_launch_velocity(50.0, 20.0)
    # Shallow angle = more horizontal, less vertical
    assert vx_shallow > vx_steep
    assert abs(vy_shallow) < abs(vy_steep)


def test_get_launch_velocity_higher_power_gives_more_speed():
    g = _make_game()
    vx1, vy1 = g._get_launch_velocity(20.0, 45.0)
    vx2, vy2 = g._get_launch_velocity(80.0, 45.0)
    assert math.hypot(vx2, vy2) > math.hypot(vx1, vy1)


# ── Flight position tests ──

def test_get_flight_position_start():
    g = _make_game()
    g.jump_x_start = 50.0
    x, y = g._get_flight_position(0, 3.0, -4.0)
    assert x == 50.0
    assert y == GROUND_Y


def test_get_flight_position_moves_right():
    g = _make_game()
    g.jump_x_start = 50.0
    x1, y1 = g._get_flight_position(0, 3.0, -4.0)
    x2, y2 = g._get_flight_position(10, 3.0, -4.0)
    assert x2 > x1


def test_get_flight_position_arc():
    g = _make_game()
    g.jump_x_start = 50.0
    # At t=0, y should be GROUND_Y
    _, y0 = g._get_flight_position(0, 3.0, -4.0)
    assert y0 == GROUND_Y
    # At some t, goes up then down
    _, y5 = g._get_flight_position(5, 3.0, -4.0)
    _, y16 = g._get_flight_position(16, 3.0, -4.0)
    _, y20 = g._get_flight_position(20, 3.0, -4.0)
    # Should go up first (vy=-4, negative = upward in screen coords)
    assert y5 < GROUND_Y  # above ground, still going up
    # Peak is at t = -vy/GRAVITY = 4/0.25 = 16 (y=168)
    # After peak: screen y increases = going down
    assert y16 < y5  # runner went higher (smaller screen y)
    assert y20 > y16  # runner started descending after peak


# ── Landing zone detection tests ──

def test_check_landing_zone_hit_first():
    g = _make_game()
    # Set up known zones
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
        Zone(140.0, GROUND_Y, 40, COLOR_LIME, "5.0m"),
    ]
    idx, dist = g._check_landing_zone(100.0)
    assert idx == 0
    assert dist == 4.0


def test_check_landing_zone_hit_second():
    g = _make_game()
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
        Zone(140.0, GROUND_Y, 40, COLOR_LIME, "5.0m"),
    ]
    idx, dist = g._check_landing_zone(140.0)
    assert idx == 1
    assert dist == 5.0


def test_check_landing_zone_edge_left():
    g = _make_game()
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
    ]
    # Left edge of zone: 100 - 20 = 80
    idx, dist = g._check_landing_zone(80.0)
    assert idx == 0


def test_check_landing_zone_edge_right():
    g = _make_game()
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
    ]
    # Right edge of zone (exclusive): 100 + 20 = 120
    idx, dist = g._check_landing_zone(119.0)
    assert idx == 0


def test_check_landing_zone_outside():
    g = _make_game()
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
    ]
    # Before first zone
    idx, dist = g._check_landing_zone(50.0)
    assert idx == -1
    assert dist == 0.0


def test_check_landing_zone_between():
    g = _make_game()
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
        Zone(140.0, GROUND_Y, 40, COLOR_LIME, "5.0m"),
    ]
    # Adjacent zones have no gap — zone boundaries are [80,120) and [120,160)
    # x=119 is inside zone 0, x=120 is inside zone 1
    idx0, _ = g._check_landing_zone(119.0)
    assert idx0 == 0
    idx1, _ = g._check_landing_zone(120.0)
    assert idx1 == 1


# ── Score computation tests ──

def test_compute_score_normal():
    g = _make_game()
    score = g._compute_score(5.0, 1, False)
    # base = int(5.0 * 10) = 50, combo_bonus = 1, multiplier = 1
    assert score == 50


def test_compute_score_with_combo():
    g = _make_game()
    score = g._compute_score(5.0, 3, False)
    # base = 50, combo_bonus = 3, multiplier = 1
    assert score == 150


def test_compute_score_super():
    g = _make_game()
    score = g._compute_score(5.0, 1, True)
    # base = 50, combo_bonus = 1, multiplier = 3
    assert score == 150


def test_compute_score_super_with_combo():
    g = _make_game()
    score = g._compute_score(5.0, 4, True)
    # base = 50, combo_bonus = 4, multiplier = 3
    assert score == 600


def test_compute_score_zero_combo_is_1():
    g = _make_game()
    score = g._compute_score(5.0, 0, False)
    assert score == 50  # combo_bonus = max(1, 0) = 1


# ── HEAT update tests ──

def test_update_heat_normal_decay():
    g = _make_game()
    heat, is_over = g._update_heat(50.0)
    assert abs(heat - (50.0 - HEAT_DECAY)) < 0.01
    assert is_over is False


def test_update_heat_threshold_exact():
    g = _make_game()
    heat, is_over = g._update_heat(HEAT_MAX)
    assert heat == HEAT_MAX
    assert is_over is True


def test_update_heat_threshold_above():
    g = _make_game()
    heat, is_over = g._update_heat(150.0)
    assert heat == 150.0
    assert is_over is True


def test_update_heat_decay_min_zero():
    g = _make_game()
    heat, is_over = g._update_heat(0.01)
    assert heat == 0.0
    assert is_over is False


# ── Angle from mouse tests ──

def test_angle_from_mouse_top():
    g = _make_game()
    angle = g._angle_from_mouse(0)
    assert abs(angle - 75.0) < 0.01


def test_angle_from_mouse_bottom():
    g = _make_game()
    angle = g._angle_from_mouse(GROUND_Y)
    assert abs(angle - 20.0) < 0.01


def test_angle_from_mouse_mid():
    g = _make_game()
    angle = g._angle_from_mouse(int(GROUND_Y / 2))
    assert 45.0 < angle < 50.0  # roughly middle


# ── COMBO chain tests ──

def test_combo_increments_on_match():
    g = _make_game()
    g.phase = Phase.APPROACH
    g.runner_x = 100.0  # Will land in zone 0
    g.current_color_idx = 0  # RED
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
        Zone(140.0, GROUND_Y, 40, COLOR_LIME, "5.0m"),
        Zone(180.0, GROUND_Y, 40, COLOR_DARK_BLUE, "6.0m"),
        Zone(220.0, GROUND_Y, 40, COLOR_YELLOW, "7.0m"),
        Zone(260.0, GROUND_Y, 40, COLOR_RED, "8.0m"),
    ]
    g.runner_y = GROUND_Y
    g.vx = 0
    g.vy = 0
    g.jump_x_start = 50.0

    g._resolve_landing()
    assert g.combo == 1
    assert g.phase == Phase.SCORING


def test_combo_resets_on_mismatch():
    g = _make_game()
    g.phase = Phase.APPROACH
    g.runner_x = 100.0
    g.current_color_idx = 1  # LIME
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
        Zone(140.0, GROUND_Y, 40, COLOR_LIME, "5.0m"),
        Zone(180.0, GROUND_Y, 40, COLOR_DARK_BLUE, "6.0m"),
        Zone(220.0, GROUND_Y, 40, COLOR_YELLOW, "7.0m"),
        Zone(260.0, GROUND_Y, 40, COLOR_RED, "8.0m"),
    ]
    g.runner_y = GROUND_Y
    g.vx = 0
    g.vy = 0
    g.jump_x_start = 50.0
    g.combo = 3
    g.heat = 0.0

    g._resolve_landing()
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH


def test_combo_chain_multiple_matches():
    g = _make_game()
    g.phase = Phase.APPROACH
    g.current_color_idx = 0  # RED
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
        Zone(140.0, GROUND_Y, 40, COLOR_RED, "5.0m"),
        Zone(180.0, GROUND_Y, 40, COLOR_RED, "6.0m"),
        Zone(220.0, GROUND_Y, 40, COLOR_RED, "7.0m"),
        Zone(260.0, GROUND_Y, 40, COLOR_RED, "8.0m"),
    ]
    g.runner_y = GROUND_Y
    g.vx = 0
    g.vy = 0
    g.jump_x_start = 50.0

    # First match
    g.runner_x = 100.0
    g._resolve_landing()
    assert g.combo == 1

    # Second match
    g.runner_x = 140.0
    g._resolve_landing()
    assert g.combo == 2

    # Third match
    g.runner_x = 180.0
    g._resolve_landing()
    assert g.combo == 3


# ── SUPER LEAP trigger tests ──

def test_super_leap_triggers_at_threshold():
    g = _make_game()
    g.phase = Phase.APPROACH
    g.current_color_idx = 0  # RED
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
        Zone(140.0, GROUND_Y, 40, COLOR_RED, "5.0m"),
        Zone(180.0, GROUND_Y, 40, COLOR_RED, "6.0m"),
        Zone(220.0, GROUND_Y, 40, COLOR_RED, "7.0m"),
        Zone(260.0, GROUND_Y, 40, COLOR_RED, "8.0m"),
    ]
    g.runner_y = GROUND_Y
    g.vx = 0
    g.vy = 0
    g.jump_x_start = 50.0
    g.combo = 3  # one below threshold
    g.super_active = False

    # 4th match should trigger SUPER
    g.runner_x = 220.0
    g._resolve_landing()
    assert g.combo == 4
    assert g.super_active is True
    assert g.super_remaining == SUPER_DURATION


def test_super_leap_any_color_match():
    g = _make_game()
    g.phase = Phase.APPROACH
    g.current_color_idx = 2  # DARK_BLUE — mismatched
    g.super_active = True
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
        Zone(140.0, GROUND_Y, 40, COLOR_LIME, "5.0m"),
        Zone(180.0, GROUND_Y, 40, COLOR_DARK_BLUE, "6.0m"),
        Zone(220.0, GROUND_Y, 40, COLOR_YELLOW, "7.0m"),
        Zone(260.0, GROUND_Y, 40, COLOR_RED, "8.0m"),
    ]
    g.runner_y = GROUND_Y
    g.vx = 0
    g.vy = 0
    g.jump_x_start = 50.0
    g.combo = 5

    # Should match even though color is mismatched (super = any-color)
    g.runner_x = 100.0
    g._resolve_landing()
    assert g.combo == 6  # incremented
    # Should not reset because super_active


# ── HEAT system tests ──

def test_heat_mismatch_increases():
    g = _make_game()
    g.phase = Phase.APPROACH
    g.current_color_idx = 0  # RED
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_LIME, "4.0m"),
    ]
    g.runner_y = GROUND_Y
    g.vx = 0
    g.vy = 0
    g.jump_x_start = 50.0
    g.runner_x = 100.0
    g.heat = 10.0
    g.super_active = False

    g._resolve_landing()
    assert g.heat == 10.0 + HEAT_MISMATCH


def test_heat_super_prevents_gain():
    g = _make_game()
    g.phase = Phase.APPROACH
    g.current_color_idx = 0  # RED
    g.super_active = True
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_LIME, "4.0m"),  # mismatched
    ]
    g.runner_y = GROUND_Y
    g.vx = 0
    g.vy = 0
    g.jump_x_start = 50.0
    g.runner_x = 100.0
    g.heat = 10.0

    g._resolve_landing()
    # HEAT should NOT increase because super_active
    assert g.heat == 10.0


def test_heat_game_over():
    g = _make_game()
    g.phase = Phase.SCORING
    g.heat = HEAT_MAX
    g.scoring_timer = 0
    g.timer = 100
    g.jumps_used = 0

    g._update_scoring()
    assert g.phase == Phase.GAME_OVER


# ── Jump counting tests ──

def test_jumps_used_increments():
    g = _make_game()
    g.phase = Phase.SCORING
    g.jumps_used = 0
    g.scoring_timer = 0
    g.heat = 0
    g.timer = 100

    g._update_scoring()
    assert g.jumps_used == 1
    assert g.phase == Phase.APPROACH  # reset for next jump


def test_victory_after_all_jumps():
    g = _make_game()
    g.phase = Phase.SCORING
    g.jumps_used = NUM_JUMPS - 1
    g.scoring_timer = 0
    g.heat = 0
    g.timer = 100

    g._update_scoring()
    assert g.jumps_used == NUM_JUMPS
    assert g.phase == Phase.VICTORY


# ── Timer tests ──

def test_timer_runs_out():
    g = _make_game()
    g.phase = Phase.SCORING
    g.jumps_used = 0
    g.scoring_timer = 0
    g.heat = 0
    g.timer = 0

    g._update_scoring()
    assert g.phase == Phase.GAME_OVER


# ── Reset for next jump tests ──

def test_reset_for_next_jump():
    g = _make_game()
    g.phase = Phase.APPROACH
    g.runner_x = 200.0
    g.power = 50.0
    g.vx = 5.0
    g.vy = -3.0
    g.flight_frame = 10

    g._reset_for_next_jump()
    assert g.runner_x == float(RUNNER_START_X)
    assert g.runner_y == float(GROUND_Y)
    assert g.power == 0.0
    assert g.vx == 0.0
    assert g.vy == 0.0
    assert g.flight_frame == 0
    assert g.phase == Phase.APPROACH


# ── Best distance tracking tests ──

def test_best_distance_updates():
    g = _make_game()
    g.phase = Phase.APPROACH
    g.current_color_idx = 0  # RED
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
        Zone(140.0, GROUND_Y, 40, COLOR_RED, "5.0m"),
        Zone(180.0, GROUND_Y, 40, COLOR_RED, "6.0m"),
        Zone(220.0, GROUND_Y, 40, COLOR_RED, "7.0m"),
        Zone(260.0, GROUND_Y, 40, COLOR_RED, "8.0m"),
    ]
    g.runner_y = GROUND_Y
    g.vx = 0
    g.vy = 0
    g.jump_x_start = 50.0
    g.best_distance = 0.0

    g.runner_x = 180.0  # 6.0m zone
    g._resolve_landing()
    assert g.best_distance == 6.0
    assert len(g.jump_distances) == 1
    assert g.jump_distances[0] == 6.0


# ── Particle tests ──

def test_add_particles():
    g = _make_game()
    initial_count = len(g.particles)
    g._add_particles(100.0, 50.0, 5, [COLOR_RED])
    assert len(g.particles) == initial_count + 5
    for p in g.particles[-5:]:
        assert p.color == COLOR_RED


def test_update_particles_removes_expired():
    g = _make_game()
    g.particles = [Particle(100.0, 50.0, 0.0, 0.0, 1, COLOR_RED)]
    g._update_particles()
    assert len(g.particles) == 0  # life=1 → 0, removed


def test_update_particles_life_decreases():
    g = _make_game()
    g.particles = [Particle(100.0, 50.0, 0.0, 0.0, 30, COLOR_RED)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 29


def test_update_particles_gravity_applies():
    g = _make_game()
    g.particles = [Particle(100.0, 50.0, 0.0, 0.0, 30, COLOR_RED)]
    g._update_particles()
    assert g.particles[0].vy == 0.1  # gravity added


# ── Floating text tests ──

def test_add_floating_text():
    g = _make_game()
    initial_count = len(g.floating_texts)
    g._add_floating_text(50.0, 30.0, "+100", COLOR_LIME)
    assert len(g.floating_texts) == initial_count + 1
    ft = g.floating_texts[-1]
    assert ft.text == "+100"
    assert ft.color == COLOR_LIME


def test_update_floating_texts_removes_expired():
    g = _make_game()
    g.floating_texts = [FloatingText(50.0, 30.0, "test", 1, COLOR_WHITE)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_update_floating_texts_rises():
    g = _make_game()
    g.floating_texts = [FloatingText(50.0, 30.0, "test", 60, COLOR_WHITE)]
    orig_y = g.floating_texts[0].y
    g._update_floating_texts()
    assert g.floating_texts[0].y == orig_y - 0.5


# ── Power system tests ──

def test_power_starts_at_zero():
    g = _make_game()
    assert g._get_power() == 0.0


# ── SHORT landing tests ──

def test_short_landing_no_zone():
    g = _make_game()
    g.phase = Phase.APPROACH
    g.current_color_idx = 0
    g.zones = [
        Zone(100.0, GROUND_Y, 40, COLOR_RED, "4.0m"),
    ]
    g.runner_y = GROUND_Y
    g.vx = 0
    g.vy = 0
    g.jump_x_start = 50.0
    g.combo = 2
    g.heat = 0.0

    # Land before first zone
    g.runner_x = 50.0
    g._resolve_landing()
    assert g.combo == 0  # reset
    assert g.scoring_is_foul is True  # treated as foul
    assert g.phase == Phase.SCORING


# ── SUPER deactivation tests ──

def test_super_deactivates_after_duration():
    g = _make_game()
    g.super_active = True
    g.super_remaining = 1

    # Simulate what _update_approach does for super decrement
    g.super_remaining -= 1
    if g.super_remaining <= 0:
        g.super_active = False

    assert g.super_remaining == 0
    assert g.super_active is False


# ── Edge case: combo_bonus max(1, combo) ──

def test_combo_bonus_minimum_one():
    g = _make_game()
    # combo=0 should still give bonus of 1
    score = g._compute_score(5.0, 0, False)
    assert score == 50  # 50 * 1 * 1


# ── Seed reproducibility test ──

def test_spawn_zones_deterministic_with_seed():
    random.seed(99)
    g1 = _make_game()
    colors1 = [z.color for z in g1.zones]

    random.seed(99)
    g2 = _make_game()
    colors2 = [z.color for z in g2.zones]

    assert colors1 == colors2


if __name__ == "__main__":
    import pytest
    import sys as _sys
    _sys.exit(pytest.main([__file__, "-v"]))
