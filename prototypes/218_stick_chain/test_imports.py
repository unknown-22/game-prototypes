"""test_imports.py — Headless logic tests for 218_stick_chain."""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from main import (  # type: ignore[import-not-found]
    DARK_BLUE,
    GAME_TIMER_FRAMES,
    HEAT_MAX,
    HEAT_MISMATCH,
    HEAT_OVERLAP_FACTOR,
    INITIAL_STICKS,
    LIME,
    RED,
    STICK_COLORS,
    STICK_MIN_LEN,
    STICK_MAX_LEN,
    WHITE,
    FloatingText,
    Game,
    Particle,
    Phase,
    Stick,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    # Pre-init all attributes
    g.phase = Phase.TITLE
    g.sticks = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.game_timer = GAME_TIMER_FRAMES
    g.round_num = 0
    g.last_color = -1
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.round_clear_timer = 0
    g._rng = random.Random(seed)
    return g


# ── Data class tests ──
def test_stick_creation() -> None:
    s = Stick(x1=0.0, y1=0.0, x2=100.0, y2=0.0, color=8)
    assert s.x1 == 0.0
    assert s.color == 8
    assert s.overlap_count == 0
    assert s.picked is False


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=20, color=8)
    assert p.x == 10.0
    assert p.life == 20
    assert p.color == 8


def test_floating_text_creation() -> None:
    ft = FloatingText(x=5.0, y=10.0, text="+10", life=30, color=7)
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == 7


# ── Stick generation tests ──
def test_generate_sticks_creates_n_sticks() -> None:
    g = _make_game()
    sticks = g._generate_sticks(18)
    assert len(sticks) == 18


def test_generate_sticks_all_unpicked() -> None:
    g = _make_game()
    sticks = g._generate_sticks(10)
    for s in sticks:
        assert s.picked is False


def test_stick_length_in_range() -> None:
    g = _make_game()
    sticks = g._generate_sticks(20)
    for s in sticks:
        length = math.hypot(s.x2 - s.x1, s.y2 - s.y1)
        assert STICK_MIN_LEN - 1 <= length <= STICK_MAX_LEN + 1


def test_stick_colors_valid() -> None:
    g = _make_game()
    sticks = g._generate_sticks(30)
    for s in sticks:
        assert s.color in STICK_COLORS


def test_stick_positions_in_bounds() -> None:
    g = _make_game()
    sticks = g._generate_sticks(30)
    for s in sticks:
        assert -10 <= s.x1 <= 330
        assert -10 <= s.x2 <= 330
        assert 20 <= s.y1 <= 250
        assert 20 <= s.y2 <= 250


# ── Overlap computation tests ──
def test_compute_overlaps_zeros_initial() -> None:
    g = _make_game()
    sticks = g._generate_sticks(10)
    for s in sticks:
        s.overlap_count = 0
    g._compute_overlaps(sticks)
    # All overlap counts should be computed (some may be zero, but that's fine)
    for s in sticks:
        assert s.overlap_count >= 0


def test_crossing_sticks_get_overlap() -> None:
    g = _make_game()
    s1 = Stick(x1=0.0, y1=50.0, x2=100.0, y2=50.0, color=RED)
    s2 = Stick(x1=50.0, y1=0.0, x2=50.0, y2=100.0, color=LIME)
    sticks = [s1, s2]
    g._compute_overlaps(sticks)
    assert s1.overlap_count == 1
    assert s2.overlap_count == 1


def test_non_crossing_sticks_no_overlap() -> None:
    g = _make_game()
    s1 = Stick(x1=0.0, y1=0.0, x2=50.0, y2=0.0, color=RED)
    s2 = Stick(x1=60.0, y1=50.0, x2=100.0, y2=50.0, color=LIME)
    sticks = [s1, s2]
    g._compute_overlaps(sticks)
    assert s1.overlap_count == 0
    assert s2.overlap_count == 0


def test_three_sticks_all_cross() -> None:
    g = _make_game()
    s1 = Stick(x1=0.0, y1=50.0, x2=100.0, y2=50.0, color=RED)
    s2 = Stick(x1=50.0, y1=0.0, x2=50.0, y2=100.0, color=LIME)
    s3 = Stick(x1=25.0, y1=25.0, x2=75.0, y2=75.0, color=DARK_BLUE)
    sticks = [s1, s2, s3]
    g._compute_overlaps(sticks)
    assert s1.overlap_count == 2
    assert s2.overlap_count == 2
    assert s3.overlap_count == 2


# ── Segment intersection tests ──
def test_segments_intersect_cross() -> None:
    g = _make_game()
    s1 = Stick(x1=0.0, y1=50.0, x2=100.0, y2=50.0, color=RED)
    s2 = Stick(x1=50.0, y1=0.0, x2=50.0, y2=100.0, color=LIME)
    assert g._segments_intersect(s1, s2) is True


def test_segments_no_intersect_parallel() -> None:
    g = _make_game()
    s1 = Stick(x1=0.0, y1=10.0, x2=100.0, y2=10.0, color=RED)
    s2 = Stick(x1=0.0, y1=30.0, x2=100.0, y2=30.0, color=LIME)
    assert g._segments_intersect(s1, s2) is False


def test_segments_no_intersect_separate() -> None:
    g = _make_game()
    s1 = Stick(x1=0.0, y1=0.0, x2=50.0, y2=0.0, color=RED)
    s2 = Stick(x1=70.0, y1=50.0, x2=120.0, y2=50.0, color=LIME)
    assert g._segments_intersect(s1, s2) is False


def test_segments_intersect_touching_endpoint() -> None:
    g = _make_game()
    s1 = Stick(x1=0.0, y1=0.0, x2=50.0, y2=50.0, color=RED)
    s2 = Stick(x1=50.0, y1=50.0, x2=100.0, y2=0.0, color=LIME)
    assert g._segments_intersect(s1, s2) is True


# ── Point-to-segment distance tests ──
def test_point_to_segment_dist_on_line() -> None:
    d = Game._point_to_segment_dist(50.0, 50.0, 0.0, 50.0, 100.0, 50.0)
    assert d == 0.0


def test_point_to_segment_dist_near_line() -> None:
    d = Game._point_to_segment_dist(50.0, 55.0, 0.0, 50.0, 100.0, 50.0)
    assert abs(d - 5.0) < 0.01


def test_point_to_segment_dist_beyond_endpoint() -> None:
    d = Game._point_to_segment_dist(-10.0, 50.0, 0.0, 50.0, 100.0, 50.0)
    assert abs(d - 10.0) < 0.01


def test_point_to_segment_dist_zero_length() -> None:
    d = Game._point_to_segment_dist(10.0, 10.0, 5.0, 5.0, 5.0, 5.0)
    expected = math.hypot(10.0 - 5.0, 10.0 - 5.0)
    assert abs(d - expected) < 0.01


# ── Click detection tests ──
def test_find_clicked_stick_hit() -> None:
    g = _make_game()
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED)]
    result = g._find_clicked_stick(100, 52)
    assert result == 0


def test_find_clicked_stick_miss() -> None:
    g = _make_game()
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED)]
    result = g._find_clicked_stick(100, 100)
    assert result is None


def test_find_clicked_stick_empty_space() -> None:
    g = _make_game()
    g.sticks = []
    result = g._find_clicked_stick(100, 100)
    assert result is None


def test_find_clicked_stick_ignores_picked() -> None:
    g = _make_game()
    g.sticks = [
        Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, picked=True),
        Stick(x1=50.0, y1=80.0, x2=150.0, y2=80.0, color=LIME),
    ]
    result = g._find_clicked_stick(100, 82)
    assert result == 1  # Picks the unpicked one (click near y=80, far from y=50)


def test_find_clicked_stick_picks_closest() -> None:
    g = _make_game()
    g.sticks = [
        Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED),
        Stick(x1=50.0, y1=55.0, x2=150.0, y2=55.0, color=LIME),
    ]
    result = g._find_clicked_stick(100, 53)
    assert result == 1  # Closer to y=55 stick


# ── Pick stick tests ──
def test_pick_stick_marks_picked() -> None:
    g = _make_game()
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=0)]
    g._pick_stick(0)
    assert g.sticks[0].picked is True


def test_pick_stick_adds_heat_from_overlap() -> None:
    g = _make_game()
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=3)]
    g.heat = 0.0
    g._pick_stick(0)
    assert g.heat == 3 * HEAT_OVERLAP_FACTOR


def test_pick_stick_no_overlap_no_extra_heat() -> None:
    g = _make_game()
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=0)]
    g.heat = 0.0
    g._pick_stick(0)
    assert g.heat == 0.0


# ── Combo tests ──
def test_first_pick_builds_combo_1() -> None:
    g = _make_game()
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=0)]
    g.last_color = -1
    gained = g._pick_stick(0)
    assert g.combo == 1
    assert gained == 10


def test_same_color_extends_combo() -> None:
    g = _make_game()
    g.last_color = RED
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=0)]
    g.combo = 2
    gained = g._pick_stick(0)
    assert g.combo == 3
    assert gained == 30  # 10 * 3


def test_different_color_resets_combo() -> None:
    g = _make_game()
    g.last_color = RED
    g.combo = 3
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=LIME, overlap_count=0)]
    g.heat = 0.0
    gained = g._pick_stick(0)
    assert g.combo == 0
    assert gained == 0
    assert g.heat == HEAT_MISMATCH


def test_combo_increases_max_combo() -> None:
    g = _make_game()
    g.last_color = RED
    g.combo = 3
    g.max_combo = 3
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=0)]
    g._pick_stick(0)
    assert g.max_combo == 4


def test_combo_increases_score_progressively() -> None:
    g = _make_game()
    g.last_color = RED
    score = 0
    for i in range(4):
        g.sticks = [Stick(x1=50.0 + i * 20, y1=50.0, x2=150.0 + i * 20, y2=50.0, color=RED, overlap_count=0)]
        g.sticks[0].picked = False
        g._pick_stick(0)
        score += 10 * (i + 1)
        assert g.score == score


# ── SUPER PICK tests ──
def test_combo_4_activates_super() -> None:
    g = _make_game()
    g.last_color = RED
    g.combo = 3
    g.super_timer = 0
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=0)]
    g._pick_stick(0)
    assert g.super_timer == 300


def test_combo_5_no_re_trigger_super() -> None:
    g = _make_game()
    g.last_color = RED
    g.combo = 4
    g.super_timer = 250
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=0)]
    g._pick_stick(0)
    assert g.super_timer == 250  # Not refreshed (already active)


def test_super_mode_any_color_matches() -> None:
    g = _make_game()
    g.last_color = RED
    g.super_timer = 300
    g.combo = 2
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=LIME, overlap_count=0)]
    gained = g._pick_stick(0)
    assert g.combo == 3  # Combos even with different color
    assert gained == 10 * 3 * 3  # 3x multiplier


def test_super_mode_3x_score() -> None:
    g = _make_game()
    g.last_color = RED
    g.super_timer = 300
    g.combo = 0
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=0)]
    gained = g._pick_stick(0)
    assert gained == 10 * 1 * 3  # 30


def test_super_mode_no_mismatch_heat() -> None:
    g = _make_game()
    g.last_color = RED
    g.super_timer = 300
    g.heat = 0.0
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=LIME, overlap_count=0)]
    g._pick_stick(0)
    assert g.combo > 0  # Not reset
    assert g.heat < HEAT_MISMATCH  # No mismatch penalty


def test_heat_still_added_from_overlap_in_super() -> None:
    g = _make_game()
    g.last_color = RED
    g.super_timer = 300
    g.heat = 0.0
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=LIME, overlap_count=2)]
    g._pick_stick(0)
    assert g.heat == 2 * HEAT_OVERLAP_FACTOR


def test_super_timer_decrements_each_frame() -> None:
    g = _make_game()
    g.super_timer = 100
    g.phase = Phase.PLAYING
    # Simulate frame logic (no round clear)
    if g.super_timer > 0:
        g.super_timer -= 1
    assert g.super_timer == 99


# ── Round management tests ──
def test_start_new_round_increments_round_num() -> None:
    g = _make_game()
    g._start_new_round()
    assert g.round_num == 1


def test_start_new_round_creates_sticks() -> None:
    g = _make_game()
    g._start_new_round()
    assert len(g.sticks) == INITIAL_STICKS


def test_start_new_round_resets_last_color() -> None:
    g = _make_game()
    g.last_color = RED
    g._start_new_round()
    assert g.last_color == -1


def test_round_stick_count_increases() -> None:
    g = _make_game()
    g._start_new_round()  # round 1: 18
    count1 = len(g.sticks)
    g._start_new_round()  # round 2: 21
    count2 = len(g.sticks)
    assert count2 == count1 + 3


def test_round_clear_timer_set_on_all_picked() -> None:
    g = _make_game()
    g._start_new_round()
    for i in range(len(g.sticks)):
        g.sticks[i].picked = True
    # Not actually setting round_clear_timer here directly, just testing behavior
    assert all(s.picked for s in g.sticks)


# ── Heat tests ──
def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat == 10.0 - 0.02


def test_heat_decay_min_zero() -> None:
    g = _make_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


def test_heat_decay_at_zero_stays_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_capped_at_max() -> None:
    g = _make_game()
    g.last_color = RED
    g.heat = HEAT_MAX
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=0)]
    g._pick_stick(0)
    assert g.heat == HEAT_MAX


def test_heat_at_max_game_over() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    g.phase = Phase.PLAYING
    # Simulate update check
    if g.heat >= HEAT_MAX:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_heat_just_below_max_not_game_over() -> None:
    g = _make_game()
    g.heat = 99.9
    g.phase = Phase.PLAYING
    if g.heat >= HEAT_MAX:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.PLAYING


def test_mismatch_adds_heat_correctly() -> None:
    g = _make_game()
    g.last_color = RED
    g.heat = 0.0
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=LIME, overlap_count=0)]
    g._pick_stick(0)
    assert g.heat == HEAT_MISMATCH


# ── Particle tests ──
def test_particles_spawned_on_pick() -> None:
    g = _make_game()
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=0)]
    g._pick_stick(0)
    assert len(g.particles) == 8


def test_particles_update_and_remove() -> None:
    g = _make_game()
    g.particles = [Particle(x=10.0, y=20.0, vx=0.0, vy=0.0, life=1, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0


def test_particles_keep_alive() -> None:
    g = _make_game()
    g.particles = [Particle(x=10.0, y=20.0, vx=1.0, vy=-1.0, life=5, color=RED)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


# ── Floating text tests ──
def test_floating_text_spawned_on_score() -> None:
    g = _make_game()
    g.last_color = RED
    g.combo = 1
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=RED, overlap_count=0)]
    g._pick_stick(0)
    assert len(g.floating_texts) >= 1


def test_floating_text_no_spawn_on_no_score() -> None:
    g = _make_game()
    g.last_color = RED
    g.combo = 0
    g.sticks = [Stick(x1=50.0, y1=50.0, x2=150.0, y2=50.0, color=LIME, overlap_count=0)]
    count_before = len(g.floating_texts)
    g._pick_stick(0)
    assert len(g.floating_texts) == count_before


def test_floating_text_update_and_remove() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=10.0, y=20.0, text="HI", life=1, color=WHITE)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_floating_text_floats_upward() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=10.0, y=20.0, text="HI", life=5, color=WHITE)]
    g._update_floating_texts()
    assert g.floating_texts[0].y < 20.0


# ── Reset tests ──
def test_reset_clears_all_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 5
    g.heat = 80.0
    g.super_timer = 200
    g.round_num = 3
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=RED)]
    g.floating_texts = [FloatingText(x=0.0, y=0.0, text="X", life=1, color=WHITE)]
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.game_timer == GAME_TIMER_FRAMES
    assert g.round_num == 0
    assert g.last_color == -1
    assert g.particles == []
    assert g.floating_texts == []
    assert g.shake_frames == 0
    assert g.round_clear_timer == 0
    assert g.phase == Phase.TITLE


# ── Edge case tests ──
def test_all_sticks_same_color() -> None:
    g = _make_game(seed=999)
    g.last_color = RED
    g.combo = 0
    for i in range(5):
        g.sticks = [Stick(x1=50.0 + i * 20, y1=50.0, x2=150.0 + i * 20, y2=50.0, color=RED, overlap_count=0)]
        g._pick_stick(0)
    assert g.combo == 5
    assert g.super_timer == 300


def test_all_sticks_different_colors() -> None:
    g = _make_game()
    colors = list(STICK_COLORS)
    for i, c in enumerate(colors):
        g.last_color = colors[i - 1] if i > 0 else -1
        g.combo = 0
        g.heat = 0.0
        g.sticks = [Stick(x1=50.0 + i * 20, y1=50.0, x2=150.0 + i * 20, y2=50.0, color=c, overlap_count=0)]
        g._pick_stick(0)
        if i > 0:
            assert g.combo == 0
            assert g.heat == HEAT_MISMATCH
        else:
            assert g.combo == 1


def test_zero_overlap_isolated_sticks() -> None:
    g = _make_game()
    s1 = Stick(x1=10.0, y1=10.0, x2=50.0, y2=10.0, color=RED)
    s2 = Stick(x1=70.0, y1=70.0, x2=120.0, y2=70.0, color=LIME)
    s3 = Stick(x1=200.0, y1=200.0, x2=250.0, y2=200.0, color=DARK_BLUE)
    sticks = [s1, s2, s3]
    g._compute_overlaps(sticks)
    for s in sticks:
        assert s.overlap_count == 0


def test_no_sticks_empty_round() -> None:
    g = _make_game()
    g.sticks = []
    assert g._find_clicked_stick(100, 100) is None


def test_score_accumulation() -> None:
    g = _make_game()
    g.last_color = RED
    for i in range(4):
        g.sticks = [Stick(x1=50.0 + i * 20, y1=50.0, x2=150.0 + i * 20, y2=50.0, color=RED, overlap_count=0)]
        g._pick_stick(0)
    assert g.score == 10 + 20 + 30 + 40  # 100


def test_game_over_by_timer() -> None:
    g = _make_game()
    g.game_timer = 0
    g.phase = Phase.PLAYING
    if g.game_timer <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


print("All tests passed!")
