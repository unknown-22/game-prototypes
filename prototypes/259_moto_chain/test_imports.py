"""test_imports.py — Headless logic tests for MOTO CHAIN."""

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/259_moto_chain")
from main import (
    BIKE_X,
    CLR_LIME,
    CLR_RED,
    CLR_WHITE,
    CLR_YELLOW,
    COMBINATION,
    COMBO_THRESHOLD,
    GAME_DURATION,
    GHOST_RECORD_INTERVAL,
    GRAVITY,
    HEAT_CRASH,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    JUMP_VELOCITY,
    MATCH_SCORE_BASE,
    MATCH_SCORE_SUPER_MULT,
    RING_RADIUS,
    SCROLL_SPEED_INITIAL,
    STUN_CRASH,
    STUN_MISMATCH,
    SUPER_MOTO_DURATION,
    FloatingText,
    Game,
    GhostDot,
    Particle,
    Phase,
    Ring,
)


def _make_game() -> Game:
    """Create a Game instance bypassing __init__ for headless testing."""
    g = Game.__new__(Game)
    # Pre-init ALL instance attributes before reset()
    g.phase = Phase.TITLE
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.timer = GAME_DURATION
    g.heat = 0.0
    g.bike_color_idx = 0
    g.bike_vy = 0.0
    g.bike_y = 180.0
    g.bike_grounded = True
    g.stun_timer = 0
    g.super_timer = 0
    g.scroll_x = 0.0
    g.scroll_speed = SCROLL_SPEED_INITIAL
    g.terrain_phase = 0.0
    g.rings = []
    g.particles = []
    g.ghost_dots = []
    g.best_ghost_dots = []
    g.floating_texts = []
    g.ring_spawn_timer = 0
    g.best_run = []
    g._rng = random.Random(42)
    g._headless = True
    g._frame_count = 0
    g.phase = Phase.PLAYING
    g._reset_playing()
    g._rng = random.Random(42)  # Re-seed after _reset_playing overwrites
    return g


# ============================================================
# Data Class Tests
# ============================================================


def test_ring_creation() -> None:
    r = Ring(x=100.0, y=150.0, color=CLR_RED)
    assert r.x == 100.0
    assert r.y == 150.0
    assert r.color == CLR_RED
    assert r.active is True


def test_particle_creation() -> None:
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=15, color=CLR_LIME)
    assert p.x == 50.0
    assert p.y == 60.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == CLR_LIME
    assert p.grav == 0.05


def test_ghost_dot_creation() -> None:
    gd = GhostDot(x=60.0, y=120.0)
    assert gd.x == 60.0
    assert gd.y == 120.0


def test_floating_text_creation() -> None:
    ft = FloatingText(x=100.0, y=80.0, text="+100", life=30, color=CLR_WHITE)
    assert ft.x == 100.0
    assert ft.y == 80.0
    assert ft.text == "+100"
    assert ft.life == 30
    assert ft.color == CLR_WHITE
    assert ft.vy == -1.5


# ============================================================
# Phase Enum Tests
# ============================================================


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.TITLE != Phase.PLAYING


# ============================================================
# Constants Tests
# ============================================================


def test_constants() -> None:
    assert len(COMBINATION) == 4
    assert COMBINATION[0] == CLR_RED  # 8
    assert COMBO_THRESHOLD == 4
    assert HEAT_MAX == 100.0
    assert SUPER_MOTO_DURATION == 300
    assert GAME_DURATION == 1800


# ============================================================
# Terrain Tests
# ============================================================


def test_get_ground_y_basic() -> None:
    g = _make_game()
    y = g._get_ground_y(0.0)
    assert 160.0 < y < 200.0


def test_get_ground_y_increases_with_scroll() -> None:
    g = _make_game()
    y1 = g._get_ground_y(0.0)
    y2 = g._get_ground_y(500.0)
    # Amplitude grows with scroll_x, so range should be wider
    assert y1 != y2


# ============================================================
# Ring Collision Tests
# ============================================================


def test_check_ring_collision_hit() -> None:
    g = _make_game()
    g.bike_y = 150.0
    ring = Ring(x=BIKE_X, y=150.0, color=CLR_RED)
    assert g._check_ring_collision(ring) is True


def test_check_ring_collision_miss_far() -> None:
    g = _make_game()
    g.bike_y = 50.0
    ring = Ring(x=BIKE_X, y=150.0, color=CLR_RED)
    assert g._check_ring_collision(ring) is False


def test_check_ring_collision_edge() -> None:
    g = _make_game()
    g.bike_y = 150.0
    # Place ring RING_RADIUS - 1 away (just inside radius)
    ring = Ring(x=BIKE_X, y=150.0 - (RING_RADIUS - 1), color=CLR_RED)
    assert g._check_ring_collision(ring) is True


def test_check_ring_collision_just_outside() -> None:
    g = _make_game()
    g.bike_y = 150.0
    ring = Ring(x=BIKE_X, y=150.0 - (RING_RADIUS + 1), color=CLR_RED)
    assert g._check_ring_collision(ring) is False


# ============================================================
# Ring Spawn Tests
# ============================================================


def test_spawn_ring() -> None:
    g = _make_game()
    assert len(g.rings) == 0
    g._spawn_ring()
    assert len(g.rings) == 1
    ring = g.rings[0]
    assert ring.x > g.scroll_x
    assert 20.0 <= ring.y <= 220.0
    assert ring.color in COMBINATION
    assert ring.active is True


# ============================================================
# Bike Physics Tests
# ============================================================


def test_update_bike_gravity() -> None:
    g = _make_game()
    g.bike_grounded = False
    g.bike_vy = 0.0
    g.bike_y = 100.0
    g._update_bike()
    assert g.bike_vy == GRAVITY  # gravity applied
    assert g.bike_y == 100.0 + GRAVITY


def test_update_bike_grounded() -> None:
    g = _make_game()
    ground_y = g._get_ground_y(g.scroll_x + BIKE_X) - 12
    g.bike_y = ground_y
    g.bike_vy = 0.0
    g.bike_grounded = True
    g._update_bike()
    assert g.bike_y == ground_y  # stays on ground
    assert g.bike_vy == 0.0


def test_update_bike_hard_landing_crash() -> None:
    g = _make_game()
    ground_y = g._get_ground_y(g.scroll_x + BIKE_X) - 12
    g.bike_y = ground_y - 3.0  # close enough to reach ground in one frame
    g.bike_vy = 5.0  # fast falling
    g.bike_grounded = False
    g._update_bike()
    # Should trigger crash (heat increased, combo reset, stun applied)
    assert g.heat >= HEAT_CRASH
    assert g.combo == 0
    assert g.stun_timer >= STUN_CRASH


def test_try_jump() -> None:
    g = _make_game()
    g.bike_grounded = True
    g.stun_timer = 0
    g._try_jump()
    assert g.bike_vy == JUMP_VELOCITY
    assert g.bike_grounded is False


def test_try_jump_stunned() -> None:
    g = _make_game()
    g.bike_grounded = True
    g.stun_timer = 10
    g._try_jump()
    assert g.bike_vy == 0.0  # no jump when stunned
    assert g.bike_grounded is True


def test_try_jump_not_grounded() -> None:
    g = _make_game()
    g.bike_grounded = False
    g.stun_timer = 0
    g._try_jump()
    assert g.bike_vy == 0.0  # no jump in air


# ============================================================
# SUPER MOTO Auto-Throttle Tests
# ============================================================


def test_super_moto_auto_jump() -> None:
    g = _make_game()
    g.super_timer = 100
    ground_y = g._get_ground_y(g.scroll_x + BIKE_X) - 12
    g.bike_y = ground_y  # exactly at ground
    g.bike_grounded = True
    g.stun_timer = 0
    g.bike_vy = 0.0
    g._update_bike()
    # After auto-jump sets vy=-7.5, gravity is applied: -7.5 + 0.4 = -7.1
    assert g.bike_vy == JUMP_VELOCITY + GRAVITY
    assert g.bike_grounded is False


def test_super_moto_no_auto_jump_when_stunned() -> None:
    g = _make_game()
    g.super_timer = 100
    ground_y = g._get_ground_y(g.scroll_x + BIKE_X) - 12
    g.bike_y = ground_y  # exactly at ground
    g.bike_grounded = True
    g.stun_timer = 10
    g.bike_vy = 0.0
    g._update_bike()
    # No auto-jump because stunned, gravity pushes down but landing clamps back
    assert g.bike_vy == 0.0  # clamped to ground
    assert g.bike_grounded is True  # still on ground
    assert g.stun_timer == 9  # decremented


# ============================================================
# Ring Update Tests (Combo Logic)
# ============================================================


def test_update_rings_move_left() -> None:
    g = _make_game()
    g.rings.append(Ring(x=200.0, y=100.0, color=CLR_RED))
    g._update_rings()
    assert g.rings[0].x == 200.0 - SCROLL_SPEED_INITIAL


def test_update_rings_remove_offscreen() -> None:
    g = _make_game()
    g.rings.append(Ring(x=g.scroll_x - RING_RADIUS - 1, y=100.0, color=CLR_RED))
    g._update_rings()
    assert len(g.rings) == 0


def test_update_rings_match_success() -> None:
    g = _make_game()
    g.bike_y = 100.0
    g.bike_color_idx = 0  # RED
    g._frame_count = 0
    ring = Ring(x=BIKE_X, y=100.0, color=CLR_RED)  # same color as bike
    g.rings = [ring]
    g.combo = 0
    g.score = 0
    g._update_rings()
    assert ring.active is False
    assert g.combo >= 1
    assert g.score > 0


def test_update_rings_match_fail() -> None:
    g = _make_game()
    g.bike_y = 100.0
    g.bike_color_idx = 0  # RED
    g._frame_count = 0
    ring = Ring(x=BIKE_X, y=100.0, color=CLR_LIME)  # different color
    g.rings = [ring]
    g.combo = 3
    g.heat = 0.0
    g._update_rings()
    assert g.combo == 0
    assert g.heat >= HEAT_MISMATCH
    assert g.stun_timer >= STUN_MISMATCH


def test_update_rings_super_mode_any_color() -> None:
    g = _make_game()
    g.bike_y = 100.0
    g.bike_color_idx = 0  # RED
    g.super_timer = 100
    ring = Ring(x=BIKE_X, y=100.0, color=CLR_LIME)  # different color, but SUPER matches any
    g.rings = [ring]
    g.combo = 0
    g.score = 0
    g._update_rings()
    assert ring.active is False
    assert g.combo >= 1
    assert g.score > 0
    # Should get SUPER multiplier
    assert g.score >= MATCH_SCORE_BASE * MATCH_SCORE_SUPER_MULT


# ============================================================
# Combo Chain Tests
# ============================================================


def test_match_success_increments_combo() -> None:
    g = _make_game()
    ring = Ring(x=100.0, y=100.0, color=CLR_RED)
    g.combo = 2
    g.max_combo = 2
    g.score = 0
    g._on_match_success(ring)
    assert g.combo == 3
    assert g.max_combo == 3
    assert g.score > 0


def test_match_success_triggers_super() -> None:
    g = _make_game()
    ring = Ring(x=100.0, y=100.0, color=CLR_RED)
    g.combo = COMBO_THRESHOLD - 1  # 3
    g.super_timer = 0
    g._on_match_success(ring)
    assert g.combo == COMBO_THRESHOLD
    assert g.super_timer == SUPER_MOTO_DURATION
    assert len(g.particles) >= 20  # SUPER particle burst


def test_match_success_super_multiplier() -> None:
    g = _make_game()
    ring = Ring(x=100.0, y=100.0, color=CLR_RED)
    g.super_timer = 100
    g.combo = 0
    g.score = 0
    g._on_match_success(ring)
    expected_min = MATCH_SCORE_BASE * MATCH_SCORE_SUPER_MULT
    assert g.score >= expected_min


def test_match_fail_resets_combo() -> None:
    g = _make_game()
    ring = Ring(x=100.0, y=100.0, color=CLR_RED)
    g.combo = 5
    g.heat = 0.0
    g.super_timer = 0
    g._on_match_fail(ring)
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH


def test_match_fail_during_super_does_not_add_heat() -> None:
    g = _make_game()
    ring = Ring(x=100.0, y=100.0, color=CLR_RED)
    g.combo = 5
    g.heat = 10.0
    g.super_timer = 100
    g._on_match_fail(ring)
    assert g.combo == 0
    assert g.heat == 10.0  # heat unchanged during SUPER


# ============================================================
# SUPER MOTO Tests
# ============================================================


def test_super_moto_duration() -> None:
    g = _make_game()
    g.super_timer = SUPER_MOTO_DURATION
    g._frame_count = 0
    # Simulate update cycle
    g.super_timer -= 1
    assert g.super_timer == SUPER_MOTO_DURATION - 1


def test_super_moto_expires() -> None:
    g = _make_game()
    g.super_timer = 1
    g._frame_count = 0
    g.super_timer -= 1
    assert g.super_timer == 0


def test_trigger_super_moto() -> None:
    g = _make_game()
    g.super_timer = 0
    g.bike_y = 100.0
    g._trigger_super_moto()
    assert g.super_timer == SUPER_MOTO_DURATION
    assert len(g.particles) >= 20


# ============================================================
# Heat Tests
# ============================================================


def test_update_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g.super_timer = 0
    g._update_heat()
    assert g.heat == max(0.0, 50.0 - HEAT_DECAY)


def test_update_heat_no_decay_during_super() -> None:
    g = _make_game()
    g.heat = 50.0
    g.super_timer = 100
    g._update_heat()
    assert g.heat == 50.0  # no decay during SUPER


def test_update_heat_floor_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_game_over() -> None:
    g = _make_game()
    g.heat = HEAT_MAX  # 100.0
    g.phase = Phase.PLAYING
    g.super_timer = 0
    g.timer = 100
    # Simulate _update_playing game-over check (before decay)
    assert g.heat >= HEAT_MAX
    # Should end game
    if g.heat >= HEAT_MAX:
        g._end_game()
    assert g.phase == Phase.GAME_OVER


# ============================================================
# Crash Tests
# ============================================================


def test_on_crash_adds_heat() -> None:
    g = _make_game()
    g.heat = 0.0
    g.combo = 3
    g.super_timer = 0
    g._on_crash()
    assert g.heat == HEAT_CRASH
    assert g.combo == 0
    assert g.stun_timer == STUN_CRASH


def test_on_crash_during_super_no_heat() -> None:
    g = _make_game()
    g.heat = 10.0
    g.combo = 3
    g.super_timer = 100
    g._on_crash()
    assert g.heat == 10.0  # heat unchanged during SUPER
    assert g.combo == 0
    assert g.stun_timer == STUN_CRASH


# ============================================================
# Particle Tests
# ============================================================


def test_spawn_particles_match() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 3, CLR_LIME, "match")
    assert len(g.particles) == 3
    for p in g.particles:
        assert p.color == CLR_LIME
        assert p.life == 15
        assert abs(p.vx) <= 1.0
        assert -2.0 <= p.vy <= -1.0


def test_spawn_particles_super() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 5, CLR_YELLOW, "super")
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color in COMBINATION  # rainbow colors
        assert p.life == 25
        assert p.grav == 0.03


def test_update_particles_lifecycle() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 2, CLR_WHITE, "match")
    assert len(g.particles) == 2
    # Life is 15, need to update 15+ times to remove
    for _ in range(16):
        g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_gravity() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 1, CLR_WHITE, "crash")
    p = g.particles[0]
    orig_vy = p.vy
    g._update_particles()
    assert p.vy == orig_vy + 0.1  # crash grav


# ============================================================
# Floating Text Tests
# ============================================================


def test_add_floating_text() -> None:
    g = _make_game()
    g._add_floating_text(100.0, 80.0, "+100", 30, CLR_WHITE)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "+100"
    assert ft.life == 30
    assert ft.color == CLR_WHITE


def test_update_floating_texts() -> None:
    g = _make_game()
    g._add_floating_text(100.0, 80.0, "test", 5, CLR_WHITE)
    ft = g.floating_texts[0]
    orig_y = ft.y
    g._update_floating_texts()
    assert ft.y == orig_y + (-1.5)  # floats upward
    assert ft.life == 4


def test_update_floating_texts_removes_expired() -> None:
    g = _make_game()
    g._add_floating_text(100.0, 80.0, "test", 1, CLR_WHITE)
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ============================================================
# Ghost Trail Tests
# ============================================================


def test_record_ghost_on_interval() -> None:
    g = _make_game()
    g._frame_count = GHOST_RECORD_INTERVAL  # exactly on interval
    g.bike_y = 120.0
    g._record_ghost()
    assert len(g.ghost_dots) == 1
    assert g.ghost_dots[0].x == BIKE_X
    assert g.ghost_dots[0].y == 120


def test_record_ghost_off_interval() -> None:
    g = _make_game()
    g._frame_count = 1  # not on interval
    g._record_ghost()
    assert len(g.ghost_dots) == 0


# ============================================================
# Scroll Tests
# ============================================================


def test_update_scroll() -> None:
    g = _make_game()
    orig_x = g.scroll_x
    g._update_scroll()
    assert g.scroll_x > orig_x
    assert g.scroll_speed >= SCROLL_SPEED_INITIAL


def test_scroll_speed_increases() -> None:
    g = _make_game()
    g.timer = GAME_DURATION // 2  # halfway
    g._update_scroll()
    # Speed should be between initial and max
    assert SCROLL_SPEED_INITIAL <= g.scroll_speed <= 5.0


# ============================================================
# Reset / State Init Tests
# ============================================================


def test_reset_playing_clears_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 5
    g.heat = 80.0
    g.rings = [Ring(x=100.0, y=100.0, color=CLR_RED)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=10, color=CLR_WHITE)]
    g.floating_texts = [FloatingText(x=0, y=0, text="x", life=5, color=CLR_WHITE)]
    g.ghost_dots = [GhostDot(x=0, y=0)]
    g._reset_playing()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert len(g.rings) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.ghost_dots) == 0
    assert g.timer == GAME_DURATION
    assert g.super_timer == 0
    assert g._frame_count == 0


# ============================================================
# End Game Tests
# ============================================================


def test_end_game_sets_phase() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 0
    g.phase = Phase.PLAYING
    g._end_game()
    assert g.phase == Phase.GAME_OVER


def test_end_game_updates_best_score() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 300
    g.phase = Phase.PLAYING
    g._end_game()
    assert g.best_score == 500


def test_end_game_keeps_best_score() -> None:
    g = _make_game()
    g.score = 200
    g.best_score = 300
    g.phase = Phase.PLAYING
    g._end_game()
    assert g.best_score == 300  # unchanged


def test_timer_game_over() -> None:
    g = _make_game()
    g.timer = 0
    g.phase = Phase.PLAYING
    if g.timer <= 0:
        g._end_game()
    assert g.phase == Phase.GAME_OVER


# ============================================================
# Bike Color Tests
# ============================================================


def test_get_bike_color_normal() -> None:
    g = _make_game()
    g.super_timer = 0
    g.bike_color_idx = 0
    g._frame_count = 0
    c = g._get_bike_color()
    assert c == COMBINATION[0]


def test_get_bike_color_super_mode() -> None:
    g = _make_game()
    g.super_timer = 100
    g._frame_count = 0
    c = g._get_bike_color()
    # In SUPER mode, color cycles through COMBINATION every 4 frames
    assert c in COMBINATION


# ============================================================
# Stun Timer Tests
# ============================================================


def test_stun_decrements() -> None:
    g = _make_game()
    g.stun_timer = 10
    g.bike_grounded = True
    g._update_bike()
    assert g.stun_timer == 9


# ============================================================
# Integration Tests
# ============================================================


def test_full_combo_to_super_flow() -> None:
    """Test: 3 matching rings → COMBO=3 → 4th triggers SUPER MOTO."""
    g = _make_game()
    g.bike_y = 100.0
    g._frame_count = 0
    g.super_timer = 0
    g.combo = 0
    g.score = 0

    for i in range(3):
        ring = Ring(x=BIKE_X, y=100.0, color=CLR_RED)
        g.rings = [ring]
        g._update_rings()
    assert g.combo == 3
    assert g.super_timer == 0  # not yet triggered

    # 4th match triggers SUPER
    ring4 = Ring(x=BIKE_X, y=100.0, color=CLR_RED)
    g.rings = [ring4]
    g._update_rings()
    assert g.combo == COMBO_THRESHOLD
    assert g.super_timer == SUPER_MOTO_DURATION


def test_mismatch_breaks_combo() -> None:
    """Test: 2 matches → mismatch → combo reset."""
    g = _make_game()
    g.bike_y = 100.0
    g._frame_count = 0
    g.combo = 0
    g.heat = 0.0

    # 2 matches
    for _ in range(2):
        ring = Ring(x=BIKE_X, y=100.0, color=CLR_RED)
        g.rings = [ring]
        g._update_rings()
    assert g.combo == 2

    # mismatch
    ring_bad = Ring(x=BIKE_X, y=100.0, color=CLR_LIME)
    g.rings = [ring_bad]
    g._update_rings()
    assert g.combo == 0
    assert g.heat >= HEAT_MISMATCH


def test_super_mode_prevents_heat_gain() -> None:
    """Test: mismatch during SUPER doesn't increase heat."""
    g = _make_game()
    g.bike_y = 100.0
    g._frame_count = 0
    g.super_timer = 100
    g.heat = 10.0

    ring = Ring(x=BIKE_X, y=100.0, color=CLR_LIME)
    g.rings = [ring]
    g._update_rings()
    assert g.heat == 10.0  # no change
    assert g.combo >= 1  # SUPER matches any color


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
