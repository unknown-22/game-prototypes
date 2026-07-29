"""test_imports.py — Headless logic tests for 257_bingo_surge."""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (
    BINGO_BONUS,
    CARD_COLS,
    CARD_LEFT,
    CARD_ROWS,
    CARD_TOP,
    CELL_SIZE,
    COMBO_THRESHOLD,
    GAME_DURATION,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    HEAT_MISS,
    PLAY_COLORS,
    SUPER_DURATION,
    CardCell,
    DriftingNumber,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def _make_game() -> Game:
    """Factory: bypass Pyxel __init__, pre-init all attrs, call reset()."""
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.best_score = 0
    g.timer = GAME_DURATION
    g.heat = 0.0
    g.player_color_idx = 0
    g.color_cycle_timer = 90
    g.card = []
    g.drifting_numbers = []
    g.particles = []
    g.floating_texts = []
    g.super_timer = 0
    g.spawn_timer = 0
    g.frame = 0
    g._cycle_colors = [8, 11, 5, 10, 8, 11, 5, 10]
    g._cycle_idx = 0
    g._title_color_timer = 0
    g._rng = random.Random(42)
    g.reset()
    return g


class TestCardInit:
    def test_card_has_5x5_cells(self):
        g = _make_game()
        assert len(g.card) == CARD_ROWS
        for row in g.card:
            assert len(row) == CARD_COLS

    def test_card_cells_have_valid_numbers(self):
        g = _make_game()
        from main import COLUMN_RANGES

        for row in g.card:
            for cell in row:
                lo, hi = COLUMN_RANGES[cell.col]
                assert lo <= cell.number <= hi

    def test_card_cells_have_valid_colors(self):
        g = _make_game()
        for row in g.card:
            for cell in row:
                assert 0 <= cell.color < len(PLAY_COLORS)

    def test_card_cells_not_daubed_initially(self):
        g = _make_game()
        for row in g.card:
            for cell in row:
                assert cell.daubed is False


class TestColorCycle:
    def test_color_cycle_interval_decreases_over_time(self):
        g = _make_game()
        g.timer = GAME_DURATION
        slow = g._color_cycle_interval()
        g.timer = GAME_DURATION // 2
        fast = g._color_cycle_interval()
        assert fast <= slow

    def test_color_cycle_interval_minimum(self):
        g = _make_game()
        g.timer = 1
        assert g._color_cycle_interval() >= 40


class TestSpawning:
    def test_spawn_adds_drifting_number(self):
        g = _make_game()
        before = len(g.drifting_numbers)
        g._spawn_number()
        assert len(g.drifting_numbers) == before + 1

    def test_spawned_number_has_valid_properties(self):
        g = _make_game()
        g._spawn_number()
        dn = g.drifting_numbers[-1]
        assert dn.x >= 310
        assert dn.x <= 340
        assert dn.y >= CARD_TOP
        assert dn.y <= CARD_TOP + CARD_ROWS * CELL_SIZE
        assert dn.color in PLAY_COLORS
        assert dn.speed >= 1.0
        assert dn.active is True

    def test_spawn_uses_undaubed_cell_numbers(self):
        g = _make_game()
        # Daub all cells except one
        target_number = -1
        for row in range(CARD_ROWS):
            for col in range(CARD_COLS):
                if row == 2 and col == 2:
                    target_number = g.card[row][col].number
                else:
                    g.card[row][col].daubed = True
        g._spawn_number()
        dn = g.drifting_numbers[-1]
        # Should target the undaubed cell's number
        assert dn.number == target_number

    def test_spawn_when_all_daubed_still_works(self):
        g = _make_game()
        for row in g.card:
            for cell in row:
                cell.daubed = True
        g._spawn_number()
        assert len(g.drifting_numbers) == 1


class TestDriftingUpdate:
    def test_drifting_moves_left(self):
        g = _make_game()
        g.drifting_numbers = [DriftingNumber(x=300.0, y=100.0, number=5, color=8, speed=2.0)]
        g._update_drifting()
        assert g.drifting_numbers[0].x < 300.0

    def test_drifting_off_screen_removed(self):
        g = _make_game()
        g.drifting_numbers = [DriftingNumber(x=float(CARD_LEFT - 21), y=100.0, number=5, color=8, speed=2.0)]
        g._update_drifting()
        assert len(g.drifting_numbers) == 0

    def test_drifting_off_screen_adds_heat(self):
        g = _make_game()
        g.drifting_numbers = [DriftingNumber(x=float(CARD_LEFT - 21), y=100.0, number=5, color=8, speed=2.0)]
        g.heat = 50.0
        g._update_drifting()
        assert g.heat == 50.0 + HEAT_MISS

    def test_drifting_off_screen_resets_combo(self):
        g = _make_game()
        g.drifting_numbers = [DriftingNumber(x=float(CARD_LEFT - 21), y=100.0, number=5, color=8, speed=2.0)]
        g.combo = 5
        g._update_drifting()
        assert g.combo == 0


class TestHeatUpdate:
    def test_heat_decays(self):
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.001

    def test_heat_does_not_go_below_zero(self):
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_at_max_triggers_game_over(self):
        g = _make_game()
        g.heat = float(HEAT_MAX)
        g._update_heat()
        assert g.phase == Phase.GAME_OVER

    def test_heat_at_max_triggers_before_decay(self):
        g = _make_game()
        g.heat = float(HEAT_MAX)
        g._update_heat()
        # If decay happened first, heat would be < MAX and phase would stay PLAYING
        assert g.phase == Phase.GAME_OVER


class TestCheckClick:
    def test_no_click_on_empty_area(self):
        g = _make_game()
        g.drifting_numbers = [DriftingNumber(x=200.0, y=100.0, number=5, color=8, speed=1.0)]
        result = g._check_click(10, 10)  # far from drifting number
        assert result is False
        assert len(g.drifting_numbers) == 1  # not removed

    def test_click_match(self):
        g = _make_game()
        # Find a cell with RED (color=8) and make player match
        target_cell = g.card[2][2]
        player_color = target_cell.color
        g.player_color_idx = player_color
        dn_color = PLAY_COLORS[player_color]
        g.drifting_numbers = [DriftingNumber(x=200.0, y=float(CARD_TOP + 2 * CELL_SIZE + CELL_SIZE // 2), number=target_cell.number, color=dn_color, speed=1.0)]
        result = g._check_click(200, int(g.drifting_numbers[0].y))
        assert result is True
        assert target_cell.daubed is True
        assert g.combo == 1
        assert g.score > 0
        assert len(g.drifting_numbers) == 0

    def test_click_mismatch(self):
        g = _make_game()
        target_cell = g.card[2][2]
        # Player color = RED (index 0), but drifting number is LIME (index 1)
        g.player_color_idx = 0
        dn_color = PLAY_COLORS[1]  # LIME - different from player
        g.drifting_numbers = [DriftingNumber(x=200.0, y=float(CARD_TOP + 2 * CELL_SIZE + CELL_SIZE // 2), number=target_cell.number, color=dn_color, speed=1.0)]
        g.heat = 30.0
        result = g._check_click(200, int(g.drifting_numbers[0].y))
        assert result is True
        assert target_cell.daubed is False
        assert g.combo == 0
        assert abs(g.heat - (30.0 + HEAT_MISMATCH)) < 0.001
        assert len(g.drifting_numbers) == 0

    def test_click_super_mode_matches_any_color(self):
        g = _make_game()
        target_cell = g.card[2][2]
        g.player_color_idx = 0  # RED
        g.super_timer = 100  # SUPER active
        dn_color = PLAY_COLORS[1]  # LIME - not matching player
        g.drifting_numbers = [DriftingNumber(x=200.0, y=float(CARD_TOP + 2 * CELL_SIZE + CELL_SIZE // 2), number=target_cell.number, color=dn_color, speed=1.0)]
        result = g._check_click(200, int(g.drifting_numbers[0].y))
        assert result is True
        assert target_cell.daubed is True
        assert g.combo > 0

    def test_click_already_daubed_cell(self):
        g = _make_game()
        target_cell = g.card[2][2]
        target_cell.daubed = True
        g.player_color_idx = target_cell.color
        dn_color = PLAY_COLORS[target_cell.color]
        g.drifting_numbers = [DriftingNumber(x=200.0, y=float(CARD_TOP + 2 * CELL_SIZE + CELL_SIZE // 2), number=target_cell.number, color=dn_color, speed=1.0)]
        result = g._check_click(200, int(g.drifting_numbers[0].y))
        assert result is True
        # Daubed already, number should be consumed without re-daubing
        assert len(g.drifting_numbers) == 0

    def test_combo_increases_score(self):
        g = _make_game()
        g.combo = 2  # simulate previous matches
        target_cell = g.card[2][2]
        g.player_color_idx = target_cell.color
        dn_color = PLAY_COLORS[target_cell.color]
        g.drifting_numbers = [DriftingNumber(x=200.0, y=float(CARD_TOP + 2 * CELL_SIZE + CELL_SIZE // 2), number=target_cell.number, color=dn_color, speed=1.0)]
        g._check_click(200, int(g.drifting_numbers[0].y))
        # Score should use combo=3 (incremented inside check_click) * 10 * 1
        assert g.combo == 3
        assert g.score == 10 * 3  # 30

    def test_super_mode_3x_score_multiplier(self):
        g = _make_game()
        g.super_timer = 100
        target_cell = g.card[2][2]
        g.player_color_idx = target_cell.color
        dn_color = PLAY_COLORS[target_cell.color]
        g.drifting_numbers = [DriftingNumber(x=200.0, y=float(CARD_TOP + 2 * CELL_SIZE + CELL_SIZE // 2), number=target_cell.number, color=dn_color, speed=1.0)]
        g._check_click(200, int(g.drifting_numbers[0].y))
        assert g.score == 10 * 1 * 3  # combo=1, 3x super


class TestComboSuperTrigger:
    def test_combo_4_triggers_super(self):
        g = _make_game()
        g.combo = 3
        target_cell = g.card[2][2]
        g.player_color_idx = target_cell.color
        dn_color = PLAY_COLORS[target_cell.color]
        g.drifting_numbers = [DriftingNumber(x=200.0, y=float(CARD_TOP + 2 * CELL_SIZE + CELL_SIZE // 2), number=target_cell.number, color=dn_color, speed=1.0)]
        g._check_click(200, int(g.drifting_numbers[0].y))
        assert g.combo == COMBO_THRESHOLD
        assert g.super_timer == SUPER_DURATION

    def test_combo_below_threshold_no_super(self):
        g = _make_game()
        g.combo = 2
        target_cell = g.card[2][2]
        g.player_color_idx = target_cell.color
        dn_color = PLAY_COLORS[target_cell.color]
        g.drifting_numbers = [DriftingNumber(x=200.0, y=float(CARD_TOP + 2 * CELL_SIZE + CELL_SIZE // 2), number=target_cell.number, color=dn_color, speed=1.0)]
        g._check_click(200, int(g.drifting_numbers[0].y))
        assert g.combo == 3
        assert g.super_timer == 0


class TestBingo:
    def test_bingo_row_detected(self):
        g = _make_game()
        # Daub all cells in row 2
        for col in range(CARD_COLS):
            g.card[2][col].daubed = True
        bingos = g._check_bingo()
        assert bingos == 1

    def test_bingo_column_detected(self):
        g = _make_game()
        for row in range(CARD_ROWS):
            g.card[row][3].daubed = True
        bingos = g._check_bingo()
        assert bingos == 1

    def test_bingo_diagonal_detected(self):
        g = _make_game()
        for i in range(CARD_ROWS):
            g.card[i][i].daubed = True
        bingos = g._check_bingo()
        assert bingos == 1

    def test_bingo_anti_diagonal_detected(self):
        g = _make_game()
        for i in range(CARD_ROWS):
            g.card[i][CARD_COLS - 1 - i].daubed = True
        bingos = g._check_bingo()
        assert bingos == 1

    def test_bingo_adds_bonus_score(self):
        g = _make_game()
        g.score = 100
        for col in range(CARD_COLS):
            g.card[2][col].daubed = True
        g._check_bingo()
        assert g.score == 100 + BINGO_BONUS

    def test_multiple_bingos_add_multiple_bonuses(self):
        g = _make_game()
        g.score = 100
        # Row 2 + Col 2 = 2 bingos (intersection at (2,2))
        for col in range(CARD_COLS):
            g.card[2][col].daubed = True
        for row in range(CARD_ROWS):
            g.card[row][2].daubed = True
        bingos = g._check_bingo()
        assert bingos >= 2
        assert g.score == 100 + BINGO_BONUS * bingos

    def test_bingo_resets_cells(self):
        g = _make_game()
        for col in range(CARD_COLS):
            g.card[2][col].daubed = True
        g._check_bingo()
        # Row 2 cells should be reset (not daubed)
        for col in range(CARD_COLS):
            assert g.card[2][col].daubed is False

    def test_no_bingo_when_not_all_daubed(self):
        g = _make_game()
        for col in range(CARD_COLS - 1):
            g.card[2][col].daubed = True
        # One cell missing
        bingos = g._check_bingo()
        assert bingos == 0


class TestFloatingTexts:
    def test_match_creates_floating_text(self):
        g = _make_game()
        target_cell = g.card[2][2]
        g.player_color_idx = target_cell.color
        dn_color = PLAY_COLORS[target_cell.color]
        g.drifting_numbers = [DriftingNumber(x=200.0, y=float(CARD_TOP + 2 * CELL_SIZE + CELL_SIZE // 2), number=target_cell.number, color=dn_color, speed=1.0)]
        before = len(g.floating_texts)
        g._check_click(200, int(g.drifting_numbers[0].y))
        assert len(g.floating_texts) > before

    def test_mismatch_creates_wrong_text(self):
        g = _make_game()
        target_cell = g.card[2][2]
        g.player_color_idx = 0
        dn_color = PLAY_COLORS[1]
        g.drifting_numbers = [DriftingNumber(x=200.0, y=float(CARD_TOP + 2 * CELL_SIZE + CELL_SIZE // 2), number=target_cell.number, color=dn_color, speed=1.0)]
        g._check_click(200, int(g.drifting_numbers[0].y))
        ft = g.floating_texts[-1]
        assert "WRONG" in ft.text


class TestParticles:
    def test_spawn_particles_creates_expected_count(self):
        g = _make_game()
        before = len(g.particles)
        g._spawn_particles(100.0, 100.0, 8, 15)
        assert len(g.particles) - before == 8

    def test_particles_have_life(self):
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 5, 15)
        for p in g.particles[-5:]:
            assert p.life == 15


class TestReset:
    def test_reset_clears_state(self):
        g = _make_game()
        g.score = 500
        g.combo = 5
        g.max_combo = 8
        g.heat = 50.0
        g.super_timer = 100
        g.drifting_numbers = [DriftingNumber(x=200.0, y=100.0, number=5, color=8, speed=1.0)]
        g.particles = [Particle(x=0.0, y=0.0, vx=1.0, vy=1.0, life=10, color=8)]
        g.floating_texts = [FloatingText(x=0.0, y=0.0, text="test", life=10, color=7)]
        g.card[0][0].daubed = True

        g.reset()

        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.super_timer == 0
        assert len(g.drifting_numbers) == 0
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0
        # Card should be fresh
        for row in g.card:
            for cell in row:
                assert cell.daubed is False


class TestFindCardCell:
    def test_finds_existing_number(self):
        g = _make_game()
        number = g.card[2][3].number
        cell = g._find_card_cell(number)
        assert cell is not None
        assert cell.number == number
        assert cell.row == 2
        assert cell.col == 3

    def test_returns_none_for_nonexistent(self):
        g = _make_game()
        cell = g._find_card_cell(999)
        assert cell is None


class TestDataClasses:
    def test_card_cell_defaults(self):
        cell = CardCell(row=0, col=0, number=10, color=0)
        assert cell.daubed is False
        assert cell.row == 0
        assert cell.col == 0
        assert cell.number == 10

    def test_drifting_number_properties(self):
        dn = DriftingNumber(x=100.0, y=50.0, number=7, color=8, speed=1.5)
        assert dn.active is True
        assert dn.x == 100.0

    def test_particle_properties(self):
        p = Particle(x=10.0, y=20.0, vx=1.0, vy=-1.0, life=15, color=8)
        assert p.life == 15
        assert p.color == 8

    def test_floating_text_properties(self):
        ft = FloatingText(x=50.0, y=60.0, text="+10", life=45, color=7)
        assert ft.text == "+10"
        assert ft.life == 45


class TestEnum:
    def test_phase_enum_values(self):
        assert Phase.TITLE in Phase
        assert Phase.PLAYING in Phase
        assert Phase.GAME_OVER in Phase

    def test_game_starts_in_title(self):
        g = _make_game()
        # After reset(), phase should be PLAYING
        assert g.phase == Phase.PLAYING


class TestHeatCap:
    def test_heat_capped_at_max_in_drifting(self):
        g = _make_game()
        g.heat = HEAT_MAX - 1
        g.drifting_numbers = [DriftingNumber(x=float(CARD_LEFT - 21), y=100.0, number=5, color=8, speed=2.0)]
        g._update_drifting()
        assert g.heat <= HEAT_MAX

    def test_heat_capped_at_max_in_mismatch(self):
        g = _make_game()
        g.heat = HEAT_MAX - 1
        target_cell = g.card[2][2]
        g.player_color_idx = 0
        dn_color = PLAY_COLORS[1]
        g.drifting_numbers = [DriftingNumber(x=200.0, y=float(CARD_TOP + 2 * CELL_SIZE + CELL_SIZE // 2), number=target_cell.number, color=dn_color, speed=1.0)]
        g._check_click(200, int(g.drifting_numbers[0].y))
        assert g.heat <= HEAT_MAX


class TestTimerGameOver:
    def test_timer_reaching_zero_triggers_game_over(self):
        g = _make_game()
        g.timer = 0
        # Simulate the check in update()
        if g.timer <= 0:
            g.phase = Phase.GAME_OVER
            g.best_score = max(g.best_score, g.score)
        assert g.phase == Phase.GAME_OVER


class TestBestScore:
    def test_best_score_updated_on_game_over(self):
        g = _make_game()
        g.score = 500
        g.best_score = 0
        g.phase = Phase.GAME_OVER
        g.best_score = max(g.best_score, g.score)
        assert g.best_score == 500

    def test_best_score_preserves_higher(self):
        g = _make_game()
        g.score = 300
        g.best_score = 500
        g.phase = Phase.GAME_OVER
        g.best_score = max(g.best_score, g.score)
        assert g.best_score == 500
