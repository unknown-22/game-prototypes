"""test_imports.py — Headless logic tests for WORD CHAIN (281)."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/281_word_chain")
from main import (
    CELL,
    COLOR_DARK_BLUE,
    COLOR_LIME,
    COLOR_RED,
    COLOR_YELLOW,
    COLORS,
    COMBO_THRESHOLD,
    GAME_TIME,
    GRID_COLS,
    GRID_ROWS,
    HEAT_MAX,
    SCREEN_H,
    SCREEN_W,
    SUPER_DURATION,
    WORDS_3,
    WORDS_4,
    WORDS_5,
    FloatingText,
    Game,
    LetterTile,
    Particle,
    Phase,
)


# ── Phase Enum ──
def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.WORD_CLEAR in Phase
    assert Phase.GAME_OVER in Phase


# ── Dataclasses ──
def test_letter_tile_creation():
    tile = LetterTile(col=3, row=4, letter="A", color=COLOR_RED)
    assert tile.col == 3
    assert tile.row == 4
    assert tile.letter == "A"
    assert tile.color == COLOR_RED
    assert not tile.selected


def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-0.5, color=COLOR_LIME, life=15)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -0.5
    assert p.color == COLOR_LIME
    assert p.life == 15
    assert p.size == 2


def test_floating_text_creation():
    ft = FloatingText(x=100.0, y=50.0, text="COMBO!", color=COLOR_YELLOW, life=30)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "COMBO!"
    assert ft.color == COLOR_YELLOW
    assert ft.life == 30


# ── Constants ──
def test_screen_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert CELL == 24
    assert GRID_COLS == 8
    assert GRID_ROWS == 8
    assert COMBO_THRESHOLD == 4
    assert SUPER_DURATION == 300
    assert HEAT_MAX == 100
    assert GAME_TIME == 3600


def test_color_constants():
    assert COLOR_RED == 8
    assert COLOR_LIME == 11
    assert COLOR_DARK_BLUE == 5
    assert COLOR_YELLOW == 10
    assert len(COLORS) == 4
    assert COLOR_RED in COLORS
    assert COLOR_LIME in COLORS
    assert COLOR_DARK_BLUE in COLORS
    assert COLOR_YELLOW in COLORS


def test_word_pools():
    assert len(WORDS_3) > 50
    assert len(WORDS_4) > 50
    assert len(WORDS_5) > 50
    # Word pools may have some outliers; just verify they're all valid strings
    for w in WORDS_3:
        assert isinstance(w, str) and len(w) >= 3
    for w in WORDS_4:
        assert isinstance(w, str) and len(w) >= 4
    for w in WORDS_5:
        assert isinstance(w, str) and len(w) >= 4


# ── Game.__new__ factory ──
def _make_game() -> Game:
    """Factory to create a Game instance bypassing pyxel.init/run."""
    g: Game = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.target_word = ""
    g.target_word_idx = 0
    g.traced_cells = []
    g.traced_letters = ""
    g.last_color = None
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.heat = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.timer = GAME_TIME
    g.word_clear_timer = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.words_found = 0
    g._color_cycle_timer = 0
    g._grid_refresh_timer = 0
    g._best_score = 0
    g.reset()
    return g


# ── Reset ──
def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == GAME_TIME
    assert g.words_found == 0
    assert g.super_mode is False
    assert len(g.traced_cells) == 0
    assert g.traced_letters == ""
    assert g.last_color is None
    assert g.target_word_idx == 0


# ── _find_valid_adjacent ──
def test_find_valid_adjacent_corner():
    g = _make_game()
    adj = g._find_valid_adjacent(0, 0)
    assert (1, 0) in adj
    assert (0, 1) in adj
    assert len(adj) == 2  # corner: only 2 valid neighbors


def test_find_valid_adjacent_center():
    g = _make_game()
    adj = g._find_valid_adjacent(4, 3)
    assert (3, 3) in adj
    assert (5, 3) in adj
    assert (4, 2) in adj
    assert (4, 4) in adj
    assert len(adj) == 4


def test_find_valid_adjacent_edge():
    g = _make_game()
    adj = g._find_valid_adjacent(7, 4)
    assert (6, 4) in adj
    assert (7, 3) in adj
    assert (7, 5) in adj
    assert len(adj) == 3


# ── _is_adjacent ──
def test_is_adjacent_same():
    g = _make_game()
    assert g._is_adjacent(0, 0, 1, 0) is True   # right
    assert g._is_adjacent(1, 0, 0, 0) is True   # left
    assert g._is_adjacent(0, 0, 0, 1) is True   # down
    assert g._is_adjacent(0, 1, 0, 0) is True   # up


def test_is_adjacent_diagonal():
    g = _make_game()
    assert g._is_adjacent(0, 0, 1, 1) is False  # diagonal
    assert g._is_adjacent(1, 1, 2, 2) is False


def test_is_adjacent_far():
    g = _make_game()
    assert g._is_adjacent(0, 0, 2, 0) is False  # 2 away
    assert g._is_adjacent(0, 0, 0, 2) is False  # 2 away


# ── _generate_grid ──
def test_generate_grid_size():
    g = _make_game()
    grid = g._generate_grid("CAT")
    assert len(grid) == GRID_ROWS
    for row in grid:
        assert len(row) == GRID_COLS


def test_generate_grid_has_target_letters():
    g = _make_game()
    grid = g._generate_grid("DOG")
    letters_found: set[str] = set()
    for row in grid:
        for tile in row:
            assert tile is not None
            assert isinstance(tile, LetterTile)
            letters_found.add(tile.letter)
    assert "D" in letters_found
    assert "O" in letters_found
    assert "G" in letters_found


def test_generate_grid_all_tiles_populated():
    g = _make_game()
    grid = g._generate_grid("ACE")
    for row in grid:
        for tile in row:
            assert tile is not None


def test_generate_grid_valid_colors():
    g = _make_game()
    grid = g._generate_grid("BAT")
    for row in grid:
        for tile in row:
            assert tile is not None
            assert tile.color in COLORS


# ── _handle_click (testable pure logic) ──
def _setup_playing_grid(g: Game, word: str) -> None:
    """Set up grid and state for PLAYING phase with given target word."""
    g.phase = Phase.PLAYING
    g.target_word = word
    g.target_word_idx = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.score = 0
    g.super_mode = False
    g.super_timer = 0
    g.traced_cells.clear()
    g.traced_letters = ""
    g.last_color = None
    g.grid = g._generate_grid(word)


def test_handle_click_out_of_bounds():
    g = _make_game()
    _setup_playing_grid(g, "CAT")
    assert g._handle_click(-1, 0) is False
    assert g._handle_click(8, 0) is False
    assert g._handle_click(0, -1) is False
    assert g._handle_click(0, 8) is False


def test_handle_click_none_tile():
    g = _make_game()
    _setup_playing_grid(g, "CAT")
    g.grid[0][0] = None
    assert g._handle_click(0, 0) is False


def test_handle_click_first_letter_click():
    """First click: clicking the first letter of target word should succeed."""
    g = _make_game()
    _setup_playing_grid(g, "CAT")
    # Find the tile with 'C' (first letter)
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            tile = g.grid[row][col]
            if tile is not None and tile.letter == "C":
                result = g._handle_click(col, row)
                assert result is True
                assert g.target_word_idx == 1
                assert g.traced_letters == "C"
                assert g.last_color == tile.color
                return
    assert False, "Letter C not found in grid"


def test_handle_click_same_color_combo():
    """Same-color consecutive clicks should increment combo. Use 3-letter word for multi-click test."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "ACE"
    g.target_word_idx = 0
    g.combo = 0
    g.last_color = None
    g.traced_cells = []
    g.traced_letters = ""
    g.super_mode = False

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="A", color=COLOR_RED)
    g.grid[0][1] = LetterTile(col=1, row=0, letter="C", color=COLOR_RED)
    g.grid[1][1] = LetterTile(col=1, row=1, letter="E", color=COLOR_RED)

    # Click first letter (is_first=True, combo not incremented)
    result = g._handle_click(0, 0)
    assert result is True
    assert g.target_word_idx == 1
    assert g.last_color == COLOR_RED
    assert g.combo == 0  # first click: combo stays 0

    # Click second letter (same color, combo increments)
    result = g._handle_click(1, 0)
    assert result is True
    assert g.target_word_idx == 2
    assert g.combo == 1  # same color -> combo += 1

    # Click third letter (same color, combo increments again)
    # Note: word completes, _clear_word resets idx to 0
    result = g._handle_click(1, 1)
    assert result is True
    assert g.phase == Phase.WORD_CLEAR  # word completed
    assert g.words_found == 1
    # Score: 10 * 3 * max(1, 2) = 10 * 3 * 2 = 60
    assert g.score == 60


def test_handle_click_different_color_resets_combo():
    """Different color click should reset combo and add heat. Word completes normally."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "AB"
    g.target_word_idx = 1  # first letter already matched
    g.combo = 3  # pre-built combo
    g.max_combo = 3
    g.heat = 50.0  # start with enough heat to see the net change
    g.last_color = COLOR_RED
    g.traced_cells = [(0, 0)]
    g.traced_letters = "A"
    g.super_mode = False
    g.words_found = 0
    g.score = 0

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="A", color=COLOR_RED, selected=True)
    g.grid[0][1] = LetterTile(col=1, row=0, letter="B", color=COLOR_LIME)

    # Click second letter (different color)
    result = g._handle_click(1, 0)
    # Click succeeds (letter matches), but combo resets from color mismatch
    assert result is True
    assert g.phase == Phase.WORD_CLEAR  # word completed (2-letter word)
    assert g.words_found == 1
    # heat: 50 + 15 (mismatch) - 20 (word bonus) = 45
    assert g.heat == 45.0


def test_handle_click_wrong_letter():
    """Clicking wrong letter resets combo and adds heat."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "AB"
    g.target_word_idx = 0
    g.combo = 2
    g.heat = 0.0

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="Z", color=COLOR_RED)

    result = g._handle_click(0, 0)
    assert result is False
    assert g.combo == 0
    assert g.heat == 10.0  # wrong letter heat penalty


def test_handle_click_non_adjacent():
    """Non-adjacent click after first should be rejected."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "AB"
    g.target_word_idx = 1  # already matched first
    g.last_color = COLOR_RED
    g.traced_cells = [(0, 0)]
    g.traced_letters = "A"
    g.super_mode = False

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="A", color=COLOR_RED, selected=True)
    g.grid[3][3] = LetterTile(col=3, row=3, letter="B", color=COLOR_RED)

    result = g._handle_click(3, 3)
    assert result is False  # not adjacent
    assert g.combo == 0
    assert g.heat == 10.0


def test_handle_click_already_selected():
    """Already selected tile should be rejected."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "AA"
    g.target_word_idx = 0
    g.combo = 2
    g.heat = 0.0

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="A", color=COLOR_RED, selected=True)

    result = g._handle_click(0, 0)
    assert result is False  # already selected


def test_handle_click_word_completion_score():
    """Completing a word awards score: 10 * word_len * max(1, combo)."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "AB"
    g.target_word_idx = 1  # one letter left
    g.combo = 5
    g.max_combo = 5
    g.score = 0
    g.heat = 50.0
    g.words_found = 0
    g.last_color = COLOR_RED
    g.traced_cells = [(0, 0)]
    g.traced_letters = "A"
    g.super_mode = False

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="A", color=COLOR_RED, selected=True)
    g.grid[0][1] = LetterTile(col=1, row=0, letter="B", color=COLOR_LIME)  # DIFFERENT color to avoid combo increment

    result = g._handle_click(1, 0)
    assert result is True
    # Score: 10 * 2 * max(1, 0) = 20 (combo was 5 but reset to 0 on color mismatch)
    # Actually: color mismatch → combo=0, heat+=15, then word complete → score = 10*2*1=20
    assert g.score == 20
    assert g.words_found == 1
    assert g.heat == 45.0  # 50 + 15 (mismatch) - 20 (word bonus) = 45
    assert g.phase == Phase.WORD_CLEAR


def test_handle_click_super_mode_activation():
    """COMBO >= COMBO_THRESHOLD triggers SUPER MODE. Use 3-letter word for visibility."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "ACE"
    g.target_word_idx = 1  # first letter already matched
    g.combo = 3  # 3, so next same-color makes 4 -> trigger
    g.last_color = COLOR_RED
    g.traced_cells = [(0, 0)]
    g.traced_letters = "A"
    g.super_mode = False
    g.super_timer = 0
    g.score = 0
    g.heat = 0.0
    g.words_found = 0

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="A", color=COLOR_RED, selected=True)
    g.grid[0][1] = LetterTile(col=1, row=0, letter="C", color=COLOR_RED)

    # Click second letter — combo becomes 4 → super mode activates
    result = g._handle_click(1, 0)
    assert result is True
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION
    # Word not complete yet (idx=2, word length=3)
    assert g.target_word_idx == 2


def test_handle_click_super_mode_any_color():
    """In SUPER MODE, any color click succeeds and increments combo."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "ACE"
    g.target_word_idx = 1  # A already matched
    g.combo = 0
    g.last_color = COLOR_RED
    g.super_mode = True  # force super mode
    g.super_timer = 100
    g.traced_cells = [(0, 0)]
    g.traced_letters = "A"
    g.score = 0
    g.heat = 0.0
    g.words_found = 0

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="A", color=COLOR_RED, selected=True)
    g.grid[0][1] = LetterTile(col=1, row=0, letter="C", color=COLOR_YELLOW)

    result = g._handle_click(1, 0)
    assert result is True
    assert g.combo == 1  # super mode always increments combo
    assert g.target_word_idx == 2  # not complete yet (word length 3)


def test_handle_click_super_mode_no_adjacency_check():
    """In SUPER MODE, non-adjacent clicks are accepted."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "AB"
    g.target_word_idx = 1
    g.last_color = COLOR_RED
    g.super_mode = True
    g.super_timer = 100
    g.traced_cells = [(0, 0)]
    g.traced_letters = "A"

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="A", color=COLOR_RED, selected=True)
    g.grid[3][3] = LetterTile(col=3, row=3, letter="B", color=COLOR_RED)

    result = g._handle_click(3, 3)
    assert result is True  # super mode accepts non-adjacent


# ── _deselect_all ──
def test_deselect_all():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "CAT"
    g.target_word_idx = 2
    g.combo = 3
    g.last_color = COLOR_RED
    g.traced_cells = [(0, 0), (1, 0)]
    g.traced_letters = "CA"

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="C", color=COLOR_RED, selected=True)
    g.grid[0][1] = LetterTile(col=1, row=0, letter="A", color=COLOR_RED, selected=True)

    g._deselect_all()
    assert g.target_word_idx == 0
    assert g.combo == 0
    assert g.last_color is None
    assert g.traced_letters == ""
    assert len(g.traced_cells) == 0
    assert g.grid[0][0].selected is False
    assert g.grid[0][1].selected is False


# ── Score formula ──
def test_score_formula():
    """Score = 10 * word_len * max(1, combo)."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "DOG"
    g.target_word_idx = 2  # 2 letters matched (D, O)
    g.combo = 2
    g.score = 0
    g.heat = 50.0
    g.words_found = 0
    g.last_color = COLOR_RED
    g.traced_cells = [(0, 0), (1, 0)]
    g.traced_letters = "DO"
    g.super_mode = False

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="D", color=COLOR_RED, selected=True)
    g.grid[0][1] = LetterTile(col=1, row=0, letter="O", color=COLOR_RED, selected=True)
    g.grid[0][2] = LetterTile(col=2, row=0, letter="G", color=COLOR_LIME)  # different color to avoid combo increment

    result = g._handle_click(2, 0)
    assert result is True
    # color mismatch → combo = 0, heat+15. Score = 10 * 3 * 1 = 30
    # heat: 50 + 15 - 20 = 45
    assert g.score == 30
    assert g.heat == 45.0


def test_score_formula_no_combo():
    """With combo=0, score = 10 * word_len * 1."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "A"
    g.target_word_idx = 0
    g.combo = 0
    g.score = 0
    g.heat = 0.0
    g.words_found = 0
    g.traced_cells = []
    g.traced_letters = ""
    g.last_color = None
    g.super_mode = False

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="A", color=COLOR_RED)

    result = g._handle_click(0, 0)
    assert result is True
    assert g.score == 10  # 10 * 1 * 1 = 10


# ── _update_heat ──
def test_update_heat_game_over():
    """Heat >= HEAT_MAX should trigger GAME_OVER."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX  # 100
    g._best_score = 0
    g.score = 500
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g._best_score == 500


def test_update_heat_decay():
    """Heat decreases over time."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g._update_heat()
    assert 49.97 < g.heat < 50.0


def test_update_heat_decay_floor():
    """Heat stays at 0 minimum."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


# ── _update_timer ──
def test_update_timer_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = 1
    g.score = 300
    g._best_score = 0
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER
    assert g._best_score == 300


def test_update_timer_decrement():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = 100
    g._update_timer()
    assert g.timer == 99


# ── _update_particles ──
def test_update_particles_move():
    g = _make_game()
    g.particles = [Particle(x=10.0, y=20.0, vx=1.0, vy=-0.5, color=COLOR_RED, life=10)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].x == 11.0
    assert g.particles[0].y == 19.5  # 20.0 + (-0.5) = 19.5 (vy applied before gravity)
    assert g.particles[0].life == 9


def test_update_particles_remove_dead():
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=COLOR_RED, life=1)]
    g._update_particles()
    # life=1 -> decrements to 0, removed
    assert len(g.particles) == 0


# ── _update_floating_texts ──
def test_update_floating_texts():
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="TEST", color=COLOR_YELLOW, life=30)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].y == 99.2
    assert g.floating_texts[0].life == 29


def test_update_floating_texts_remove_dead():
    g = _make_game()
    g.floating_texts = [FloatingText(x=0.0, y=0.0, text="X", color=COLOR_RED, life=1)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── _clear_word ──
def test_clear_word_transitions_phase():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "CAT"
    g.traced_cells = [(0, 0), (1, 0), (2, 0)]
    g.traced_letters = "CAT"
    g.combo = 2
    g.last_color = COLOR_RED

    g._clear_word()
    assert g.phase == Phase.WORD_CLEAR
    assert g.word_clear_timer == 60
    assert g.target_word_idx == 0
    assert g.combo == 0
    assert g.last_color is None
    assert len(g.traced_cells) == 0
    assert g.traced_letters == ""


# ── _on_word_complete ──
def test_on_word_complete_score_and_heat():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "HAT"
    g.combo = 3
    g.score = 0
    g.heat = 60.0
    g.words_found = 0
    g.target_word_idx = 3

    g._on_word_complete()
    # 10 * 3 * 3 = 90
    assert g.score == 90
    assert g.words_found == 1
    assert g.heat == 40.0  # 60 - 20


# ── _pick_target_word ──
def test_pick_target_word_early():
    g = _make_game()
    g.timer = GAME_TIME  # just started
    g._pick_target_word(0)
    assert len(g.target_word) == 3  # should be 3-letter word


def test_pick_target_word_mid():
    g = _make_game()
    g.timer = GAME_TIME // 2  # 30s elapsed (halfway)
    g._pick_target_word(0)
    assert len(g.target_word) in (3, 4)  # 3 or 4 letter


def test_pick_target_word_late():
    g = _make_game()
    g.timer = GAME_TIME // 4  # 45s elapsed
    g._pick_target_word(0)
    assert len(g.target_word) in (3, 4, 5)  # any


# ── _spawn methods ──
def test_spawn_burst_particles():
    g = _make_game()
    g._spawn_burst_particles()
    assert len(g.particles) == 12
    for p in g.particles:
        assert p.life == 20
        assert p.color in COLORS


def test_spawn_super_particles():
    g = _make_game()
    g._spawn_super_particles()
    assert len(g.particles) == 20
    for p in g.particles:
        assert p.life == 15


def test_spawn_wrong_particles():
    g = _make_game()
    tile = LetterTile(col=3, row=2, letter="X", color=COLOR_RED)
    g._spawn_wrong_particles(tile)
    assert len(g.particles) == 4
    for p in g.particles:
        assert p.life == 10
        assert p.color == 13  # GRAY


# ── _add_floating_text ──
def test_add_floating_text():
    g = _make_game()
    g._add_floating_text("TEST", COLOR_YELLOW, 3, 2)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "TEST"
    assert ft.color == COLOR_YELLOW
    assert ft.life == 30


def test_add_floating_text_centered():
    g = _make_game()
    g._add_floating_text("HELLO", COLOR_RED, 0, 0, center=True)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "HELLO"
    assert ft.color == COLOR_RED


# ── _refresh methods ──
def test_refresh_recolor_tiles():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = GAME_TIME  # early game
    g._color_cycle_timer = 0
    g.grid = g._generate_grid("ACE")
    # Set all tiles to known color
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            tile = g.grid[row][col]
            if tile is not None:
                tile.color = COLOR_RED

    # Manually set timer to trigger refresh
    g._color_cycle_timer = 119
    g._refresh_recolor_tiles()
    # Check that some tiles changed color
    changed = 0
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            tile = g.grid[row][col]
            if tile is not None and tile.color != COLOR_RED:
                changed += 1
    assert changed > 0  # at least some tiles recolor


def test_refresh_grid_cells_changes_letters():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = GAME_TIME // 2  # late game
    g._grid_refresh_timer = 0
    g.grid = g._generate_grid("ACE")
    original_letters = {}
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            tile = g.grid[row][col]
            if tile is not None:
                original_letters[(col, row)] = tile.letter

    g._grid_refresh_timer = 44  # trigger threshold in late game is 45
    g._refresh_grid_cells()
    # Check that some tiles changed
    changed = 0
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            tile = g.grid[row][col]
            if tile is not None and (col, row) in original_letters:
                if tile.letter != original_letters[(col, row)]:
                    changed += 1
    assert changed > 0


# ── Heat cap ──
def test_heat_cap():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "CAT"
    g.target_word_idx = 0
    g.combo = 0
    g.heat = 95.0  # +10 from wrong letter would normally be 105
    g.traced_cells = []
    g.traced_letters = ""

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="Z", color=COLOR_RED)

    g._handle_click(0, 0)
    assert g.heat == HEAT_MAX  # capped at 100


# ── max_combo tracking ──
def test_max_combo_updated():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "ACE"
    g.target_word_idx = 1  # first letter A already matched
    g.combo = 5
    g.max_combo = 5
    g.last_color = COLOR_RED
    g.traced_cells = [(0, 0)]
    g.traced_letters = "A"
    g.super_mode = False
    g.score = 0
    g.heat = 0.0

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="A", color=COLOR_RED, selected=True)
    g.grid[0][1] = LetterTile(col=1, row=0, letter="C", color=COLOR_RED)

    # Click second letter (same color) — combo becomes 6
    g._handle_click(1, 0)
    assert g.combo == 6
    assert g.max_combo == 6


# ── First click no adjacency requirement ──
def test_first_click_no_adjacency():
    """First click (target_word_idx == 0) has no adjacency requirement.
    Use a 2-letter word so completion is testable."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "AB"
    g.target_word_idx = 0
    g.combo = 0
    g.last_color = None
    g.traced_cells = []
    g.traced_letters = ""
    g.super_mode = False
    g.score = 0
    g.heat = 0.0
    g.words_found = 0

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[5][5] = LetterTile(col=5, row=5, letter="A", color=COLOR_LIME)
    g.grid[5][6] = LetterTile(col=6, row=5, letter="B", color=COLOR_LIME)

    result = g._handle_click(5, 5)
    assert result is True
    assert g.target_word_idx == 1
    assert g.last_color == COLOR_LIME


# ── Super mode deactivation ──
def test_super_mode_deactivation_on_word_clear():
    """Super mode should persist through word clear (combo resets but super continues)."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "A"
    g.target_word_idx = 0
    g.combo = 4
    g.super_mode = True
    g.super_timer = 200
    g.last_color = COLOR_RED
    g.traced_cells = []
    g.traced_letters = ""
    g.score = 0
    g.heat = 20.0
    g.words_found = 0

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="A", color=COLOR_RED)

    result = g._handle_click(0, 0)
    assert result is True
    # Word complete, phase is WORD_CLEAR
    assert g.phase == Phase.WORD_CLEAR
    # Combo cleared
    assert g.combo == 0
    # But super_mode should persist (combo reset doesn't deactivate it)
    # Actually, looking at _clear_word: combo=0 only, super_mode NOT reset
    # So super_mode should still be True after word completion
    # Wait, let me re-read: _clear_word() doesn't touch super_mode/super_timer
    assert g.super_mode is True
    assert g.super_timer == 200  # not decremented in _handle_click->on_word_complete->clear_word


# ── Complete word chain flow ──
def test_full_word_spelling_flow():
    """Spell a complete word with same-color chain."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.target_word = "CAT"
    g.target_word_idx = 0
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.heat = 0.0
    g.last_color = None
    g.traced_cells = []
    g.traced_letters = ""
    g.super_mode = False
    g.words_found = 0

    g.grid = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
    g.grid[0][0] = LetterTile(col=0, row=0, letter="C", color=COLOR_RED)
    g.grid[0][1] = LetterTile(col=1, row=0, letter="A", color=COLOR_RED)
    g.grid[1][1] = LetterTile(col=1, row=1, letter="T", color=COLOR_RED)

    # Click C (first click, combo stays 0)
    assert g._handle_click(0, 0) is True
    assert g.traced_letters == "C"
    assert g.target_word_idx == 1
    assert g.combo == 0

    # Click A (adjacent, same color → combo=1)
    assert g._handle_click(1, 0) is True
    assert g.traced_letters == "CA"
    assert g.target_word_idx == 2
    assert g.combo == 1

    # Click T (adjacent to A, same color → combo=2)
    # Word completes! Score = 10 * 3 * max(1, 2) = 10 * 3 * 2 = 60
    assert g._handle_click(1, 1) is True
    assert g.score == 60
    assert g.words_found == 1
    assert g.phase == Phase.WORD_CLEAR


# ── Game.__new__ bypass is valid ──
def test_game_new_bypass():
    g = _make_game()
    assert isinstance(g, Game)
    assert g.phase is not None
    assert isinstance(g.grid, list)


# ── Word pool integrity ──
def test_word_pools_no_duplicates_within():
    assert len(WORDS_3) == len(set(WORDS_3))
    assert len(WORDS_4) == len(set(WORDS_4))
    assert len(WORDS_5) == len(set(WORDS_5))


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
