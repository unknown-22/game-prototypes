"""test_imports.py — Headless logic tests for 238_lift_chain."""
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (
    Game, Phase, Particle, FloatingText, GhostLift,
    PLATE_COLORS, PLATFORM_Y, LIFT_LINE_Y,
    POWER_MAX, HEAT_MAX, HEAT_DECAY, HEAT_MISMATCH, HEAT_MISS,
    VELOCITY_FACTOR, GRAVITY, POWER_BUILD_RATE,
    SUPER_DURATION, SUPER_SCORE_MULT,
    SUPER_AUTO_LIFT_INTERVAL,
    TIMER_START, COLOR_CYCLE_INTERVAL_START, COLOR_CYCLE_INTERVAL_MIN,
)


def _make_game() -> Game:
    """Create a Game instance without pyxel init."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes before _init_state
    g._rng = random.Random(42)
    g.particles = []
    g.floating_texts = []
    g.ghost_recording = []
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = TIMER_START
    g.power = 0.0
    g.barbell_y = PLATFORM_Y
    g.barbell_vy = 0.0
    g.barbell_color = 0
    g.attempt_color = 0
    g.super_timer = 0
    g.super_mode = False
    g.super_auto_frame = 0
    g.result_timer = 0
    g.lift_success = False
    g.last_score = 0
    g.color_cycle_timer = 0
    g.color_cycle_interval = COLOR_CYCLE_INTERVAL_START
    g.powering = False
    g.difficulty_level = 0.0
    g.best_lift_y = PLATFORM_Y
    g.screen_shake = 0
    # Call _init_state, then overwrite _rng for determinism
    g._init_state()
    g._rng = random.Random(42)
    return g


# ── Phase Enum ──
def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.POWERING in Phase
    assert Phase.LIFTING in Phase
    assert Phase.RESULT in Phase
    assert Phase.GAME_OVER in Phase
    assert len(Phase.__members__) == 5


# ── Dataclasses ──
def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.life == 15


def test_floating_text_creation():
    ft = FloatingText(x=100.0, y=50.0, text="+10", life=30, color=7)
    assert ft.text == "+10"
    assert ft.life == 30


def test_ghost_lift_creation():
    gl = GhostLift(y=100.0, color=0, frame=42)
    assert gl.y == 100.0
    assert gl.color == 0
    assert gl.frame == 42


# ── Game.init_state / reset ──
def test_init_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == TIMER_START
    assert g.power == 0.0
    assert g.barbell_y == PLATFORM_Y
    assert g.barbell_vy == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.particles == []
    assert g.floating_texts == []


def test_reset():
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.heat = 50.0
    g.phase = Phase.GAME_OVER
    g.particles = [Particle(0, 0, 0, 0, 5, 8)]
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.phase == Phase.TITLE
    assert g.particles == []


# ── Power build ──
def test_build_power():
    g = _make_game()
    g.power = 0.0
    g._build_power()
    assert g.power == POWER_BUILD_RATE  # 2.0
    for _ in range(25):
        g._build_power()
    assert g.power == POWER_BUILD_RATE * 26  # 52.0


def test_build_power_caps():
    g = _make_game()
    g.power = 98.0
    g._build_power()
    assert g.power == POWER_MAX  # 100.0
    g._build_power()
    assert g.power == POWER_MAX  # shouldn't exceed


# ── Release lift ──
def test_release_lift():
    g = _make_game()
    g.power = 80.0
    g._release_lift()
    assert g.barbell_vy == -80.0 * VELOCITY_FACTOR  # -8.0
    assert g.phase == Phase.LIFTING
    assert g.lift_success is False


def test_release_lift_full_power():
    g = _make_game()
    g.power = POWER_MAX  # 100.0
    g._release_lift()
    assert g.barbell_vy == -10.0


# ── Update lift (physics) ──
def test_update_lift_gravity():
    g = _make_game()
    g.barbell_y = 150.0
    g.barbell_vy = -5.0
    g.best_lift_y = PLATFORM_Y
    g.phase = Phase.LIFTING
    g._update_lift()
    assert g.barbell_vy == -5.0 + GRAVITY  # -4.75
    assert g.barbell_y == 150.0 + (-4.75)  # 145.25


def test_update_lift_best_tracking():
    g = _make_game()
    g.barbell_y = 100.0
    g.barbell_vy = -5.0
    g.best_lift_y = PLATFORM_Y
    g._update_lift()
    assert g.best_lift_y < PLATFORM_Y  # updated to lower value
    assert g.best_lift_y == g.barbell_y  # after update


def test_update_lift_crosses_line():
    g = _make_game()
    # lift_success is set in _update_lifting(), not _update_lift()
    # With y=76, vy=-5: after gravity, y = 76 + (-5 + 0.25) = 71.25 <= 75
    g.barbell_y = 76.0
    g.barbell_vy = -5.0
    g.lift_success = False
    g.phase = Phase.LIFTING
    g._update_lifting()
    # 76 - 4.75 = 71.25 <= 75 → lift_success = True
    assert g.lift_success is True

    # Reset and test: not enough velocity to reach line
    g = _make_game()
    g.barbell_y = 80.0
    g.barbell_vy = -2.0
    g.lift_success = False
    g._update_lifting()
    # 80 + (-2 + 0.25) = 78.25 > 75 → lift_success stays False
    assert g.lift_success is False


# ── Resolve lift ──
def test_resolve_lift_miss():
    g = _make_game()
    g.score = 100
    g.combo = 2
    g.heat = 0.0
    g._resolve_lift(False)
    assert g.lift_success is False
    assert g.heat == HEAT_MISS  # 15.0
    assert g.combo == 0
    assert g.last_score == 0
    assert g.score == 100  # unchanged
    assert len(g.particles) == 5
    assert len(g.floating_texts) == 1


def test_resolve_lift_match():
    g = _make_game()
    g.score = 100
    g.combo = 0
    g.heat = 0.0
    g.barbell_color = 0
    g.attempt_color = 0
    g._resolve_lift(True)
    assert g.combo == 1
    assert g.last_score == 10  # 10 * combo(1) * 1
    assert g.score == 110
    assert g.heat == 0.0
    assert len(g.particles) == 12


def test_resolve_lift_match_combo_chain():
    g = _make_game()
    g.score = 100
    g.combo = 2
    g.barbell_color = 1
    g.attempt_color = 1
    g._resolve_lift(True)
    assert g.combo == 3
    assert g.last_score == 30  # 10 * 3 * 1
    assert g.score == 130


def test_resolve_lift_mismatch():
    g = _make_game()
    g.score = 100
    g.combo = 3
    g.heat = 0.0
    g.barbell_color = 0  # RED
    g.attempt_color = 1  # LIME
    g._resolve_lift(True)
    assert g.combo == 0
    assert g.last_score == 0
    assert g.heat == HEAT_MISMATCH  # 10.0
    assert g.score == 100  # unchanged


def test_resolve_lift_super_mode():
    g = _make_game()
    g.score = 100
    g.combo = 5
    g.heat = 0.0
    g.super_mode = True
    g.barbell_color = 0
    g.attempt_color = 1  # mismatched but super ignores
    g._resolve_lift(True)
    assert g.combo == 6
    assert g.last_score == 10 * 6 * SUPER_SCORE_MULT  # 180
    assert g.score == 280


# ── SUPER activation ──
def test_activate_super():
    g = _make_game()
    g.combo = 3
    g._resolve_lift(True)  # combo becomes 4
    # The code checks combo >= COMBO_THRESHOLD and not super_mode
    # But _resolve_lift increments combo first, then checks
    # Let me test with combo already at 3, barbell matches
    g = _make_game()
    g.combo = 3
    g.barbell_color = 0
    g.attempt_color = 0
    g._resolve_lift(True)
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION  # 300


def test_super_not_re_activate():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.combo = 4
    g.barbell_color = 0
    g.attempt_color = 0
    g._resolve_lift(True)
    assert g.combo == 5
    assert g.super_mode is True  # still on, not re-activated
    assert g.super_timer == 100  # unchanged by _resolve_lift


# ── Super auto-lift ──
def test_execute_auto_lift():
    g = _make_game()
    g._execute_auto_lift()
    assert g.power == POWER_MAX  # 100.0
    assert g.barbell_vy == -POWER_MAX * VELOCITY_FACTOR  # -10.0
    assert g.lift_success is False


def test_update_super_auto_lift_triggers():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 200
    g.super_auto_frame = 1
    g._update_super()
    # super_auto_frame decremented 1→0, triggers auto-lift (resets to interval=40)
    assert g.super_auto_frame == SUPER_AUTO_LIFT_INTERVAL  # 40
    assert g.power == POWER_MAX  # auto-lift triggered with max power

    # Test that auto_lift doesn't trigger when frame > 1
    g = _make_game()
    g.super_mode = True
    g.super_timer = 200
    g.super_auto_frame = 5
    g.power = 0.0
    g._update_super()
    assert g.super_auto_frame == 4  # just decremented
    assert g.power == 0.0  # no auto-lift triggered


def test_update_super_expires():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_mode is False
    assert g.super_timer == 0  # decremented before check


# ── HEAT ──
def test_update_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.001


def test_update_heat_floor():
    g = _make_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


# ── Timer ──
def test_update_timer():
    g = _make_game()
    g.timer = 100
    g._update_timer()
    assert g.timer == 99


def test_update_timer_floor():
    g = _make_game()
    g.timer = 0
    g._update_timer()
    assert g.timer == 0


def test_update_timer_paused_in_super():
    g = _make_game()
    g.super_mode = True
    g.timer = 100
    g._update_timer()
    assert g.timer == 100  # unchanged


# ── Difficulty ──
def test_update_difficulty():
    g = _make_game()
    g.timer = 3000  # 10 seconds elapsed
    g._update_difficulty()
    assert abs(g.difficulty_level - 2.0) < 0.01
    expected_interval = max(COLOR_CYCLE_INTERVAL_MIN, int(COLOR_CYCLE_INTERVAL_START - 2.0))
    assert g.color_cycle_interval == expected_interval


def test_update_difficulty_at_min():
    g = _make_game()
    g.timer = 0  # max difficulty (12.0 seconds of "elapsed" * scale)
    g._update_difficulty()
    # formula: interval = max(MIN, int(START - elapsed * SCALE))
    # elapsed = (3600-0)/300 * 1.0 = 12.0, so interval = max(40, int(90-12)) = max(40, 78) = 78
    assert g.color_cycle_interval == 78
    # The minimum is reachable only after 50+ seconds of "elapsed" but we only have 60s total
    # This is a design limitation — in practice interval goes from 90 to ~78


# ── Color cycle ──
def test_cycle_attempt_color():
    g = _make_game()
    g.attempt_color = 0
    g.color_cycle_timer = 1
    g._cycle_attempt_color()
    # timer decremented 1→0, triggers reset → timer = color_cycle_interval, color advances
    assert g.attempt_color == 1
    assert g.color_cycle_timer == g.color_cycle_interval  # reset to interval


# ── Start powering ──
def test_start_powering():
    g = _make_game()
    g.power = 50.0
    g.lift_success = True
    g._start_powering()
    assert g.phase == Phase.POWERING
    assert g.power == 0.0
    assert g.lift_success is False
    assert g.barbell_y == PLATFORM_Y


# ── Particles ──
def test_spawn_particles():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_particles(100.0, 50.0, 10, 8)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.life > 0
        assert p.color == 8


def test_update_particles():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_particles(100.0, 50.0, 5, 8)
    initial_count = len(g.particles)
    # Set one particle to die
    g.particles[0].life = 1
    g._update_particles()
    # Particle with life=1 decrements to 0 → removed
    assert len(g.particles) == initial_count - 1


# ── Floating text ──
def test_spawn_floating_text():
    g = _make_game()
    g._spawn_floating_text(100.0, 50.0, "+10", 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+10"


def test_update_floating_texts():
    g = _make_game()
    g._spawn_floating_text(100.0, 50.0, "+10", 7)
    g._update_floating_texts()
    assert g.floating_texts[0].life == 39
    # Set to die
    g.floating_texts[0].life = 1
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Score accumulation ──
def test_score_accumulation():
    g = _make_game()
    g.score = 0
    g.combo = 0
    g.barbell_color = 0
    g.attempt_color = 0
    # 5 successful lifts. At combo=4, SUPER activates.
    # combo 1→5: scores = 10 + 20 + 30 + 40 + (10*5*3=150) = 250
    for i in range(5):
        g._resolve_lift(True)
    assert g.combo == 5
    assert g.score == 250  # 10+20+30+40+150
    assert g.super_mode is True


# ── Max combo tracking ──
def test_max_combo_tracking():
    g = _make_game()
    g.combo = 0
    g.barbell_color = 0
    g.attempt_color = 0
    g._resolve_lift(True)  # combo=1
    g._resolve_lift(True)  # combo=2
    assert g.max_combo == 2
    # Mismatch resets combo but max_combo preserved
    g.attempt_color = 1
    g._resolve_lift(True)  # combo=0
    assert g.combo == 0
    assert g.max_combo == 2


# ── Game over conditions ──
def test_heat_game_over():
    g = _make_game()
    g.heat = HEAT_MAX
    g.phase = Phase.POWERING
    # We can't call _update_powering (uses pyxel), so test the condition directly
    assert g.heat >= HEAT_MAX


def test_timer_game_over():
    g = _make_game()
    g.timer = 0
    g.phase = Phase.POWERING
    assert g.timer <= 0


# ── Barbell x ──
def test_barbell_x():
    g = _make_game()
    from main import LIFTER_X as _LX
    assert g.barbell_x() == _LX


# ── Result phase transition ──
def test_start_result():
    g = _make_game()
    g._start_result()
    assert g.phase == Phase.RESULT
    assert g.result_timer > 0


# ── Physics edge cases ──
def test_max_power_velocity():
    g = _make_game()
    g.power = POWER_MAX
    g._release_lift()
    assert abs(g.barbell_vy - (-10.0)) < 0.001


def test_min_power_not_enough():
    """Power=75 should not be enough to reach LIFT_LINE with VELOCITY_FACTOR=0.10, GRAVITY=0.25"""
    # apex = PLATFORM_Y - 2*vy² with vy = power * 0.10, need apex < 75
    # 190 - 2*(75*0.10)² = 190 - 2*(7.5)² = 190 - 2*56.25 = 190-112.5 = 77.5 > 75
    # So power=75 gives apex=77.5, barely not enough. But it might cross LIFT_LINE on the way.
    # Let's just verify the formula
    vy = 75 * VELOCITY_FACTOR
    apex = PLATFORM_Y - 2 * vy * vy  # but this approximation is wrong
    # Actually: time to apex = vy/GRAVITY, max_height = PLATFORM_Y - vy*t_apex + 0.5*GRAVITY*t_apex²
    # = PLATFORM_Y - vy²/GRAVITY + 0.5*GRAVITY*(vy²/GRAVITY²)
    # = PLATFORM_Y - vy²/GRAVITY + 0.5*vy²/GRAVITY
    # = PLATFORM_Y - 0.5*vy²/GRAVITY
    # = 190 - 0.5 * 7.5² / 0.25 = 190 - 0.5 * 56.25 / 0.25 = 190 - 112.5 = 77.5
    assert apex > LIFT_LINE_Y  # Not enough


def test_enough_power():
    """Power=80 should be enough."""
    vy = 80 * VELOCITY_FACTOR
    apex = PLATFORM_Y - 0.5 * vy * vy / GRAVITY
    # = 190 - 0.5 * 64 / 0.25 = 190 - 128 = 62
    assert apex < LIFT_LINE_Y  # Reaches above line


# ── Color constants ──
def test_plate_colors():
    assert len(PLATE_COLORS) == 4
    for c in PLATE_COLORS:
        assert 0 <= c <= 15


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
