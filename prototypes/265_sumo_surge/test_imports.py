"""test_imports.py — Headless logic tests for SUMO SURGE."""

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/265_sumo_surge")
from main import (
    Game, Wrestler, PowerZone, Particle, FloatingText, Phase,
    SCREEN_W, SCREEN_H, RING_CX, RING_CY, RING_RADIUS,
    WRESTLER_RADIUS, ZONE_RADIUS, MAX_ZONES,
    PLAYER_COLORS, COLOR_NAMES,
    SUPER_THRESHOLD, SUPER_DURATION, SUPER_FORCE_MULT,
    COLOR_CYCLE_FRAMES, ZONE_SPAWN_INTERVAL_START, ZONE_LIFE,
    HEAT_MISMATCH, HEAT_PUSHED_OUT, HEAT_DECAY, HEAT_CAP,
    OVERHEAT_DURATION, GAME_TIMER, WIN_THRESHOLD, ROUND_END_DURATION,
    RED, WHITE,
)


def _make_game() -> Game:
    """Create a Game instance bypassing pyxel init."""
    g = Game.__new__(Game)
    # Pre-init ALL instance attributes that _init_state() sets
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.player = Wrestler(x=0, y=0)
    g.ai = Wrestler(x=0, y=0)
    g.zones = []
    g.particles = []
    g.floating_texts = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.player_ringouts = 0
    g.ai_ringouts = 0
    g.heat = 0.0
    g.overheat_timer = 0
    g.super_timer = 0
    g.color_timer = COLOR_CYCLE_FRAMES
    g.ai_color_timer = COLOR_CYCLE_FRAMES  # Actually AI_COLOR_CYCLE_FRAMES=25
    g.timer = GAME_TIMER
    g.zone_spawn_timer = ZONE_SPAWN_INTERVAL_START
    g.zone_spawn_interval = ZONE_SPAWN_INTERVAL_START
    g.zone_spawn_speedup_counter = 0
    g.shake_frames = 0
    g.best_score = 0
    g.round_end_timer = 0
    g._init_state()
    g._rng = random.Random(42)  # Reseed after _init_state
    return g


# ── Data Class Tests ──

def test_wrestler_defaults() -> None:
    w = Wrestler(x=100.0, y=200.0)
    assert w.x == 100.0
    assert w.y == 200.0
    assert w.vx == 0.0
    assert w.vy == 0.0
    assert w.radius == WRESTLER_RADIUS
    assert w.color_idx == 0
    assert w.push_force == 1.0
    assert w.stunned == 0


def test_wrestler_custom() -> None:
    w = Wrestler(x=50.0, y=60.0, color_idx=2, push_force=3.5, stunned=10)
    assert w.color_idx == 2
    assert w.push_force == 3.5
    assert w.stunned == 10


def test_power_zone() -> None:
    z = PowerZone(x=100.0, y=200.0, color_idx=1)
    assert z.x == 100.0
    assert z.y == 200.0
    assert z.color_idx == 1
    assert z.life == ZONE_LIFE
    assert z.radius == ZONE_RADIUS


def test_particle() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=RED)
    assert p.life == 15
    assert p.color == RED
    assert p.size == 2


def test_floating_text() -> None:
    ft = FloatingText(x=50.0, y=60.0, text="TEST", life=30, color=WHITE)
    assert ft.text == "TEST"
    assert ft.life == 30
    assert ft.color == WHITE


# ── Phase tests ──

def test_init_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.player_ringouts == 0
    assert g.ai_ringouts == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.timer == GAME_TIMER


def test_reset_preserves_best_score() -> None:
    g = _make_game()
    g.best_score = 500
    g.score = 100
    g.reset()
    assert g.best_score == 500
    assert g.score == 0
    assert g.phase == Phase.TITLE


# ── Color cycle tests ──

def test_cycle_color_no_change_within_window() -> None:
    g = _make_game()
    g.player.color_idx = 0
    g.color_timer = COLOR_CYCLE_FRAMES
    g._cycle_color()
    assert g.player.color_idx == 0
    assert g.color_timer == COLOR_CYCLE_FRAMES - 1


def test_cycle_color_changes_at_zero() -> None:
    g = _make_game()
    g.player.color_idx = 0
    g.color_timer = 1
    g._cycle_color()
    assert g.player.color_idx == 1
    assert g.color_timer == COLOR_CYCLE_FRAMES


def test_cycle_color_wraps() -> None:
    g = _make_game()
    g.player.color_idx = 3
    g.color_timer = 1
    g._cycle_color()
    assert g.player.color_idx == 0


# ── Zone spawning tests ──

def test_spawn_zone_adds_one() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    initial = len(g.zones)
    g._spawn_zone()
    assert len(g.zones) == initial + 1


def test_spawn_zone_inside_ring() -> None:
    g = _make_game()
    g._rng = random.Random(99)
    for _ in range(10):
        g._spawn_zone()
    for z in g.zones:
        dist = math.hypot(z.x - RING_CX, z.y - RING_CY)
        assert dist <= RING_RADIUS - ZONE_RADIUS - 5


def test_spawn_zone_respects_max() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    # Fill up to MAX_ZONES
    for _ in range(MAX_ZONES):
        g._spawn_zone()
    assert len(g.zones) == MAX_ZONES
    g._spawn_zone()  # Should not add
    assert len(g.zones) == MAX_ZONES


def test_spawn_zone_not_too_close_to_wrestlers() -> None:
    g = _make_game()
    g.player.x = RING_CX
    g.player.y = RING_CY
    g.ai.x = RING_CX + 50
    g.ai.y = RING_CY
    g._rng = random.Random(7)
    for _ in range(10):
        g._spawn_zone()
    for z in g.zones:
        dp = math.hypot(z.x - g.player.x, z.y - g.player.y)
        da = math.hypot(z.x - g.ai.x, z.y - g.ai.y)
        min_dist = WRESTLER_RADIUS + ZONE_RADIUS + 4
        assert dp >= min_dist or da >= min_dist


# ── Zone update tests ──

def test_update_zones_decrements_life() -> None:
    g = _make_game()
    g.zones = [PowerZone(x=100.0, y=100.0, color_idx=0, life=10)]
    g._update_zones()
    assert g.zones[0].life == 9


def test_update_zones_removes_expired() -> None:
    g = _make_game()
    g.zones = [
        PowerZone(x=100.0, y=100.0, color_idx=0, life=1),
        PowerZone(x=120.0, y=120.0, color_idx=1, life=5),
    ]
    g._update_zones()
    assert len(g.zones) == 1
    assert g.zones[0].color_idx == 1


# ── Zone collision tests ──

def test_zone_collision_match_builds_combo() -> None:
    g = _make_game()
    g.player.x = 100.0
    g.player.y = 100.0
    g.player.color_idx = 0  # RED
    g.combo = 0
    g.heat = 10.0
    g.zones = [PowerZone(x=100.0, y=100.0, color_idx=0, life=50)]
    g._check_zone_collisions()
    assert g.combo == 1
    assert len(g.zones) == 0


def test_zone_collision_mismatch_resets_combo() -> None:
    g = _make_game()
    g.player.x = 100.0
    g.player.y = 100.0
    g.player.color_idx = 0  # RED
    g.combo = 3
    g.heat = 10.0
    g.zones = [PowerZone(x=100.0, y=100.0, color_idx=1, life=50)]  # LIME
    g._check_zone_collisions()
    assert g.combo == 0
    assert g.heat == 10.0 + HEAT_MISMATCH
    assert len(g.zones) == 0


def test_zone_collision_super_auto_matches() -> None:
    g = _make_game()
    g.player.x = 100.0
    g.player.y = 100.0
    g.player.color_idx = 0  # RED
    g.combo = 5
    g.super_timer = 100
    g.zones = [PowerZone(x=100.0, y=100.0, color_idx=2, life=50)]  # DARK_BLUE
    g._check_zone_collisions()
    # SUPER mode: auto-match regardless of color
    assert g.combo == 6
    assert len(g.zones) == 0


def test_zone_collision_no_overlap_ignores() -> None:
    g = _make_game()
    g.player.x = 0.0
    g.player.y = 0.0
    g.player.color_idx = 0
    g.combo = 0
    g.zones = [PowerZone(x=200.0, y=200.0, color_idx=0, life=50)]
    g._check_zone_collisions()
    assert len(g.zones) == 1
    assert g.combo == 0


# ── Push force tests ──

def test_push_force_normal() -> None:
    g = _make_game()
    g.combo = 3
    g.super_timer = 0
    g._update_push_force()
    expected = 1.0 + 3 * 0.3
    assert abs(g.player.push_force - expected) < 0.01


def test_push_force_super() -> None:
    g = _make_game()
    g.combo = 5
    g.super_timer = 100
    g._update_push_force()
    expected = (1.0 + 5 * 0.3) * SUPER_FORCE_MULT
    assert abs(g.player.push_force - expected) < 0.01


def test_push_force_zero_combo() -> None:
    g = _make_game()
    g.combo = 0
    g.super_timer = 0
    g._update_push_force()
    assert abs(g.player.push_force - 1.0) < 0.01


# ── Push mechanic tests ──

def test_check_push_when_overlapping() -> None:
    g = _make_game()
    g.player.x = 100.0
    g.player.y = 100.0
    g.player.push_force = 2.0
    g.ai.x = 120.0
    g.ai.y = 100.0
    g.ai.push_force = 1.0
    g._check_push()
    # Both wrestlers should have moved away from each other
    assert g.player.x != 100.0 or g.player.y != 100.0


def test_check_push_no_overlap() -> None:
    g = _make_game()
    g.player.x = 0.0
    g.player.y = 0.0
    g.ai.x = 200.0
    g.ai.y = 200.0
    orig_px, orig_py = g.player.x, g.player.y
    g._check_push()
    assert g.player.x == orig_px
    assert g.player.y == orig_py


def test_check_push_direction() -> None:
    """Player on left, AI on right; stronger player pushes AI right."""
    g = _make_game()
    g.player.x = 100.0
    g.player.y = 100.0
    g.player.push_force = 5.0
    g.ai.x = 120.0
    g.ai.y = 100.0
    g.ai.push_force = 0.5
    g._check_push()
    # Player with higher force should push AI away
    assert g.ai.x > 120.0  # AI pushed right


# ── Ring boundary tests ──

def test_ring_boundary_inside() -> None:
    g = _make_game()
    w = Wrestler(x=RING_CX, y=RING_CY)
    assert not g._check_ring_boundary(w)


def test_ring_boundary_outside() -> None:
    g = _make_game()
    w = Wrestler(x=RING_CX + RING_RADIUS + 10, y=RING_CY)
    assert g._check_ring_boundary(w)


def test_ring_boundary_at_edge() -> None:
    g = _make_game()
    w = Wrestler(x=RING_CX + RING_RADIUS, y=RING_CY)
    # Exactly at boundary: > means outside
    assert not g._check_ring_boundary(w)


# ── Ring-out tests ──

def test_ring_out_player_scores() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.ai.x = RING_CX + RING_RADIUS + 20  # AI outside ring
    g.ai.y = RING_CY
    g.player.x = RING_CX
    g.player.y = RING_CY
    g.combo = 3
    g._check_ring_out()
    assert g.player_ringouts == 1
    assert g.ai_ringouts == 0
    assert g.score == 100 + 3 * 10


def test_ring_out_player_gets_pushed() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = RING_CX + RING_RADIUS + 20  # Player outside ring
    g.player.y = RING_CY
    g.ai.x = RING_CX
    g.ai.y = RING_CY
    g.combo = 2
    g.heat = 30.0
    g._check_ring_out()
    assert g.ai_ringouts == 1
    assert g.player_ringouts == 0
    assert g.heat == min(HEAT_CAP, 30.0 + HEAT_PUSHED_OUT)
    assert g.combo == 0


def test_ring_out_both_outside_respawns() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player.x = RING_CX + RING_RADIUS + 20
    g.player.y = RING_CY
    g.ai.x = RING_CX + RING_RADIUS + 20
    g.ai.y = RING_CY
    g._check_ring_out()
    # Both respawn at center
    assert g.player_ringouts == 0
    assert g.ai_ringouts == 0
    assert math.hypot(g.player.x - RING_CX, g.player.y - RING_CY) < 10
    assert math.hypot(g.ai.x - RING_CX, g.ai.y - RING_CY) < 10


def test_ring_out_triggers_round_end_for_victory() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_ringouts = WIN_THRESHOLD - 1
    g.ai.x = RING_CX + RING_RADIUS + 20
    g.ai.y = RING_CY
    g._check_ring_out()
    assert g.phase == Phase.GAME_OVER


def test_ring_out_triggers_round_end_not_victory() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_ringouts = 0
    g.ai.x = RING_CX + RING_RADIUS + 20
    g.ai.y = RING_CY
    g.timer = 1000
    g._check_ring_out()
    assert g.phase == Phase.ROUND_END
    assert g.round_end_timer == ROUND_END_DURATION


# ── AI tests ──

def test_find_nearest_zone_finds_correct() -> None:
    g = _make_game()
    g.zones = [
        PowerZone(x=100.0, y=50.0, color_idx=0),
        PowerZone(x=150.0, y=50.0, color_idx=0),
        PowerZone(x=200.0, y=50.0, color_idx=1),
    ]
    result = g._find_nearest_zone(100.0, 40.0, 0)
    assert result is not None
    assert abs(result.x - 100.0) < 0.1
    assert abs(result.y - 50.0) < 0.1


def test_find_nearest_zone_returns_none_for_wrong_color() -> None:
    g = _make_game()
    g.zones = [
        PowerZone(x=100.0, y=50.0, color_idx=0),
        PowerZone(x=150.0, y=50.0, color_idx=2),
    ]
    result = g._find_nearest_zone(100.0, 40.0, 1)
    assert result is None


def test_find_nearest_zone_empty_list() -> None:
    g = _make_game()
    result = g._find_nearest_zone(100.0, 100.0, 0)
    assert result is None


def test_update_ai_moves_toward_zone() -> None:
    g = _make_game()
    g.ai.x = 100.0
    g.ai.y = 100.0
    g.ai.color_idx = 0
    g.player.x = 300.0  # Far away from AI (won't trigger push)
    g.player.y = 300.0
    g.zones = [PowerZone(x=150.0, y=100.0, color_idx=0, life=100)]
    g._update_ai()
    # AI should move toward the zone
    assert g.ai.x > 100.0  # Moved right


def test_update_ai_moves_toward_player_when_close() -> None:
    g = _make_game()
    g.ai.x = 100.0
    g.ai.y = 100.0
    g.player.x = 110.0
    g.player.y = 100.0
    g.zones = []
    g._update_ai()
    # AI should move toward player (within 40px)
    assert g.ai.x > 100.0


def test_update_ai_moves_to_center_when_near_edge() -> None:
    g = _make_game()
    # Place AI near edge
    g.ai.x = RING_CX + RING_RADIUS - 10
    g.ai.y = RING_CY
    g.player.x = RING_CX
    g.player.y = RING_CY
    g.zones = []
    g._update_ai()
    # AI should move toward center
    assert g.ai.x < RING_CX + RING_RADIUS - 10  # Moved left toward center


def test_update_ai_stunned_does_nothing() -> None:
    g = _make_game()
    g.ai.stunned = 5
    orig_x = g.ai.x
    orig_y = g.ai.y
    g._update_ai()
    assert g.ai.x == orig_x
    assert g.ai.y == orig_y
    assert g.ai.stunned == 4


# ── HEAT tests ──

def test_update_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g.overheat_timer = 0
    g._update_heat()
    assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.001


def test_update_heat_floor_at_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_triggers_overheat() -> None:
    g = _make_game()
    g.heat = 100.0
    g.overheat_timer = 0
    g._update_heat()
    assert g.overheat_timer == OVERHEAT_DURATION - 1  # decremented same frame
    assert g.heat == HEAT_CAP


def test_update_heat_overheat_cooldown() -> None:
    g = _make_game()
    g.heat = 80.0
    g.overheat_timer = 1
    g._update_heat()
    assert g.overheat_timer == 0
    assert g.heat == 50.0  # cooldown to 50, no decay this frame (entered overheat block)


# ── SUPER activation tests ──

def test_super_activation_at_threshold() -> None:
    g = _make_game()
    g.combo = SUPER_THRESHOLD
    g.super_timer = 0
    g._check_super_activation()
    assert g.super_timer == SUPER_DURATION


def test_super_activation_below_threshold() -> None:
    g = _make_game()
    g.combo = SUPER_THRESHOLD - 1
    g.super_timer = 0
    g._check_super_activation()
    assert g.super_timer == 0


def test_super_activation_no_double_trigger() -> None:
    g = _make_game()
    g.combo = 10
    g.super_timer = 200  # Already active
    g._check_super_activation()
    assert g.super_timer == 200  # Not reset


# ── Score computation tests ──

def test_compute_score() -> None:
    g = _make_game()
    g.player_ringouts = 2
    g.max_combo = 7
    g.timer = 1500
    expected = 2 * 100 + 7 * 10 + (1500 // 30)
    assert g.compute_score() == expected


def test_compute_score_zero() -> None:
    g = _make_game()
    g.player_ringouts = 0
    g.max_combo = 0
    g.timer = 0
    assert g.compute_score() == 0


# ── Clamp to ring tests ──

def test_clamp_to_ring_inside() -> None:
    g = _make_game()
    w = Wrestler(x=RING_CX, y=RING_CY)
    g._clamp_to_ring(w)
    assert w.x == RING_CX
    assert w.y == RING_CY


def test_clamp_to_ring_outside() -> None:
    g = _make_game()
    w = Wrestler(x=RING_CX + RING_RADIUS + 50, y=RING_CY)
    g._clamp_to_ring(w)
    dist = math.hypot(w.x - RING_CX, w.y - RING_CY)
    assert abs(dist - (RING_RADIUS - w.radius)) < 0.1


def test_clamp_to_ring_corner_outside() -> None:
    g = _make_game()
    w = Wrestler(x=RING_CX + 200, y=RING_CY + 200)
    g._clamp_to_ring(w)
    dist = math.hypot(w.x - RING_CX, w.y - RING_CY)
    assert abs(dist - (RING_RADIUS - w.radius)) < 0.1


# ── Reset round tests ──

def test_reset_round() -> None:
    g = _make_game()
    g.combo = 5
    g.zones = [PowerZone(x=100.0, y=100.0, color_idx=0)]
    g._reset_round()
    assert g.phase == Phase.PLAYING
    assert g.combo == 0
    assert len(g.zones) == 0
    assert abs(g.player.x - RING_CX) < 1 and abs(g.player.y - (RING_CY + 30)) < 1
    assert abs(g.ai.x - RING_CX) < 1 and abs(g.ai.y - (RING_CY - 30)) < 1


# ── Particle tests ──

def test_update_particles_decrements_life() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_particles_zone(100.0, 100.0, 5, RED)
    assert len(g.particles) == 5
    g._update_particles()
    for p in g.particles:
        assert p.life < 30  # was decremented


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0


# ── Floating text tests ──

def test_update_floating_texts_decrements_life() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="TEST", life=5, color=WHITE)]
    g._update_floating_texts()
    assert g.floating_texts[0].life == 4


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="TEST", life=1, color=WHITE)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Constants tests ──

def test_player_colors_count() -> None:
    assert len(PLAYER_COLORS) == 4
    assert len(COLOR_NAMES) == 4


def test_constants_reasonable() -> None:
    assert SUPER_THRESHOLD == 4
    assert SUPER_DURATION == 300
    assert GAME_TIMER == 1800
    assert WIN_THRESHOLD == 3
    assert MAX_ZONES == 6


def test_ring_constants() -> None:
    assert RING_CX == 160
    assert RING_CY == 130
    assert RING_RADIUS == 90
    assert SCREEN_W == 320
    assert SCREEN_H == 240


if __name__ == "__main__":
    import traceback

    tests = [
        ("test_wrestler_defaults", test_wrestler_defaults),
        ("test_wrestler_custom", test_wrestler_custom),
        ("test_power_zone", test_power_zone),
        ("test_particle", test_particle),
        ("test_floating_text", test_floating_text),
        ("test_init_state", test_init_state),
        ("test_reset_preserves_best_score", test_reset_preserves_best_score),
        ("test_cycle_color_no_change_within_window", test_cycle_color_no_change_within_window),
        ("test_cycle_color_changes_at_zero", test_cycle_color_changes_at_zero),
        ("test_cycle_color_wraps", test_cycle_color_wraps),
        ("test_spawn_zone_adds_one", test_spawn_zone_adds_one),
        ("test_spawn_zone_inside_ring", test_spawn_zone_inside_ring),
        ("test_spawn_zone_respects_max", test_spawn_zone_respects_max),
        ("test_spawn_zone_not_too_close_to_wrestlers", test_spawn_zone_not_too_close_to_wrestlers),
        ("test_update_zones_decrements_life", test_update_zones_decrements_life),
        ("test_update_zones_removes_expired", test_update_zones_removes_expired),
        ("test_zone_collision_match_builds_combo", test_zone_collision_match_builds_combo),
        ("test_zone_collision_mismatch_resets_combo", test_zone_collision_mismatch_resets_combo),
        ("test_zone_collision_super_auto_matches", test_zone_collision_super_auto_matches),
        ("test_zone_collision_no_overlap_ignores", test_zone_collision_no_overlap_ignores),
        ("test_push_force_normal", test_push_force_normal),
        ("test_push_force_super", test_push_force_super),
        ("test_push_force_zero_combo", test_push_force_zero_combo),
        ("test_check_push_when_overlapping", test_check_push_when_overlapping),
        ("test_check_push_no_overlap", test_check_push_no_overlap),
        ("test_check_push_direction", test_check_push_direction),
        ("test_ring_boundary_inside", test_ring_boundary_inside),
        ("test_ring_boundary_outside", test_ring_boundary_outside),
        ("test_ring_boundary_at_edge", test_ring_boundary_at_edge),
        ("test_ring_out_player_scores", test_ring_out_player_scores),
        ("test_ring_out_player_gets_pushed", test_ring_out_player_gets_pushed),
        ("test_ring_out_both_outside_respawns", test_ring_out_both_outside_respawns),
        ("test_ring_out_triggers_round_end_for_victory", test_ring_out_triggers_round_end_for_victory),
        ("test_ring_out_triggers_round_end_not_victory", test_ring_out_triggers_round_end_not_victory),
        ("test_find_nearest_zone_finds_correct", test_find_nearest_zone_finds_correct),
        ("test_find_nearest_zone_returns_none_for_wrong_color", test_find_nearest_zone_returns_none_for_wrong_color),
        ("test_find_nearest_zone_empty_list", test_find_nearest_zone_empty_list),
        ("test_update_ai_moves_toward_zone", test_update_ai_moves_toward_zone),
        ("test_update_ai_moves_toward_player_when_close", test_update_ai_moves_toward_player_when_close),
        ("test_update_ai_moves_to_center_when_near_edge", test_update_ai_moves_to_center_when_near_edge),
        ("test_update_ai_stunned_does_nothing", test_update_ai_stunned_does_nothing),
        ("test_update_heat_decay", test_update_heat_decay),
        ("test_update_heat_floor_at_zero", test_update_heat_floor_at_zero),
        ("test_update_heat_triggers_overheat", test_update_heat_triggers_overheat),
        ("test_update_heat_overheat_cooldown", test_update_heat_overheat_cooldown),
        ("test_super_activation_at_threshold", test_super_activation_at_threshold),
        ("test_super_activation_below_threshold", test_super_activation_below_threshold),
        ("test_super_activation_no_double_trigger", test_super_activation_no_double_trigger),
        ("test_compute_score", test_compute_score),
        ("test_compute_score_zero", test_compute_score_zero),
        ("test_clamp_to_ring_inside", test_clamp_to_ring_inside),
        ("test_clamp_to_ring_outside", test_clamp_to_ring_outside),
        ("test_clamp_to_ring_corner_outside", test_clamp_to_ring_corner_outside),
        ("test_reset_round", test_reset_round),
        ("test_update_particles_decrements_life", test_update_particles_decrements_life),
        ("test_update_particles_removes_dead", test_update_particles_removes_dead),
        ("test_update_floating_texts_decrements_life", test_update_floating_texts_decrements_life),
        ("test_update_floating_texts_removes_dead", test_update_floating_texts_removes_dead),
        ("test_player_colors_count", test_player_colors_count),
        ("test_constants_reasonable", test_constants_reasonable),
        ("test_ring_constants", test_ring_constants),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception:
            print(f"FAIL: {name}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    if failed > 0:
        sys.exit(1)
