from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/288_glass_chain")
from main import (
    GRID_COLS,
    GRID_ROWS,
    CELL_SIZE,
    GRID_OFFSET_X,
    GRID_OFFSET_Y,
    HEAT_MAX,
    HEAT_PER_PLACE,
    HEAT_DECAY_PER_TICK,
    MAX_TIER,
    SURGE_COMBO_THRESHOLD,
    TICK_INTERVAL,
    GAME_DURATION,
    SYNTH_SCORE_PER_TIER_MULT,
    PLACE_SCORE_PER_TIER,
    CRACK_SCORE_PENALTY,
    Cell,
    Phase,
    Game,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.grid = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.game_timer = GAME_DURATION
    g.surge_timer = 0.0
    g.surge_color = 0
    g.mouse_grid_x = -1
    g.mouse_grid_y = -1
    g.selected_color = 1
    g.phase = Phase.PLAYING
    g.particles = []
    g.floating_texts = []
    g.anim_timer = 0.0
    g.cells_to_anim = []
    g._rng = random.Random(seed)
    g._tick_timer = 0.0
    g.best_score = 0
    g._init_grid()
    return g


class TestCellAt:
    def test_inside_grid(self) -> None:
        g = _make_game()
        result = g._cell_at(GRID_OFFSET_X, GRID_OFFSET_Y)
        assert result == (0, 0)

    def test_inside_grid_middle(self) -> None:
        g = _make_game()
        mx = GRID_OFFSET_X + 3 * CELL_SIZE + CELL_SIZE // 2
        my = GRID_OFFSET_Y + 2 * CELL_SIZE + CELL_SIZE // 2
        result = g._cell_at(mx, my)
        assert result == (3, 2)

    def test_outside_grid_left(self) -> None:
        g = _make_game()
        result = g._cell_at(GRID_OFFSET_X - 10, GRID_OFFSET_Y)
        assert result is None

    def test_outside_grid_right(self) -> None:
        g = _make_game()
        mx = GRID_OFFSET_X + GRID_COLS * CELL_SIZE + 10
        result = g._cell_at(mx, GRID_OFFSET_Y)
        assert result is None

    def test_outside_grid_top(self) -> None:
        g = _make_game()
        result = g._cell_at(GRID_OFFSET_X, GRID_OFFSET_Y - 10)
        assert result is None


class TestAdjacentPositions:
    def test_center_cell(self) -> None:
        g = _make_game()
        positions = g._adjacent_positions(3, 2)
        assert len(positions) == 4

    def test_corner_cell(self) -> None:
        g = _make_game()
        positions = g._adjacent_positions(0, 0)
        assert len(positions) == 2

    def test_edge_cell(self) -> None:
        g = _make_game()
        positions = g._adjacent_positions(0, 3)
        assert len(positions) == 3


class TestGetConnected:
    def test_empty_cell_returns_empty(self) -> None:
        g = _make_game()
        result = g._get_connected(0, 0)
        assert len(result) == 0

    def test_isolated_cell_returns_one(self) -> None:
        g = _make_game()
        g.grid[0][0] = Cell(color=1, tier=1)
        result = g._get_connected(0, 0)
        assert result == {(0, 0)}

    def test_connected_same_color(self) -> None:
        g = _make_game()
        g.grid[0][0] = Cell(color=1, tier=1)
        g.grid[0][1] = Cell(color=1, tier=1)
        g.grid[1][0] = Cell(color=1, tier=1)
        result = g._get_connected(0, 0)
        assert result == {(0, 0), (1, 0), (0, 1)}

    def test_different_color_not_connected(self) -> None:
        g = _make_game()
        g.grid[0][0] = Cell(color=1, tier=1)
        g.grid[0][1] = Cell(color=2, tier=1)
        result = g._get_connected(0, 0)
        assert result == {(0, 0)}


class TestPlaceGlass:
    def test_place_on_empty_cell(self) -> None:
        g = _make_game()
        g.selected_color = 1
        gain = g._place_glass(0, 0)
        assert gain > 0
        assert g.grid[0][0].color == 1
        assert g.grid[0][0].tier == 1

    def test_place_on_occupied_cell_does_nothing(self) -> None:
        g = _make_game()
        g.selected_color = 1
        g.grid[0][0] = Cell(color=2, tier=2)
        gain = g._place_glass(0, 0)
        assert gain == 0
        assert g.grid[0][0].color == 2
        assert g.grid[0][0].tier == 2

    def test_place_returns_place_score(self) -> None:
        g = _make_game()
        g.selected_color = 1
        gain = g._place_glass(0, 0)
        assert gain == PLACE_SCORE_PER_TIER

    def test_place_with_same_color_neighbor_triggers_synthesis(self) -> None:
        g = _make_game()
        g.selected_color = 1
        g.grid[0][0] = Cell(color=1, tier=1)
        gain = g._place_glass(1, 0)
        assert gain > PLACE_SCORE_PER_TIER
        assert g.grid[0][0].tier == 2
        assert g.grid[0][1].tier == 2

    def test_place_with_different_color_neighbor_no_synthesis(self) -> None:
        g = _make_game()
        g.selected_color = 1
        g.grid[0][0] = Cell(color=2, tier=1)
        gain = g._place_glass(1, 0)
        assert gain == PLACE_SCORE_PER_TIER
        assert g.grid[0][0].tier == 1


class TestSynthesize:
    def test_synthesis_returns_score(self) -> None:
        g = _make_game()
        g.grid[0][0] = Cell(color=1, tier=1)
        g.grid[0][1] = Cell(color=1, tier=1)
        cluster = {(0, 0), (1, 0)}
        score = g._synthesize(cluster)
        assert score == 2 * 2 * SYNTH_SCORE_PER_TIER_MULT * 2

    def test_synthesis_max_tier_does_not_upgrade(self) -> None:
        g = _make_game()
        g.grid[0][0] = Cell(color=1, tier=MAX_TIER)
        cluster = {(0, 0)}
        score = g._synthesize(cluster)
        assert score == 0
        assert g.grid[0][0].tier == MAX_TIER

    def test_synthesis_from_tier_3_to_4(self) -> None:
        g = _make_game()
        g.grid[0][0] = Cell(color=1, tier=3)
        cluster = {(0, 0)}
        score = g._synthesize(cluster)
        assert score == MAX_TIER * MAX_TIER * SYNTH_SCORE_PER_TIER_MULT
        assert g.grid[0][0].tier == MAX_TIER

    def test_synthesis_skip_empty_cells(self) -> None:
        g = _make_game()
        g.grid[0][0] = Cell(color=1, tier=1)
        g.grid[0][1] = Cell(color=0, tier=0)
        cluster = {(0, 0), (1, 0)}
        score = g._synthesize(cluster)
        assert score == 2 * 2 * SYNTH_SCORE_PER_TIER_MULT
        assert g.grid[0][0].tier == 2
        assert g.grid[0][1].tier == 0


class TestCAPropagate:
    def test_ca_propagate_seeded(self) -> None:
        g = _make_game(seed=123)
        g.grid[2][3] = Cell(color=1, tier=1)
        spread = g._ca_propagate()
        assert spread >= 0

    def test_ca_propagate_from_empty_grid(self) -> None:
        g = _make_game()
        spread = g._ca_propagate()
        assert spread == 0


class TestCombo:
    def test_combo_increments_on_placement(self) -> None:
        g = _make_game()
        assert g.combo == 0
        g._do_placement(0, 0)
        assert g.combo == 1

    def test_combo_and_max_combo_track(self) -> None:
        g = _make_game()
        g._do_placement(0, 0)
        g._do_placement(3, 0)
        g._do_placement(5, 2)
        assert g.combo == 3
        assert g.max_combo >= 3

    def test_combo_resets_on_crack(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX  # will crack on next placement
        g._do_placement(0, 0)
        assert g.combo == 0


class TestSurge:
    def test_surge_triggers_at_combo_threshold(self) -> None:
        g = _make_game()
        g.selected_color = 1
        g.combo = SURGE_COMBO_THRESHOLD - 1
        g.grid[0][0] = Cell(color=1, tier=1)
        g._do_placement(1, 0)
        assert g.surge_timer > 0
        assert g.surge_color == 1

    def test_surge_upgrades_to_max_tier(self) -> None:
        g = _make_game()
        g.selected_color = 1
        g.combo = SURGE_COMBO_THRESHOLD - 1
        g.grid[0][0] = Cell(color=1, tier=2)
        g.grid[0][1] = Cell(color=1, tier=2)
        g._do_placement(2, 0)
        assert g.grid[0][0].tier == MAX_TIER
        assert g.grid[0][1].tier == MAX_TIER

    def test_surge_sets_surge_timer(self) -> None:
        g = _make_game()
        g.selected_color = 1
        g.combo = SURGE_COMBO_THRESHOLD - 1
        g.grid[0][0] = Cell(color=1, tier=1)
        g._do_placement(1, 0)
        assert g.surge_timer > 0


class TestHeat:
    def test_heat_increases_on_placement(self) -> None:
        g = _make_game()
        assert g.heat == 0.0
        g._do_placement(0, 0)
        assert g.heat == HEAT_PER_PLACE

    def test_heat_decays_per_tick(self) -> None:
        g = _make_game()
        g.heat = 10.0
        g._update_tick()
        assert g.heat == max(0.0, 10.0 - HEAT_DECAY_PER_TICK)

    def test_heat_clamps_to_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_tick()
        assert g.heat == 0.0

    def test_heat_clamps_to_max(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX - 1
        g.selected_color = 1
        g._do_placement(0, 0)
        # Heat clamps to HEAT_MAX, then crack triggers and resets to 0
        assert g.heat == 0.0

    def test_heat_at_max_triggers_crack(self) -> None:
        g = _make_game(seed=42)
        g.selected_color = 1
        g.grid[0][0] = Cell(color=1, tier=1)
        g.grid[1][0] = Cell(color=1, tier=1)
        g.heat = HEAT_MAX
        initial_score = g.score
        g._do_placement(2, 0)
        assert g.heat == 0.0
        assert g.score < initial_score


class TestCrack:
    def test_crack_on_non_empty_cell_only(self) -> None:
        g = _make_game(seed=42)
        g.grid[0][0] = Cell(color=1, tier=1)
        penalty = g._crack_glass()
        assert penalty == CRACK_SCORE_PENALTY
        assert g.grid[0][0].color == 0
        assert g.grid[0][0].tier == 0

    def test_crack_empty_grid_returns_zero(self) -> None:
        g = _make_game()
        penalty = g._crack_glass()
        assert penalty == 0


class TestTimer:
    def test_timer_decreases_on_tick(self) -> None:
        g = _make_game()
        initial_time = g.game_timer
        g._update_tick()
        assert g.game_timer == max(0.0, initial_time - TICK_INTERVAL)

    def test_timer_clamps_to_zero(self) -> None:
        g = _make_game()
        g.game_timer = 0.5
        g._update_tick()
        assert g.game_timer == 0.0


class TestReset:
    def test_reset_clears_grid(self) -> None:
        g = _make_game()
        g.grid[0][0] = Cell(color=1, tier=2)
        g.reset()
        assert g.grid[0][0].color == 0
        assert g.grid[0][0].tier == 0

    def test_reset_clears_score_and_combo(self) -> None:
        g = _make_game()
        g.score = 500
        g.combo = 5
        g.max_combo = 7
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0

    def test_reset_preserves_best_score(self) -> None:
        g = _make_game()
        g.score = 500
        g.best_score = 300
        g.reset()
        # reset() preserves best_score as-is (updated on game over, not in reset)
        assert g.best_score == 300

    def test_reset_clears_heat(self) -> None:
        g = _make_game()
        g.heat = 80.0
        g.reset()
        assert g.heat == 0.0

    def test_reset_sets_title_phase(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.reset()
        assert g.phase == Phase.TITLE


class TestSurgeTimer:
    def test_surge_timer_decays_on_tick(self) -> None:
        g = _make_game()
        g.surge_timer = 3.0
        g.surge_color = 1
        g._update_tick()
        assert g.surge_timer == 2.0

    def test_surge_timer_resets_color_on_expiry(self) -> None:
        g = _make_game()
        g.surge_timer = 0.5
        g.surge_color = 1
        g._update_tick()
        assert g.surge_color == 0


class TestParticles:
    def test_add_particles_creates_particles(self) -> None:
        g = _make_game()
        g._add_particles(100, 100, 8, 5)
        assert len(g.particles) == 5

    def test_particle_count_and_color(self) -> None:
        g = _make_game(seed=42)
        g._add_particles(100, 100, 8, 3)
        assert len(g.particles) == 3
        for p in g.particles:
            assert p.color == 8

    def test_update_particles_removes_expired(self) -> None:
        g = _make_game()
        g._add_particles(100, 100, 8, 3)
        for p in g.particles:
            p.life = 0
        g._update_particles()
        assert len(g.particles) == 0


class TestFloatingText:
    def test_floating_text_decreases_life(self) -> None:
        g = _make_game()
        g.floating_texts = []
        from main import FloatingText as FT

        g.floating_texts.append(FT(x=50, y=50, text="test", life=10, color=7))
        g._update_floating_texts()
        ft = g.floating_texts[0]
        assert ft.life == 9

    def test_floating_text_removed_when_expired(self) -> None:
        g = _make_game()
        from main import FloatingText as FT

        g.floating_texts.append(FT(x=50, y=50, text="test", life=1, color=7))
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


class TestPlacementEdgeCases:
    def test_place_when_grid_full(self) -> None:
        g = _make_game()
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                g.grid[r][c] = Cell(color=1, tier=1)
        gain = g._place_glass(0, 0)
        assert gain == 0

    def test_different_color_adjacent_no_synthesis(self) -> None:
        g = _make_game()
        g.selected_color = 1
        # Place different-color neighbors around (2,2), then place same-color at (2,2)
        g.grid[1][2] = Cell(color=2, tier=1)  # above
        g.grid[3][2] = Cell(color=3, tier=1)  # below
        g.grid[2][1] = Cell(color=4, tier=1)  # left
        gain = g._place_glass(2, 2)
        assert gain == PLACE_SCORE_PER_TIER


class TestIntegration:
    def test_full_placement_cycle(self) -> None:
        g = _make_game(seed=42)
        g.selected_color = 1
        g._do_placement(0, 0)
        assert g.grid[0][0].color == 1
        assert g.grid[0][0].tier == 1
        assert g.score > 0
        assert g.combo == 1
        assert g.heat == HEAT_PER_PLACE

    def test_chained_synthesis(self) -> None:
        g = _make_game()
        g.selected_color = 1
        g.grid[0][0] = Cell(color=1, tier=1)
        g._do_placement(1, 0)
        assert g.grid[0][0].tier == 2
        assert g.grid[0][1].tier == 2


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
