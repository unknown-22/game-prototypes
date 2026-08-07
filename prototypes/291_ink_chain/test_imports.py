from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "prototypes" / "291_ink_chain"))

from main import (  # noqa: E402
    CA_INTERVAL_INITIAL,
    CA_INTERVAL_MIN,
    CA_SPREAD_CHANCE,
    COLOR_CYCLE_INITIAL,
    COLOR_CYCLE_MIN,
    COLS,
    GRID_ORIGIN_X,
    GRID_ORIGIN_Y,
    HEAT_CAP,
    HEAT_DECAY_PER_FRAME,
    HEAT_PER_MISMATCH,
    INK_COLORS,
    ROWS,
    SUPER_DURATION,
    SUPER_THRESHOLD,
    TIMER_FRAMES,
    CELL,
    Game,
    Particle,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    game = Game.__new__(Game)
    game._init_attrs()
    game._rng = random.Random(seed)
    game.reset()
    return game


class TestGameInit:
    def test_reset_initializes_state(self) -> None:
        game = _make_game()
        assert game.phase == Phase.PLAYING
        assert game.score == 0
        assert game.combo == 0
        assert game.max_combo == 0
        assert game.heat == 0.0
        assert game.timer == TIMER_FRAMES
        assert game.super_timer == 0
        assert game.color_idx == 0
        assert game.last_painted_color == 0
        assert all(all(cell == 0 for cell in row) for row in game.grid)

    def test_grid_dimensions(self) -> None:
        game = _make_game()
        assert len(game.grid) == ROWS
        for row in game.grid:
            assert len(row) == COLS


class TestHandleClick:
    def test_first_click_sets_last_painted_color(self) -> None:
        game = _make_game()
        result = game._handle_click(0, 0)
        assert result is True
        assert game.last_painted_color == INK_COLORS[0]
        assert game.grid[0][0] == INK_COLORS[0]
        assert game.combo == 1
        assert game.heat == 0.0

    def test_click_occupied_cell_returns_false(self) -> None:
        game = _make_game()
        game.grid[0][0] = INK_COLORS[0]
        result = game._handle_click(0, 0)
        assert result is False

    def test_same_color_builds_combo(self) -> None:
        game = _make_game()
        game._handle_click(0, 0)
        game._handle_click(1, 0)
        assert game.combo == 2
        assert game.heat == 0.0

    def test_wrong_color_resets_combo_and_adds_heat(self) -> None:
        game = _make_game()
        game._handle_click(0, 0)
        game.color_idx = 1  # different color
        game._handle_click(1, 0)
        assert game.combo == 0
        assert game.heat == HEAT_PER_MISMATCH

    def test_super_brush_prevents_mismatch_heat(self) -> None:
        game = _make_game()
        game.super_timer = SUPER_DURATION
        game._handle_click(0, 0)
        game.color_idx = 1
        game._handle_click(1, 0)
        assert game.combo == 2
        assert game.heat == 0.0

    def test_combo_4_triggers_super_brush(self) -> None:
        game = _make_game()
        for i in range(4):
            game._handle_click(i, 0)
        assert game.super_timer == SUPER_DURATION

    def test_super_brush_gives_3x_score(self) -> None:
        game = _make_game()
        game._handle_click(0, 0)
        game._handle_click(1, 0)
        game._handle_click(2, 0)
        game._handle_click(3, 0)  # triggers super
        base_score = game.score
        game._handle_click(4, 0)
        delta = game.score - base_score
        assert delta == 10 * 5 * 3  # base * combo * 3x super

    def test_score_uses_combo_multiplier(self) -> None:
        game = _make_game()
        game._handle_click(0, 0)
        assert game.score == 10 * 1
        game._handle_click(1, 0)
        assert game.score == 10 * 1 + 10 * 2


class TestHeat:
    def test_heat_decays_over_time(self) -> None:
        game = _make_game()
        game.heat = 30.0
        for _ in range(100):
            game._update_heat()
        assert game.heat < 30.0

    def test_heat_capped_at_100(self) -> None:
        game = _make_game()
        game.heat = HEAT_CAP
        game._handle_click(0, 0)  # should not go above cap
        assert game.heat <= HEAT_CAP

    def test_heat_100_triggers_game_over(self) -> None:
        game = _make_game()
        game.heat = HEAT_CAP
        game._update_heat()
        assert game.phase == Phase.GAME_OVER


class TestTimer:
    def test_timer_zero_triggers_game_over(self) -> None:
        game = _make_game()
        game.timer = 1
        game._update_playing()
        assert game.timer == 0
        assert game.phase == Phase.GAME_OVER

    def test_best_score_updates_on_game_over(self) -> None:
        game = _make_game()
        game.score = 500
        game.timer = 1
        game._update_playing()
        assert game.best_score == 500


class TestCABleed:
    def test_ca_bleed_spreads_ink(self) -> None:
        game = _make_game(seed=42)
        game.grid[4][5] = INK_COLORS[0]
        # Run multiple CA cycles
        for _ in range(20):
            game._ca_bleed()
        # Check that at least one cell adjacent to (5,4) got filled
        spread = any(
            game.grid[4 + dy][5 + dx] != 0
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
            if 0 <= 5 + dx < COLS and 0 <= 4 + dy < ROWS
        )
        assert spread

    def test_ca_does_not_overwrite_painted_cells(self) -> None:
        game = _make_game(seed=42)
        game.grid[4][5] = INK_COLORS[0]
        game.grid[4][6] = INK_COLORS[1]
        # After bleed, (5,6) should still have its original color
        for _ in range(20):
            game._ca_bleed()
        assert game.grid[4][6] == INK_COLORS[1]


class TestDifficultyEscalation:
    def test_color_cycle_interval_decreases(self) -> None:
        game = _make_game()
        game._elapsed_frames = TIMER_FRAMES // 2
        game._color_cycle_timer = 1
        game._update_playing()
        expected = int(COLOR_CYCLE_INITIAL - (COLOR_CYCLE_INITIAL - COLOR_CYCLE_MIN) * 0.5)
        assert game._color_cycle_timer == expected

    def test_ca_interval_decreases(self) -> None:
        game = _make_game()
        game._elapsed_frames = TIMER_FRAMES // 2
        game._ca_timer = 1
        game._update_playing()
        expected = int(CA_INTERVAL_INITIAL - (CA_INTERVAL_INITIAL - CA_INTERVAL_MIN) * 0.5)
        assert game._ca_timer == expected


class TestMouseToGrid:
    def test_mouse_to_grid_inside(self) -> None:
        g = _make_game()
        col, row = (GRID_ORIGIN_X + 3 * CELL + CELL // 2), (GRID_ORIGIN_Y + 2 * CELL + CELL // 2)
        result = Game.mouse_to_grid(col, row)
        assert result == (3, 2)

    def test_mouse_to_grid_outside(self) -> None:
        result = Game.mouse_to_grid(0, 0)
        assert result is None


class TestParticleSystem:
    def test_spawn_particles(self) -> None:
        game = _make_game()
        game._spawn_particles(100, 100, 5, 8)
        assert len(game.particles) == 5
        for p in game.particles:
            assert p.color == 8
            assert p.life > 0
            assert p.max_life > 0

    def test_update_particles_removes_dead(self) -> None:
        game = _make_game()
        game._spawn_particles(100, 100, 3, 8)
        for p in game.particles:
            p.life = 0
        game._update_particles()
        assert len(game.particles) == 0


class TestGridFullEdgeCase:
    def test_full_grid_returns_false(self) -> None:
        game = _make_game()
        for r in range(ROWS):
            for c in range(COLS):
                game.grid[r][c] = INK_COLORS[0]
        assert game._handle_click(0, 0) is False


class TestSuperBrushDecay:
    def test_super_brush_decay_resets_combo(self) -> None:
        game = _make_game()
        game.super_timer = 1
        game.combo = 5
        game.last_painted_color = INK_COLORS[0]
        game._update_playing()
        assert game.super_timer == 0
        assert game.combo == 0
        assert game.last_painted_color == 0
