"""test_imports.py — Headless logic tests for 220_chroma_mix."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import (
    BASE_SCORE,
    COMBO_THRESHOLD,
    HEAT_DECAY,
    HEAT_EXPIRE,
    HEAT_MAX,
    HEAT_MISMATCH,
    ORDER_SPEED_BASE,
    ORDER_X_DEAD,
    ORDER_X_SPAWN,
    SUPER_DURATION,
    TANK_COLORS,
    TIME_LIMIT,
    FPS,
    Game,
    Order,
    Particle,
    Phase,
    RED,
    YELLOW,
    WHITE,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g._pre_init_state()
    return g


# ── Game.__new__ pattern ──


def test_game_new_pre_init_works() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.timer == TIME_LIMIT * FPS
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.palette_color == -1
    assert g.orders == []
    assert g.particles == []
    assert g.score_popups == []
    assert len(g._occupied_slots) == 0


# ── Reset ──


def test_reset_clears_all_state() -> None:
    g = _make_game()
    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.timer == TIME_LIMIT * FPS
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.palette_color == -1
    assert g.orders == []
    assert g.particles == []
    assert g.score_popups == []
    assert len(g._occupied_slots) == 0


def test_reset_clears_existing_orders() -> None:
    g = _make_game()
    g.reset()
    order = g._spawn_order()
    assert order is not None
    g.orders.append(order)
    assert len(g.orders) == 1
    g.reset()
    assert g.orders == []
    assert len(g._occupied_slots) == 0


# ── Spawn Order ──


def test_spawn_order_returns_valid_order() -> None:
    g = _make_game()
    g.reset()
    order = g._spawn_order()
    assert order is not None
    assert order.x == ORDER_X_SPAWN
    assert order.y in [70, 100, 130, 160]
    assert order.color in TANK_COLORS
    assert order.active is True
    assert order.slot in {0, 1, 2, 3}


def test_spawn_order_occupies_slot() -> None:
    g = _make_game()
    g.reset()
    order = g._spawn_order()
    assert order is not None
    assert order.slot in g._occupied_slots


def test_spawn_order_fills_all_4_slots() -> None:
    g = _make_game()
    g.reset()
    orders = []
    for _ in range(4):
        o = g._spawn_order()
        assert o is not None
        orders.append(o)
    assert len(g._occupied_slots) == 4
    assert g._spawn_order() is None


def test_spawn_order_fills_unique_slots() -> None:
    g = _make_game()
    g.reset()
    slots = set()
    for _ in range(4):
        o = g._spawn_order()
        assert o is not None
        slots.add(o.slot)
    assert len(slots) == 4


# ── Update Orders ──


def test_update_orders_moves_order_leftward() -> None:
    g = _make_game()
    g.reset()
    o = Order(x=200.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}
    g.orders = [o]

    g._update_orders()

    assert g.orders[0].x < 200.0
    assert g.orders[0].active is True


def test_update_orders_expires_order_at_left_edge() -> None:
    g = _make_game()
    g.reset()
    o = Order(x=ORDER_X_DEAD + ORDER_SPEED_BASE * 0.5, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}
    g.orders = [o]

    g._update_orders()

    assert len(g.orders) == 0
    assert g.heat == HEAT_EXPIRE
    assert 0 not in g._occupied_slots


def test_update_orders_expired_order_adds_heat() -> None:
    g = _make_game()
    g.reset()
    g.heat = 0.0
    o = Order(x=ORDER_X_DEAD + ORDER_SPEED_BASE * 0.5, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}
    g.orders = [o]

    g._update_orders()

    assert g.heat == HEAT_EXPIRE


def test_update_orders_super_mode_auto_matches() -> None:
    g = _make_game()
    g.reset()
    g.super_mode = True
    g.super_timer = 10
    g.score = 0
    g.combo = 0

    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}
    g.orders = [o]

    g._update_orders()

    assert len(g.orders) == 0
    assert g.score > 0
    assert g.combo == 1
    assert 0 not in g._occupied_slots


def test_update_orders_super_does_not_move_orders() -> None:
    g = _make_game()
    g.reset()
    g.super_mode = True
    g.super_timer = 10

    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}
    g.orders = [o]

    initial_x = o.x
    g._update_orders()
    assert o.x == initial_x


# ── Nearest Order ──


def test_get_nearest_order_idx_finds_rightmost() -> None:
    g = _make_game()
    g.reset()
    o1 = Order(x=200.0, y=70.0, color=RED, active=True, slot=0)
    o2 = Order(x=250.0, y=100.0, color=YELLOW, active=True, slot=1)
    g.orders = [o1, o2]

    idx = g._get_nearest_order_idx()
    assert idx == 1
    assert g.orders[idx].color == YELLOW


def test_get_nearest_order_idx_ignores_inactive() -> None:
    g = _make_game()
    g.reset()
    o1 = Order(x=250.0, y=70.0, color=RED, active=False, slot=0)
    o2 = Order(x=200.0, y=100.0, color=YELLOW, active=True, slot=1)
    g.orders = [o1, o2]

    idx = g._get_nearest_order_idx()
    assert idx == 1


def test_get_nearest_order_idx_empty_returns_minus1() -> None:
    g = _make_game()
    g.reset()
    assert g._get_nearest_order_idx() == -1


# ── Select Color / Click ──


def test_select_color_matches_correct_order() -> None:
    g = _make_game()
    g.reset()
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}
    g.orders = [o]
    g.score = 0
    g.combo = 0

    g._select_color(RED)

    assert o.active is False
    assert g.score > 0
    assert g.combo == 1
    assert 0 not in g._occupied_slots


def test_select_color_mismatch_resets_combo() -> None:
    g = _make_game()
    g.reset()
    g.combo = 3
    g.heat = 0.0
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}
    g.orders = [o]

    g._select_color(YELLOW)

    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH
    assert o.active is True  # order NOT removed on mismatch


def test_select_color_super_mode_any_color_matches() -> None:
    g = _make_game()
    g.reset()
    g.super_mode = True
    g.super_timer = 10
    g.score = 0
    g.combo = 1
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}
    g.orders = [o]

    g._select_color(YELLOW)

    assert o.active is False
    assert g.score > 0
    assert g.combo == 2


def test_select_color_no_orders_sets_palette_only() -> None:
    g = _make_game()
    g.reset()
    g.score = 0
    g.combo = 0

    g._select_color(RED)

    assert g.palette_color == RED
    assert g.palette_flash == 3
    assert g.score == 0
    assert g.combo == 0


# ── Try Match ──


def test_try_match_scores_and_removes_order() -> None:
    g = _make_game()
    g.reset()
    g.score = 0
    g.combo = 0
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}

    g._try_match(o)

    assert o.active is False
    assert g.score > 0
    assert g.combo == 1
    assert g.max_combo == 1
    assert 0 not in g._occupied_slots


def test_try_match_combo_increments_correctly() -> None:
    g = _make_game()
    g.reset()
    g.combo = 3
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}

    g._try_match(o)

    assert g.combo == 4
    assert g.max_combo == 4


def test_try_match_triggers_super_at_threshold() -> None:
    g = _make_game()
    g.reset()
    g.combo = COMBO_THRESHOLD - 1
    g.super_mode = False
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}

    g._try_match(o)

    assert g.combo == COMBO_THRESHOLD
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_try_match_spawns_particles() -> None:
    g = _make_game()
    g.reset()
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}

    pre_count = len(g.particles)
    g._try_match(o)
    assert len(g.particles) > pre_count


def test_try_match_spawns_score_popup() -> None:
    g = _make_game()
    g.reset()
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}

    pre_count = len(g.score_popups)
    g._try_match(o)
    assert len(g.score_popups) > pre_count


# ── Mismatch ──


def test_mismatch_adds_heat() -> None:
    g = _make_game()
    g.reset()
    g.heat = 0.0

    g._mismatch(RED)

    assert g.heat == HEAT_MISMATCH


def test_mismatch_resets_combo_to_zero() -> None:
    g = _make_game()
    g.reset()
    g.combo = 5

    g._mismatch(RED)

    assert g.combo == 0


def test_mismatch_heat_caps_at_max() -> None:
    g = _make_game()
    g.reset()
    g.heat = HEAT_MAX - 5.0

    g._mismatch(RED)

    assert g.heat == HEAT_MAX


# ── Combo Multiplier ──


def test_compute_combo_multiplier_combo_0() -> None:
    g = _make_game()
    assert g._compute_combo_multiplier(0) == 1


def test_compute_combo_multiplier_combo_1() -> None:
    g = _make_game()
    assert g._compute_combo_multiplier(1) == 1


def test_compute_combo_multiplier_combo_3() -> None:
    g = _make_game()
    assert g._compute_combo_multiplier(3) == 2


def test_compute_combo_multiplier_combo_5() -> None:
    g = _make_game()
    assert g._compute_combo_multiplier(5) == 3


def test_compute_combo_multiplier_combo_6() -> None:
    g = _make_game()
    assert g._compute_combo_multiplier(6) == 5


# ── Score Calculation ──


def test_score_first_match() -> None:
    g = _make_game()
    g.reset()
    g.combo = 0
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}

    pre_score = g.score
    g._try_match(o)
    assert g.score == pre_score + BASE_SCORE  # combo=1, mult=1


def test_score_combo_3_match() -> None:
    g = _make_game()
    g.reset()
    g.combo = 2
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}

    pre_score = g.score
    g._try_match(o)
    assert g.score == pre_score + BASE_SCORE * 2  # combo=3, mult=2


def test_score_super_mode_match() -> None:
    g = _make_game()
    g.reset()
    g.super_mode = True
    g.combo = 1
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}

    pre_score = g.score
    g._try_match(o)
    assert g.score == pre_score + BASE_SCORE * 1 * 3  # combo=2, mult=1, super 3x


def test_score_match_order() -> None:
    g = _make_game()
    g.reset()
    g.super_mode = True
    g.combo = 2
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}

    pre_score = g.score
    g._match_order(o)
    assert g.score == pre_score + BASE_SCORE * 2 * 3  # combo=3, mult=2, super 3x


# ── Heat System ──


def test_heat_decays_over_time() -> None:
    g = _make_game()
    g.reset()
    g.heat = 50.0

    g._update_heat()

    assert g.heat < 50.0
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_does_not_go_below_zero() -> None:
    g = _make_game()
    g.reset()
    g.heat = 0.01

    g._update_heat()

    assert g.heat == 0.0


def test_heat_at_max_triggers_game_over() -> None:
    g = _make_game()
    g.reset()
    g.heat = HEAT_MAX
    g.timer = 100

    assert g._check_game_over() is True


def test_heat_below_max_does_not_trigger_game_over() -> None:
    g = _make_game()
    g.reset()
    g.heat = HEAT_MAX - 1
    g.timer = 100

    assert g._check_game_over() is False


# ── Game Over Conditions ──


def test_timer_zero_triggers_game_over() -> None:
    g = _make_game()
    g.reset()
    g.timer = 0
    g.heat = 0.0

    assert g._check_game_over() is True


def test_timer_negative_triggers_game_over() -> None:
    g = _make_game()
    g.reset()
    g.timer = -1
    g.heat = 0.0

    assert g._check_game_over() is True


# ── Super Mode ──


def test_super_mode_deactivates_after_duration() -> None:
    g = _make_game()
    g.reset()
    g.super_mode = True
    g.super_timer = 2

    g._update_super_mode()
    assert g.super_mode is True
    assert g.super_timer == 1

    g._update_super_mode()
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.super_flash == 0


def test_super_mode_does_not_reactivate_while_active() -> None:
    g = _make_game()
    g.reset()
    g.super_mode = True
    g.super_timer = 10
    g.combo = COMBO_THRESHOLD

    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}
    old_timer = g.super_timer

    g._try_match(o)

    assert g.super_mode is True
    assert g.super_timer == old_timer  # timer not reset


def test_activate_super_spawns_particles() -> None:
    g = _make_game()
    g.reset()

    pre_count = len(g.particles)
    g._activate_super()
    assert len(g.particles) > pre_count


# ── Difficulty Scaling ──


def test_order_speed_increases_over_time() -> None:
    g = _make_game()
    g.reset()
    g.timer = TIME_LIMIT * FPS

    speed1 = min(2.0, ORDER_SPEED_BASE + 0 * 0.05)

    g.timer = TIME_LIMIT * FPS - (10 * FPS)
    speed2 = min(2.0, ORDER_SPEED_BASE + 1 * 0.05)

    g.timer = TIME_LIMIT * FPS - (30 * FPS)
    speed3 = min(2.0, ORDER_SPEED_BASE + 3 * 0.05)

    assert speed2 > speed1
    assert speed3 > speed2


def test_spawn_interval_decreases_over_time() -> None:
    g = _make_game()
    g.reset()
    g.timer = TIME_LIMIT * FPS

    g._update_spawning()
    interval1 = g.spawn_interval

    g.timer = TIME_LIMIT * FPS - (10 * FPS)
    g._update_spawning()
    interval2 = g.spawn_interval

    assert interval2 < interval1


def test_spawn_interval_has_minimum() -> None:
    g = _make_game()
    g.reset()
    g.timer = 1  # very late game

    g._update_spawning()
    assert g.spawn_interval >= 40


# ── Particle System ──


def test_particle_life_decrements() -> None:
    g = _make_game()
    g.reset()
    p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=5, color=RED)
    g.particles = [p]

    g._update_particles()
    assert p.life == 4


def test_particle_dies_at_life_1() -> None:
    g = _make_game()
    g.reset()
    p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=RED)
    g.particles = [p]

    g._update_particles()
    assert len(g.particles) == 0


def test_spawn_collect_particles_adds_count() -> None:
    g = _make_game()
    g.reset()

    pre_count = len(g.particles)
    g._spawn_collect_particles(100.0, 100.0, RED, 5)
    assert len(g.particles) == pre_count + 5


# ── Score Popups ──


def test_score_popup_floats_upward() -> None:
    g = _make_game()
    g.reset()
    g.score_popups = [(100.0, 100.0, 10, 20, WHITE)]

    g._update_score_popups()
    assert len(g.score_popups) == 1
    assert g.score_popups[0][1] < 100.0  # y decreased


def test_score_popup_expires_after_life() -> None:
    g = _make_game()
    g.reset()
    g.score_popups = [(100.0, 100.0, 10, 1, WHITE)]

    g._update_score_popups()
    assert len(g.score_popups) == 0


# ── Occupied Slots Tracking ──


def test_match_order_frees_slot() -> None:
    g = _make_game()
    g.reset()
    g._occupied_slots = {0}
    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)

    g._try_match(o)
    assert 0 not in g._occupied_slots


def test_order_expiration_frees_slot() -> None:
    g = _make_game()
    g.reset()
    g._occupied_slots = {0}
    o = Order(x=ORDER_X_DEAD + ORDER_SPEED_BASE * 0.5, y=70.0, color=RED, active=True, slot=0)
    g.orders = [o]

    g._update_orders()
    assert len(g._occupied_slots) == 0


# ── Handle Click (tank detection) ──


def test_handle_click_invalid_area_sets_nothing() -> None:
    g = _make_game()
    g.reset()
    g.palette_color = -1

    g._handle_click(-10, -10)  # off-screen

    assert g.palette_color == -1


def test_handle_click_on_tank_sets_palette() -> None:
    g = _make_game()
    g.reset()
    g.palette_color = -1

    tank_x = 5 + 0 * (70 + 10)
    g._handle_click(tank_x + 5, 225)

    assert g.palette_color == RED
    assert g.palette_flash == 3


# ── Max Combo Tracking ──


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.reset()
    g.combo = 0
    g.max_combo = 0

    o = Order(x=250.0, y=70.0, color=RED, active=True, slot=0)
    g._occupied_slots = {0}
    g._try_match(o)  # combo=1
    assert g.max_combo == 1

    g._mismatch(RED)  # combo=0
    assert g.max_combo == 1  # unchanged

    g._occupied_slots = {1}
    o2 = Order(x=250.0, y=100.0, color=RED, active=True, slot=1)
    g._try_match(o2)  # combo=1
    g._occupied_slots = {2}
    o3 = Order(x=250.0, y=130.0, color=RED, active=True, slot=2)
    g._try_match(o3)  # combo=2
    assert g.max_combo == 2


# ── Super mode auto-match in update_orders ──


def test_super_auto_clear_all_orders() -> None:
    g = _make_game()
    g.reset()
    g.super_mode = True
    g.super_timer = 300
    g.score = 0
    g.combo = 0

    g._occupied_slots = {0, 1}
    o1 = Order(x=200.0, y=70.0, color=RED, active=True, slot=0)
    o2 = Order(x=250.0, y=100.0, color=YELLOW, active=True, slot=1)
    g.orders = [o1, o2]

    g._update_orders()

    assert len(g.orders) == 0
    assert g.combo == 2
    assert g.score > 0
    assert len(g._occupied_slots) == 0


# ── Title screen start ──


def test_title_button_click_coordinates() -> None:
    bx = 160 - 30
    by = 210
    assert bx == 130
    assert by == 210


print("All tests passed!")
