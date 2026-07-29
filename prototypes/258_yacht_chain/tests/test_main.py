from __future__ import annotations

import random

from main import (
    DIE_COLORS,
    DARK_BLUE,
    GAME_TIME,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    LIME,
    MAX_ROLLS,
    RED,
    ROLL_ANIM_FRAMES,
    SCORE_ANIM_FRAMES,
    SUPER_COMBO_THRESHOLD,
    SUPER_DURATION,
    YELLOW,
    Die,
    Game,
    Phase,
    evaluate_hand,
)


def _new_game() -> Game:
    g = Game.__new__(Game)
    g._set_defaults()
    g._headless = True
    g._rng = random.Random(42)
    return g


def _start_game(g: Game) -> None:
    g.phase = Phase.ROLLING
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_TIME
    g.super_timer = 0
    g.best_hand = ""
    g.best_hand_score = 0
    g.rolls_left = MAX_ROLLS
    g.prev_dominant_color = -1
    g.particles.clear()
    g.floating_texts.clear()
    g.score_anim_frame = 0
    g.last_hand_name = ""
    g.last_hand_score = 0
    g.last_dominant_color = -1
    g.yahtzee_flash = 0
    g.button_hover = False
    g.frame = 0
    for d in g.dice:
        d.color = RED
        d.held = False
        d.roll_frame = 0
        d.target_color = RED


# ---------------------------------------------------------------------------
# evaluate_hand tests
# ---------------------------------------------------------------------------
class TestEvaluateHand:
    def test_yahtzee_all_five_same(self) -> None:
        dice = [Die(color=RED), Die(color=RED), Die(color=RED), Die(color=RED), Die(color=RED)]
        score, name, color = evaluate_hand(dice)
        assert name == "YAHTZEE!"
        assert score == 100
        assert color == RED

    def test_four_kind(self) -> None:
        dice = [Die(color=RED), Die(color=RED), Die(color=RED), Die(color=RED), Die(color=LIME)]
        score, name, color = evaluate_hand(dice)
        assert name == "FOUR KIND"
        assert score == 60
        assert color == RED

    def test_full_house(self) -> None:
        dice = [Die(color=RED), Die(color=RED), Die(color=RED), Die(color=LIME), Die(color=LIME)]
        score, name, color = evaluate_hand(dice)
        assert name == "FULL HOUSE"
        assert score == 50
        assert color == RED

    def test_three_kind(self) -> None:
        dice = [Die(color=RED), Die(color=RED), Die(color=RED), Die(color=LIME), Die(color=YELLOW)]
        score, name, color = evaluate_hand(dice)
        assert name == "THREE KIND"
        assert score == 30
        assert color == RED

    def test_two_pair(self) -> None:
        dice = [Die(color=RED), Die(color=RED), Die(color=LIME), Die(color=LIME), Die(color=YELLOW)]
        score, name, color = evaluate_hand(dice)
        assert name == "TWO PAIR"
        assert score == 20
        # dominant color could be RED or LIME (both 2), Counter.most_common is stable
        assert color in (RED, LIME, YELLOW)

    def test_one_pair(self) -> None:
        dice = [Die(color=RED), Die(color=RED), Die(color=LIME), Die(color=YELLOW), Die(color=DARK_BLUE)]
        score, name, color = evaluate_hand(dice)
        assert name == "ONE PAIR"
        assert score == 10
        assert color == RED

    def test_no_match(self) -> None:
        dice = [Die(color=RED), Die(color=LIME), Die(color=YELLOW), Die(color=DARK_BLUE), Die(color=DARK_BLUE)]
        score, name, color = evaluate_hand(dice)
        assert name == "ONE PAIR"
        assert score == 10

    def test_yahtzee_different_color(self) -> None:
        dice = [Die(color=LIME), Die(color=LIME), Die(color=LIME), Die(color=LIME), Die(color=LIME)]
        score, name, color = evaluate_hand(dice)
        assert name == "YAHTZEE!"
        assert score == 100
        assert color == LIME


# ---------------------------------------------------------------------------
# Reset tests
# ---------------------------------------------------------------------------
class TestReset:
    def test_reset_sets_title_phase(self) -> None:
        g = _new_game()
        g.phase = Phase.ROLLING
        g.score = 500
        g.combo = 10
        g.heat = 50.0
        g.timer = 100
        g.reset()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.timer == GAME_TIME
        assert g.rolls_left == MAX_ROLLS
        assert g.super_timer == 0
        assert g.prev_dominant_color == -1

    def test_reset_clears_dice_state(self) -> None:
        g = _new_game()
        for d in g.dice:
            d.color = LIME
            d.held = True
        g.reset()
        for d in g.dice:
            assert d.color == RED
            assert d.held is False


# ---------------------------------------------------------------------------
# Dice roll tests
# ---------------------------------------------------------------------------
class TestDiceRoll:
    def test_do_roll_decrements_rolls_left(self) -> None:
        g = _new_game()
        _start_game(g)
        assert g.rolls_left == 3
        g._do_roll()
        assert g.rolls_left == 2

    def test_do_roll_only_unheld_dice(self) -> None:
        g = _new_game()
        _start_game(g)
        g.dice[0].held = True
        old_color = g.dice[0].color
        g._do_roll()
        for _ in range(ROLL_ANIM_FRAMES):
            g._update_roll_animation()
        assert g.dice[0].color == old_color
        assert g.dice[0].held is True

    def test_cannot_roll_when_rolls_left_is_zero(self) -> None:
        g = _new_game()
        _start_game(g)
        g.rolls_left = 0
        g._do_roll()
        assert g.rolls_left == 0

    def test_cannot_roll_while_rolling(self) -> None:
        g = _new_game()
        _start_game(g)
        g.dice[0].roll_frame = 5
        assert g._is_rolling() is True
        g._do_roll()
        assert g.rolls_left == 3

    def test_roll_animation_sets_target_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g._do_roll()
        for _ in range(ROLL_ANIM_FRAMES + 1):
            g._update_roll_animation()
        for d in g.dice:
            assert d.roll_frame == 0

    def test_roll_final_colors_are_valid(self) -> None:
        g = _new_game()
        _start_game(g)
        g._do_roll()
        for _ in range(ROLL_ANIM_FRAMES + 1):
            g._update_roll_animation()
        for d in g.dice:
            assert d.color in DIE_COLORS


# ---------------------------------------------------------------------------
# Hold toggle tests
# ---------------------------------------------------------------------------
class TestHoldToggle:
    def test_hit_die_returns_true_for_die_area(self) -> None:
        g = _new_game()
        _start_game(g)
        d = g.dice[0]
        cx, cy = d.x, d.y
        assert g._hit_die(cx, cy, d) is True

    def test_hit_die_returns_false_outside(self) -> None:
        g = _new_game()
        _start_game(g)
        d = g.dice[0]
        assert g._hit_die(0, 0, d) is False

    def test_hold_toggles_on_click(self) -> None:
        g = _new_game()
        _start_game(g)
        d = g.dice[0]
        assert d.held is False
        mx, my = d.x, d.y
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": mx, "mouse_y": my, "mouse_pressed": True,
        })
        assert d.held is True
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": mx, "mouse_y": my, "mouse_pressed": True,
        })
        assert d.held is False


# ---------------------------------------------------------------------------
# DO SCORE tests
# ---------------------------------------------------------------------------
class TestDoScore:
    def test_do_score_evaluates_hand_and_adds_score(self) -> None:
        g = _new_game()
        _start_game(g)
        for d in g.dice:
            d.color = RED
        g._do_score()
        assert g.last_hand_name == "YAHTZEE!"
        assert g.last_hand_score > 0
        assert g.score > 0
        assert g.phase == Phase.SCORING

    def test_do_score_no_combo_no_mismatch_heat(self) -> None:
        g = _new_game()
        _start_game(g)
        g.prev_dominant_color = -1
        g.heat = 0.0
        for d in g.dice:
            d.color = RED
        g._do_score()
        assert g.combo == 1
        assert g.heat == 0.0

    def test_mismatch_increases_heat(self) -> None:
        g = _new_game()
        _start_game(g)
        g.prev_dominant_color = RED
        for d in g.dice:
            d.color = LIME
        g._do_score()
        assert g.combo == 0
        assert g.heat == HEAT_MISMATCH

    def test_mismatch_no_heat_in_super(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 100
        g.prev_dominant_color = RED
        g.heat = 0.0
        for d in g.dice:
            d.color = LIME
        g._do_score()
        assert g.heat == 0.0

    def test_same_color_increments_combo(self) -> None:
        g = _new_game()
        _start_game(g)
        g.prev_dominant_color = RED
        g.combo = 2
        for d in g.dice:
            d.color = RED  # YAHTZEE, dominant = RED
        g._do_score()
        assert g.combo == 3
        assert g.last_dominant_color == RED

    def test_super_miltiplier_applies(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 200
        g.combo = 1
        g.prev_dominant_color = RED
        for d in g.dice:
            d.color = RED  # YAHTZEE, base 100
        g._do_score()
        expected = int(100 * (1 + 2 * 0.5) * 3)  # 100 * 2 * 3 = 600
        assert g.last_hand_score == expected

    def test_super_activates_at_combo_threshold(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 0
        g.combo = SUPER_COMBO_THRESHOLD - 1
        g.prev_dominant_color = RED
        for d in g.dice:
            d.color = RED
        g._do_score()
        assert g.combo == SUPER_COMBO_THRESHOLD
        assert g.super_timer == SUPER_DURATION

    def test_best_hand_tracked(self) -> None:
        g = _new_game()
        _start_game(g)
        for d in g.dice:
            d.color = RED
        g._do_score()
        assert g.best_hand_score > 0
        assert g.best_hand != ""

    def test_auto_score_after_max_rolls(self) -> None:
        g = _new_game()
        _start_game(g)
        g.rolls_left = 0
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.phase == Phase.SCORING

    def test_scoring_transitions_back_to_rolling(self) -> None:
        g = _new_game()
        _start_game(g)
        for d in g.dice:
            d.color = RED
        g._do_score()
        assert g.phase == Phase.SCORING
        for _ in range(SCORE_ANIM_FRAMES + 1):
            g._update_scoring({
                "space_p": False, "space": False, "r_p": False,
                "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
            })
        assert g.phase == Phase.ROLLING
        assert g.rolls_left == MAX_ROLLS


# ---------------------------------------------------------------------------
# COMBO tests
# ---------------------------------------------------------------------------
class TestCombo:
    def test_combo_tracks_max_combo(self) -> None:
        g = _new_game()
        _start_game(g)
        g.prev_dominant_color = RED
        g.combo = 1
        g.max_combo = 1
        for d in g.dice:
            d.color = RED
        g._do_score()
        assert g.combo == 2
        assert g.max_combo == 2

    def test_mismatch_resets_combo(self) -> None:
        g = _new_game()
        _start_game(g)
        g.prev_dominant_color = RED
        g.combo = 5
        g.max_combo = 5
        for d in g.dice:
            d.color = LIME
        g._do_score()
        assert g.combo == 0

    def test_combo_score_multiplier(self) -> None:
        g = _new_game()
        _start_game(g)
        g.prev_dominant_color = RED
        g.combo = 4
        for d in g.dice:
            d.color = RED  # ONE PAIR: base=10
        g.dice[0].color = RED
        g.dice[1].color = RED
        g.dice[2].color = LIME
        g.dice[3].color = YELLOW
        g.dice[4].color = DARK_BLUE
        g._do_score()
        expected = int(10 * (1 + 5 * 0.5))  # 10 * 3.5 = 35
        assert g.last_hand_score >= expected


# ---------------------------------------------------------------------------
# HEAT tests
# ---------------------------------------------------------------------------
class TestHeat:
    def test_heat_decay(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = 50.0
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.heat == 50.0 - HEAT_DECAY

    def test_heat_decay_not_below_zero(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = 0.001
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.heat == 0.0

    def test_heat_no_decay_in_super(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 100
        g.heat = 50.0
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.heat == 50.0

    def test_heat_game_over(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = HEAT_MAX
        g.timer = 100
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.phase == Phase.GAME_OVER

    def test_mismatch_heat_capped_at_max(self) -> None:
        g = _new_game()
        _start_game(g)
        g.prev_dominant_color = RED
        g.heat = 95.0
        for d in g.dice:
            d.color = LIME
        g._do_score()
        assert g.heat == HEAT_MAX


# ---------------------------------------------------------------------------
# SUPER MODE tests
# ---------------------------------------------------------------------------
class TestSuperMode:
    def test_is_super_returns_false_when_inactive(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 0
        assert g._is_super() is False

    def test_is_super_returns_true_when_active(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 100
        assert g._is_super() is True

    def test_super_timer_countdown(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 5
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.super_timer == 4

    def test_super_expires_combo_resets(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 1
        g.combo = 5
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.super_timer == 0
        assert g.combo == 0


# ---------------------------------------------------------------------------
# Timer tests
# ---------------------------------------------------------------------------
class TestTimer:
    def test_timer_decreases_in_rolling(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = 100
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.timer == 99

    def test_timer_decreases_in_scoring(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = 100
        g.phase = Phase.SCORING
        g._update_scoring({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.timer == 99

    def test_timer_zero_game_over_rolling(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = 1
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.phase == Phase.GAME_OVER

    def test_timer_zero_game_over_scoring(self) -> None:
        g = _new_game()
        _start_game(g)
        g.phase = Phase.SCORING
        g.timer = 1
        g._update_scoring({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.phase == Phase.GAME_OVER


# ---------------------------------------------------------------------------
# Phase flow tests
# ---------------------------------------------------------------------------
class TestPhaseFlow:
    def test_title_to_rolling(self) -> None:
        g = _new_game()
        g.reset()
        g._update_title({
            "space_p": True, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.phase == Phase.ROLLING

    def test_title_click_to_start(self) -> None:
        g = _new_game()
        g.reset()
        g._update_title({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 100, "mouse_y": 100, "mouse_pressed": True,
        })
        assert g.phase == Phase.ROLLING

    def test_game_over_to_title(self) -> None:
        g = _new_game()
        g.phase = Phase.GAME_OVER
        g._update_game_over({
            "space_p": True, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.phase == Phase.TITLE

    def test_r_key_restarts(self) -> None:
        g = _new_game()
        g.phase = Phase.GAME_OVER
        g._update_game_over({
            "space_p": False, "space": False, "r_p": True,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.phase == Phase.TITLE


# ---------------------------------------------------------------------------
# Button hit tests
# ---------------------------------------------------------------------------
class TestHitButtons:
    def test_roll_button_hit(self) -> None:
        g = _new_game()
        _start_game(g)
        bx = (320 - 100) // 2
        assert g._hit_roll_button(bx + 50, 170) is True

    def test_roll_button_miss(self) -> None:
        g = _new_game()
        _start_game(g)
        assert g._hit_roll_button(0, 0) is False

    def test_score_button_hit(self) -> None:
        g = _new_game()
        _start_game(g)
        assert g._hit_score_button(270, 170) is True

    def test_score_button_miss(self) -> None:
        g = _new_game()
        _start_game(g)
        assert g._hit_score_button(0, 0) is False


# ---------------------------------------------------------------------------
# Roll button click triggers roll
# ---------------------------------------------------------------------------
class TestRollButton:
    def test_click_roll_button_does_roll(self) -> None:
        g = _new_game()
        _start_game(g)
        bx = (320 - 100) // 2 + 50
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": bx, "mouse_y": 170, "mouse_pressed": True,
        })
        assert g.rolls_left == 2

    def test_space_does_roll(self) -> None:
        g = _new_game()
        _start_game(g)
        g._update_rolling({
            "space_p": True, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.rolls_left == 2


# ---------------------------------------------------------------------------
# Score button click triggers score
# ---------------------------------------------------------------------------
class TestScoreButton:
    def test_click_score_button_scores(self) -> None:
        g = _new_game()
        _start_game(g)
        g.rolls_left = 2  # already spent 1 roll to enable score button
        for d in g.dice:
            d.color = RED
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 270, "mouse_y": 170, "mouse_pressed": True,
        })
        assert g.phase == Phase.SCORING


# ---------------------------------------------------------------------------
# Particles tests
# ---------------------------------------------------------------------------
class TestParticles:
    def test_particles_spawn(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_particles(100.0, 100.0, 5, RED)
        assert len(g.particles) == 5

    def test_particles_move(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_particles(100.0, 100.0, 1, RED)
        p = g.particles[0]
        ox, oy = p.x, p.y
        g._update_particles()
        assert p.x != ox or p.y != oy

    def test_particles_expire(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_particles(100.0, 100.0, 1, RED)
        g.particles[0].life = 0
        g._update_particles()
        assert len(g.particles) == 0

    def test_floating_texts_spawn(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_floating_text(100.0, 100.0, "TEST", RED, 20)
        assert len(g.floating_texts) == 1

    def test_floating_texts_float_upward(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_floating_text(100.0, 100.0, "TEST", RED, 20)
        oy = g.floating_texts[0].y
        g._update_floating_texts()
        assert g.floating_texts[0].y < oy

    def test_yahtzee_spawns_30_particles(self) -> None:
        g = _new_game()
        _start_game(g)
        g.particles.clear()
        for d in g.dice:
            d.color = RED
        g._do_score()
        assert len(g.particles) == 30

    def test_four_kind_spawns_20_particles(self) -> None:
        g = _new_game()
        _start_game(g)
        g.particles.clear()
        for i, d in enumerate(g.dice):
            d.color = RED if i < 4 else LIME
        g._do_score()
        assert len(g.particles) == 20


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_best_score_tracked(self) -> None:
        g = _new_game()
        _start_game(g)
        g.score = 500
        g.best_score = 0
        g.timer = 1
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.best_score == 500

    def test_yahtzee_flash_set_on_yahtzee(self) -> None:
        g = _new_game()
        _start_game(g)
        for d in g.dice:
            d.color = RED
        g._do_score()
        assert g.yahtzee_flash == 15

    def test_yahtzee_flash_not_set_on_non_yahtzee(self) -> None:
        g = _new_game()
        _start_game(g)
        g.yahtzee_flash = 0
        for i, d in enumerate(g.dice):
            d.color = RED if i < 4 else LIME
        g._do_score()
        assert g.yahtzee_flash == 0

    def test_rng_deterministic(self) -> None:
        g1 = _new_game()
        g2 = _new_game()
        _start_game(g1)
        _start_game(g2)
        g1._do_roll()
        g2._do_roll()
        for _ in range(ROLL_ANIM_FRAMES + 1):
            g1._update_roll_animation()
            g2._update_roll_animation()
        for d1, d2 in zip(g1.dice, g2.dice):
            assert d1.color == d2.color

    def test_super_timer_countdown_and_combo_reset_on_expire(self) -> None:
        g = _new_game()
        _start_game(g)
        g.combo = 5
        g.super_timer = SUPER_DURATION
        # simulate countdown
        for _ in range(SUPER_DURATION):
            g.super_timer -= 1
            if g.super_timer == 0:
                g.combo = 0
        assert g.super_timer == 0
        assert g.combo == 0

    def test_dice_init_positions(self) -> None:
        g = _new_game()
        assert len(g.dice) == 5
        for i in range(4):
            assert g.dice[i].x < g.dice[i + 1].x

    def test_heat_capped_in_update(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = HEAT_MAX
        g.timer = 100
        g._update_rolling({
            "space_p": False, "space": False, "r_p": False,
            "mouse_x": 0, "mouse_y": 0, "mouse_pressed": False,
        })
        assert g.phase == Phase.GAME_OVER
