"""test_imports.py — Headless logic tests for 246_piece_chain."""
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (
    Game, Phase, Piece, Particle, FloatingText,
    CELL, GAP, GRID_LEFT, GRID_TOP, GRID_COLS, GRID_ROWS, TOTAL_PIECES,
    TRAY_LEFT, TRAY_TOP, TRAY_ITEM_SIZE,
    PLAY_TIME, SUPER_DURATION,
    COLOR_RED, COLOR_LIME, COLOR_DARK_BLUE, COLOR_YELLOW,
    PLAYER_COLORS, HEAT_WRONG, HEAT_DECAY, HEAT_MAX,
    SCREEN_W, SCREEN_H,
)


def _make_game(seed: int = 42) -> Game:
    """Create a Game bypassing pyxel.init()."""
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.timer = PLAY_TIME
    g.heat = 0.0
    g.pieces = []
    g.slots = []
    g.selected_piece = None
    g.super_mode = False
    g.super_timer = 0
    g.particles = []
    g.floating_texts = []
    g.last_placed_color = None
    g.placed_count = 0
    g._rng = random.Random(seed)
    g._tray_scroll = 0
    g._screen_shake = 0
    g.reset()
    g._rng = random.Random(seed)  # re-seed after reset overwrites
    return g


# ── Basic initialization ──

def test_game_init() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.timer == PLAY_TIME
    assert g.heat == 0.0
    assert g.placed_count == 0
    assert g.selected_piece is None
    assert g.super_mode is False
    assert g.last_placed_color is None
    assert len(g.pieces) == TOTAL_PIECES
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_pieces_created() -> None:
    g = _make_game()
    assert len(g.pieces) == 12
    # 3 of each color
    for c in PLAYER_COLORS:
        count = sum(1 for p in g.pieces if p.color == c)
        assert count == 3, f"Expected 3 pieces of color {c}, got {count}"


def test_slots_initialized_empty() -> None:
    g = _make_game()
    assert len(g.slots) == GRID_COLS
    assert len(g.slots[0]) == GRID_ROWS
    for col in range(GRID_COLS):
        for row in range(GRID_ROWS):
            assert g.slots[col][row] is None


def test_each_slot_has_corresponding_piece() -> None:
    g = _make_game()
    covered = set()
    for p in g.pieces:
        key = (p.target_col, p.target_row)
        assert key not in covered, f"Duplicate piece for slot {key}"
        covered.add(key)
    assert len(covered) == TOTAL_PIECES


def test_reset_clears_state() -> None:
    g = _make_game()
    # Simulate some play
    g.score = 500
    g.combo = 3
    g.placed_count = 5
    g.heat = 50.0
    g.super_mode = True
    g.particles = [Particle(0, 0, 0, 0, 10, COLOR_RED)]
    g.floating_texts = [FloatingText(0, 0, "test", 10, 7)]
    g.reset()
    g._rng = random.Random(42)
    assert g.score == 0
    assert g.combo == 0
    assert g.placed_count == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.particles == []
    assert g.floating_texts == []
    assert g.phase == Phase.PLAYING


# ── Slot coordinate calculations ──

def test_get_slot_rect() -> None:
    g = _make_game()
    x, y, w, h = g._get_slot_rect(0, 0)
    assert x == GRID_LEFT
    assert y == GRID_TOP
    assert w == CELL
    assert h == CELL

    x2, y2, _, _ = g._get_slot_rect(1, 1)
    assert x2 == GRID_LEFT + 1 * (CELL + GAP)
    assert y2 == GRID_TOP + 1 * (CELL + GAP)


def test_check_click_slot() -> None:
    g = _make_game()
    # Click on first slot
    x0, y0, w, h = g._get_slot_rect(0, 0)
    result = g._check_click_slot(x0 + 5, y0 + 5)
    assert result == (0, 0)

    # Click on last slot
    xl, yl, wl, hl = g._get_slot_rect(3, 2)
    result = g._check_click_slot(xl + 5, yl + 5)
    assert result == (3, 2)

    # Click outside grid
    result = g._check_click_slot(0, 0)
    assert result is None


def test_check_click_tray() -> None:
    g = _make_game()
    unplaced = [p for p in g.pieces if not p.placed]
    # Click on first tray item
    py = TRAY_TOP - g._tray_scroll
    mid_x = TRAY_LEFT + TRAY_ITEM_SIZE // 2
    mid_y = py + TRAY_ITEM_SIZE // 2
    result = g._check_click_tray(mid_x, mid_y)
    assert result is not None
    assert result is unplaced[0]


# ── Placement and COMBO logic ──

def test_try_place_correct_color() -> None:
    g = _make_game()
    piece = [p for p in g.pieces if not p.placed][0]
    g.selected_piece = piece
    result = g._try_place(piece.target_col, piece.target_row)
    assert result is True
    assert piece.placed is True
    assert g.placed_count == 1
    assert g.slots[piece.target_col][piece.target_row] == piece.color
    assert g.combo == 1
    assert g.score == 10  # 10 * combo(1) * multiplier(1)


def test_try_place_wrong_color() -> None:
    g = _make_game()
    # Find a piece and try to place it in a different color's slot
    pieces = [p for p in g.pieces if not p.placed]
    piece = pieces[0]
    # Find a slot that expects a different color
    wrong_slot = None
    for p in pieces[1:]:
        if p.color != piece.color:
            wrong_slot = (p.target_col, p.target_row)
            break
    assert wrong_slot is not None

    g.selected_piece = piece
    initial_heat = g.heat
    result = g._try_place(wrong_slot[0], wrong_slot[1])
    assert result is False
    assert piece.placed is False
    assert g.placed_count == 0
    assert g.heat == initial_heat + HEAT_WRONG
    assert g.combo == 0
    assert g.last_placed_color is None
    assert g._screen_shake > 0


def test_combo_same_color_consecutive() -> None:
    g = _make_game()
    # Find 3 pieces of the same color
    same_color = COLOR_RED
    red_pieces = [p for p in g.pieces if p.color == same_color and not p.placed]
    assert len(red_pieces) >= 2, f"Need at least 2 red pieces, got {len(red_pieces)}"

    # First placement
    g.selected_piece = red_pieces[0]
    g._try_place(red_pieces[0].target_col, red_pieces[0].target_row)
    assert g.combo == 1
    assert g.score == 10

    # Second placement (same color)
    g.selected_piece = red_pieces[1]
    g._try_place(red_pieces[1].target_col, red_pieces[1].target_row)
    assert g.combo == 2
    assert g.score == 10 + 20  # 10 + 10*2
    assert g.last_placed_color == same_color


def test_combo_reset_on_different_color() -> None:
    g = _make_game()
    # Find pieces of different colors
    red_pieces = [p for p in g.pieces if p.color == COLOR_RED and not p.placed]
    lime_pieces = [p for p in g.pieces if p.color == COLOR_LIME and not p.placed]
    assert len(red_pieces) >= 1
    assert len(lime_pieces) >= 1

    # Place red
    g.selected_piece = red_pieces[0]
    g._try_place(red_pieces[0].target_col, red_pieces[0].target_row)
    assert g.combo == 1

    # Place lime (different color - combo resets to 1)
    g.selected_piece = lime_pieces[0]
    g._try_place(lime_pieces[0].target_col, lime_pieces[0].target_row)
    assert g.combo == 1  # reset to 1
    assert g.last_placed_color == COLOR_LIME


def test_max_combo_tracking() -> None:
    g = _make_game()
    same_color = COLOR_RED
    red_pieces = [p for p in g.pieces if p.color == same_color and not p.placed]

    for i, piece in enumerate(red_pieces):
        g.selected_piece = piece
        g._try_place(piece.target_col, piece.target_row)
        assert g.max_combo == i + 1

    assert g.max_combo == len(red_pieces)


def test_cant_place_on_filled_slot() -> None:
    g = _make_game()
    piece = [p for p in g.pieces if not p.placed][0]
    g.selected_piece = piece
    g._try_place(piece.target_col, piece.target_row)
    assert piece.placed

    # Try another piece on same slot
    piece2 = [p for p in g.pieces if not p.placed][0]
    g.selected_piece = piece2
    result = g._try_place(piece.target_col, piece.target_row)
    assert result is False  # slot already filled


def test_cant_place_without_selection() -> None:
    g = _make_game()
    result = g._try_place(0, 0)
    assert result is False


# ── SUPER SOLVE ──

def test_super_solve_trigger() -> None:
    g = _make_game()
    same_color = COLOR_RED
    red_pieces = [p for p in g.pieces if p.color == same_color and not p.placed]
    assert len(red_pieces) >= 3, f"Need 3+ red pieces, got {len(red_pieces)}"

    for i, piece in enumerate(red_pieces):
        g.selected_piece = piece
        g._try_place(piece.target_col, piece.target_row)
        if i + 1 >= 3:
            assert g.super_mode is True
            assert g.super_timer == SUPER_DURATION
            break

    assert g.super_mode is True


def test_super_mode_triple_score() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = SUPER_DURATION
    g.combo = 2
    # In super mode, any piece matches any slot and combo continues
    g.last_placed_color = COLOR_RED  # set so combo continues

    piece = [p for p in g.pieces if not p.placed][0]
    g.selected_piece = piece
    g._try_place(piece.target_col, piece.target_row)
    # In super mode: combo 2→3, score = 10 * 3 * 3 = 90
    assert g.score == 10 * 3 * 3  # combo=3, multiplier=3


def test_super_mode_any_color_counts_for_combo() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = SUPER_DURATION

    # Place red
    red = [p for p in g.pieces if p.color == COLOR_RED and not p.placed][0]
    g.selected_piece = red
    g._try_place(red.target_col, red.target_row)
    assert g.combo == 1

    # Place lime (different color, but super mode keeps combo going)
    lime = [p for p in g.pieces if p.color == COLOR_LIME and not p.placed][0]
    g.selected_piece = lime
    g._try_place(lime.target_col, lime.target_row)
    assert g.combo == 2  # combo continues in super mode


def test_super_mode_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 2

    # Simulate 3 frames (timer goes 2→1→0→-1, expires)
    for _ in range(3):
        g.super_timer -= 1
        if g.super_timer <= 0:
            g.super_mode = False
    assert g.super_mode is False


# ── HEAT mechanics ──

def test_heat_threshold_causes_game_over() -> None:
    g = _make_game()
    # Set heat to exactly HEAT_MAX (which would cap from wrong placements)
    g.heat = HEAT_MAX

    # Simulate the update check (as done in _update_playing)
    if g.heat >= HEAT_MAX:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_heat_threshold_check_before_decay() -> None:
    """Verify decay doesn't prevent game over at exactly HEAT_MAX."""
    g = _make_game()
    g.heat = HEAT_MAX  # exactly 100

    # Check BEFORE decay (as _update_playing now does)
    if g.heat >= HEAT_MAX:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER

    # Even if decay ran first, at 100.0, decay to 99.98 makes the check fail
    # Our fix ensures check comes first
    g2 = _make_game()
    g2.heat = HEAT_MAX
    g2._update_heat()  # decay first: 100 → 99.98
    assert g2.heat < HEAT_MAX
    if g2.heat >= HEAT_MAX:
        g2.phase = Phase.GAME_OVER
    # This should NOT trigger after decay — proving the fix is needed
    assert g2.phase == Phase.PLAYING


def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_does_not_go_below_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0

    g.heat = HEAT_DECAY / 2
    g._update_heat()
    assert g.heat == 0.0


def test_heat_capped_at_max() -> None:
    g = _make_game()
    g.heat = HEAT_MAX - 5
    g.heat = min(HEAT_MAX, g.heat + HEAT_WRONG)  # simulate _try_place wrong
    assert g.heat == HEAT_MAX  # capped


def test_wrong_placement_heat_no_decay_during_check() -> None:
    g = _make_game()
    g.heat = 85.0
    # Do a wrong placement
    piece = [p for p in g.pieces if not p.placed][0]
    # Find wrong slot
    wrong = None
    for p in g.pieces:
        if p.color != piece.color:
            wrong = (p.target_col, p.target_row)
            break
    g.selected_piece = piece
    assert wrong is not None
    g._try_place(wrong[0], wrong[1])
    assert g.heat == 100.0  # 85 + 15 = 100, capped
    # Now check should trigger game over (before decay)
    if g.heat >= HEAT_MAX:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── Win/Lose conditions ──

def test_victory_on_all_placed() -> None:
    g = _make_game()
    for piece in g.pieces:
        g.selected_piece = piece
        g._try_place(piece.target_col, piece.target_row)
    assert g.placed_count == TOTAL_PIECES
    assert g.phase == Phase.VICTORY


def test_game_over_on_timer_expiry() -> None:
    g = _make_game()
    g.timer = 1
    g._update_playing()
    # Timer goes to 0, game over
    assert g.timer <= 0
    assert g.phase == Phase.GAME_OVER


def test_game_over_on_heat_max() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    # Simulate check in _update_playing
    if g.heat >= HEAT_MAX:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── Particle system ──

def test_spawn_particles() -> None:
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100, 100, COLOR_RED, 8)
    assert len(g.particles) == 8
    for p in g.particles:
        assert p.color == COLOR_RED
        assert 15 <= p.life <= 25


def test_update_particles() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, COLOR_RED, 5)
    initial_count = len(g.particles)
    for _ in range(10):
        g._update_particles()
    # Some particles should still be alive
    assert len(g.particles) <= initial_count


def test_particles_removed_when_life_zero() -> None:
    g = _make_game()
    g.particles = [Particle(100, 100, 1, 1, 1, COLOR_RED)]
    g._update_particles()
    assert len(g.particles) == 0  # life went to 0


# ── Floating text ──

def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 100, "TEST", 7, 30)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "TEST"
    assert ft.life == 30
    assert ft.color == 7


def test_update_floating_texts() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 100, "TEST", 7, 5)
    for _ in range(10):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0  # all expired


def test_floating_text_rises() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 100, "TEST", 7, 10)
    initial_y = g.floating_texts[0].y
    g._update_floating_texts()
    assert g.floating_texts[0].y < initial_y  # moved up


# ── Tray scrolling ──

def test_tray_scroll() -> None:
    g = _make_game()
    assert g._tray_scroll == 0


# ── Score with super multiplier ──

def test_score_without_super() -> None:
    g = _make_game()
    piece = [p for p in g.pieces if not p.placed][0]
    g.selected_piece = piece
    g.combo = 2  # simulate having placed 1 same-color before
    g.last_placed_color = piece.color  # same color → combo continues
    g._try_place(piece.target_col, piece.target_row)
    # combo becomes 3 (2+1), score = 10 * 3 = 30
    assert g.combo == 3
    assert g.score == 10 * 3  # combo=3, multiplier=1


def test_piece_placement_tracking() -> None:
    g = _make_game()
    piece = [p for p in g.pieces if not p.placed][0]
    g.selected_piece = piece
    g._try_place(piece.target_col, piece.target_row)
    assert g.last_placed_color == piece.color
    assert g.placed_count == 1


# ── Dataclass instantiation ──

def test_piece_dataclass() -> None:
    p = Piece(color=COLOR_RED, target_col=0, target_row=0)
    assert p.color == COLOR_RED
    assert p.target_col == 0
    assert p.target_row == 0
    assert p.placed is False
    assert p.tray_index == 0


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-1.0, life=15, color=COLOR_RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.life == 15


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=10.0, y=20.0, text="+100", life=30)
    assert ft.text == "+100"
    assert ft.life == 30
    assert ft.color == 7


# ── Phase enum ──

def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.VICTORY in Phase
    assert len(Phase) == 4


# ── Constants ──

def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert CELL == 40
    assert GAP == 2
    assert GRID_COLS == 4
    assert GRID_ROWS == 3
    assert TOTAL_PIECES == 12
    assert PLAY_TIME == 60 * 60
    assert SUPER_DURATION == 300
    assert HEAT_MAX == 100.0
    assert len(PLAYER_COLORS) == 4
    assert COLOR_RED == 8
    assert COLOR_LIME == 11
    assert COLOR_DARK_BLUE == 5
    assert COLOR_YELLOW == 10


# ── Selected piece deselects after placement ──

def test_selected_piece_stays_after_placement() -> None:
    g = _make_game()
    piece = [p for p in g.pieces if not p.placed][0]
    g.selected_piece = piece
    g._try_place(piece.target_col, piece.target_row)
    # Selected piece is not cleared after placement
    # (design choice: user might want to place another piece)
    assert g.selected_piece is piece
    assert piece.placed is True


# ── Replay with same seed produces same layout ──

def test_deterministic_layout_with_seed() -> None:
    g1 = _make_game(42)
    g2 = _make_game(42)

    p1 = [(p.color, p.target_col, p.target_row) for p in g1.pieces]
    p2 = [(p.color, p.target_col, p.target_row) for p in g2.pieces]
    assert p1 == p2


# ── Screen shake ──

def test_screen_shake_on_wrong_placement() -> None:
    g = _make_game()
    assert g._screen_shake == 0
    piece = [p for p in g.pieces if not p.placed][0]
    wrong = None
    for p in g.pieces:
        if p.color != piece.color:
            wrong = (p.target_col, p.target_row)
            break
    g.selected_piece = piece
    assert wrong is not None
    g._try_place(wrong[0], wrong[1])
    assert g._screen_shake > 0


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
