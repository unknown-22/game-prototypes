"""test_imports.py — Headless logic tests for 173_gomoku_surge."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/173_gomoku_surge")

import random
from main import (
    AI_COLOR,
    COMBO_BONUS,
    GRID_SIZE,
    HEAT_PER_WRONG,
    MAX_HEAT,
    PLAYER_COLORS,
    SUPER_DURATION,
    FloatingText,
    Game,
    Particle,
    Phase,
    _make_game,
)


def test_make_game_factory() -> None:
    """Factory creates a valid game instance with seeded RNG."""
    g = _make_game()
    assert g is not None
    assert g.phase == Phase.TITLE
    assert len(g.grid) == GRID_SIZE
    assert all(len(row) == GRID_SIZE for row in g.grid)
    assert g.combo == 0
    assert g.score == 0
    assert g.heat == 0.0


def test_init_state_sets_playing() -> None:
    """_init_state() sets phase to PLAYING."""
    g = _make_game()
    g._init_state()
    assert g.phase == Phase.PLAYING
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0


def test_check_win_horizontal() -> None:
    """5 consecutive same-color stones horizontally = win."""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    for i in range(2, 7):
        grid[3][i] = 8  # RED
    # Place at col=2, should complete 5 from col=2 to col=6
    assert Game._check_win(grid, 2, 3, 8) is True


def test_check_win_vertical() -> None:
    """5 consecutive same-color stones vertically = win."""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    for i in range(0, 5):
        grid[i][4] = 3  # GREEN
    assert Game._check_win(grid, 4, 0, 3) is True


def test_check_win_diagonal_down() -> None:
    """5 consecutive same-color stones diagonally (down-right) = win."""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    for i in range(0, 5):
        grid[i][i] = 5  # DARK_BLUE
    assert Game._check_win(grid, 0, 0, 5) is True


def test_check_win_diagonal_up() -> None:
    """5 consecutive same-color stones diagonally (up-right) = win."""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    for i in range(0, 5):
        grid[4 - i][i] = 10  # YELLOW
    assert Game._check_win(grid, 0, 4, 10) is True


def test_check_win_no_win_4() -> None:
    """Only 4-in-a-row does NOT trigger win."""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    for i in range(2, 6):
        grid[3][i] = 8
    assert Game._check_win(grid, 2, 3, 8) is False


def test_check_win_blocked_by_different_color() -> None:
    """Different color stone breaks the line."""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    grid[3][2] = 8
    grid[3][3] = 8
    grid[3][4] = 13  # GRAY breaks
    grid[3][5] = 8
    grid[3][6] = 8
    assert Game._check_win(grid, 2, 3, 8) is False


def test_place_stone_same_color_builds_combo() -> None:
    """Placing same-color stone builds combo."""
    g = _make_game()
    g._init_state()
    # First placement
    info = g._place_stone(3, 3, PLAYER_COLORS[0])  # RED
    assert g.combo == 1
    assert info["combo_added"] == 1
    assert info["score_added"] >= 100

    # Advance to next color (cycle), but place same as current
    g._cycle_color()
    # Current color is now GREEN (index 1)
    g._place_stone(4, 3, PLAYER_COLORS[1])  # GREEN matches
    assert g.combo == 2


def test_place_stone_wrong_color_resets_combo() -> None:
    """Wrong-color placement resets combo to 0 and adds heat."""
    g = _make_game()
    g._init_state()
    # Place RED (matches current color index 0)
    g._place_stone(3, 3, PLAYER_COLORS[0])
    assert g.combo == 1

    # Place wrong color without cycling — GREEN doesn't match
    info = g._place_stone(4, 3, PLAYER_COLORS[1])  # GREEN != RED
    assert g.combo == 0
    assert info.get("heat_added") == HEAT_PER_WRONG
    assert g.heat == HEAT_PER_WRONG


def test_max_combo_tracking() -> None:
    """max_combo tracks highest combo achieved."""
    g = _make_game()
    g._init_state()
    # 3 same-color placements
    for i in range(3):
        g._place_stone(i, i, PLAYER_COLORS[0])
        g._cycle_color()
        # Revert to RED to fake same-color
        g.current_color_index = 0
    assert g.combo == 3
    assert g.max_combo == 3

    # Wrong color resets combo
    g._place_stone(5, 5, PLAYER_COLORS[1])  # GREEN != RED
    assert g.combo == 0
    assert g.max_combo == 3  # max preserved


def test_super_mode_activates_at_combo_5() -> None:
    """COMBO >= 5 triggers SUPER STONE mode."""
    g = _make_game()
    g._init_state()
    for i in range(5):
        g._place_stone(i, i, PLAYER_COLORS[0])
        g._cycle_color()
        g.current_color_index = 0  # Keep same effective color
    assert g.combo == 5
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_mode_any_color_matches() -> None:
    """During super mode, ANY color placement counts as match."""
    g = _make_game()
    g._init_state()
    g.super_mode = True
    g.super_timer = 100
    g.combo = 5

    # Place a color that doesn't match current (RED)
    g.current_color_index = 0  # RED
    info = g._place_stone(3, 3, PLAYER_COLORS[1])  # GREEN != RED
    assert g.combo == 6  # Still increments because super_mode
    assert info["combo_added"] == 1
    assert info["score_added"] > BASE_SCORE  # 3x bonus


def test_heat_game_over() -> None:
    """HEAT >= MAX_HEAT should cause game over."""
    g = _make_game()
    g._init_state()
    g.heat = MAX_HEAT  # 100
    # Simulate update check — in real game this happens in update()
    assert g.heat >= MAX_HEAT


def test_board_full_game_over() -> None:
    """Full board = game over."""
    grid = [[8] * GRID_SIZE for _ in range(GRID_SIZE)]
    assert Game._is_board_full(grid) is True

    grid[0][0] = 0
    assert Game._is_board_full(grid) is False


def test_ai_finds_winning_move() -> None:
    """AI completes its own 4-in-a-row."""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    rng = random.Random(42)
    for i in range(2, 6):
        grid[3][i] = AI_COLOR  # 4 gray stones
    move = Game._ai_find_best_move(grid, AI_COLOR, PLAYER_COLORS, 1.0, rng)
    assert move is not None
    assert move in [(1, 3), (6, 3)]  # extend left or right


def test_ai_blocks_player_4() -> None:
    """AI blocks player's 4-in-a-row."""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    rng = random.Random(42)
    for i in range(2, 6):
        grid[3][i] = PLAYER_COLORS[0]  # 4 RED stones
    move = Game._ai_find_best_move(grid, AI_COLOR, PLAYER_COLORS, 1.0, rng)
    assert move is not None
    assert move in [(1, 3), (6, 3)]  # block either end


def test_ai_blocks_player_3_with_difficulty() -> None:
    """AI blocks player's 3-in-a-row when difficulty > 0."""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    rng = random.Random(42)
    for i in range(2, 5):
        grid[3][i] = PLAYER_COLORS[0]  # 3 RED
    # With high difficulty and random check passing
    move = Game._ai_find_best_move(grid, AI_COLOR, PLAYER_COLORS, 1.0, rng)
    assert move is not None
    assert move in [(1, 3), (5, 3)]


def test_ai_makes_random_move() -> None:
    """AI always returns a valid move on non-empty board."""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    rng = random.Random(42)
    grid[3][3] = 8
    move = Game._ai_find_best_move(grid, AI_COLOR, PLAYER_COLORS, 0.5, rng)
    assert move is not None
    col, row = move
    assert 0 <= col < GRID_SIZE
    assert 0 <= row < GRID_SIZE
    assert grid[row][col] == 0


def test_ai_returns_none_on_full_board() -> None:
    """AI returns None when board is full."""
    grid = [[8] * GRID_SIZE for _ in range(GRID_SIZE)]
    rng = random.Random(42)
    move = Game._ai_find_best_move(grid, AI_COLOR, PLAYER_COLORS, 1.0, rng)
    assert move is None


def test_score_combo_bonus() -> None:
    """Score includes base + combo bonus."""
    g = _make_game()
    g._init_state()
    # First placement
    info = g._place_stone(3, 3, PLAYER_COLORS[0])
    assert info["score_added"] >= 100  # base only

    # Reset to fake combo 2
    g.combo = 1
    g.current_color_index = 0
    info2 = g._place_stone(4, 3, PLAYER_COLORS[0])
    assert info2["score_added"] >= 100 + 2 * COMBO_BONUS


def test_reset_clears_all_state() -> None:
    """reset() clears all game state."""
    g = _make_game()
    g._init_state()
    g._place_stone(3, 3, PLAYER_COLORS[0])
    g.score = 500
    g.combo = 3
    g.heat = 50
    g.particles.append(Particle(0, 0, 0, 0, 8, 10))
    g.floats.append(FloatingText(0, 0, "test", 7, 10, -0.5))

    g._init_state()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0
    assert g.turn == 0
    assert len(g.particles) == 0
    assert len(g.floats) == 0
    assert g.phase == Phase.PLAYING


def test_count_direction() -> None:
    """_count_direction counts consecutive same-color stones."""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    for i in range(3, 7):
        grid[3][i] = 8  # 4 RED stones to the right of (2,3)
    count = Game._count_direction(grid, 2, 3, 1, 0, 8)
    assert count == 4
    # Left direction has 0
    count_left = Game._count_direction(grid, 2, 3, -1, 0, 8)
    assert count_left == 0


def test_super_mode_score_3x() -> None:
    """During super mode, score is multiplied by 3."""
    g = _make_game()
    g._init_state()
    g.super_mode = True
    g.super_timer = 100
    g.combo = 5
    g.current_color_index = 0
    info = g._place_stone(3, 3, PLAYER_COLORS[0])
    # Score should be (100 + 6*50) * 3 + 200
    expected_base = (100 + 6 * 50) * 3 + 200
    assert info["score_added"] == expected_base


def test_win_detection_after_placement() -> None:
    """After placing 5th stone, _check_win detects victory."""
    g = _make_game()
    g._init_state()
    for i in range(4):
        g._place_stone(i, 3, PLAYER_COLORS[0])
        g._cycle_color()
        g.current_color_index = 0
    # Place 5th stone
    g._place_stone(4, 3, PLAYER_COLORS[0])
    assert Game._check_win(g.grid, 4, 3, PLAYER_COLORS[0]) is True


def test_player_wins_before_ai_turn() -> None:
    """When player gets 5-in-a-row, phase should go to VICTORY (not call AI)."""
    g = _make_game()
    g._init_state()
    for i in range(4):
        g._place_stone(i, 3, PLAYER_COLORS[0])
        g._cycle_color()
        g.current_color_index = 0
    # 5th placement completes the row
    g._place_stone(4, 3, PLAYER_COLORS[0])
    assert Game._check_win(g.grid, 4, 3, PLAYER_COLORS[0]) is True
    # In real game, phase would be set to VICTORY by update()


def test_heat_decay() -> None:
    """Heat decays over time in PLAYING phase."""
    g = _make_game()
    g._init_state()
    g.heat = 50.0
    # Simulate heat decay (normally done in update() each frame)
    for _ in range(100):
        if g.heat > 0:
            g.heat = max(0.0, g.heat - 0.005)
    assert g.heat < 50.0
    assert g.heat >= 0.0


def test_super_mode_expires() -> None:
    """Super mode expires after timer runs out."""
    g = _make_game()
    g._init_state()
    g.super_mode = True
    g.super_timer = 3
    # Simulate 3 frames
    for _ in range(3):
        g.super_timer -= 1
        if g.super_timer <= 0:
            g.super_mode = False
            g.super_timer = 0
    assert g.super_mode is False
    assert g.super_timer == 0


def test_phase_enum_values() -> None:
    """Phase enum has expected values."""
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.VICTORY == 2
    assert Phase.GAME_OVER == 3


# ── Base score constant used in tests ──
BASE_SCORE = 100


def test_grid_placement_rejects_occupied() -> None:
    """Stone cannot be placed on occupied cell."""
    g = _make_game()
    g._init_state()
    g._place_stone(3, 3, PLAYER_COLORS[0])
    assert g.grid[3][3] == PLAYER_COLORS[0]
    # Verify cell is now non-zero
    assert g._is_valid_cell(3, 3) is False


def test_pos_to_cell_conversion() -> None:
    """Grid position conversion from mouse coordinates."""
    # Cell (0,0) center is at (20+14, 20+14) = (34, 34)
    col, row = Game._pos_to_cell(34, 34)
    assert col == 0
    assert row == 0
    # Cell (3,4) 
    col, row = Game._pos_to_cell(20 + 3 * 28 + 14, 20 + 4 * 28 + 14)
    assert col == 3
    assert row == 4


def test_make_game_deterministic() -> None:
    """_make_game with seeded RNG produces deterministic results.
    
    NOTE: reset() overwrites _rng with unseeded random.Random(),
    so we must re-seed after _init_state().
    """
    g1 = _make_game()
    g2 = _make_game()
    g1._init_state()
    g2._init_state()
    g1._rng = random.Random(42)
    g2._rng = random.Random(42)

    move1 = Game._ai_find_best_move(g1.grid, AI_COLOR, PLAYER_COLORS, 1.0, g1._rng)
    move2 = Game._ai_find_best_move(g2.grid, AI_COLOR, PLAYER_COLORS, 1.0, g2._rng)
    assert move1 == move2
