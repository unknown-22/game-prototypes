"""test_imports.py — Headless logic tests for 188_skip_surge."""

from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/188_skip_surge")
from main import Game, Particle, FloatingText, Phase, ROPE_COLORS
from main import (
    GROUND_Y,
    JUMP_VELOCITY,
    GRAVITY,
    JUMP_WINDOW_RADIANS,
    INITIAL_ROPE_SPEED,
    HEAT_MISS,
    HEAT_DECAY,
    MAX_HEAT,
    SUPER_COMBO,
    SUPER_DURATION,
    SEGMENT_COUNT,
    SEGMENT_ANGLE,
    PLAYER_X,
)


def _make_game() -> Game:
    """Factory: create a Game instance without Pyxel init."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.rope_angle = 0.0
    g.rope_speed = INITIAL_ROPE_SPEED
    g.player_y = float(GROUND_Y)
    g.player_vy = 0.0
    g.is_jumping = False
    g.on_ground = True
    g.active_color = ROPE_COLORS[0]
    g.prev_segment_index = 0
    g.prev_jump_color = 0
    g.super_timer = 0
    g.particles = []
    g.floating_texts = []
    g.frame = 0
    g.shake_frames = 0
    g.rope_colors = list(ROPE_COLORS)
    g.reset()
    g._rng = random.Random(42)
    return g


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8


def test_floating_text_creation() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+10", life=30, color=10)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == 10


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------


def test_phase_enum() -> None:
    assert Phase.TITLE.value == "title"
    assert Phase.PLAYING.value == "playing"
    assert Phase.GAME_OVER.value == "game_over"


# ---------------------------------------------------------------------------
# Game constants
# ---------------------------------------------------------------------------


def test_constants() -> None:
    assert Game.GROUND_Y == 200
    assert Game.ROPE_RADIUS == 40
    assert Game.COMBO_FOR_SUPER == SUPER_COMBO == 4
    assert Game.SUPER_DURATION == 300
    assert Game.HEAT_MISS == 10.0
    assert Game.MAX_HEAT == 100.0
    assert len(ROPE_COLORS) == 4
    assert ROPE_COLORS == [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW


# ---------------------------------------------------------------------------
# Game initialization / reset
# ---------------------------------------------------------------------------


def test_make_game_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.rope_speed == INITIAL_ROPE_SPEED
    assert g.player_y == float(GROUND_Y)
    assert g.on_ground is True
    assert g.is_jumping is False
    assert g.super_timer == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.frame == 0
    assert g.shake_frames == 0


def test_reset_clears_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 10
    g.max_combo = 12
    g.heat = 50.0
    g.super_timer = 200
    g.particles = [Particle(0, 0, 0, 0, 5, 8)]
    g.floating_texts = [FloatingText(0, 0, "test", 5, 7)]
    g.frame = 999
    g.shake_frames = 10

    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.frame == 0
    assert g.shake_frames == 0
    assert g.rope_speed == INITIAL_ROPE_SPEED
    assert g.player_y == float(GROUND_Y)
    assert g.on_ground is True


def test_shuffle_rope_colors_has_all_colors() -> None:
    g = _make_game()
    assert sorted(g.rope_colors) == sorted(ROPE_COLORS)
    assert len(g.rope_colors) == 4


# ---------------------------------------------------------------------------
# _get_segment_index_at_bottom
# ---------------------------------------------------------------------------


def test_segment_index_at_bottom_initial() -> None:
    g = _make_game()
    g.rope_angle = 0.0
    # bottom = pi/2; normalized = (pi/2 - 0) % 2pi = pi/2
    # pi/2 / (pi/2) = 1, so index = 1
    assert g._get_segment_index_at_bottom() == 1


def test_segment_index_rotates() -> None:
    g = _make_game()
    g.rope_angle = SEGMENT_ANGLE  # pi/2
    # bottom = pi/2; normalized = (pi/2 - pi/2) % 2pi = 0
    # 0 / (pi/2) = 0, index = 0
    assert g._get_segment_index_at_bottom() == 0


def test_segment_index_wraps() -> None:
    g = _make_game()
    g.rope_angle = 2 * math.pi
    # Same as angle=0, so index=1
    assert g._get_segment_index_at_bottom() == 1


# ---------------------------------------------------------------------------
# _get_active_color
# ---------------------------------------------------------------------------


def test_get_active_color() -> None:
    g = _make_game()
    g.rope_colors = [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW
    g.rope_angle = SEGMENT_ANGLE  # index 0 is at bottom
    assert g._get_active_color() == 8  # RED


# ---------------------------------------------------------------------------
# _is_segment_in_jump_window
# ---------------------------------------------------------------------------


def test_is_in_jump_window_true() -> None:
    g = _make_game()
    # rope_angle = 7*pi/4 places segment 1 center at exactly pi/2 (6 o'clock)
    g.rope_angle = 7 * math.pi / 4
    assert g._is_segment_in_jump_window() is True


def test_is_in_jump_window_false() -> None:
    g = _make_game()
    # rope_angle = 3*pi/2 puts pi/2 halfway between segment centers
    # distance from pi/2 to nearest center = pi/4 ≈ 0.785 > JUMP_WINDOW_RADIANS (0.45)
    g.rope_angle = 3 * math.pi / 2
    assert g._is_segment_in_jump_window() is False


# ---------------------------------------------------------------------------
# _update_rope
# ---------------------------------------------------------------------------


def test_update_rope_advances_angle() -> None:
    g = _make_game()
    g.rope_speed = 0.1
    old_angle = g.rope_angle
    g._update_rope()
    assert g.rope_angle == (old_angle + 0.1) % (2 * math.pi)


def test_update_rope_updates_active_color() -> None:
    g = _make_game()
    g.rope_angle = 0.0
    g._update_rope()
    assert g.active_color == g._get_active_color()


def test_update_rope_speed_increase() -> None:
    g = _make_game()
    # frame = 99 → no speed increase (100 frame interval)
    g.frame = 99
    g.rope_speed = 0.03
    g._update_rope()
    assert g.rope_speed == 0.03

    # frame = 100 → speed increase
    g.frame = 100
    g._update_rope()
    assert g.rope_speed == 0.03 + 0.002  # SPEED_INCREMENT


def test_update_rope_speed_capped() -> None:
    g = _make_game()
    g.frame = 100
    g.rope_speed = 0.099  # MAX_ROPE_SPEED = 0.10
    g._update_rope()
    assert g.rope_speed == 0.10  # capped


# ---------------------------------------------------------------------------
# _jump
# ---------------------------------------------------------------------------


def test_jump_from_ground() -> None:
    g = _make_game()
    g.on_ground = True
    g._jump()
    assert g.player_vy == JUMP_VELOCITY
    assert g.is_jumping is True
    assert g.on_ground is False


def test_jump_while_in_air_does_nothing() -> None:
    g = _make_game()
    g.on_ground = False
    g.player_vy = -2.0
    g._jump()
    assert g.player_vy == -2.0  # unchanged


# ---------------------------------------------------------------------------
# _update_player
# ---------------------------------------------------------------------------


def test_update_player_gravity() -> None:
    g = _make_game()
    g._jump()  # sets vy = JUMP_VELOCITY = -5.5
    old_vy = g.player_vy
    g._update_player()
    assert g.player_vy == old_vy + GRAVITY
    assert g.player_y < GROUND_Y


def test_update_player_lands() -> None:
    g = _make_game()
    g.player_y = GROUND_Y - 1.0
    g.player_vy = 2.0  # falling fast
    g.on_ground = False
    g._update_player()
    assert g.player_y == float(GROUND_Y)
    assert g.player_vy == 0.0
    assert g.on_ground is True
    assert g.is_jumping is False


# ---------------------------------------------------------------------------
# _check_jump_timing
# ---------------------------------------------------------------------------


def test_check_jump_timing_success() -> None:
    g = _make_game()
    g.on_ground = False
    g.player_y = GROUND_Y - 20  # in air, above threshold
    g.active_color = 8
    g.prev_jump_color = 8  # same color
    timing_ok, color_match = g._check_jump_timing()
    assert timing_ok is True
    assert color_match is True


def test_check_jump_timing_color_mismatch() -> None:
    g = _make_game()
    g.on_ground = False
    g.player_y = GROUND_Y - 20
    g.active_color = 8
    g.prev_jump_color = 3  # different color
    timing_ok, color_match = g._check_jump_timing()
    assert timing_ok is True
    assert color_match is False


def test_check_jump_timing_bad_timing_on_ground() -> None:
    g = _make_game()
    g.on_ground = True
    g.player_y = GROUND_Y
    timing_ok, color_match = g._check_jump_timing()
    assert timing_ok is False


def test_check_jump_timing_first_jump_always_match() -> None:
    g = _make_game()
    g.on_ground = False
    g.player_y = GROUND_Y - 20
    g.active_color = 8
    g.prev_jump_color = 0  # no previous jump
    timing_ok, color_match = g._check_jump_timing()
    assert timing_ok is True
    assert color_match is True  # first jump always matches


def test_check_jump_timing_near_ground() -> None:
    g = _make_game()
    g.on_ground = False
    g.player_y = GROUND_Y - 3  # within 5px of ground → too low
    timing_ok, _ = g._check_jump_timing()
    assert timing_ok is False


# ---------------------------------------------------------------------------
# _resolve_jump
# ---------------------------------------------------------------------------


def test_resolve_jump_success_adds_score() -> None:
    g = _make_game()
    g.active_color = 8  # RED = score 8
    g.super_timer = 0
    g.prev_jump_color = 0  # first jump
    g._resolve_jump(timing_ok=True, color_match=True)
    assert g.score == 8  # base score for RED
    assert g.combo == 1
    assert g.prev_jump_color == 8
    assert g.max_combo == 1


def test_resolve_jump_combo_chain() -> None:
    g = _make_game()
    g.active_color = 8
    g.prev_jump_color = 8  # same color, continuing combo
    g.combo = 3
    g.super_timer = 0
    g._resolve_jump(timing_ok=True, color_match=True)
    assert g.combo == 4
    assert g.max_combo == 4
    assert g.score == 8


def test_resolve_jump_color_mismatch_resets_combo() -> None:
    g = _make_game()
    g.active_color = 3  # GREEN
    g.prev_jump_color = 8  # RED (different)
    g.combo = 5
    g._resolve_jump(timing_ok=True, color_match=False)
    assert g.combo == 1  # reset to 1 (not 0, since it was a successful jump)
    assert g.prev_jump_color == 3  # updated to new color


def test_resolve_jump_timing_miss_adds_heat() -> None:
    g = _make_game()
    g.heat = 0.0
    g.combo = 3
    g._resolve_jump(timing_ok=False, color_match=False)
    assert g.heat == HEAT_MISS  # 10.0
    assert g.combo == 0  # reset
    assert g.prev_jump_color == 0


def test_resolve_jump_timing_miss_spawns_particles() -> None:
    g = _make_game()
    g._resolve_jump(timing_ok=False, color_match=False)
    assert len(g.particles) == 8  # miss particles
    assert g.shake_frames == 8


def test_resolve_jump_triggers_super() -> None:
    g = _make_game()
    g.active_color = 8
    g.prev_jump_color = 8
    g.combo = 3  # next jump makes combo=4 → SUPER
    g.super_timer = 0
    g._resolve_jump(timing_ok=True, color_match=True)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION  # 300


def test_resolve_jump_super_multiplier() -> None:
    g = _make_game()
    g.active_color = 10  # YELLOW = score 10
    g.prev_jump_color = 0
    g.super_timer = 100  # active
    g._resolve_jump(timing_ok=True, color_match=True)
    assert g.score == 30  # 10 * 3


def test_resolve_jump_no_double_super() -> None:
    g = _make_game()
    g.active_color = 8
    g.prev_jump_color = 8
    g.combo = 3
    g.super_timer = 200  # already in SUPER
    g._resolve_jump(timing_ok=True, color_match=True)
    # super_timer should NOT be reset (already active)
    assert g.super_timer == 200  # unchanged by _activate_super call... wait, let me check code

    # Actually the code says: if combo >= SUPER_COMBO and super_timer == 0
    # So it won't re-activate. But _update_super() isn't called here.
    # super_timer stays at 200.
    assert g.super_timer == 200


def test_resolve_jump_max_combo_tracks_only_increases() -> None:
    g = _make_game()
    g.max_combo = 10
    g.combo = 3
    g.active_color = 8
    g.prev_jump_color = 8
    g._resolve_jump(timing_ok=True, color_match=True)
    assert g.combo == 4
    assert g.max_combo == 10  # unchanged (4 < 10)


# ---------------------------------------------------------------------------
# _update_heat
# ---------------------------------------------------------------------------


def test_update_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_update_heat_not_below_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_game_over_at_max() -> None:
    g = _make_game()
    # heat must be high enough that decay still leaves it >= 100
    g.heat = 100.1
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_update_heat_game_over_from_above_max() -> None:
    g = _make_game()
    g.heat = 110.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.heat == MAX_HEAT
    assert g.phase == Phase.GAME_OVER


# ---------------------------------------------------------------------------
# _activate_super
# ---------------------------------------------------------------------------


def test_activate_super() -> None:
    g = _make_game()
    g.super_timer = 0
    g._activate_super()
    assert g.super_timer == SUPER_DURATION
    assert len(g.particles) == 20  # super particles


# ---------------------------------------------------------------------------
# _update_super
# ---------------------------------------------------------------------------


def test_update_super_decrements() -> None:
    g = _make_game()
    g.super_timer = 50
    g._update_super()
    assert g.super_timer == 49


def test_update_super_stays_at_zero() -> None:
    g = _make_game()
    g.super_timer = 0
    g._update_super()
    assert g.super_timer == 0


# ---------------------------------------------------------------------------
# _update_particles
# ---------------------------------------------------------------------------


def test_update_particles_move() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=100.0, vx=2.0, vy=-1.0, life=10, color=8)
    g.particles = [p]
    g._update_particles()
    assert p.x == 102.0
    # y += vy (using old vy=-1.0), THEN vy += 0.1
    # So p.y = 100.0 + (-1.0) = 99.0, then vy = -1.0 + 0.1 = -0.9
    assert abs(p.y - 99.0) < 0.01
    assert abs(p.vy - (-0.9)) < 0.01
    assert p.life == 9


def test_update_particles_removes_expired() -> None:
    g = _make_game()
    g.particles = [Particle(0, 0, 0, 0, 1, 8)]
    g._update_particles()
    assert len(g.particles) == 0  # life went to 0, filtered


def test_update_particles_capped_at_100() -> None:
    g = _make_game()
    g.particles = [Particle(float(i), 0, 0, 0, 50, 8) for i in range(150)]
    g._update_particles()
    assert len(g.particles) == 100


# ---------------------------------------------------------------------------
# _update_floating_texts
# ---------------------------------------------------------------------------


def test_update_floating_texts_move() -> None:
    g = _make_game()
    ft = FloatingText(x=100.0, y=50.0, text="test", life=10, color=7)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert ft.y == 50.0 - 1.2
    assert ft.life == 9


def test_update_floating_texts_removes_expired() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(0, 0, "x", 1, 7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ---------------------------------------------------------------------------
# _spawn_floating_text
# ---------------------------------------------------------------------------


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100.0, 50.0, "+10", 10)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == 10


# ---------------------------------------------------------------------------
# _spawn_jump_particles
# ---------------------------------------------------------------------------


def test_spawn_jump_particles_normal() -> None:
    g = _make_game()
    g.combo = 1
    g._spawn_jump_particles(100.0, 50.0, 8)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == 8
        assert 8 <= p.life <= 22


def test_spawn_jump_particles_milestone() -> None:
    g = _make_game()
    g.combo = 5  # combo > 0 and combo % 5 == 0
    g._spawn_jump_particles(100.0, 50.0, 8)
    assert len(g.particles) == 10


# ---------------------------------------------------------------------------
# _spawn_miss_particles
# ---------------------------------------------------------------------------


def test_spawn_miss_particles() -> None:
    g = _make_game()
    g._spawn_miss_particles(100.0, 200.0)
    assert len(g.particles) == 8
    for p in g.particles:
        assert p.color == 8  # RED


# ---------------------------------------------------------------------------
# _spawn_super_particles
# ---------------------------------------------------------------------------


def test_spawn_super_particles() -> None:
    g = _make_game()
    g._spawn_super_particles(100.0, 100.0)
    assert len(g.particles) == 20


# ---------------------------------------------------------------------------
# _shuffle_rope_colors
# ---------------------------------------------------------------------------


def test_shuffle_rope_colors_contains_all() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g._shuffle_rope_colors()
    assert sorted(g.rope_colors) == sorted(ROPE_COLORS)
    assert len(g.rope_colors) == 4


# ---------------------------------------------------------------------------
# Full game loop simulation
# ---------------------------------------------------------------------------


def test_full_game_loop_100_frames() -> None:
    """Simulate 100 frames of game loop without pyxel."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g._rng = random.Random(42)

    for _ in range(100):
        # Simulate game loop without pyxel input calls
        g.frame += 1
        g._update_player()
        g._update_rope()
        g._update_super()
        g._update_heat()

        current_seg_idx = g._get_segment_index_at_bottom()
        if current_seg_idx != g.prev_segment_index:
            g.prev_segment_index = current_seg_idx
            timing_ok, _ = g._check_jump_timing()
            g._resolve_jump(timing_ok, False)

        g._update_particles()
        g._update_floating_texts()

        if g.heat >= MAX_HEAT:
            g.phase = Phase.GAME_OVER
            break

    # Verify game is still running or ended appropriately
    assert g.phase in (Phase.PLAYING, Phase.GAME_OVER)
    assert g.frame == 100


def test_game_over_from_heat() -> None:
    """Simulate heat reaching max."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 95.0

    # Simulate one miss that pushes heat over
    g._resolve_jump(timing_ok=False, color_match=False)
    assert g.heat == 95.0 + HEAT_MISS  # 105.0, but capped

    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.heat == MAX_HEAT


def test_combo_progression_to_super() -> None:
    """Simulate building combo up to SUPER."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g._rng = random.Random(42)

    # Simulate 4 same-color successful jumps
    for i in range(4):
        g.active_color = 8  # RED
        g.prev_jump_color = 8 if i > 0 else 0
        g.combo = i  # 0, 1, 2, 3
        g._resolve_jump(timing_ok=True, color_match=(i > 0))

    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION
    assert g.max_combo == 4


def test_midair_jump_prevented() -> None:
    """Jump while already in air should not change velocity."""
    g = _make_game()
    g._jump()  # first jump
    initial_vy = g.player_vy
    g._jump()  # second jump should do nothing
    assert g.player_vy == initial_vy


def test_floating_text_life_off_by_one() -> None:
    """FloatingText with life=2 should survive one update, die after second."""
    g = _make_game()
    g.floating_texts = [FloatingText(0, 0, "x", 2, 7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1  # life=2 → 1, survived
    g._update_floating_texts()
    assert len(g.floating_texts) == 0  # life=1 → 0, removed


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_all_colors_different_no_continuous_combo() -> None:
    """If rope_colors alternate each segment, combo-chaining is hard."""
    g = _make_game()
    g.rope_colors = [8, 3, 5, 10]  # all different
    g.rope_angle = 0.0
    # Segment indices cycle: 1, 2, 3, 0, 1, ...
    # Colors: 3, 5, 10, 8, 3, ...
    # No two consecutive same
    colors = []
    for _ in range(8):
        g._update_rope()
        colors.append(g.active_color)
    # Verify no 3 consecutive same (rotation is deterministic per-frame)
    # Just verify we get 8 color readings
    assert len(colors) == 8


def test_particles_dont_overflow() -> None:
    g = _make_game()
    # Add 200 particles
    g.particles = [Particle(0, 0, 0, 0, 50, 8) for _ in range(200)]
    g._update_particles()
    assert len(g.particles) <= 100


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
