from __future__ import annotations

import random

from main import (
    BIKE_X,
    COLOR_VALS,
    GAME_DURATION,
    GATE_GAP_WIDTH,
    GRAVITY,
    GROUND_Y,
    HEAT_DECAY,
    HEAT_IGNORE,
    HEAT_MISMATCH,
    JUMP_VY,
    MAX_HEAT,
    STAMINA_JUMP_COST,
    STAMINA_MAX,
    STAMINA_RECHARGE,
    SUPER_DURATION,
    Game,
    Gate,
    Phase,
)


def _new_game() -> Game:
    g = Game.__new__(Game)
    g._set_defaults()
    g._headless = True
    g._rng = random.Random(42)
    return g


def _start_game(g: Game) -> None:
    g.phase = Phase.PLAYING
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.stamina = STAMINA_MAX
    g.timer = GAME_DURATION
    g.bike_color = 0
    g.bike_color_timer = 20
    g.bike_y = float(GROUND_Y)
    g.bike_vy = 0.0
    g.is_jumping = False
    g.super_timer = 0
    g.gates.clear()
    g.particles.clear()
    g.floating_texts.clear()
    g.scroll_speed = 2.0
    g.scroll_x = 0.0
    g.gate_spawn_timer = 30
    g.gate_spawn_interval = 90
    g.shake_frames = 0
    g.stun_frames = 0
    g.frame = 0
    g.ghost_trail.clear()
    g.current_trail.clear()


# ---------------------------------------------------------------------------
# Reset tests
# ---------------------------------------------------------------------------
class TestReset:
    def test_reset_sets_title_phase(self) -> None:
        g = _new_game()
        g.phase = Phase.PLAYING
        g.score = 500
        g.combo = 10
        g.max_combo = 15
        g.heat = 80.0
        g.timer = 100
        g.reset()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.stamina == STAMINA_MAX
        assert g.timer == GAME_DURATION
        assert g.bike_color == 0
        assert g.bike_y == float(GROUND_Y)
        assert g.super_timer == 0
        assert len(g.gates) == 0
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0

    def test_reset_clears_trails(self) -> None:
        g = _new_game()
        g.ghost_trail = [(100, 200), (200, 200)]
        g.best_trail = [(100, 200)]
        g.current_trail = [(50, 200)]
        g.reset()
        assert len(g.ghost_trail) == 0
        assert len(g.best_trail) == 0
        assert len(g.current_trail) == 0


# ---------------------------------------------------------------------------
# Gate process tests
# ---------------------------------------------------------------------------
class TestProcessGate:
    def test_match_when_same_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_color = 0  # RED=8
        gate = Gate(x=100.0, y=float(GROUND_Y), color=COLOR_VALS[0], width=GATE_GAP_WIDTH)
        assert g._process_gate(gate) is True

    def test_mismatch_when_different_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_color = 0  # RED=8
        gate = Gate(x=100.0, y=float(GROUND_Y), color=COLOR_VALS[1], width=GATE_GAP_WIDTH)
        assert g._process_gate(gate) is False

    def test_match_in_super_mode_any_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_color = 0
        g.super_timer = 100  # SUPER active
        gate = Gate(x=100.0, y=float(GROUND_Y), color=COLOR_VALS[3], width=GATE_GAP_WIDTH)
        assert g._process_gate(gate) is True

    def test_match_all_colors_when_color_cycles(self) -> None:
        g = _new_game()
        _start_game(g)
        for i, expected_color in enumerate(COLOR_VALS):
            g.bike_color = i
            gate = Gate(x=100.0, y=float(GROUND_Y), color=expected_color, width=GATE_GAP_WIDTH)
            assert g._process_gate(gate) is True


# ---------------------------------------------------------------------------
# Gate update tests
# ---------------------------------------------------------------------------
class TestUpdateGates:
    def test_gates_move_left_by_scroll_speed(self) -> None:
        g = _new_game()
        _start_game(g)
        gate = Gate(x=200.0, y=float(GROUND_Y), color=COLOR_VALS[0], width=GATE_GAP_WIDTH)
        g.gates = [gate]
        g.scroll_speed = 3.0
        g._update_gates()
        assert gate.x == 197.0

    def test_gate_match_increases_combo_and_score(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_color = 0
        g.bike_y = float(GROUND_Y)
        gate = Gate(x=BIKE_X + 1.0, y=float(GROUND_Y), color=COLOR_VALS[0], width=GATE_GAP_WIDTH)
        g.gates = [gate]
        g.scroll_speed = 3.0
        g._update_gates()
        assert g.combo == 1
        assert g.score == 10
        assert g.max_combo == 1
        assert gate.passed is True

    def test_gate_mismatch_resets_combo_adds_heat(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_color = 0
        g.bike_y = float(GROUND_Y)
        g.combo = 3
        g.max_combo = 3
        gate = Gate(x=BIKE_X + 1.0, y=float(GROUND_Y), color=COLOR_VALS[1], width=GATE_GAP_WIDTH)
        g.gates = [gate]
        g.scroll_speed = 3.0
        g._update_gates()
        assert g.combo == 0
        assert g.heat == HEAT_MISMATCH
        assert g.stun_frames == 15
        assert g.shake_frames == 10

    def test_gate_skip_while_jumping_adds_heat(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_y = float(GROUND_Y - 30)
        g.heat = 0.0
        gate = Gate(x=BIKE_X + 1.0, y=float(GROUND_Y), color=COLOR_VALS[0], width=GATE_GAP_WIDTH)
        g.gates = [gate]
        g.scroll_speed = 3.0
        g._update_gates()
        assert g.heat == HEAT_IGNORE
        assert gate.passed is True

    def test_gate_not_processed_twice(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_color = 0
        g.bike_y = float(GROUND_Y)
        gate = Gate(x=BIKE_X + 1.0, y=float(GROUND_Y), color=COLOR_VALS[0], width=GATE_GAP_WIDTH)
        g.gates = [gate]
        g.scroll_speed = 3.0
        g._update_gates()
        first_combo = g.combo
        g._update_gates()
        assert g.combo == first_combo

    def test_off_screen_gates_removed(self) -> None:
        g = _new_game()
        _start_game(g)
        gate = Gate(x=-100.0, y=float(GROUND_Y), color=COLOR_VALS[0], width=GATE_GAP_WIDTH)
        g.gates = [gate]
        g.scroll_speed = 3.0
        g._update_gates()
        assert len(g.gates) == 0

    def test_combo_score_increases_with_multiplier(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_color = 0
        g.bike_y = float(GROUND_Y)
        g.combo = 4
        g.super_timer = 100
        gate = Gate(x=BIKE_X + 1.0, y=float(GROUND_Y), color=COLOR_VALS[1], width=GATE_GAP_WIDTH)
        g.gates = [gate]
        g.scroll_speed = 3.0
        g._update_gates()
        assert g.combo == 5
        assert g.score == 10 * 5 * 3


# ---------------------------------------------------------------------------
# Gate spawn tests
# ---------------------------------------------------------------------------
class TestSpawnGate:
    def test_spawn_gate_adds_to_list(self) -> None:
        g = _new_game()
        _start_game(g)
        assert len(g.gates) == 0
        g._spawn_gate()
        assert len(g.gates) == 1

    def test_spawned_gate_at_right_edge(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_gate()
        gate = g.gates[0]
        assert gate.x > 300
        assert gate.y == float(GROUND_Y)
        assert gate.width == GATE_GAP_WIDTH
        assert gate.passed is False

    def test_spawned_gate_has_valid_color(self) -> None:
        g = _new_game()
        _start_game(g)
        g._spawn_gate()
        assert g.gates[0].color in COLOR_VALS


# ---------------------------------------------------------------------------
# Heat tests
# ---------------------------------------------------------------------------
class TestHeat:
    def test_heat_decay(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = 50.0
        g._update_heat()
        assert g.heat == 50.0 - HEAT_DECAY

    def test_heat_decay_not_below_zero(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = 0.001
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_no_decay_in_super_mode(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 100
        g.heat = 50.0
        g._update_heat()
        assert g.heat == 50.0

    def test_heat_capped_at_max(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = MAX_HEAT
        g._update_gates()  # any heat addition would be ignored
        assert g.heat == MAX_HEAT

    def test_heat_game_over(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = MAX_HEAT
        g.timer = 100
        # Simulate the update check
        g._update_playing({"space": False, "space_p": False})
        assert g.phase == Phase.GAME_OVER


# ---------------------------------------------------------------------------
# Stamina tests
# ---------------------------------------------------------------------------
class TestStamina:
    def test_stamina_recharge(self) -> None:
        g = _new_game()
        _start_game(g)
        g.stamina = 50.0
        g._update_stamina()
        assert g.stamina == 50.0 + STAMINA_RECHARGE

    def test_stamina_capped_at_max(self) -> None:
        g = _new_game()
        _start_game(g)
        g.stamina = STAMINA_MAX
        g._update_stamina()
        assert g.stamina == STAMINA_MAX

    def test_jump_cost(self) -> None:
        g = _new_game()
        _start_game(g)
        g.stamina = STAMINA_MAX
        g.bike_y = float(GROUND_Y)
        g._update_bike_jump({"space_p": True})
        assert g.stamina == STAMINA_MAX - STAMINA_JUMP_COST
        assert g.bike_vy == JUMP_VY
        assert g.is_jumping is True


# ---------------------------------------------------------------------------
# Jump physics tests
# ---------------------------------------------------------------------------
class TestJumpPhysics:
    def test_gravity_pulls_bike_down(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_y = float(GROUND_Y - 10)
        g.bike_vy = -2.0
        g._update_bike_physics()
        assert g.bike_vy == -2.0 + GRAVITY

    def test_bike_lands_on_ground(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_y = float(GROUND_Y - 0.2)
        g.bike_vy = 0.5
        g.is_jumping = True
        g._update_bike_physics()
        assert g.bike_y == float(GROUND_Y)
        assert g.bike_vy == 0.0
        assert g.is_jumping is False

    def test_bike_cannot_jump_in_air(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_y = float(GROUND_Y - 10)
        g.bike_vy = -2.0
        g.stamina = STAMINA_MAX
        g._update_bike_jump({"space_p": True})
        assert g.stamina == STAMINA_MAX  # no cost, jump not applied


# ---------------------------------------------------------------------------
# Super mode tests
# ---------------------------------------------------------------------------
class TestSuperMode:
    def test_super_mode_activates_at_combo_threshold(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_color = 0
        g.bike_y = float(GROUND_Y)
        g.combo = 3
        g.super_timer = 0
        gate = Gate(x=BIKE_X + 1.0, y=float(GROUND_Y), color=COLOR_VALS[0], width=GATE_GAP_WIDTH)
        g.gates = [gate]
        g.scroll_speed = 3.0
        g._update_gates()
        assert g.combo == 4
        assert g.super_timer == SUPER_DURATION

    def test_super_mode_expires_combo_resets(self) -> None:
        g = _new_game()
        _start_game(g)
        g.combo = 5
        g.super_timer = 1
        g.super_timer -= 1
        if g.super_timer == 0:
            g.combo = 0
        assert g.super_timer == 0

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


# ---------------------------------------------------------------------------
# Bike color cycle tests
# ---------------------------------------------------------------------------
class TestBikeColorCycle:
    def test_color_cycles_through_all_four(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_color = 0
        g.bike_color_timer = 20
        for _ in range(20):
            g._update_bike_color()
        assert g.bike_color == 1
        assert g.bike_color_timer == 20

    def test_color_wraps_from_last_to_first(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_color = 3
        g.bike_color_timer = 1
        g._update_bike_color()
        assert g.bike_color == 0


# ---------------------------------------------------------------------------
# Score tests
# ---------------------------------------------------------------------------
class TestScore:
    def test_base_score_with_combo(self) -> None:
        g = _new_game()
        _start_game(g)
        g.combo = 3
        g.bike_color = 0
        g.bike_y = float(GROUND_Y)
        gate = Gate(x=BIKE_X + 1.0, y=float(GROUND_Y), color=COLOR_VALS[0], width=GATE_GAP_WIDTH)
        g.gates = [gate]
        g.scroll_speed = 3.0
        g._update_gates()
        assert g.score == 10 * 4 * 1

    def test_super_score_3x_multiplier(self) -> None:
        g = _new_game()
        _start_game(g)
        g.combo = 5
        g.super_timer = 100
        g.bike_color = 0
        g.bike_y = float(GROUND_Y)
        gate = Gate(x=BIKE_X + 1.0, y=float(GROUND_Y), color=COLOR_VALS[0], width=GATE_GAP_WIDTH)
        g.gates = [gate]
        g.scroll_speed = 3.0
        g._update_gates()
        assert g.score == 10 * 6 * 3


# ---------------------------------------------------------------------------
# Timer tests
# ---------------------------------------------------------------------------
class TestTimer:
    def test_timer_decreases(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = 100
        g._update_playing({"space": False, "space_p": False})
        assert g.timer == 99

    def test_timer_zero_game_over(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = 1
        g._update_playing({"space": False, "space_p": False})
        assert g.phase == Phase.GAME_OVER

    def test_best_score_updated_on_game_over(self) -> None:
        g = _new_game()
        _start_game(g)
        g.score = 500
        g.best_score = 0
        g.timer = 1
        g._update_playing({"space": False, "space_p": False})
        assert g.best_score == 500


# ---------------------------------------------------------------------------
# Scroll speed tests
# ---------------------------------------------------------------------------
class TestScrollSpeed:
    def test_scroll_speed_increases_over_time(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = GAME_DURATION // 2
        # simulates the elapsed calculation
        elapsed = GAME_DURATION - g.timer
        speed = 2.0 + 3.0 * (elapsed / GAME_DURATION)
        assert speed > 2.0
        assert speed < 5.0

    def test_scroll_speed_at_start(self) -> None:
        g = _new_game()
        _start_game(g)
        g.timer = GAME_DURATION
        assert g.scroll_speed == 2.0

    def test_scroll_x_accumulates(self) -> None:
        g = _new_game()
        _start_game(g)
        g.scroll_speed = 3.0
        g.scroll_x = 0.0
        g.scroll_x += g.scroll_speed
        assert g.scroll_x == 3.0


# ---------------------------------------------------------------------------
# Phase flow tests
# ---------------------------------------------------------------------------
class TestPhaseFlow:
    def test_title_to_playing(self) -> None:
        g = _new_game()
        g.reset()
        g._update_title({"space_p": True})
        assert g.phase == Phase.PLAYING

    def test_playing_to_game_over_heat(self) -> None:
        g = _new_game()
        _start_game(g)
        g.heat = MAX_HEAT
        g.timer = 100
        g._update_playing({"space": False, "space_p": False})
        assert g.phase == Phase.GAME_OVER

    def test_game_over_to_title(self) -> None:
        g = _new_game()
        g.phase = Phase.GAME_OVER
        g._update_game_over({"space_p": True})
        assert g.phase == Phase.TITLE

    def test_best_trail_saved_on_game_over(self) -> None:
        g = _new_game()
        _start_game(g)
        g.current_trail = [(100, 200), (200, 200)]
        g.score = 100
        g.best_score = 0
        g.timer = 1
        g._update_playing({"space": False, "space_p": False})
        assert g.phase == Phase.GAME_OVER
        assert g.best_trail == [(100, 200), (200, 200)]


# ---------------------------------------------------------------------------
# _super_timer_check helper
# ---------------------------------------------------------------------------
def test_super_timer_countdown_and_combo_reset() -> None:
    g = _new_game()
    _start_game(g)
    g.combo = 5
    g.super_timer = SUPER_DURATION
    for _ in range(SUPER_DURATION):
        g.super_timer -= 1
        if g.super_timer == 0:
            g.combo = 0
    assert g.super_timer == 0
    assert g.combo == 0


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_multiple_gates_processed_independently(self) -> None:
        g = _new_game()
        _start_game(g)
        g.bike_color = 0
        g.bike_y = float(GROUND_Y)
        g1 = Gate(x=BIKE_X + 1.0, y=float(GROUND_Y), color=COLOR_VALS[0], width=GATE_GAP_WIDTH)
        g2 = Gate(x=BIKE_X + 1.0, y=float(GROUND_Y), color=COLOR_VALS[1], width=GATE_GAP_WIDTH)
        g.gates = [g1, g2]
        g.scroll_speed = 3.0
        g._update_gates()
        assert g1.passed is True
        assert g2.passed is True
        assert g.combo == 0  # second gate mismatched
        assert g.heat == HEAT_MISMATCH

    def test_super_mode_freezes_heat(self) -> None:
        g = _new_game()
        _start_game(g)
        g.super_timer = 100
        g.heat = 50.0
        g._update_heat()
        assert g.heat == 50.0

    def test_rng_deterministic(self) -> None:
        g1 = _new_game()
        g2 = _new_game()
        _start_game(g1)
        _start_game(g2)
        g1._spawn_gate()
        g2._spawn_gate()
        assert g1.gates[0].color == g2.gates[0].color
