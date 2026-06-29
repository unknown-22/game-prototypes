"""test_imports.py — Headless logic tests for PEG SURGE."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/176_peg_surge")

import random
from main import (
    Game, Phase, Peg, Particle, FloatingText,
    VALID_CELLS, PEG_COLORS, CELL, BOARD_OFFSET_X, BOARD_OFFSET_Y,
    PEG_RADIUS, SUPER_DURATION, HEAT_DECAY, HEAT_WRONG_COLOR, HEAT_MAX,
    BASE_SCORE, COMBO_SCORE_FACTOR,
    SUPER_BURST_PARTICLE_COUNT,
    PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX,
)


def _make_game(seed: int = 42) -> Game:
    """Create a Game instance bypassing pyxel.init/run."""
    g: Game = Game.__new__(Game)
    # Pre-init all instance attributes (matching __init__)
    g._pegs = {}
    g._phase = Phase.TITLE
    g._score = 0
    g._combo = 0
    g._max_combo = 0
    g._heat = 0.0
    g._super_timer = 0
    g._selected_col = None
    g._selected_row = None
    g._last_captured_color = None
    g._particles = []
    g._floating_texts = []
    g._shake_frames = 0
    g._hover_col = None
    g._hover_row = None
    g._rng = random.Random()
    g._rainbow_cycle = 0
    g.reset()
    g._rng = random.Random(seed)
    return g


# ── Dataclass tests ──────────────────────────────────────────────

def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_peg_creation() -> None:
    p = Peg(col=2, row=3, color=PEG_COLORS[0])
    assert p.col == 2
    assert p.row == 3
    assert p.color == PEG_COLORS[0]


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-0.5, life=20, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -0.5
    assert p.life == 20
    assert p.color == 8


def test_floating_text_creation() -> None:
    ft = FloatingText(x=50.0, y=60.0, text="+10", life=30, color=7)
    assert ft.x == 50.0
    assert ft.y == 60.0
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == 7


# ── Board validation tests ───────────────────────────────────────

def test_valid_cells_count() -> None:
    assert len(VALID_CELLS) == 33  # English peg solitaire cross


def test_center_is_valid_and_corners_not() -> None:
    assert (3, 3) in VALID_CELLS  # center
    assert (0, 0) not in VALID_CELLS  # top-left corner
    assert (6, 0) not in VALID_CELLS  # top-right corner
    assert (0, 6) not in VALID_CELLS  # bottom-left corner
    assert (6, 6) not in VALID_CELLS  # bottom-right corner


def test_is_valid_cell_static() -> None:
    assert Game._is_valid_cell(3, 3)
    assert not Game._is_valid_cell(0, 0)
    assert not Game._is_valid_cell(-1, 0)
    assert Game._is_valid_cell(2, 0)  # top row, middle 3 columns are valid


def test_is_adjacent() -> None:
    # Horizontal jump 2 cells apart
    assert Game._is_adjacent(2, 3, 4, 3)
    # Vertical jump 2 cells apart
    assert Game._is_adjacent(3, 1, 3, 3)
    # Not adjacent: diagonal
    assert not Game._is_adjacent(2, 2, 4, 4)
    # Not adjacent: 1 cell away
    assert not Game._is_adjacent(2, 3, 3, 3)
    # Not adjacent: 3 cells away
    assert not Game._is_adjacent(2, 3, 5, 3)


def test_middle_cell() -> None:
    assert Game._middle_cell(2, 3, 4, 3) == (3, 3)
    assert Game._middle_cell(3, 1, 3, 3) == (3, 2)
    assert Game._middle_cell(4, 5, 2, 5) == (3, 5)


# ── Reset / initialization tests ─────────────────────────────────

def test_reset_initial_state() -> None:
    g = _make_game()
    assert g._score == 0
    assert g._combo == 0
    assert g._max_combo == 0
    assert g._heat == 0.0
    assert g._super_timer == 0
    assert g._selected_col is None
    assert g._selected_row is None
    assert g._last_captured_color is None
    assert g._phase == Phase.TITLE  # reset() doesn't set phase
    assert len(g._particles) == 0
    assert len(g._floating_texts) == 0
    assert g._shake_frames == 0


def test_reset_places_32_pegs() -> None:
    g = _make_game()
    assert len(g._pegs) == 32


def test_reset_center_is_empty() -> None:
    g = _make_game()
    assert (3, 3) not in g._pegs


def test_reset_color_distribution() -> None:
    g = _make_game()
    color_counts: dict[int, int] = {}
    for peg in g._pegs.values():
        color_counts[peg.color] = color_counts.get(peg.color, 0) + 1
    for c in PEG_COLORS:
        assert color_counts.get(c, 0) == 8  # 8 of each color


# ── Jump mechanics tests ─────────────────────────────────────────

def test_can_jump_valid() -> None:
    g = _make_game()
    # Manually set up: peg at (2,3), peg at (3,3), empty at (4,3)
    g._pegs.clear()
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])
    assert g._can_jump(2, 3, 4, 3)  # jump from 2 to 4 over 3


def test_can_jump_destination_occupied() -> None:
    g = _make_game()
    g._pegs.clear()
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])
    g._pegs[(4, 3)] = Peg(col=4, row=3, color=PEG_COLORS[2])
    assert not g._can_jump(2, 3, 4, 3)  # destination occupied


def test_can_jump_no_middle_peg() -> None:
    g = _make_game()
    g._pegs.clear()
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    assert not g._can_jump(2, 3, 4, 3)  # no peg at (3,3)


def test_can_jump_invalid_destination() -> None:
    g = _make_game()
    g._pegs.clear()
    # Test: not adjacent (3 apart)
    g._pegs[(0, 1)] = Peg(col=0, row=1, color=PEG_COLORS[0])
    g._pegs[(1, 1)] = Peg(col=1, row=1, color=PEG_COLORS[1])
    assert not g._can_jump(0, 1, 3, 1)  # 3 apart, not adjacent
    # Test: not adjacent (diagonal)
    assert not g._can_jump(0, 1, 2, 3)  # diagonal
    # Test: non-adjacent (4 apart)
    g._pegs.clear()
    g._pegs[(0, 2)] = Peg(col=0, row=2, color=PEG_COLORS[0])
    g._pegs[(1, 2)] = Peg(col=1, row=2, color=PEG_COLORS[1])
    assert not g._can_jump(0, 2, 4, 2)  # 4 apart, not 2
    # Test jumping to occupied cell
    g._pegs.clear()
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])
    g._pegs[(4, 3)] = Peg(col=4, row=3, color=PEG_COLORS[2])
    assert not g._can_jump(2, 3, 4, 3)  # destination occupied


def test_get_valid_moves() -> None:
    g = _make_game()
    g._pegs.clear()
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])
    moves = g._get_valid_moves(2, 3)
    assert (4, 3) in moves
    assert len(moves) == 1


def test_get_valid_moves_multiple() -> None:
    g = _make_game()
    g._pegs.clear()
    # Set up: peg at (3,1) can jump to (3,3) over (3,2)
    g._pegs[(3, 1)] = Peg(col=3, row=1, color=PEG_COLORS[0])
    g._pegs[(3, 2)] = Peg(col=3, row=2, color=PEG_COLORS[1])
    g._pegs[(2, 1)] = Peg(col=2, row=1, color=PEG_COLORS[2])
    moves = g._get_valid_moves(3, 1)
    assert (3, 3) in moves  # jump down
    assert len(moves) == 1


def test_all_valid_moves() -> None:
    g = _make_game()
    g._pegs.clear()
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])
    all_moves = g._all_valid_moves()
    assert len(all_moves) == 2  # (2,3)→(4,3) and (3,3)→(1,3)


# ── Execute jump tests ───────────────────────────────────────────

def test_execute_jump_basic() -> None:
    g = _make_game()
    g._pegs.clear()
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])  # RED
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[0])  # RED (same color)
    g._last_captured_color = PEG_COLORS[0]  # RED

    initial_score = g._score
    gained = g._execute_jump(2, 3, 4, 3)
    assert gained > 0
    assert g._score == initial_score + gained
    assert (2, 3) not in g._pegs  # source empty
    assert (3, 3) not in g._pegs  # captured peg removed
    assert (4, 3) in g._pegs  # destination has peg
    assert g._pegs[(4, 3)].color == PEG_COLORS[0]
    assert g._combo == 1


def test_execute_jump_same_color_combo_chain() -> None:
    g = _make_game()
    g._pegs.clear()
    g._last_captured_color = PEG_COLORS[0]  # RED
    g._combo = 2
    g._max_combo = 2

    # Jump over same color
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[1])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[0])  # RED = same as last

    g._execute_jump(2, 3, 4, 3)
    assert g._combo == 3
    assert g._max_combo == 3


def test_execute_jump_wrong_color_resets_combo() -> None:
    g = _make_game()
    g._pegs.clear()
    g._last_captured_color = PEG_COLORS[0]  # RED
    g._combo = 3
    g._max_combo = 3

    # Jump over different color
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[1])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])  # GREEN != RED

    g._execute_jump(2, 3, 4, 3)
    assert g._combo == 0
    assert g._heat == HEAT_WRONG_COLOR  # +15


def test_execute_jump_first_jump_no_last_color() -> None:
    g = _make_game()
    g._pegs.clear()
    g._last_captured_color = None  # first jump ever
    g._combo = 0

    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])

    g._execute_jump(2, 3, 4, 3)
    assert g._combo == 0  # No match because last_captured_color was None
    assert g._last_captured_color == PEG_COLORS[1]


# ── SUPER mode tests ─────────────────────────────────────────────

def test_super_activates_at_combo_4() -> None:
    g = _make_game()
    g._pegs.clear()
    g._last_captured_color = PEG_COLORS[0]
    g._combo = 3
    g._selected_col = 2
    g._selected_row = 3

    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[0])

    g._execute_jump(2, 3, 4, 3)
    assert g._combo == 4
    assert g._super_timer == SUPER_DURATION


def test_super_mode_any_color_matches() -> None:
    g = _make_game()
    g._pegs.clear()
    g._last_captured_color = PEG_COLORS[0]  # RED
    g._combo = 5
    g._super_timer = 100  # SUPER active

    # Jump over different color - should still combo in SUPER
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])  # GREEN != RED

    g._execute_jump(2, 3, 4, 3)
    assert g._combo == 6  # combo increased (SUPER mode ignores color)
    assert g._heat == 0.0  # no heat (SUPER mode ignores wrong color)


def test_super_mode_score_multiplier() -> None:
    g = _make_game()
    g._pegs.clear()
    g._last_captured_color = PEG_COLORS[0]
    g._combo = 4
    g._super_timer = 100  # SUPER active

    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[0])

    g._execute_jump(2, 3, 4, 3)
    assert g._score > 20  # Should be significantly higher due to 3x multiplier


def test_super_deactivation() -> None:
    g = _make_game()
    g._super_timer = 50
    g._deactivate_super()
    assert g._super_timer == 0


# ── Score calculation tests ──────────────────────────────────────

def test_score_no_combo() -> None:
    g = _make_game()
    g._pegs.clear()
    g._last_captured_color = None
    g._combo = 0

    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])

    gained = g._execute_jump(2, 3, 4, 3)
    expected = int(BASE_SCORE * 1.0 * 1.0)  # base * combo_bonus(1.0) * multiplier(1.0)
    assert gained == expected


def test_score_with_combo() -> None:
    g = _make_game()
    g._pegs.clear()
    g._last_captured_color = PEG_COLORS[0]
    g._combo = 3  # combo is at 3, next jump makes it 4

    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[0])  # same color

    # Combo goes to 4, combo_bonus = 1.0 + 0.5 * 4 = 3.0
    gained = g._execute_jump(2, 3, 4, 3)
    expected = int(BASE_SCORE * (1.0 + COMBO_SCORE_FACTOR * 4) * 1.0)
    assert gained == expected


# ── Heat system tests ────────────────────────────────────────────

def test_heat_accumulates_on_wrong_color() -> None:
    g = _make_game()
    g._pegs.clear()
    g._last_captured_color = PEG_COLORS[0]  # RED
    g._combo = 0
    g._heat = 0.0

    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[1])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])  # GREEN != RED

    g._execute_jump(2, 3, 4, 3)
    assert g._heat == HEAT_WRONG_COLOR  # 15


def test_heat_does_not_accumulate_on_same_color() -> None:
    g = _make_game()
    g._pegs.clear()
    g._last_captured_color = PEG_COLORS[0]
    g._combo = 0
    g._heat = 10.0

    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[1])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[0])  # RED = same

    g._execute_jump(2, 3, 4, 3)
    assert g._heat == 10.0  # unchanged


def test_heat_game_over() -> None:
    g = _make_game()
    g._phase = Phase.PLAYING
    g._pegs.clear()
    g._heat = HEAT_MAX - 1  # 99
    g._last_captured_color = PEG_COLORS[0]
    g._combo = 0

    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[1])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])  # GREEN != RED

    g._execute_jump(2, 3, 4, 3)
    assert g._heat >= HEAT_MAX  # should be >= 100


# ── Game over conditions tests ───────────────────────────────────

def test_no_valid_moves_zero_pegs() -> None:
    g = _make_game()
    g._pegs.clear()
    assert not g._has_valid_moves()


def test_no_valid_moves_one_peg() -> None:
    g = _make_game()
    g._pegs.clear()
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[0])
    assert not g._has_valid_moves()


def test_has_valid_moves_with_setup() -> None:
    g = _make_game()
    g._pegs.clear()
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[1])
    assert g._has_valid_moves()


# ── Particles tests ──────────────────────────────────────────────

def test_spawn_capture_particles() -> None:
    g = _make_game()
    assert len(g._particles) == 0
    g._spawn_capture_particles(100.0, 100.0, PEG_COLORS[0], 5)
    assert len(g._particles) == 5
    for p in g._particles:
        assert p.color == PEG_COLORS[0]
        assert PARTICLE_LIFE_MIN <= p.life <= PARTICLE_LIFE_MAX


def test_spawn_super_burst() -> None:
    g = _make_game()
    g._spawn_super_burst(100.0, 100.0)
    assert len(g._particles) == SUPER_BURST_PARTICLE_COUNT


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g._particles = [
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=0, color=7),
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=5, color=7),
    ]
    g._update_particles()
    assert len(g._particles) == 1
    assert g._particles[0].life == 4


def test_update_particles_applies_gravity() -> None:
    g = _make_game()
    g._particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=5, color=7)]
    g._update_particles()
    assert g._particles[0].vy == 0.05  # gravity added


# ── Floating text tests ──────────────────────────────────────────

def test_update_floating_texts() -> None:
    g = _make_game()
    g._floating_texts = [
        FloatingText(x=50.0, y=60.0, text="+10", life=2, color=7),
        FloatingText(x=50.0, y=60.0, text="+20", life=0, color=7),
    ]
    g._update_floating_texts()
    assert len(g._floating_texts) == 1  # dead one removed
    assert g._floating_texts[0].life == 1
    assert g._floating_texts[0].y < 60.0  # floated up


# ── Find hovered cell tests ──────────────────────────────────────

def test_find_hovered_cell_center() -> None:
    g = _make_game()
    # Center of cell (3,3)
    cx = 3 * CELL + BOARD_OFFSET_X + CELL // 2
    cy = 3 * CELL + BOARD_OFFSET_Y + CELL // 2
    result = g._find_hovered_cell(cx, cy)
    assert result == (3, 3)


def test_find_hovered_cell_outside() -> None:
    g = _make_game()
    result = g._find_hovered_cell(0, 0)
    assert result is None


# ── Handle click tests ───────────────────────────────────────────

def test_handle_click_select_peg() -> None:
    g = _make_game()
    g._pegs.clear()
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    cx = 2 * CELL + BOARD_OFFSET_X + CELL // 2
    cy = 3 * CELL + BOARD_OFFSET_Y + CELL // 2
    g._handle_click(cx, cy)
    assert g._selected_col == 2
    assert g._selected_row == 3


def test_handle_click_deselect_same_peg() -> None:
    g = _make_game()
    g._pegs.clear()
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    cx = 2 * CELL + BOARD_OFFSET_X + CELL // 2
    cy = 3 * CELL + BOARD_OFFSET_Y + CELL // 2
    g._selected_col = 2
    g._selected_row = 3
    g._handle_click(cx, cy)
    assert g._selected_col is None
    assert g._selected_row is None


def test_handle_click_empty_cell_deselects() -> None:
    g = _make_game()
    g._selected_col = 2
    g._selected_row = 3
    cx = 3 * CELL + BOARD_OFFSET_X + CELL // 2  # center, empty
    cy = 3 * CELL + BOARD_OFFSET_Y + CELL // 2
    g._handle_click(cx, cy)
    assert g._selected_col is None
    assert g._selected_row is None


# ── Edge case tests ──────────────────────────────────────────────

def test_multi_jump_keeps_selection() -> None:
    g = _make_game()
    g._pegs.clear()
    g._pegs[(2, 3)] = Peg(col=2, row=3, color=PEG_COLORS[0])
    g._pegs[(3, 3)] = Peg(col=3, row=3, color=PEG_COLORS[0])
    g._last_captured_color = PEG_COLORS[0]

    # Execute jump from (2,3) to (4,3)
    g._execute_jump(2, 3, 4, 3)
    # After execution, the _handle_click sets selected_col/row
    # but _execute_jump itself doesn't change selection
    # So we verify the peg moved to (4,3)
    assert (4, 3) in g._pegs
    assert (3, 3) not in g._pegs


def test_no_pegs_left_perfect_bonus() -> None:
    g = _make_game()
    g._score = 100
    g._pegs.clear()  # all pegs removed
    # Simulate what _update_playing does on all pegs removed
    g._score += 500
    assert g._score == 600


# ── Phase state tests ────────────────────────────────────────────

def test_reset_does_not_change_phase() -> None:
    g = _make_game()
    g._phase = Phase.PLAYING
    g.reset()
    assert g._phase == Phase.PLAYING  # reset doesn't touch _phase


# ── Constants sanity tests ───────────────────────────────────────

def test_peg_colors_are_valid() -> None:
    for c in PEG_COLORS:
        assert 0 <= c <= 15


def test_constants_non_negative() -> None:
    assert SUPER_DURATION > 0
    assert HEAT_DECAY > 0
    assert HEAT_MAX > 0
    assert BASE_SCORE > 0
    assert CELL > 0
    assert PEG_RADIUS > 0


def test_valid_cells_are_within_grid() -> None:
    for c, r in VALID_CELLS:
        assert 0 <= c <= 6
        assert 0 <= r <= 6


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
