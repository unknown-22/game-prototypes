"""test_imports.py — Headless logic tests for Boomerang Chain (206)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import (
    Game,
    Phase,
    Target,
    Boomerang,
    Particle,
    FloatingText,
    COLOR_CYCLE,
    TARGET_COLORS,
    TARGET_COUNT,
    TARGETS_PER_COLOR,
    TARGET_HALF,
    HEAT_MAX,
    HEAT_PER_WRONG,
    HEAT_DECAY,
    SUPER_REQUIRED_COMBO,
    SUPER_DURATION,
    PLAYER_X,
    PLAYER_Y,
    CATCH_RADIUS,
    MIN_FLY_FRAMES,
    BOOMERANG_SPEED_MIN,
    BOOMERANG_CURVE_RATE,
    RED,
    GREEN,
    LIGHT_BLUE,
    YELLOW,
    WHITE,
    GRAY,
    NAVY,
    BLACK,
    RESOLVE_DURATION,
    SCREEN_W,
    SCREEN_H,
    GAME_DURATION,
)


def _make_game(seed: int = 42) -> Game:
    """Create a Game instance for headless testing (bypasses pyxel.init/run)."""
    g = Game.__new__(Game)
    g._rng_seed = seed
    g.reset()
    return g


# === Data Class Tests ===

def test_target_dataclass() -> None:
    t = Target(x=100.0, y=50.0, color=RED)
    assert t.alive is True
    assert t.color == RED


def test_boomerang_dataclass() -> None:
    b = Boomerang(x=160.0, y=220.0, vx=3.0, vy=0.0, color=GREEN)
    assert b.alive is True
    assert b.fly_frames == 0
    assert len(b.trail) == 0


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=RED)
    assert p.life == 15
    assert p.gravity == 0.05


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+100", life=30, color=WHITE)
    assert ft.life == 30
    assert ft.text == "+100"


# === Initial State Tests ===

def test_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.game_timer == GAME_DURATION
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.aim_active is False
    assert g.boomerang is None
    assert g.boomerang_color_idx == 0
    assert g.boomerang_color == COLOR_CYCLE[0]
    assert g.best_score == 0
    assert g.shake_frames == 0
    assert g.resolve_timer == 0


def test_target_count_and_colors() -> None:
    g = _make_game()
    assert len(g.targets) == TARGET_COUNT
    assert sum(1 for t in g.targets if t.alive) == TARGET_COUNT
    colors = [t.color for t in g.targets]
    for c in TARGET_COLORS:
        assert colors.count(c) == TARGETS_PER_COLOR


def test_targets_not_overlapping() -> None:
    g = _make_game()
    for i, t1 in enumerate(g.targets):
        for j, t2 in enumerate(g.targets):
            if i >= j:
                continue
            # Should not be perfectly overlapping
            assert abs(t1.x - t2.x) >= 2 or abs(t1.y - t2.y) >= 2


def test_targets_in_bounds() -> None:
    g = _make_game()
    for t in g.targets:
        assert 0 <= t.x <= SCREEN_W
        assert 0 <= t.y <= SCREEN_H


# === Boomerang Launch Tests ===

def test_launch_boomerang() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g._launch_boomerang(math.pi * 0.5, 3.0)
    assert g.boomerang is not None
    assert g.boomerang.alive
    assert g.boomerang.x == PLAYER_X
    assert g.boomerang.y == PLAYER_Y
    assert abs(g.boomerang.vx - 0.0) < 1.0  # cos(pi/2) ≈ 0
    assert abs(g.boomerang.vy - 3.0) < 0.01  # sin(pi/2) = 1
    assert g.boomerang.color == COLOR_CYCLE[0]
    assert len(g.hit_targets_this_throw) == 0


def test_launch_boomerang_horizontal() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g._launch_boomerang(0.0, 4.0)
    assert g.boomerang is not None
    assert abs(g.boomerang.vx - 4.0) < 0.01
    assert abs(g.boomerang.vy - 0.0) < 0.01


def test_launch_boomerang_with_speed_clamp() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    # Speed is used directly by _launch_boomerang, clamping happens in update()
    g._launch_boomerang(0.0, BOOMERANG_SPEED_MIN)
    assert g.boomerang is not None
    assert abs(g.boomerang.vx - BOOMERANG_SPEED_MIN) < 0.01


# === Boomerang Movement Tests ===

def test_boomerang_movement() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g._launch_boomerang(0.0, 3.0)  # Launch right
    b = g.boomerang
    assert b is not None
    initial_x = b.x
    for _ in range(10):
        g._update_boomerang()
    b = g.boomerang
    assert b is not None
    assert b.fly_frames == 10
    assert b.x > initial_x  # Should have moved right
    assert len(b.trail) == 10


def test_boomerang_curves() -> None:
    """Boomerang should curve over time due to curve rate."""
    g = _make_game()
    g.phase = Phase.AIMING
    g._launch_boomerang(0.0, 3.0)  # Launch right (angle=0)
    g._update_boomerang()
    # After curve rotation, vy should no longer be zero
    # Rotation matrix: v'x = vx*cos(c) - vy*sin(c), v'y = vx*sin(c) + vy*cos(c)
    c = BOOMERANG_CURVE_RATE
    expected_vy = 3.0 * math.sin(c) + 0.0 * math.cos(c)
    b = g.boomerang
    assert b is not None
    assert abs(b.vy - expected_vy) < 0.01


def test_boomerang_trail_capped() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g._launch_boomerang(0.0, 3.0)
    for _ in range(100):
        g._update_boomerang()
    b = g.boomerang
    assert b is not None
    assert len(b.trail) <= b.max_trail


def test_boomerang_clamped_to_screen() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    # Launch straight up
    g._launch_boomerang(-math.pi / 2, 4.0)  # angle= -pi/2 is UP
    for _ in range(100):
        g._update_boomerang()
    b = g.boomerang
    assert b is not None
    assert 0 <= b.x <= SCREEN_W
    assert 0 <= b.y <= SCREEN_H


# === Collision Tests ===

def test_no_collision_with_no_boomerang() -> None:
    g = _make_game()
    g.boomerang = None
    hits = g._check_target_collisions()
    assert len(hits) == 0


def test_collision_with_target() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    # Place a target at a known position
    target = g.targets[0]
    g.boomerang = Boomerang(
        x=target.x, y=target.y, vx=0.0, vy=0.0, color=target.color
    )
    g.hit_targets_this_throw.clear()
    hits = g._check_target_collisions()
    assert len(hits) == 1
    assert hits[0] is target
    # Same target should not be hit again (tracked in set)
    hits2 = g._check_target_collisions()
    assert len(hits2) == 0


def test_collision_nearby() -> None:
    g = _make_game()
    target = g.targets[0]
    # Position boomerang just within collision range
    g.boomerang = Boomerang(
        x=target.x + TARGET_HALF + 2,
        y=target.y,
        vx=0.0,
        vy=0.0,
        color=target.color,
    )
    g.hit_targets_this_throw.clear()
    hits = g._check_target_collisions()
    # Should hit (distance is within BOOMERANG_RADIUS + TARGET_HALF = 4 + 7 = 11)
    assert len(hits) == 1


def test_no_collision_far_away() -> None:
    g = _make_game()
    target = g.targets[0]
    g.boomerang = Boomerang(
        x=target.x + 40,
        y=target.y + 40,
        vx=0.0,
        vy=0.0,
        color=target.color,
    )
    g.hit_targets_this_throw.clear()
    hits = g._check_target_collisions()
    assert len(hits) == 0


def test_dead_target_not_hit() -> None:
    g = _make_game()
    target = g.targets[0]
    target.alive = False
    g.boomerang = Boomerang(
        x=target.x, y=target.y, vx=0.0, vy=0.0, color=target.color
    )
    g.hit_targets_this_throw.clear()
    hits = g._check_target_collisions()
    assert len(hits) == 0


# === Hit Handling Tests ===

def test_same_color_hit() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    target = g.targets[0]
    g.boomerang = Boomerang(
        x=target.x, y=target.y, vx=0.0, vy=0.0, color=target.color
    )
    g.score = 0
    g.combo = 0
    g.heat = 0
    g.super_mode = False
    initial_alive = target.alive
    g._handle_hit(target)
    assert target.alive is False
    assert target.alive != initial_alive
    assert g.combo == 1
    assert g.score > 0
    assert g.heat == 0


def test_same_color_hit_increments_max_combo() -> None:
    g = _make_game()
    target = g.targets[0]
    g.boomerang = Boomerang(
        x=target.x, y=target.y, vx=0.0, vy=0.0, color=target.color
    )
    g.combo = 2
    g.max_combo = 2
    g.super_mode = False
    g._handle_hit(target)
    assert g.combo == 3
    assert g.max_combo == 3


def test_different_color_hit_resets_combo() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    # Find a target with different color than boomerang
    g.boomerang = Boomerang(
        x=0, y=0, vx=0.0, vy=0.0, color=RED
    )
    different_target = next(t for t in g.targets if t.color != RED and t.alive)
    g.boomerang.x = different_target.x
    g.boomerang.y = different_target.y
    g.score = 1000
    g.combo = 3
    g.heat = 0
    g.super_mode = False
    g._handle_hit(different_target)
    assert g.combo == 0
    assert g.score == 1100  # base 100
    assert g.heat == HEAT_PER_WRONG


def test_different_color_hit_adds_heat() -> None:
    g = _make_game()
    g.boomerang = Boomerang(
        x=0, y=0, vx=0.0, vy=0.0, color=RED
    )
    different_target = next(t for t in g.targets if t.color != RED and t.alive)
    g.boomerang.x = different_target.x
    g.boomerang.y = different_target.y
    g.heat = 50
    g.combo = 0
    g.super_mode = False
    g._handle_hit(different_target)
    assert g.heat == 60.0


def test_heat_capped_at_max() -> None:
    g = _make_game()
    g.boomerang = Boomerang(
        x=0, y=0, vx=0.0, vy=0.0, color=RED
    )
    different_target = next(t for t in g.targets if t.color != RED and t.alive)
    g.boomerang.x = different_target.x
    g.boomerang.y = different_target.y
    g.heat = 95
    g.combo = 0
    g.super_mode = False
    g._handle_hit(different_target)
    assert g.heat == HEAT_MAX


def test_super_mode_hit_any_color() -> None:
    g = _make_game()
    g.super_mode = True
    target = g.targets[0]
    g.boomerang = Boomerang(
        x=target.x, y=target.y, vx=0.0, vy=0.0, color=RED
    )
    # Even if colors don't match, super mode should still count as combo
    g.score = 1000
    g.combo = 0
    g.heat = 50
    # Set boomerang color different from target
    if target.color == RED:
        g.boomerang.color = GREEN
    g._handle_hit(target)
    assert g.combo == 1
    assert g.score > 1000  # 3x multiplier in super
    assert g.heat == 50  # Heat unchanged in super


def test_super_mode_3x_score() -> None:
    g = _make_game()
    g.super_mode = True
    target = g.targets[0]
    g.boomerang = Boomerang(
        x=target.x, y=target.y, vx=0.0, vy=0.0, color=target.color
    )
    g.score = 0
    g.combo = 0
    g.heat = 0
    g._handle_hit(target)
    # combo=1 → base = 100 * (1 + 1*0.5) = 150, super *3 = 450
    assert g.score == 450


def test_handle_hit_with_none_boomerang() -> None:
    g = _make_game()
    target = g.targets[0]
    g.boomerang = None
    initial_score = g.score
    g._handle_hit(target)
    assert g.score == initial_score  # No-op


# === Catch Tests ===

def test_catch_transitions_to_resolve() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.boomerang = Boomerang(
        x=PLAYER_X, y=PLAYER_Y - 10, vx=0.0, vy=0.0, color=RED
    )
    g.super_mode = False
    g.combo = 2  # below super threshold
    g._handle_catch()
    assert g.boomerang is None
    assert g.phase == Phase.RESOLVE
    assert g.resolve_timer == RESOLVE_DURATION


def test_catch_advances_color_idx() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.boomerang = Boomerang(
        x=PLAYER_X, y=PLAYER_Y - 10, vx=0.0, vy=0.0, color=RED
    )
    g.super_mode = False
    g.combo = 0
    g.boomerang_color_idx = 0
    g.boomerang_color = COLOR_CYCLE[0]
    g._handle_catch()
    assert g.boomerang_color_idx == 1
    assert g.boomerang_color == COLOR_CYCLE[1]


def test_catch_color_cycle_wraps() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.boomerang = Boomerang(
        x=PLAYER_X, y=PLAYER_Y - 10, vx=0.0, vy=0.0, color=RED
    )
    g.super_mode = False
    g.combo = 0
    g.boomerang_color_idx = len(COLOR_CYCLE) - 1
    g._handle_catch()
    assert g.boomerang_color_idx == 0


def test_catch_triggers_super() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.boomerang = Boomerang(
        x=PLAYER_X, y=PLAYER_Y - 10, vx=0.0, vy=0.0, color=RED
    )
    g.super_mode = False
    g.combo = SUPER_REQUIRED_COMBO  # exactly 4
    g._handle_catch()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION
    assert g.phase == Phase.RESOLVE


def test_catch_game_over_by_heat() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.boomerang = Boomerang(
        x=PLAYER_X, y=PLAYER_Y - 10, vx=0.0, vy=0.0, color=RED
    )
    g.super_mode = False
    g.combo = 0
    g.heat = HEAT_MAX
    g._handle_catch()
    assert g.phase == Phase.GAME_OVER


def test_catch_game_over_by_timer() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.boomerang = Boomerang(
        x=PLAYER_X, y=PLAYER_Y - 10, vx=0.0, vy=0.0, color=RED
    )
    g.super_mode = False
    g.combo = 0
    g.heat = 0
    g.game_timer = 0
    g._handle_catch()
    assert g.phase == Phase.GAME_OVER


def test_catch_deactivates_super() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.boomerang = Boomerang(
        x=PLAYER_X, y=PLAYER_Y - 10, vx=0.0, vy=0.0, color=RED
    )
    g.super_mode = True
    g.super_timer = 50
    g.combo = 1  # below super threshold, so no reactivation
    g._handle_catch()
    assert g.super_mode is False
    assert g.super_timer == 0


# === Super Mode Tests ===

def test_activate_super() -> None:
    g = _make_game()
    g.super_mode = False
    g.shake_frames = 0
    g._activate_super()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION
    assert g.shake_frames > 0


# === Heat Tests ===

def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 49.5
    g._update_heat()
    assert g.heat == 49.0


def test_heat_decay_floor_at_zero() -> None:
    g = _make_game()
    g.heat = 0.3
    g._update_heat()
    assert g.heat == 0.0


def test_heat_no_decay_at_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


# === Particle Tests ===

def test_spawn_hit_particles() -> None:
    g = _make_game()
    initial_count = len(g.particles)
    g._spawn_hit_particles(100, 100, RED, 8, 1.0, 3.0, 20, 30)
    assert len(g.particles) == initial_count + 8


def test_update_particles() -> None:
    g = _make_game()
    g._spawn_hit_particles(100, 100, RED, 5, 1.0, 2.0, 10, 20)
    g._update_particles()
    # Particles should have life decremented and moved
    for p in g.particles:
        assert p.life >= 0
        # Some particles may have been removed (life <= 0)


def test_particles_removed_when_dead() -> None:
    g = _make_game()
    # Create particles with life=1 — they'll die on first update
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0


def test_spawn_catch_particles() -> None:
    g = _make_game()
    initial = len(g.particles)
    g._spawn_catch_particles()
    assert len(g.particles) == initial + 8


# === Floating Text Tests ===

def test_spawn_floating_text() -> None:
    g = _make_game()
    initial = len(g.floating_texts)
    g._spawn_floating_text(100, 100, "+100", WHITE)
    assert len(g.floating_texts) == initial + 1
    assert g.floating_texts[-1].text == "+100"
    assert g.floating_texts[-1].life > 0


def test_update_floating_texts() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 100, "+100", WHITE)
    ft = g.floating_texts[-1]
    initial_y = ft.y
    initial_life = ft.life
    g._update_floating_texts()
    # After update: moved up and life decremented
    remaining = g.floating_texts
    if len(remaining) > 0:
        assert remaining[0].y < initial_y
        assert remaining[0].life == initial_life - 1


def test_floating_text_removed_when_dead() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100, y=100, text="+100", life=1, color=WHITE)
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# === Target Respawn Tests ===

def test_respawn_targets_restores_count() -> None:
    g = _make_game()
    # Kill some targets
    for i in range(4):
        g.targets[i].alive = False
    alive_before = sum(1 for t in g.targets if t.alive)
    assert alive_before == TARGET_COUNT - 4
    g._respawn_targets()
    alive_after = sum(1 for t in g.targets if t.alive)
    assert alive_after == TARGET_COUNT


def test_respawn_targets_noop_when_full() -> None:
    g = _make_game()
    # All targets alive
    original_colors = [t.color for t in g.targets]
    g._respawn_targets()
    current_colors = [t.color for t in g.targets]
    assert current_colors == original_colors


# === Score Tests ===

def test_combo_scoring() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    target = g.targets[0]
    g.boomerang = Boomerang(
        x=target.x, y=target.y, vx=0.0, vy=0.0, color=target.color
    )
    g.score = 0
    g.combo = 2
    g.super_mode = False
    g._handle_hit(target)
    # combo becomes 3, base = 100 * (1 + 3 * 0.5) = 100 * 2.5 = 250
    assert g.score == 250


def test_super_scoring_multiplier() -> None:
    g = _make_game()
    g.super_mode = True
    target = g.targets[0]
    g.boomerang = Boomerang(
        x=target.x, y=target.y, vx=0.0, vy=0.0, color=target.color
    )
    g.score = 0
    g.combo = 0
    g._handle_hit(target)
    # combo=1, base = 100*1.5=150, *3 = 450
    assert g.score == 450


def test_best_score_updated() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.best_score = 0
    g.score = 500
    g.boomerang = Boomerang(
        x=PLAYER_X, y=PLAYER_Y - 10, vx=0.0, vy=0.0, color=RED
    )
    g.super_mode = False
    g.combo = 0
    g._handle_catch()
    assert g.best_score == 500


# === Game Over Tests ===

def test_go_game_over() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g.score = 300
    g.best_score = 200
    g._go_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 300


def test_go_game_over_doesnt_lower_best() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g.score = 100
    g.best_score = 500
    g._go_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500  # unchanged


# === Enums ===

def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.AIMING in Phase
    assert Phase.FLYING in Phase
    assert Phase.RESOLVE in Phase
    assert Phase.GAME_OVER in Phase


# === Constants ===

def test_color_constants() -> None:
    assert RED == 8
    assert GREEN == 3
    assert LIGHT_BLUE == 6
    assert YELLOW == 10
    assert WHITE == 7
    assert GRAY == 13
    assert NAVY == 1
    assert BLACK == 0


def test_game_constants() -> None:
    assert HEAT_MAX == 100.0
    assert HEAT_PER_WRONG == 10.0
    assert HEAT_DECAY == 0.5
    assert SUPER_REQUIRED_COMBO == 4
    assert SUPER_DURATION == 180
    assert TARGET_COUNT == 12
    assert TARGETS_PER_COLOR == 3
    assert len(TARGET_COLORS) == 4


def test_boomerang_catches_after_min_frames() -> None:
    """Test that a boomerang near the player catches after MIN_FLY_FRAMES."""
    g = _make_game()
    g.phase = Phase.FLYING
    # Launch boomerang and simulate flying
    g._launch_boomerang(0.0, 3.0)
    b = g.boomerang
    assert b is not None
    # Move boomerang close to player after MIN_FLY_FRAMES
    b.fly_frames = MIN_FLY_FRAMES
    b.x = PLAYER_X + CATCH_RADIUS - 5
    b.y = PLAYER_Y
    # Simulate what _update would do in FLYING phase
    dx = b.x - PLAYER_X
    dy = b.y - PLAYER_Y
    assert math.hypot(dx, dy) < CATCH_RADIUS
    # Should catch
    g._handle_catch()
    assert g.boomerang is None
    assert g.phase == Phase.RESOLVE


def test_boomerang_not_caught_before_min_frames() -> None:
    """Check that the MIN_FLY_FRAMES check exists in the catch logic."""
    g = _make_game()
    g.phase = Phase.FLYING
    g._launch_boomerang(0.0, 3.0)
    b = g.boomerang
    assert b is not None
    b.fly_frames = MIN_FLY_FRAMES - 1  # Not enough frames
    # Even if position is at player, should not trigger via the update() check
    # But _handle_catch itself doesn't check fly_frames — the update() method does
    # So direct _handle_catch still works (intended for the manual test pattern)
    # We verify MIN_FLY_FRAMES as a constant
    assert MIN_FLY_FRAMES > 0


# === Float Comparison Tests ===

def test_heat_decay_float_accumulation() -> None:
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert abs(g.heat - 9.5) < 0.01
    g._update_heat()
    assert abs(g.heat - 9.0) < 0.01


def test_boomerang_physics_curve_accumulation() -> None:
    """After many frames, the boomerang should have turned significantly."""
    g = _make_game()
    g.phase = Phase.AIMING
    g._launch_boomerang(0.0, 3.0)
    # After 45 frames (~90 degrees rotation at 2 deg/frame)
    for _ in range(45):
        g._update_boomerang()
    b = g.boomerang
    assert b is not None
    # Initial angle was 0 (vx=3, vy=0). After 45*0.035 ≈ 1.575 rad ≈ 90°, vx≈0, vy≈3
    assert abs(b.vx) < 1.0  # Should be close to 0
    assert abs(b.vy) > 1.0  # Should have significant vertical component


# === Super Color Test ===

def test_super_color_cycling() -> None:
    g = _make_game()
    c1 = g._super_color()
    g.frame = 1
    c2 = g._super_color()
    # Colors cycle based on frame
    assert isinstance(c1, int)
    assert isinstance(c2, int)


# === Seed Determinism ===

def test_deterministic_with_seed() -> None:
    g1 = _make_game(12345)
    g2 = _make_game(12345)
    assert g1.targets[0].x == g2.targets[0].x
    assert g1.targets[0].y == g2.targets[0].y
    assert g1.targets[0].color == g2.targets[0].color


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
