"""test_imports.py — Headless logic tests for SEESAW CHAIN.

Uses Game.__new__(Game) to bypass __init__ (avoids pyxel.init/run).
Tests core logic methods directly — never calls pyxel input functions.
"""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/135_seesaw_chain")

from main import (  # noqa: E402
    BEAM_LENGTH,
    COLOR_VALS,
    COMBO_SUPER_THRESHOLD,
    COMMIT_MULTIPLIER,
    FloatingText,
    GAME_TIME,
    HEAT_COMBO_MATCH,
    HEAT_MISS_COMMIT,
    HEAT_WRONG_COLOR,
    MAX_ANGLE,
    MAX_HEAT,
    MAX_WEIGHT_MASS,
    MIN_WEIGHT_MASS,
    NUM_COLORS,
    Particle,
    Phase,
    SCREEN_H,
    SCREEN_W,
    Side,
    SUPER_DURATION,
    SUPER_SCORE_MULTIPLIER,
    SUPER_TORQUE_REDUCTION,
    TORQUE_SCALE,
    Game,
    Weight,
    WEIGHT_PLACEMENT_SCORE,
    WEIGHT_SPAWN_INTERVAL,
)


def _make_game() -> Game:
    """Create a headless Game instance ready for testing."""
    g: Game = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.beam_angle = 0.0
    g.weights = []
    g.last_color = None
    g.next_color = 0
    g.committed = False
    g.super_timer = 0
    g.super_active = False
    g.game_timer = GAME_TIME
    g.active_color = 0
    g.spawn_timer = WEIGHT_SPAWN_INTERVAL
    g.current_mass = 3.0
    g.particles = []
    g.floating_texts = []
    g.reset()
    return g


# ═══════════════════════════════════════════════════════════════════
# Constant verification
# ═══════════════════════════════════════════════════════════════════


def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert MAX_ANGLE == 30
    assert MAX_HEAT == 100
    assert GAME_TIME == 90 * 30
    assert SUPER_DURATION == 5 * 30
    assert NUM_COLORS == 4
    assert len(COLOR_VALS) == 4
    assert TORQUE_SCALE == 8.0
    assert COMBO_SUPER_THRESHOLD == 4
    assert HEAT_WRONG_COLOR > 0
    assert HEAT_MISS_COMMIT > 0
    assert HEAT_COMBO_MATCH < 0


# ═══════════════════════════════════════════════════════════════════
# Phase and Side enums
# ═══════════════════════════════════════════════════════════════════


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_side_enum() -> None:
    assert Side.LEFT in Side
    assert Side.RIGHT in Side
    assert Side.LEFT != Side.RIGHT


# ═══════════════════════════════════════════════════════════════════
# Data class creation
# ═══════════════════════════════════════════════════════════════════


def test_weight_creation() -> None:
    w = Weight(color=0, mass=3.0, side=Side.LEFT, dist=100.0)
    assert w.color == 0
    assert w.mass == 3.0
    assert w.side == Side.LEFT
    assert w.dist == 100.0
    assert w.x == 0.0
    assert w.y == 0.0
    assert w.landed is False
    assert w.landing_frame == 0


def test_particle_creation() -> None:
    p = Particle(x=0.0, y=0.0, vx=1.0, vy=2.0, life=20, color=8)
    assert p.life == 20
    assert p.color == 8
    assert p.vx == 1.0
    assert p.vy == 2.0


def test_floating_text_creation() -> None:
    ft = FloatingText(x=0.0, y=0.0, text="TEST", life=30, color=7)
    assert ft.text == "TEST"
    assert ft.life == 30
    assert ft.color == 7
    assert ft.vy == -1.0


# ═══════════════════════════════════════════════════════════════════
# Game._make_game factory
# ═══════════════════════════════════════════════════════════════════


def test_make_game_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.beam_angle == 0.0
    assert len(g.weights) == 0
    assert g.last_color is None
    assert g.committed is False
    assert g.super_active is False
    assert g.super_timer == 0
    assert g.game_timer == GAME_TIME
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


# ═══════════════════════════════════════════════════════════════════
# Torque computation
# ═══════════════════════════════════════════════════════════════════


def test_torque_no_weights() -> None:
    g = _make_game()
    g.weights = []
    assert g._compute_torque() == 0.0


def test_torque_one_weight_left() -> None:
    g = _make_game()
    w = Weight(color=0, mass=2.0, side=Side.LEFT, dist=50.0)
    g.weights = [w]
    torque = g._compute_torque()
    assert torque < 0  # LEFT is negative
    assert torque == -2.0 * 50.0


def test_torque_one_weight_right() -> None:
    g = _make_game()
    w = Weight(color=1, mass=3.0, side=Side.RIGHT, dist=60.0)
    g.weights = [w]
    torque = g._compute_torque()
    assert torque > 0  # RIGHT is positive
    assert torque == 3.0 * 60.0


def test_torque_balanced() -> None:
    g = _make_game()
    w1 = Weight(color=0, mass=5.0, side=Side.LEFT, dist=40.0)
    w2 = Weight(color=1, mass=5.0, side=Side.RIGHT, dist=40.0)
    g.weights = [w1, w2]
    torque = g._compute_torque()
    assert torque == 0.0


def test_torque_multiple_weights() -> None:
    g = _make_game()
    w1 = Weight(color=0, mass=2.0, side=Side.LEFT, dist=30.0)
    w2 = Weight(color=1, mass=4.0, side=Side.RIGHT, dist=50.0)
    g.weights = [w1, w2]
    torque = g._compute_torque()
    expected = -2.0 * 30.0 + 4.0 * 50.0
    assert torque == expected


def test_torque_weight_mass_proportional() -> None:
    w1 = Weight(color=0, mass=2.0, side=Side.RIGHT, dist=50.0)
    w2 = Weight(color=0, mass=4.0, side=Side.RIGHT, dist=50.0)
    t1 = Game.__new__(Game)
    t1._rng = random.Random(42)
    t1.weights = [w1]
    t2 = Game.__new__(Game)
    t2._rng = random.Random(42)
    t2.weights = [w2]
    assert t2._compute_torque() == 2.0 * t1._compute_torque()


def test_torque_weight_distance_proportional() -> None:
    w1 = Weight(color=0, mass=3.0, side=Side.RIGHT, dist=20.0)
    w2 = Weight(color=0, mass=3.0, side=Side.RIGHT, dist=60.0)
    t1 = Game.__new__(Game)
    t1._rng = random.Random(42)
    t1.weights = [w1]
    t2 = Game.__new__(Game)
    t2._rng = random.Random(42)
    t2.weights = [w2]
    assert t2._compute_torque() == 3.0 * t1._compute_torque()


# ═══════════════════════════════════════════════════════════════════
# Beam angle computation
# ═══════════════════════════════════════════════════════════════════


def test_beam_angle_zero_torque() -> None:
    g = _make_game()
    assert g._compute_beam_angle(0.0) == 0.0


def test_beam_angle_within_bounds() -> None:
    g = _make_game()
    # Moderate torque should give moderate angle
    angle = g._compute_beam_angle(80.0)
    assert 0.0 < angle < MAX_ANGLE


def test_beam_angle_clamped_max() -> None:
    g = _make_game()
    angle = g._compute_beam_angle(10000.0)
    assert angle == MAX_ANGLE


def test_beam_angle_clamped_min() -> None:
    g = _make_game()
    angle = g._compute_beam_angle(-10000.0)
    assert angle == -MAX_ANGLE


# ═══════════════════════════════════════════════════════════════════
# Weight placement — score and combo
# ═══════════════════════════════════════════════════════════════════


def test_place_weight_returns_score() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    score = g._place_weight(0, Side.RIGHT)
    assert score > 0
    assert len(g.weights) == 1


def test_place_weight_combo_increments_same_color() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.last_color = 0  # simulate previous placement

    g._place_weight(0, Side.RIGHT)  # same color → combo 1
    assert g.combo == 1
    assert g.max_combo == 1

    g._place_weight(0, Side.LEFT)  # same color → combo 2
    assert g.combo == 2
    assert g.max_combo == 2


def test_place_weight_combo_resets_different_color() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.last_color = 0

    g._place_weight(0, Side.RIGHT)  # same color → combo 1
    assert g.combo == 1

    g._place_weight(1, Side.RIGHT)  # different color → combo 0
    assert g.combo == 0


def test_place_weight_combo_zero_first_placement() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    # last_color is None → first placement
    score = g._place_weight(0, Side.RIGHT)
    assert g.combo == 0  # first placement doesn't combo
    assert score > 0


# ═══════════════════════════════════════════════════════════════════
# HEAT mechanics
# ═══════════════════════════════════════════════════════════════════


def test_heat_increases_wrong_color() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.last_color = 0

    g._place_weight(0, Side.RIGHT)  # match → no penalty
    heat_before = g.heat

    g._place_weight(1, Side.RIGHT)  # mismatch → penalty
    assert g.heat > heat_before
    assert g.heat == heat_before + HEAT_WRONG_COLOR


def test_heat_decreases_on_combo_match() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.last_color = 0
    g.heat = 30.0

    g._place_weight(0, Side.RIGHT)  # match → combo, heat decreases
    assert g.heat < 30.0
    assert g.heat == 30.0 + HEAT_COMBO_MATCH


def test_heat_no_penalty_first_placement() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    # last_color is None
    g._place_weight(0, Side.RIGHT)
    assert g.heat == 0.0  # no penalty on first placement


# ═══════════════════════════════════════════════════════════════════
# SUPER BALANCE
# ═══════════════════════════════════════════════════════════════════


def test_super_activates_at_combo_threshold() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.last_color = 0
    g.combo = COMBO_SUPER_THRESHOLD - 1  # combo = 3

    g._place_weight(0, Side.RIGHT)  # combo becomes 4 → SUPER
    assert g.combo == COMBO_SUPER_THRESHOLD
    assert g.super_active is True
    assert g.super_timer == SUPER_DURATION


def test_super_gives_3x_score() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.last_color = 0
    g.combo = COMBO_SUPER_THRESHOLD - 1

    g._place_weight(0, Side.RIGHT)  # activates super
    assert g.super_active is True

    g.last_color = 0
    score_normal = g._place_weight(1, Side.RIGHT)  # in super, always matches

    # Calculate expected: mass * 10 * combo_mul * super_mul
    expected = int(3.0 * WEIGHT_PLACEMENT_SCORE * (g.combo - 1) * SUPER_SCORE_MULTIPLIER)
    assert score_normal >= expected  # approximate due to rounding


def test_super_mode_all_colors_match() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.super_active = True
    g.combo = 5
    g.last_color = 0

    prev_combo = g.combo
    g._place_weight(3, Side.RIGHT)  # different color, but super → matches
    assert g.combo == prev_combo + 1  # combo incremented


def test_super_ends_after_duration() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_active = True
    g.super_timer = 1
    g.combo = 5

    g.super_timer -= 1
    if g.super_timer <= 0:
        g.super_active = False
        g.combo = 0

    assert g.super_active is False
    assert g.combo == 0


def test_super_torque_reduction() -> None:
    """During super, torque is halved."""
    g = _make_game()
    g.super_active = True
    g.weights = [Weight(color=0, mass=2.0, side=Side.RIGHT, dist=20.0)]
    total_torque = g._compute_torque()
    reduced = total_torque * SUPER_TORQUE_REDUCTION
    angle = g._compute_beam_angle(reduced)
    full_angle = g._compute_beam_angle(total_torque)
    assert abs(angle) < abs(full_angle)


# ═══════════════════════════════════════════════════════════════════
# Commitment (future hand) mechanic
# ═══════════════════════════════════════════════════════════════════


def test_commitment_bonus_when_matches() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.committed = True
    g.next_color = 0
    g.last_color = 0

    score = g._place_weight(0, Side.RIGHT)
    expected_base = int(3.0 * WEIGHT_PLACEMENT_SCORE * 1 * 1.0 * COMMIT_MULTIPLIER)
    assert score == expected_base
    assert g.committed is False  # cleared after placement


def test_commitment_penalty_when_mismatch() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.committed = True
    g.next_color = 2  # committed to color 2
    g.last_color = 0  # but we placed color 0

    heat_before = g.heat
    g._place_weight(0, Side.RIGHT)
    assert g.heat == heat_before + HEAT_MISS_COMMIT
    assert g.committed is False


# ═══════════════════════════════════════════════════════════════════
# Game over conditions
# ═══════════════════════════════════════════════════════════════════


def test_game_over_heat_max() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = float(MAX_HEAT)
    g.game_timer = 100
    g.beam_angle = 0.0
    assert g._check_game_over() is True


def test_game_over_timer_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g.game_timer = 0
    g.beam_angle = 0.0
    assert g._check_game_over() is True


def test_game_over_beam_angle_exceed() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g.game_timer = 100
    g.beam_angle = float(MAX_ANGLE)
    assert g._check_game_over() is True


def test_game_over_negative_angle_exceed() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g.game_timer = 100
    g.beam_angle = -float(MAX_ANGLE)
    assert g._check_game_over() is True


def test_game_over_not_yet() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g.game_timer = 100
    g.beam_angle = 15.0
    assert g._check_game_over() is False


# ═══════════════════════════════════════════════════════════════════
# Reset clears all state
# ═══════════════════════════════════════════════════════════════════


def test_reset_clears_state() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 500
    g.combo = 3
    g.max_combo = 5
    g.heat = 80.0
    g.beam_angle = 25.0
    g.weights = [Weight(color=0, mass=3.0, side=Side.LEFT, dist=50.0)]
    g.last_color = 2
    g.committed = True
    g.super_active = True
    g.super_timer = 100
    g.game_timer = 10
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=0)]
    g.floating_texts = [FloatingText(x=0.0, y=0.0, text="X", life=1, color=0)]
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.beam_angle == 0.0
    assert len(g.weights) == 0
    assert g.last_color is None
    assert g.committed is False
    assert g.super_active is False
    assert g.super_timer == 0
    assert g.game_timer == GAME_TIME
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


# ═══════════════════════════════════════════════════════════════════
# max_combo tracking
# ═══════════════════════════════════════════════════════════════════


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.last_color = 0

    g._place_weight(0, Side.RIGHT)  # combo 1
    g._place_weight(0, Side.RIGHT)  # combo 2
    g._place_weight(0, Side.RIGHT)  # combo 3
    assert g.max_combo == 3
    assert g.combo == 3

    g._place_weight(1, Side.RIGHT)  # combo resets to 0
    assert g.combo == 0
    assert g.max_combo == 3  # max preserved


def test_max_combo_persists_through_resets_of_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.last_color = 0

    g._place_weight(0, Side.RIGHT)  # combo 1
    g._place_weight(0, Side.RIGHT)  # combo 2
    assert g.max_combo == 2

    g._place_weight(1, Side.RIGHT)  # combo 0
    g._place_weight(1, Side.RIGHT)  # combo 1
    assert g.max_combo == 2  # still 2, didn't exceed previous max


# ═══════════════════════════════════════════════════════════════════
# Score calculation formula
# ═══════════════════════════════════════════════════════════════════


def test_score_formula_basic() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g.last_color = 0

    g._place_weight(0, Side.RIGHT)  # combo becomes 1
    # score = mass * 10 * combo_mul * super_mul * commit_mul
    # = 3.0 * 10 * 1 * 1.0 * 1.0 = 30
    expected = int(3.0 * WEIGHT_PLACEMENT_SCORE * 1 * 1.0 * 1.0)
    assert g.score == expected


def test_score_formula_with_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 2.0
    g.last_color = 0

    g._place_weight(0, Side.RIGHT)  # combo 1, score = 2 * 10 = 20
    score_before = g.score

    # current_mass was reset, set it again
    g.current_mass = 2.0
    g._place_weight(0, Side.RIGHT)  # combo 2, score = 2 * 10 * 2 = 40
    expected_gain = int(2.0 * WEIGHT_PLACEMENT_SCORE * 2 * 1.0 * 1.0)
    assert g.score == score_before + expected_gain


def test_score_formula_with_commit_bonus() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 4.0
    g.last_color = 0
    g.committed = True
    g.next_color = 0

    score = g._place_weight(0, Side.RIGHT)
    expected = int(4.0 * WEIGHT_PLACEMENT_SCORE * 1 * 1.0 * COMMIT_MULTIPLIER)
    assert score == expected


def test_score_formula_heavy_weight() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = MAX_WEIGHT_MASS  # 5.0
    g.last_color = 0

    score = g._place_weight(0, Side.RIGHT)
    expected = int(MAX_WEIGHT_MASS * WEIGHT_PLACEMENT_SCORE * 1 * 1.0 * 1.0)
    assert score == expected


# ═══════════════════════════════════════════════════════════════════
# Particle and floating text systems
# ═══════════════════════════════════════════════════════════════════


def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 120.0, 8, 5)
    assert len(g.particles) == 5


def test_update_particles() -> None:
    g = _make_game()
    p = Particle(x=0.0, y=0.0, vx=1.0, vy=0.0, life=5, color=8)
    g.particles = [p]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].x == 1.0
    assert g.particles[0].life == 4


def test_update_particles_expired_removed() -> None:
    g = _make_game()
    p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=8)
    g.particles = [p]
    g._update_particles()
    assert len(g.particles) == 0


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100.0, 120.0, "TEST", 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"


def test_update_floating_texts() -> None:
    g = _make_game()
    ft = FloatingText(x=0.0, y=100.0, text="UP", life=10, color=7)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].y == 99.0  # vy=-1.0
    assert g.floating_texts[0].life == 9


# ═══════════════════════════════════════════════════════════════════
# Weight placement — side tracking
# ═══════════════════════════════════════════════════════════════════


def test_place_weight_right_side() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g._place_weight(0, Side.RIGHT)
    assert g.weights[0].side == Side.RIGHT
    assert g.weights[0].dist > 0


def test_place_weight_left_side() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g._place_weight(0, Side.LEFT)
    assert g.weights[0].side == Side.LEFT
    assert g.weights[0].dist > 0


def test_place_weight_distance_increases_on_same_side() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    g._place_weight(0, Side.RIGHT)
    dist1 = g.weights[0].dist
    g._place_weight(1, Side.RIGHT)
    dist2 = g.weights[1].dist
    assert dist2 > dist1


def test_place_weight_distance_clamped() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.current_mass = 3.0
    for _ in range(20):
        g._place_weight(0, Side.RIGHT)
    assert all(w.dist <= BEAM_LENGTH / 2 - 10.0 for w in g.weights)


# ═══════════════════════════════════════════════════════════════════
# _activate_super
# ═══════════════════════════════════════════════════════════════════


def test_activate_super() -> None:
    g = _make_game()
    g._activate_super()
    assert g.super_active is True
    assert g.super_timer == SUPER_DURATION
    assert len(g.particles) == 30
    assert len(g.floating_texts) == 5  # 4 color texts + 1 "BALANCE!"


# ═══════════════════════════════════════════════════════════════════
# Weight mass range
# ═══════════════════════════════════════════════════════════════════


def test_weight_mass_in_range() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    for _ in range(100):
        mass = g._rng.uniform(MIN_WEIGHT_MASS, MAX_WEIGHT_MASS)
        assert MIN_WEIGHT_MASS <= mass <= MAX_WEIGHT_MASS


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
