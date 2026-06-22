"""Tests for BINGO SURGE game logic. All tests are headless (no pyxel init/run)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (  # type: ignore[import-untyped]
    CALL_DELAY,
    SHAKE_FRAMES,
    SUPER_DAUB_DURATION,
    TOTAL_CALLS,
    NUM_COLORS,
    Cell,
    CallInfo,
    FloatingText,
    Particle,
    Phase,
    Game,
)


def _make_game(seed: int = 42) -> Game:
    """Factory for a fresh headless Game instance. Uses __new__ to bypass pyxel init/run."""
    g = Game.__new__(Game)
    g.phase = Phase.PLAYING
    g.cells = g._generate_card()
    g.call_queue = g._generate_calls()
    g.current_call_index = 0
    g.call_timer = CALL_DELAY
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0
    g.bingo_count = 0
    g.bingo_lines = set()
    g.super_daub_timer = 0
    g.shake_timer = 0
    g.flash_timer = 0
    g.particles = []
    g.floating_texts = []
    g.title_blink = 0
    g.game_over_blink = 0
    g.hits = 0
    g.missed = 0
    g.wrong_color = 0
    g.total_marks = 0
    g._call_handled = False
    if g.call_queue:
        g.call_queue[0].active = True
    return g


def _setup_card(game: Game, cells: list[list[Cell]]) -> None:
    """Override the card with a pre-configured one for deterministic tests."""
    game.cells = cells


def _setup_calls(game: Game, calls: list[CallInfo]) -> None:
    """Override the call queue."""
    game.call_queue = calls
    game.current_call_index = 0
    game.call_timer = CALL_DELAY
    game._call_handled = False
    if calls:
        calls[0].active = True


def _cell(n: int, c: int, marked: bool = False) -> Cell:
    return Cell(number=n, color=c, marked=marked)


# ============================================================
# 1. Card generation
# ============================================================


class TestCardGeneration:
    def test_5x5_grid(self) -> None:
        g = _make_game()
        card = g._generate_card()
        assert len(card) == 5
        for row in card:
            assert len(row) == 5

    def test_unique_numbers(self) -> None:
        g = _make_game()
        card = g._generate_card()
        numbers: list[int] = []
        for row in card:
            for cell in row:
                numbers.append(cell.number)
        assert len(set(numbers)) == 25
        assert all(1 <= n <= 75 for n in numbers)

    def test_center_free_space(self) -> None:
        g = _make_game()
        card = g._generate_card()
        assert card[2][2].marked is True

    def test_valid_colors(self) -> None:
        g = _make_game()
        card = g._generate_card()
        for row in card:
            for cell in row:
                assert 0 <= cell.color < NUM_COLORS


# ============================================================
# 2. Call generation
# ============================================================


class TestCallGeneration:
    def test_generates_50_calls(self) -> None:
        g = _make_game()
        calls = g._generate_calls()
        assert len(calls) == TOTAL_CALLS

    def test_call_colors_valid(self) -> None:
        g = _make_game()
        calls = g._generate_calls()
        for call in calls:
            assert 0 <= call.color < NUM_COLORS
            assert 1 <= call.number <= 75


# ============================================================
# 3. Advance call
# ============================================================


class TestAdvanceCall:
    def test_advances_index(self) -> None:
        g = _make_game()
        g.current_call_index = 0
        g.call_timer = 0
        g._advance_call()
        assert g.current_call_index == 1
        assert g.call_timer == CALL_DELAY

    def test_last_call_triggers_game_over(self) -> None:
        g = _make_game()
        g.current_call_index = TOTAL_CALLS - 1
        g.call_timer = 0
        result = g._advance_call()
        assert result == "game_over"
        assert g.phase == Phase.GAME_OVER

    def test_deactivates_previous_activates_next(self) -> None:
        g = _make_game()
        g.call_queue[0].active = True
        g._advance_call()
        assert g.call_queue[0].active is False
        assert g.call_queue[1].active is True

    def test_missed_call_heat(self) -> None:
        g = _make_game()
        g.call_timer = 0
        g._advance_call()
        # When call_timer expires in update(), _update_heat(15) is called
        # and _call_handled stays False so missed increments
        # This test verifies _advance_call itself resets _call_handled
        assert g._call_handled is False


# ============================================================
# 4. Is correct cell / color match
# ============================================================


class TestCellChecks:
    def test_is_correct_cell_true(self) -> None:
        g = _make_game()
        cell = _cell(42, 0)
        _setup_card(g, [[cell] + [_cell(i, 0) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=42, color=0)])
        g.call_queue[0].active = True
        assert g._is_correct_cell(0, 0) is True

    def test_is_correct_cell_false(self) -> None:
        g = _make_game()
        cell = _cell(42, 0)
        _setup_card(g, [[cell] + [_cell(i, 0) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=99, color=0)])
        g.call_queue[0].active = True
        assert g._is_correct_cell(0, 0) is False

    def test_is_correct_cell_no_call(self) -> None:
        g = _make_game()
        g.current_call_index = TOTAL_CALLS
        assert g._is_correct_cell(0, 0) is False

    def test_cell_matches_color_true(self) -> None:
        g = _make_game()
        _setup_card(g, [[_cell(42, 2)] + [_cell(i, 0) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=42, color=2)])
        g.call_queue[0].active = True
        assert g._cell_matches_called_color(0, 0) is True

    def test_cell_matches_color_false(self) -> None:
        g = _make_game()
        _setup_card(g, [[_cell(42, 2)] + [_cell(i, 0) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=42, color=1)])
        g.call_queue[0].active = True
        assert g._cell_matches_called_color(0, 0) is False


# ============================================================
# 5. Combo
# ============================================================


class TestCombo:
    def test_combo_increments_on_match(self) -> None:
        g = _make_game()
        g.combo = 0
        g._update_combo(True)
        assert g.combo == 1
        g._update_combo(True)
        assert g.combo == 2
        assert g.max_combo == 2

    def test_combo_resets_on_miss(self) -> None:
        g = _make_game()
        g.combo = 3
        g.max_combo = 3
        g._update_combo(False)
        assert g.combo == 0
        assert g.max_combo == 3  # max preserved

    def test_combo_frozen_during_super_daub(self) -> None:
        g = _make_game()
        g.combo = 4
        g.super_daub_timer = 100
        g._update_combo(True)
        assert g.combo == 4  # unchanged
        g._update_combo(False)
        assert g.combo == 4  # unchanged


# ============================================================
# 6. Heat
# ============================================================


class TestHeat:
    def test_heat_accumulates(self) -> None:
        g = _make_game()
        g._update_heat(25)
        assert g.heat == 25
        g._update_heat(40)
        assert g.heat == 65

    def test_heat_overflow_triggers_shake(self) -> None:
        g = _make_game()
        g.heat = 60
        g._update_heat(40)
        assert g.heat == 0  # reset after shake
        assert g.shake_timer == SHAKE_FRAMES

    def test_clamped_at_max(self) -> None:
        g = _make_game()
        g.heat = 90
        g.shake_timer = 1  # already shaking, no new shake
        g._update_heat(50)
        assert g.heat == 100  # clamped

    def test_no_shake_if_already_shaking(self) -> None:
        g = _make_game()
        g.shake_timer = 50
        g.heat = 80
        g._update_heat(30)
        assert g.shake_timer == 50  # unchanged


# ============================================================
# 7. Bingo check
# ============================================================


class TestBingoCheck:
    def test_row_bingo(self) -> None:
        g = _make_game()
        # Only row 0 is fully marked; everything else is unmarked
        cells = [[_cell(r * 5 + c, 0, marked=False) for c in range(5)] for r in range(5)]
        for c in range(5):
            cells[0][c].marked = True
        _setup_card(g, cells)
        lines = g._check_bingo()
        assert "R0" in lines
        assert len(lines) == 1

    def test_column_bingo(self) -> None:
        g = _make_game()
        cells = [[_cell(i, 0, marked=False) for i in range(5)] for _ in range(5)]
        for r in range(5):
            cells[r][2].marked = True
        _setup_card(g, cells)
        lines = g._check_bingo()
        assert "C2" in lines

    def test_diagonal_bingo(self) -> None:
        g = _make_game()
        cells = [[_cell(i, 0, marked=False) for i in range(5)] for _ in range(5)]
        # Mark diagonal
        for i in range(5):
            cells[i][i].marked = True
        _setup_card(g, cells)
        lines = g._check_bingo()
        assert "D0" in lines

    def test_anti_diagonal_bingo(self) -> None:
        g = _make_game()
        cells = [[_cell(i, 0, marked=False) for i in range(5)] for _ in range(5)]
        for i in range(5):
            cells[i][4 - i].marked = True
        _setup_card(g, cells)
        lines = g._check_bingo()
        assert "D1" in lines

    def test_no_duplicate_bingo(self) -> None:
        g = _make_game()
        cells = [[_cell(i, 0, marked=True) for i in range(5)] for _ in range(5)]
        _setup_card(g, cells)
        g.bingo_lines.add("R0")
        lines = g._check_bingo()
        assert "R0" not in lines  # already counted

    def test_bingo_score_bonus_escalates(self) -> None:
        g = _make_game()
        # Initially only row 0 fully marked
        cells = [[_cell(r * 5 + c, 0, marked=False) for c in range(5)] for r in range(5)]
        for c in range(5):
            cells[0][c].marked = True
        _setup_card(g, cells)
        # First bingo
        lines1 = g._check_bingo()
        g.bingo_count += len(lines1)
        g.score += 500 * g.bingo_count
        assert g.bingo_count == 1
        assert g.score == 500
        # Now also mark row 1 fully for a second bingo
        for c in range(5):
            cells[1][c].marked = True
        _setup_card(g, cells)
        g.bingo_lines = {"R0"}
        lines2 = g._check_bingo()
        g.bingo_count += len(lines2)
        g.score += 500 * g.bingo_count
        assert g.bingo_count == 2
        assert g.score == 500 + 1000  # 1500 total


# ============================================================
# 8. Super Daub
# ============================================================


class TestSuperDaub:
    def test_activate_sets_timer(self) -> None:
        g = _make_game()
        g._activate_super_daub()
        assert g.super_daub_timer == SUPER_DAUB_DURATION

    def test_update_decrements_timer(self) -> None:
        g = _make_game()
        g.super_daub_timer = 50
        g._update_super_daub()
        assert g.super_daub_timer == 49

    def test_update_stops_at_zero(self) -> None:
        g = _make_game()
        g.super_daub_timer = 1
        g._update_super_daub()
        assert g.super_daub_timer == 0
        g._update_super_daub()
        assert g.super_daub_timer == 0

    def test_auto_daub_marks_matching_color(self) -> None:
        g = _make_game()
        cells = [[_cell(i + j * 5, (i + j) % NUM_COLORS, marked=False) for i in range(5)] for j in range(5)]
        _setup_card(g, cells)
        # Count BEFORE auto_daub
        expected = sum(1 for row in cells for c in row if c.color == 0 and not c.marked)
        count = g._auto_daub(0)  # color 0 = RED
        assert count == expected
        # All color-0 cells should now be marked
        for row in cells:
            for c in row:
                if c.color == 0:
                    assert c.marked is True

    def test_auto_daub_awards_score(self) -> None:
        g = _make_game()
        # Pattern that avoids any complete row/col/diag of color 0
        cells = [[_cell(r * 5 + c, (r + 2 * c) % NUM_COLORS, marked=False) for c in range(5)] for r in range(5)]
        _setup_card(g, cells)
        old_score = g.score
        g._auto_daub(0)
        # 8 cells have color 0, no bingo triggered
        assert g.score == old_score + 8 * 300

    def test_auto_daub_does_nothing_for_wrong_color(self) -> None:
        g = _make_game()
        cells = [[_cell(i, 1, marked=False) for i in range(5)] for _ in range(5)]
        _setup_card(g, cells)
        count = g._auto_daub(0)  # looking for color 0, but all are color 1
        assert count == 0


# ============================================================
# 9. Handle click
# ============================================================


class TestHandleClick:
    def test_correct_color_click(self) -> None:
        g = _make_game()
        _setup_card(g, [[_cell(42, 0, marked=False)] + [_cell(i, 0) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=42, color=0)])
        g.call_queue[0].active = True
        result = g._handle_click(0, 0)
        assert result == "correct_color"
        assert g.cells[0][0].marked is True
        assert g.combo == 1
        assert g.hits == 1

    def test_wrong_color_click(self) -> None:
        g = _make_game()
        _setup_card(g, [[_cell(42, 1, marked=False)] + [_cell(i, 0) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=42, color=0)])
        g.call_queue[0].active = True
        result = g._handle_click(0, 0)
        assert result == "wrong_color"
        assert g.cells[0][0].marked is True  # still marked
        assert g.combo == 0  # combo reset
        assert g.heat == 25
        assert g.wrong_color == 1

    def test_wrong_number_click(self) -> None:
        g = _make_game()
        _setup_card(g, [[_cell(99, 0, marked=False)] + [_cell(i, 0) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=42, color=0)])
        g.call_queue[0].active = True
        result = g._handle_click(0, 0)
        assert result == "wrong_number"
        assert g.cells[0][0].marked is False  # NOT marked
        assert g.combo == 0
        assert g.heat == 40

    def test_already_marked_ignored(self) -> None:
        g = _make_game()
        _setup_card(g, [[_cell(42, 0, marked=True)] + [_cell(i, 0) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=42, color=0)])
        g.call_queue[0].active = True
        result = g._handle_click(0, 0)
        assert result == "already_marked"

    def test_click_during_shake_ignored(self) -> None:
        g = _make_game()
        _setup_card(g, [[_cell(42, 0, marked=False)] + [_cell(i, 0) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=42, color=0)])
        g.shake_timer = 10
        result = g._handle_click(0, 0)
        assert result == "shake"

    def test_click_when_not_playing_ignored(self) -> None:
        g = _make_game()
        g.phase = Phase.TITLE
        result = g._handle_click(0, 0)
        assert result == "no_play"

    def test_correct_color_scores_with_combo(self) -> None:
        g = _make_game()
        _setup_card(g, [[_cell(42, 0, marked=False)] + [_cell(i, 0) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=42, color=0)])
        g.combo = 2
        g._handle_click(0, 0)
        # combo goes from 2 to 3, score = 100 * 3 = 300
        assert g.score == 300

    def test_super_daub_triggers_at_combo_4(self) -> None:
        g = _make_game()
        _setup_card(g, [[_cell(42, 0, marked=False)] + [_cell(i, 1) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=42, color=0)])
        g.combo = 3
        g._handle_click(0, 0)
        assert g.combo == 4
        assert g.super_daub_timer == SUPER_DAUB_DURATION

    def test_score_multiplied_during_super_daub(self) -> None:
        g = _make_game()
        _setup_card(g, [[_cell(42, 0, marked=False)] + [_cell(i, 0) for i in range(1, 5)] for _ in range(5)])
        _setup_calls(g, [CallInfo(number=42, color=0)])
        g.super_daub_timer = 100
        g.combo = 1
        g._handle_click(0, 0)
        # During super daub combo is FROZEN: combo stays 1
        # multiplier = max(1, 1) * 3 = 3
        # bonus = 100 * 3 = 300
        assert g.score == 300

    def test_handle_click_triggers_bingo_bonus(self) -> None:
        g = _make_game()
        # Set up a card where only row 0 has cols 1-4 marked.
        # Clicking (0,0) on the correct number will complete row 0 bingo.
        cells = [[_cell(42, 0, marked=False)] + [_cell(i + 100, 0, marked=True) for i in range(1, 5)] for _ in range(5)]
        # Rows 1-4: all unmarked (different numbers so they don't interfere)
        for r in range(1, 5):
            for c in range(5):
                cells[r][c].marked = False
        _setup_card(g, cells)
        _setup_calls(g, [CallInfo(number=42, color=0)])
        g.combo = 0
        g._handle_click(0, 0)
        assert g.bingo_count == 1
        # Score = 100 (base correct with combo 1) + 500 (first bingo) = 600
        assert g.score == 600
        assert g.flash_timer == 3


# ============================================================
# 10. Particles and floating texts
# ============================================================


class TestParticles:
    def test_spawn_mark_particles(self) -> None:
        g = _make_game()
        g._spawn_mark_particles(0, 0)
        assert len(g.particles) == 8

    def test_update_particles_decrements_life(self) -> None:
        g = _make_game()
        g.particles = [Particle(x=0, y=0, vx=1, vy=-1, life=5, color=8)]
        g._update_particles()
        assert g.particles[0].life == 4

    def test_dead_particles_removed(self) -> None:
        g = _make_game()
        g.particles = [Particle(x=0, y=0, vx=1, vy=-1, life=1, color=8)]
        g._update_particles()
        assert len(g.particles) == 0

    def test_floating_text_moves_up(self) -> None:
        g = _make_game()
        g.floating_texts = [FloatingText(x=100, y=100, text="TEST", life=10, color=8)]
        orig_y = g.floating_texts[0].y
        g._update_floating_texts()
        assert g.floating_texts[0].y < orig_y

    def test_floating_text_removes_when_dead(self) -> None:
        g = _make_game()
        g.floating_texts = [FloatingText(x=100, y=100, text="TEST", life=1, color=8)]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


# ============================================================
# 11. Full game flow
# ============================================================


class TestGameFlow:
    def test_update_call_timer_counts_down(self) -> None:
        g = _make_game()
        orig = g.call_timer
        g.update()
        assert g.call_timer == orig - 1

    def test_update_advances_call_when_timer_zero(self) -> None:
        g = _make_game()
        g.call_timer = 1
        g.current_call_index = 0
        g._call_handled = False
        g.update()
        # After one update, call_timer decrements to 0, then _advance_call resets it to CALL_DELAY
        assert g.call_timer == CALL_DELAY
        assert g.current_call_index == 1  # advanced to next call

    def test_update_does_not_advance_in_title(self) -> None:
        g = _make_game()
        g.phase = Phase.TITLE
        orig_call = g.current_call_index
        g.update()
        assert g.current_call_index == orig_call

    def test_reset_initializes_all_state(self) -> None:
        g = _make_game(seed=123)
        g.combo = 5
        g.heat = 80
        g.bingo_count = 3
        g.bingo_lines.add("R0")
        g.reset()
        assert g.phase == Phase.PLAYING
        assert g.combo == 0
        assert g.heat == 0
        assert g.bingo_count == 0
        assert len(g.bingo_lines) == 0
        assert g.score == 0
        assert g.shake_timer == 0
        assert g.super_daub_timer == 0
        assert g.hits == 0
        assert g.missed == 0
        assert len(g.cells) == 5
        assert len(g.call_queue) == TOTAL_CALLS

    def test_full_game_runs_all_50_calls(self) -> None:
        """Simulate running through all calls — each call either gets a hit or becomes missed."""
        # Set up the game manually so every cell matches a call
        g = _make_game(seed=42)
        # Run update for 50 calls * 90 frames, should result in game over
        for _ in range(TOTAL_CALLS * CALL_DELAY + 10):
            g.update()
            if g.phase == Phase.GAME_OVER:
                break
        assert g.phase == Phase.GAME_OVER
        assert g.current_call_index >= TOTAL_CALLS
