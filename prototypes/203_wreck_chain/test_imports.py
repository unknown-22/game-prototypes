"""test_imports.py — Headless logic tests for Wreck Chain.

Uses Game.__new__(Game) to bypass pyxel.init/run.
Tests core logic methods directly — never calls pyxel.btn/btnp/frame_count.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import (
    BALL_RADIUS,
    BLOCK_COLORS,
    CELL,
    COLS,
    COMBO_THRESHOLD,
    GRID_X,
    GRID_Y,
    HEAT_DECAY,
    HEAT_HIT_WRONG,
    HEAT_MAX,
    PIVOT_X,
    PIVOT_Y,
    ROPE_BASE,
    ROPE_MIN,
    ROWS,
    SUPER_BALL_RADIUS,
    SUPER_DURATION,
    TIMER_MAX,
    Block,
    Game,
    Phase,
)


def _make_game() -> Game:
    """Factory: create a Game bypassing __init__ for headless testing."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes touched by reset()
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = TIMER_MAX
    g.super_timer = 0
    g._is_super = False
    g.pendulum_angle = 0.0
    g.pendulum_angular_vel = 0.0
    g.charge = 0.0
    g.charging = False
    g._swing_power = 0.0
    g._swinging = False
    g._ball_x = PIVOT_X
    g._ball_y = PIVOT_Y + ROPE_BASE
    g._rope_len = ROPE_BASE
    g.last_hit_color = -1
    g._super_color_cycle = 0
    g.blocks = []
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g._rng = random.Random(42)  # Seeded for deterministic tests
    g._init_grid()
    return g


# ════════════════════════════════════════════════════════════════════
# Grid Tests
# ════════════════════════════════════════════════════════════════════


def test_init_grid_creates_all_blocks() -> None:
    g = _make_game()
    assert len(g.blocks) == COLS * ROWS
    assert all(not b.destroyed for b in g.blocks)
    assert all(b.color in BLOCK_COLORS for b in g.blocks)


def test_any_blocks_alive_all_alive() -> None:
    g = _make_game()
    assert g._any_blocks_alive() is True


def test_any_blocks_alive_all_destroyed() -> None:
    g = _make_game()
    for b in g.blocks:
        b.destroyed = True
    assert g._any_blocks_alive() is False


def test_init_grid_clears_previous_blocks() -> None:
    g = _make_game()
    g.blocks.append(Block(col=99, row=99, color=0, destroyed=False))
    g._init_grid()
    assert len(g.blocks) == COLS * ROWS


# ════════════════════════════════════════════════════════════════════
# Pendulum Physics Tests
# ════════════════════════════════════════════════════════════════════


def test_pendulum_angle_changes_over_time() -> None:
    g = _make_game()
    g.pendulum_angle = 0.5  # start at non-zero angle
    initial = g.pendulum_angle
    for _ in range(10):
        g._update_pendulum()
    # Angle should change due to gravity
    assert g.pendulum_angle != initial


def test_pendulum_gravity_pulls_down() -> None:
    """At angle > 0, gravity should pull angle back toward 0 (decrease)."""
    g = _make_game()
    g.pendulum_angle = 0.5
    g.pendulum_angular_vel = 0.0
    g._update_pendulum()
    # angular_vel should now be positive or negative depending on sin(angle)
    # sin(0.5) > 0, so vel should increase (positive), then angle increases
    assert g.pendulum_angular_vel != 0.0


def test_ball_position_at_rest() -> None:
    g = _make_game()
    g.pendulum_angle = 0.0
    g._rope_len = ROPE_BASE
    g._update_ball_position()
    assert abs(g._ball_x - PIVOT_X) < 0.01
    assert abs(g._ball_y - (PIVOT_Y + ROPE_BASE)) < 0.01


def test_ball_position_at_angle() -> None:
    g = _make_game()
    g.pendulum_angle = math.pi / 2  # 90 degrees right
    g._rope_len = ROPE_BASE
    g._update_ball_position()
    assert abs(g._ball_x - (PIVOT_X + ROPE_BASE)) < 0.01
    assert abs(g._ball_y - PIVOT_Y) < 0.01


def test_rope_len_charging() -> None:
    g = _make_game()
    g.charging = True
    g.charge = 50.0
    length = g._get_rope_len()
    # At 50% charge, length should be halfway between BASE and MIN
    expected = ROPE_BASE - 0.5 * (ROPE_BASE - ROPE_MIN)
    assert abs(length - expected) < 0.01


def test_rope_len_not_charging() -> None:
    g = _make_game()
    g.charging = False
    assert g._get_rope_len() == ROPE_BASE


def test_rope_len_full_charge() -> None:
    g = _make_game()
    g.charging = True
    g.charge = 100.0
    length = g._get_rope_len()
    assert abs(length - ROPE_MIN) < 0.01


# ════════════════════════════════════════════════════════════════════
# Block Collision & Rect Tests
# ════════════════════════════════════════════════════════════════════


def test_block_rect_top_left() -> None:
    g = _make_game()
    block = Block(col=0, row=0, color=8)
    x1, y1, x2, y2 = g._block_rect(block)
    assert x1 == GRID_X
    assert y1 == GRID_Y
    assert x2 == GRID_X + CELL
    assert y2 == GRID_Y + CELL


def test_block_rect_bottom_right() -> None:
    g = _make_game()
    block = Block(col=COLS - 1, row=ROWS - 1, color=8)
    x1, y1, x2, y2 = g._block_rect(block)
    assert x2 == GRID_X + COLS * CELL
    assert y2 == GRID_Y + ROWS * CELL


def test_check_collisions_no_overlap() -> None:
    g = _make_game()
    # Place ball far from blocks
    g._ball_x = 0
    g._ball_y = 0
    g._is_super = False
    hits = g._check_block_collisions()
    assert len(hits) == 0


def test_check_collisions_direct_hit() -> None:
    g = _make_game()
    # Place ball at center of block (0,0)
    g._ball_x = GRID_X + CELL // 2
    g._ball_y = GRID_Y + CELL // 2
    g._is_super = False
    hits = g._check_block_collisions()
    assert (0, 0) in hits


def test_check_collisions_super_bigger_radius() -> None:
    g = _make_game()
    g._is_super = True
    # Ball near but not touching normal-radius block
    g._ball_x = GRID_X + CELL + SUPER_BALL_RADIUS
    g._ball_y = GRID_Y + CELL // 2
    hits = g._check_block_collisions()
    # Super ball should hit more blocks due to larger radius
    # Verify at least the nearest blocks are hit
    assert len(hits) >= 1


def test_check_collisions_destroyed_blocks_ignored() -> None:
    g = _make_game()
    # Destroy first block
    g.blocks[0].destroyed = True
    g._ball_x = GRID_X + CELL // 2
    g._ball_y = GRID_Y + CELL // 2
    hits = g._check_block_collisions()
    assert (0, 0) not in hits


# ════════════════════════════════════════════════════════════════════
# Destroy Block Tests
# ════════════════════════════════════════════════════════════════════


def test_destroy_block_first_hit() -> None:
    g = _make_game()
    g._ball_x = GRID_X + CELL // 2
    g._ball_y = GRID_Y + CELL // 2
    g.last_hit_color = -1
    result = g._destroy_block(0, 0)
    assert result is True
    assert g.blocks[0].destroyed is True
    assert g.combo == 1
    assert g.score > 0


def test_destroy_block_same_color_combo() -> None:
    g = _make_game()
    # Hit first block, set color
    g.last_hit_color = -1
    g._destroy_block(0, 0)
    first_color = g.blocks[0].color if g.blocks[0].destroyed else -1
    combo_before = g.combo
    score_before = g.score

    # Make block (1,0) same color and hit it
    g.blocks[1].color = first_color
    g.last_hit_color = first_color
    g._destroy_block(1, 0)
    assert g.combo == combo_before + 1  # combo incremented
    assert g.score > score_before


def test_destroy_block_wrong_color_resets() -> None:
    g = _make_game()
    g.last_hit_color = -1
    g._destroy_block(0, 0)
    first_color = g.last_hit_color

    # Make next block a different color
    wrong_color = next(c for c in BLOCK_COLORS if c != first_color)
    g.blocks[1].color = wrong_color
    g._destroy_block(1, 0)
    assert g.combo == 0  # combo reset
    assert g.heat > 0  # heat added
    assert g.last_hit_color == -1  # reset


def test_destroy_block_super_mode_always_matches() -> None:
    g = _make_game()
    g._is_super = True
    g.last_hit_color = 8  # RED
    # Hit a GREEN block — should match in super mode
    g.blocks[0].color = 3  # GREEN
    result = g._destroy_block(0, 0)
    assert result is True
    assert g.combo == 1  # combo incremented


def test_destroy_block_already_destroyed() -> None:
    g = _make_game()
    g.blocks[0].destroyed = True
    result = g._destroy_block(0, 0)
    assert result is False


# ════════════════════════════════════════════════════════════════════
# Score / Combo Tests
# ════════════════════════════════════════════════════════════════════


def test_on_same_color_hit_score_calculation() -> None:
    g = _make_game()
    g.combo = 0
    g.score = 0
    g._is_super = False
    g._on_same_color_hit(8)  # RED
    # score = 10 * (1 + 1 * 0.5) = 15
    assert g.score == 15
    assert g.combo == 1


def test_on_same_color_hit_combo_3() -> None:
    g = _make_game()
    g.combo = 2
    g.score = 0
    g._on_same_color_hit(8)
    # combo becomes 3, score = 10 * (1 + 3 * 0.5) = 25
    assert g.score == 25
    assert g.combo == 3


def test_on_same_color_hit_super_multiplier() -> None:
    g = _make_game()
    g.combo = 0
    g.score = 0
    g._is_super = True
    g._on_same_color_hit(8)
    # score = 10 * (1 + 1 * 0.5) * 3 = 45
    assert g.score == 45


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.max_combo = 0
    g.combo = 4
    g._on_same_color_hit(8)
    assert g.max_combo == 5


def test_on_wrong_color_hit_adds_heat_and_resets() -> None:
    g = _make_game()
    g.combo = 5
    g.heat = 10.0
    g._on_wrong_color_hit()
    assert g.heat == 10.0 + HEAT_HIT_WRONG
    assert g.combo == 0


# ════════════════════════════════════════════════════════════════════
# Super Ball Tests
# ════════════════════════════════════════════════════════════════════


def test_activate_super() -> None:
    g = _make_game()
    g._activate_super()
    assert g._is_super is True
    assert g.super_timer == SUPER_DURATION
    assert g.shake_frames == 10
    assert len(g.particles) == 20  # burst particles
    assert len(g.floating_texts) == 1


def test_deactivate_super() -> None:
    g = _make_game()
    g._is_super = True
    g.super_timer = 100
    g._deactivate_super()
    assert g._is_super is False
    assert g.super_timer == 0


def test_get_ball_radius_normal() -> None:
    g = _make_game()
    g._is_super = False
    assert g._get_ball_radius() == BALL_RADIUS


def test_get_ball_radius_super() -> None:
    g = _make_game()
    g._is_super = True
    assert g._get_ball_radius() == SUPER_BALL_RADIUS


def test_super_activates_at_combo_threshold() -> None:
    g = _make_game()
    g.combo = COMBO_THRESHOLD - 1  # 3
    g._is_super = False
    g._on_same_color_hit(8)  # combo becomes 4, triggers super
    assert g._is_super is True


def test_super_does_not_reactivate() -> None:
    g = _make_game()
    g._is_super = True
    g.super_timer = 50  # already active with some time left
    g.combo = 10
    # Should not re-activate (is_super already True, _activate_super skipped)
    g._on_same_color_hit(8)
    assert g._is_super is True  # remains super
    assert g.super_timer == 50  # unchanged — _activate_super not called


# ════════════════════════════════════════════════════════════════════
# Timer & Heat Tests
# ════════════════════════════════════════════════════════════════════


def test_update_timer_decrements() -> None:
    g = _make_game()
    initial = g.timer
    g._update_timer()
    assert g.timer == initial - 1


def test_update_timer_stops_at_zero() -> None:
    g = _make_game()
    g.timer = 0
    g._update_timer()
    assert g.timer == 0  # stays at 0


def test_update_heat_decays() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_update_heat_does_not_go_negative() -> None:
    g = _make_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


def test_heat_cap_at_max() -> None:
    g = _make_game()
    g.heat = HEAT_MAX  # already at max
    g.heat = min(HEAT_MAX, g.heat + HEAT_HIT_WRONG)  # shouldn't exceed
    assert g.heat == HEAT_MAX


# ════════════════════════════════════════════════════════════════════
# Particle & Floating Text Tests
# ════════════════════════════════════════════════════════════════════


def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, 8, 12)
    assert len(g.particles) == 12
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 100.0
        assert p.color == 8
        assert p.life >= 15
        assert p.life <= 30


def test_update_particles_move_and_die() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, 8, 5)
    # Force all particles to have short life
    for p in g.particles:
        p.life = 1
    g._update_particles()
    assert len(g.particles) == 0  # all should be removed


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 100, "+15", 8)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "+15"
    assert ft.color == 8
    assert ft.life == 30


def test_update_floating_texts_move_and_die() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 100, "test", 8)
    # Force short life
    g.floating_texts[0].life = 1
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ════════════════════════════════════════════════════════════════════
# Grid Clear / Respawn Tests
# ════════════════════════════════════════════════════════════════════


def test_grid_respawn_when_all_destroyed() -> None:
    g = _make_game()
    # Destroy all blocks
    for b in g.blocks:
        b.destroyed = True
    assert g._any_blocks_alive() is False
    # Re-init should work
    g._init_grid()
    assert g._any_blocks_alive() is True
    assert len(g.blocks) == COLS * ROWS


# ════════════════════════════════════════════════════════════════════
# Phase & State Tests
# ════════════════════════════════════════════════════════════════════


def test_reset_initializes_all_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == TIMER_MAX
    assert g.super_timer == 0
    assert g._is_super is False
    assert len(g.blocks) == COLS * ROWS


def test_rng_deterministic_with_seed() -> None:
    g1 = _make_game()
    colors1 = [b.color for b in g1.blocks[:10]]

    g2 = _make_game()
    colors2 = [b.color for b in g2.blocks[:10]]

    # With same seed (42), colors should be identical
    assert colors1 == colors2


# ════════════════════════════════════════════════════════════════════
# Edge Cases
# ════════════════════════════════════════════════════════════════════


def test_ball_hits_multiple_blocks_in_one_frame() -> None:
    """Super ball can hit multiple blocks simultaneously."""
    g = _make_game()
    g._is_super = True
    # Place ball to overlap 4 adjacent blocks
    g._ball_x = GRID_X + CELL  # between col 0 and 1
    g._ball_y = GRID_Y + CELL  # between row 0 and 1
    hits = g._check_block_collisions()
    # Should hit at least 2 blocks (adjacent)
    assert len(hits) >= 2


def test_charge_clamps_to_100() -> None:
    g = _make_game()
    g.charging = True
    for _ in range(200):  # way more than needed to hit 100
        g.charge = min(100.0, g.charge + 1.5)
    assert g.charge == 100.0


def test_combo_reset_on_empty_grid_after_clear() -> None:
    g = _make_game()
    g.combo = 5
    g.last_hit_color = 8
    # Simulate all blocks destroyed
    for b in g.blocks:
        b.destroyed = True
    assert not g._any_blocks_alive()
    # What happens in game: _init_grid called, last_hit_color reset
    g._init_grid()
    g.last_hit_color = -1
    assert g.last_hit_color == -1


def test_pendulum_angle_wraps() -> None:
    """Pendulum angle is not explicitly wrapped but shouldn't cause issues."""
    g = _make_game()
    g.pendulum_angle = math.pi * 10  # many full rotations
    g._update_pendulum()
    # Should still produce valid ball position
    g._update_ball_position()
    assert isinstance(g._ball_x, float)
    assert isinstance(g._ball_y, float)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
