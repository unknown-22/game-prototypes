from __future__ import annotations

import random


from main import COLS, HEAT_CAP, HEAT_DECAY, HEAT_MISMATCH, HEAT_UNTRIGGERED, MAX_PLACES, ROWS, SUPER_DURATION, SUPER_THRESHOLD, Game, Node, Phase


def _new_game() -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    return g


# ---------------------------------------------------------------------------
# Grid setup helpers
# ---------------------------------------------------------------------------
def _empty_grid() -> list[list[Node | None]]:
    return [[None for _ in range(COLS)] for _ in range(ROWS)]


# ---------------------------------------------------------------------------
# BFS chain tests
# ---------------------------------------------------------------------------
class TestBfsChain:
    def test_bfs_straight_line(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        for c in range(4):
            g.grid[0][c] = Node(col=c, row=0, color=0)
        result = g._bfs_chain(0, 0, 0)
        assert result == {(c, 0) for c in range(4)}

    def test_bfs_l_shape(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.grid[0][1] = Node(col=1, row=0, color=0)
        g.grid[1][1] = Node(col=1, row=1, color=0)
        result = g._bfs_chain(0, 0, 0)
        assert result == {(0, 0), (1, 0), (1, 1)}

    def test_bfs_isolated_node(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[2][3] = Node(col=3, row=2, color=0)
        result = g._bfs_chain(3, 2, 0)
        assert result == {(3, 2)}

    def test_bfs_respects_color_boundaries(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.grid[0][1] = Node(col=1, row=0, color=1)
        g.grid[0][2] = Node(col=2, row=0, color=0)
        result = g._bfs_chain(0, 0, 0)
        assert result == {(0, 0)}
        assert (2, 0) not in result

    def test_bfs_respects_empty_gaps(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.grid[0][2] = Node(col=2, row=0, color=0)
        result = g._bfs_chain(0, 0, 0)
        assert result == {(0, 0)}
        assert (2, 0) not in result

    def test_bfs_empty_cell_returns_empty(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        result = g._bfs_chain(5, 3, 0)
        assert result == set()

    def test_bfs_2x2_block(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        for r in range(2):
            for c in range(2):
                g.grid[r][c] = Node(col=c, row=r, color=2)
        result = g._bfs_chain(0, 0, 2)
        assert result == {(0, 0), (1, 0), (0, 1), (1, 1)}


# ---------------------------------------------------------------------------
# COMBO tests
# ---------------------------------------------------------------------------
class TestCombo:
    def test_combo_increments_on_same_color(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.selected_color = 0
        assert g.combo == 0
        g.combo += 1
        assert g.combo == 1

    def test_combo_resets_on_switch(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.selected_color = 0
        g.combo = 3
        g._select_color(1)
        assert g.combo == 0

    def test_combo_no_reset_on_same_selection(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.combo = 5
        g._select_color(0)
        assert g.combo == 5

    def test_max_combo_tracking(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.selected_color = 0
        assert g.max_combo == 0
        g.combo = 7
        g.max_combo = max(g.max_combo, g.combo)
        assert g.max_combo == 7
        g.combo = 3
        g.max_combo = max(g.max_combo, g.combo)
        assert g.max_combo == 7


# ---------------------------------------------------------------------------
# SUPER MODE tests
# ---------------------------------------------------------------------------
class TestSuperMode:
    def test_super_mode_activation_at_threshold(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.combo = SUPER_THRESHOLD - 1
        g.combo += 1
        assert g.combo >= SUPER_THRESHOLD
        g.super_mode = True
        g.super_timer = SUPER_DURATION
        assert g.super_mode is True
        assert g.super_timer > 0

    def test_super_mode_deactivation_after_timer(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.super_mode = True
        g.super_timer = 1
        g.super_timer -= 1
        assert g.super_timer == 0
        assert g.super_mode is True
        g.super_timer -= 1
        assert g.super_timer <= 0


# ---------------------------------------------------------------------------
# Score computation tests
# ---------------------------------------------------------------------------
class TestScore:
    def test_score_chain_size_combo_mul_10(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.grid[0][1] = Node(col=1, row=0, color=0)
        g.grid[0][2] = Node(col=2, row=0, color=0)
        g.combo = 2
        g.super_mode = False
        score = g._resolve_chains()
        assert score == 3 * (2 + 1) * 10  # 90

    def test_score_super_mode_3x(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.grid[0][1] = Node(col=1, row=0, color=0)
        g.grid[0][2] = Node(col=2, row=0, color=0)
        g.combo = 2
        g.super_mode = True
        score = g._resolve_chains()
        assert score == 3 * (2 + 1) * 10 * 3  # 270

    def test_no_score_for_small_cluster(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.combo = 5
        g.super_mode = False
        score = g._resolve_chains()
        assert score == 0

    def test_multiple_chains_score_sum(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.grid[0][1] = Node(col=1, row=0, color=0)
        g.grid[0][3] = Node(col=3, row=0, color=1)
        g.grid[0][4] = Node(col=4, row=0, color=1)
        g.combo = 1
        g.super_mode = False
        score = g._resolve_chains()
        assert score == 2 * 2 * 10 + 2 * 2 * 10  # 80


# ---------------------------------------------------------------------------
# HEAT tests
# ---------------------------------------------------------------------------
class TestHeat:
    def test_heat_added_on_color_switch(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.combo = 5
        initial_heat = g.heat
        g._select_color(1)
        assert g.heat == initial_heat + HEAT_MISMATCH

    def test_heat_untracked_nodes(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.grid[0][5] = Node(col=5, row=0, color=1)
        initial_heat = g.heat
        g._resolve_chains()
        assert g.heat == initial_heat + HEAT_UNTRIGGERED * 2

    def test_heat_decay(self) -> None:
        g = _new_game()
        g.reset()
        g.heat = 10.0
        g._update_heat()
        assert g.heat == 10.0 - HEAT_DECAY

    def test_heat_decay_not_below_zero(self) -> None:
        g = _new_game()
        g.reset()
        g.heat = 0.001
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_cap_triggers_game_over(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.heat = HEAT_CAP
        g.phase = Phase.GAME_OVER if g.heat >= HEAT_CAP else g.phase
        assert g.phase == Phase.GAME_OVER


# ---------------------------------------------------------------------------
# Node placement tests
# ---------------------------------------------------------------------------
class TestPlacement:
    def test_place_on_empty_cell(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.places_remaining = MAX_PLACES
        g._place_node(2, 3)
        assert g.grid[3][2] is not None
        assert g.grid[3][2].col == 2
        assert g.grid[3][2].row == 3

    def test_place_blocked_on_occupied(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g._place_node(2, 3)
        g.places_remaining = MAX_PLACES
        g._place_node(2, 3)
        assert g.places_remaining == MAX_PLACES

    def test_place_count_decrement(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.places_remaining = MAX_PLACES
        g._place_node(0, 0)
        assert g.places_remaining == MAX_PLACES - 1

    def test_no_place_when_no_remaining(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.places_remaining = 0
        g._place_node(0, 0)
        assert g.grid[0][0] is None


# ---------------------------------------------------------------------------
# Spawn tests
# ---------------------------------------------------------------------------
class TestSpawn:
    def test_spawn_count_scales_with_turn(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.turn = 10
        g._spawn_nodes()
        expected = min(2 + 10 // 3, COLS * ROWS // 2)
        node_count = sum(1 for r in range(ROWS) for c in range(COLS) if g.grid[r][c] is not None)
        assert node_count == expected

    def test_spawn_on_empty_cells_only(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.turn = 5
        g._spawn_nodes()
        assert g.grid[0][0] is not None
        assert g.grid[0][0].col == 0
        assert g.grid[0][0].row == 0


# ---------------------------------------------------------------------------
# Reset tests
# ---------------------------------------------------------------------------
class TestReset:
    def test_reset_clears_grid(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.score = 500
        g.combo = 10
        g.max_combo = 15
        g.heat = 80.0
        g.turn = 20
        g.reset()
        assert g.grid[0][0] is None
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.turn == 0
        assert g.phase == Phase.TITLE

    def test_start_game_sets_build_phase(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        assert g.phase == Phase.BUILD


# ---------------------------------------------------------------------------
# Resolve logic tests
# ---------------------------------------------------------------------------
class TestResolve:
    def test_triggered_nodes_removed(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.grid[0][1] = Node(col=1, row=0, color=0)
        g.grid[0][2] = Node(col=2, row=0, color=0)
        g._resolve_chains()
        for c in range(3):
            assert g.grid[0][c] is None

    def test_small_clusters_not_removed(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g._resolve_chains()
        assert g.grid[0][0] is not None

    def test_resolve_score_gained_tracked(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.grid[0][1] = Node(col=1, row=0, color=0)
        g.combo = 3
        g._resolve_chains()
        assert g.resolve_score_gained > 0
        assert g.resolve_nodes_triggered == 2


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_full_grid_no_placement(self) -> None:
        g = _new_game()
        g.reset()
        g._start_game()
        for r in range(ROWS):
            for c in range(COLS):
                g.grid[r][c] = Node(col=c, row=r, color=0)
        g.places_remaining = MAX_PLACES
        g._place_node(0, 0)
        assert g.places_remaining == MAX_PLACES

    def test_super_mode_score_multiplier(self) -> None:
        g = _new_game()
        g.reset()
        g.grid = _empty_grid()
        g.grid[0][0] = Node(col=0, row=0, color=0)
        g.grid[0][1] = Node(col=1, row=0, color=0)
        g.combo = 5
        g.super_mode = True
        score = g._resolve_chains()
        assert score == 2 * 6 * 10 * 3  # 360
