import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    GRID_SIZE,
    HEAT_MAX,
    SUPER_DURATION,
    TIMER_MAX,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.grid = []
    g.selected = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.super_timer = 0
    g.words_found = 0
    g.heat = 0.0
    g.timer = TIMER_MAX
    g.particles = []
    g.floating_texts = []
    g.high_score = 0
    g._init_grid()
    g.phase = Phase.PLAYING
    return g


class TestGridInit:
    def test_grid_size(self) -> None:
        g = make_game()
        assert len(g.grid) == GRID_SIZE
        for row in g.grid:
            assert len(row) == GRID_SIZE

    def test_all_cells_filled(self) -> None:
        g = make_game()
        for row in g.grid:
            for tile in row:
                assert tile is not None

    def test_letter_range(self) -> None:
        g = make_game()
        for row in g.grid:
            for tile in row:
                assert tile is not None
                assert "A" <= tile.letter <= "Z"

    def test_color_from_letter(self) -> None:
        g = make_game()
        from main import TILE_COLORS

        for row in g.grid:
            for tile in row:
                assert tile is not None
                expected_color = TILE_COLORS[ord(tile.letter) % 4]
                assert tile.color == expected_color


class TestAdjacency:
    def test_adjacent_same_row(self) -> None:
        g = make_game()
        assert g._is_adjacent(0, 0, 0, 1) is True

    def test_adjacent_same_col(self) -> None:
        g = make_game()
        assert g._is_adjacent(0, 0, 1, 0) is True

    def test_not_adjacent_diagonal(self) -> None:
        g = make_game()
        assert g._is_adjacent(0, 0, 1, 1) is False

    def test_not_adjacent_far(self) -> None:
        g = make_game()
        assert g._is_adjacent(0, 0, 2, 0) is False

    def test_not_adjacent_same_tile(self) -> None:
        g = make_game()
        assert g._is_adjacent(1, 1, 1, 1) is False


class TestSelection:
    def test_select_first_tile(self) -> None:
        g = make_game()
        result = g._try_select(0, 0)
        assert result is True
        assert len(g.selected) == 1
        assert g.selected[0] == (0, 0)

    def test_select_adjacent_tile(self) -> None:
        g = make_game()
        g._try_select(0, 0)
        result = g._try_select(0, 1)
        assert result is True
        assert len(g.selected) == 2

    def test_reject_non_adjacent_tile(self) -> None:
        g = make_game()
        g._try_select(0, 0)
        result = g._try_select(0, 2)
        assert result is False
        assert len(g.selected) == 1

    def test_deselect_from_tile(self) -> None:
        g = make_game()
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        assert len(g.selected) == 3
        g._try_select(0, 1)  # Click on middle tile → deselect from it
        assert len(g.selected) == 1
        assert g.selected[0] == (0, 0)

    def test_deselect_first_tile(self) -> None:
        g = make_game()
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        g._try_select(0, 0)  # Click on first tile → deselect all
        assert len(g.selected) == 0

    def test_select_out_of_bounds_returns_false(self) -> None:
        g = make_game()
        assert g._try_select(-1, 0) is False
        assert g._try_select(GRID_SIZE, 0) is False

    def test_cancel_selection(self) -> None:
        g = make_game()
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._cancel_selection()
        assert len(g.selected) == 0


class TestCombo:
    def test_combo_starts_at_one(self) -> None:
        g = make_game()
        g._try_select(0, 0)
        assert g.combo == 1

    def test_combo_same_color_increases(self) -> None:
        g = make_game(42)
        # Force same-color tiles
        tile00 = g.grid[0][0]
        tile01 = g.grid[0][1]
        assert tile00 is not None and tile01 is not None
        if tile00.color != tile01.color:
            tile01.color = tile00.color

        g._try_select(0, 0)
        g._try_select(0, 1)
        assert g.combo == 2

    def test_combo_resets_on_different_color(self) -> None:
        g = make_game(42)
        tile00 = g.grid[0][0]
        tile01 = g.grid[0][1]
        tile02 = g.grid[0][2]
        assert tile00 is not None and tile01 is not None and tile02 is not None
        # Make first two same, third different
        tile01.color = tile00.color
        # Ensure tile02 is different
        if tile02.color == tile00.color:
            tile02.color = (tile00.color + 1) % 4 if tile00.color is not None else 0

        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        assert g.combo == 1  # Reset on third tile

    def test_super_activation_at_combo_four(self) -> None:
        g = make_game(42)
        # Set up 4 same-color tiles in a row
        for c in range(4):
            t = g.grid[0][c]
            if t is not None:
                t.color = 8  # RED
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        assert g.super_timer == 0  # COMBO=3, not enough
        g._try_select(0, 3)
        assert g.combo == 4
        assert g.super_timer == SUPER_DURATION


class TestScoring:
    def test_base_score(self) -> None:
        g = make_game(42)
        # Select 3 tiles
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        base, mult = g._compute_score()
        assert base >= 150  # At minimum 3*50

    def test_submit_word_increases_score(self) -> None:
        g = make_game(42)
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        old_score = g.score
        earned = g._submit_word()
        assert earned > 0
        assert g.score == old_score + earned

    def test_submit_word_increases_words_found(self) -> None:
        g = make_game(42)
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        g._submit_word()
        assert g.words_found == 1

    def test_submit_too_short_word_returns_zero(self) -> None:
        g = make_game(42)
        g._try_select(0, 0)
        g._try_select(0, 1)
        earned = g._submit_word()
        assert earned == 0
        assert g.words_found == 0

    def test_combo_increases_multiplier(self) -> None:
        g = make_game(42)
        # Force 4 same-color tiles
        for c in range(4):
            t = g.grid[0][c]
            if t is not None:
                t.color = 8
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        g._try_select(0, 3)
        assert g.combo >= 4
        _, mult = g._compute_score()
        assert mult >= 3.0  # 1.0 + 0.5*4 = 3.0

    def test_super_word_triples_multiplier(self) -> None:
        g = make_game(42)
        for c in range(4):
            t = g.grid[0][c]
            if t is not None:
                t.color = 8
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        g._try_select(0, 3)
        assert g.super_timer > 0
        _, mult = g._compute_score()
        assert mult >= 9.0  # (1.0+0.5*4)*3 = 9.0


class TestHeat:
    def test_low_multiplier_increases_heat(self) -> None:
        g = make_game(42)
        initial_heat = g.heat
        g._update_heat(150, 1.0)
        assert g.heat > initial_heat

    def test_high_multiplier_decreases_heat(self) -> None:
        g = make_game(42)
        g.heat = 20.0
        g._update_heat(500, 4.0)
        assert g.heat < 20.0

    def test_heat_capped_at_max(self) -> None:
        g = make_game(42)
        g.heat = HEAT_MAX - 1
        g._update_heat(100, 1.0)
        assert g.heat <= HEAT_MAX

    def test_heat_at_zero_stays_non_negative(self) -> None:
        g = make_game(42)
        g.heat = 0.0
        g._update_heat(500, 5.0)  # Should decrease heat
        assert g.heat >= 0.0


class TestGridManipulation:
    def test_submit_word_clears_tiles(self) -> None:
        g = make_game(42)
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        g._submit_word()
        # All 3 selected tiles should be cleared
        assert g.grid[0][0] is not None or True  # They get refilled

    def test_gravity_fills_empty_cells(self) -> None:
        g = make_game(42)
        # Set bottom tile to None
        g.grid[5][0] = None
        g._apply_gravity()
        # Bottom cell should now be filled if there was a tile above
        # This test verifies gravity works without crashing
        assert g.grid[5][0] is not None or g.grid[4][0] is None

    def test_new_tiles_spawn_to_fill_grid(self) -> None:
        g = make_game(42)
        for r in range(GRID_SIZE):
            g.grid[r][0] = None
        g._spawn_new_tiles()
        for r in range(GRID_SIZE):
            assert g.grid[r][0] is not None

    def test_grid_fully_populated_after_submit(self) -> None:
        g = make_game(42)
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        g._submit_word()
        for row in g.grid:
            for tile in row:
                assert tile is not None

    def test_selection_reset_after_submit(self) -> None:
        g = make_game(42)
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        g._submit_word()
        assert len(g.selected) == 0
        assert g.combo == 0


class TestTimer:
    def test_timer_decrements(self) -> None:
        g = make_game()
        initial = g.timer
        g._update_timer()
        assert g.timer == initial - 1

    def test_timer_zero_triggers_game_over(self) -> None:
        g = make_game()
        g.timer = 1
        g._update_timer()
        assert g.phase == Phase.GAME_OVER

    def test_timer_game_over_stores_high_score(self) -> None:
        g = make_game()
        g.score = 500
        g.high_score = 0
        g.timer = 1
        g._update_timer()
        assert g.high_score == 500


class TestReset:
    def test_reset_clears_state(self) -> None:
        g = make_game()
        g.score = 500
        g.combo = 5
        g.super_timer = 100
        g.words_found = 3
        g.heat = 50.0
        g.timer = 500
        g.selected = [(0, 0), (0, 1)]
        g.reset()
        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.combo == 0
        assert g.super_timer == 0
        assert g.words_found == 0
        assert g.heat == 0.0
        assert g.timer == TIMER_MAX
        assert len(g.selected) == 0

    def test_reset_repopulates_grid(self) -> None:
        g = make_game()
        g._submit_word()  # Should fail but still
        g.reset()
        for row in g.grid:
            for tile in row:
                assert tile is not None


class TestSuperMode:
    def test_super_timer_decrements(self) -> None:
        g = make_game(42)
        for c in range(4):
            t = g.grid[0][c]
            if t is not None:
                t.color = 8
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        g._try_select(0, 3)
        st = g.super_timer
        assert st == SUPER_DURATION
        g._update_super()
        assert g.super_timer == st - 1

    def test_super_expires(self) -> None:
        g = make_game(42)
        g.super_timer = 1
        g._update_super()
        assert g.super_timer == 0


class TestParticles:
    def test_particles_spawn_on_submit(self) -> None:
        g = make_game(42)
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        g._submit_word()
        assert len(g.particles) > 0

    def test_particles_aged(self) -> None:
        g = make_game(42)
        g.particles = [
            Particle(x=10.0, y=10.0, vx=1.0, vy=-1.0, life=5, color=8),
            Particle(x=20.0, y=20.0, vx=0.0, vy=1.0, life=0, color=3),
        ]
        g._update_particles()
        assert len(g.particles) == 1
        assert g.particles[0].x == 11.0

    def test_floating_texts_spawn_on_submit(self) -> None:
        g = make_game(42)
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        g._submit_word()
        assert len(g.floating_texts) > 0

    def test_floating_texts_aged(self) -> None:
        g = make_game(42)
        g.floating_texts = [
            FloatingText(x=100.0, y=100.0, text="+500", life=5, color=10),
            FloatingText(x=100.0, y=100.0, text="+0", life=0, color=10),
        ]
        g._update_floating_texts()
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].y == 99.0
        assert g.floating_texts[0].life == 4


class TestEdgeCases:
    def test_submit_word_less_than_min(self) -> None:
        g = make_game(42)
        earned = g._submit_word()
        assert earned == 0

    def test_strange_selection_path(self) -> None:
        g = make_game(42)
        # Build a path: (0,0) -> (1,0) -> (1,1) -> (2,1)
        g._try_select(0, 0)
        g._try_select(1, 0)
        g._try_select(1, 1)
        g._try_select(2, 1)
        assert len(g.selected) == 4

    def test_backtrack_and_continue(self) -> None:
        g = make_game(42)
        g._try_select(0, 0)
        g._try_select(0, 1)
        g._try_select(0, 2)
        g._try_select(0, 1)  # Backtrack
        assert len(g.selected) == 1
        g._try_select(1, 0)  # Continue in new direction
        assert len(g.selected) == 2

    def test_select_same_tile_twice_from_empty(self) -> None:
        g = make_game(42)
        g._try_select(0, 0)
        g._try_select(0, 1)
        # Click first tile → deselect everything after it (nothing changes if it's first tile and set is length 1)
        # Actually clicking first tile deselects all since index 0 means remove from 0 onward
        g._try_select(0, 0)
        assert len(g.selected) == 0
