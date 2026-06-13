"""test_imports.py — Headless logic tests for 121_lift_chain."""
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (
    Game, Phase, PlaySubPhase, Particle,
    MAX_HEAT, PLATE_COLORS, NUM_COLORS, COMBO_FOR_SUPER,
    SUPER_DURATION, HEAT_MISS, HEAT_WRONG_COLOR, HEAT_DECAY,
    INITIAL_WEIGHT, WEIGHT_INCREMENT, INITIAL_TARGET_WIDTH, MIN_TARGET_WIDTH,
    POWER_RATE,
)


def _make_game(seed: int = 42) -> Game:
    """Create a Game bypassing pyxel.init/run for headless testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    # Pre-init all attributes that reset() touches
    g.phase = Phase.TITLE
    g.sub_phase = PlaySubPhase.AWAIT_LIFT
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.plate_color = 0
    g.prev_plate_color = 0
    g.weight = INITIAL_WEIGHT
    g.power = 0.0
    g.power_rate = POWER_RATE
    g.target_center = 0.5
    g.target_width = INITIAL_TARGET_WIDTH
    g.super_timer = 0
    g.result_timer = 0
    g.lockout_timer = 0
    g.last_result = ""
    g.last_score_gain = 0
    g.particles: list[Particle] = []
    g.frames = 0
    g.high_score = 0
    g.blink_timer = 0
    g.reset()
    return g


# --- Test Constants ---
def test_constants() -> None:
    assert len(PLATE_COLORS) == NUM_COLORS == 4
    assert COMBO_FOR_SUPER == 4
    assert SUPER_DURATION == 150
    assert MAX_HEAT == 100.0
    assert HEAT_MISS == 15.0
    assert HEAT_WRONG_COLOR == 5.0
    assert HEAT_DECAY == 0.05
    assert INITIAL_WEIGHT == 100
    assert WEIGHT_INCREMENT == 25
    assert INITIAL_TARGET_WIDTH == 0.30
    assert MIN_TARGET_WIDTH == 0.08


# --- Dataclass Tests ---
def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8


# --- Phase Enum Tests ---
def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert len(list(Phase)) == 3


def test_play_subphase_enum() -> None:
    assert PlaySubPhase.AWAIT_LIFT in PlaySubPhase
    assert PlaySubPhase.POWERING in PlaySubPhase
    assert PlaySubPhase.LOCKOUT in PlaySubPhase
    assert PlaySubPhase.RESULT in PlaySubPhase
    assert len(list(PlaySubPhase)) == 4


# --- Game.__new__ Bypass Tests ---
def test_game_new_bypass() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    # Pre-init
    g.phase = Phase.TITLE
    g.sub_phase = PlaySubPhase.AWAIT_LIFT
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.plate_color = 0
    g.prev_plate_color = 0
    g.weight = INITIAL_WEIGHT
    g.power = 0.0
    g.power_rate = POWER_RATE
    g.target_center = 0.5
    g.target_width = INITIAL_TARGET_WIDTH
    g.super_timer = 0
    g.result_timer = 0
    g.lockout_timer = 0
    g.last_result = ""
    g.last_score_gain = 0
    g.particles = []
    g.frames = 0
    g.high_score = 0
    g.blink_timer = 0
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.weight == INITIAL_WEIGHT


# --- _check_lift Tests ---
def test_check_lift_perfect() -> None:
    g = _make_game()
    g.target_center = 0.5
    g.target_width = 0.3
    g.power = 0.5
    result, accuracy = g._check_lift()
    assert result == "perfect"
    assert abs(accuracy - 1.0) < 0.01


def test_check_lift_ok() -> None:
    g = _make_game()
    g.target_center = 0.5
    g.target_width = 0.3
    # 0.5 + 0.15*0.3 = 0.545; 0.5 + 0.075 = 0.575 ok border
    g.power = 0.56
    result, accuracy = g._check_lift()
    assert result == "ok"
    assert accuracy > 0.5


def test_check_lift_miss() -> None:
    g = _make_game()
    g.target_center = 0.5
    g.target_width = 0.3
    g.power = 0.1
    result, accuracy = g._check_lift()
    assert result == "miss"
    assert accuracy == 0.0


def test_check_lift_super_auto_perfect() -> None:
    g = _make_game()
    g.super_timer = 50
    g.power = 0.1  # far from center
    result, accuracy = g._check_lift()
    assert result == "perfect"
    assert accuracy == 1.0


# --- _resolve_lift Tests ---
def test_resolve_lift_perfect_matching_color() -> None:
    g = _make_game()
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 1
    g.weight = 100
    gain = g._resolve_lift("perfect", 1.0)
    assert gain > 0
    assert g.combo == 2
    assert g.max_combo == 2
    assert g.score > 0
    assert g.heat == 0.0


def test_resolve_lift_ok_matching_color() -> None:
    g = _make_game()
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 1
    g.weight = 100
    gain = g._resolve_lift("ok", 0.6)
    assert gain > 0
    assert g.combo == 2
    assert gain < 200  # lower than perfect due to 1.0x timing mult


def test_resolve_lift_miss_resets_combo() -> None:
    g = _make_game()
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 3
    g.heat = 0
    gain = g._resolve_lift("miss", 0.0)
    assert gain == 0
    assert g.combo == 0
    assert g.heat == HEAT_MISS
    assert g.last_result == "miss"


def test_resolve_lift_wrong_color_non_super() -> None:
    g = _make_game()
    g.plate_color = 1
    g.prev_plate_color = 0
    g.combo = 3
    g.super_timer = 0
    g._resolve_lift("perfect", 1.0)
    assert g.heat == HEAT_WRONG_COLOR
    # Combo resets to 1 on wrong color when not in super
    assert g.combo == 1


def test_resolve_lift_wrong_color_during_super() -> None:
    g = _make_game()
    g.plate_color = 1
    g.prev_plate_color = 0
    g.combo = 5
    g.super_timer = 50
    g.heat = 0
    g._resolve_lift("perfect", 1.0)
    # During super, wrong color still adds heat but doesn't reset combo
    assert g.heat == HEAT_WRONG_COLOR
    assert g.combo == 6  # incremented even on wrong color during super


def test_resolve_lift_super_trigger() -> None:
    g = _make_game()
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 3  # next lift = combo 4 => SUPER
    g.super_timer = 0
    g._resolve_lift("perfect", 1.0)
    assert g.super_timer == SUPER_DURATION
    assert g.combo == 4


def test_resolve_lift_super_3x_multiplier() -> None:
    g = _make_game()
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 4
    g.super_timer = SUPER_DURATION
    g.weight = 100
    g.score = 0
    gain = g._resolve_lift("perfect", 1.0)
    # score = weight * timing(1.5) * combo_mult(1.75) * super(3.0) = 100 * 1.5 * 1.75 * 3 = 787
    assert gain > 500  # 3x multiplier from super
    assert g.combo == 5


def test_resolve_lift_heat_game_over_check() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 1
    g.heat = MAX_HEAT
    g._resolve_lift("perfect", 1.0)
    assert g.phase == Phase.GAME_OVER


# --- _update_heat Tests ---
def test_update_heat_decay() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g._update_heat()
    assert g.phase == Phase.PLAYING
    assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.001


def test_update_heat_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_update_heat_clamp_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_decay_before_check() -> None:
    """Verify heat threshold is checked BEFORE decay (fixed by OpenCode)."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT
    g._update_heat()
    # Should trigger GAME_OVER before decaying
    assert g.phase == Phase.GAME_OVER
    # Heat should remain at MAX (decay skipped due to early return)
    assert g.heat == MAX_HEAT


# --- _weight_for_combo Tests ---
def test_weight_for_combo_base() -> None:
    g = _make_game()
    g.combo = 1
    assert g._weight_for_combo() == INITIAL_WEIGHT


def test_weight_for_combo_scaling() -> None:
    g = _make_game()
    g.combo = 5
    assert g._weight_for_combo() == INITIAL_WEIGHT + 4 * WEIGHT_INCREMENT


# --- _target_width_for_weight Tests ---
def test_target_width_base() -> None:
    g = _make_game()
    assert g._target_width_for_weight(INITIAL_WEIGHT) == INITIAL_TARGET_WIDTH


def test_target_width_shrinks() -> None:
    g = _make_game()
    w = INITIAL_WEIGHT + 5 * WEIGHT_INCREMENT
    result = g._target_width_for_weight(w)
    assert result < INITIAL_TARGET_WIDTH


def test_target_width_clamped() -> None:
    g = _make_game()
    w = INITIAL_WEIGHT + 100 * WEIGHT_INCREMENT
    result = g._target_width_for_weight(w)
    assert result == MIN_TARGET_WIDTH


# --- _start_lift Tests ---
def test_start_lift_sets_prev_color() -> None:
    g = _make_game()
    g.plate_color = 2
    g.prev_plate_color = 0
    g._start_lift()
    assert g.prev_plate_color == 2


def test_start_lift_same_color_probability() -> None:
    """With high combo, same-color probability is 40%."""
    g = _make_game()
    g.combo = 3
    g.prev_plate_color = 0
    g._rng.random = lambda: 0.3  # type: ignore  # < 0.4 => same color
    g._start_lift()
    assert g.plate_color == 0  # kept same


def test_start_lift_different_color() -> None:
    g = _make_game()
    g.combo = 3
    g.prev_plate_color = 0
    g._rng.random = lambda: 0.9  # type: ignore  # >= 0.4 => different color
    g._rng.randint = lambda a, b: 2  # type: ignore  # force color 2
    g._start_lift()
    assert g.plate_color == 2


def test_start_lift_super_keeps_color() -> None:
    g = _make_game()
    g.super_timer = 50
    g.plate_color = 1  # current color is 1
    g._start_lift()
    # _start_lift sets prev = plate_color (1), then plate = prev (1)
    assert g.plate_color == 1  # always same during super


# --- Particle Tests ---
def test_spawn_particles() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_particles(100, 100, 5, 8)
    assert len(g.particles) == 5
    for p in g.particles:
        assert 15 <= p.life <= 30
        assert p.color == 8


def test_spawn_super_particles() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_super_particles(100, 100, 3)
    assert len(g.particles) == 3
    for p in g.particles:
        assert 20 <= p.life <= 40
        assert p.color in PLATE_COLORS


def test_spawn_miss_particles() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_miss_particles(100, 100, 3)
    assert len(g.particles) == 3
    for p in g.particles:
        assert 10 <= p.life <= 20
        assert p.color == 8  # RED


def test_update_particles() -> None:
    g = _make_game()
    g.particles = [Particle(x=50.0, y=50.0, vx=1.0, vy=-2.0, life=5, color=8)]
    g._update_particles()
    assert len(g.particles) == 1
    p = g.particles[0]
    assert p.life == 4
    assert p.vy > -2.0  # gravity applied


def test_update_particles_removal() -> None:
    g = _make_game()
    g.particles = [Particle(x=50.0, y=50.0, vx=0.0, vy=0.0, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0  # life goes to 0, removed


def test_update_particles_super_gravity() -> None:
    g = _make_game()
    g.super_timer = 50
    g.particles = [Particle(x=50.0, y=50.0, vx=0.0, vy=0.0, life=10, color=8)]
    g._update_particles()
    assert g.particles[0].vy == 0.03  # super gravity is 0.03


# --- Game State Tests ---
def test_game_state_initial() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.weight == INITIAL_WEIGHT
    assert g.super_timer == 0


def test_max_combo_tracking() -> None:
    g = _make_game()
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 5
    g.max_combo = 5
    # Miss resets combo but max_combo persists
    g._resolve_lift("miss", 0.0)
    assert g.combo == 0
    assert g.max_combo == 5


def test_high_score_tracking() -> None:
    g = _make_game()
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 1
    g.weight = 100
    g.score = 0
    g.high_score = 0
    g._resolve_lift("perfect", 1.0)
    assert g.high_score == g.score
    assert g.high_score > 0


def test_score_accumulation() -> None:
    g = _make_game()
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 1
    g.weight = 100
    score_before = g.score
    g._resolve_lift("perfect", 1.0)
    assert g.score > score_before


def test_reset_clears_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 5
    g.heat = 50
    g.super_timer = 30
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.phase == Phase.TITLE


# --- Timing & Multiplier Tests ---
def test_perfect_timing_multiplier() -> None:
    g = _make_game()
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 1
    g.weight = 100
    gain_perfect = g._resolve_lift("perfect", 1.0)
    # Reset and try ok
    g.score = 0
    g.combo = 1
    g.plate_color = 0
    g.prev_plate_color = 0
    gain_ok = g._resolve_lift("ok", 0.6)
    assert gain_perfect > gain_ok  # perfect gives 1.5x, ok gives 1.0x


def test_combo_multiplier_increases() -> None:
    g = _make_game()
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 1
    g.weight = 100
    gain_low = g._resolve_lift("perfect", 1.0)
    # combo=1: mult = 1.0 + 0*0.25 = 1.0
    # combo=5: mult = 1.0 + 4*0.25 = 2.0
    g.score = 0
    g.combo = 5
    g.plate_color = 0
    g.prev_plate_color = 0
    gain_high = g._resolve_lift("perfect", 1.0)
    assert gain_high > gain_low  # higher combo multiplier


# --- Heat System Tests ---
def test_heat_accumulation_miss() -> None:
    g = _make_game()
    g.combo = 1
    g._resolve_lift("miss", 0.0)
    assert g.heat == HEAT_MISS


def test_heat_accumulation_wrong_color() -> None:
    g = _make_game()
    g.plate_color = 1
    g.prev_plate_color = 0
    g.combo = 1
    g._resolve_lift("perfect", 1.0)
    assert g.heat == HEAT_WRONG_COLOR


def test_heat_clamped_at_max() -> None:
    g = _make_game()
    g.heat = 95.0
    g.combo = 1
    # Miss adds 15; 95+15=110 clamped to 100
    g._resolve_lift("miss", 0.0)
    assert g.heat == MAX_HEAT


# --- SUPER MODE Tests ---
def test_super_mode_3x_multiplier() -> None:
    g = _make_game()
    g.plate_color = 0
    g.prev_plate_color = 0
    g.combo = 4
    g.super_timer = SUPER_DURATION
    g.weight = 100
    gain_super = g._resolve_lift("perfect", 1.0)
    # Without super: 100 * 1.5 * (1+3*0.25) = 100*1.5*1.75 = 262.5
    # With super: 262.5 * 3 = 787.5
    assert gain_super >= 700


def test_super_auto_perfect() -> None:
    g = _make_game()
    g.super_timer = 50
    g.power = 0.0  # far from target
    result, accuracy = g._check_lift()
    assert result == "perfect"
    assert accuracy == 1.0


def test_super_wrong_color_still_increments_combo() -> None:
    g = _make_game()
    g.super_timer = 50
    g.plate_color = 1
    g.prev_plate_color = 0
    g.combo = 5
    g._resolve_lift("perfect", 1.0)
    assert g.combo == 6  # still increments during super


if __name__ == "__main__":
    import traceback

    tests = [
        test_constants,
        test_particle_creation,
        test_phase_enum,
        test_play_subphase_enum,
        test_game_new_bypass,
        test_check_lift_perfect,
        test_check_lift_ok,
        test_check_lift_miss,
        test_check_lift_super_auto_perfect,
        test_resolve_lift_perfect_matching_color,
        test_resolve_lift_ok_matching_color,
        test_resolve_lift_miss_resets_combo,
        test_resolve_lift_wrong_color_non_super,
        test_resolve_lift_wrong_color_during_super,
        test_resolve_lift_super_trigger,
        test_resolve_lift_super_3x_multiplier,
        test_resolve_lift_heat_game_over_check,
        test_update_heat_decay,
        test_update_heat_game_over,
        test_update_heat_clamp_zero,
        test_update_heat_decay_before_check,
        test_weight_for_combo_base,
        test_weight_for_combo_scaling,
        test_target_width_base,
        test_target_width_shrinks,
        test_target_width_clamped,
        test_start_lift_sets_prev_color,
        test_start_lift_same_color_probability,
        test_start_lift_different_color,
        test_start_lift_super_keeps_color,
        test_spawn_particles,
        test_spawn_super_particles,
        test_spawn_miss_particles,
        test_update_particles,
        test_update_particles_removal,
        test_update_particles_super_gravity,
        test_game_state_initial,
        test_max_combo_tracking,
        test_high_score_tracking,
        test_score_accumulation,
        test_reset_clears_state,
        test_perfect_timing_multiplier,
        test_combo_multiplier_increases,
        test_heat_accumulation_miss,
        test_heat_accumulation_wrong_color,
        test_heat_clamped_at_max,
        test_super_mode_3x_multiplier,
        test_super_auto_perfect,
        test_super_wrong_color_still_increments_combo,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {test.__name__}: {e}")
            traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
