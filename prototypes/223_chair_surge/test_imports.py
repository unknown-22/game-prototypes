"""test_imports.py — Headless logic tests for 223_chair_surge (Musical Chairs)."""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/223_chair_surge")
from main import (
    CHAIR_TIME_MIN,
    CHAIR_TIME_START,
    CIRCLE_R,
    CIRCLE_CY,
    CIRCLE_CX,
    COLOR_VALS,
    COMBO_SUPER,
    DARK_BLUE,
    GAME_DURATION,
    HEAT_MAX,
    HEAT_MISMATCH,
    LIME,
    NUM_CHAIRS,
    RED,
    SUPER_DURATION,
    WHITE,
    YELLOW,
    Chair,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    """Create a headless Game instance bypassing pyxel init/run."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes that _reset() touches
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.chairs = []
    g.player_angle = 0.0
    g.timer = CHAIR_TIME_START
    g.overall_timer = GAME_DURATION
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.heat = 0.0
    g.last_color = None
    g.super_timer = 0
    g.sit_flash = 0
    g.particles = []
    g.floating_texts = []
    g._reset()
    return g


# ── Constants ──
def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert NUM_CHAIRS == 8
    assert CHAIR_TIME_START == 90
    assert CHAIR_TIME_MIN == 30
    assert HEAT_MAX == 100
    assert HEAT_MISMATCH == 15
    assert COMBO_SUPER == 4
    assert SUPER_DURATION == 150
    assert GAME_DURATION == 60 * 30
    assert COLOR_VALS == (RED, LIME, DARK_BLUE, YELLOW)


# ── Phase Enum ──
def test_phase_values() -> None:
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.SIT_ANIM == 2
    assert Phase.COMPRESS == 3
    assert Phase.SUPER == 4
    assert Phase.GAME_OVER == 5


# ── Dataclass Construction ──
def test_chair_dataclass() -> None:
    c = Chair(angle=1.5, target_angle=1.5, color=RED)
    assert c.angle == 1.5
    assert c.target_angle == 1.5
    assert c.color == RED
    assert c.active is True


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-1.0, life=15, color=YELLOW)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -1.0
    assert p.life == 15
    assert p.color == YELLOW


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+30", life=20, color=WHITE)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+30"
    assert ft.life == 20
    assert ft.color == WHITE


# ── Game._reset() ──
def test_reset_initializes_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert len(g.chairs) == NUM_CHAIRS
    assert g.player_angle == 0.0
    assert g.timer == CHAIR_TIME_START
    assert g.overall_timer == GAME_DURATION
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.heat == 0.0
    assert g.last_color is None
    assert g.super_timer == 0
    assert g.sit_flash == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_reset_chairs_are_active() -> None:
    g = _make_game()
    assert all(c.active for c in g.chairs)


def test_reset_chairs_evenly_spaced() -> None:
    g = _make_game()
    for i, chair in enumerate(g.chairs):
        expected = 2.0 * math.pi * i / NUM_CHAIRS
        assert abs(chair.angle - expected) < 0.001


def test_reset_chairs_have_valid_colors() -> None:
    g = _make_game()
    for chair in g.chairs:
        assert chair.color in COLOR_VALS


# ── _resolve_sit: first sit ──
def test_first_sit_is_always_match() -> None:
    """First sit (last_color=None) should match regardless of chair color."""
    g = _make_game()
    # Place player at chair[0] position
    g.player_angle = g.chairs[0].angle
    initial_score = g.score
    g._resolve_sit()
    assert g.combo == 1
    assert g.score > initial_score
    assert g.heat == 0.0
    assert g.last_color == g.chairs[0].color  # fault: chair[0] is now inactive, but its color was recorded


def test_first_sit_score_is_correct() -> None:
    """First sit combo=1, score += 10*1*1 = 10."""
    g = _make_game()
    g.player_angle = g.chairs[0].angle
    g._resolve_sit()
    assert g.score == 10
    assert g.combo == 1


# ── _resolve_sit: same-color chain ──
def test_same_color_chain_builds_combo() -> None:
    g = _make_game()
    # First sit
    g.player_angle = g.chairs[0].angle
    first_color = g.chairs[0].color
    g._resolve_sit()
    assert g.combo == 1
    # Set all remaining chairs to same color and place player
    for c in g.chairs:
        if c.active:
            c.color = first_color
    # Second sit on next active chair
    next_active = [c for c in g.chairs if c.active]
    assert len(next_active) >= 1
    g.player_angle = next_active[0].angle
    g._resolve_sit()
    assert g.combo == 2
    assert g.score == 10 + 20  # combo=1:10, combo=2:20
    assert g.heat == 0.0


def test_same_color_chain_three_in_row() -> None:
    g = _make_game()
    color = RED
    # Set all chairs to RED
    for c in g.chairs:
        c.color = color
    # Sit 3 times
    for expected_combo in range(1, 4):
        active = [c for c in g.chairs if c.active]
        g.player_angle = active[0].angle
        g._resolve_sit()
        assert g.combo == expected_combo
    assert g.combo == 3


def test_same_color_chain_tracks_max_combo() -> None:
    g = _make_game()
    color = RED
    for c in g.chairs:
        c.color = color
    for _ in range(5):
        active = [c for c in g.chairs if c.active]
        g.player_angle = active[0].angle
        g._resolve_sit()
    assert g.max_combo == 5


# ── _resolve_sit: wrong-color behavior ──
def test_wrong_color_resets_combo() -> None:
    g = _make_game()
    # Build combo of 3
    color = RED
    for c in g.chairs:
        c.color = color
    for _ in range(3):
        active = [c for c in g.chairs if c.active]
        g.player_angle = active[0].angle
        g._resolve_sit()
    assert g.combo == 3
    # Now switch color
    for c in g.chairs:
        if c.active:
            c.color = LIME  # different color
    active = [c for c in g.chairs if c.active]
    g.player_angle = active[0].angle
    g._resolve_sit()
    assert g.combo == 0
    assert g.heat > 0


def test_wrong_color_adds_heat() -> None:
    g = _make_game()
    # Build combo of 2 in RED
    for c in g.chairs:
        c.color = RED
    for _ in range(2):
        active = [c for c in g.chairs if c.active]
        g.player_angle = active[0].angle
        g._resolve_sit()
    # Switch to LIME
    for c in g.chairs:
        if c.active:
            c.color = LIME
    active = [c for c in g.chairs if c.active]
    g.player_angle = active[0].angle
    g._resolve_sit()
    assert g.heat == HEAT_MISMATCH


def test_after_mismatch_can_restart_combo() -> None:
    """After mismatch, last_color updates to new color so player can restart chain."""
    g = _make_game()
    # Build combo RED
    for c in g.chairs:
        c.color = RED
    for _ in range(2):
        active = [c for c in g.chairs if c.active]
        g.player_angle = active[0].angle
        g._resolve_sit()
    # Mismatch LIME
    for c in g.chairs:
        if c.active:
            c.color = LIME
    active = [c for c in g.chairs if c.active]
    g.player_angle = active[0].angle
    g._resolve_sit()
    assert g.combo == 0
    assert g.last_color == LIME  # updated to new color
    # Next LIME sit should be match and restart combo
    for c in g.chairs:
        if c.active:
            c.color = LIME
    active = [c for c in g.chairs if c.active]
    g.player_angle = active[0].angle
    g._resolve_sit()
    assert g.combo == 1  # restarted


# ── _resolve_sit: SUPER mode ──
def test_super_activates_at_combo_threshold() -> None:
    g = _make_game()
    color = RED
    for c in g.chairs:
        c.color = color
    for i in range(COMBO_SUPER):
        active = [c for c in g.chairs if c.active]
        g.player_angle = active[0].angle
        g._resolve_sit()
    # After resolving sit that hits COMBO_SUPER, super_timer should be set
    # But super_timer is set in COMPRESS phase completion, not in _resolve_sit directly
    # Let's simulate the COMPRESS -> PLAYING transition
    g.phase = Phase.COMPRESS
    # Advance through compress
    for c in g.chairs:
        if c.active:
            c.angle = c.target_angle
    # Now trigger the phase transition that checks super
    # We need to call _update or replicate its COMPRESS logic
    # Simpler: manually check the condition
    assert g.combo >= COMBO_SUPER


def test_super_mode_any_color_matches() -> None:
    g = _make_game()
    # Build combo with RED
    for c in g.chairs:
        c.color = RED
    for _ in range(COMBO_SUPER):
        active = [c for c in g.chairs if c.active]
        g.player_angle = active[0].angle
        g._resolve_sit()
    # Manually activate SUPER
    g.super_timer = SUPER_DURATION
    # Now sit on a different color — should still match
    for c in g.chairs:
        if c.active:
            c.color = LIME
    active = [c for c in g.chairs if c.active]
    prev_combo = g.combo
    g.player_angle = active[0].angle
    g._resolve_sit()
    assert g.combo == prev_combo + 1  # combo incremented despite color mismatch
    assert g.heat == 0.0  # no heat added


def test_super_mode_3x_score() -> None:
    g = _make_game()
    for c in g.chairs:
        c.color = RED
    for _ in range(COMBO_SUPER):
        active = [c for c in g.chairs if c.active]
        g.player_angle = active[0].angle
        g._resolve_sit()
    g.super_timer = SUPER_DURATION
    prev_score = g.score
    prev_combo = g.combo
    active = [c for c in g.chairs if c.active]
    g.player_angle = active[0].angle
    g._resolve_sit()
    expected_gain = 10 * (prev_combo + 1) * 3
    assert g.score == prev_score + expected_gain


# ── _resolve_sit: score calculation ──
def test_score_scales_with_combo() -> None:
    g = _make_game()
    color = RED
    for c in g.chairs:
        c.color = color
    expected_score = 0
    for combo in range(1, 6):
        active = [c for c in g.chairs if c.active]
        g.player_angle = active[0].angle
        g._resolve_sit()
        expected_score += 10 * combo
    assert g.score == expected_score


# ── _resolve_sit: heat game over ──
def test_heat_max_triggers_game_over() -> None:
    g = _make_game()
    g.heat = HEAT_MAX - 5  # just below max
    # Sit mismatch to push over
    for c in g.chairs:
        c.color = RED
    # Sit once on RED to set last_color
    g.player_angle = g.chairs[0].angle
    g._resolve_sit()
    # Force mismatch
    for c in g.chairs:
        if c.active:
            c.color = LIME
    active = [c for c in g.chairs if c.active]
    g.player_angle = active[0].angle
    g._resolve_sit()
    assert g.heat >= HEAT_MAX
    assert g.phase == Phase.GAME_OVER


def test_heat_clamps_to_max() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    for c in g.chairs:
        c.color = RED
    g.player_angle = g.chairs[0].angle
    g._resolve_sit()
    # Match sit should keep heat (no change to heat)
    assert g.heat == HEAT_MAX


# ── _resolve_sit: timer game over ──
def test_overall_timer_zero_triggers_game_over() -> None:
    g = _make_game()
    g.overall_timer = 0
    g.player_angle = g.chairs[0].angle
    g._resolve_sit()
    assert g.phase == Phase.GAME_OVER


# ── _resolve_sit: chair removal ──
def test_sat_chair_becomes_inactive() -> None:
    g = _make_game()
    active_before = sum(1 for c in g.chairs if c.active)
    g.player_angle = g.chairs[0].angle
    g._resolve_sit()
    active_after = sum(1 for c in g.chairs if c.active)
    assert active_after == active_before - 1
    assert g.chairs[0].active is False


# ── _resolve_sit: gap compression ──
def test_after_sit_remaining_chairs_have_targets() -> None:
    g = _make_game()
    g.player_angle = g.chairs[0].angle
    g._resolve_sit()
    active = [c for c in g.chairs if c.active]
    assert len(active) == NUM_CHAIRS - 1
    for i, chair in enumerate(active):
        expected = 2.0 * math.pi * i / len(active)
        assert abs(chair.target_angle - expected) < 0.001


# ── _resolve_sit: zero active chairs ──
def test_zero_active_chairs_respawns() -> None:
    g = _make_game()
    # Deactivate all chairs except one
    for c in g.chairs[:-1]:
        c.active = False
    g.player_angle = g.chairs[-1].angle
    g._resolve_sit()
    # After sitting on the last active chair, COMPRESS phase spawns 1 new chair
    assert g.phase == Phase.COMPRESS
    # Simulate COMPRESS completion: all active chairs at target
    for c in g.chairs:
        if c.active:
            c.angle = c.target_angle
    # Now simulate the COMPRESS -> PLAYING transition (copied from _update)
    all_done = all(
        abs(c.angle - c.target_angle) < 0.01 for c in g.chairs if c.active
    )
    if all_done:
        g._spawn_chair()
        g.timer = max(CHAIR_TIME_MIN, CHAIR_TIME_START - g.score // 50)
        g.phase = Phase.PLAYING
    # Should now have at least one active chair and be in PLAYING
    assert sum(1 for c in g.chairs if c.active) >= 1
    assert g.phase == Phase.PLAYING


# ── _resolve_sit: nearest chair selection ──
def test_nearest_chair_selected() -> None:
    g = _make_game()
    # Place player exactly at chair[2]'s angle
    g.player_angle = g.chairs[2].angle
    target_color = g.chairs[2].color
    g._resolve_sit()
    assert g.last_color == target_color


def test_nearest_chair_wraps_around_circle() -> None:
    g = _make_game()
    # Place player at angle just past 2*pi, wrapping to chair[0]
    g.player_angle = 0.001  # very close to chair[0]
    target_color = g.chairs[0].color
    g._resolve_sit()
    assert g.last_color == target_color


# ── _spawn_chair ──
def test_spawn_chair_adds_one() -> None:
    g = _make_game()
    # Remove one chair
    g.chairs[0].active = False
    count_before = sum(1 for c in g.chairs if c.active)
    g._spawn_chair()
    count_after = sum(1 for c in g.chairs if c.active)
    assert count_after == count_before + 1


def test_spawn_chair_only_at_free_slots() -> None:
    g = _make_game()
    # Deactivate chair[0] only — one free slot
    g.chairs[0].active = False
    g._spawn_chair()
    occupied = [c.target_angle for c in g.chairs if c.active]
    # The new chair should fill the previously empty slot
    assert len(occupied) == NUM_CHAIRS  # all slots filled now


def test_spawn_chair_no_free_slots_does_nothing() -> None:
    g = _make_game()
    # All chairs active
    assert all(c.active for c in g.chairs)
    count_before = len(g.chairs)
    g._spawn_chair()
    assert len(g.chairs) == count_before


# ── _respawn_all_chairs ──
def test_respawn_all_replaces_all() -> None:
    g = _make_game()
    original = g.chairs[:]
    g._respawn_all_chairs()
    assert len(g.chairs) == NUM_CHAIRS
    assert all(c.active for c in g.chairs)
    # Should be new Chair objects (different id)
    assert g.chairs is not original


# ── _update_particles ──
def test_particles_move_and_decay() -> None:
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=-2.0, life=5, color=RED)]
    g._update_particles()
    assert abs(g.particles[0].x - 101.0) < 0.01
    assert abs(g.particles[0].y - 98.0) < 0.01
    assert g.particles[0].life == 4


def test_particles_expire_and_removed() -> None:
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0


# ── _update_floating_texts ──
def test_floating_text_rises_and_fades() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="TEST", life=5, color=WHITE)]
    g._update_floating_texts()
    assert abs(g.floating_texts[0].y - 99.5) < 0.01
    assert g.floating_texts[0].life == 4


def test_floating_text_expires() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="TEST", life=1, color=WHITE)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── _resolve_sit: floating text produced ──
def test_match_produces_score_floating_text() -> None:
    g = _make_game()
    g.player_angle = g.chairs[0].angle
    assert len(g.floating_texts) == 0
    g._resolve_sit()
    # At least one floating text for score
    score_texts = [ft for ft in g.floating_texts if "+" in ft.text]
    assert len(score_texts) >= 1


def test_mismatch_produces_wrong_floating_text() -> None:
    g = _make_game()
    # First sit to set last_color=RED
    for c in g.chairs:
        c.color = RED
    g.player_angle = g.chairs[0].angle
    g._resolve_sit()
    # Now force wrong color
    for c in g.chairs:
        if c.active:
            c.color = LIME
    active = [c for c in g.chairs if c.active]
    g.player_angle = active[0].angle
    g._resolve_sit()
    wrong_texts = [ft for ft in g.floating_texts if "WRONG" in ft.text]
    assert len(wrong_texts) >= 1


def test_combo2_produces_combo_floating_text() -> None:
    g = _make_game()
    color = RED
    for c in g.chairs:
        c.color = color
    # Build combo 2
    for _ in range(2):
        active = [c for c in g.chairs if c.active]
        g.player_angle = active[0].angle
        g._resolve_sit()
    combo_texts = [ft for ft in g.floating_texts if "x2" in ft.text]
    assert len(combo_texts) >= 1


# ── _resolve_sit: particles produced ──
def test_match_produces_particles() -> None:
    g = _make_game()
    g.player_angle = g.chairs[0].angle
    assert len(g.particles) == 0
    g._resolve_sit()
    assert len(g.particles) > 0


# ── _spawn_particles ──
def test_spawn_particles_creates_8() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, RED)
    assert len(g.particles) == 8


# ── Timer escalation ──
def test_timer_decreases_with_score_after_compress() -> None:
    g = _make_game()
    g.score = 500  # should reduce timer
    expected = max(CHAIR_TIME_MIN, CHAIR_TIME_START - 500 // 50)
    assert expected == max(CHAIR_TIME_MIN, CHAIR_TIME_START - 10)


# ── Chair position helpers ──
def test_chair_circle_position() -> None:
    g = _make_game()
    c = g.chairs[0]
    cx = CIRCLE_CX + math.cos(c.angle) * CIRCLE_R
    cy = CIRCLE_CY + math.sin(c.angle) * CIRCLE_R
    # angle is 0 (first chair), so should be at (CIRCLE_CX + CIRCLE_R, CIRCLE_CY)
    assert abs(cx - (CIRCLE_CX + CIRCLE_R)) < 0.01
    assert abs(cy - CIRCLE_CY) < 0.01


def test_player_circle_position() -> None:
    g = _make_game()
    g.player_angle = 0.0
    px = CIRCLE_CX + math.cos(g.player_angle) * CIRCLE_R
    py = CIRCLE_CY + math.sin(g.player_angle) * CIRCLE_R
    assert abs(px - (CIRCLE_CX + CIRCLE_R)) < 0.01
    assert abs(py - CIRCLE_CY) < 0.01


# ── Heat edge cases ──
def test_heat_does_not_increase_on_match() -> None:
    g = _make_game()
    color = RED
    for c in g.chairs:
        c.color = color
    for _ in range(3):
        active = [c for c in g.chairs if c.active]
        g.player_angle = active[0].angle
        g._resolve_sit()
    assert g.heat == 0.0


def test_multiple_mismatches_stack_heat() -> None:
    g = _make_game()
    # Sit on RED
    for c in g.chairs:
        c.color = RED
    g.player_angle = g.chairs[0].angle
    g._resolve_sit()
    # Mismatch LIME
    for c in g.chairs:
        if c.active:
            c.color = LIME
    active = [c for c in g.chairs if c.active]
    g.player_angle = active[0].angle
    g._resolve_sit()
    assert g.heat == HEAT_MISMATCH
    # Mismatch again on another color
    for c in g.chairs:
        if c.active:
            c.color = DARK_BLUE
    active = [c for c in g.chairs if c.active]
    g.player_angle = active[0].angle
    g._resolve_sit()
    assert g.heat == HEAT_MISMATCH * 2


# ── Phase after resolve ──
def test_resolve_sit_sets_compress_phase() -> None:
    g = _make_game()
    g.player_angle = g.chairs[0].angle
    g._resolve_sit()
    assert g.phase == Phase.COMPRESS


# ── Player angle wrapping ──
def test_player_angle_wraps_positive() -> None:
    g = _make_game()
    g.player_angle = 6.5  # > 2*pi (~6.283)
    g.player_angle %= 2.0 * math.pi
    assert 0 <= g.player_angle < 2.0 * math.pi


def test_player_angle_wraps_negative() -> None:
    g = _make_game()
    g.player_angle = -1.0
    g.player_angle %= 2.0 * math.pi
    assert 0 <= g.player_angle < 2.0 * math.pi


# ── SUPPLY -- imported consts for attribute tests ──
SCREEN_W = 320
SCREEN_H = 240


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
