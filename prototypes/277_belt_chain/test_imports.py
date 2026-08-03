"""test_imports.py — Headless logic tests for BELT CHAIN."""
import sys
import random

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/277_belt_chain")
from main import (
    Game,
    Phase,
    BeltItem,
    Particle,
    FloatingText,
    GAME_TIME,
    SUPER_DURATION,
    HEAT_MAX,
    SUPER_COMBO_THRESHOLD,
    SUPER_SCORE_MULTIPLIER,
    HEAT_MISMATCH,
    MAX_ITEMS,
    SPAWN_INTERVAL_BASE,
    SPAWN_INTERVAL_MIN,
    SPAWN_MARGIN,
    PROCESS_X,
    ITEM_SIZE,
    INITIAL_ITEM_SPEED,
    COLORS,
    RED,
    LIME,
    DARK_BLUE,
    YELLOW,
    WHITE,
    SCREEN_W,
    SCREEN_H,
    LANE_Y,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.PLAYING
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.game_timer = GAME_TIME
    g.super_timer = 0
    g.frame = 0
    g.machine_color = COLORS[0]
    g.machine_index = 0
    g.items = []
    g.particles = []
    g.floating_texts = []
    g.spawn_timer = 0
    g.processed_count = 0
    g.shake_frames = 0
    g.belt_offset = 0.0
    g.belt_dot_timer = 0
    g.item_speed = INITIAL_ITEM_SPEED
    g._rng = random.Random(42)
    return g


# ═══════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════


class TestDataClasses:
    def test_belt_item_defaults(self):
        item = BeltItem(lane=0, x=10.0, color=RED)
        assert item.lane == 0
        assert item.x == 10.0
        assert item.color == RED
        assert item.processed is False
        assert item.alive is True

    def test_belt_item_processed(self):
        item = BeltItem(lane=2, x=200.0, color=LIME, processed=True)
        assert item.processed is True

    def test_particle(self):
        p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=20, color=RED)
        assert p.life == 20
        assert p.color == RED

    def test_floating_text(self):
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=WHITE, life=30)
        assert ft.text == "+10"
        assert ft.life == 30


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════


class TestConstants:
    def test_colors(self):
        assert COLORS == [RED, LIME, DARK_BLUE, YELLOW]
        assert len(COLORS) == 4

    def test_super_threshold(self):
        assert SUPER_COMBO_THRESHOLD == 4

    def test_super_duration(self):
        assert SUPER_DURATION == 300

    def test_super_score_multiplier(self):
        assert SUPER_SCORE_MULTIPLIER == 3

    def test_game_duration(self):
        assert GAME_TIME == 3600  # 60 * 60

    def test_heat_max(self):
        assert HEAT_MAX == 100.0

    def test_heat_mismatch(self):
        assert HEAT_MISMATCH == 15.0

    def test_max_items(self):
        assert MAX_ITEMS == 15

    def test_lane_count(self):
        assert len(LANE_Y) == 3


# ═══════════════════════════════════════════════════════════════
# Item processing
# ═══════════════════════════════════════════════════════════════


class TestProcessItem:
    def test_match_same_color(self):
        g = _make_game()
        g.machine_color = RED
        g.combo = 1
        item = BeltItem(lane=0, x=PROCESS_X, color=RED)
        score_g, heat_g, is_match = g._process_item(item)
        assert is_match is True
        assert score_g > 0
        assert heat_g == 0.0
        assert item.processed is True

    def test_match_first_item_combo_zero(self):
        g = _make_game()
        g.machine_color = RED
        g.combo = 0
        item = BeltItem(lane=0, x=PROCESS_X, color=RED)
        score_g, heat_g, is_match = g._process_item(item)
        assert is_match is True
        assert score_g == 10
        assert heat_g == 0.0

    def test_mismatch_wrong_color(self):
        g = _make_game()
        g.machine_color = RED
        g.combo = 3
        item = BeltItem(lane=0, x=PROCESS_X, color=LIME)
        score_g, heat_g, is_match = g._process_item(item)
        assert is_match is False
        assert score_g == 0
        assert heat_g == HEAT_MISMATCH
        assert item.processed is True

    def test_super_mode_auto_match(self):
        g = _make_game()
        g.super_timer = SUPER_DURATION
        g.machine_color = RED
        g.combo = 5
        item = BeltItem(lane=0, x=PROCESS_X, color=LIME)
        score_g, heat_g, is_match = g._process_item(item)
        assert is_match is True
        assert score_g == 10 * SUPER_SCORE_MULTIPLIER  # 30
        assert heat_g == 0.0

    def test_super_mode_score_flat(self):
        g = _make_game()
        g.super_timer = SUPER_DURATION
        g.machine_color = RED
        g.combo = 10
        item = BeltItem(lane=0, x=PROCESS_X, color=DARK_BLUE)
        score_g, _, is_match = g._process_item(item)
        assert is_match is True
        # Super score is always 10 * SUPER_SCORE_MULTIPLIER, not based on combo
        assert score_g == 30

    def test_match_score_scales_with_combo(self):
        g = _make_game()
        g.machine_color = RED
        g.combo = 4
        item = BeltItem(lane=0, x=PROCESS_X, color=RED)
        score_g, _, _ = g._process_item(item)
        assert score_g == 40  # 10 * combo(4)

    def test_marks_item_processed(self):
        g = _make_game()
        g.machine_color = RED
        item = BeltItem(lane=0, x=PROCESS_X, color=LIME)
        g._process_item(item)
        assert item.processed is True


# ═══════════════════════════════════════════════════════════════
# Update items
# ═══════════════════════════════════════════════════════════════


class TestUpdateItems:
    def test_items_move_right(self):
        g = _make_game()
        item = BeltItem(lane=0, x=0.0, color=RED)
        g.items = [item]
        g.item_speed = 1.5
        g._update_items()
        assert abs(item.x - 1.5) < 0.001

    def test_items_removed_off_screen(self):
        g = _make_game()
        item = BeltItem(lane=0, x=SCREEN_W + ITEM_SIZE + 1, color=RED)
        g.items = [item]
        g._update_items()
        assert len(g.items) == 0

    def test_processed_item_removed_past_zone(self):
        g = _make_game()
        item = BeltItem(lane=0, x=PROCESS_X + ITEM_SIZE * 3 + 1, color=RED, processed=True)
        g.items = [item]
        g._update_items()
        assert len(g.items) == 0

    def test_processing_increments_processed_count(self):
        g = _make_game()
        g.machine_color = RED
        item = BeltItem(lane=0, x=PROCESS_X, color=RED)
        g.items = [item]
        g._update_items()
        assert g.processed_count == 1
        assert item.processed is True

    def test_processing_updates_score(self):
        g = _make_game()
        g.machine_color = RED
        g.combo = 2
        item = BeltItem(lane=0, x=PROCESS_X, color=RED)
        g.items = [item]
        g._update_items()
        assert g.score > 0

    def test_mismatch_adds_heat(self):
        g = _make_game()
        g.machine_color = RED
        item = BeltItem(lane=0, x=PROCESS_X, color=LIME)
        g.items = [item]
        g._update_items()
        assert g.heat == HEAT_MISMATCH

    def test_mismatch_resets_combo(self):
        g = _make_game()
        g.machine_color = RED
        g.combo = 5
        g.max_combo = 5
        item = BeltItem(lane=0, x=PROCESS_X, color=LIME)
        g.items = [item]
        g._update_items()
        assert g.combo == 0
        assert g.max_combo == 5  # preserved

    def test_multiple_items_processing(self):
        g = _make_game()
        g.machine_color = RED
        items = [
            BeltItem(lane=0, x=PROCESS_X, color=RED),
            BeltItem(lane=1, x=PROCESS_X + 5, color=RED),
            BeltItem(lane=2, x=PROCESS_X - 5, color=RED),
        ]
        g.items = items
        g._update_items()
        assert g.processed_count == 3


# ═══════════════════════════════════════════════════════════════
# Combo system
# ═══════════════════════════════════════════════════════════════


class TestCombo:
    def test_combo_increments_on_match(self):
        g = _make_game()
        g.machine_color = RED
        g.combo = 0
        item = BeltItem(lane=0, x=PROCESS_X, color=RED)
        g.items = [item]
        g._update_items()
        assert g.combo == 1

    def test_max_combo_tracks_peak(self):
        g = _make_game()
        g.machine_color = RED
        g.combo = 0
        for _ in range(5):
            item = BeltItem(lane=0, x=PROCESS_X, color=RED)
            g.items = [item]
            g._update_items()
        assert g.combo == 5
        assert g.max_combo == 5

    def test_max_combo_survives_mismatch(self):
        g = _make_game()
        g.machine_color = RED
        g.combo = 0
        # Build combo
        for _ in range(3):
            item = BeltItem(lane=0, x=PROCESS_X, color=RED)
            g.items = [item]
            g._update_items()
        assert g.max_combo == 3
        # Mismatch
        item = BeltItem(lane=0, x=PROCESS_X, color=LIME)
        g.items = [item]
        g._update_items()
        assert g.combo == 0
        assert g.max_combo == 3

    def test_super_triggers_at_threshold(self):
        g = _make_game()
        g.machine_color = RED
        g.combo = SUPER_COMBO_THRESHOLD - 1  # combo=3
        g.super_timer = 0
        item = BeltItem(lane=0, x=PROCESS_X, color=RED)
        g.items = [item]
        g._update_items()
        assert g.combo == SUPER_COMBO_THRESHOLD  # became 4
        assert g.super_timer == SUPER_DURATION

    def test_super_extends_on_re_threshold(self):
        g = _make_game()
        g.machine_color = RED
        g.combo = SUPER_COMBO_THRESHOLD - 1
        g.super_timer = 100  # some remaining
        item = BeltItem(lane=0, x=PROCESS_X, color=RED)
        g.items = [item]
        g._update_items()
        # Should not re-trigger since already in super, but combo still increments
        assert g.combo == SUPER_COMBO_THRESHOLD


# ═══════════════════════════════════════════════════════════════
# Heat system
# ═══════════════════════════════════════════════════════════════


class TestHeatSystem:
    def test_heat_starts_zero(self):
        g = _make_game()
        assert g.heat == 0.0

    def test_heat_decay_works(self):
        g = _make_game()
        g.heat = 10.0
        g._update_heat()
        assert g.heat < 10.0

    def test_heat_never_goes_negative(self):
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_clamped_to_max(self):
        g = _make_game()
        g.heat = HEAT_MAX + 10
        g._update_heat()
        assert g.heat == HEAT_MAX

    def test_heat_accumulates_on_mismatch(self):
        g = _make_game()
        g.machine_color = RED
        for _ in range(3):
            item = BeltItem(lane=0, x=PROCESS_X, color=LIME)
            g.items = [item]
            g._update_items()
        assert abs(g.heat - 3 * HEAT_MISMATCH) < 0.01

    def test_end_game_at_heat_max(self):
        g = _make_game()
        g.heat = HEAT_MAX
        g.score = 300
        g.best_score = 200
        g._end_game()
        assert g.phase == Phase.GAME_OVER


# ═══════════════════════════════════════════════════════════════
# Super timer
# ═══════════════════════════════════════════════════════════════


class TestSuperTimer:
    def test_super_timer_counts_down(self):
        g = _make_game()
        g.super_timer = 10
        g._update_super_timer()
        assert g.super_timer == 9

    def test_super_timer_stays_at_zero(self):
        g = _make_game()
        g.super_timer = 0
        g._update_super_timer()
        assert g.super_timer == 0

    def test_super_timer_decreases_to_zero(self):
        g = _make_game()
        g.super_timer = 1
        g._update_super_timer()
        assert g.super_timer == 0


# ═══════════════════════════════════════════════════════════════
# Spawning
# ═══════════════════════════════════════════════════════════════


class TestSpawning:
    def test_spawn_item(self):
        g = _make_game()
        item = g._spawn_item()
        assert item is not None
        assert item.lane in (0, 1, 2)
        assert item.color in COLORS
        assert item.x == SPAWN_MARGIN
        assert item.processed is False
        assert item.alive is True

    def test_spawn_item_when_full(self):
        g = _make_game()
        g.items = [BeltItem(lane=0, x=0.0, color=RED) for _ in range(MAX_ITEMS)]
        result = g._spawn_item()
        assert result is None

    def test_spawn_timer_countdown(self):
        g = _make_game()
        g.spawn_timer = 5
        result = False
        for _ in range(5):
            result = g._update_spawn_timer()
        assert result is True

    def test_spawn_timer_not_ready(self):
        g = _make_game()
        g.spawn_timer = 3
        result = g._update_spawn_timer()
        assert result is False
        assert g.spawn_timer == 2

    def test_get_spawn_interval_start(self):
        g = _make_game()
        g.game_timer = GAME_TIME
        interval = g._get_spawn_interval()
        assert interval == SPAWN_INTERVAL_BASE

    def test_get_spawn_interval_decreases(self):
        g = _make_game()
        g.game_timer = GAME_TIME // 2
        interval = g._get_spawn_interval()
        assert interval < SPAWN_INTERVAL_BASE
        assert interval >= SPAWN_INTERVAL_MIN

    def test_get_spawn_interval_minimum(self):
        g = _make_game()
        g.game_timer = 0
        interval = g._get_spawn_interval()
        assert interval == SPAWN_INTERVAL_MIN


# ═══════════════════════════════════════════════════════════════
# Escalation
# ═══════════════════════════════════════════════════════════════


class TestEscalation:
    def test_speed_starts_default(self):
        g = _make_game()
        g.game_timer = GAME_TIME
        g._update_escalation()
        assert g.item_speed == INITIAL_ITEM_SPEED

    def test_speed_near_end(self):
        g = _make_game()
        g.game_timer = 1  # almost done
        g._update_escalation()
        assert g.item_speed > 2.0


# ═══════════════════════════════════════════════════════════════
# Particles
# ═══════════════════════════════════════════════════════════════


class TestParticles:
    def test_update_particles_moves(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=1.0, vy=-1.0, life=10, color=RED)
        g.particles = [p]
        g._update_particles()
        assert abs(p.x - 101.0) < 0.001
        assert abs(p.y - 99.0) < 0.001
        assert abs(p.vy - (-0.9)) < 0.001

    def test_update_particles_gravity(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=10, color=RED)
        g.particles = [p]
        g._update_particles()
        assert abs(p.vy - 0.1) < 0.001

    def test_update_particles_removes_dead(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=RED)
        g.particles = [p]
        g._update_particles()
        assert len(g.particles) == 0

    def test_spawn_match_particles(self):
        g = _make_game()
        item = BeltItem(lane=0, x=PROCESS_X, color=RED)
        assert len(g.particles) == 0
        g._spawn_match_particles(item)
        assert len(g.particles) == 6

    def test_spawn_match_particles_super(self):
        g = _make_game()
        g.super_timer = SUPER_DURATION
        item = BeltItem(lane=0, x=PROCESS_X, color=RED)
        assert len(g.particles) == 0
        g._spawn_match_particles(item)
        assert len(g.particles) == 12

    def test_spawn_mismatch_particles(self):
        g = _make_game()
        item = BeltItem(lane=0, x=PROCESS_X, color=LIME)
        assert len(g.particles) == 0
        g._spawn_mismatch_particles(item)
        assert len(g.particles) == 3

    def test_spawn_super_burst(self):
        g = _make_game()
        assert len(g.particles) == 0
        g._spawn_super_burst()
        assert len(g.particles) == 12


# ═══════════════════════════════════════════════════════════════
# Floating texts
# ═══════════════════════════════════════════════════════════════


class TestFloatingTexts:
    def test_spawn_floating_text(self):
        g = _make_game()
        g._spawn_floating_text(100.0, 50.0, "+10", WHITE, 30)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "+10"
        assert g.floating_texts[0].life == 30

    def test_update_floating_texts_rise(self):
        g = _make_game()
        g._spawn_floating_text(100.0, 50.0, "+10", WHITE, 30)
        g._update_floating_texts()
        assert g.floating_texts[0].y == 49.0
        assert g.floating_texts[0].life == 29

    def test_update_floating_texts_removes_dead(self):
        g = _make_game()
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=WHITE, life=1)
        g.floating_texts = [ft]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


# ═══════════════════════════════════════════════════════════════
# Machine color
# ═══════════════════════════════════════════════════════════════


class TestMachineColor:
    def test_initial_color(self):
        g = _make_game()
        assert g.machine_color == COLORS[0]
        assert g.machine_index == 0

    def test_set_machine_color(self):
        g = _make_game()
        g._set_machine_color(2)
        assert g.machine_color == COLORS[2]
        assert g.machine_index == 2

    def test_set_machine_color_all(self):
        g = _make_game()
        for i in range(4):
            g._set_machine_color(i)
            assert g.machine_color == COLORS[i]
            assert g.machine_index == i


# ═══════════════════════════════════════════════════════════════
# Phase and reset
# ═══════════════════════════════════════════════════════════════


class TestPhases:
    def test_initial_phase(self):
        g = _make_game()
        assert g.phase == Phase.PLAYING

    def test_reset_sets_title(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.reset()
        assert g.phase == Phase.TITLE

    def test_reset_clears_score(self):
        g = _make_game()
        g.score = 999
        g.reset()
        assert g.score == 0

    def test_reset_clears_combo(self):
        g = _make_game()
        g.combo = 5
        g.reset()
        assert g.combo == 0

    def test_reset_clears_max_combo(self):
        g = _make_game()
        g.max_combo = 5
        g.reset()
        assert g.max_combo == 0

    def test_reset_clears_heat(self):
        g = _make_game()
        g.heat = 80.0
        g.reset()
        assert g.heat == 0.0

    def test_reset_clears_items(self):
        g = _make_game()
        g.items = [BeltItem(lane=0, x=100.0, color=RED)]
        g.reset()
        assert len(g.items) == 0

    def test_reset_clears_particles_and_texts(self):
        g = _make_game()
        g.particles = [Particle(0, 0, 0, 0, 1, RED)]
        g.floating_texts = [FloatingText(0, 0, "test", WHITE, 1)]
        g.reset()
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0

    def test_reset_clears_processed_count(self):
        g = _make_game()
        g.processed_count = 42
        g.reset()
        assert g.processed_count == 0

    def test_reset_machine_color(self):
        g = _make_game()
        g.machine_color = COLORS[2]
        g.machine_index = 2
        g.reset()
        assert g.machine_color == COLORS[0]
        assert g.machine_index == 0

    def test_best_score_preserved_across_reset(self):
        g = _make_game()
        g.best_score = 500
        g.reset()
        assert g.best_score == 500

    def test_best_score_updated_on_game_over(self):
        g = _make_game()
        g.score = 700
        g.best_score = 500
        g._end_game()
        assert g.best_score == 700

    def test_best_score_not_lowered(self):
        g = _make_game()
        g.best_score = 500
        g.score = 300
        g._end_game()
        assert g.best_score == 500

    def test_start_game_sets_playing(self):
        g = _make_game()
        g.phase = Phase.TITLE
        g._start_game()
        assert g.phase == Phase.PLAYING
        assert g.game_timer == GAME_TIME


# ═══════════════════════════════════════════════════════════════
# Timer
# ═══════════════════════════════════════════════════════════════


class TestTimer:
    def test_game_timer_starts_full(self):
        g = _make_game()
        assert g.game_timer == GAME_TIME

    def test_end_game_on_timer_zero(self):
        g = _make_game()
        g.game_timer = 0
        g.score = 200
        g.best_score = 100
        g._end_game()
        assert g.phase == Phase.GAME_OVER


# ═══════════════════════════════════════════════════════════════
# Button layout
# ═══════════════════════════════════════════════════════════════


class TestButtonLayout:
    def test_button_positions(self):
        from main import BTN_X, BTN_W, BTN_GAP
        assert len(BTN_X) == 4
        for i in range(3):
            assert BTN_X[i + 1] - BTN_X[i] == BTN_W + BTN_GAP

    def test_buttons_in_screen(self):
        from main import BTN_X, BTN_W, BTN_Y, BTN_H
        for bx in BTN_X:
            assert 0 <= bx
            assert bx + BTN_W <= SCREEN_W
        assert BTN_Y >= 0
        assert BTN_Y + BTN_H <= SCREEN_H
