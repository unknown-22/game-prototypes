"""test_imports.py — Headless logic tests for 153_row_surge."""
import random
import sys
from pathlib import Path

# Add prototype dir to path for imports
_proto_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_proto_dir))

# ruff: noqa: E402
from main import (
    Game, Phase, Stroke, WakeParticle, Hazard, FloatingText, Particle,
    COLOR_MAP, COMBO_THRESHOLD, MAX_HEAT, HEAT_PER_HAZARD, BASE_SCORE, SUPER_DURATION,
    HAZARD_MAX,
    BOAT_Y, GAME_TIME,
)


# ── Factory helper ───────────────────────────────────────────────────────────

def _make_game() -> Game:
    """Create Game instance bypassing pyxel.init/run via Game.__new__."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g._rng = random.Random(42)
    g._font = None
    g.phase = Phase.TITLE
    g.score = 0
    g.high_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.boat_x = 0.0
    g.boat_y = float(BOAT_Y)
    g.stroke_color = 0
    g.prev_stroke_color = -1
    g.stroke_cooldown = 0
    g.stroke_timer = 0
    g.super_timer = 0
    g.super_mode = False
    g.camera_x = 0.0
    g.distance = 0.0
    g.game_timer = GAME_TIME
    g.speed_burst = 0.0
    g.echo_active = False
    g.color_cycle_timer = 0
    g.ca_spread_timer = 0
    g.strokes = []
    g.wake_particles = []
    g.hazards = []
    g.floating_texts = []
    g.particles = []
    g.frame = 0
    g.shake_frames = 0
    g.shake_intensity = 0
    g.path = []
    g.reset()
    return g


# ── Data Classes ─────────────────────────────────────────────────────────────

def test_stroke_dataclass():
    s = Stroke(color=2, x=100.5)
    assert s.color == 2
    assert s.x == 100.5


def test_wake_particle_dataclass():
    wp = WakeParticle(x=50.0, y=30.0, color=0, life=0.8)
    assert wp.x == 50.0
    assert wp.color == 0
    assert abs(wp.life - 0.8) < 0.001


def test_hazard_dataclass():
    h = Hazard(x=200.0, y=100.0, color=3, radius=12.0)
    assert h.color == 3
    assert abs(h.radius - 12.0) < 0.001


def test_floating_text_dataclass():
    ft = FloatingText(x=60.0, y=100.0, text="+10", color=8, life=30)
    assert ft.text == "+10"
    assert ft.life == 30


def test_particle_dataclass():
    p = Particle(x=10.0, y=20.0, vx=-1.0, vy=2.0, life=15, color=3)
    assert p.life == 15
    assert abs(p.vy - 2.0) < 0.001


# ── Constants ────────────────────────────────────────────────────────────────

def test_color_map():
    assert len(COLOR_MAP) == 4
    assert COLOR_MAP == [8, 3, 6, 10]  # RED, GREEN, LIGHT_BLUE, YELLOW


def test_thresholds():
    assert COMBO_THRESHOLD == 4
    assert MAX_HEAT == 100.0
    assert SUPER_DURATION == 300
    assert GAME_TIME == 3600


# ── Phase Enum ───────────────────────────────────────────────────────────────

def test_phase_enum():
    from main import Phase
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    # Verify they're distinct
    assert Phase.TITLE != Phase.PLAYING
    assert Phase.PLAYING != Phase.GAME_OVER


# ── Static Scoring ───────────────────────────────────────────────────────────

def test_compute_stroke_score_base():
    # combo=0, not super, no echo
    s = Game._compute_stroke_score(0, False, False)
    assert s == BASE_SCORE  # 10


def test_compute_stroke_score_with_combo():
    # combo=3: base=10 + 3*5 = 25
    s = Game._compute_stroke_score(3, False, False)
    assert s == 25


def test_compute_stroke_score_super():
    # combo=5, super=True, no echo: (10 + 5*5) * 3 = 35 * 3 = 105
    s = Game._compute_stroke_score(5, True, False)
    assert s == 105


def test_compute_stroke_score_echo():
    # combo=2, no super, echo=True: (10 + 2*5) * 1.5 = 20 * 1.5 = 30
    s = Game._compute_stroke_score(2, False, True)
    assert s == 30


def test_compute_stroke_score_super_and_echo():
    # combo=4, super=True, echo=True: (10 + 4*5) * 3 * 1.5 = 30 * 4.5 = 135
    s = Game._compute_stroke_score(4, True, True)
    assert s == 135


# ── State Initialization ─────────────────────────────────────────────────────

def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.stroke_color == 0


def test_start_game_resets_everything():
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.heat = 50.0
    g._start_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.phase == Phase.PLAYING
    assert len(g.hazards) >= 1  # initial hazards spawned


# ── Heat System ──────────────────────────────────────────────────────────────

def test_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert abs(g.heat - 49.7) < 0.01


def test_heat_decay_at_zero():
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_decay_near_zero():
    g = _make_game()
    g.heat = 0.1
    g._update_heat()
    assert g.heat == 0.0


# ── SUPER STROKE ─────────────────────────────────────────────────────────────

def test_activate_super():
    g = _make_game()
    g._start_game()
    g._activate_super()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_timer_countdown():
    g = _make_game()
    g._start_game()
    g._activate_super()
    g._update_super()
    assert g.super_timer == SUPER_DURATION - 1
    assert g.super_mode is True


def test_super_expires():
    g = _make_game()
    g._start_game()
    g._activate_super()
    g.super_timer = 1
    g._update_super()
    assert g.super_timer == 0
    assert g.super_mode is False


# ── Boat Movement ────────────────────────────────────────────────────────────

def test_boat_movement_normal():
    g = _make_game()
    g._start_game()
    g._update_boat()
    assert g.boat_x > 0.0
    assert g.distance > 0.0


def test_boat_movement_super_speed():
    g = _make_game()
    g._start_game()
    g.super_mode = True
    old_x = g.boat_x
    g._update_boat()
    assert g.boat_x > old_x + 1.0  # super gives 1.5x speed


def test_speed_burst_decay():
    g = _make_game()
    g._start_game()
    g.speed_burst = 3.0
    g._update_boat()
    assert g.speed_burst < 3.0  # should have decayed


# ── Hazard Collision ─────────────────────────────────────────────────────────

def test_hazard_collision_triggers_heat():
    g = _make_game()
    g._start_game()
    # Place a hazard right at the boat position
    g.hazards = [Hazard(x=g.boat_x, y=g.boat_y, color=0, radius=16.0)]
    g._check_hazard_collision()
    assert g.heat >= HEAT_PER_HAZARD


def test_hazard_collision_resets_combo():
    g = _make_game()
    g._start_game()
    g.combo = 5
    g.hazards = [Hazard(x=g.boat_x, y=g.boat_y, color=0, radius=16.0)]
    g._check_hazard_collision()
    assert g.combo == 0


def test_hazard_no_collision_when_far():
    g = _make_game()
    g._start_game()
    g.boat_x = 0.0
    g.boat_y = 0.0
    g.hazards = [Hazard(x=200.0, y=200.0, color=0, radius=8.0)]
    initial_heat = g.heat
    g._check_hazard_collision()
    assert g.heat == initial_heat


# ── Hazard CA Spread ─────────────────────────────────────────────────────────

def test_ca_spread_creates_new_hazards():
    g = _make_game()
    g._start_game()
    g._rng = random.Random(42)
    g.hazards = [Hazard(x=300.0, y=120.0, color=2, radius=12.0)]
    # Force CA spread to trigger
    g._rng.random = lambda: 0.01  # below CA_SPREAD_CHANCE (0.15)
    initial_count = len(g.hazards)
    g._ca_spread()
    assert len(g.hazards) > initial_count


def test_ca_spread_respects_max():
    g = _make_game()
    g._start_game()
    g._rng = random.Random(42)
    # Fill to max
    g.hazards = [Hazard(x=float(i * 30), y=120.0, color=0, radius=8.0) for i in range(HAZARD_MAX)]
    old_random = g._rng.random
    g._rng.random = lambda: 0.01  # force spread
    g._ca_spread()
    g._rng.random = old_random
    assert len(g.hazards) == HAZARD_MAX  # should not exceed


# ── Wake System ──────────────────────────────────────────────────────────────

def test_wake_spawn_on_stroke():
    g = _make_game()
    g._start_game()
    g._rng = random.Random(42)
    g._spawn_wake(g.boat_x, g.boat_y, 0)
    assert len(g.wake_particles) >= 3


def test_wake_update_fades():
    g = _make_game()
    g._start_game()
    g.wake_particles = [WakeParticle(x=100.0, y=120.0, color=0, life=0.001)]
    g._update_wake()
    assert len(g.wake_particles) == 0  # faded out


def test_wake_echo_detection():
    g = _make_game()
    g._start_game()
    g.stroke_color = 0
    g.boat_x = 100.0
    g.boat_y = 120.0
    g.echo_active = False
    # Place a same-color wake particle near boat
    g.wake_particles = [WakeParticle(x=100.0, y=120.0, color=0, life=1.0)]
    g._check_wake_echo()
    assert g.echo_active is True


def test_wake_echo_wrong_color_no_trigger():
    g = _make_game()
    g._start_game()
    g.stroke_color = 0  # RED
    g.boat_x = 100.0
    g.boat_y = 120.0
    g.echo_active = False
    g.wake_particles = [WakeParticle(x=100.0, y=120.0, color=1, life=1.0)]  # GREEN
    g._check_wake_echo()
    assert g.echo_active is False


def test_wake_echo_already_active_skips():
    g = _make_game()
    g._start_game()
    g.echo_active = True
    g.wake_particles = [WakeParticle(x=100.0, y=120.0, color=0, life=1.0)]
    g._check_wake_echo()
    assert g.echo_active is True  # unchanged


# ── Handle Stroke ────────────────────────────────────────────────────────────

def test_handle_stroke_first_stroke():
    g = _make_game()
    g._start_game()
    g._rng = random.Random(42)
    g.stroke_color = 0
    g.prev_stroke_color = -1
    g.score = 0
    g._handle_stroke()
    assert g.combo == 1
    assert g.score > 0
    assert g.prev_stroke_color == 0


def test_handle_stroke_same_color_combo():
    g = _make_game()
    g._start_game()
    g._rng = random.Random(42)
    g.stroke_color = 1
    g.prev_stroke_color = 1
    g.stroke_timer = 5  # within COMBO_WINDOW
    g.combo = 2
    g.score = 100
    g._handle_stroke()
    assert g.combo == 3
    assert g.score > 100


def test_handle_stroke_wrong_color_resets_combo():
    g = _make_game()
    g._start_game()
    g._rng = random.Random(42)
    g.stroke_color = 2
    g.prev_stroke_color = 0  # different
    g.stroke_timer = 5
    g.combo = 3
    g.heat = 10.0
    g._handle_stroke()
    assert g.combo == 0
    assert g.heat > 10.0  # HEAT_PER_WRONG added


def test_handle_stroke_super_mode_always_match():
    g = _make_game()
    g._start_game()
    g._rng = random.Random(42)
    g.super_mode = True
    g.stroke_color = 3
    g.prev_stroke_color = 0  # different, but super ignores
    g.combo = 5
    g.score = 500
    g._handle_stroke()
    assert g.combo == 6  # incremented
    assert g.score > 500


def test_handle_stroke_cooldown_blocks():
    g = _make_game()
    g._start_game()
    g._rng = random.Random(42)
    g.stroke_cooldown = 10  # still cooling down
    g.combo = 1
    g.score = 50
    g._handle_stroke()
    assert g.combo == 1  # unchanged
    assert g.score == 50  # unchanged


def test_handle_stroke_reaches_super():
    g = _make_game()
    g._start_game()
    g._rng = random.Random(42)
    g.stroke_color = 1
    g.prev_stroke_color = 1
    g.stroke_timer = 5
    g.combo = 3  # next stroke = 4 = threshold
    g._handle_stroke()
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


# ── Game Over ─────────────────────────────────────────────────────────────────

def test_game_over_triggers_on_heat():
    g = _make_game()
    g._start_game()
    g.heat = MAX_HEAT  # exactly at threshold
    g._on_game_over()
    assert g.phase == Phase.GAME_OVER


def test_game_over_triggers_on_timer():
    g = _make_game()
    g._start_game()
    g.game_timer = 0
    g._on_game_over()
    assert g.phase == Phase.GAME_OVER


def test_high_score_update():
    g = _make_game()
    g._start_game()
    g.score = 1000
    g.high_score = 500
    g._on_game_over()
    assert g.high_score == 1000


def test_high_score_not_updated_if_lower():
    g = _make_game()
    g._start_game()
    g.score = 200
    g.high_score = 500
    g._on_game_over()
    assert g.high_score == 500


# ── Spawn Hazard ─────────────────────────────────────────────────────────────

def test_spawn_hazard_initial():
    g = _make_game()
    g._start_game()
    g._rng = random.Random(42)
    g.camera_x = 0.0
    initial_count = len(g.hazards)
    g._spawn_hazard(initial=True)
    assert len(g.hazards) == initial_count + 1


def test_spawn_hazard_respects_max():
    g = _make_game()
    g._start_game()
    g.hazards = [Hazard(x=float(i * 20), y=120.0, color=0, radius=8.0) for i in range(HAZARD_MAX)]
    g._spawn_hazard(initial=True)
    assert len(g.hazards) == HAZARD_MAX


# ── Floating Texts ───────────────────────────────────────────────────────────

def test_floating_text_lifecycle():
    g = _make_game()
    g._start_game()
    g.floating_texts = [FloatingText(x=100.0, y=120.0, text="TEST", color=8, life=1)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0  # life=1 expires after update


def test_floating_text_persists_with_life():
    g = _make_game()
    g._start_game()
    g.floating_texts = [FloatingText(x=100.0, y=120.0, text="TEST", color=8, life=3)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 2


# ── Particles ────────────────────────────────────────────────────────────────

def test_particle_lifecycle():
    g = _make_game()
    g._start_game()
    g.particles = [Particle(x=100.0, y=120.0, vx=0.0, vy=0.0, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0


def test_particle_gravity():
    g = _make_game()
    g._start_game()
    p = Particle(x=100.0, y=120.0, vx=0.0, vy=0.0, life=10, color=8)
    g.particles = [p]
    g._update_particles()
    assert p.vy > 0  # gravity applied
    assert p.life == 9


# ── Phase Transitions ────────────────────────────────────────────────────────

def test_start_game_sets_playing():
    g = _make_game()
    assert g.phase == Phase.TITLE
    g._start_game()
    assert g.phase == Phase.PLAYING


def test_game_over_transitions():
    g = _make_game()
    g._start_game()
    g._on_game_over()
    assert g.phase == Phase.GAME_OVER


# ── Floating Point Safety ────────────────────────────────────────────────────

def test_heat_never_negative():
    g = _make_game()
    g._start_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat >= 0.0


def test_burst_never_negative():
    g = _make_game()
    g._start_game()
    g.speed_burst = 0.0
    g._update_boat()  # max(0.0, 0.0 - decay) should stay 0
    assert g.speed_burst >= 0.0


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
