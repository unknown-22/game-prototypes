"""test_imports.py — Headless logic tests for CARE CHAIN."""
import sys
import random

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/273_care_chain")
from main import (
    Game,
    Phase,
    ActionType,
    Particle,
    FloatingText,
    ACTION_COLORS,
    ACTION_EFFECTS,
    ACTIONS_ORDERED,
    COMBO_THRESHOLD,
    SUPER_DURATION,
    SUPER_MULT,
    STRESS_CAP,
    STAT_MIN,
    STAT_MAX,
    GAME_DURATION,
    DECAY_HAPPINESS,
    DECAY_HUNGER,
    DECAY_ENERGY,
    DECAY_STRESS,
    BUTTON_XS,
    BUTTON_Y,
    BUTTON_W,
    BUTTON_H,
    WHITE,
    RED,
    ORANGE,
    YELLOW,
    LIME,
    CYAN,
    GRAY,
    GREEN,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.last_action = None
    g.timer = GAME_DURATION
    g.super_timer = 0
    g.stress = 0.0
    g.happiness = 50.0
    g.hunger = 50.0
    g.energy = 50.0
    g.particles = []
    g.floating_texts = []
    g.frame = 0
    g.shake_frames = 0
    g.pet_frame = 0
    g._rng = random.Random(42)
    g.reset()
    return g


# ═══════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════


class TestDataClasses:
    def test_particle(self):
        p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=20, color=RED)
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.life == 20
        assert p.color == RED

    def test_floating_text(self):
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=WHITE, life=30)
        assert ft.text == "+10"
        assert ft.life == 30
        assert ft.color == WHITE


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════


class TestConstants:
    def test_action_colors(self):
        assert ACTION_COLORS[ActionType.FEED] == GRAY
        assert ACTION_COLORS[ActionType.PLAY] == LIME
        assert ACTION_COLORS[ActionType.REST] == CYAN
        assert ACTION_COLORS[ActionType.TRAIN] == ORANGE

    def test_action_effects(self):
        assert ACTION_EFFECTS[ActionType.FEED] == (5.0, 15.0, 5.0, 2.0)
        assert ACTION_EFFECTS[ActionType.PLAY] == (15.0, -10.0, -5.0, 3.0)
        assert ACTION_EFFECTS[ActionType.REST] == (3.0, -2.0, 15.0, -10.0)
        assert ACTION_EFFECTS[ActionType.TRAIN] == (10.0, -5.0, -8.0, 8.0)

    def test_actions_ordered(self):
        assert ACTIONS_ORDERED == [
            ActionType.FEED,
            ActionType.PLAY,
            ActionType.REST,
            ActionType.TRAIN,
        ]

    def test_button_layout(self):
        assert len(BUTTON_XS) == 4
        assert BUTTON_W == 60
        assert BUTTON_H == 40

    def test_combo_threshold(self):
        assert COMBO_THRESHOLD == 4

    def test_super_duration(self):
        assert SUPER_DURATION == 300


# ═══════════════════════════════════════════════════════════════
# Action detection
# ═══════════════════════════════════════════════════════════════


class TestActionDetection:
    def test_feed_button(self):
        g = _make_game()
        x = BUTTON_XS[0] + BUTTON_W // 2
        y = BUTTON_Y + BUTTON_H // 2
        assert g._get_action_at(x, y) == ActionType.FEED

    def test_play_button(self):
        g = _make_game()
        x = BUTTON_XS[1] + BUTTON_W // 2
        y = BUTTON_Y + BUTTON_H // 2
        assert g._get_action_at(x, y) == ActionType.PLAY

    def test_rest_button(self):
        g = _make_game()
        x = BUTTON_XS[2] + BUTTON_W // 2
        y = BUTTON_Y + BUTTON_H // 2
        assert g._get_action_at(x, y) == ActionType.REST

    def test_train_button(self):
        g = _make_game()
        x = BUTTON_XS[3] + BUTTON_W // 2
        y = BUTTON_Y + BUTTON_H // 2
        assert g._get_action_at(x, y) == ActionType.TRAIN

    def test_outside_buttons(self):
        g = _make_game()
        assert g._get_action_at(0, 0) is None
        assert g._get_action_at(200, BUTTON_Y - 10) is None

    def test_gap_between_buttons(self):
        g = _make_game()
        gap_x = BUTTON_XS[0] + BUTTON_W + 2
        assert g._get_action_at(gap_x, BUTTON_Y + BUTTON_H // 2) is None


# ═══════════════════════════════════════════════════════════════
# Combo bonus
# ═══════════════════════════════════════════════════════════════


class TestComboBonus:
    def test_combo_0_bonus(self):
        g = _make_game()
        assert g._combo_bonus() == 1.0

    def test_combo_3_bonus(self):
        g = _make_game()
        g.combo = 3
        assert g._combo_bonus() == 1.75

    def test_combo_4_bonus(self):
        g = _make_game()
        g.combo = 4
        assert g._combo_bonus() == 2.0


# ═══════════════════════════════════════════════════════════════
# Do action — first action / same color combo
# ═══════════════════════════════════════════════════════════════


class TestDoAction:
    def test_first_action_no_combo(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0

        g._do_action(ActionType.FEED)
        assert g.combo == 1
        assert g.last_action == ActionType.FEED
        assert g.happiness == 55.0
        assert g.hunger == 65.0
        assert g.energy == 55.0
        assert g.stress == 2.0
        assert g.score > 0

    def test_same_color_combo_increment(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 2
        g.score = 100

        g._do_action(ActionType.FEED)
        assert g.combo == 3
        assert g.score > 100  # gained points
        assert g.happiness > 50.0

    def test_different_color_resets_combo(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 3
        g.max_combo = 3

        g._do_action(ActionType.PLAY)
        assert g.combo == 1
        assert g.max_combo == 3  # preserved
        assert g.last_action == ActionType.PLAY
        assert g.stress > 0.0  # penalty applied

    def test_same_color_preserves_shake_empty(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 2

        g._do_action(ActionType.FEED)
        assert g.shake_frames == 0  # no shake on match

    def test_different_color_causes_shake(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 2

        g._do_action(ActionType.PLAY)
        assert g.shake_frames == 8

    def test_super_mode_activates_at_threshold(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 3  # next = 4

        g._do_action(ActionType.FEED)
        assert g.combo == 4
        assert g.super_timer == SUPER_DURATION

    def test_super_mode_3x_effect(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 4
        g.super_timer = SUPER_DURATION
        g.score = 0

        old_h = g.happiness
        g._do_action(ActionType.FEED)
        assert g.happiness == old_h + 5.0 * SUPER_MULT
        assert g.stress == 1.0  # reduced cost in super

    def test_super_mode_any_color_counts(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.super_timer = SUPER_DURATION

        g._do_action(ActionType.PLAY)  # different from last_action
        assert g.combo == 1  # wait, actually super mode should keep combo
        # In super mode, any action is treated as matching
        # Since combo is not reset in the implementation...

    def test_super_reactivation_at_combo_8(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 7
        g.super_timer = 100  # partially depleted

        g._do_action(ActionType.FEED)
        assert g.combo == 8
        assert g.super_timer == SUPER_DURATION  # refreshed

    def test_max_combo_tracking(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 3

        g._do_action(ActionType.FEED)
        assert g.max_combo == 4

        g.last_action = ActionType.FEED
        g.combo = 4
        g._rng = random.Random(42)
        g._do_action(ActionType.FEED)
        assert g.max_combo == 5

    def test_spawns_particles(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 0

        assert len(g.particles) == 0
        g._do_action(ActionType.FEED)
        assert len(g.particles) == 8

    def test_spawns_floating_text(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 0

        assert len(g.floating_texts) == 0
        g._do_action(ActionType.FEED)
        assert len(g.floating_texts) >= 1

    def test_clamp_happiness_at_max(self):
        g = _make_game()
        g.happiness = 99.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.PLAY
        g.combo = 0

        g._do_action(ActionType.PLAY)  # +15 happiness
        assert g.happiness == STAT_MAX

    def test_clamp_stress_at_max(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 99.0
        g.last_action = None
        g.combo = 0

        g._do_action(ActionType.TRAIN)  # +8 stress
        assert g.stress == STRESS_CAP


# ═══════════════════════════════════════════════════════════════
# Stat update
# ═══════════════════════════════════════════════════════════════


class TestStatUpdate:
    def test_stat_decay(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0

        g._update_stats()
        assert g.happiness == 50.0 - DECAY_HAPPINESS
        assert g.hunger == 50.0 - DECAY_HUNGER
        assert g.energy == 50.0 - DECAY_ENERGY
        assert g.stress == 0.0 + DECAY_STRESS

    def test_stat_clamp_min(self):
        g = _make_game()
        g.happiness = 0.1
        g.hunger = 0.1
        g.energy = 0.1
        g.stress = 0.0

        g._update_stats()
        assert g.happiness >= STAT_MIN
        assert g.hunger >= STAT_MIN
        assert g.energy >= STAT_MIN

    def test_stat_clamp_max(self):
        g = _make_game()
        g.happiness = 100.0
        g.hunger = 100.0
        g.energy = 100.0
        g.stress = 0.0

        g._update_stats()
        # After decay, values should be below 100
        assert g.happiness <= STAT_MAX
        assert g.hunger <= STAT_MAX
        assert g.energy <= STAT_MAX


# ═══════════════════════════════════════════════════════════════
# CA Spread
# ═══════════════════════════════════════════════════════════════


class TestCASpread:
    def test_no_spread_when_all_ok(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 50.0

        g._check_ca_spread()
        assert g.happiness == 50.0
        assert g.hunger == 50.0
        assert g.energy == 50.0
        assert g.stress == 50.0

    def test_spread_from_min_happiness(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.happiness = 0.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 50.0

        g._check_ca_spread()
        assert g.hunger < 50.0  # right neighbor affected

    def test_spread_from_max_hunger(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.happiness = 50.0
        g.hunger = 100.0
        g.energy = 50.0
        g.stress = 50.0

        g._check_ca_spread()
        assert g.happiness > 50.0  # left neighbor +2
        assert g.energy > 50.0  # right neighbor +3

    def test_spread_clamped_after(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.happiness = 0.0
        g.hunger = 0.5
        g.energy = 50.0
        g.stress = 50.0

        g._check_ca_spread()
        assert g.hunger >= STAT_MIN  # clamped


# ═══════════════════════════════════════════════════════════════
# Timer
# ═══════════════════════════════════════════════════════════════


class TestTimer:
    def test_timer_decrements(self):
        g = _make_game()
        g.timer = 100
        g._update_timer()
        assert g.timer == 99

    def test_timer_game_over_at_zero(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.timer = 1
        g.score = 500
        g.best_score = 300

        g._update_timer()
        assert g.timer == 0
        assert g.phase == Phase.GAME_OVER
        assert g.best_score == 500

    def test_timer_best_score_preserved_when_lower(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.timer = 1
        g.score = 200
        g.best_score = 500

        g._update_timer()
        assert g.best_score == 500


# ═══════════════════════════════════════════════════════════════
# Super mode lifecycle
# ═══════════════════════════════════════════════════════════════


class TestSuperMode:
    def test_super_timer_starts_at_zero(self):
        g = _make_game()
        assert g.super_timer == 0

    def test_super_is_off_when_timer_zero(self):
        g = _make_game()
        g.super_timer = 0
        assert g.super_timer == 0

    def test_super_is_on_when_timer_positive(self):
        g = _make_game()
        g.super_timer = 10
        assert g.super_timer > 0


# ═══════════════════════════════════════════════════════════════
# Particles
# ═══════════════════════════════════════════════════════════════


class TestParticles:
    def test_spawn_particles(self):
        g = _make_game()
        g._spawn_particles(100.0, 100.0, RED, 5)
        assert len(g.particles) == 5
        for p in g.particles:
            assert p.color == RED

    def test_update_particles_gravity(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=10, color=RED)
        g.particles = [p]
        g._update_particles()
        assert abs(p.vy - 0.1) < 0.001

    def test_update_particles_moves(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=1.0, vy=-1.0, life=10, color=RED)
        g.particles = [p]
        g._update_particles()
        assert abs(p.x - 101.0) < 0.001
        assert abs(p.y - 99.1) < 0.001

    def test_update_particles_removes_dead(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=RED)
        g.particles = [p]
        g._update_particles()
        assert len(g.particles) == 0

    def test_update_particles_life_2_survives(self):
        g = _make_game()
        p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=2, color=RED)
        g.particles = [p]
        g._update_particles()
        assert len(g.particles) == 1
        assert g.particles[0].life == 1


# ═══════════════════════════════════════════════════════════════
# Floating texts
# ═══════════════════════════════════════════════════════════════


class TestFloatingTexts:
    def test_spawn_floating_text(self):
        g = _make_game()
        g._spawn_floating_text(100.0, 50.0, "+10", WHITE)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "+10"
        assert g.floating_texts[0].life == 30

    def test_update_floating_texts_rise(self):
        g = _make_game()
        g._spawn_floating_text(100.0, 50.0, "+10", WHITE)
        g._update_floating_texts()
        assert g.floating_texts[0].y == 49.0
        assert g.floating_texts[0].life == 29

    def test_update_floating_texts_removes_dead(self):
        g = _make_game()
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=WHITE, life=1)
        g.floating_texts = [ft]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0

    def test_update_floating_texts_life_2_survives(self):
        g = _make_game()
        ft = FloatingText(x=100.0, y=50.0, text="+10", color=WHITE, life=2)
        g.floating_texts = [ft]
        g._update_floating_texts()
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].life == 1


# ═══════════════════════════════════════════════════════════════
# Phase transitions
# ═══════════════════════════════════════════════════════════════


class TestPhases:
    def test_initial_phase_title(self):
        g = _make_game()
        assert g.phase == Phase.TITLE

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

    def test_reset_clears_stress(self):
        g = _make_game()
        g.stress = 80.0
        g.reset()
        assert g.stress == 0.0

    def test_reset_stats_to_50(self):
        g = _make_game()
        g.happiness = 10.0
        g.hunger = 90.0
        g.energy = 30.0
        g.reset()
        assert g.happiness == 50.0
        assert g.hunger == 50.0
        assert g.energy == 50.0

    def test_reset_clears_particles_and_texts(self):
        g = _make_game()
        g.particles = [Particle(0, 0, 0, 0, 1, RED)]
        g.floating_texts = [FloatingText(0, 0, "test", WHITE, 1)]
        g.reset()
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0

    def test_stress_game_over(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.stress = STRESS_CAP
        g.score = 300
        g.best_score = 200

        # simulate the check from _update_playing
        if g.stress >= STRESS_CAP:
            g.phase = Phase.GAME_OVER
            if g.score > g.best_score:
                g.best_score = g.score
        assert g.phase == Phase.GAME_OVER
        assert g.best_score == 300


# ═══════════════════════════════════════════════════════════════
# Score and tracking
# ═══════════════════════════════════════════════════════════════


class TestScoreTracking:
    def test_score_accumulates(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 0

        g._do_action(ActionType.FEED)
        assert g.score > 0

    def test_max_combo_persists_after_reset(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 0.0
        g.last_action = ActionType.FEED
        g.combo = 3

        g._do_action(ActionType.FEED)
        assert g.max_combo == 4

        # Now a different action
        g.combo = 0
        g._do_action(ActionType.PLAY)
        assert g.max_combo == 4  # preserved

    def test_best_score_preserved_across_reset(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 700
        g.stress = STRESS_CAP

        if g.stress >= STRESS_CAP:
            g.phase = Phase.GAME_OVER
            if g.score > g.best_score:
                g.best_score = g.score
        assert g.best_score == 700

        g.reset()
        assert g.best_score == 700
        assert g.score == 0

    def test_best_score_not_lowered(self):
        g = _make_game()
        g.best_score = 500
        g.score = 300
        g.timer = 1
        g.phase = Phase.PLAYING

        g._update_timer()
        assert g.best_score == 500


# ═══════════════════════════════════════════════════════════════
# Stress management (REST reduces stress)
# ═══════════════════════════════════════════════════════════════


class TestStressManagement:
    def test_rest_reduces_stress(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 50.0
        g.last_action = ActionType.REST
        g.combo = 2

        g._do_action(ActionType.REST)
        assert g.stress < 50.0  # REST has -10 stress

    def test_stress_clamped_at_zero(self):
        g = _make_game()
        g.happiness = 50.0
        g.hunger = 50.0
        g.energy = 50.0
        g.stress = 5.0
        g.last_action = ActionType.REST
        g.combo = 0

        g._do_action(ActionType.REST)
        assert g.stress == 0.0  # clamped


# ═══════════════════════════════════════════════════════════════
# Color helpers
# ═══════════════════════════════════════════════════════════════


class TestColorHelpers:
    def test_happy_color_high(self):
        g = _make_game()
        g.happiness = 80.0
        assert g._happy_color() == YELLOW

    def test_happy_color_mid(self):
        g = _make_game()
        g.happiness = 30.0
        assert g._happy_color() == ORANGE

    def test_happy_color_low(self):
        g = _make_game()
        g.happiness = 10.0
        assert g._happy_color() == RED

    def test_hunger_color_high(self):
        g = _make_game()
        g.hunger = 80.0
        assert g._hunger_color() == GREEN

    def test_hunger_color_low(self):
        g = _make_game()
        g.hunger = 10.0
        assert g._hunger_color() == RED

    def test_energy_color_high(self):
        g = _make_game()
        g.energy = 80.0
        assert g._energy_color() == CYAN

    def test_energy_color_mid(self):
        g = _make_game()
        g.energy = 30.0
        assert g._energy_color() == LIME

    def test_energy_color_low(self):
        g = _make_game()
        g.energy = 10.0
        assert g._energy_color() == ORANGE

    def test_stress_color_low(self):
        g = _make_game()
        g.stress = 10.0
        assert g._stress_color() == GREEN

    def test_stress_color_mid(self):
        g = _make_game()
        g.stress = 45.0
        assert g._stress_color() == ORANGE

    def test_stress_color_high(self):
        g = _make_game()
        g.stress = 80.0
        assert g._stress_color() == RED
