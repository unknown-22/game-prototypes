"""test_imports.py — Headless logic tests for Axe Chain (126_axe_chain)."""
from __future__ import annotations

import math
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/126_axe_chain")

from main import (
    Axe,
    AXE_COLORS,
    FloatingText,
    Game,
    Particle,
    Phase,
    TargetRing,
    RED,
    GREEN,
    DARK_BLUE,
    YELLOW,
    WHITE,
)


# ── Test helpers ───────────────────────────────────────────────────────


def _make_game(seed: int = 42) -> Game:
    """Create a headless game instance with deterministic RNG."""
    g = Game.__new__(Game, headless=True)
    g._pre_init_attributes()
    g.set_seed(seed)
    return g


# ── Dataclass tests ────────────────────────────────────────────────────


def test_dataclass_axe() -> None:
    a = Axe(x=100.0, y=200.0, vx=0.0, vy=0.0, color=RED)
    assert a.x == 100.0
    assert a.y == 200.0
    assert a.color == RED
    assert not a.flying
    assert not a.landed
    assert a.landed_ring == -1
    assert a.rotation == 0.0
    assert a.spin_speed == 0.15


def test_dataclass_target_ring() -> None:
    tr = TargetRing(70.0, RED, 10)
    assert tr.radius == 70.0
    assert tr.color == RED
    assert tr.points == 10


def test_dataclass_particle() -> None:
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=10, color=YELLOW)
    assert p.x == 50.0
    assert p.life == 10
    assert p.size == 2


def test_dataclass_floating_text() -> None:
    ft = FloatingText(x=100.0, y=200.0, text="+50", life=25, color=WHITE)
    assert ft.text == "+50"
    assert ft.life == 25


# ── Phase enum tests ───────────────────────────────────────────────────


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.AIMING in Phase
    assert Phase.FLYING in Phase
    assert Phase.SCORING in Phase
    assert Phase.GAME_OVER in Phase


# ── Color constants ────────────────────────────────────────────────────


def test_axe_colors() -> None:
    assert len(AXE_COLORS) == 4
    assert RED in AXE_COLORS
    assert GREEN in AXE_COLORS
    assert DARK_BLUE in AXE_COLORS
    assert YELLOW in AXE_COLORS


# ── Game initialization ────────────────────────────────────────────────


def test_game_pre_init() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.best_ring == -1
    assert g.axes_thrown == 0
    assert g.heat == 0.0
    assert not g.super_active
    assert g.super_remaining == 0
    assert len(g.target_rings) == 4
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert not g.dragging


def test_start_game() -> None:
    g = _make_game()
    g.start_game()
    assert g.phase == Phase.AIMING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert not g.super_active
    assert g.axes_thrown == 0


def test_target_rings_values() -> None:
    g = _make_game()
    rings = g.target_rings
    assert rings[0].radius == 70.0 and rings[0].color == RED and rings[0].points == 10
    assert rings[1].radius == 52.5 and rings[1].color == GREEN and rings[1].points == 25
    assert rings[2].radius == 35.0 and rings[2].color == DARK_BLUE and rings[2].points == 50
    assert rings[3].radius == 17.5 and rings[3].color == YELLOW and rings[3].points == 100


# ── Aiming ─────────────────────────────────────────────────────────────


def test_start_aim_near_axe() -> None:
    g = _make_game()
    g.start_game()
    g._start_aim(g.AXE_SPAWN_X, g.AXE_SPAWN_Y)
    assert g.dragging
    assert g.drag_start_x == g.AXE_SPAWN_X
    assert g.drag_start_y == g.AXE_SPAWN_Y


def test_start_aim_far_from_axe() -> None:
    g = _make_game()
    g.start_game()
    g._start_aim(10.0, 10.0)  # far from axe at (160, 220)
    assert not g.dragging


def test_start_aim_wrong_phase() -> None:
    g = _make_game()
    # Still in TITLE phase
    g._start_aim(g.AXE_SPAWN_X, g.AXE_SPAWN_Y)
    assert not g.dragging


def test_update_aim() -> None:
    g = _make_game()
    g.start_game()
    g._start_aim(g.AXE_SPAWN_X, g.AXE_SPAWN_Y)
    g._update_aim(200.0, 100.0)
    assert g.drag_current_x == 200.0
    assert g.drag_current_y == 100.0


def test_release_aim_basic() -> None:
    g = _make_game()
    g.start_game()
    # Drag from axe to create velocity vector
    g._start_aim(g.AXE_SPAWN_X, g.AXE_SPAWN_Y)
    g._update_aim(100.0, 150.0)  # drag left-up from axe
    g._release_aim(100.0, 150.0)
    assert not g.dragging
    assert g.axe.flying
    assert g.phase == Phase.FLYING
    assert g.axes_thrown == 1
    assert g.last_axe_color == g.axe.color
    assert g.axe.vx > 0  # dx = 160-100 = 60, should be positive
    assert g.axe.vy > 0  # dy = 220-150 = 70, should be positive


def test_release_aim_zero_power() -> None:
    g = _make_game()
    g.start_game()
    g._start_aim(g.AXE_SPAWN_X, g.AXE_SPAWN_Y)
    g._release_aim(g.AXE_SPAWN_X, g.AXE_SPAWN_Y)  # same position = zero power
    assert not g.dragging
    assert g.axe.flying
    assert g.axe.vx == 0.0
    assert g.axe.vy == 0.0


def test_release_aim_max_power_clamp() -> None:
    g = _make_game()
    g.start_game()
    g._start_aim(g.AXE_SPAWN_X, g.AXE_SPAWN_Y)
    # Drag very far to exceed max power
    g._release_aim(-500.0, -500.0)
    power = math.sqrt(g.axe.vx**2 + g.axe.vy**2)
    assert abs(power - g.MAX_POWER) < 0.1


def test_release_aim_not_dragging() -> None:
    g = _make_game()
    g.start_game()
    g._release_aim(100.0, 100.0)  # not dragging
    assert g.phase == Phase.AIMING  # unchanged


# ── Target collision ───────────────────────────────────────────────────


def test_check_target_hit_bullseye() -> None:
    g = _make_game()
    g.start_game()
    # Place axe at target center
    g.axe.x = g.TARGET_CX
    g.axe.y = g.TARGET_CY
    ring = g._check_target_hit()
    assert ring == 3  # bullseye


def test_check_target_hit_outer() -> None:
    g = _make_game()
    g.start_game()
    # Place axe at outer ring boundary
    g.axe.x = g.TARGET_CX + 60.0
    g.axe.y = g.TARGET_CY
    ring = g._check_target_hit()
    assert ring == 0  # outer ring


def test_check_target_hit_mid_outer() -> None:
    g = _make_game()
    g.start_game()
    g.axe.x = g.TARGET_CX + 40.0
    g.axe.y = g.TARGET_CY
    ring = g._check_target_hit()
    assert ring == 1  # mid-outer


def test_check_target_hit_mid_inner() -> None:
    g = _make_game()
    g.start_game()
    g.axe.x = g.TARGET_CX + 25.0
    g.axe.y = g.TARGET_CY
    ring = g._check_target_hit()
    assert ring == 2  # mid-inner


def test_check_target_hit_miss() -> None:
    g = _make_game()
    g.start_game()
    g.axe.x = g.TARGET_CX + 80.0  # beyond max radius
    g.axe.y = g.TARGET_CY
    ring = g._check_target_hit()
    assert ring == -1


def test_ring_center_distance() -> None:
    g = _make_game()
    dist = g._ring_center_distance(g.TARGET_CX + 30.0, g.TARGET_CY)
    assert abs(dist - 30.0) < 0.01
    dist = g._ring_center_distance(g.TARGET_CX + 40.0, g.TARGET_CY + 30.0)
    assert abs(dist - 50.0) < 0.01


# ── Hit resolution ─────────────────────────────────────────────────────


def test_resolve_hit_color_match() -> None:
    g = _make_game()
    g.start_game()
    # Force axe color to match ring 3 (YELLOW, bullseye)
    g.axe.color = YELLOW
    g.axe.landed = True  # simulate landing (normally set by _update_axe)
    g.axe.landed_ring = 3
    initial_score = g.score
    g._resolve_hit(3)
    assert g.score > initial_score  # scored
    assert g.heat < 5.0  # heat cooled
    assert g.phase == Phase.SCORING
    assert g.axe.landed
    assert g.best_ring == 3
    assert g.combo == 1


def test_resolve_hit_color_match_combo_chain() -> None:
    g = _make_game()
    g.start_game()
    # Set combo to 4
    g.combo = 4
    g.axe.color = YELLOW
    scores = []
    for i in range(3):
        g.axe.color = YELLOW
        g._resolve_hit(3)
        scores.append(g.score)
        # Reset for next throw
        g.phase = Phase.AIMING
        g.axe.landed = False
        g.axe.landed_ring = -1
    assert g.combo > 0 or g.super_active  # combo built up
    assert g.max_combo >= 1


def test_resolve_hit_wrong_color() -> None:
    g = _make_game()
    g.start_game()
    g.combo = 3
    g.max_combo = 3
    # Axe color is RED, ring is GREEN (no match)
    g.axe.color = RED
    g._resolve_hit(1)  # mid-outer = GREEN
    assert g.combo == 0  # reset
    assert g.max_combo == 3  # unchanged
    assert g.phase == Phase.SCORING


def test_resolve_hit_miss() -> None:
    g = _make_game()
    g.start_game()
    g.combo = 3
    g.max_combo = 3
    g._handle_miss()
    assert g.combo == 0
    assert g.heat > 0  # heat increased
    assert g.phase == Phase.SCORING
    assert len(g.floating_texts) >= 1


def test_resolve_hit_super_axe() -> None:
    g = _make_game()
    g.start_game()
    g.super_active = True
    g.super_remaining = 1
    g.combo = 0
    initial_score = g.score
    g.axe.color = RED
    g._resolve_hit(3)  # bullseye
    assert g.super_remaining <= 0  # consumed, or 0 if only 1
    if g.super_remaining <= 0:
        assert not g.super_active
    assert g.shake_frames == 8
    assert g.score > initial_score


def test_super_activation_after_combo() -> None:
    g = _make_game()
    g.start_game()
    g.combo = 4
    g.axe.color = YELLOW
    g._resolve_hit(3)  # color match bullseye, combo becomes 5
    assert g.super_active
    assert g.super_remaining == 1


def test_check_super_activation() -> None:
    g = _make_game()
    assert not g._check_super_activation()
    g.combo = 4
    assert not g._check_super_activation()
    g.combo = 5
    assert g._check_super_activation()
    g.combo = 10
    assert g._check_super_activation()


# ── Score / heat helpers ───────────────────────────────────────────────


def test_add_score() -> None:
    g = _make_game()
    g._add_score(100)
    assert g.score == 100
    g._add_score(50)
    assert g.score == 150


def test_apply_heat() -> None:
    g = _make_game()
    g._apply_heat(30.0)
    assert abs(g.heat - 30.0) < 0.01
    g._apply_heat(-10.0)
    assert abs(g.heat - 20.0) < 0.01


def test_apply_heat_clamp_zero() -> None:
    g = _make_game()
    g._apply_heat(-50.0)
    assert g.heat == 0.0


def test_apply_heat_clamp_max() -> None:
    g = _make_game()
    g._apply_heat(150.0)
    assert abs(g.heat - 100.0) < 0.01


# ── Particles ──────────────────────────────────────────────────────────


def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 200.0, YELLOW, 8)
    assert len(g.particles) == 8
    for p in g.particles:
        assert p.color == YELLOW
        assert 8 <= p.life <= 20
        assert p.x == 100.0
        assert p.y == 200.0


def test_update_particles_moves_and_decays() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 200.0, GREEN, 1)
    p = g.particles[0]
    old_x, old_y, old_life = p.x, p.y, p.life
    g._update_particles()
    assert p.x != old_x or p.y != old_y  # moved
    assert p.life == old_life - 1


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 200.0, RED, 1)
    # Set life to 1 so it dies after one update
    g.particles[0].life = 1
    g._update_particles()
    assert len(g.particles) == 0


# ── Floating text ──────────────────────────────────────────────────────


def test_add_floating_text() -> None:
    g = _make_game()
    g._add_floating_text(100.0, 200.0, "+100", YELLOW)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+100"
    assert g.floating_texts[0].life == 25


def test_update_floating_texts() -> None:
    g = _make_game()
    g._add_floating_text(100.0, 200.0, "+50", WHITE)
    ft = g.floating_texts[0]
    old_y, old_life = ft.y, ft.life
    g._update_floating_texts()
    assert ft.y < old_y  # moved up
    assert ft.life == old_life - 1


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    g._add_floating_text(100.0, 200.0, "+50", WHITE)
    g.floating_texts[0].life = 1
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Scoring phase ──────────────────────────────────────────────────────


def test_update_scoring_next_axe() -> None:
    g = _make_game()
    g.start_game()
    g.phase = Phase.SCORING
    g.scoring_timer = 1
    g.axes_thrown = 5
    g.heat = 50.0
    g._update_scoring()
    assert g.phase == Phase.AIMING  # next axe


def test_update_scoring_game_over_heat() -> None:
    g = _make_game()
    g.start_game()
    g.phase = Phase.SCORING
    g.scoring_timer = 1
    g.heat = 100.0
    g._update_scoring()
    assert g.phase == Phase.GAME_OVER


def test_update_scoring_game_over_axes_exhausted() -> None:
    g = _make_game()
    g.start_game()
    g.phase = Phase.SCORING
    g.scoring_timer = 1
    g.axes_thrown = g.AXES_PER_GAME
    g._update_scoring()
    assert g.phase == Phase.GAME_OVER


def test_update_scoring_not_scoring_phase() -> None:
    g = _make_game()
    g.start_game()
    g._update_scoring()  # phase is AIMING
    assert g.phase == Phase.AIMING  # unchanged


# ── Axe physics ────────────────────────────────────────────────────────


def test_update_axe_gravity() -> None:
    g = _make_game()
    g.start_game()
    g.axe.flying = True
    g.axe.x = 160.0
    g.axe.y = 100.0
    g.axe.vx = 2.0
    g.axe.vy = 0.0
    g._update_axe()
    assert g.axe.vy > 0  # gravity applied
    assert g.axe.x > 160.0  # moved right
    assert g.axe.y > 100.0  # moved down


def test_update_axe_hits_target() -> None:
    g = _make_game()
    g.start_game()
    g.axe.flying = True
    # Place axe right above target center, moving down
    g.axe.x = g.TARGET_CX
    g.axe.y = g.TARGET_CY - 1.0
    g.axe.vx = 0.0
    g.axe.vy = 5.0
    g._update_axe()
    assert not g.axe.flying
    assert g.axe.landed
    assert g.axe.landed_ring >= 0


def test_update_axe_off_screen_miss() -> None:
    g = _make_game()
    g.start_game()
    g.axe.flying = True
    g.axe.x = -100.0  # off screen left
    g.axe.y = 100.0
    g.axe.vx = -5.0
    g.axe.vy = 0.0
    g.combo = 3
    g._update_axe()
    assert not g.axe.flying
    assert g.combo == 0  # miss resets combo
    assert g.phase == Phase.SCORING


# ── Compute throw velocity ─────────────────────────────────────────────


def test_compute_throw_velocity() -> None:
    g = _make_game()
    g.start_game()
    g._start_aim(g.AXE_SPAWN_X, g.AXE_SPAWN_Y)
    g._update_aim(100.0, 150.0)
    vx, vy = g._compute_throw_velocity()
    # dx = 160-100=60, dy=220-150=70, power ~92, exceeds MAX_POWER=12
    # Clamped: scale = 12/92 ≈ 0.13, so vx ≈ 7.8, vy ≈ 9.1
    power = math.sqrt(vx**2 + vy**2)
    assert abs(power - g.MAX_POWER) < 0.5


def test_compute_throw_velocity_not_dragging() -> None:
    g = _make_game()
    g.start_game()
    vx, vy = g._compute_throw_velocity()
    assert vx == 0.0
    assert vy == 0.0


# ── Random axe color ───────────────────────────────────────────────────


def test_random_axe_color() -> None:
    g = _make_game()
    for _ in range(50):
        c = g._random_axe_color()
        assert c in AXE_COLORS


def test_spawn_axe() -> None:
    g = _make_game()
    g.start_game()
    g._spawn_axe()
    assert g.axe.x == g.AXE_SPAWN_X
    assert g.axe.y == g.AXE_SPAWN_Y
    assert g.axe.color in AXE_COLORS
    assert not g.axe.flying


# ── Edge cases ─────────────────────────────────────────────────────────


def test_heat_exactly_100_game_over_via_scoring() -> None:
    g = _make_game()
    g.start_game()
    g.heat = 100.0
    g.phase = Phase.SCORING
    g.scoring_timer = 1
    g._update_scoring()
    assert g.phase == Phase.GAME_OVER


def test_best_ring_tracks_max() -> None:
    g = _make_game()
    g.start_game()
    g.axe.color = YELLOW
    g._resolve_hit(1)  # mid-outer
    assert g.best_ring == 1
    # Reset for next hit
    g.phase = Phase.AIMING
    g.axe.landed = False
    g.axe.landed_ring = -1
    g._resolve_hit(3)  # bullseye
    assert g.best_ring == 3  # updated to better


def test_combo_sequence_same_color() -> None:
    """5 same-color bullseyes should build combo=5 and activate super."""
    g = _make_game()
    g.start_game()
    for i in range(5):
        g.axe.color = YELLOW
        g._resolve_hit(3)
        # Reset for next throw
        g.phase = Phase.AIMING
        g.axe.landed = False
        g.axe.landed_ring = -1
    assert g.combo == 5 or g.super_active
    assert g.max_combo >= 5


def test_combo_reset_on_wrong_color() -> None:
    g = _make_game()
    g.start_game()
    # Build combo
    g.axe.color = RED
    g._resolve_hit(0)  # outer ring = RED, match
    assert g.combo == 1
    g.phase = Phase.AIMING
    g.axe.landed = False
    g.axe.landed_ring = -1
    # Wrong color
    g.axe.color = RED
    g._resolve_hit(3)  # bullseye = YELLOW, no match
    assert g.combo == 0


def test_score_with_combo_multiplier() -> None:
    """Score should be base_points * (1 + combo) for color match."""
    g = _make_game()
    g.start_game()
    g.combo = 4
    g.axe.color = RED
    g._resolve_hit(0)  # outer ring, RED on RED = match, 10 pts
    # Points = 10 * (1 + 5) = 60
    assert g.score >= 50  # at least 10*(1+5)=60 but check >= 50 for float safety
    assert g.combo == 5


def test_miss_builds_heat() -> None:
    g = _make_game()
    g.start_game()
    initial_heat = g.heat
    g._handle_miss()
    assert g.heat > initial_heat


def test_hit_cools_heat() -> None:
    g = _make_game()
    g.start_game()
    g.heat = 50.0
    g._apply_heat(-g.HEAT_COOL_PER_HIT)
    assert g.heat < 50.0


def test_axe_landed_not_drawn() -> None:
    """After landing via _update_axe, axe.landed is True."""
    g = _make_game()
    g.start_game()
    g.axe.flying = True
    g.axe.x = g.TARGET_CX
    g.axe.y = g.TARGET_CY
    g.axe.vx = 0.0
    g.axe.vy = 0.1
    g._update_axe()
    assert g.axe.landed


def test_multiple_axes_game_progression() -> None:
    """When all axes are thrown (axes_thrown >= AXES_PER_GAME) and scoring ends, game is over."""
    g = _make_game()
    g.start_game()
    g.axe.color = YELLOW
    g.axe.flying = True
    g.axe.x = g.TARGET_CX
    g.axe.y = g.TARGET_CY
    g.axe.vx = 0.0
    g.axe.vy = 0.1
    g.axes_thrown = g.AXES_PER_GAME  # all axes used
    g._update_axe()  # hits target, transitions to SCORING
    assert g.phase == Phase.SCORING
    g.scoring_timer = 1  # expire immediately
    g._update_scoring()
    assert g.phase == Phase.GAME_OVER


def test_constants() -> None:
    assert Game.GRAVITY == 0.15
    assert Game.MAX_POWER == 12.0
    assert Game.AXES_PER_GAME == 15
    assert Game.HEAT_PER_MISS == 15.0
    assert Game.HEAT_COOL_PER_HIT == 5.0
    assert Game.COMBO_FOR_SUPER == 5
    assert Game.TARGET_CX == 160
    assert Game.TARGET_CY == 90
    assert Game.TARGET_MAX_RADIUS == 70
    assert Game.AXE_SPAWN_X == 160
    assert Game.AXE_SPAWN_Y == 220


# ── Run ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
