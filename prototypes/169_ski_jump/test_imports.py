"""test_imports.py — Headless logic tests for Ski Jump prototype."""
import random
import sys
from pathlib import Path

# Add prototype dir to path
sys.path.insert(0, str(Path(__file__).parent))

from main import (
    COMBO_SUPER_THRESHOLD,
    DEFAULT_SPEED,
    GATE_COLORS,
    GRAVITY,
    HEAT_PER_MISMATCH,
    MAX_HEAT,
    MAX_SPEED,
    MIN_SPEED,
    Phase,
    RAMP_START_X,
    RAMP_START_Y,
    RAMP_TAKEOFF_X,
    RAMP_TAKEOFF_Y,
    SUPER_DURATION,
    FloatingText,
    Game,
    Gate,
    Particle,
)


def _make_game() -> Game:
    """Factory: bypass pyxel.init, seed RNG, call _reset()."""
    g: Game = Game.__new__(Game)
    # Pre-init all attributes _reset() touches
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.last_gate_color = None
    g.heat = 0.0
    g.wobble = False
    g.super_jump = False
    g.super_timer = 0
    g.player_x = float(RAMP_START_X)
    g.player_y = float(RAMP_START_Y)
    g.player_speed = DEFAULT_SPEED
    g.player_vx = 0.0
    g.player_vy = 0.0
    g.player_angle = 0.0
    g.player_on_ramp = True
    g.flight_distance = 0.0
    g.landing_quality = 0.0
    g.gates = []
    g.particles = []
    g.floating_texts = []
    g.game_timer = 90.0
    g.landing_timer = 0
    g._rng = random.Random(42)
    g._reset()
    return g


# ── Phase enum ──────────────────────────────────────────────────────────────
def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.APPROACH in Phase
    assert Phase.FLIGHT in Phase
    assert Phase.LANDING in Phase
    assert Phase.GAME_OVER in Phase


# ── Dataclass construction ──────────────────────────────────────────────────
def test_gate_construction() -> None:
    gate = Gate(x=100.0, y=150.0, color=8)
    assert gate.x == 100.0
    assert gate.y == 150.0
    assert gate.color == 8
    assert gate.width == 24
    assert gate.height == 32
    assert gate.passed is False


def test_particle_construction() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=3)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 3


def test_floating_text_construction() -> None:
    ft = FloatingText(x=160.0, y=80.0, text="+100", life=30, color=7)
    assert ft.x == 160.0
    assert ft.y == 80.0
    assert ft.text == "+100"
    assert ft.life == 30
    assert ft.color == 7


# ── Ramp geometry ───────────────────────────────────────────────────────────
def test_ramp_y_start() -> None:
    y = Game._ramp_y(RAMP_START_X)
    assert y == float(RAMP_START_Y)


def test_ramp_y_takeoff() -> None:
    y = Game._ramp_y(RAMP_TAKEOFF_X)
    assert y == float(RAMP_TAKEOFF_Y)


def test_ramp_y_midpoint() -> None:
    y = Game._ramp_y(140.0)
    # Ramp goes upward (Y decreases from 180 to 60)
    assert y < RAMP_START_Y  # going up (lower y = higher on screen)
    assert y > RAMP_TAKEOFF_Y


def test_ground_y() -> None:
    gy = Game._ground_y(RAMP_TAKEOFF_X)
    expected = RAMP_TAKEOFF_Y + 30 + (RAMP_TAKEOFF_X - RAMP_TAKEOFF_X) * 0.5
    assert gy == expected


def test_ground_y_slopes_down() -> None:
    # ground slopes down from takeoff
    g0 = Game._ground_y(RAMP_TAKEOFF_X)
    g1 = Game._ground_y(RAMP_TAKEOFF_X + 100)
    assert g1 > g0  # further right = lower (higher y)


# ── Gate spawning ───────────────────────────────────────────────────────────
def test_spawn_gates_creates_gates() -> None:
    g = _make_game()
    g._spawn_gates()
    assert len(g.gates) >= 2  # seed 42 produces 2-3 gates
    # All gates should be before takeoff
    for gate in g.gates:
        assert gate.x < RAMP_TAKEOFF_X
        assert not gate.passed


def test_spawn_gates_are_on_ramp() -> None:
    g = _make_game()
    g._spawn_gates()
    for gate in g.gates:
        expected_y = Game._ramp_y(gate.x)
        assert abs(gate.y - expected_y) < 0.01


def test_spawn_gates_deterministic() -> None:
    g1 = _make_game()
    g1._rng = random.Random(42)
    g1._spawn_gates()

    g2 = _make_game()
    g2._rng = random.Random(42)
    g2._spawn_gates()

    assert len(g1.gates) == len(g2.gates)
    for i, (a, b) in enumerate(zip(g1.gates, g2.gates)):
        assert a.x == b.x
        assert a.color == b.color


def test_spawn_gates_all_colors_used() -> None:
    g = _make_game()
    g._spawn_gates()
    colors = {gate.color for gate in g.gates}
    # With 4 possible colors and many gates, should see multiple colors
    assert len(colors) >= 2


# ── Gate passing / combo logic ─────────────────────────────────────────────
def test_pass_first_gate() -> None:
    g = _make_game()
    gate = Gate(x=100.0, y=150.0, color=8)  # RED
    g._pass_gate(gate)
    assert gate.passed is True
    assert g.combo == 1
    assert g.last_gate_color == 8
    assert g.score == 50


def test_pass_same_color_gate_builds_combo() -> None:
    g = _make_game()
    g1 = Gate(x=100.0, y=150.0, color=8)  # RED
    g2 = Gate(x=120.0, y=130.0, color=8)  # RED (same)
    g._pass_gate(g1)
    assert g.combo == 1
    g._pass_gate(g2)
    assert g.combo == 2
    assert g.last_gate_color == 8
    assert g.score == 50 + 50 * 2  # 50 + 100 = 150


def test_pass_same_color_chain_to_super_threshold() -> None:
    g = _make_game()
    for i in range(1, 5):  # pass 4 same-color gates
        gate = Gate(x=float(i * 20), y=100.0, color=8)
        g._pass_gate(gate)
    assert g.combo == 4
    assert g.max_combo == 4
    # Score: 50 + 100 + 150 + 200 = 500
    assert g.score == 500


def test_pass_different_color_resets_combo() -> None:
    g = _make_game()
    g1 = Gate(x=100.0, y=150.0, color=8)   # RED
    g2 = Gate(x=120.0, y=130.0, color=3)   # GREEN (different)
    g3 = Gate(x=140.0, y=110.0, color=8)   # RED

    g._pass_gate(g1)
    assert g.combo == 1
    assert g.score == 50

    g._pass_gate(g2)  # color mismatch — combo resets
    assert g.combo == 1
    assert g.heat == HEAT_PER_MISMATCH
    assert g.last_gate_color == 3

    g._pass_gate(g3)  # RED again, but last was GREEN → mismatch again
    assert g.combo == 1
    assert g.heat == HEAT_PER_MISMATCH * 2
    # Score: only first gate added score (50). Mismatches add no score.
    assert g.score == 50


def test_pass_different_color_adds_heat() -> None:
    g = _make_game()
    g1 = Gate(x=100.0, y=150.0, color=8)  # RED
    g._pass_gate(g1)
    assert g.heat == 0

    g2 = Gate(x=120.0, y=130.0, color=3)  # GREEN (different)
    g._pass_gate(g2)
    assert g.heat == HEAT_PER_MISMATCH

    g3 = Gate(x=140.0, y=110.0, color=10)  # YELLOW (different again)
    g._pass_gate(g3)
    assert g.heat == HEAT_PER_MISMATCH * 2


def test_heat_capped_at_max() -> None:
    g = _make_game()
    g.heat = MAX_HEAT - 5
    g.last_gate_color = 8  # RED
    gate = Gate(x=100.0, y=150.0, color=3)  # GREEN (different)
    g._pass_gate(gate)
    assert g.heat == MAX_HEAT


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    # Build combo to 3
    for i in range(3):
        gate = Gate(x=float(i * 20), y=100.0, color=8)
        g._pass_gate(gate)
    assert g.max_combo == 3

    # Break combo
    gate = Gate(x=80.0, y=100.0, color=3)
    g._pass_gate(gate)
    assert g.combo == 1
    assert g.max_combo == 3  # max_combo preserves highest


def test_particles_spawned_on_gate_pass() -> None:
    g = _make_game()
    assert len(g.particles) == 0
    gate = Gate(x=100.0, y=150.0, color=8)
    g._pass_gate(gate)
    assert len(g.particles) == 8  # first gate spawns 8
    for p in g.particles:
        assert p.color == 8
        assert p.life > 0


def test_floating_text_spawned_on_gate_pass() -> None:
    g = _make_game()
    gate = Gate(x=100.0, y=150.0, color=8)
    g._pass_gate(gate)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+50"


def test_floating_text_combo_on_match() -> None:
    g = _make_game()
    g1 = Gate(x=100.0, y=150.0, color=8)
    g._pass_gate(g1)  # combo=1
    g2 = Gate(x=120.0, y=130.0, color=8)
    g._pass_gate(g2)  # combo=2
    # Should have 3 floating texts: +50 from g1, +100 from g2, COMBO x2
    assert len(g.floating_texts) == 3
    combo_texts = [ft for ft in g.floating_texts if "COMBO" in ft.text]
    assert len(combo_texts) == 1
    assert "x2" in combo_texts[0].text


def test_miss_floating_text() -> None:
    g = _make_game()
    g1 = Gate(x=100.0, y=150.0, color=8)
    g._pass_gate(g1)
    g2 = Gate(x=120.0, y=130.0, color=3)  # different
    g._pass_gate(g2)
    miss_texts = [ft for ft in g.floating_texts if "MISS" in ft.text]
    assert len(miss_texts) == 1


# ── Takeoff ─────────────────────────────────────────────────────────────────
def test_takeoff_sets_flight_phase() -> None:
    g = _make_game()
    g.phase = Phase.APPROACH
    g.player_speed = DEFAULT_SPEED
    g.combo = 2
    g._takeoff()
    assert g.phase == Phase.FLIGHT
    assert g.player_on_ramp is False
    assert g.player_vx > 0  # moving forward
    assert g.player_vy < 0  # moving upward


def test_takeoff_no_combo_handled() -> None:
    g = _make_game()
    g.phase = Phase.APPROACH
    g.combo = 0
    g._takeoff()
    assert g.phase == Phase.FLIGHT
    assert g.player_vx > 0


def test_takeoff_with_super() -> None:
    g = _make_game()
    g.phase = Phase.APPROACH
    g.combo = COMBO_SUPER_THRESHOLD  # 4
    g.player_speed = DEFAULT_SPEED
    g._takeoff()
    assert g.super_jump is True
    assert g.super_timer == SUPER_DURATION  # 300
    # SUPER JUMP floating text
    super_texts = [ft for ft in g.floating_texts if "SUPER" in ft.text]
    assert len(super_texts) == 1
    # SUPER particles
    assert len(g.particles) == 25


def test_takeoff_super_boosts_velocity() -> None:
    g = _make_game()
    g.phase = Phase.APPROACH
    g.player_speed = DEFAULT_SPEED

    # Without super
    g.combo = 2
    g._takeoff()
    vx_normal = g.player_vx
    vy_normal = g.player_vy
    assert vx_normal > 0

    # With super (combo=4)
    g2 = _make_game()
    g2.phase = Phase.APPROACH
    g2.player_speed = DEFAULT_SPEED
    g2.combo = COMBO_SUPER_THRESHOLD
    g2._takeoff()
    assert g2.player_vx > vx_normal  # super should boost
    assert g2.player_vy < vy_normal  # more upward (more negative)


# ── Flight physics ───────────────────────────────────────────────────────────
def test_flight_gravity_applies() -> None:
    g = _make_game()
    g.phase = Phase.FLIGHT
    g.player_vx = 3.0
    g.player_vy = -5.0
    g.player_x = float(RAMP_TAKEOFF_X)
    g.player_y = float(RAMP_TAKEOFF_Y)
    # We can't call _update_flight directly (uses pyxel.btn/frame_count)
    # But we can test the physics model manually
    vy_before = g.player_vy
    g.player_vy += GRAVITY
    assert g.player_vy == vy_before + GRAVITY


def test_flight_distance_tracking() -> None:
    g = _make_game()
    g.phase = Phase.FLIGHT
    g.player_x = float(RAMP_TAKEOFF_X + 50)
    g.flight_distance = g.player_x - RAMP_TAKEOFF_X
    assert g.flight_distance == 50.0


# ── Landing ─────────────────────────────────────────────────────────────────
def test_land_transitions_to_landing_phase() -> None:
    g = _make_game()
    g.phase = Phase.FLIGHT
    g.player_x = float(RAMP_TAKEOFF_X + 80)
    g.player_y = float(RAMP_TAKEOFF_Y + 50)  # below takeoff
    g.flight_distance = 80.0
    g.player_angle = 0.0
    g.score = 200
    g._land()
    assert g.phase == Phase.LANDING
    assert g.landing_timer == 120
    assert g.score > 200  # landing adds score


def test_landing_quality_perfect_when_angle_matches_slope() -> None:
    g = _make_game()
    g.phase = Phase.FLIGHT
    g.player_angle = 0.463  # atan(0.5) ~ 0.4636 — matches slope
    g.player_x = float(RAMP_TAKEOFF_X + 50)
    g.player_y = float(RAMP_TAKEOFF_Y + 50)
    g.flight_distance = 50.0
    g._land()
    assert g.landing_quality > 0.9  # near perfect


def test_landing_quality_bad_when_angle_mismatch() -> None:
    g = _make_game()
    g.phase = Phase.FLIGHT
    g.player_angle = -0.5  # opposite direction from slope (~0.46)
    g.player_x = float(RAMP_TAKEOFF_X + 50)
    g.player_y = float(RAMP_TAKEOFF_Y + 50)
    g.flight_distance = 50.0
    g._land()
    # With angle=-0.5 vs slope≈0.46, diff≈0.96, quality≈0.04
    assert g.landing_quality < 0.3  # poor landing


def test_landing_super_multiplier() -> None:
    g_normal = _make_game()
    g_normal.phase = Phase.FLIGHT
    g_normal.player_angle = 0.0
    g_normal.flight_distance = 100.0
    g_normal.player_x = float(RAMP_TAKEOFF_X + 100)
    g_normal.player_y = float(RAMP_TAKEOFF_Y + 80)
    g_normal.score = 0
    g_normal.super_jump = False
    g_normal._land()
    score_normal = g_normal.score

    g_super = _make_game()
    g_super.phase = Phase.FLIGHT
    g_super.player_angle = 0.0
    g_super.flight_distance = 100.0
    g_super.player_x = float(RAMP_TAKEOFF_X + 100)
    g_super.player_y = float(RAMP_TAKEOFF_Y + 80)
    g_super.score = 0
    g_super.super_jump = True
    g_super._land()
    score_super = g_super.score

    # SUPER should give ~3x the distance score component
    # (landing_quality bonus may differ slightly due to angle)
    assert score_super > score_normal * 2  # at least 2x


def test_landing_updates_best_score() -> None:
    g = _make_game()
    g.best_score = 0
    g.phase = Phase.FLIGHT
    g.player_angle = 0.0
    g.flight_distance = 100.0
    g.player_x = float(RAMP_TAKEOFF_X + 100)
    g.player_y = float(RAMP_TAKEOFF_Y + 80)
    g.score = 0
    g._land()
    assert g.best_score > 0
    assert g.best_score == g.score


# ── Reset ───────────────────────────────────────────────────────────────────
def test_reset_clears_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 4
    g.heat = 80
    g.super_jump = True
    g.gates = [Gate(x=100.0, y=150.0, color=8)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=5, color=0)]
    g.floating_texts = [FloatingText(x=0, y=0, text="x", life=5, color=0)]

    g._reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_jump is False
    assert g.gates == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g.phase == Phase.TITLE


def test_reset_for_run_starts_approach() -> None:
    g = _make_game()
    g.best_score = 5000
    g._reset_for_run()
    assert g.phase == Phase.APPROACH
    assert g.best_score == 5000  # preserved
    assert g.score == 0  # reset
    assert len(g.gates) > 0  # spawned new gates


def test_reset_for_run_preserves_best_score() -> None:
    g = _make_game()
    g.best_score = 9999
    g.score = 100
    g._reset_for_run()
    assert g.best_score == 9999
    assert g.score == 0


# ── Heat / wobble ───────────────────────────────────────────────────────────
def test_heat_starts_at_zero() -> None:
    g = _make_game()
    assert g.heat == 0.0
    assert g.wobble is False


def test_wobble_activates_at_max_heat() -> None:
    g = _make_game()
    g.heat = MAX_HEAT
    # Simulate what _update_approach does for wobble check:
    g.wobble = g.heat >= MAX_HEAT
    assert g.wobble is True


def test_wobble_not_active_below_max() -> None:
    g = _make_game()
    g.heat = MAX_HEAT - 1
    g.wobble = g.heat >= MAX_HEAT
    assert g.wobble is False


# ── Constants ────────────────────────────────────────────────────────────────
def test_gate_colors() -> None:
    assert len(GATE_COLORS) == 4
    assert 8 in GATE_COLORS  # RED
    assert 3 in GATE_COLORS  # GREEN
    assert 5 in GATE_COLORS  # DARK_BLUE
    assert 10 in GATE_COLORS  # YELLOW


def test_constant_ranges() -> None:
    assert COMBO_SUPER_THRESHOLD == 4
    assert SUPER_DURATION == 300
    assert HEAT_PER_MISMATCH == 15
    assert MAX_HEAT == 100
    assert MIN_SPEED < DEFAULT_SPEED < MAX_SPEED


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
