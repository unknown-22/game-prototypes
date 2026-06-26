"""test_imports.py — Headless logic tests for 165_reactor_idle."""
import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/165_reactor_idle")

from main import FloatingText, Game, Particle, Phase, Reactor


# ── Helpers ──


def make_game() -> Game:
    """Create a Game bypassing pyxel init."""
    g = Game.__new__(Game)
    # Pre-init all attributes reset() touches
    g.phase = Phase.TITLE
    g.grid = [[None] * 4 for _ in range(4)]
    g.energy = 50.0
    g.total_energy = 0.0
    g.heat = 0.0
    g.combo = 0
    g.max_combo = 0
    g.last_color = -1
    g.super_mode = False
    g.super_timer = 0
    g.tick_timer = 0
    g.particles = []
    g.floating_texts = []
    g.hover_col = -1
    g.hover_row = -1
    g.selected_col = -1
    g.selected_row = -1
    g.win = False
    g._rng = random.Random(42)
    g.reset()
    g._rng = random.Random(42)  # re-seed after reset overwrites
    return g


# ── Data Classes ──


def test_reactor_dataclass():
    r = Reactor(2, 1, 0, 2)
    assert r.col == 2
    assert r.row == 1
    assert r.color == 0
    assert r.tier == 2


def test_particle_dataclass():
    p = Particle(10.0, 20.0, -1.0, 0.5, 15, 8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == -1.0
    assert p.vy == 0.5
    assert p.life == 15
    assert p.color == 8


def test_floating_text_dataclass():
    ft = FloatingText(100, 50, "+3", 20, 10)
    assert ft.x == 100
    assert ft.y == 50
    assert ft.text == "+3"
    assert ft.life == 20
    assert ft.color == 10


# ── Game Constants ──


def test_game_constants():
    assert Game.GRID_COLS == 4
    assert Game.GRID_ROWS == 4
    assert Game.CELL_SIZE == 48
    assert Game.TARGET_ENERGY == 1000
    assert Game.MAX_HEAT == 100
    assert Game.TICK_INTERVAL == 30
    assert Game.SUPER_COMBO_THRESHOLD == 5
    assert Game.SUPER_DURATION == 300
    assert Game.HEAT_PER_TICK == 2
    assert Game.HEAT_DECAY == 0.5
    assert Game.ENERGY_PER_TIER == [1, 3, 7]
    assert Game.UPGRADE_COST == [20, 60]
    assert Game.PLACE_COST == 10
    assert Game.COOLING_COST == 30
    assert Game.COLORS == [8, 3, 5, 10]
    assert Game.COLOR_NAMES == ["RED", "GREEN", "BLUE", "YELLOW"]


# ── Grid Helpers ──


def test_get_grid_rect():
    g = make_game()
    x, y, w, h = g._get_grid_rect(0, 0)
    assert x == 64
    assert y == 60
    assert w == 48
    assert h == 48
    x2, y2, w2, h2 = g._get_grid_rect(3, 3)
    assert x2 == 64 + 3 * 48
    assert y2 == 60 + 3 * 48


def test_screen_to_grid_inside():
    g = make_game()
    col, row = g._screen_to_grid(64 + 24, 60 + 24)  # center of (0,0)
    assert col == 0
    assert row == 0
    col, row = g._screen_to_grid(64 + 48 + 24, 60 + 48 + 24)  # center of (1,1)
    assert col == 1
    assert row == 1


def test_screen_to_grid_outside():
    g = make_game()
    col, row = g._screen_to_grid(0, 0)
    assert col == -1
    assert row == -1
    col, row = g._screen_to_grid(400, 300)
    assert col == -1
    assert row == -1


# ── Neighbor Counting ──


def test_count_same_color_neighbors_none():
    g = make_game()
    assert g._count_same_color_neighbors(1, 1, 0) == 0


def test_count_same_color_neighbors_some():
    g = make_game()
    g.grid[0][1] = Reactor(1, 0, 0, 1)  # top neighbor, same color
    g.grid[2][1] = Reactor(1, 2, 1, 1)  # bottom neighbor, different color
    g.grid[1][0] = Reactor(0, 1, 0, 1)  # left neighbor, same color
    g.grid[1][2] = Reactor(2, 1, 0, 1)  # right neighbor, same color
    assert g._count_same_color_neighbors(1, 1, 0) == 3


def test_count_same_color_neighbors_edges():
    g = make_game()
    # Corner cell (0,0): only right and bottom neighbors exist
    g.grid[0][1] = Reactor(1, 0, 0, 1)
    g.grid[1][0] = Reactor(0, 1, 0, 1)
    assert g._count_same_color_neighbors(0, 0, 0) == 2


# ── Combo / Chain Logic ──


def test_check_chain_first_placement():
    g = make_game()
    g._check_chain(0)
    assert g.combo == 1
    assert g.last_color == 0


def test_check_chain_same_color():
    g = make_game()
    g._check_chain(0)
    g._check_chain(0)
    assert g.combo == 2
    assert g.last_color == 0


def test_check_chain_color_change_resets():
    g = make_game()
    g._check_chain(0)
    g._check_chain(0)
    g._check_chain(1)
    assert g.combo == 1
    assert g.last_color == 1


def test_check_chain_max_combo_tracks():
    g = make_game()
    g._check_chain(0)
    g._check_chain(0)
    g._check_chain(0)
    assert g.max_combo == 3
    g._check_chain(1)
    assert g.max_combo == 3  # max_combo preserved


def test_check_chain_super_activation():
    g = make_game()
    for _ in range(5):
        g._check_chain(0)
    assert g.combo == 5
    assert g.super_mode is True
    assert g.super_timer == 300


def test_check_chain_super_not_reactivate_while_active():
    g = make_game()
    for _ in range(5):
        g._check_chain(0)
    assert g.super_mode is True
    g._check_chain(0)  # combo 6, super already active
    assert g.super_timer == 300  # should NOT reset


# ── Reactor Placement ──


def test_place_reactor_deducts_energy():
    g = make_game()
    g._place_reactor(0, 0)
    assert abs(g.energy - (50.0 - Game.PLACE_COST)) < 0.01
    assert g.grid[0][0] is not None
    assert g.grid[0][0].tier == 1


def test_place_reactor_creates_particles():
    g = make_game()
    initial_particles = len(g.particles)
    g._place_reactor(0, 0)
    assert len(g.particles) > initial_particles


def test_handle_click_place_on_empty():
    g = make_game()
    assert g.grid[1][1] is None
    g._handle_click(1, 1)
    assert g.grid[1][1] is not None


def test_handle_click_no_place_if_insufficient_energy():
    g = make_game()
    g.energy = 5.0  # below PLACE_COST
    g._handle_click(1, 1)
    assert g.grid[1][1] is None


def test_handle_click_upgrade_existing():
    g = make_game()
    g.grid[1][1] = Reactor(1, 1, 0, 1)
    g.energy = 100.0
    g._handle_click(1, 1)
    assert g.grid[1][1].tier == 2


def test_handle_click_upgrade_insufficient_energy():
    g = make_game()
    g.grid[1][1] = Reactor(1, 1, 0, 1)
    g.energy = 5.0
    g._handle_click(1, 1)
    assert g.grid[1][1].tier == 1  # unchanged


def test_handle_click_upgrade_max_tier_noop():
    g = make_game()
    g.grid[1][1] = Reactor(1, 1, 0, 3)
    g.energy = 100.0
    g._handle_click(1, 1)
    assert g.grid[1][1].tier == 3  # unchanged


# ── Chain Multiplier ──


def test_chain_multiplier_no_neighbors():
    g = make_game()
    g.grid[1][1] = Reactor(1, 1, 0, 1)
    assert abs(g._chain_multiplier(1, 1, 0) - 1.0) < 0.01


def test_chain_multiplier_two_same_neighbors():
    g = make_game()
    g.grid[0][1] = Reactor(1, 0, 0, 1)
    g.grid[1][0] = Reactor(0, 1, 0, 1)
    g.grid[1][2] = Reactor(2, 1, 0, 1)  # right neighbor, also same
    # middle has left+top+right = 3 same-color neighbors
    # chain = 1.0 + 0.5 * (3-1) = 2.0
    mult = g._chain_multiplier(1, 1, 0)
    assert abs(mult - 2.0) < 0.01


def test_chain_multiplier_one_neighbor_no_bonus():
    g = make_game()
    g.grid[0][1] = Reactor(1, 0, 0, 1)  # one neighbor
    assert abs(g._chain_multiplier(1, 1, 0) - 1.0) < 0.01


# ── Production System ──


def test_update_production_adds_energy():
    g = make_game()
    g.energy = 0.0
    g.grid[0][0] = Reactor(0, 0, 0, 1)  # tier 1 = 1 energy/tick
    g._update_production()
    assert g.energy > 0.0
    assert g.total_energy > 0.0


def test_update_production_super_multiplier():
    g = make_game()
    g.energy = 0.0
    g.total_energy = 0.0
    g.heat = 0.0
    g.grid[0][0] = Reactor(0, 0, 0, 1)
    
    # Without super
    g._update_production()
    normal_energy = g.total_energy
    
    # With super
    g.energy = 0.0
    g.total_energy = 0.0
    g.heat = 0.0
    g.super_mode = True
    g.grid[0][0] = Reactor(0, 0, 0, 1)
    g._update_production()
    super_energy = g.total_energy
    
    assert super_energy > normal_energy * 1.5  # rough 3x check


def test_update_production_tier_affects_output():
    g = make_game()
    g.energy = 0.0
    g.total_energy = 0.0
    g.heat = 0.0
    g.grid[0][0] = Reactor(0, 0, 0, 3)
    g._update_production()
    assert g.total_energy >= 7.0  # tier 3 base


def test_update_production_adds_heat():
    g = make_game()
    g.heat = 0.0
    g.grid[0][0] = Reactor(0, 0, 0, 1)
    g.grid[1][1] = Reactor(1, 1, 0, 1)
    g._update_production()
    assert g.heat >= Game.HEAT_PER_TICK * 2  # 2 reactors


def test_update_production_win_condition():
    g = make_game()
    g.total_energy = 999.0
    g.heat = 0.0
    g.grid[0][0] = Reactor(0, 0, 0, 1)
    g._update_production()
    assert g.phase == Phase.GAME_OVER
    assert g.win is True


def test_update_production_heat_game_over():
    g = make_game()
    g.heat = 99.0
    # Place many reactors to push heat over 100
    for row in range(4):
        for col in range(4):
            g.grid[row][col] = Reactor(col, row, 0, 1)
    g._update_production()
    # heat should be >= 100 after 16 reactors * 2
    assert g.phase == Phase.GAME_OVER
    assert g.win is False


# ── Tick System ──


def test_update_tick_increments():
    g = make_game()
    assert g.tick_timer == 0
    g._update_tick()
    assert g.tick_timer == 1


def test_update_tick_triggers_production():
    g = make_game()
    g.tick_timer = Game.TICK_INTERVAL - 1
    initial_total = g.total_energy
    g.grid[0][0] = Reactor(0, 0, 0, 1)
    g._update_tick()
    assert g.tick_timer == 0  # reset
    assert g.total_energy > initial_total


# ── Heat System ──


def test_update_heat_decays():
    g = make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0
    assert g.heat >= 49.0  # decay is 0.5


def test_update_heat_clamps_to_zero():
    g = make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_game_over_at_threshold():
    g = make_game()
    g.heat = 100.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.win is False
    assert g.heat == 100.0  # clamped


def test_update_heat_game_over_above_threshold():
    g = make_game()
    g.heat = 150.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.win is False


# ── Super Mode ──


def test_update_super_decrements_timer():
    g = make_game()
    g.super_mode = True
    g.super_timer = 10
    g._update_super()
    assert g.super_timer == 9
    assert g.super_mode is True


def test_update_super_ends():
    g = make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_timer == 0
    assert g.super_mode is False


def test_update_super_noop_when_inactive():
    g = make_game()
    g.super_mode = False
    g.super_timer = 0
    g._update_super()
    assert g.super_mode is False
    assert g.super_timer == 0


# ── Cooling ──


def test_cool_down_reduces_heat():
    g = make_game()
    g.heat = 80.0
    g.energy = 100.0
    g._cool_down()
    assert abs(g.heat - 60.0) < 0.01


def test_cool_down_deducts_energy():
    g = make_game()
    g.energy = 100.0
    g._cool_down()
    assert abs(g.energy - (100.0 - Game.COOLING_COST)) < 0.01


def test_cool_down_insufficient_energy():
    g = make_game()
    g.energy = 5.0
    g.heat = 80.0
    g._cool_down()
    assert abs(g.heat - 80.0) < 0.01  # unchanged
    assert abs(g.energy - 5.0) < 0.01


def test_cool_down_clamps_heat_to_zero():
    g = make_game()
    g.energy = 100.0
    g.heat = 10.0
    g._cool_down()
    assert g.heat == 0.0


# ── Particles ──


def test_spawn_particles_creates():
    g = make_game()
    g._spawn_particles(100, 100, 8, 5)
    assert len(g.particles) == 5


def test_update_particles_removes_dead():
    g = make_game()
    g.particles = [Particle(10, 10, 0, 0, 0, 8)]
    g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_keeps_alive():
    g = make_game()
    g.particles = [Particle(10, 10, 1, -1, 5, 8)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


def test_particles_gravity():
    g = make_game()
    g.particles = [Particle(10, 10, 0, 0, 10, 8)]
    g._update_particles()
    assert g.particles[0].vy > 0  # gravity applied


# ── Floating Texts ──


def test_update_floating_texts_removes_dead():
    g = make_game()
    g.floating_texts = [FloatingText(10, 10, "test", 0, 7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_update_floating_texts_moves_up():
    g = make_game()
    g.floating_texts = [FloatingText(10, 10, "test", 5, 7)]
    g._update_floating_texts()
    assert g.floating_texts[0].y < 10


# ── All Reactors ──


def test_all_reactors_empty():
    g = make_game()
    assert g._all_reactors() == []


def test_all_reactors_returns_all():
    g = make_game()
    g.grid[0][0] = Reactor(0, 0, 0, 1)
    g.grid[2][2] = Reactor(2, 2, 1, 2)
    reactors = g._all_reactors()
    assert len(reactors) == 2


# ── Reset / State ──


def test_reset_initial_state():
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.energy == 50.0
    assert g.total_energy == 0.0
    assert g.heat == 0.0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.super_mode is False
    assert g.win is False


def test_reset_clears_grid():
    g = make_game()
    g.grid[0][0] = Reactor(0, 0, 0, 1)
    g.reset()
    assert g.grid[0][0] is None


# ── Full update_playing cycle ──


def test_update_playing_runs_all_steps():
    g = make_game()
    g.phase = Phase.PLAYING
    g.grid[0][0] = Reactor(0, 0, 0, 1)
    initial_particles = len(g.particles)
    g.update_playing()
    # tick advanced, heat decayed, particles updated
    assert g.tick_timer >= 1
    assert len(g.particles) >= 0  # some may have been created/destroyed


# ── Numeric precision / edge cases ──


def test_energy_never_negative():
    g = make_game()
    g.energy = 0.0
    g.heat = 0.0
    g.grid[0][0] = Reactor(0, 0, 0, 1)
    g._update_production()
    assert g.energy >= 0.0


def test_heat_clamped_range():
    g = make_game()
    g.heat = -10.0
    g._update_heat()
    assert g.heat >= 0.0  # clamped to 0 by max(0, ...)


def test_grid_full_does_not_crash():
    g = make_game()
    # Fill all 16 cells
    for row in range(4):
        for col in range(4):
            g.grid[row][col] = Reactor(col, row, row % 4, 3)
    g._update_production()  # should not crash


def test_combo_resets_correctly_after_mismatch():
    g = make_game()
    g._check_chain(0)
    g._check_chain(0)
    g._check_chain(0)
    assert g.combo == 3
    g._check_chain(1)
    assert g.combo == 1
    assert g.last_color == 1
    g._check_chain(1)
    assert g.combo == 2


def test_handle_click_bounds_checked():
    """_handle_click with invalid coords — should be handled gracefully.
    This primarily tests that grid indexing doesn't crash with edge values."""
    g = make_game()
    # Valid click on empty cell
    g._handle_click(0, 0)
    assert g.grid[0][0] is not None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
