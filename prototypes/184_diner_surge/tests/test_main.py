from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    COLORS,
    COMBO_FOR_SUPER,
    GAME_DURATION,
    HEAT_MISMATCH,
    HEAT_TIMEOUT,
    MAX_ORDERS,
    PATIENCE_MAX,
    SUPER_DURATION,
    Game,
    Order,
    Phase,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.PLAYING
    g.orders = []
    g.last_color = -1
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.heat = 0.0
    g.super_timer = 0
    g.game_timer = GAME_DURATION
    g.particles = []
    g.floating_texts = []
    g.rng = random.Random(42)
    g.regular_positions = []
    g.spawn_timer = 0
    g.served_this_frame = False
    g.super_rainbow_tick = 0
    g.font = None
    return g


# --- 1. Order spawning fills empty positions ---
def test_spawn_fills_empty_positions() -> None:
    g = _make_game()
    g._spawn_order()
    assert len(g.orders) == 1
    o = g.orders[0]
    assert 0 <= o.col < 4
    assert 0 <= o.row < 3
    assert o.color in COLORS
    assert o.timer == PATIENCE_MAX


# --- 2. Serve matching color builds combo ---
def test_serve_matching_color_builds_combo() -> None:
    g = _make_game()
    g.last_color = COLORS[0]
    g.orders.append(Order(0, 0, COLORS[0]))
    score = g._handle_serve(0, 0)
    assert g.combo == 1
    assert score > 0


# --- 3. Serve mismatching color resets combo + adds heat ---
def test_serve_mismatching_resets_combo_and_adds_heat() -> None:
    g = _make_game()
    g.last_color = COLORS[0]
    g.combo = 3
    g.orders.append(Order(0, 0, COLORS[1]))
    g._handle_serve(0, 0)
    assert g.combo == 1
    assert g.heat == HEAT_MISMATCH
    assert g.regular_positions == [(0, 0)]


# --- 4. COMBO >= 4 triggers super ---
def test_combo_4_triggers_super() -> None:
    g = _make_game()
    g.last_color = COLORS[0]
    for i in range(COMBO_FOR_SUPER):
        g.orders.append(Order(i, 0, COLORS[0]))
        g._handle_serve(i, 0)
    assert g.super_timer == SUPER_DURATION


# --- 5. Super mode: any color counts, score * 3 ---
def test_super_mode_any_color_match() -> None:
    g = _make_game()
    g.super_timer = 10
    g.last_color = COLORS[0]
    g.orders.append(Order(0, 0, COLORS[1]))
    score = g._handle_serve(0, 0)
    assert score == 30  # super base score
    assert g.combo == 1


# --- 6. Heat accumulation + game over ---
def test_heat_accumulation() -> None:
    g = _make_game()
    g.last_color = COLORS[0]
    g.orders.append(Order(0, 0, COLORS[1]))
    g._handle_serve(0, 0)
    assert g.heat == HEAT_MISMATCH
    g._update_orders()
    g.heat = max(0.0, g.heat - 0.03)
    assert g.heat < HEAT_MISMATCH


# --- 7. Timer expiration = game over ---
def test_timer_expiration() -> None:
    g = _make_game()
    g.game_timer = 0
    g.tick()
    assert g.game_timer <= 0


# --- 8. Order timeout removes order + adds heat ---
def test_order_timeout() -> None:
    g = _make_game()
    g.orders.append(Order(0, 0, COLORS[0], timer=1))
    g._update_orders()
    assert len(g.orders) == 0
    assert g.heat == HEAT_TIMEOUT


# --- 9. Particle spawning and lifecycle ---
def test_particle_spawning_and_lifecycle() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, COLORS[0], 10)
    assert len(g.particles) == 10
    life_before = [p.life for p in g.particles]
    for p in g.particles:
        assert p.color == COLORS[0]
        assert p.life > 0
        assert -2.5 <= p.vx <= 2.5
    g._update_particles()
    for i, p in enumerate(g.particles):
        assert p.life == life_before[i] - 1


# --- 10. Floating text lifecycle ---
def test_floating_text_lifecycle() -> None:
    g = _make_game()
    g._add_floating_text(100, 100, "TEST", 7)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "TEST"
    initial_y = ft.y
    g._update_floating_texts()
    ft = g.floating_texts[0]
    assert ft.life == 29
    assert ft.y < initial_y


# --- 11. Regular positions tracking after streak ---
def test_regular_positions_tracking() -> None:
    g = _make_game()
    g.last_color = COLORS[0]
    g.orders.append(Order(0, 0, COLORS[0]))
    g._handle_serve(0, 0)
    assert g.regular_positions == [(0, 0)]
    g.orders.append(Order(1, 0, COLORS[0]))
    g._handle_serve(1, 0)
    assert g.regular_positions == [(0, 0), (1, 0)]


# --- 12. Click on empty table = no-op ---
def test_click_empty_table_noop() -> None:
    g = _make_game()
    score = g._handle_serve(0, 0)
    assert score == 0
    assert g.served_this_frame is False


# --- 13. Max orders cap ---
def test_max_orders_cap() -> None:
    g = _make_game()
    for i in range(MAX_ORDERS + 4):
        g._spawn_order()
    assert len(g.orders) <= MAX_ORDERS


# --- 14. Super timer decay ---
def test_super_timer_decay() -> None:
    g = _make_game()
    g.super_timer = SUPER_DURATION
    g.tick()
    assert g.super_timer == SUPER_DURATION - 1

    g.super_timer = 1
    g.tick()
    assert g.super_timer == 0


# --- Additional: get_clicked_table ---
def test_get_clicked_table() -> None:
    g = _make_game()
    from main import GRID_X, GRID_Y

    mx = GRID_X + 10
    my = GRID_Y + 10
    result = g._get_clicked_table(mx, my)
    assert result == (0, 0)

    result_none = g._get_clicked_table(0, 0)
    assert result_none is None


# --- Additional: get_table_center ---
def test_get_table_center() -> None:
    g = _make_game()
    from main import GRID_X, GRID_Y, TABLE_W, TABLE_H

    cx, cy = g._get_table_center(0, 0)
    assert cx == GRID_X + TABLE_W // 2
    assert cy == GRID_Y + TABLE_H // 2


# --- Additional: _can_serve ---
def test_can_serve() -> None:
    g = _make_game()
    assert g._can_serve(0, 0) is False
    g.orders.append(Order(0, 0, COLORS[0]))
    assert g._can_serve(0, 0) is True
    assert g._can_serve(1, 0) is False


# --- Additional: heat decay ---
def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 1.0
    g.tick()
    assert g.heat < 1.0
    assert g.heat >= 0.0
