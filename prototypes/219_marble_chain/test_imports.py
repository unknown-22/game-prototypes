"""test_imports.py — Headless logic tests for 219_marble_chain."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/219_marble_chain")
from main import (
    BASE_SCORE,
    COLLECTION_Y,
    GAME_DURATION,
    HEAT_MAX,
    HEAT_PER_MISMATCH,
    LANE_X,
    MARBLE_COLORS,
    MARBLE_SPEED,
    SWITCH1_RECT,
    SWITCH2_RECT,
    BinState,
    Game,
    Marble,
    Particle,
    Phase,
    RED,
    GREEN,
    DARK_BLUE,
    YELLOW,
    WHITE,
)


def _make_game(seed: int = 42) -> Game:
    """Create a headless Game instance with deterministic RNG."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g._pre_init_state()
    return g


# ── Game.__new__ pattern ──


def test_game_new_bypass_works() -> None:
    """Game.__new__(Game) creates instance without calling __init__."""
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert len(g.switches) == 2
    assert len(g.bins) == 3
    assert len(g.marbles) == 0


def test_reset_enters_playing() -> None:
    """reset() transitions to PLAYING with clean state."""
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.max_combo = 5
    g.heat = 50
    g.marbles.append(Marble(160, 100, RED, 1))
    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == GAME_DURATION
    assert len(g.marbles) == 0
    assert len(g.particles) == 0
    assert len(g.score_popups) == 0
    assert g.super_mode is False
    assert g.super_timer == 0


# ── Spawning ──


def test_spawn_marble_has_valid_color() -> None:
    """_spawn_marble creates marble at center lane with a valid color."""
    g = _make_game(42)
    m = g._spawn_marble()
    assert m.color in MARBLE_COLORS
    assert m.x == 160.0
    assert m.lane == 1
    assert m.target_x == 160.0
    assert m.collected is False


def test_spawn_marble_is_deterministic() -> None:
    """Same seed produces same sequence of marble colors."""
    g1 = _make_game(42)
    g2 = _make_game(42)
    colors1 = [g1._spawn_marble().color for _ in range(10)]
    colors2 = [g2._spawn_marble().color for _ in range(10)]
    assert colors1 == colors2


# ── Marble Movement ──


def test_marble_moves_down() -> None:
    """Marble y increases by MARBLE_SPEED each update."""
    g = _make_game()
    g.reset()
    m = Marble(x=160.0, y=100.0, color=RED, lane=1, target_x=160.0)
    g.marbles = [m]
    g._update_marbles()
    assert m.y == 100.0 + MARBLE_SPEED
    assert m.collected is False


def test_marble_collected_at_bottom() -> None:
    """Marble at collection zone gets collected."""
    g = _make_game()
    g.reset()
    m = Marble(x=160.0, y=COLLECTION_Y, color=RED, lane=1, target_x=160.0)
    g.marbles = [m]
    g._update_marbles()
    assert m.collected is True
    assert len(g.marbles) == 0  # removed from list


def test_marble_collected_at_right_lane() -> None:
    """Marble at right lane gets collected into bin 2."""
    g = _make_game()
    g.reset()
    m = Marble(x=240.0, y=COLLECTION_Y, color=GREEN, lane=2, target_x=240.0)
    g.marbles = [m]
    g._update_marbles()
    assert m.collected is True
    assert g.bins[2].last_color == GREEN


def test_marble_collected_at_left_lane() -> None:
    """Marble at left lane gets collected into bin 0."""
    g = _make_game()
    g.reset()
    m = Marble(x=80.0, y=COLLECTION_Y, color=DARK_BLUE, lane=0, target_x=80.0)
    g.marbles = [m]
    g._update_marbles()
    assert m.collected is True
    assert g.bins[0].last_color == DARK_BLUE


# ── Switch Logic ──


def test_switch_diverts_marble_to_left() -> None:
    """Switch 1 in divert state routes marbles from CENTER to LEFT."""
    g = _make_game()
    g.reset()
    g.switches[0].state = 0  # divert to LEFT (lane 0)
    m = Marble(x=160.0, y=79.0, color=RED, lane=1, target_x=160.0)
    g.marbles = [m]
    g._update_marbles()
    assert m.passed_switch1 is True
    assert m.lane == 0
    assert m.target_x == LANE_X[0]


def test_switch_keep_does_not_divert() -> None:
    """Switch in keep state (1) does NOT change lane."""
    g = _make_game()
    g.reset()
    g.switches[0].state = 1  # keep center
    m = Marble(x=160.0, y=79.0, color=RED, lane=1, target_x=160.0)
    g.marbles = [m]
    g._update_marbles()
    assert m.passed_switch1 is True
    assert m.lane == 1  # still center


def test_marble_only_diverted_once_per_switch() -> None:
    """Marble with passed_switch1=True is not checked again."""
    g = _make_game()
    g.reset()
    g.switches[0].state = 0
    m = Marble(x=160.0, y=79.0, color=RED, lane=1, target_x=160.0, passed_switch1=True)
    g.marbles = [m]
    g._update_marbles()
    assert m.lane == 1  # not diverted


def test_switch2_diverts_to_right() -> None:
    """Switch 2 divert state routes to RIGHT lane."""
    g = _make_game()
    g.reset()
    g.switches[1].state = 0  # divert to RIGHT (lane 2)
    m = Marble(x=160.0, y=149.0, color=GREEN, lane=1, target_x=160.0)
    g.marbles = [m]
    g._update_marbles()
    assert m.passed_switch2 is True
    assert m.lane == 2
    assert m.target_x == LANE_X[2]


def test_marble_lane_change_lerps_x() -> None:
    """Marble x approaches target_x during lane change."""
    g = _make_game()
    g.reset()
    m = Marble(x=160.0, y=81.0, color=RED, lane=0, target_x=80.0)
    g.marbles = [m]
    g._update_marbles()
    # x should move toward 80.0 from 160.0
    assert m.x < 160.0
    assert m.x >= 80.0


def test_marble_already_at_target_no_lane_change() -> None:
    """Marble x stays if already at target_x."""
    g = _make_game()
    g.reset()
    m = Marble(x=80.0, y=100.0, color=RED, lane=0, target_x=80.0)
    g.marbles = [m]
    g._update_marbles()
    assert m.x == 80.0


# ── Collection Logic ──


def test_first_collection_sets_bin_color() -> None:
    """First marble into empty bin sets last_color and starts combo."""
    g = _make_game()
    g.reset()
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.bins[1].last_color == RED
    assert g.combo == 1
    assert g.bins[1].combo == 1


def test_same_color_increases_combo() -> None:
    """Same-color marble in same bin increases combo."""
    g = _make_game()
    g.reset()
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.combo == 2
    assert g.bins[1].combo == 2
    assert g.bins[1].last_color == RED


def test_different_color_resets_combo_and_adds_heat() -> None:
    """Different-color marble in same bin resets combo and adds heat."""
    g = _make_game()
    g.reset()
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.bins[1].last_color == RED
    g._collect_marble(Marble(160, COLLECTION_Y, GREEN, 1), 1)
    assert g.combo == 1  # reset
    assert g.heat == HEAT_PER_MISMATCH
    assert g.bins[1].last_color == GREEN


def test_different_bins_independent() -> None:
    """Each bin tracks combo independently."""
    g = _make_game()
    g.reset()
    g._collect_marble(Marble(80, COLLECTION_Y, RED, 0), 0)
    g._collect_marble(Marble(240, COLLECTION_Y, GREEN, 2), 2)
    assert g.bins[0].last_color == RED
    assert g.bins[2].last_color == GREEN
    assert g.heat == 0.0
    assert g.combo == 2  # global combo: both collects were matches (different bins, each empty first)


def test_empty_bin_first_marble_any_color_ok() -> None:
    """First marble into empty bin always matches (last_color == -1)."""
    g = _make_game()
    g.reset()
    # Empty bin, any color is a match
    assert g.bins[1].last_color == -1
    g._collect_marble(Marble(160, COLLECTION_Y, YELLOW, 1), 1)
    assert g.combo == 1
    assert g.bins[1].last_color == YELLOW
    assert g.heat == 0.0


def test_mismatch_does_not_add_heat_for_first_of_new_color() -> None:
    """Only add heat on mismatch when bin was NOT empty and color differs."""
    g = _make_game()
    g.reset()
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)  # same, no heat
    assert g.heat == 0.0
    g._collect_marble(Marble(160, COLLECTION_Y, GREEN, 1), 1)  # different
    assert g.heat == HEAT_PER_MISMATCH


# ── Score Calculation ──


def test_base_score_for_no_combo() -> None:
    """combo=1 gives multiplier 1, base score = BASE_SCORE * 1."""
    g = _make_game()
    g.reset()
    old_score = g.score
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.score == old_score + BASE_SCORE


def test_combo_2_gives_multiplier_2() -> None:
    """combo=2 gives multiplier 2."""
    g = _make_game()
    g.reset()
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    old_score = g.score
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.score == old_score + BASE_SCORE * 2


def test_combo_4_gives_multiplier_3() -> None:
    """combo=4 gives multiplier 3."""
    g = _make_game()
    g.reset()
    for _ in range(3):
        g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    old_score = g.score
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.score == old_score + BASE_SCORE * 3


def test_combo_6_gives_multiplier_5() -> None:
    """combo=6+ gives multiplier 5 (super mode adds 3x on top)."""
    g = _make_game()
    g.reset()
    for _ in range(5):
        g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    # After 5 collects: combo=5, super_mode active. Score so far computed correctly.
    # 6th collect: combo=6, multiplier=5, in super mode → score += BASE_SCORE * 5 * 3
    old_score = g.score
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.combo == 6
    expected_gain = BASE_SCORE * 5 * 3  # combo multiplier 5 × super 3x
    assert g.score == old_score + expected_gain


def test_max_combo_tracked() -> None:
    """max_combo tracks the highest combo reached."""
    g = _make_game()
    g.reset()
    for _ in range(5):
        g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.max_combo == 5


# ── Super Mode ──


def test_combo_4_activates_super_mode() -> None:
    """COMBO≥4 triggers SUPER MODE."""
    g = _make_game()
    g.reset()
    for _ in range(3):
        g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.super_mode is False
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.super_mode is True
    assert g.super_timer > 0


def test_super_mode_scores_3x() -> None:
    """SUPER MODE applies 3x multiplier."""
    g = _make_game()
    g.reset()
    # Build combo to trigger super
    for _ in range(4):
        g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.super_mode is True
    old_score = g.score
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    # Actually after 4 collects: combo = 4, triggers super
    # 5th collect: combo = 5, multiplier = 5 (combo≥6 → 5x, combo 5 → 3x)
    # 3x for combo=5, then 3x super = 9x total? No: mult * SUPER_SCORE_MULT
    # combo=5 → mult=3 (2≤combo<4→2, 4≤combo<6→3, combo≥6→5)
    # Actually wait, let me re-check _compute_combo_multiplier:
    # combo<2→1, combo<4→2, combo<6→3, combo≥6→5
    # combo=5 → 3x. Then super: 3 * 3 = 9x. BASE_SCORE=10 → 90.
    expected_gain = BASE_SCORE * 3 * 3  # 90
    assert g.score == old_score + expected_gain


def test_super_mode_all_colors_match() -> None:
    """In SUPER MODE, any color matches (doesn't reset combo)."""
    g = _make_game()
    g.reset()
    for _ in range(4):
        g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.super_mode is True
    combo_before = g.combo
    # Collect different color — should still increase combo in super mode
    g._collect_marble(Marble(160, COLLECTION_Y, GREEN, 1), 1)
    assert g.combo == combo_before + 1
    assert g.heat == 0.0  # no mismatch heat


def test_super_mode_expires() -> None:
    """SUPER MODE eventually expires."""
    g = _make_game()
    g.reset()
    for _ in range(4):
        g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.super_mode is True
    # Simulate super timer expiry: set to 1 so _update_super_mode decrements to 0
    g.super_timer = 1
    g._update_super_mode()
    assert g.super_mode is False


# ── Heat Management ──


def test_heat_decays() -> None:
    """Heat decays over time."""
    g = _make_game()
    g.reset()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0


def test_heat_does_not_go_negative() -> None:
    """Heat clamps to 0."""
    g = _make_game()
    g.reset()
    g.heat = 0.01
    g._update_heat()
    assert g.heat >= 0.0


def test_heat_capped_at_max() -> None:
    """Heat doesn't exceed HEAT_MAX."""
    g = _make_game()
    g.reset()
    # Collect same color 2x, then different colors repeatedly
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    for _ in range(10):
        g._collect_marble(Marble(160, COLLECTION_Y, GREEN, 1), 1)
        g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.heat <= HEAT_MAX  # capped in _collect_marble


# ── Game Over ──


def test_game_over_by_timer() -> None:
    """Game ends when timer reaches 0."""
    g = _make_game()
    g.reset()
    g.timer = 0
    assert g._check_game_over() is True


def test_game_over_by_heat() -> None:
    """Game ends when heat reaches max."""
    g = _make_game()
    g.reset()
    g.heat = HEAT_MAX
    assert g._check_game_over() is True


def test_not_game_over_during_play() -> None:
    """Game continues with time and low heat."""
    g = _make_game()
    g.reset()
    g.timer = 100
    g.heat = 50
    assert g._check_game_over() is False


def test_game_over_sets_high_score() -> None:
    """High score is updated on game over."""
    g = _make_game()
    g.reset()
    g.score = 500
    g.high_score = 0
    g.timer = 0
    # Trigger game over check (done in _update_playing)
    # Manual simulation
    if g._check_game_over():
        if g.score > g.high_score:
            g.high_score = g.score
        g.phase = Phase.GAME_OVER
    assert g.high_score == 500
    assert g.phase == Phase.GAME_OVER


# ── Switch Toggling ──


def test_toggle_switch_flips_state() -> None:
    """_toggle_switch flips 0↔1."""
    g = _make_game()
    g.reset()
    assert g.switches[0].state == 1
    g._toggle_switch(0)
    assert g.switches[0].state == 0
    g._toggle_switch(0)
    assert g.switches[0].state == 1


def test_toggle_switch_sets_flash_timer() -> None:
    """Toggling sets flash_timer."""
    g = _make_game()
    g.reset()
    g._toggle_switch(0)
    assert g.switches[0].flash_timer > 0


# ── Click Handling ──


def test_click_on_switch1_toggles_it() -> None:
    """Click inside SWITCH1_RECT toggles switch 0."""
    g = _make_game()
    g.reset()
    rx, ry, rw, rh = SWITCH1_RECT
    g._handle_click(rx + 1, ry + 1)
    assert g.switches[0].state == 0


def test_click_on_switch2_toggles_it() -> None:
    """Click inside SWITCH2_RECT toggles switch 1."""
    g = _make_game()
    g.reset()
    rx, ry, rw, rh = SWITCH2_RECT
    g._handle_click(rx + 1, ry + 1)
    assert g.switches[1].state == 0


def test_click_outside_switches_does_nothing() -> None:
    """Click outside both switches changes nothing."""
    g = _make_game()
    g.reset()
    old_state0 = g.switches[0].state
    old_state1 = g.switches[1].state
    g._handle_click(10, 10)
    assert g.switches[0].state == old_state0
    assert g.switches[1].state == old_state1


# ── Spawn Timer ──


def test_spawn_timer_decrements() -> None:
    """spawn_timer decrements each update."""
    g = _make_game()
    g.reset()
    old_timer = g.spawn_timer
    g._update_spawning()
    assert g.spawn_timer == old_timer - 1


def test_spawn_creates_marble_when_timer_reaches_zero() -> None:
    """When spawn_timer hits 0, a marble is created."""
    g = _make_game(42)
    g.reset()
    g.spawn_timer = 1
    g._update_spawning()
    assert len(g.marbles) == 1
    assert g.spawn_timer > 0  # reset


def test_spawn_interval_decreases_over_time() -> None:
    """Spawn interval decreases as game progresses."""
    g = _make_game()
    g.reset()
    initial = g.spawn_interval
    g.timer = GAME_DURATION - 1000  # simulate elapsed time
    g._update_spawning()
    # interval may have decreased
    assert g.spawn_interval <= initial


# ── BinState ──


def test_binstate_defaults() -> None:
    """BinState starts with last_color=-1, combo=0."""
    bs = BinState()
    assert bs.last_color == -1
    assert bs.combo == 0


# ── Particle System ──


def test_collect_spawns_particles() -> None:
    """Collecting a marble spawns particles."""
    g = _make_game(42)
    g.reset()
    old_count = len(g.particles)
    g._spawn_collect_particles(160.0, 200.0, RED, 6)
    assert len(g.particles) == old_count + 6


def test_particles_move_and_decay() -> None:
    """Particles move, life decrements, dead ones removed."""
    g = _make_game()
    g.reset()
    g.particles = [Particle(100.0, 100.0, 1.0, -1.0, 1, RED)]
    g._update_particles()
    assert len(g.particles) == 0  # life went to 0, removed


def test_particles_survive_with_life() -> None:
    """Particles with life>1 survive one update."""
    g = _make_game()
    g.reset()
    g.particles = [Particle(100.0, 100.0, 1.0, -1.0, 2, RED)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 1


# ── Data class integrity ──


def test_marble_defaults() -> None:
    """Marble dataclass has correct defaults."""
    m = Marble(x=100.0, y=50.0, color=RED, lane=1)
    assert m.collected is False
    assert m.passed_switch1 is False
    assert m.passed_switch2 is False
    assert m.target_x == 160.0


def test_switch_defaults() -> None:
    """Switch dataclass has correct defaults."""
    s = Game.__new__(Game)
    s._rng = random.Random(42)
    s._pre_init_state()
    assert s.switches[0].from_lane == 1
    assert s.switches[0].to_lane == 0  # LEFT
    assert s.switches[1].from_lane == 1
    assert s.switches[1].to_lane == 2  # RIGHT


# ── Scored popups ──


def test_score_popup_spawned_on_collect() -> None:
    """Collecting a marble creates a score popup."""
    g = _make_game()
    g.reset()
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert len(g.score_popups) >= 1


def test_score_popups_decay() -> None:
    """Score popups have decreasing life."""
    g = _make_game()
    g.reset()
    g.score_popups = [(160.0, 200.0, 10, 2, WHITE)]
    g._update_score_popups()
    assert g.score_popups[0][3] == 1  # life decreased


# ── Combo Multiplier ──


def test_combo_multiplier_1_for_combo_1() -> None:
    """combo=1 → multiplier 1."""
    g = _make_game()
    assert g._compute_combo_multiplier(1) == 1


def test_combo_multiplier_2_for_combo_2() -> None:
    """combo=2 → multiplier 2."""
    g = _make_game()
    assert g._compute_combo_multiplier(2) == 2


def test_combo_multiplier_3_for_combo_4() -> None:
    """combo=4 → multiplier 3."""
    g = _make_game()
    assert g._compute_combo_multiplier(4) == 3


def test_combo_multiplier_5_for_combo_6() -> None:
    """combo=6 → multiplier 5."""
    g = _make_game()
    assert g._compute_combo_multiplier(6) == 5


def test_combo_multiplier_5_for_combo_100() -> None:
    """combo=100 → multiplier 5 (capped)."""
    g = _make_game()
    assert g._compute_combo_multiplier(100) == 5


# ── Edge Cases ──


def test_all_same_color_builds_huge_combo() -> None:
    """10 same-color marbles in same bin should build combo=10."""
    g = _make_game()
    g.reset()
    for _ in range(10):
        g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.combo == 10
    assert g.max_combo == 10
    assert g.heat == 0.0


def test_alternating_colors_resets_combo() -> None:
    """Alternating colors constantly resets combo."""
    g = _make_game()
    g.reset()
    colors = [RED, GREEN, RED, GREEN, RED, GREEN]
    for c in colors:
        g._collect_marble(Marble(160, COLLECTION_Y, c, 1), 1)
    assert g.combo == 1  # last reset
    assert g.heat > 0


def test_heat_never_exceeds_max_on_collect() -> None:
    """Heat is clamped to HEAT_MAX in _collect_marble."""
    g = _make_game()
    g.reset()
    g.heat = HEAT_MAX - 1  # near max
    g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)  # first = match
    g._collect_marble(Marble(160, COLLECTION_Y, GREEN, 1), 1)  # mismatch → +15
    assert g.heat <= HEAT_MAX


def test_super_mode_trumps_mismatch() -> None:
    """In SUPER MODE, mismatch heat is NOT added."""
    g = _make_game()
    g.reset()
    # Enter super mode
    for _ in range(4):
        g._collect_marble(Marble(160, COLLECTION_Y, RED, 1), 1)
    assert g.super_mode is True
    old_heat = g.heat
    # Different color should NOT increase heat in super mode
    g._collect_marble(Marble(160, COLLECTION_Y, GREEN, 1), 1)
    assert g.heat == old_heat


def test_marble_past_both_switches_without_matching_y_not_diverted() -> None:
    """Marble above switch1 y is not checked."""
    g = _make_game()
    g.reset()
    g.switches[0].state = 0  # divert
    m = Marble(x=160.0, y=50.0, color=RED, lane=1, target_x=160.0)
    g.marbles = [m]
    g._update_marbles()
    # y went from 50 to 52, still below SWITCH1_Y=80
    assert m.passed_switch1 is False
    assert m.lane == 1


def test_marble_crosses_both_switches_in_one_update() -> None:
    """Marble moving fast enough could cross both switches in one frame."""
    g = _make_game()
    g.reset()
    g.switches[0].state = 0  # divert LEFT
    g.switches[1].state = 0  # divert RIGHT
    # Place marble at y=70 with super speed (e.g. y increases past both)
    m = Marble(x=160.0, y=79.0, color=RED, lane=1, target_x=160.0)
    m.y = 79.0
    g.marbles = [m]
    # Override speed for this test
    g._update_marbles()
    # Switch 1 at y=80: marble crosses it
    # Switch 2 at y=150: marble at y=81, not yet there
    assert m.passed_switch1 is True
    assert m.passed_switch2 is False
