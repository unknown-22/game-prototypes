"""test_imports.py — Headless logic tests for 189_sumo_surge."""
import math
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/189_sumo_surge")
from main import (
    BLACK, BROWN, WHITE, RED, GREEN, DARK_BLUE, YELLOW, ORANGE, CYAN, PINK, LIME, GRAY,
    WRESTLER_RADIUS, RING_CX, RING_CY, RING_RADIUS,
    COLORS, SUPER_COLORS,
    CHARGE_FORCE_BASE, HEAT_MISMATCH, HEAT_MAX, HEAT_DECAY,
    SUPER_DURATION, CHARGE_COOLDOWN, COLOR_CYCLE_SPEED,
    Particle, FloatingText, Phase, Game,
)


def _make_game() -> Game:
    """Factory for headless Game instances."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes that reset() touches
    g.particles = []
    g.floating_texts = []
    g.reset()
    return g


# ── Ring Boundary ──

def test_is_in_ring_center() -> None:
    g = _make_game()
    assert g._is_in_ring(RING_CX, RING_CY) is True


def test_is_in_ring_edge() -> None:
    g = _make_game()
    assert g._is_in_ring(RING_CX + RING_RADIUS - 1, RING_CY) is True
    assert g._is_in_ring(RING_CX + RING_RADIUS, RING_CY) is True


def test_is_in_ring_outside() -> None:
    g = _make_game()
    assert g._is_in_ring(RING_CX + RING_RADIUS + 1, RING_CY) is False
    assert g._is_in_ring(RING_CX, RING_CY + RING_RADIUS + 10) is False


def test_clamp_to_ring_inside() -> None:
    g = _make_game()
    cx, cy = g._clamp_to_ring(RING_CX, RING_CY)
    assert abs(cx - RING_CX) < 0.01
    assert abs(cy - RING_CY) < 0.01


def test_clamp_to_ring_outside() -> None:
    g = _make_game()
    far_x = RING_CX + RING_RADIUS + 50
    far_y = RING_CY
    cx, cy = g._clamp_to_ring(far_x, far_y)
    dist = math.hypot(cx - RING_CX, cy - RING_CY)
    assert abs(dist - (RING_RADIUS - WRESTLER_RADIUS)) < 1.0


def test_clamp_to_ring_same_point() -> None:
    """Clamping (RING_CX, RING_CY) returns same point."""
    g = _make_game()
    cx, cy = g._clamp_to_ring(RING_CX, RING_CY)
    assert cx == RING_CX
    assert cy == RING_CY


# ── Distance ──

def test_distance() -> None:
    g = _make_game()
    assert g._distance(0, 0, 3, 4) == 5.0
    assert g._distance(0, 0, 0, 0) == 0.0


# ── Charge direction ──

def test_charge_direction() -> None:
    g = _make_game()
    g.px, g.py = 100.0, 100.0
    g.ox, g.oy = 200.0, 100.0
    dx, dy = g._charge_direction()
    assert abs(dx - 1.0) < 0.01
    assert abs(dy - 0.0) < 0.01


def test_charge_direction_same_position() -> None:
    g = _make_game()
    g.px, g.py = 100.0, 100.0
    g.ox, g.oy = 100.0, 100.0
    dx, dy = g._charge_direction()
    assert abs(dx - 0.0) < 0.01
    assert abs(dy - (-1.0)) < 0.01  # default direction up


# ── Apply push ──

def test_apply_push() -> None:
    g = _make_game()
    nx, ny = g._apply_push(10.0, 0.0, 100.0, 100.0)
    assert nx == 110.0
    assert ny == 100.0


# ── KO detection ──

def test_check_ko_false() -> None:
    g = _make_game()
    assert g._check_ko(RING_CX, RING_CY) is False


def test_check_ko_true() -> None:
    g = _make_game()
    assert g._check_ko(RING_CX + RING_RADIUS + 10, RING_CY) is True


# ── Color cycling ──

def test_color_cycle_advances_on_timer() -> None:
    g = _make_game()
    g.p_color_idx = 0
    g.o_color_idx = 2
    g.color_timer = COLOR_CYCLE_SPEED - 1
    g._cycle_colors()
    assert g.p_color_idx == 1
    assert g.o_color_idx == 3  # 2 → 3
    assert g.color_timer == 0


def test_color_cycle_wraps() -> None:
    g = _make_game()
    g.p_color_idx = 3
    g.o_color_idx = 3
    g.color_timer = COLOR_CYCLE_SPEED - 1
    g._cycle_colors()
    assert g.p_color_idx == 0  # wraps
    assert g.o_color_idx == 0


def test_color_cycle_no_change_before_timer() -> None:
    g = _make_game()
    g.p_color_idx = 1
    g.o_color_idx = 1
    g.color_timer = 20
    g._cycle_colors()
    assert g.p_color_idx == 1  # unchanged
    assert g.color_timer == 21


# ── Charge resolution: color match ──

def test_resolve_charge_match() -> None:
    g = _make_game()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30  # opponent above
    g.p_color_idx = 0  # RED
    g.o_color_idx = 0  # RED (match)
    g.combo = 0
    g.heat = 0.0
    g.score = 0
    g.super_mode = False

    g._resolve_charge()

    # COMBO incremented
    assert g.combo == 1
    assert g.max_combo == 1
    # Score awarded
    assert g.score > 0
    # Opponent pushed away from player
    assert g.oy < RING_CY - 30  # pushed further up
    # No heat change on match
    assert g.heat == 0.0


def test_resolve_charge_mismatch() -> None:
    g = _make_game()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30
    g.p_color_idx = 0  # RED
    g.o_color_idx = 1  # GREEN (mismatch)
    g.combo = 3
    g.max_combo = 3
    g.heat = 0.0
    g.score = 0
    g.super_mode = False

    g._resolve_charge()

    # COMBO reset
    assert g.combo == 0
    # max_combo preserved
    assert g.max_combo == 3
    # HEAT increased
    assert g.heat == HEAT_MISMATCH
    # No score on mismatch
    assert g.score == 0
    # Mismatch doesn't push opponent — only applies heat
    # (opponent stays at same position)
    assert abs(g.oy - (RING_CY - 30)) < 0.01


def test_resolve_charge_match_with_existing_combo() -> None:
    g = _make_game()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30
    g.p_color_idx = 0
    g.o_color_idx = 0
    g.combo = 2
    g.max_combo = 2
    g.heat = 0.0
    g.score = 0
    g.super_mode = False

    g._resolve_charge()

    # COMBO = 3, force_mult = 1 + 0.25*2 = 1.5
    assert g.combo == 3
    assert g.max_combo == 3
    score_before_super = g.score
    assert score_before_super > 100  # base 100 * (1 + 0.5*3) = 250
    assert g.heat == 0.0


def test_resolve_charge_activates_super_at_combo_4() -> None:
    g = _make_game()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30
    g.p_color_idx = 0
    g.o_color_idx = 0
    g.combo = 3  # this hit will push to 4
    g.max_combo = 3
    g.heat = 0.0
    g.score = 0
    g.super_mode = False
    g.super_timer = 0

    g._resolve_charge()

    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_resolve_charge_no_super_activation_below_4() -> None:
    g = _make_game()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30
    g.p_color_idx = 0
    g.o_color_idx = 0
    g.combo = 1
    g.super_mode = False

    g._resolve_charge()

    assert g.combo == 2
    assert g.super_mode is False


def test_resolve_charge_super_mode_always_matches() -> None:
    g = _make_game()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30
    g.p_color_idx = 0  # RED
    g.o_color_idx = 2  # DARK_BLUE (would mismatch normally)
    g.combo = 0
    g.heat = 0.0
    g.score = 0
    g.super_mode = True
    g.super_timer = 100

    g._resolve_charge()

    # SUPER MODE always matches
    assert g.combo == 1
    assert g.heat == 0.0
    assert g.score > 0


# ── SUPER MODE ──

def test_super_mode_timer_decrements() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 50
    g._update_super_mode()
    assert g.super_mode is True
    assert g.super_timer == 49


def test_super_mode_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super_mode()
    assert g.super_mode is False
    assert g.super_timer == 0


def test_super_mode_noop_when_inactive() -> None:
    g = _make_game()
    g.super_mode = False
    g.super_timer = 0
    g._update_super_mode()
    assert g.super_mode is False
    assert g.super_timer == 0


# ── HEAT system ──

def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 10.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert abs(g.heat - (10.0 - HEAT_DECAY)) < 0.001


def test_heat_decay_floor_zero() -> None:
    g = _make_game()
    g.heat = 0.01
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.heat == 0.0


def test_heat_reaches_max_triggers_game_over() -> None:
    g = _make_game()
    g.heat = HEAT_MAX  # 100.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "OVERHEAT!"


def test_heat_above_max_triggers_game_over() -> None:
    g = _make_game()
    g.heat = HEAT_MAX + 1.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_below_max_no_trigger() -> None:
    g = _make_game()
    g.heat = HEAT_MAX - 0.1
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.PLAYING
    assert abs(g.heat - (HEAT_MAX - 0.1 - HEAT_DECAY)) < 0.001


def test_heat_exactly_max_from_resolve_charge_triggers_after_check() -> None:
    """Verify that heat=100 (from min() clamp in resolve) triggers game over
    in the next _update_heat call (check happens before decay)."""
    g = _make_game()
    # Simulate reaching exactly 100 from charge mismatch
    g.heat = 85.0
    g.p_color_idx = 0
    g.o_color_idx = 1
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30
    g.phase = Phase.PLAYING
    g._resolve_charge()
    # After mismatch: heat = min(100, 85+15) = 100
    assert g.heat == HEAT_MAX
    # Now _update_heat should trigger game over
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


# ── KO ──

def test_on_ko_increments_ko_count_and_score() -> None:
    g = _make_game()
    g.ox = RING_CX + RING_RADIUS + 10
    g.oy = RING_CY
    g.ko_count = 0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.round_num = 1
    g.phase = Phase.PLAYING
    g._on_ko()
    assert g.ko_count == 1
    assert g.score == 500
    assert g.round_num == 2


def test_on_ko_resets_combo() -> None:
    g = _make_game()
    g.ox = RING_CX + RING_RADIUS + 10
    g.oy = RING_CY
    g.combo = 3
    g.max_combo = 3
    g.phase = Phase.PLAYING
    g._on_ko()
    assert g.combo == 0
    # max_combo is preserved (combo was 3 before KO, then becomes 4 during KO, max becomes 4)
    assert g.max_combo >= 3


def test_ko_via_resolve_charge() -> None:
    """When resolve_charge pushes opponent out of ring, KO triggers."""
    g = _make_game()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - (RING_RADIUS - 5)  # near top edge
    g.p_color_idx = 0
    g.o_color_idx = 0  # match for strong push
    g.combo = 4  # already at super-level force
    g.super_mode = True  # 3x force
    g.super_timer = 100
    g.ko_count = 0
    g.score = 0
    g.phase = Phase.PLAYING
    g._resolve_charge()
    # Opponent should have been pushed out → KO
    assert g.ko_count == 1


# ── Opponent spawning ──

def test_spawn_opponent_within_ring() -> None:
    g = _make_game()
    g._spawn_opponent(1)
    assert g._is_in_ring(g.ox, g.oy) is True
    assert g.o_hp == 10.0
    assert g.opponent_speed == 0.6


def test_spawn_opponent_scales_with_round() -> None:
    g = _make_game()
    g._spawn_opponent(3)
    assert g.o_hp == 10.0 + 2 * 3.0  # 16.0
    assert g.opponent_speed == 0.6 + 2 * 0.15  # 0.9
    assert g.opponent_aggression == min(0.3 + 2 * 0.1, 0.8)  # 0.5


# ── Particles ──

def test_spawn_push_particles() -> None:
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_push_particles(100.0, 100.0, RED, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == RED
        assert 15 <= p.life <= 25


def test_spawn_ko_particles() -> None:
    g = _make_game()
    g._spawn_ko_particles(100.0, 100.0)
    assert len(g.particles) == 20
    for p in g.particles:
        assert 20 <= p.life <= 35
        assert abs(p.gravity - 0.05) < 0.001


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.particles = [
        Particle(0, 0, 0, 0, 1, RED, 0.0),   # dies this tick
        Particle(0, 0, 0, 0, 2, GREEN, 0.0),  # survives
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 1  # decremented from 2


def test_update_particles_applies_velocity_and_gravity() -> None:
    g = _make_game()
    g.particles = [Particle(0.0, 0.0, 2.0, 1.0, 10, RED, 0.1)]
    g._update_particles()
    p = g.particles[0]
    assert p.x == 2.0
    assert p.y == 1.0
    assert p.vy == 1.1  # gravity applied
    assert p.life == 9


# ── Floating text ──

def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100.0, 50.0, "TEST!", WHITE)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "TEST!"
    assert ft.color == WHITE
    assert ft.life == 30


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatingText(0, 0, "dead", 1, WHITE),
        FloatingText(0, 0, "alive", 2, WHITE),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "alive"
    assert g.floating_texts[0].life == 1


def test_update_floating_texts_rises() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(100.0, 50.0, "UP", 10, WHITE)]
    g._update_floating_texts()
    assert g.floating_texts[0].y < 50.0  # moves up


# ── Reset ──

def test_reset_clears_all_state() -> None:
    g = _make_game()
    # Modify state
    g.score = 500
    g.combo = 5
    g.heat = 80.0
    g.ko_count = 3
    g.super_mode = True
    g.particles = [Particle(0, 0, 0, 0, 5, RED, 0)]
    g.floating_texts = [FloatingText(0, 0, "x", 5, WHITE)]
    g.phase = Phase.GAME_OVER

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.ko_count == 0
    assert g.round_num == 1
    assert g.game_timer == 60 * 60
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.phase == Phase.TITLE
    assert g.particles == []
    assert g.floating_texts == []
    assert g.px == RING_CX
    assert abs(g.py - (RING_CY + 60)) < 0.01


# ── Combo multiplier math ──

def test_combo_force_multiplier() -> None:
    """Force multiplier = 1 + 0.25 * combo (before charge)"""
    g = _make_game()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30
    g.p_color_idx = 0
    g.o_color_idx = 0

    # combo=0 → force_mult = 1.0
    g.combo = 0
    ox_before = g.ox
    g._resolve_charge()
    displacement_0 = abs(g.oy - ox_before)

    # Reset
    g.reset()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30
    g.p_color_idx = 0
    g.o_color_idx = 0
    g.combo = 3  # force_mult = 1 + 0.25*3 = 1.75
    ox_before = g.ox
    g._resolve_charge()
    displacement_3 = abs(g.oy - ox_before)

    # Higher combo = larger displacement
    assert displacement_3 > displacement_0


# ── Score calculation ──

def test_score_multiplier_increases_with_combo() -> None:
    g = _make_game()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30
    g.p_color_idx = 0
    g.o_color_idx = 0

    g.combo = 0
    g._resolve_charge()
    score_0 = g.score

    g.reset()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30
    g.p_color_idx = 0
    g.o_color_idx = 0
    g.combo = 3
    g._resolve_charge()
    score_3 = g.score

    # Higher combo = more points per hit
    # combo=3 → score = 100 * (1 + 0.5*4) = 100 * 3 = 300
    # combo=0 → score = 100 * (1 + 0.5*1) = 100 * 1.5 = 150
    assert score_3 > score_0


def test_super_mode_triple_score() -> None:
    g = _make_game()
    g.px = RING_CX
    g.py = RING_CY + 50
    g.ox = RING_CX
    g.oy = RING_CY - 30
    g.p_color_idx = 0
    g.o_color_idx = 0
    g.combo = 0
    g.super_mode = True
    g.super_timer = 100
    g._resolve_charge()
    assert g.score > 200  # 100 * (1 + 0.5*1) * 3.0 = 450


# ── Opponent AI ──

def test_opponent_ai_moves_toward_player() -> None:
    g = _make_game()
    g.px = RING_CX + 50
    g.py = RING_CY
    g.ox = RING_CX
    g.oy = RING_CY
    g.opponent_speed = 1.0
    g.opp_charge_timer = 999  # won't charge
    ox_before = g.ox
    g._update_opponent_ai()
    assert g.ox > ox_before  # moved right toward player


def test_opponent_ai_clamped_to_ring() -> None:
    g = _make_game()
    g.ox = RING_CX + RING_RADIUS - 3
    g.oy = RING_CY
    g.px = RING_CX + RING_RADIUS + 50  # player outside — pulls AI
    g.py = RING_CY
    g.opponent_speed = 10.0
    g.opp_charge_timer = 999
    g._update_opponent_ai()
    assert g._is_in_ring(g.ox, g.oy) is True


# ── Constants ──

def test_color_arrays() -> None:
    assert len(COLORS) == 4
    assert COLORS == [RED, GREEN, DARK_BLUE, YELLOW]
    assert len(SUPER_COLORS) == 8


def test_constants() -> None:
    assert WRESTLER_RADIUS == 14
    assert RING_RADIUS == 100
    assert CHARGE_FORCE_BASE == 4.0
    assert HEAT_MISMATCH == 15.0
    assert HEAT_MAX == 100.0
    assert SUPER_DURATION == 300
    assert CHARGE_COOLDOWN == 15


# ── Phase enum ──

def test_phase_values() -> None:
    assert Phase.TITLE.value == 0
    assert Phase.PLAYING.value == 1
    assert Phase.GAME_OVER.value == 2


# ── Dataclass fields ──

def test_particle_fields() -> None:
    p = Particle(1.0, 2.0, 3.0, 4.0, 10, RED, 0.1)
    assert p.x == 1.0
    assert p.y == 2.0
    assert p.vx == 3.0
    assert p.vy == 4.0
    assert p.life == 10
    assert p.color == RED
    assert p.gravity == 0.1


def test_floating_text_fields() -> None:
    ft = FloatingText(100.0, 50.0, "Test", 30, WHITE)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "Test"
    assert ft.life == 30
    assert ft.color == WHITE


# ── Initial state ──

def test_initial_player_position() -> None:
    g = _make_game()
    assert g.px == RING_CX
    assert g.py == RING_CY + 60


def test_initial_opponent_position() -> None:
    g = _make_game()
    assert g.ox == RING_CX
    assert g.oy == RING_CY - 50


def test_initial_game_timer() -> None:
    g = _make_game()
    assert g.game_timer == 60 * 60


def test_initial_no_super_mode() -> None:
    g = _make_game()
    assert g.super_mode is False
    assert g.super_timer == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
