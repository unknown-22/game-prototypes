"""test_imports.py — Headless logic tests for SIGNAL SURGE (139_signal_surge)."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    BLACK,
    GREEN,
    LIGHT_BLUE,
    WHITE,
    RED,
    ORANGE,
    YELLOW,
    LIME,
    CYAN,
    PINK,
    PEACH,
    PURPLE,
    SIGNAL_COLORS,
    SCREEN_W,
    SCREEN_H,
    FPS,
    LANE_COUNT,
    LANE_TOP,
    LANE_H,
    LANE_CENTER_Y,
    MAX_HEAT,
    SUPER_DURATION,
    COMBO_THRESHOLD,
    BASE_SCORE,
    WRONG_HEAT,
    MISS_HEAT,
    INITIAL_SPAWN_INTERVAL,
    MIN_SPAWN_INTERVAL,
    SIGNAL_W,
    SIGNAL_H,
    BASE_SPEED,
    Signal,
    Particle,
    Phase,
    Game,
)


# ══════════════════════════════════════════════════
# Factory
# ══════════════════════════════════════════════════
def _make_game() -> Game:
    """Create a Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.signals = []
    g.particles = []
    g.spawn_timer = 0
    g.game_timer = 0
    g.spawn_interval = INITIAL_SPAWN_INTERVAL
    g.decoded_count = 0
    g._rng = random.Random(42)
    g._super_flash = 0
    g._shake_timer = 0
    g._popup_texts = []
    g.reset()
    g._rng = random.Random(42)  # re-seed after reset()
    return g


# ══════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════
def test_color_constants():
    """Verify color constants are correct int values."""
    assert RED == 8
    assert GREEN == 3
    assert LIGHT_BLUE == 6
    assert YELLOW == 10
    assert WHITE == 7
    assert BLACK == 0
    assert len(SIGNAL_COLORS) == 4
    assert SIGNAL_COLORS == [RED, GREEN, LIGHT_BLUE, YELLOW]


def test_screen_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert FPS == 30


def test_lane_config():
    assert LANE_COUNT == 4
    assert len(LANE_CENTER_Y) == 4
    assert LANE_CENTER_Y[0] == LANE_TOP + LANE_H // 2  # 40 + 20 = 60
    assert LANE_CENTER_Y[3] == LANE_TOP + 3 * LANE_H + LANE_H // 2  # 40 + 120 + 20 = 180


def test_game_constants():
    assert MAX_HEAT == 100
    assert SUPER_DURATION == 5 * 30  # 150
    assert COMBO_THRESHOLD == 5
    assert BASE_SCORE == 10
    assert WRONG_HEAT == 15
    assert MISS_HEAT == 5
    assert INITIAL_SPAWN_INTERVAL == 45
    assert MIN_SPAWN_INTERVAL == 15
    assert SIGNAL_W == 30
    assert SIGNAL_H == 20
    assert BASE_SPEED == 1.5


# ══════════════════════════════════════════════════
# Data classes
# ══════════════════════════════════════════════════
def test_signal_dataclass():
    s = Signal(x=100.0, y=60.0, color=RED, speed=1.5, color_idx=0)
    assert s.x == 100.0
    assert s.y == 60.0
    assert s.color == RED
    assert s.speed == 1.5
    assert s.color_idx == 0
    assert s.active is True
    assert s.flash_timer == 0


def test_particle_dataclass():
    p = Particle(x=50.0, y=50.0, vx=1.0, vy=-2.0, life=20, max_life=20, color=RED, size=2)
    assert p.life == 20
    assert p.max_life == 20
    assert p.color == RED
    assert p.size == 2


# ══════════════════════════════════════════════════
# Phase enum
# ══════════════════════════════════════════════════
def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ══════════════════════════════════════════════════
# Game.reset()
# ══════════════════════════════════════════════════
def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.signals == []
    assert g.particles == []
    assert g.spawn_timer == 0
    assert g.game_timer == 0
    assert g.spawn_interval == INITIAL_SPAWN_INTERVAL
    assert g.decoded_count == 0
    assert g._super_flash == 0
    assert g._shake_timer == 0
    assert g._popup_texts == []


# ══════════════════════════════════════════════════
# _spawn_signal
# ══════════════════════════════════════════════════
def test_spawn_signal_creates_valid_signal():
    g = _make_game()
    g._rng = random.Random(42)
    s = g._spawn_signal()
    assert s is not None
    assert s.x == float(SCREEN_W + SIGNAL_W)  # 320 + 30 = 350
    assert s.active is True
    assert s.color in SIGNAL_COLORS
    assert s.color_idx in (0, 1, 2, 3)
    assert s.speed >= BASE_SPEED


def test_spawn_signal_deterministic_with_seed():
    g1 = _make_game()
    g1._rng = random.Random(42)
    s1 = g1._spawn_signal()
    assert s1 is not None

    g2 = _make_game()
    g2._rng = random.Random(42)
    s2 = g2._spawn_signal()
    assert s2 is not None

    assert s1.color_idx == s2.color_idx
    assert s1.x == s2.x


# ══════════════════════════════════════════════════
# _current_speed
# ══════════════════════════════════════════════════
def test_current_speed_increases():
    g = _make_game()
    assert g._current_speed() == BASE_SPEED
    g.decoded_count = 100
    assert g._current_speed() == BASE_SPEED + 100 * 0.03
    assert g._current_speed() > BASE_SPEED


# ══════════════════════════════════════════════════
# _update_signals
# ══════════════════════════════════════════════════
def test_update_signals_moves_signals_left():
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=2.0, color_idx=0)]
    g._update_signals()
    assert g.signals[0].x == 198.0


def test_update_signals_removes_off_screen():
    g = _make_game()
    g.signals = [Signal(x=-SIGNAL_W - 1, y=60.0, color=RED, speed=1.0, color_idx=0)]
    g._update_signals()
    assert len(g.signals) == 0
    assert g.heat == MISS_HEAT  # 5


def test_update_signals_removes_inactive():
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0, active=False)]
    g._update_signals()
    assert len(g.signals) == 0


def test_update_signals_flash_timer_decrements():
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0, flash_timer=5)]
    g._update_signals()
    assert g.signals[0].flash_timer == 4


# ══════════════════════════════════════════════════
# _find_decode_target
# ══════════════════════════════════════════════════
def test_find_decode_target_returns_rightmost():
    g = _make_game()
    g.signals = [
        Signal(x=100.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=150.0, y=100.0, color=RED, speed=1.0, color_idx=0),
    ]
    target = g._find_decode_target(0)
    assert target is not None
    assert target.x == 200.0


def test_find_decode_target_returns_none_for_wrong_color():
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    target = g._find_decode_target(1)  # GREEN
    assert target is None


def test_find_decode_target_skips_inactive():
    g = _make_game()
    g.signals = [
        Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0, active=False),
    ]
    target = g._find_decode_target(0)
    assert target is None


# ══════════════════════════════════════════════════
# _decode_signal
# ══════════════════════════════════════════════════
def test_decode_signal_successful():
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    score, success = g._decode_signal(0)  # RED
    assert success is True
    assert score == BASE_SCORE  # combo=1, multiplier=1.0
    assert g.combo == 1
    assert g.decoded_count == 1


def test_decode_signal_no_matching_signal():
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    score, success = g._decode_signal(1)  # GREEN, no match
    assert success is False
    assert score == 0


def test_decode_signal_deactivates_target():
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    g._decode_signal(0)
    assert g.signals[0].active is False


def test_decode_signal_combo_multiplier():
    g = _make_game()
    g.signals = [
        Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=180.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=160.0, y=60.0, color=RED, speed=1.0, color_idx=0),
    ]
    # 1st: combo=1, multiplier=1.0
    score1, _ = g._decode_signal(0)
    assert score1 == BASE_SCORE  # 10
    # 2nd: combo=2, multiplier=1.5
    score2, _ = g._decode_signal(0)
    assert score2 == int(BASE_SCORE * 1.5)  # 15
    # 3rd: combo=3, multiplier=2.0
    score3, _ = g._decode_signal(0)
    assert score3 == int(BASE_SCORE * 2.0)  # 20


def test_decode_signal_multiplier_capped_at_5():
    g = _make_game()
    g.combo = 20  # would be >5.0 without cap
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    score, _ = g._decode_signal(0)
    assert score == int(BASE_SCORE * 5.0)  # 50, capped


def test_decode_signal_triggers_super_at_threshold():
    g = _make_game()
    g.combo = COMBO_THRESHOLD - 1  # 4
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    score, success = g._decode_signal(0)
    assert success is True
    assert g.combo == COMBO_THRESHOLD  # 5
    assert g.super_timer == SUPER_DURATION  # 150


def test_decode_signal_does_not_re_trigger_super():
    g = _make_game()
    g.combo = COMBO_THRESHOLD  # 5
    g.super_timer = SUPER_DURATION  # already in super
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    g._decode_signal(0)
    # super_timer should remain at SUPER_DURATION (not reset to 150 again)
    assert g.super_timer == SUPER_DURATION


def test_decode_signal_max_combo_tracks():
    g = _make_game()
    g.signals = [
        Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=180.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=160.0, y=60.0, color=RED, speed=1.0, color_idx=0),
    ]
    g._decode_signal(0)
    assert g.max_combo == 1
    g._decode_signal(0)
    assert g.max_combo == 2
    g._decode_signal(0)
    assert g.max_combo == 3


# ══════════════════════════════════════════════════
# _decode_wrong
# ══════════════════════════════════════════════════
def test_decode_wrong_adds_heat():
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    score, success = g._decode_wrong(1)  # GREEN, RED is on screen
    assert success is False
    assert score == 0
    assert g.heat == WRONG_HEAT  # 15
    assert g.combo == 0


def test_decode_wrong_no_signals_on_screen():
    g = _make_game()
    score, success = g._decode_wrong(0)
    assert success is False
    assert score == 0
    assert g.heat == 0  # no signals, no penalty


def test_decode_wrong_matching_color_present():
    """_decode_wrong should NOT penalize if a signal of that color IS on screen (it's handled by _decode_signal)."""
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    score, success = g._decode_wrong(0)  # RED is present
    assert success is False  # not a "wrong" - it has a target
    assert g.heat == 0  # no penalty since target exists


# ══════════════════════════════════════════════════
# _process_decode_key (main decode entry)
# ══════════════════════════════════════════════════
def test_process_decode_key_match():
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    score, was_match, pcol, px, py = g._process_decode_key(0)  # RED
    assert was_match is True
    assert score > 0
    assert pcol == RED
    assert px == 200.0
    assert py == 60.0


def test_process_decode_key_wrong():
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    score, was_match, pcol, px, py = g._process_decode_key(1)  # GREEN, no GREEN signals
    assert was_match is False
    assert score == 0
    assert g.heat == WRONG_HEAT  # 15
    assert g.combo == 0


def test_process_decode_key_during_super():
    g = _make_game()
    g.super_timer = 30
    g.signals = [
        Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=180.0, y=100.0, color=GREEN, speed=1.0, color_idx=1),
    ]
    score, was_match, pcol, px, py = g._process_decode_key(0)
    assert was_match is True
    assert score > 0  # 3x during super
    assert len([s for s in g.signals if s.active]) == 0  # all decoded


# ══════════════════════════════════════════════════
# _super_decode_all
# ══════════════════════════════════════════════════
def test_super_decode_all_decodes_everything():
    g = _make_game()
    g.signals = [
        Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=180.0, y=100.0, color=GREEN, speed=1.0, color_idx=1),
        Signal(x=160.0, y=140.0, color=LIGHT_BLUE, speed=1.0, color_idx=2),
    ]
    total, success = g._super_decode_all()
    assert success is True
    assert total > 0
    assert all(not s.active for s in g.signals)
    assert g.decoded_count == 3


def test_super_decode_all_3x_multiplier():
    g = _make_game()
    g.combo = 0
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    total, _ = g._super_decode_all()
    # combo becomes 1, multiplier=1.0, score = 10 * 1.0 * 3 = 30
    assert total == 30


def test_super_decode_all_skips_inactive():
    g = _make_game()
    g.signals = [
        Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=180.0, y=100.0, color=GREEN, speed=1.0, color_idx=1, active=False),
    ]
    total, _ = g._super_decode_all()
    assert g.decoded_count == 1  # only the active one


# ══════════════════════════════════════════════════
# _update_super
# ══════════════════════════════════════════════════
def test_update_super_ticks_down():
    g = _make_game()
    g.super_timer = 10
    g.combo = 5
    g._update_super()
    assert g.super_timer == 9


def test_update_super_resets_combo_on_expire():
    g = _make_game()
    g.super_timer = 1
    g.combo = 10
    g._update_super()
    assert g.super_timer == 0
    assert g.combo == 0


def test_update_super_does_nothing_when_not_active():
    g = _make_game()
    g.super_timer = 0
    g.combo = 5
    g._update_super()
    assert g.super_timer == 0
    assert g.combo == 5  # unchanged


# ══════════════════════════════════════════════════
# _update_particles
# ══════════════════════════════════════════════════
def test_update_particles_moves_and_decays():
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=-1.0, life=5, max_life=5, color=RED)]
    g._update_particles()
    assert g.particles[0].x == 101.0
    assert g.particles[0].y == 99.0
    assert g.particles[0].life == 4


def test_update_particles_removes_dead():
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, max_life=5, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0


# ══════════════════════════════════════════════════
# _spawn_particles
# ══════════════════════════════════════════════════
def test_spawn_particles_creates_correct_count():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_particles(100.0, 100.0, RED, 8)
    assert len(g.particles) == 8


def test_spawn_particles_append():
    g = _make_game()
    existing = len(g.particles)
    g._rng = random.Random(42)
    g._spawn_particles(100.0, 100.0, RED, 5)
    assert len(g.particles) == existing + 5


# ══════════════════════════════════════════════════
# _spawn_super_particles
# ══════════════════════════════════════════════════
def test_spawn_super_particles_creates_30():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_super_particles()
    assert len(g.particles) == 30


# ══════════════════════════════════════════════════
# _update_difficulty
# ══════════════════════════════════════════════════
def test_update_difficulty_decreases_interval():
    g = _make_game()
    assert g.spawn_interval == INITIAL_SPAWN_INTERVAL  # 45
    g.decoded_count = 10
    g._update_difficulty()
    # reduction = 10 // 5 = 2, spawn_interval = 45 - 2*2 = 41
    assert g.spawn_interval == 41


def test_update_difficulty_min_interval():
    g = _make_game()
    g.decoded_count = 100
    g._update_difficulty()
    assert g.spawn_interval == MIN_SPAWN_INTERVAL  # 15


# ══════════════════════════════════════════════════
# _check_game_over
# ══════════════════════════════════════════════════
def test_check_game_over_below_threshold():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 99.0
    assert g._check_game_over() is False
    assert g.phase == Phase.PLAYING


def test_check_game_over_at_threshold():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 100.0
    assert g._check_game_over() is True
    assert g.phase == Phase.GAME_OVER
    assert g._shake_timer == 20


def test_check_game_over_above_threshold():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 150.0
    assert g._check_game_over() is True
    assert g.phase == Phase.GAME_OVER


# ══════════════════════════════════════════════════
# _get_score_multiplier
# ══════════════════════════════════════════════════
def test_get_score_multiplier_combo_0():
    g = _make_game()
    g.combo = 0
    assert g._get_score_multiplier() == 1.0


def test_get_score_multiplier_combo_1():
    g = _make_game()
    g.combo = 1
    assert g._get_score_multiplier() == 1.0


def test_get_score_multiplier_combo_3():
    g = _make_game()
    g.combo = 3
    assert g._get_score_multiplier() == 2.0  # 1.0 + (3-1)*0.5


def test_get_score_multiplier_combo_10_capped():
    g = _make_game()
    g.combo = 10
    assert g._get_score_multiplier() == 5.0  # capped


def test_get_score_multiplier_max_combo():
    """combo=9: 1.0 + 8*0.5 = 5.0 (at cap)"""
    g = _make_game()
    g.combo = 9
    assert g._get_score_multiplier() == 5.0


# ══════════════════════════════════════════════════
# _update_popups
# ══════════════════════════════════════════════════
def test_update_popups_move_up_and_decay():
    g = _make_game()
    g._popup_texts = [("+10", 100.0, 100.0, WHITE, 2)]
    g._update_popups()
    assert len(g._popup_texts) == 1
    assert g._popup_texts[0][2] == 98.5  # y - 1.5
    assert g._popup_texts[0][4] == 1  # life - 1


def test_update_popups_remove_expired():
    g = _make_game()
    g._popup_texts = [("+10", 100.0, 100.0, WHITE, 0)]
    g._update_popups()
    assert len(g._popup_texts) == 0


# ══════════════════════════════════════════════════
# Scoring integration
# ══════════════════════════════════════════════════
def test_score_accumulation():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.signals = [
        Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=180.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=160.0, y=60.0, color=RED, speed=1.0, color_idx=0),
    ]
    # Simulate 3 successful decodes (via _process_decode_key to get score)
    for _ in range(3):
        score, was_match, _, _, _ = g._process_decode_key(0)
        assert was_match
        g.score += score
    assert g.combo == 3
    assert g.score == 10 + 15 + 20  # 45


def test_super_triggers_and_auto_decodes():
    """After hitting combo threshold, super activates. On next key press during super, all signals auto-decode."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = COMBO_THRESHOLD - 1  # 4
    # Add 5 signals
    for i in range(5):
        g.signals.append(
            Signal(x=200.0 - i * 20, y=LANE_CENTER_Y[i % 4], color=SIGNAL_COLORS[i % 4],
                   speed=1.0, color_idx=i % 4)
        )
    # First decode triggers super (combo goes to 5), decodes ONE signal
    score, was_match, _, _, _ = g._process_decode_key(0)
    g.score += score
    assert g.super_timer > 0  # super activated
    assert g.combo == COMBO_THRESHOLD  # 5

    # Remaining signals are still active (super auto-decode runs on NEXT key press)
    active_count = sum(1 for s in g.signals if s.active)
    assert active_count == 4  # 5 total, 1 decoded

    # Next key press during super triggers auto-decode of ALL remaining
    score2, was_match2, _, _, _ = g._process_decode_key(0)
    g.score += score2
    assert all(not s.active for s in g.signals)


# ══════════════════════════════════════════════════
# Heat system
# ══════════════════════════════════════════════════
def test_miss_heat_accumulates():
    g = _make_game()
    g.heat = 95.0
    g.signals = [Signal(x=-SIGNAL_W - 1, y=60.0, color=RED, speed=1.0, color_idx=0)]
    g._update_signals()
    assert g.heat == 95.0 + MISS_HEAT  # 100
    assert len(g.signals) == 0


def test_wrong_key_heat():
    g = _make_game()
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    g._process_decode_key(1)  # GREEN — wrong
    assert g.heat == WRONG_HEAT  # 15


def test_heat_game_over_chain():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    # 6 wrong presses -> heat = 90
    for _ in range(6):
        g._process_decode_key(1)  # GREEN (wrong)
    assert g.heat == 90.0
    assert g.phase == Phase.PLAYING
    # 7th wrong press -> heat = 105, game over
    g._process_decode_key(1)
    assert g.heat >= 100.0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


# ══════════════════════════════════════════════════
# Speed / difficulty
# ══════════════════════════════════════════════════
def test_spawn_interval_decreases_with_decodes():
    g = _make_game()
    g.decoded_count = 0
    g._update_difficulty()
    assert g.spawn_interval == INITIAL_SPAWN_INTERVAL  # 45
    g.decoded_count = 15
    g._update_difficulty()
    # reduction = 15//5 = 3, spawn_interval = 45 - 3*2 = 39
    assert g.spawn_interval == 39


# ══════════════════════════════════════════════════
# _start_game
# ══════════════════════════════════════════════════
def test_start_game_resets_state():
    g = _make_game()
    g.phase = Phase.GAME_OVER
    g.score = 500
    g.heat = 80.0
    g.combo = 7
    g.max_combo = 10
    g.super_timer = 50
    g.decoded_count = 20
    g.signals = [Signal(x=100.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=5, max_life=5, color=RED)]

    g._start_game()

    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.signals == []
    assert g.particles == []
    assert g.spawn_interval == INITIAL_SPAWN_INTERVAL
    assert g.decoded_count == 0


# ══════════════════════════════════════════════════
# Edge cases
# ══════════════════════════════════════════════════
def test_no_signals_decode_does_nothing():
    g = _make_game()
    score, was_match, _, _, _ = g._process_decode_key(0)
    assert was_match is False
    assert score == 0
    assert g.heat == 0  # no signals = no penalty (per _process_decode_key logic)


def test_multiple_signals_same_color_rightmost_decoded():
    g = _make_game()
    g.signals = [
        Signal(x=100.0, y=60.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=200.0, y=100.0, color=RED, speed=1.0, color_idx=0),
        Signal(x=150.0, y=140.0, color=RED, speed=1.0, color_idx=0),
    ]
    target = g._find_decode_target(0)
    assert target is not None
    assert target.x == 200.0  # rightmost


def test_super_timer_exact_expiry():
    g = _make_game()
    g.super_timer = 1
    g.combo = 10
    g._update_super()
    assert g.super_timer == 0
    assert g.combo == 0  # combo resets when super expires


def test_heat_exact_100_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 100.0
    assert g._check_game_over() is True


def test_signal_speed_off_screen():
    """Very fast signal should move off screen in one update."""
    g = _make_game()
    g.signals = [Signal(x=50.0, y=60.0, color=RED, speed=100.0, color_idx=0)]
    g._update_signals()
    assert len(g.signals) == 0
    assert g.heat == MISS_HEAT


# ══════════════════════════════════════════════════
# Static helpers
# ══════════════════════════════════════════════════
def test_lighter_color_map():
    assert Game._lighter(RED) == ORANGE
    assert Game._lighter(GREEN) == LIME
    assert Game._lighter(LIGHT_BLUE) == CYAN
    assert Game._lighter(YELLOW) == PEACH
    assert Game._lighter(ORANGE) == YELLOW
    assert Game._lighter(BLACK) == WHITE  # default


def test_rainbow_color():
    colors = [RED, ORANGE, YELLOW, GREEN, LIGHT_BLUE, PURPLE, PINK]
    for i, expected in enumerate(colors):
        assert Game._rainbow_color(i) == expected
    # Wraps around
    assert Game._rainbow_color(len(colors)) == colors[0]


# ══════════════════════════════════════════════════
# Super decode 3x score verification
# ══════════════════════════════════════════════════
def test_super_decode_3x_multiplier_with_combo():
    """During super, score = base * multiplier * 3."""
    g = _make_game()
    g.combo = 2  # multiplier = 1.0 + 1*0.5 = 1.5
    g.signals = [Signal(x=200.0, y=60.0, color=RED, speed=1.0, color_idx=0)]
    total, _ = g._super_decode_all()
    # combo increments to 3 during decode, multiplier becomes 2.0
    # Actually _super_decode_all increments combo for each signal, so:
    # Signal 1: combo=3, multiplier=2.0, score=10*2.0*3=60
    assert total == 60
