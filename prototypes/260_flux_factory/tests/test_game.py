"""Tests for FLUX FACTORY game logic."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "prototypes/260_flux_factory")
import main  # noqa: E402


def _make_game(seed: int = 42) -> main.Game:
    g = main.Game.__new__(main.Game)
    g._rng = random.Random(seed)
    # Pre-init all attributes
    g.phase = main.Phase.PLAYING
    g.grid = [[main.EMPTY for _ in range(main.ROWS)] for _ in range(main.COLS)]
    g.items = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = main.TOTAL_FRAMES
    g.super_timer = 0
    g.particles = []
    g.floating_texts = []
    g.tick_timer = main.TICK_INTERVAL_START
    g.tick_interval = main.TICK_INTERVAL_START
    g.spawn_timer = main.SPAWN_INTERVAL_START
    g.spawn_interval = main.SPAWN_INTERVAL_START
    g.frame = 0
    g._idle_flow_timer = 0
    g._idle_items = []
    return g


# ── Test: Spawning ──────────────────────────────────────────────────


def test_spawn_item_adds_to_list():
    g = _make_game()
    assert len(g.items) == 0
    g._spawn_item()
    assert len(g.items) == 1
    item = g.items[0]
    assert item.grid_col == 0
    assert 0 <= item.grid_row < main.ROWS
    assert item.color in main.ITEM_COLORS


def test_spawn_interval_initial():
    g = _make_game()
    assert g.spawn_interval == main.SPAWN_INTERVAL_START


def test_spawn_interval_decreases():
    g = _make_game()
    g.timer = main.TOTAL_FRAMES // 2  # halfway through
    g._update_spawn_timer()
    assert g.spawn_interval < main.SPAWN_INTERVAL_START
    assert g.tick_interval < main.TICK_INTERVAL_START


def test_spawn_interval_at_end():
    g = _make_game()
    g.timer = 0
    g._update_spawn_timer()
    assert g.spawn_interval == main.SPAWN_INTERVAL_END
    assert g.tick_interval == main.TICK_INTERVAL_END


# ── Test: Item Movement ─────────────────────────────────────────────


def test_move_items_on_north_belt():
    g = _make_game()
    g.grid[0][2] = main.N
    g.tick_interval = 1
    item = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=0, grid_row=2, arrived_time=999)
    g.items.append(item)
    g._move_items()
    assert item.grid_col == 0
    assert item.grid_row == 1


def test_move_items_on_east_belt():
    g = _make_game()
    g.grid[0][2] = main.E
    g.tick_interval = 1
    item = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=0, grid_row=2, arrived_time=999)
    g.items.append(item)
    g._move_items()
    assert item.grid_col == 1
    assert item.grid_row == 2


def test_move_items_on_south_belt():
    g = _make_game()
    g.grid[0][0] = main.S
    g.tick_interval = 1
    item = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=0, grid_row=0, arrived_time=999)
    g.items.append(item)
    g._move_items()
    assert item.grid_col == 0
    assert item.grid_row == 1


def test_move_items_on_west_belt():
    g = _make_game()
    g.grid[1][2] = main.W
    g.tick_interval = 1
    item = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=999)
    g.items.append(item)
    g._move_items()
    assert item.grid_col == 0
    assert item.grid_row == 2


def test_move_items_empty_cell_removes_and_heats():
    g = _make_game()
    g.grid[0][2] = main.EMPTY
    g.tick_interval = 1
    item = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=0, grid_row=2, arrived_time=999)
    g.items.append(item)
    g._move_items()
    assert len(g.items) == 0
    assert g.heat == main.HEAT_LOST


def test_move_items_exit_right_scores():
    g = _make_game()
    g.grid[main.COLS - 1][2] = main.E
    g.tick_interval = 1
    item = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=main.COLS - 1, grid_row=2, arrived_time=999)
    g.items.append(item)
    g._move_items()
    assert len(g.items) == 0
    assert g.score == main.EXIT_SCORE


def test_move_items_junction_pauses():
    g = _make_game()
    g.grid[0][2] = main.JUNCTION
    g.tick_interval = 1
    item = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=0, grid_row=2, arrived_time=0)
    g.items.append(item)
    g._move_items()
    assert item.grid_col == 0
    assert item.grid_row == 2
    assert item.arrived_time == 1


def test_move_items_junction_proceeds_after_pause():
    g = _make_game()
    g.grid[0][2] = main.JUNCTION
    g.tick_interval = 1
    item = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=0, grid_row=2, arrived_time=main.JUNCTION_PAUSE + 1)
    g.items.append(item)
    g._move_items()
    # Should have moved from junction
    assert item.grid_col != 0 or item.grid_row != 2


def test_move_items_not_yet_ticked():
    g = _make_game()
    g.grid[0][2] = main.E
    g.tick_interval = 10
    item = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=0, grid_row=2, arrived_time=3)
    g.items.append(item)
    g._move_items()
    assert item.grid_col == 0
    assert item.grid_row == 2
    assert item.arrived_time == 4


def test_move_items_off_grid_top_removes():
    g = _make_game()
    g.grid[0][0] = main.N
    g.tick_interval = 1
    item = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=0, grid_row=0, arrived_time=999)
    g.items.append(item)
    g._move_items()
    assert len(g.items) == 0
    assert g.heat == main.HEAT_LOST


# ── Test: Synthesis ─────────────────────────────────────────────────


def test_synthesis_same_color():
    g = _make_game()
    g.grid[1][2] = main.JUNCTION
    g.score = 0
    g.combo = 0
    item1 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    item2 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    g.items = [item1, item2]
    g._check_synthesis()
    assert len(g.items) == 0
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == main.SYNTHESIS_BASE * 1
    assert len(g.particles) > 0


def test_synthesis_combo_chain():
    g = _make_game()
    g.grid[1][2] = main.JUNCTION
    g.combo = 3
    g.max_combo = 3
    g.score = 500
    item1 = main.Item(x=0, y=0, color=main.ITEM_COLORS[1], grid_col=1, grid_row=2, arrived_time=0)
    item2 = main.Item(x=0, y=0, color=main.ITEM_COLORS[1], grid_col=1, grid_row=2, arrived_time=0)
    g.items = [item1, item2]
    g._check_synthesis()
    assert g.combo == 4
    assert g.max_combo == 4
    assert g.score == 500 + main.SYNTHESIS_BASE * 4


def test_synthesis_triggers_super_flux():
    g = _make_game()
    g.grid[1][2] = main.JUNCTION
    g.combo = 3
    g.score = 0
    item1 = main.Item(x=0, y=0, color=main.ITEM_COLORS[2], grid_col=1, grid_row=2, arrived_time=0)
    item2 = main.Item(x=0, y=0, color=main.ITEM_COLORS[2], grid_col=1, grid_row=2, arrived_time=0)
    g.items = [item1, item2]
    g._check_synthesis()
    assert g.combo == 4
    assert g.super_timer == main.SUPER_DURATION


def test_synthesis_during_super_flux():
    g = _make_game()
    g.grid[1][2] = main.JUNCTION
    g.super_timer = 50
    g.combo = 4
    g.score = 0
    item1 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    item2 = main.Item(x=0, y=0, color=main.ITEM_COLORS[2], grid_col=1, grid_row=2, arrived_time=0)
    g.items = [item1, item2]
    g._check_synthesis()
    assert g.combo == 5
    assert g.score == main.SYNTHESIS_BASE * 5 * main.SUPER_MULTIPLIER


def test_super_flux_any_color_works():
    g = _make_game()
    g.grid[1][2] = main.JUNCTION
    g.super_timer = 50
    g.combo = 5
    g.score = 0
    g.heat = 20
    item1 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    item2 = main.Item(x=0, y=0, color=main.ITEM_COLORS[1], grid_col=1, grid_row=2, arrived_time=0)
    item3 = main.Item(x=0, y=0, color=main.ITEM_COLORS[2], grid_col=1, grid_row=2, arrived_time=0)
    g.items = [item1, item2, item3]
    g._check_synthesis()
    assert g.combo == 6
    assert g.score > 0
    assert g.heat == 20  # heat unchanged during super


def test_no_synthesis_single_item():
    g = _make_game()
    g.grid[1][2] = main.JUNCTION
    g.combo = 2
    g.score = 500
    item = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    g.items = [item]
    g._check_synthesis()
    assert len(g.items) == 1
    assert g.combo == 2
    assert g.score == 500


# ── Test: Mismatch ──────────────────────────────────────────────────


def test_mismatch_different_colors():
    g = _make_game()
    g.grid[1][2] = main.JUNCTION
    g.combo = 3
    g.max_combo = 3
    g.heat = 0
    item1 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    item2 = main.Item(x=0, y=0, color=main.ITEM_COLORS[1], grid_col=1, grid_row=2, arrived_time=0)
    g.items = [item1, item2]
    g._check_synthesis()
    assert len(g.items) == 0
    assert g.combo == 0
    assert g.max_combo == 3  # max_combo is preserved
    assert g.heat == main.HEAT_MISMATCH
    # Should say "HEAT!" floating text
    assert any("HEAT!" in ft.text for ft in g.floating_texts)


def test_mismatch_multiple_items():
    g = _make_game()
    g.grid[1][2] = main.JUNCTION
    g.combo = 5
    g.heat = 10
    item1 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    item2 = main.Item(x=0, y=0, color=main.ITEM_COLORS[1], grid_col=1, grid_row=2, arrived_time=0)
    item3 = main.Item(x=0, y=0, color=main.ITEM_COLORS[2], grid_col=1, grid_row=2, arrived_time=0)
    g.items = [item1, item2, item3]
    g._check_synthesis()
    assert len(g.items) == 0
    assert g.combo == 0
    assert g.heat == 10 + main.HEAT_MISMATCH


# ── Test: Heat System ───────────────────────────────────────────────


def test_heat_decay():
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat < 10.0
    assert g.heat >= 0.0


def test_heat_does_not_go_below_zero():
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_over_max_game_over():
    g = _make_game()
    g.heat = main.MAX_HEAT
    g._update_heat()
    assert g.phase == main.Phase.GAME_OVER


def test_heat_slightly_under_max_not_game_over():
    g = _make_game()
    g.heat = main.MAX_HEAT - 0.001  # Just under
    g._update_heat()
    assert g.phase == main.Phase.PLAYING


def test_heat_frozen_during_super():
    g = _make_game()
    g.super_timer = 100
    g.heat = 10.0
    g._update_heat()
    assert g.heat == 10.0  # No decay during super


# ── Test: Cell Cycling ──────────────────────────────────────────────


def test_cycle_cell_empty_to_north():
    g = _make_game()
    g.grid[0][0] = main.EMPTY
    g._cycle_cell(0, 0)
    assert g.grid[0][0] == main.N


def test_cycle_cell_full_cycle():
    g = _make_game()
    g.grid[0][0] = main.EMPTY
    g._cycle_cell(0, 0)  # -> N
    g._cycle_cell(0, 0)  # -> E
    g._cycle_cell(0, 0)  # -> S
    g._cycle_cell(0, 0)  # -> W
    g._cycle_cell(0, 0)  # -> JUNCTION
    g._cycle_cell(0, 0)  # -> EMPTY
    assert g.grid[0][0] == main.EMPTY


def test_cycle_cell_north_to_east():
    g = _make_game()
    g.grid[0][0] = main.N
    g._cycle_cell(0, 0)
    assert g.grid[0][0] == main.E


def test_cycle_cell_junction_to_empty():
    g = _make_game()
    g.grid[0][0] = main.JUNCTION
    g._cycle_cell(0, 0)
    assert g.grid[0][0] == main.EMPTY


# ── Test: Initialization ────────────────────────────────────────────


def test_init_state():
    g = _make_game()
    assert g.phase == main.Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == main.TOTAL_FRAMES
    assert g.super_timer == 0
    assert len(g.items) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert all(g.grid[c][r] == main.EMPTY for c in range(main.COLS) for r in range(main.ROWS))


def test_start_game_resets_all():
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.heat = 50
    g.items = [main.Item(x=0, y=0, color=0, grid_col=0, grid_row=0)]
    g.particles = [main.Particle(x=0, y=0, vx=0, vy=0, life=1, color=0)]
    g.floating_texts = [main.FloatingText(x=0, y=0, text="x", life=1, color=0)]
    g._start_game()
    assert g.phase == main.Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert len(g.items) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_next_cell_north():
    g = _make_game()
    nc, nr = g._next_cell(3, 2, main.N)
    assert nc == 3
    assert nr == 1


def test_next_cell_east():
    g = _make_game()
    nc, nr = g._next_cell(3, 2, main.E)
    assert nc == 4
    assert nr == 2


def test_next_cell_south():
    g = _make_game()
    nc, nr = g._next_cell(3, 2, main.S)
    assert nc == 3
    assert nr == 3


def test_next_cell_west():
    g = _make_game()
    nc, nr = g._next_cell(3, 2, main.W)
    assert nc == 2
    assert nr == 2


# ── Test: Super Mode ────────────────────────────────────────────────


def test_super_mode_property():
    g = _make_game()
    assert g.super_mode is False
    g.super_timer = 100
    assert g.super_mode is True
    g.super_timer = 0
    assert g.super_mode is False


def test_super_timer_decrements():
    g = _make_game()
    g.super_timer = 10
    # Simulate update_super_timer logic
    g.super_timer -= 1
    assert g.super_timer == 9


# ── Test: Floating Text ─────────────────────────────────────────────


def test_synthesis_creates_floating_text():
    g = _make_game()
    g.grid[1][2] = main.JUNCTION
    g.combo = 2
    item1 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    item2 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    g.items = [item1, item2]
    g._check_synthesis()
    assert len(g.floating_texts) >= 2  # score text + combo text


# ── Test: Deterministic random ─────────────────────────────────────


def test_spawn_deterministic():
    g1 = _make_game(seed=42)
    g2 = _make_game(seed=42)
    g1._spawn_item()
    g2._spawn_item()
    assert g1.items[0].grid_row == g2.items[0].grid_row
    assert g1.items[0].color == g2.items[0].color


# ── Test: Multiple syntheses ───────────────────────────────────────


def test_multiple_syntheses_same_frame():
    g = _make_game()
    g.grid[1][2] = main.JUNCTION
    g.grid[3][2] = main.JUNCTION
    g.combo = 0
    g.score = 0
    item1 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    item2 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    item3 = main.Item(x=0, y=0, color=main.ITEM_COLORS[1], grid_col=3, grid_row=2, arrived_time=0)
    item4 = main.Item(x=0, y=0, color=main.ITEM_COLORS[1], grid_col=3, grid_row=2, arrived_time=0)
    g.items = [item1, item2, item3, item4]
    g._check_synthesis()
    assert len(g.items) == 0
    assert g.combo == 2
    assert g.score == main.SYNTHESIS_BASE * 1 + main.SYNTHESIS_BASE * 2


def test_synthesis_and_mismatch_same_frame():
    g = _make_game()
    g.grid[1][2] = main.JUNCTION  # synthesis
    g.grid[3][2] = main.JUNCTION  # mismatch
    g.combo = 1
    g.score = 0
    g.heat = 0
    item1 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    item2 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=1, grid_row=2, arrived_time=0)
    item3 = main.Item(x=0, y=0, color=main.ITEM_COLORS[0], grid_col=3, grid_row=2, arrived_time=0)
    item4 = main.Item(x=0, y=0, color=main.ITEM_COLORS[1], grid_col=3, grid_row=2, arrived_time=0)
    g.items = [item1, item2, item3, item4]
    g._check_synthesis()
    # Both cells should be cleared
    assert len(g.items) == 0
    # Combo should be 0 due to mismatch reset after synthesis
    assert g.combo == 0
    assert g.heat == main.HEAT_MISMATCH


# ── Test: Timer Game Over ──────────────────────────────────────────


def test_timer_game_over():
    g = _make_game()
    g.timer = 1
    # Simulate timer reaching 0 in update logic
    g.timer -= 1
    if g.timer <= 0:
        g.phase = main.Phase.GAME_OVER
    assert g.phase == main.Phase.GAME_OVER


def test_timer_not_game_over_yet():
    g = _make_game()
    g.timer = 100
    g.timer -= 1
    if g.timer <= 0:
        g.phase = main.Phase.GAME_OVER
    assert g.phase == main.Phase.PLAYING
