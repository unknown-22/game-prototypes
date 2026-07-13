"""test_imports.py — Headless logic tests for ROPE CHAIN (230_rope_chain)."""
import sys
import math
import random
import unittest.mock as mock

mock_display = mock.MagicMock()
mock_display.return_value = None
sys.modules["pyxel"] = mock.MagicMock()
sys.modules["pyxel"].COLOR_BLACK = 0
sys.modules["pyxel"].COLOR_NAVY = 1
sys.modules["pyxel"].COLOR_PURPLE = 2
sys.modules["pyxel"].COLOR_GREEN = 3
sys.modules["pyxel"].COLOR_BROWN = 4
sys.modules["pyxel"].COLOR_DARK_BLUE = 5
sys.modules["pyxel"].COLOR_LIGHT_BLUE = 6
sys.modules["pyxel"].COLOR_WHITE = 7
sys.modules["pyxel"].COLOR_RED = 8
sys.modules["pyxel"].COLOR_ORANGE = 9
sys.modules["pyxel"].COLOR_YELLOW = 10
sys.modules["pyxel"].COLOR_LIME = 11
sys.modules["pyxel"].COLOR_CYAN = 12
sys.modules["pyxel"].COLOR_GRAY = 13
sys.modules["pyxel"].COLOR_PINK = 14
sys.modules["pyxel"].COLOR_PEACH = 15
sys.modules["pyxel"].MOUSE_BUTTON_LEFT = 0
sys.modules["pyxel"].MOUSE_BUTTON_RIGHT = 1
sys.modules["pyxel"].MOUSE_BUTTON_MIDDLE = 2
sys.modules["pyxel"].KEY_SPACE = 8
sys.modules["pyxel"].KEY_RETURN = 9
sys.modules["pyxel"].btnp = mock.MagicMock(return_value=False)
sys.modules["pyxel"].btn = mock.MagicMock(return_value=False)
sys.modules["pyxel"].frame_count = 0

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/230_rope_chain")
sys.modules["pyxel"].FONT_WIDTH = 4

from main import (  # noqa: E402
    Game, Phase, Particle, FloatingText,
    GROUND_Y, ROPE_PIVOT_X, ROPE_PIVOT_Y, ROPE_LENGTH,
    JUMP_VY, MAX_HEAT, HEAT_MISMATCH, HEAT_ROPE_HIT, HEAT_DECAY,
    GAME_DURATION, SUPER_DURATION, STUN_DURATION,
    COLOR_INTERVAL_START, COLOR_INTERVAL_END,
    ROPE_SPEED_START, ROPE_SPEED_END, MAX_ROPE_ANGLE,
    WHITE, RED,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.rope_angle = 0.0
    g._rope_phase = 0.0
    g.rope_speed = ROPE_SPEED_START
    g.player_y = float(GROUND_Y)
    g.player_vy = 0.0
    g.is_jumping = False
    g.jump_color = 0
    g.current_color = 0
    g.color_timer = COLOR_INTERVAL_START
    g.color_interval = COLOR_INTERVAL_START
    g.super_timer = 0
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.stun_timer = 0
    g._pass_cooldown = 0
    g.particles = []
    g.floating_texts = []
    g.rng = random.Random(42)
    g.phase = Phase.PLAYING
    return g


# ── Test reset ──

def test_reset_clears_all_state() -> None:
    g = _make_game()
    g.phase = Phase.GAME_OVER
    g.score = 999
    g.combo = 5
    g.max_combo = 7
    g.heat = 80.0
    g.timer = 100
    g.stun_timer = 10
    g.super_timer = 50
    g.is_jumping = True
    g.player_vy = -3.0
    g._pass_cooldown = 5
    g.rope_speed = 0.5
    g.color_interval = 30
    g.current_color = 3
    g.jump_color = 2
    g.particles = [Particle(10, 10, 0, 0, 5, RED)]
    g.floating_texts = [FloatingText(10, 10, "test", 10, WHITE)]

    g.reset()

    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.player_y == float(GROUND_Y)
    assert g.player_vy == 0.0
    assert not g.is_jumping
    assert g.jump_color == 0
    assert g.current_color == 0
    assert g.color_timer == COLOR_INTERVAL_START
    assert g.color_interval == COLOR_INTERVAL_START
    assert g.super_timer == 0
    assert g.heat == 0.0
    assert g.timer == GAME_DURATION
    assert g.stun_timer == 0
    assert g._pass_cooldown == 0
    assert g.rope_speed == ROPE_SPEED_START
    assert g.particles == []
    assert g.floating_texts == []


# ── Test rope physics ──

def test_rope_tip_straight_down() -> None:
    g = _make_game()
    g.rope_angle = 0.0
    tip_x, tip_y = g._rope_tip()
    assert tip_x == ROPE_PIVOT_X
    assert tip_y == ROPE_PIVOT_Y + ROPE_LENGTH


def test_rope_tip_at_max_angle() -> None:
    g = _make_game()
    g.rope_angle = MAX_ROPE_ANGLE
    tip_x, tip_y = g._rope_tip()
    expected_x = ROPE_PIVOT_X + math.sin(MAX_ROPE_ANGLE) * ROPE_LENGTH
    expected_y = ROPE_PIVOT_Y + math.cos(MAX_ROPE_ANGLE) * ROPE_LENGTH
    assert abs(tip_x - expected_x) < 0.01
    assert abs(tip_y - expected_y) < 0.01


def test_update_rope_advances_phase() -> None:
    g = _make_game()
    prev_phase = g._rope_phase
    g._update_rope()
    assert g._rope_phase == prev_phase + ROPE_SPEED_START


def test_update_rope_changes_angle() -> None:
    g = _make_game()
    g._rope_phase = math.pi / 2
    g._update_rope()
    # At pi/2 + speed, sin starts decreasing, so angle < MAX_ROPE_ANGLE
    assert g.rope_angle < MAX_ROPE_ANGLE


# ── Test jump physics ──

def test_apply_jump_from_ground() -> None:
    g = _make_game()
    g.player_y = float(GROUND_Y)
    result = g._apply_jump()
    assert result is True
    assert g.is_jumping
    assert g.player_vy == JUMP_VY
    assert g.jump_color == g.current_color


def test_apply_jump_while_airborne_fails() -> None:
    g = _make_game()
    g.player_y = 100.0
    g.is_jumping = True
    result = g._apply_jump()
    assert result is False


def test_apply_jump_while_stunned_fails() -> None:
    g = _make_game()
    g.stun_timer = 10
    result = g._apply_jump()
    assert result is False


def test_update_player_applies_gravity() -> None:
    g = _make_game()
    g._apply_jump()
    old_y = g.player_y
    g._update_player()
    assert g.player_vy > JUMP_VY  # gravity increased vy
    assert g.player_y < old_y  # moved upward


def test_player_lands_after_jump() -> None:
    g = _make_game()
    g._apply_jump()
    for _ in range(100):
        g._update_player()
    assert not g.is_jumping
    assert g.player_y == float(GROUND_Y)
    assert g.player_vy == 0.0


# ── Test color cycling ──

def test_color_timer_decrements() -> None:
    g = _make_game()
    g.color_timer = 50
    g.current_color = 1
    g._update_color()
    assert g.color_timer == 49
    assert g.current_color == 1


def test_color_cycles_when_timer_expires() -> None:
    g = _make_game()
    g.color_timer = 1
    g.current_color = 0
    g.color_interval = 90
    g._update_color()
    assert g.current_color == 1
    assert g.color_timer == 90


def test_color_wraps_from_3_to_0() -> None:
    g = _make_game()
    g.color_timer = 1
    g.current_color = 3
    g.color_interval = 90
    g._update_color()
    assert g.current_color == 0


# ── Test difficulty escalation ──

def test_difficulty_rope_speed_at_start() -> None:
    g = _make_game()
    g.timer = GAME_DURATION
    g._update_difficulty()
    assert g.rope_speed == ROPE_SPEED_START


def test_difficulty_rope_speed_at_end() -> None:
    g = _make_game()
    g.timer = 0
    g._update_difficulty()
    assert g.rope_speed == ROPE_SPEED_END


def test_difficulty_rope_speed_midway() -> None:
    g = _make_game()
    g.timer = GAME_DURATION // 2
    g._update_difficulty()
    mid = (ROPE_SPEED_START + ROPE_SPEED_END) / 2
    assert abs(g.rope_speed - mid) < 0.001


def test_difficulty_color_interval_at_start() -> None:
    g = _make_game()
    g.timer = GAME_DURATION
    g._update_difficulty()
    assert g.color_interval == COLOR_INTERVAL_START


def test_difficulty_color_interval_at_end() -> None:
    g = _make_game()
    g.timer = 0
    g._update_difficulty()
    assert g.color_interval == COLOR_INTERVAL_END


# ── Test rope pass: success (match) ──

def test_rope_pass_success_with_match() -> None:
    g = _make_game()
    g.rope_angle = 0.0  # rope tip at (160, 220), y>=190, x near 160
    g.is_jumping = True
    g.jump_color = 0
    g.current_color = 0  # match
    result = g._check_rope_pass()
    assert result == "jump"
    assert g.combo == 1
    assert g.score == 10  # 10 * combo(1) * 1
    assert g.max_combo == 1
    assert len(g.particles) == 8
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+10"


def test_rope_pass_success_increases_combo() -> None:
    g = _make_game()
    g.rope_angle = 0.0
    g.is_jumping = True
    g.combo = 2
    g.max_combo = 2
    g.jump_color = 0
    g.current_color = 0
    g._check_rope_pass()
    assert g.combo == 3
    assert g.score == 30  # 10 * 3 * 1
    assert g.max_combo == 3


# ── Test rope pass: miss (mismatch) ──

def test_rope_pass_mismatch_resets_combo() -> None:
    g = _make_game()
    g.rope_angle = 0.0
    g.is_jumping = True
    g.combo = 5
    g.max_combo = 5
    g.jump_color = 0
    g.current_color = 1  # mismatch
    g._check_rope_pass()
    assert g.combo == 0
    assert g.max_combo == 5  # max_combo preserved
    assert g.heat == HEAT_MISMATCH
    assert len(g.floating_texts) == 1
    assert "MISS" in g.floating_texts[0].text


# ── Test rope pass: hit ──

def test_rope_pass_hit_when_on_ground() -> None:
    g = _make_game()
    g.rope_angle = 0.0
    g.is_jumping = False
    g.combo = 3
    result = g._check_rope_pass()
    assert result == "hit"
    assert g.heat == HEAT_ROPE_HIT
    assert g.combo == 0
    assert g.stun_timer == STUN_DURATION
    assert len(g.particles) == 8  # red particles
    assert len(g.floating_texts) == 1
    assert "HEAT" in g.floating_texts[0].text


# ── Test rope pass: cooldown ──

def test_rope_pass_cooldown_blocks_retrigger() -> None:
    g = _make_game()
    g.rope_angle = 0.0
    g.is_jumping = True
    g.jump_color = 0
    g.current_color = 0
    result1 = g._check_rope_pass()
    assert result1 == "jump"
    assert g.combo == 1
    assert g._pass_cooldown == 15
    result2 = g._check_rope_pass()
    assert result2 == "none"
    assert g.combo == 1  # combo unchanged
    assert g._pass_cooldown == 14


# ── Test rope pass: no trigger when rope away ──

def test_rope_pass_no_trigger_when_tip_high() -> None:
    g = _make_game()
    g.rope_angle = MAX_ROPE_ANGLE  # tip_y ≈ 140, below threshold 190
    g.is_jumping = False
    result = g._check_rope_pass()
    assert result == "none"
    assert g.heat == 0.0


def test_rope_pass_no_trigger_when_tip_far_x() -> None:
    g = _make_game()
    # Angle such that tip_x is far from player
    g.rope_angle = 0.8  # tip_y still > 190? cos(0.8)*160 ≈ 0.697*160=111.5, +60=171.5 < 190
    # Need an angle where tip_y >= 190 but tip_x far
    # tip_y >= 190 → cos(angle) >= 130/160 = 0.8125 → |angle| < 0.622
    # tip_x = 160 + sin(angle)*160, so tip_x near 160 when angle near 0
    # At angle=0.6: tip_y = 60 + cos(0.6)*160 = 60+0.825*160=192.1 (in danger zone)
    # tip_x = 160 + sin(0.6)*160 = 160+0.565*160=250.3 (far from 160, diff=90.3 > 20)
    g.rope_angle = 0.6
    g.is_jumping = False
    result = g._check_rope_pass()
    assert result == "none"


# ── Test SUPER mode ──

def test_super_activated_at_combo_4() -> None:
    g = _make_game()
    g.rope_angle = 0.0
    g.is_jumping = True
    g.combo = 3
    g.max_combo = 3
    g.jump_color = 0
    g.current_color = 0
    g._check_rope_pass()
    assert g.super_timer == SUPER_DURATION
    assert g.combo == 4


def test_super_mode_auto_jump() -> None:
    g = _make_game()
    g.rope_angle = 0.0
    g.is_jumping = False
    g.super_timer = 100
    g.combo = 0
    g._check_rope_pass()
    # Auto-jump applied, then success — player is now jumping
    assert g.is_jumping
    assert g.combo == 1


def test_super_mode_color_mismatch_still_matches() -> None:
    g = _make_game()
    g.rope_angle = 0.0
    g.is_jumping = True
    g.super_timer = 100
    g.jump_color = 0
    g.current_color = 3  # would be mismatch normally
    g._check_rope_pass()
    assert g.combo == 1  # super mode matches any color
    assert g.heat == 0.0


def test_super_mode_3x_score() -> None:
    g = _make_game()
    g.rope_angle = 0.0
    g.is_jumping = True
    g.super_timer = 100
    g.combo = 0
    g.jump_color = 0
    g.current_color = 0
    g._check_rope_pass()
    assert g.score == 30  # 10 * 1 * 3


def test_super_timer_decrements() -> None:
    g = _make_game()
    g.super_timer = 100
    g._update_super()
    assert g.super_timer == 99


def test_super_expiry_resets_combo() -> None:
    g = _make_game()
    g.super_timer = 1
    g.combo = 10
    g._update_super()
    assert g.super_timer == 0
    assert g.combo == 0


def test_super_mode_super_already_active_does_not_retrigger() -> None:
    """Combo >= 4 while already in SUPER mode does not reset super_timer."""
    g = _make_game()
    g.super_timer = 200
    g.rope_angle = 0.0
    g.is_jumping = True
    g.combo = 5
    g.jump_color = 0
    g.current_color = 0
    g._check_rope_pass()
    assert g.super_timer == 200  # not reset, already active
    assert g.combo == 6


# ── Test heat ──

def test_heat_decays() -> None:
    g = _make_game()
    g.heat = 20.0
    g._update_heat()
    assert g.heat == 20.0 - HEAT_DECAY


def test_heat_stays_at_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_clamped_on_hit() -> None:
    g = _make_game()
    g.heat = MAX_HEAT - 10
    g._on_rope_hit()  # adds HEAT_ROPE_HIT, clamped at MAX_HEAT
    assert g.heat <= MAX_HEAT


def test_heat_at_max_triggers_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


# ── Test timer ──

def test_timer_decrements() -> None:
    g = _make_game()
    old = g.timer
    g._update_timer()
    assert g.timer == old - 1


def test_timer_zero_triggers_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


# ── Test particles ──

def test_particles_move_and_decay() -> None:
    g = _make_game()
    p = Particle(100.0, 100.0, 1.0, -2.0, 10, RED, 2)
    g.particles = [p]
    g._update_particles()
    assert p.life == 9
    assert p.x == 101.0
    assert p.y == 100.0 + (-2.0 + 0.15)  # 100 + (-1.85) = 98.15
    assert p.vy == -2.0 + 0.15


def test_particles_expire() -> None:
    g = _make_game()
    g.particles = [Particle(0, 0, 0, 0, 1, RED)]
    g._update_particles()
    assert len(g.particles) == 0


def test_particles_gravity() -> None:
    g = _make_game()
    p = Particle(0, 0, 0, 0, 10, RED)
    g.particles = [p]
    g._update_particles()
    assert p.vy == 0.15


# ── Test floating texts ──

def test_floating_texts_move_and_decay() -> None:
    g = _make_game()
    ft = FloatingText(100.0, 100.0, "+10", 30, WHITE)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert ft.life == 29
    assert ft.y == 98.5


def test_floating_texts_expire() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(0, 0, "x", 1, WHITE)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Test stun ──

def test_stun_timer_decrements() -> None:
    g = _make_game()
    g.stun_timer = 10
    g._update_stun()
    assert g.stun_timer == 9


def test_stun_timer_stays_at_zero() -> None:
    g = _make_game()
    g.stun_timer = 0
    g._update_stun()
    assert g.stun_timer == 0


# ── Test score calculation ──

def test_score_increases_with_combo() -> None:
    g = _make_game()
    g.combo = 4
    g.rope_angle = 0.0
    g.is_jumping = True
    g.jump_color = 0
    g.current_color = 0
    g._check_rope_pass()
    assert g.score == 50  # 10 * 5 * 1


def test_score_with_super_multiplier() -> None:
    g = _make_game()
    g.super_timer = 100
    g.combo = 2
    g.rope_angle = 0.0
    g.is_jumping = True
    g.jump_color = 0
    g.current_color = 0
    g._check_rope_pass()
    assert g.score == 90  # 10 * 3 * 3


# ── Test max_combo tracking ──

def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.max_combo = 5
    g.combo = 5
    g.rope_angle = 0.0
    g.is_jumping = True
    g.jump_color = 0
    g.current_color = 0
    g._check_rope_pass()
    assert g.max_combo == 6


def test_max_combo_preserved_on_mismatch() -> None:
    g = _make_game()
    g.max_combo = 10
    g.combo = 10
    g.rope_angle = 0.0
    g.is_jumping = True
    g.jump_color = 0
    g.current_color = 1
    g._check_rope_pass()
    assert g.max_combo == 10
    assert g.combo == 0


# ── Test _on_rope_hit directly ──

def test_on_rope_hit_heat_and_stun() -> None:
    g = _make_game()
    g.combo = 3
    g.heat = 10.0
    g._on_rope_hit()
    assert g.heat == min(MAX_HEAT, 10.0 + HEAT_ROPE_HIT)
    assert g.stun_timer == STUN_DURATION
    assert g.combo == 0
    assert len(g.particles) == 8
    assert len(g.floating_texts) == 1


# ── Test _on_successful_jump directly ──

def test_on_successful_jump_match() -> None:
    g = _make_game()
    g.jump_color = 2
    g.current_color = 2
    g.combo = 0
    g._on_successful_jump()
    assert g.combo == 1
    assert g.score == 10
    assert len(g.particles) == 8
    assert len(g.floating_texts) == 1


def test_on_successful_jump_mismatch() -> None:
    g = _make_game()
    g.jump_color = 0
    g.current_color = 1
    g.combo = 3
    g._on_successful_jump()
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH
    assert len(g.floating_texts) == 1
    assert "MISS" in g.floating_texts[0].text


def test_on_successful_jump_super_activation_particles() -> None:
    g = _make_game()
    g.combo = 3
    g.jump_color = 0
    g.current_color = 0
    g._on_successful_jump()
    assert g.super_timer == SUPER_DURATION
    # 8 regular + 16 super activation particles
    assert len(g.particles) == 24
    assert len(g.floating_texts) == 2


# ── Run all tests ──
if __name__ == "__main__":
    import traceback

    tests = [
        ("test_reset_clears_all_state", test_reset_clears_all_state),
        ("test_rope_tip_straight_down", test_rope_tip_straight_down),
        ("test_rope_tip_at_max_angle", test_rope_tip_at_max_angle),
        ("test_update_rope_advances_phase", test_update_rope_advances_phase),
        ("test_update_rope_changes_angle", test_update_rope_changes_angle),
        ("test_apply_jump_from_ground", test_apply_jump_from_ground),
        ("test_apply_jump_while_airborne_fails", test_apply_jump_while_airborne_fails),
        ("test_apply_jump_while_stunned_fails", test_apply_jump_while_stunned_fails),
        ("test_update_player_applies_gravity", test_update_player_applies_gravity),
        ("test_player_lands_after_jump", test_player_lands_after_jump),
        ("test_color_timer_decrements", test_color_timer_decrements),
        ("test_color_cycles_when_timer_expires", test_color_cycles_when_timer_expires),
        ("test_color_wraps_from_3_to_0", test_color_wraps_from_3_to_0),
        ("test_difficulty_rope_speed_at_start", test_difficulty_rope_speed_at_start),
        ("test_difficulty_rope_speed_at_end", test_difficulty_rope_speed_at_end),
        ("test_difficulty_rope_speed_midway", test_difficulty_rope_speed_midway),
        ("test_difficulty_color_interval_at_start", test_difficulty_color_interval_at_start),
        ("test_difficulty_color_interval_at_end", test_difficulty_color_interval_at_end),
        ("test_rope_pass_success_with_match", test_rope_pass_success_with_match),
        ("test_rope_pass_success_increases_combo", test_rope_pass_success_increases_combo),
        ("test_rope_pass_mismatch_resets_combo", test_rope_pass_mismatch_resets_combo),
        ("test_rope_pass_hit_when_on_ground", test_rope_pass_hit_when_on_ground),
        ("test_rope_pass_cooldown_blocks_retrigger", test_rope_pass_cooldown_blocks_retrigger),
        ("test_rope_pass_no_trigger_when_tip_high", test_rope_pass_no_trigger_when_tip_high),
        ("test_rope_pass_no_trigger_when_tip_far_x", test_rope_pass_no_trigger_when_tip_far_x),
        ("test_super_activated_at_combo_4", test_super_activated_at_combo_4),
        ("test_super_mode_auto_jump", test_super_mode_auto_jump),
        ("test_super_mode_color_mismatch_still_matches", test_super_mode_color_mismatch_still_matches),
        ("test_super_mode_3x_score", test_super_mode_3x_score),
        ("test_super_timer_decrements", test_super_timer_decrements),
        ("test_super_expiry_resets_combo", test_super_expiry_resets_combo),
        ("test_super_mode_super_already_active_does_not_retrigger", test_super_mode_super_already_active_does_not_retrigger),
        ("test_heat_decays", test_heat_decays),
        ("test_heat_stays_at_zero", test_heat_stays_at_zero),
        ("test_heat_clamped_on_hit", test_heat_clamped_on_hit),
        ("test_heat_at_max_triggers_game_over", test_heat_at_max_triggers_game_over),
        ("test_timer_decrements", test_timer_decrements),
        ("test_timer_zero_triggers_game_over", test_timer_zero_triggers_game_over),
        ("test_particles_move_and_decay", test_particles_move_and_decay),
        ("test_particles_expire", test_particles_expire),
        ("test_particles_gravity", test_particles_gravity),
        ("test_floating_texts_move_and_decay", test_floating_texts_move_and_decay),
        ("test_floating_texts_expire", test_floating_texts_expire),
        ("test_stun_timer_decrements", test_stun_timer_decrements),
        ("test_stun_timer_stays_at_zero", test_stun_timer_stays_at_zero),
        ("test_score_increases_with_combo", test_score_increases_with_combo),
        ("test_score_with_super_multiplier", test_score_with_super_multiplier),
        ("test_max_combo_tracks_highest", test_max_combo_tracks_highest),
        ("test_max_combo_preserved_on_mismatch", test_max_combo_preserved_on_mismatch),
        ("test_on_rope_hit_heat_and_stun", test_on_rope_hit_heat_and_stun),
        ("test_on_successful_jump_match", test_on_successful_jump_match),
        ("test_on_successful_jump_mismatch", test_on_successful_jump_mismatch),
        ("test_on_successful_jump_super_activation_particles", test_on_successful_jump_super_activation_particles),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception:
            print(f"  FAIL {name}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
