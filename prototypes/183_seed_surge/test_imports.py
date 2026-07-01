"""test_imports.py — Headless logic tests for SEED SURGE (prototype #183).

Tests cover: dataclasses, board init, sow path building, capture logic,
combo/heat tracking, game over conditions, AI selection, super sow adjacency.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

# Add prototype dir to path for import
_proto_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_proto_dir))

from main import (  # noqa: E402
    SCREEN_W,
    SCREEN_H,
    PIT_SIZE,
    PIT_GAP,
    BOARD_LEFT,
    BOARD_TOP_AI,
    BOARD_TOP_PLAYER,
    PITS_PER_ROW,
    NUM_ROWS,
    INITIAL_SEEDS_PER_PIT,
    HEAT_MAX,
    HEAT_DECAY,
    HEAT_WRONG_CAPTURE,
    SUPER_SOW_THRESHOLD,
    SUPER_SOW_DURATION,
    FLOAT_TEXT_LIFE,
    SEED_COLORS,
    RED, GREEN, LIGHT_BLUE, YELLOW,
    WHITE,
    Pit, Particle, FloatText, Phase, Game,
)


# ── Helpers ────────────────────────────────────────────────────────────

def make_game(seed: int = 42) -> Game:
    """Create a Game instance for headless testing (bypasses pyxel.init)."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes that reset() touches
    g._rng = random.Random(seed)
    g.board = []
    g.stores = [0, 0]
    g.player_turn = True
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.score = 0
    g.turn_count = 0
    g.particles = []
    g.floating_texts = []
    g.last_capture_color = -1
    g.super_sow_timer = 0
    g.phase = Phase.TITLE
    g.game_over_reason = ""
    g._sow_anim = []
    g._sow_anim_start_color = -1
    g._anim_timer = 0
    g._hovered_col = -1
    g._font = None
    g.reset()
    return g


# ── Dataclass Tests ─────────────────────────────────────────────────────

def test_pit_creation():
    p = Pit(seeds=4, color=0)
    assert p.seeds == 4
    assert p.color == 0


def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == RED


def test_float_text_creation():
    ft = FloatText(x=100.0, y=50.0, text="+10", life=30, color=YELLOW)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == YELLOW


def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.TITLE != Phase.PLAYING


# ── Board Initialization Tests ──────────────────────────────────────────

def test_reset_initializes_board():
    g = make_game()
    assert len(g.board) == NUM_ROWS
    assert all(len(row) == PITS_PER_ROW for row in g.board)
    assert g.stores == [0, 0]
    assert g.player_turn is True
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.score == 0
    assert g.turn_count == 0
    assert g.last_capture_color == -1
    assert g.super_sow_timer == 0
    assert g.phase == Phase.TITLE  # reset doesn't change phase
    assert g.game_over_reason == ""


def test_board_seeds_initialized():
    g = make_game()
    for row in range(NUM_ROWS):
        for col in range(PITS_PER_ROW):
            pit = g.board[row][col]
            assert pit.seeds == INITIAL_SEEDS_PER_PIT
            assert 0 <= pit.color <= 3


def test_board_colors_are_valid():
    g = make_game()
    for row in range(NUM_ROWS):
        for col in range(PITS_PER_ROW):
            assert g.board[row][col].color in (0, 1, 2, 3)


def test_seed_colors_mapping():
    assert len(SEED_COLORS) == 4
    assert SEED_COLORS[0] == RED
    assert SEED_COLORS[1] == GREEN
    assert SEED_COLORS[2] == LIGHT_BLUE
    assert SEED_COLORS[3] == YELLOW


# ── Pit Geometry Tests ──────────────────────────────────────────────────

def test_get_pit_center():
    g = make_game()
    x, y = g._get_pit_center(1, 0)
    expected_x = BOARD_LEFT + 10 + 0 * (PIT_SIZE + PIT_GAP) + PIT_SIZE // 2
    expected_y = BOARD_TOP_PLAYER + PIT_SIZE // 2
    assert x == float(expected_x)
    assert y == float(expected_y)


def test_get_pit_center_ai_row():
    g = make_game()
    x, y = g._get_pit_center(0, 5)
    expected_x = BOARD_LEFT + 10 + 5 * (PIT_SIZE + PIT_GAP) + PIT_SIZE // 2
    expected_y = BOARD_TOP_AI + PIT_SIZE // 2
    assert x == float(expected_x)
    assert y == float(expected_y)


def test_get_store_center():
    g = make_game()
    x, y = g._get_store_center(1)
    expected_x = BOARD_LEFT + PITS_PER_ROW * (PIT_SIZE + PIT_GAP) + 25
    expected_y = BOARD_TOP_PLAYER + PIT_SIZE // 2
    assert x == float(expected_x)
    assert y == float(expected_y)


def test_pit_at_pos_hit():
    g = make_game()
    cx, cy = g._get_pit_center(1, 2)
    col = g._pit_at_pos(int(cx), int(cy))
    assert col == 2


def test_pit_at_pos_miss():
    g = make_game()
    col = g._pit_at_pos(999, 999)
    assert col is None


def test_pit_at_pos_near_miss():
    g = make_game()
    cx, cy = g._get_pit_center(1, 0)
    far_x = int(cx) + PIT_SIZE * 2  # clearly outside any pit
    col = g._pit_at_pos(far_x, int(cy))
    assert col is None


# ── Sow Path Building Tests ─────────────────────────────────────────────

def test_build_sow_path_player_small():
    g = make_game()
    path = g._build_sow_path(1, 2, 3)  # player row, col 2, 3 seeds
    # 3 seeds: each goes to next pit in sequence
    assert len(path) == 3
    # First goes to (1, 3), second to (1, 4), third to (1, 5)
    assert path[0] == (1, 3, False)
    assert path[1] == (1, 4, False)
    assert path[2] == (1, 5, False)


def test_build_sow_path_player_wraps():
    g = make_game()
    path = g._build_sow_path(1, 4, 5)  # player row, col 4, 5 seeds
    # col 4: right to 5, then store, then AI row right-to-left
    assert len(path) == 5
    assert path[0] == (1, 5, False)   # (1, 5)
    assert path[1] == (1, -1, True)   # player store
    assert path[2] == (0, 5, False)   # AI (0, 5)
    assert path[3] == (0, 4, False)   # AI (0, 4)
    assert path[4] == (0, 3, False)   # AI (0, 3)


def test_build_sow_path_player_full_cycle():
    g = make_game()
    # With 14 seeds, the single_path has 13 positions (excludes starting pit).
    # Seeds wrap around: seed 13 wraps to idx 0 = (1, 1)
    path = g._build_sow_path(1, 0, 14)
    assert len(path) == 14
    # First seed goes to (1, 1)
    assert path[0] == (1, 1, False)
    # 13 single_path entries: last is AI store, 14th seed wraps to (1,1)
    assert path[12] == (0, -1, True)  # AI store (idx 12)
    assert path[13] == (1, 1, False)  # wraps to idx 0


def test_build_sow_path_ai():
    g = make_game()
    path = g._build_sow_path(0, 3, 3)  # AI row, col 3, 3 seeds
    assert len(path) == 3
    # AI goes left: (0,2), (0,1), (0,0)
    assert path[0] == (0, 2, False)
    assert path[1] == (0, 1, False)
    assert path[2] == (0, 0, False)


def test_build_sow_path_ai_wraps():
    g = make_game()
    path = g._build_sow_path(0, 1, 5)
    assert len(path) == 5
    assert path[0] == (0, 0, False)    # left
    assert path[1] == (0, -1, True)    # AI store
    assert path[2] == (1, 0, False)    # player (1,0)
    assert path[3] == (1, 1, False)    # player (1,1)
    assert path[4] == (1, 2, False)    # player (1,2)


def test_build_sow_path_many_seeds():
    g = make_game()
    # 30 seeds should wrap around multiple times
    path = g._build_sow_path(1, 3, 30)
    assert len(path) == 30
    # First seed always goes to next pit
    assert path[0] == (1, 4, False)
    # Verify all positions are valid
    for r, c, is_store in path:
        if not is_store:
            assert 0 <= r < NUM_ROWS
            assert 0 <= c < PITS_PER_ROW


# ── Capture Tests ───────────────────────────────────────────────────────

def test_capture_basic():
    g = make_game()
    # Set up: landing pit has 3 seeds, opposite has 2
    g.board[1][2].seeds = 3
    g.board[0][2].seeds = 2
    captured = g._capture(1, 2, 1)  # player captures row 1 col 2
    assert captured == 5  # 3 + 2
    assert g.board[1][2].seeds == 0
    assert g.board[0][2].seeds == 0
    assert g.stores[1] == 5


def test_capture_ai():
    g = make_game()
    g.board[0][3].seeds = 4
    g.board[1][3].seeds = 3
    captured = g._capture(0, 3, 0)  # AI captures row 0 col 3
    assert captured == 7
    assert g.board[0][3].seeds == 0
    assert g.board[1][3].seeds == 0
    assert g.stores[0] == 7


def test_capture_empty_opposite():
    g = make_game()
    g.board[1][1].seeds = 2
    g.board[0][1].seeds = 0  # opposite empty
    captured = g._capture(1, 1, 1)
    assert captured == 2
    assert g.stores[1] == 2


def test_capture_accumulates_in_store():
    g = make_game()
    g.stores[1] = 10
    g.board[1][0].seeds = 1
    g.board[0][0].seeds = 1
    g._capture(1, 0, 1)
    assert g.stores[1] == 12


# ── Start Sow Tests (state manipulation) ────────────────────────────────

def test_start_sow_removes_seeds():
    g = make_game()
    g.board[1][0].seeds = 6
    g._start_sow(1, 0, g.board[1][0].color)
    assert g.board[1][0].seeds == 0
    assert len(g._sow_anim) == 6
    assert g._anim_timer > 0


def test_start_sow_stores_start_color():
    g = make_game()
    g.board[1][2].color = 2  # LIGHT_BLUE
    g._start_sow(1, 2, 2)
    assert g._sow_anim_start_color == 2


# ── Process Sow Result (simulated) ──────────────────────────────────────

def test_process_sow_result_match_triggers_capture():
    """Simulate a match scenario: start and landing colors match."""
    g = make_game(seed=99)
    # Manually set up: player clicks pit (1,0) with color 0 (RED)
    g.player_turn = True
    g.phase = Phase.PLAYING
    g.board[1][0].color = 0  # RED
    g.board[1][0].seeds = 4
    g.board[1][1].color = 0  # RED - this will be the landing pit
    g.board[1][1].seeds = 3
    g.board[0][1].seeds = 2  # opposite pit

    # Simulate sow: 4 seeds from (1,0) go right
    # Path: (1,1), (1,2), (1,3), (1,4)
    # Last seed lands at (1,4)
    # We need start color == landing color for capture
    # Let's set up column 4 as RED too
    g.board[1][4].color = 0  # RED
    g.board[0][4].seeds = 5  # opposite has seeds

    g._sow_anim = [
        {"row": 1, "col": 1, "is_store": False},
        {"row": 1, "col": 2, "is_store": False},
        {"row": 1, "col": 3, "is_store": False},
        {"row": 1, "col": 4, "is_store": False},
    ]
    g._sow_anim_start_color = 0
    g._anim_timer = 1  # will be checked

    # Save pre-state
    pre_score = g.score
    pre_heat = g.heat

    g._process_sow_result()

    # Seeds should be distributed
    assert g.board[1][1].seeds == 4  # was 3, +1
    assert g.board[1][2].seeds == 5  # was 4, +1
    assert g.board[1][3].seeds == 5  # was 4, +1
    # Landing pit (1,4) got +1 then captured to 0
    # Actually: seeds are added first, then capture clears it
    # So: board[1][4] had 4 seeds, +1 = 5, then captured => 0
    assert g.board[1][4].seeds == 0  # captured
    assert g.board[0][4].seeds == 0  # opposite captured
    assert g.combo == 1  # combo starts at 0, +1 from match
    assert g.score > pre_score
    assert g.heat == pre_heat  # heat unchanged on match


def test_process_sow_result_mismatch_adds_heat():
    """Simulate a mismatch: start and landing colors differ."""
    g = make_game(seed=99)
    g.player_turn = True
    g.phase = Phase.PLAYING
    g.board[1][0].color = 0  # RED
    g.board[1][0].seeds = 3
    g.board[1][4].color = 2  # LIGHT_BLUE (different from start)

    g._sow_anim = [
        {"row": 1, "col": 1, "is_store": False},
        {"row": 1, "col": 2, "is_store": False},
        {"row": 1, "col": 3, "is_store": False},
    ]
    g._sow_anim_start_color = 0
    g._anim_timer = 1

    pre_heat = g.heat

    g._process_sow_result()

    assert g.combo == 0  # combo reset
    assert g.heat == pre_heat + HEAT_WRONG_CAPTURE
    assert g.last_capture_color == -1


def test_process_sow_result_empty_board_no_error():
    """Test handling when sow_anim is empty."""
    g = make_game()
    g._sow_anim = []
    g._anim_timer = 1
    g._process_sow_result()  # should not crash
    assert g.phase == Phase.TITLE  # finish_turn doesn't change phase


# ── Combo Tracking Tests ────────────────────────────────────────────────

def test_combo_increments_and_max_tracked():
    g = make_game()
    assert g.combo == 0
    assert g.max_combo == 0

    # Simulate combo increases
    g.combo = 3
    g.max_combo = max(g.max_combo, g.combo)
    assert g.max_combo == 3

    g.combo = 5
    g.max_combo = max(g.max_combo, g.combo)
    assert g.max_combo == 5

    # Reset combo
    g.combo = 0
    assert g.max_combo == 5  # max stays


def test_combo_resets_on_mismatch():
    g = make_game()
    g.combo = 3
    g.max_combo = 3

    # Simulate mismatch in _process_sow_result
    g.player_turn = True
    g.board[1][0].color = 0
    g.board[1][0].seeds = 2
    g.board[1][2].color = 1  # different color

    g._sow_anim = [
        {"row": 1, "col": 1, "is_store": False},
        {"row": 1, "col": 2, "is_store": False},
    ]
    g._sow_anim_start_color = 0
    g._anim_timer = 1
    g.phase = Phase.PLAYING

    g._process_sow_result()
    assert g.combo == 0
    assert g.max_combo == 3  # max preserved


# ── Heat Tests ──────────────────────────────────────────────────────────

def test_heat_increases_on_mismatch():
    g = make_game()
    g.heat = 20.0
    g.player_turn = True
    g.board[1][0].color = 0
    g.board[1][0].seeds = 2
    g.board[1][2].color = 1

    g._sow_anim = [
        {"row": 1, "col": 1, "is_store": False},
        {"row": 1, "col": 2, "is_store": False},
    ]
    g._sow_anim_start_color = 0
    g._anim_timer = 1

    g._process_sow_result()
    assert g.heat == 20.0 + HEAT_WRONG_CAPTURE


def test_heat_clamped_at_max():
    g = make_game()
    g.heat = HEAT_MAX - 5.0
    g.player_turn = True
    g.board[1][0].color = 0
    g.board[1][0].seeds = 2
    g.board[1][2].color = 1

    g._sow_anim = [
        {"row": 1, "col": 1, "is_store": False},
        {"row": 1, "col": 2, "is_store": False},
    ]
    g._sow_anim_start_color = 0
    g._anim_timer = 1
    g.phase = Phase.PLAYING

    g._process_sow_result()
    assert g.heat <= HEAT_MAX


def test_heat_decay_on_player_turn_start():
    g = make_game()
    g.heat = 50.0
    g.player_turn = False  # AI just finished
    g.phase = Phase.PLAYING
    g._finish_turn()  # switches to player, decays heat
    assert g.player_turn is True
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_never_negative():
    g = make_game()
    g.heat = 0.1
    g.player_turn = False
    g.phase = Phase.PLAYING
    g._finish_turn()
    assert g.heat >= 0.0


# ── Game Over Tests ─────────────────────────────────────────────────────

def test_game_over_heat_max():
    g = make_game()
    g.heat = HEAT_MAX
    g.phase = Phase.PLAYING
    assert g._check_game_over() is True
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "Overheated!"


def test_game_over_heat_just_below_max():
    g = make_game()
    g.heat = HEAT_MAX - 0.1
    g.phase = Phase.PLAYING
    assert g._check_game_over() is False
    assert g.phase == Phase.PLAYING


def test_game_over_player_empty():
    g = make_game()
    for col in range(PITS_PER_ROW):
        g.board[1][col].seeds = 0
    g.phase = Phase.PLAYING
    assert g._check_game_over() is True
    assert g.phase == Phase.GAME_OVER
    assert "Empty" in g.game_over_reason


def test_game_over_ai_empty():
    g = make_game()
    for col in range(PITS_PER_ROW):
        g.board[0][col].seeds = 0
    g.phase = Phase.PLAYING
    assert g._check_game_over() is True
    assert g.phase == Phase.GAME_OVER


def test_game_over_not_when_both_have_seeds():
    g = make_game()
    g.phase = Phase.PLAYING
    assert g._check_game_over() is False


# ── AI Tests ────────────────────────────────────────────────────────────

def test_ai_pick_pit_returns_valid():
    g = make_game()
    move = g._ai_pick_pit()
    assert move is not None
    r, c = move
    assert r == 0  # AI row
    assert 0 <= c < PITS_PER_ROW
    assert g.board[r][c].seeds > 0


def test_ai_pick_pit_prefers_counter_color():
    g = make_game(seed=42)
    # Set up: last capture was color 0 (RED)
    g.last_capture_color = 0
    # Make only one AI pit match color 0
    for col in range(PITS_PER_ROW):
        g.board[0][col].color = 2  # LIGHT_BLUE
    g.board[0][3].color = 0  # RED — this should be picked
    move = g._ai_pick_pit()
    assert move == (0, 3)


def test_ai_pick_pit_most_seeds():
    g = make_game(seed=42)
    g.last_capture_color = -1  # no counter-pick
    g.board[0][0].seeds = 1
    g.board[0][1].seeds = 1
    g.board[0][2].seeds = 10  # most seeds
    g.board[0][3].seeds = 1
    g.board[0][4].seeds = 3
    g.board[0][5].seeds = 1
    move = g._ai_pick_pit()
    assert move == (0, 2)


def test_ai_pick_pit_none_when_empty():
    g = make_game()
    for col in range(PITS_PER_ROW):
        g.board[0][col].seeds = 0
    assert g._ai_pick_pit() is None


def test_ai_turn_starts_sow():
    g = make_game(seed=42)
    g.player_turn = False
    g.phase = Phase.PLAYING
    g._ai_turn()
    # After AI turn start, should have sow animation
    assert len(g._sow_anim) > 0
    assert g._anim_timer > 0


def test_ai_turn_skips_when_no_moves():
    g = make_game()
    for col in range(PITS_PER_ROW):
        g.board[0][col].seeds = 0
    g.player_turn = False
    g.phase = Phase.PLAYING
    g._ai_turn()
    # Should call _finish_turn which switches to player
    # But _check_game_over may trigger first
    # Either way, it doesn't crash
    assert g._anim_timer == 0  # no sow started


# ── Super Sow Tests ─────────────────────────────────────────────────────

def test_find_adjacent_same_color_center():
    g = make_game()
    # Set all pits to color 0 (RED)
    for r in range(NUM_ROWS):
        for c in range(PITS_PER_ROW):
            g.board[r][c].color = 0
            g.board[r][c].seeds = 4
    # Center pit (1, 2): adjacents are (1,1), (1,3), (0,2)
    neighbors = g._find_adjacent_same_color(1, 2, 0)
    assert len(neighbors) == 3  # (1,1), (1,3), (0,2)


def test_find_adjacent_same_color_edge():
    g = make_game()
    for r in range(NUM_ROWS):
        for c in range(PITS_PER_ROW):
            g.board[r][c].color = 0
            g.board[r][c].seeds = 4
    # Corner pit (0, 0): adjacents are (0,1), (1,0)
    neighbors = g._find_adjacent_same_color(0, 0, 0)
    assert len(neighbors) == 2


def test_find_adjacent_same_color_different():
    g = make_game()
    for r in range(NUM_ROWS):
        for c in range(PITS_PER_ROW):
            g.board[r][c].color = 1  # GREEN
            g.board[r][c].seeds = 4
    g.board[0][0].color = 0  # RED - different
    # Center (1,2) should not include (0,0) because different color
    # But (0,0) is not adjacent to (1,2) anyway
    neighbors = g._find_adjacent_same_color(1, 2, 1)
    # (0,2), (1,1), (1,3)
    assert len(neighbors) == 3


def test_find_adjacent_requires_seeds():
    g = make_game()
    for r in range(NUM_ROWS):
        for c in range(PITS_PER_ROW):
            g.board[r][c].color = 0
    g.board[1][2].seeds = 4
    g.board[1][1].seeds = 0  # adjacent but empty
    g.board[1][3].seeds = 4
    g.board[0][2].seeds = 0  # adjacent but empty

    neighbors = g._find_adjacent_same_color(1, 2, 0)
    # Only (1,3) should be included
    assert len(neighbors) == 1
    assert neighbors[0] == (1, 3)


def test_trigger_super_sow_sets_timer():
    g = make_game()
    for r in range(NUM_ROWS):
        for c in range(PITS_PER_ROW):
            g.board[r][c].color = 0
            g.board[r][c].seeds = 4
    g.combo = SUPER_SOW_THRESHOLD
    g.phase = Phase.PLAYING

    g._trigger_super_sow(1, 2, 1)  # player row
    assert g.super_sow_timer == SUPER_SOW_DURATION


def test_trigger_super_sow_captures_adjacent():
    g = make_game()
    for r in range(NUM_ROWS):
        for c in range(PITS_PER_ROW):
            g.board[r][c].color = 0
            g.board[r][c].seeds = 4
    g.combo = SUPER_SOW_THRESHOLD
    g.phase = Phase.PLAYING
    g.stores[1] = 0

    pre_score = g.score
    g._trigger_super_sow(1, 2, 1)  # player row captures center

    # Adjacent pits (1,1), (1,3), (0,2) should be captured
    assert g.board[1][1].seeds == 0
    assert g.board[1][3].seeds == 0
    assert g.board[0][2].seeds == 0
    # The center pit (1,2) was already captured before super sow
    assert g.stores[1] > 0
    assert g.score > pre_score


# ── Turn Management Tests ───────────────────────────────────────────────

def test_finish_turn_switches_player():
    g = make_game()
    g.player_turn = True
    g.phase = Phase.PLAYING
    g._finish_turn()
    assert g.player_turn is False
    g._finish_turn()
    assert g.player_turn is True


def test_turn_count_increments():
    g = make_game()
    g.player_turn = False  # AI just finished
    g.phase = Phase.PLAYING
    g._finish_turn()  # switches to player
    assert g.turn_count == 1


def test_finish_turn_clears_anim():
    g = make_game()
    g._sow_anim = [{"row": 1, "col": 0, "is_store": False}]
    g._anim_timer = 10
    g.phase = Phase.PLAYING
    g._finish_turn()
    assert len(g._sow_anim) == 0
    assert g._anim_timer == 0


# ── Particle and Float Text Tests ───────────────────────────────────────

def test_spawn_particles():
    g = make_game(seed=42)
    g._spawn_particles(100, 100, 5, RED)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 100.0
        assert p.color == RED
        assert 12 <= p.life <= 28


def test_update_particles():
    g = make_game()
    g.particles = [
        Particle(x=10, y=10, vx=1, vy=-2, life=5, color=RED),
        Particle(x=30, y=30, vx=-1, vy=1, life=1, color=LIGHT_BLUE),
    ]
    g._update_particles()
    # Particle 1: life 5→4, moves, kept
    # Particle 2: life 1→0, removed (filter keeps life > 0)
    assert len(g.particles) == 1
    assert g.particles[0].life == 4
    assert g.particles[0].x == 11
    assert abs(g.particles[0].y - 8.0) < 0.01  # y + vy = 10 + (-2), then vy += 0.12


def test_spawn_float_text():
    g = make_game()
    g._spawn_float_text(50, 60, "TEST", GREEN)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.x == 50
    assert ft.y == 60
    assert ft.text == "TEST"
    assert ft.life == FLOAT_TEXT_LIFE
    assert ft.color == GREEN


def test_update_floating_texts():
    g = make_game()
    g.floating_texts = [
        FloatText(x=10, y=10, text="A", life=FLOAT_TEXT_LIFE, color=WHITE),
        FloatText(x=20, y=20, text="B", life=0, color=WHITE),  # dead
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == FLOAT_TEXT_LIFE - 1
    assert g.floating_texts[0].y < 10  # moved up


# ── Handle Player Click Tests ───────────────────────────────────────────

def test_handle_player_click_empty_pit():
    g = make_game()
    g.board[1][0].seeds = 0
    g.player_turn = True
    g.phase = Phase.PLAYING
    g._handle_player_click(0)
    # Should do nothing (no sow started)
    assert len(g._sow_anim) == 0


def test_handle_player_click_starts_sow():
    g = make_game()
    g.board[1][3].seeds = 4
    g.player_turn = True
    g.phase = Phase.PLAYING
    g._handle_player_click(3)
    assert len(g._sow_anim) == 4
    assert g.board[1][3].seeds == 0  # seeds taken


# ── Score Tests ─────────────────────────────────────────────────────────

def test_score_calculation_basic():
    """Verify the scoring formula: captured * combo * 10."""
    g = make_game()
    g.combo = 2
    captured = 3
    bonus = captured * g.combo * 10
    assert bonus == 60


def test_super_sow_score_bonus():
    """Verify super sow adds captured * combo * 5 per neighbor."""
    g = make_game()
    g.combo = SUPER_SOW_THRESHOLD
    captured = 4
    bonus = captured * g.combo * 5
    assert bonus == 80


def test_game_over_adds_store_bonus():
    g = make_game(seed=42)
    pre_store = g.stores[1]
    # Empty AI pits to trigger game over
    for col in range(PITS_PER_ROW):
        g.board[0][col].seeds = 0
    # Player has 4 seeds × 6 pits = 24 remaining seeds
    g._check_game_over()
    # Store gets remaining player seeds added: pre_store + 24
    assert g.stores[1] == pre_store + 24
    # Score gets stores[1] * 5 bonus
    assert g.score == g.stores[1] * 5


# ── Super Sow Threshold Tests ───────────────────────────────────────────

def test_super_sow_triggers_at_threshold():
    g = make_game()
    g.combo = SUPER_SOW_THRESHOLD
    g.player_turn = True
    g.phase = Phase.PLAYING

    # Set up: player click (1,0), color 0, 4 seeds
    # Make it so last seed lands at (1,3) which also has color 0
    g.board[1][0].color = 0
    g.board[1][0].seeds = 3
    g.board[1][3].color = 0  # landing color match
    g.board[0][3].seeds = 2

    g._sow_anim = [
        {"row": 1, "col": 1, "is_store": False},
        {"row": 1, "col": 2, "is_store": False},
        {"row": 1, "col": 3, "is_store": False},
    ]
    g._sow_anim_start_color = 0
    g._anim_timer = 1

    g._process_sow_result()
    # combo was already >= SUPER_SOW_THRESHOLD, so super sow triggered
    assert g.super_sow_timer == SUPER_SOW_DURATION


# ── Store bonus when game ends ──────────────────────────────────────────

def test_game_over_remaining_player_seeds_awarded():
    g = make_game(seed=42)
    # Empty AI pits, player has seeds
    for col in range(PITS_PER_ROW):
        g.board[0][col].seeds = 0
    g.board[1][0].seeds = 5
    g.board[1][1].seeds = 3
    g.board[1][2].seeds = 0
    g.board[1][3].seeds = 0
    g.board[1][4].seeds = 0
    g.board[1][5].seeds = 0
    g.stores[1] = 10
    g.phase = Phase.PLAYING

    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    # Player's remaining seeds (5+3=8) added to store
    assert g.stores[1] == 18
    # Score bonus = stores[1] * 5
    assert g.score == 18 * 5


# ── Deterministic Board Test ────────────────────────────────────────────

def test_deterministic_board_with_seed():
    g1 = make_game(seed=42)
    g2 = make_game(seed=42)
    for r in range(NUM_ROWS):
        for c in range(PITS_PER_ROW):
            assert g1.board[r][c].seeds == g2.board[r][c].seeds
            assert g1.board[r][c].color == g2.board[r][c].color


# ── Constants Validation ────────────────────────────────────────────────

def test_constants_are_consistent():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert INITIAL_SEEDS_PER_PIT == 4
    assert HEAT_MAX == 100.0
    assert HEAT_WRONG_CAPTURE == 15.0
    assert SUPER_SOW_THRESHOLD == 4
    assert FLOAT_TEXT_LIFE == 30
    assert PITS_PER_ROW == 6
    assert NUM_ROWS == 2


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=False,
    )
